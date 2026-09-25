"""
experiments/experiment_01/cropper.py
───────────────────────────────────
Saliency and contour-based object cropper for Phase 8 Experiment 01.
Detects the primary foreground jewellery object to eliminate background clutter,
extraneous distance framing, and surface noise before CLIP embedding.
"""

from typing import Tuple, Union
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


class SaliencyObjectCropper:
    """
    Automated jewellery/foreground object cropper using Spectral Residual Saliency
    and Otsu thresholding with adaptive margin padding.
    """

    def __init__(self, margin_ratio: float = 0.15, min_area_ratio: float = 0.04, max_area_ratio: float = 0.95):
        """
        Args:
            margin_ratio: Context padding around detected bounding box (15%).
            min_area_ratio: Minimum fraction of image area for a valid detection.
            max_area_ratio: Maximum fraction; if detected box covers entire image, keep original.
        """
        self.margin_ratio = margin_ratio
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.saliency = cv2.saliency.StaticSaliencySpectralResidual_create()

    def crop(self, image_input: Union[str, Path, Image.Image]) -> Tuple[Image.Image, bool]:
        """
        Crop the primary salient object from an image.

        Args:
            image_input: File path or PIL Image.

        Returns:
            (cropped_pil_image, was_cropped_boolean)
        """
        if isinstance(image_input, (str, Path)):
            bgr = cv2.imread(str(image_input))
            if bgr is None:
                raise ValueError(f"Could not load image from {image_input}")
        elif isinstance(image_input, Image.Image):
            rgb = np.array(image_input.convert("RGB"))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")

        H, W = bgr.shape[:2]
        total_area = H * W

        # Compute Spectral Residual Saliency map
        success, saliency_map = self.saliency.computeSaliency(bgr)
        if not success:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), False

        # Otsu thresholding on saliency map
        thresh = (saliency_map * 255).astype("uint8")
        _, binary = cv2.threshold(thresh, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Morphological opening to reduce noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Find largest salient contour
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), False

        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        box_area = w * h

        area_frac = box_area / total_area
        # Only crop if region is meaningful (not entire image, not tiny speck)
        if area_frac < self.min_area_ratio or area_frac > self.max_area_ratio:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), False

        # Add context margin
        pad_x = int(w * self.margin_ratio)
        pad_y = int(h * self.margin_ratio)

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(W, x + w + pad_x)
        y2 = min(H, y + h + pad_y)

        cropped_bgr = bgr[y1:y2, x1:x2]
        if cropped_bgr.size == 0 or cropped_bgr.shape[0] < 20 or cropped_bgr.shape[1] < 20:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), False

        cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(cropped_rgb), True
