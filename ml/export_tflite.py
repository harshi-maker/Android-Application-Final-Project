"""
Export and INT8 Quantization Script for edge deployment to TensorFlow Lite.
"""

import os
import tensorflow as tf
import numpy as np

def representative_dataset():
    # Provide sample calibration data (e.g. 100 images normalized to [0, 1])
    for _ in range(100):
        data = np.random.rand(1, 224, 224, 3).astype(np.float32)
        yield [data]

def convert_to_tflite_int8(saved_model_dir: str, output_path: str):
    """
    Converts a SavedModel / Keras model to full integer INT8 TFLite model.
    """
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    
    # Ensure full integer quantization for NNAPI / Hexagon NPU execution
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.uint8
    converter.inference_output_type = tf.uint8
    
    tflite_quant_model = converter.convert()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_quant_model)
        
    print(f"Quantized model saved to {output_path} (Size: {len(tflite_quant_model)/1024:.2f} KB)")

if __name__ == "__main__":
    print("TFLite INT8 Export Script Ready.")
