from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def ecc_translation_facts(
    previous_gray: np.ndarray,
    current_gray: np.ndarray,
) -> dict[str, Any]:
    warp_matrix = np.eye(2, 3, dtype=np.float32)
    try:
        score, warp_matrix = cv2.findTransformECC(
            previous_gray.astype(np.float32),
            current_gray.astype(np.float32),
            warp_matrix,
            cv2.MOTION_TRANSLATION,
        )
    except cv2.error as exc:
        return {
            "ecc_converged": False,
            "ecc_score": None,
            "ecc_dx": None,
            "ecc_dy": None,
            "ecc_error": str(exc),
        }

    if not np.isfinite(score) or not np.all(np.isfinite(warp_matrix)):
        return {
            "ecc_converged": False,
            "ecc_score": finite_float_or_none(score),
            "ecc_dx": finite_float_or_none(warp_matrix[0, 2]),
            "ecc_dy": finite_float_or_none(warp_matrix[1, 2]),
            "ecc_error": "ECC returned non-finite score or warp matrix.",
        }

    return {
        "ecc_converged": True,
        "ecc_score": finite_float_or_none(score),
        "ecc_dx": finite_float_or_none(warp_matrix[0, 2]),
        "ecc_dy": finite_float_or_none(warp_matrix[1, 2]),
        "ecc_error": None,
    }


def finite_float_or_none(value: Any) -> float | None:
    number = float(value)
    if not np.isfinite(number):
        return None
    return number
