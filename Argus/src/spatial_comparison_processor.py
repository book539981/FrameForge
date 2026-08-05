from __future__ import annotations

from typing import Any

import numpy as np

from .comparison_engine import ComparisonEngine


class SpatialComparisonProcessor:
    def __init__(self, comparison_engine: ComparisonEngine) -> None:
        self.comparison_engine = comparison_engine

    def process(
        self,
        sample_grays: dict[int, np.ndarray],
        candidate_segments: list[dict[str, Any]],
        representative_report: dict[str, Any],
    ) -> dict[str, Any]:
        representative_by_segment = {
            segment["segment_index"]: segment
            for segment in representative_report["segment_results"]
        }
        sample_comparisons: list[dict[str, Any]] = []
        representative_comparisons: list[dict[str, Any]] = []

        for segment in candidate_segments:
            sample_indices = segment["sample_indices"]
            anchor_sample_index = sample_indices[len(sample_indices) // 2]
            anchor_gray = sample_grays[anchor_sample_index]
            representative = representative_by_segment[segment["segment_index"]]

            for sample_index in sample_indices:
                comparison = self._compare_regions(anchor_gray, sample_grays[sample_index])
                row = {
                    "segment_index": segment["segment_index"],
                    "sample_index": sample_index,
                    "anchor_sample_index": anchor_sample_index,
                    "comparison": comparison,
                    "whole_difference": comparison["whole"]["difference"],
                    "left_difference": comparison["left"]["difference"],
                    "center_difference": comparison["center"]["difference"],
                    "right_difference": comparison["right"]["difference"],
                    "whole_ssim": comparison["whole"]["ssim"],
                    "left_ssim": comparison["left"]["ssim"],
                    "center_ssim": comparison["center"]["ssim"],
                    "right_ssim": comparison["right"]["ssim"],
                }
                sample_comparisons.append(row)

                if sample_index == representative["representative_sample_index"]:
                    representative_comparisons.append(
                        {
                            "segment_index": segment["segment_index"],
                            "representative_sample_index": sample_index,
                            "representative_frame_index": representative[
                                "representative_frame_index"
                            ],
                            "anchor_sample_index": anchor_sample_index,
                            "comparison": comparison,
                        }
                    )

        return {
            "roi_definition": {
                "left": "x from 0 to width/3",
                "center": "x from width/3 to 2*width/3",
                "right": "x from 2*width/3 to width",
            },
            "sample_comparisons": sample_comparisons,
            "representative_comparisons": representative_comparisons,
            "summary": {
                "sample_comparison_count": len(sample_comparisons),
                "representative_comparison_count": len(representative_comparisons),
            },
        }

    def _compare_regions(
        self,
        anchor_gray: np.ndarray,
        sample_gray: np.ndarray,
    ) -> dict[str, dict[str, float]]:
        anchor_regions = split_regions(anchor_gray)
        sample_regions = split_regions(sample_gray)
        comparisons: dict[str, dict[str, float]] = {}
        for region_name in ("whole", "left", "center", "right"):
            result = self.comparison_engine.compare(
                anchor_regions[region_name],
                sample_regions[region_name],
            )
            comparisons[region_name] = {
                "difference": result["difference_score"],
                "ssim": result["ssim_score"],
            }
        return comparisons


def split_regions(gray: np.ndarray) -> dict[str, np.ndarray]:
    width = gray.shape[1]
    first_cut = width // 3
    second_cut = (width * 2) // 3
    return {
        "whole": gray,
        "left": gray[:, :first_cut],
        "center": gray[:, first_cut:second_cut],
        "right": gray[:, second_cut:],
    }
