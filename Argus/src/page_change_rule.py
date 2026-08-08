from __future__ import annotations

from typing import Any


class PageChangeRule:
    def __init__(self, page_change_config: dict[str, Any]) -> None:
        self.changed_area_ratio_threshold = required_float(
            page_change_config,
            "changed_area_ratio_threshold",
        )
        self.ssim_threshold = required_float(page_change_config, "ssim_threshold")
        self.ecc_score_minimum = required_float(
            page_change_config,
            "ecc_score_minimum",
        )
        self.alignment_translation_maximum_pixels = required_float(
            page_change_config,
            "alignment_translation_maximum_pixels",
        )

    def is_page_change(self, frame: dict[str, Any]) -> bool:
        changed_area_ratio = frame["changed_area_ratio"]
        if (
            changed_area_ratio is None
            or changed_area_ratio <= self.changed_area_ratio_threshold
        ):
            return False

        ssim = frame["ssim"]
        if ssim is not None and ssim < self.ssim_threshold:
            return True

        return not self._has_same_page_alignment(frame)

    def summary(self) -> dict[str, Any]:
        return {
            "page_change_condition": "Decision Tree: changed_area_ratio <= changed_area_ratio_threshold => Same Page; otherwise ssim < ssim_threshold => Page Change; otherwise ECC Translation decides Same Page only when ecc_converged is true, ecc_score >= ecc_score_minimum, abs(ecc_dx) <= alignment_translation_maximum_pixels, and abs(ecc_dy) <= alignment_translation_maximum_pixels.",
            "changed_area_ratio_threshold": self.changed_area_ratio_threshold,
            "ssim_threshold": self.ssim_threshold,
            "ecc_score_minimum": self.ecc_score_minimum,
            "alignment_translation_maximum_pixels": self.alignment_translation_maximum_pixels,
        }

    def _has_same_page_alignment(self, frame: dict[str, Any]) -> bool:
        return (
            frame["ecc_converged"] is True
            and frame["ecc_score"] is not None
            and frame["ecc_score"] >= self.ecc_score_minimum
            and frame["ecc_dx"] is not None
            and abs(frame["ecc_dx"]) <= self.alignment_translation_maximum_pixels
            and frame["ecc_dy"] is not None
            and abs(frame["ecc_dy"]) <= self.alignment_translation_maximum_pixels
        )


def required_float(config: dict[str, Any], key: str) -> float:
    value = config.get(key)
    if value is None:
        raise ValueError(f"page_change.{key} is required.")
    return float(value)
