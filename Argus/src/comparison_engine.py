from __future__ import annotations

import cv2
import numpy as np


def normalized_mean_absolute_difference(image_a: np.ndarray, image_b: np.ndarray) -> float:
    return float(np.mean(cv2.absdiff(image_a, image_b))) / 255.0


def changed_pixel_count(image_a: np.ndarray, image_b: np.ndarray) -> int:
    return int(np.count_nonzero(cv2.absdiff(image_a, image_b)))


def changed_area_ratio(image_a: np.ndarray, image_b: np.ndarray) -> float | None:
    total_pixel_count = int(image_a.size)
    if not total_pixel_count:
        return None
    return changed_pixel_count(image_a, image_b) / total_pixel_count


def ssim_score(image_a: np.ndarray, image_b: np.ndarray) -> float:
    a = image_a.astype(np.float64)
    b = image_b.astype(np.float64)

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    mu_a = float(np.mean(a))
    mu_b = float(np.mean(b))
    sigma_a = float(np.mean((a - mu_a) ** 2))
    sigma_b = float(np.mean((b - mu_b) ** 2))
    sigma_ab = float(np.mean((a - mu_a) * (b - mu_b)))

    numerator = (2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a**2 + mu_b**2 + c1) * (sigma_a + sigma_b + c2)
    return float(numerator / denominator) if denominator else 1.0
