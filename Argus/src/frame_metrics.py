from __future__ import annotations

import cv2
import numpy as np


def difference_score(from_gray: np.ndarray, to_gray: np.ndarray) -> float:
    return float(np.mean(cv2.absdiff(from_gray, to_gray)) / 255.0)


def ssim(from_gray: np.ndarray, to_gray: np.ndarray) -> float:
    from_array = from_gray.astype(np.float64)
    to_array = to_gray.astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    mu_x = float(np.mean(from_array))
    mu_y = float(np.mean(to_array))
    sigma_x = float(np.var(from_array))
    sigma_y = float(np.var(to_array))
    covariance = float(np.mean((from_array - mu_x) * (to_array - mu_y)))

    numerator = (2 * mu_x * mu_y + c1) * (2 * covariance + c2)
    denominator = (mu_x**2 + mu_y**2 + c1) * (sigma_x + sigma_y + c2)
    return float(numerator / denominator) if denominator else 1.0
