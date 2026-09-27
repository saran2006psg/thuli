"""
app/retrieval/encoder.py
────────────────────────
Vision encoder — loads pretrained CLIP vision model and extracts
L2-normalized embedding vectors for single images and image batches.
"""

import os
from pathlib import Path
from typing import List, Union

# Prevent transformers from attempting to import TensorFlow
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
from PIL import Image
import torch
from transformers import CLIPModel, CLIPProcessor

from app.config import ENCODER_MODEL, EMBEDDING_DIM


class JewelleryEncoder:
    """
    Pretrained vision encoder wrapper for jewellery feature extraction.
    Generates unit-normalized (L2 norm = 1.0) embedding vectors.
    """

    def __init__(
        self,
        model_name: str = ENCODER_MODEL,
        device: str = None,
    ):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model_name = model_name
        try:
            self.processor = CLIPProcessor.from_pretrained(model_name, local_files_only=True, use_fast=True)
            self.model = CLIPModel.from_pretrained(model_name, local_files_only=True, low_cpu_mem_usage=False).to(self.device)
        except Exception:
            try:
                self.processor = CLIPProcessor.from_pretrained(model_name, use_fast=True)
                self.model = CLIPModel.from_pretrained(model_name, low_cpu_mem_usage=False).to(self.device)
            except Exception:
                self.processor = CLIPProcessor.from_pretrained(model_name)
                self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

        self.embedding_dim = self.model.config.projection_dim if hasattr(self.model.config, "projection_dim") else EMBEDDING_DIM

    def _load_pil(self, img_input: Union[Image.Image, str, Path]) -> Image.Image:
        """Helper to ensure input is an RGB PIL Image."""
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
            return img
        elif isinstance(img_input, Image.Image):
            if img_input.mode != "RGB":
                return img_input.convert("RGB")
            return img_input
        else:
            raise TypeError(f"Unsupported image type: {type(img_input)}")

    @torch.no_grad()
    def encode_image(self, image: Union[Image.Image, str, Path]) -> np.ndarray:
        """
        Extract L2-normalized embedding vector for a single image.

        Args:
            image: PIL Image, filepath string, or Path.

        Returns:
            1D numpy array of shape (embedding_dim,), dtype float32, L2 norm = 1.0.
        """
        pil_img = self._load_pil(image)
        inputs = self.processor(images=pil_img, return_tensors="pt").to(self.device)
        image_features = self.model.get_image_features(**inputs)

        # Convert to float numpy
        features = image_features.cpu().numpy().astype(np.float32)[0]

        # L2-normalization
        norm = np.linalg.norm(features)
        if norm > 1e-12:
            features = features / norm

        return features

    @torch.no_grad()
    def encode_batch(self, images: List[Union[Image.Image, str, Path]]) -> np.ndarray:
        """
        Extract L2-normalized embedding vectors for a batch of images.

        Args:
            images: List of PIL Images, filepath strings, or Paths.

        Returns:
            2D numpy array of shape (batch_size, embedding_dim), dtype float32,
            each row has L2 norm = 1.0.
        """
        if not images:
            return np.empty((0, self.embedding_dim), dtype=np.float32)

        pil_images = [self._load_pil(img) for img in images]
        inputs = self.processor(images=pil_images, return_tensors="pt", padding=True).to(self.device)
        image_features = self.model.get_image_features(**inputs)

        features = image_features.cpu().numpy().astype(np.float32)

        # L2-normalization per row
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-12, None)
        features = features / norms

        return features
