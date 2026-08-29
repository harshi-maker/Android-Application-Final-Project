package com.fishai.analyzer

import android.graphics.Bitmap
import android.graphics.Matrix
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.fishai.ml.FishDetectorTFLite
import com.fishai.ml.FishDetectionResult

/**
 * CameraX ImageAnalysis frame analyzer.
 * Processes high-rate camera frames non-blockingly using STRATEGY_KEEP_ONLY_LATEST.
 */
class FishFrameAnalyzer(
    private val detector: FishDetectorTFLite,
    private val onResult: (FishDetectionResult) -> Unit
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

        // Convert camera YUV buffer to Bitmap
        val bitmap = imageProxy.toBitmap()

        // Correct orientation if needed
        val rotatedBitmap = if (rotationDegrees != 0) {
            val matrix = Matrix().apply { postRotate(rotationDegrees.toFloat()) }
            Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
        } else {
            bitmap
        }

        try {
            val result = detector.detect(rotatedBitmap)
            onResult(result)
        } finally {
            imageProxy.close()
            isProcessing = false
        }
    }
}
