package com.fishai.analyzer

import android.graphics.Bitmap
import android.graphics.Matrix
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import org.opencv.android.Utils
import org.opencv.core.*
import org.opencv.imgproc.Imgproc
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow

data class ProcessedFishFrameResult(
    val processedBitmap: Bitmap,
    val lengthCm: Double,
    val widthCm: Double,
    val estimatedWeightG: Double,
    val detected: Boolean
)

/**
 * CameraX ImageAnalysis analyzer that processes each frame via OpenCV:
 * - Segments and isolates ONLY the fish on a black background.
 * - Draws the green perimeter contour outline.
 * - Computes length, width, and allometric weight.
 * - Produces a display-ready Bitmap for ImageView rendering.
 */
class FishMaskRendererAnalyzer(
    private val ppm: Double = 22.5,
    private val minFishArea: Double = 4000.0,
    private val aParam: Double = 0.015,
    private val bParam: Double = 3.02,
    private val onFrameProcessed: (ProcessedFishFrameResult) -> Unit
) : ImageAnalysis.Analyzer {

    @Volatile
    private var isProcessing = false

    override fun analyze(imageProxy: ImageProxy) {
        if (isProcessing) {
            imageProxy.close()
            return
        }

        isProcessing = true
        val rotationDegrees = imageProxy.imageInfo.rotationDegrees

        try {
            // 1. Convert CameraX image to Bitmap & rotate if needed
            val rawBitmap = imageProxy.toBitmap()
            val inputBitmap = if (rotationDegrees != 0) {
                val matrix = Matrix().apply { postRotate(rotationDegrees.toFloat()) }
                Bitmap.createBitmap(rawBitmap, 0, 0, rawBitmap.width, rawBitmap.height, matrix, true)
            } else {
                rawBitmap
            }

            // 2. Convert Bitmap to OpenCV Mat (RGBA)
            val srcRgba = Mat()
            Utils.bitmapToMat(inputBitmap, srcRgba)

            val gray = Mat()
            val blurred = Mat()
            val thresh = Mat()

            // 3. Pre-processing: Grayscale & Gaussian Blur
            Imgproc.cvtColor(srcRgba, gray, Imgproc.COLOR_RGBA2GRAY)
            Imgproc.GaussianBlur(gray, blurred, Size(5.0, 5.0), 0.0)

            // 4. Otsu inverted thresholding
            Imgproc.threshold(blurred, thresh, 0.0, 255.0, Imgproc.THRESH_BINARY_INV + Imgproc.THRESH_OTSU)

            // 5. Morphological filtering (Close to fill holes, Open to remove specks)
            val morphKernel = Imgproc.getStructuringElement(Imgproc.MORPH_ELLIPSE, Size(7.0, 7.0))
            Imgproc.morphologyEx(thresh, thresh, Imgproc.MORPH_CLOSE, morphKernel, Point(-1.0, -1.0), 2)
            Imgproc.morphologyEx(thresh, thresh, Imgproc.MORPH_OPEN, morphKernel, Point(-1.0, -1.0), 1)

            // 6. Contour detection
            val contours = ArrayList<MatOfPoint>()
            val hierarchy = Mat()
            Imgproc.findContours(thresh, contours, hierarchy, Imgproc.RETR_EXTERNAL, Imgproc.CHAIN_APPROX_SIMPLE)

            var largestIdx = -1
            var maxArea = minFishArea

            for (i in contours.indices) {
                val area = Imgproc.contourArea(contours[i])
                if (area > maxArea) {
                    maxArea = area
                    largestIdx = i
                }
            }

            val displayMat = Mat.zeros(srcRgba.size(), srcRgba.type())
            var detected = false
            var lengthCm = 0.0
            var widthCm = 0.0
            var weightG = 0.0

            if (largestIdx != -1) {
                detected = true
                val contour = contours[largestIdx]
                val contour2f = MatOfPoint2f(*contour.toArray())

                // Metric Calculations
                val minRect: RotatedRect = Imgproc.minAreaRect(contour2f)
                val wPx = min(minRect.size.width, minRect.size.height)
                val lPx = max(minRect.size.width, minRect.size.height)

                lengthCm = lPx / ppm
                widthCm = wPx / ppm
                weightG = aParam * lengthCm.pow(bParam)

                // 7. Isolate ONLY fish: Black background mask
                val fishMask = Mat.zeros(gray.size(), CvType.CV_8UC1)
                Imgproc.drawContours(fishMask, contours, largestIdx, Scalar(255.0), -1)

                srcRgba.copyTo(displayMat, fishMask)

                // Draw perimeter outline (Green)
                Imgproc.drawContours(displayMat, contours, largestIdx, Scalar(0.0, 255.0, 102.0, 255.0), 3)

                fishMask.release()
            } else {
                // If no fish detected, show darkened raw camera feed or clean frame
                srcRgba.copyTo(displayMat)
            }

            // Convert processed OpenCV Mat back to Bitmap for ImageView
            val outBitmap = Bitmap.createBitmap(displayMat.cols(), displayMat.rows(), Bitmap.Config.ARGB_8888)
            Utils.matToBitmap(displayMat, outBitmap)

            onFrameProcessed(
                ProcessedFishFrameResult(
                    processedBitmap = outBitmap,
                    lengthCm = lengthCm,
                    widthCm = widthCm,
                    estimatedWeightG = weightG,
                    detected = detected
                )
            )

            // Cleanup native memory
            srcRgba.release()
            gray.release()
            blurred.release()
            thresh.release()
            morphKernel.release()
            hierarchy.release()
            displayMat.release()

        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            imageProxy.close()
            isProcessing = false
        }
    }
}
