package com.fishai.math

import android.graphics.PointF

data class FishMetrics(
    val lengthMm: Float,
    val widthMm: Float,
    val heightMm: Float,
    val maxGirthMm: Float,
    val volumeCm3: Float,
    val estimatedWeightGrams: Float
)

object MetricCalibration {

    /**
     * Computes real-world length, width, height, estimated volume (ellipsoid), and weight
     * using camera depth (Z in mm), focal length (pixels), and biological tissue density.
     *
     * @param lengthPx Length of the detected bounding box/contour in pixels (longer dimension)
     * @param widthPx Width of the detected bounding box/contour in pixels (shorter dimension)
     * @param depthZMm Distance from camera to fish plane in mm (e.g. 500 mm)
     * @param focalLengthPx Camera focal length fx/fy in pixels (e.g. 800 px)
     * @param densityGCm3 Fish muscle/tissue density in g/cm³ (default 1.045 g/cm³)
     * @param assumedHeightRatio Ratio of Height to Width if height is not directly visible (default 0.90)
     */
    fun calculateDimensionsAndWeight(
        lengthPx: Float,
        widthPx: Float,
        depthZMm: Float = 500f,
        focalLengthPx: Float = 800f,
        densityGCm3: Float = 1.045f,
        assumedHeightRatio: Float = 0.90f
    ): FishMetrics {
        // 1. Compute Real-World Dimensions (in mm)
        val lengthMm = (lengthPx * depthZMm) / focalLengthPx
        val widthMm = (widthPx * depthZMm) / focalLengthPx
        val heightMm = widthMm * assumedHeightRatio

        // Convert to cm for volume calculation
        val lengthCm = lengthMm / 10.0f
        val widthCm = widthMm / 10.0f
        val heightCm = heightMm / 10.0f

        // 2. Compute Volume (approximating as an ellipsoid: V = (4/3) * pi * (L/2) * (W/2) * (H/2))
        val volumeCm3 = ((4.0 / 3.0) * Math.PI * (lengthCm / 2.0) * (widthCm / 2.0) * (heightCm / 2.0)).toFloat()

        // 3. Compute Ramanujan Girth Perimeter (mm)
        val hAxis = heightMm / 2.0
        val wAxis = widthMm / 2.0
        val hTerm = Math.pow((hAxis - wAxis) / (hAxis + wAxis), 2.0)
        val girthMm = (Math.PI * (hAxis + wAxis) * (1.0 + (3.0 * hTerm) / (10.0 + Math.sqrt(4.0 - 3.0 * hTerm)))).toFloat()

        // 4. Compute Weight (g)
        val weightGrams = volumeCm3 * densityGCm3

        return FishMetrics(
            lengthMm = lengthMm,
            widthMm = widthMm,
            heightMm = heightMm,
            maxGirthMm = girthMm,
            volumeCm3 = volumeCm3,
            estimatedWeightGrams = weightGrams
        )
    }

    /**
     * Keypoint-based metric calculation with Fulton allometric + volumetric mass.
     */
    fun calculateFishMetrics(
        snout: PointF,
        tailTip: PointF,
        dorsal: PointF,
        ventral: PointF,
        pixelsPerMm: Float,
        a: Double = 0.0112,
        b: Double = 3.01,
        bodyAspectRatio: Double = 0.62,
        densityGCm3: Double = 1.045
    ): FishMetrics {
        val dxL = (tailTip.x - snout.x).toDouble()
        val dyL = (tailTip.y - snout.y).toDouble()
        val pixelLength = Math.sqrt(dxL * dxL + dyL * dyL).toFloat()
        val lengthMm = pixelLength / pixelsPerMm
        val lengthCm = lengthMm / 10.0f

        val dxH = (ventral.x - dorsal.x).toDouble()
        val dyH = (ventral.y - dorsal.y).toDouble()
        val pixelHeight = Math.sqrt(dxH * dxH + dyH * dyH).toFloat()
        val heightMm = pixelHeight / pixelsPerMm
        val widthMm = (heightMm * bodyAspectRatio).toFloat()

        val lengthCmD = lengthMm / 10.0
        val widthCmD = widthMm / 10.0
        val heightCmD = heightMm / 10.0

        val volumeCm3 = ((4.0 / 3.0) * Math.PI * (lengthCmD / 2.0) * (widthCmD / 2.0) * (heightCmD / 2.0)).toFloat()

        val hAxis = heightMm / 2.0
        val wAxis = widthMm / 2.0
        val hTerm = Math.pow((hAxis - wAxis) / (hAxis + wAxis), 2.0)
        val girthMm = (Math.PI * (hAxis + wAxis) * (1.0 + (3.0 * hTerm) / (10.0 + Math.sqrt(4.0 - 3.0 * hTerm)))).toFloat()

        // Ensemble Weight: Allometric (65%) + Volumetric Ellipsoid (35%)
        val weightAllometric = (a * Math.pow(lengthCmD, b)).toFloat()
        val weightVolumetric = (volumeCm3 * densityGCm3).toFloat()
        val weightGrams = (0.65f * weightAllometric) + (0.35f * weightVolumetric)

        return FishMetrics(
            lengthMm = lengthMm,
            widthMm = widthMm,
            heightMm = heightMm,
            maxGirthMm = girthMm,
            volumeCm3 = volumeCm3,
            estimatedWeightGrams = weightGrams
        )
    }
}
