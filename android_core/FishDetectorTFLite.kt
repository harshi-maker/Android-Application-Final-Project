package com.fishai.ml

import android.content.Context
import android.graphics.Bitmap
import android.graphics.RectF
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import org.tensorflow.lite.nnapi.NnApiDelegate
import org.tensorflow.lite.support.common.FileUtil
import java.nio.ByteBuffer
import java.nio.ByteOrder

data class FishKeypoints(
    val snout: Pair<Float, Float>,
    val eye: Pair<Float, Float>,
    val dorsal: Pair<Float, Float>,
    val ventral: Pair<Float, Float>,
    val tailBase: Pair<Float, Float>,
    val tailTip: Pair<Float, Float>
)

data class FishDetectionResult(
    val species: String,
    val confidence: Float,
    val freshnessScore: Float,
    val boundingBox: RectF,
    val keypoints: FishKeypoints
)

class FishDetectorTFLite(
    context: Context,
    modelPath: String = "fish_model_quant.tflite"
) {
    private var interpreter: Interpreter
    private val inputSize = 224
    private val labels = listOf(
        "Atlantic Salmon", "Yellowfin Tuna", "Cod", "Mackerel", 
        "Red Snapper", "Sea Bass", "Tilapia", "Rainbow Trout"
    )

    init {
        val modelBuffer = FileUtil.loadMappedFile(context, modelPath)
        val options = Interpreter.Options()

        // 1. Try NNAPI (NPU) delegate first
        try {
            options.addDelegate(NnApiDelegate())
        } catch (e: Exception) {
            // 2. Fallback to GPU delegate
            val compatList = CompatibilityList()
            if (compatList.isDelegateSupportedOnThisDevice) {
                options.addDelegate(GpuDelegate(compatList.bestOptionsForThisDevice))
            } else {
                options.setNumThreads(4)
            }
        }

        interpreter = Interpreter(modelBuffer, options)
    }

    fun detect(bitmap: Bitmap): FishDetectionResult {
        val resized = Bitmap.createScaledBitmap(bitmap, inputSize, inputSize, true)
        val inputBuffer = ByteBuffer.allocateDirect(inputSize * inputSize * 3).apply {
            order(ByteOrder.nativeOrder())
            rewind()
        }

        val intValues = IntArray(inputSize * inputSize)
        resized.getPixels(intValues, 0, inputSize, 0, 0, inputSize, inputSize)

        for (pixel in intValues) {
            inputBuffer.put(((pixel shr 16) and 0xFF).toByte())
            inputBuffer.put(((pixel shr 8) and 0xFF).toByte())
            inputBuffer.put((pixel and 0xFF).toByte())
        }

        // TFLite output buffers
        val speciesOutput = Array(1) { ByteArray(labels.size) }
        val freshnessOutput = Array(1) { ByteArray(1) }
        val keypointsOutput = Array(1) { ByteArray(12) }

        val outputs = mapOf(
            0 to speciesOutput,
            1 to freshnessOutput,
            2 to keypointsOutput
        )

        interpreter.runForMultipleInputsOutputs(arrayOf(inputBuffer), outputs)

        // Dequantize and decode predictions
        val maxIdx = speciesOutput[0].indices.maxByOrNull { speciesOutput[0][it].toInt() and 0xFF } ?: 0
        val speciesConfidence = (speciesOutput[0][maxIdx].toInt() and 0xFF) / 255.0f
        val freshness = (freshnessOutput[0][0].toInt() and 0xFF) / 255.0f

        val kps = keypointsOutput[0].map { (it.toInt() and 0xFF) / 255.0f }

        return FishDetectionResult(
            species = labels.getOrElse(maxIdx) { "Unknown" },
            confidence = speciesConfidence,
            freshnessScore = freshness,
            boundingBox = RectF(0.1f, 0.2f, 0.9f, 0.8f),
            keypoints = FishKeypoints(
                snout = Pair(kps[0], kps[1]),
                eye = Pair(kps[2], kps[3]),
                dorsal = Pair(kps[4], kps[5]),
                ventral = Pair(kps[6], kps[7]),
                tailBase = Pair(kps[8], kps[9]),
                tailTip = Pair(kps[10], kps[11])
            )
        )
    }

    fun close() {
        interpreter.close()
    }
}
