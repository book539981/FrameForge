from __future__ import annotations

from typing import Any

import numpy as np

from .comparison_engine import ComparisonEngine


class AnchorComparisonProcessor:
    def __init__(self, comparison_engine: ComparisonEngine) -> None:
        self.comparison_engine = comparison_engine

    def process(
        self,
        samples: list[dict[str, Any]],
        sample_grays: dict[int, np.ndarray],
        candidate_segments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        samples_by_index = {sample["sample_index"]: sample for sample in samples}
        rows: list[dict[str, Any]] = []
        segment_summaries: list[dict[str, Any]] = []

        for segment in candidate_segments:
            sample_indices = segment["sample_indices"]
            anchor_sample_index = sample_indices[len(sample_indices) // 2]
            anchor_gray = sample_grays[anchor_sample_index]

            segment_rows: list[dict[str, Any]] = []
            for sample_index in sample_indices:
                sample = samples_by_index[sample_index]
                comparison = self.comparison_engine.compare(
                    anchor_gray,
                    sample_grays[sample_index],
                )
                row = {
                    "segment_index": segment["segment_index"],
                    "sample_index": sample["sample_index"],
                    "frame_index": sample["frame_index"],
                    "analysis_timestamp_seconds": sample["analysis_timestamp_seconds"],
                    "target_timestamp_seconds": sample["target_timestamp_seconds"],
                    "laplacian_variance": sample["laplacian_variance"],
                    "anchor_sample_index": anchor_sample_index,
                    "anchor_difference_score": comparison["difference_score"],
                    "anchor_ssim_score": comparison["ssim_score"],
                }
                rows.append(row)
                segment_rows.append(row)

            segment_summaries.append(
                {
                    "segment_index": segment["segment_index"],
                    "anchor_sample_index": anchor_sample_index,
                    "sample_count": segment["sample_count"],
                    "difference_statistics": summarize(
                        row["anchor_difference_score"] for row in segment_rows
                    ),
                    "ssim_statistics": summarize(
                        row["anchor_ssim_score"] for row in segment_rows
                    ),
                }
            )

        return {
            "anchor_definition": "Candidate Segment middle sample; even-length segments use the later middle sample.",
            "sample_comparisons": rows,
            "segment_summaries": segment_summaries,
            "summary": {
                "segment_count": len(candidate_segments),
                "comparison_sample_count": len(rows),
                "difference_statistics": summarize(
                    row["anchor_difference_score"] for row in rows
                ),
                "ssim_statistics": summarize(row["anchor_ssim_score"] for row in rows),
            },
            "histograms": {
                "difference": difference_histogram(
                    row["anchor_difference_score"] for row in rows
                ),
                "ssim": ssim_histogram(row["anchor_ssim_score"] for row in rows),
            },
        }


def summarize(values: Any) -> dict[str, float | None]:
    numbers = [float(value) for value in values]
    if not numbers:
        return {"minimum": None, "maximum": None, "average": None}
    return {
        "minimum": min(numbers),
        "maximum": max(numbers),
        "average": sum(numbers) / len(numbers),
    }


def difference_histogram(values: Any) -> list[dict[str, Any]]:
    bins = [
        ("0.000~0.001", 0.0, 0.001),
        ("0.001~0.003", 0.001, 0.003),
        ("0.003~0.010", 0.003, 0.010),
        ("0.010~0.030", 0.010, 0.030),
        ("0.030~0.100", 0.030, 0.100),
        ("0.100+", 0.100, None),
    ]
    return histogram(values, bins)


def ssim_histogram(values: Any) -> list[dict[str, Any]]:
    bins = [
        ("0.000~0.500", 0.0, 0.500),
        ("0.500~0.800", 0.500, 0.800),
        ("0.800~0.900", 0.800, 0.900),
        ("0.900~0.950", 0.900, 0.950),
        ("0.950~0.990", 0.950, 0.990),
        ("0.990~1.000", 0.990, None),
    ]
    return histogram(values, bins)


def histogram(values: Any, bins: list[tuple[str, float, float | None]]) -> list[dict[str, Any]]:
    rows = [{"range": label, "count": 0} for label, _, _ in bins]
    for value in values:
        number = float(value)
        for row, (_, lower, upper) in zip(rows, bins):
            if number >= lower and (upper is None or number < upper):
                row["count"] += 1
                break
    return rows
