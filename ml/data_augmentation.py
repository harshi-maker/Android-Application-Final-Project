"""
Synthetic Data Augmentation Pipeline for Fish Catch Identification.
Simulates wet specular reflections, water caustics, and deck lighting.
"""

import cv2
import numpy as np
import albumentations as A

def get_fish_augmentation_pipeline(img_size=640):
    return A.Compose([
        A.Resize(img_size, img_size),
        A.HorizontalFlip(p=0.5),
        A.RandomRotate90(p=0.5),
        A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=20, p=0.7, border_mode=cv2.BORDER_CONSTANT),
        # Wet specular glare / sunlight reflections
        A.OneOf([
            A.RandomSunFlare(flare_roi=(0, 0, 1, 0.5), angle_lower=0.5, p=0.6),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.7),
        ], p=0.8),
        # Water/Underwater color shift and caustics simulation
        A.OneOf([
            A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.3, hue=0.1, p=0.6),
            A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=20, val_shift_limit=15, p=0.5),
        ], p=0.7),
        # Low light / deck noise
        A.OneOf([
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.5),
            A.MotionBlur(blur_limit=5, p=0.4),
        ], p=0.5),
    ], keypoint_params=A.KeypointParams(format='xy', remove_invisible=False))

if __name__ == "__main__":
    print("Fish Data Augmentation Pipeline initialized successfully.")
