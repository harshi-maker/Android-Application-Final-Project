"""
Multi-task model training script for Fish Detection, Freshness Classification, and Keypoint Regression.
"""

import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

class MultiTaskFishNet(nn.Module):
    def __init__(self, num_species=20, num_keypoints=6):
        super(MultiTaskFishNet, self).__init__()
        
        # Lightweight MobileNetV3 backbone
        weights = MobileNet_V3_Small_Weights.DEFAULT
        backbone = mobilenet_v3_small(weights=weights)
        self.features = backbone.features
        self.avgpool = backbone.avgpool
        
        feature_dim = 576  # MobileNetV3-Small pooled feature size
        
        # Head 1: Species Classification
        self.species_head = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.Hardswish(),
            nn.Dropout(0.2),
            nn.Linear(256, num_species)
        )
        
        # Head 2: Freshness / Quality Scoring (0 = Spoilage, 1 = Prime Fresh)
        self.freshness_head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.Hardswish(),
            nn.Dropout(0.2),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
        
        # Head 3: Normalized Keypoint Coordinates (Snout, Eye, Dorsal, Ventral, Tail Base, Tail Tip)
        self.keypoint_head = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.Hardswish(),
            nn.Linear(256, num_keypoints * 2), # (x, y) pairs in [0, 1]
            nn.Sigmoid()
        )

    def forward(self, x):
        feat = self.features(x)
        feat = self.avgpool(feat)
        feat = torch.flatten(feat, 1)
        
        species_logits = self.species_head(feat)
        freshness_score = self.freshness_head(feat)
        keypoints = self.keypoint_head(feat)
        
        return {
            "species": species_logits,
            "freshness": freshness_score,
            "keypoints": keypoints
        }

if __name__ == "__main__":
    model = MultiTaskFishNet()
    dummy_input = torch.randn(1, 3, 224, 224)
    out = model(dummy_input)
    print("MultiTaskFishNet initialized successfully.")
    print("Species shape:", out["species"].shape)
    print("Freshness shape:", out["freshness"].shape)
    print("Keypoints shape:", out["keypoints"].shape)
