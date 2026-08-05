from __future__ import annotations

from typing import Any


REPRESENTATIVE_MARGIN_SAMPLES = 2


class RepresentativeSelectionProcessor:
    def process(
        self,
        samples: list[dict[str, Any]],
        candidate_segments: list[dict[str, Any]],
        anchor_comparison_report: dict[str, Any],
    ) -> dict[str, Any]:
        samples_by_index = {sample["sample_index"]: sample for sample in samples}
        comparisons_by_segment = self._comparisons_by_segment(
            anchor_comparison_report["sample_comparisons"]
        )

        segment_results: list[dict[str, Any]] = []
        for segment in candidate_segments:
            sample_indices = segment["sample_indices"]
            anchor_sample_index = sample_indices[len(sample_indices) // 2]
            margin_applied = segment["sample_count"] > REPRESENTATIVE_MARGIN_SAMPLES * 2
            if margin_applied:
                eligible_indices = sample_indices[
                    REPRESENTATIVE_MARGIN_SAMPLES:-REPRESENTATIVE_MARGIN_SAMPLES
                ]
            else:
                eligible_indices = sample_indices

            tail_bias_applied = len(eligible_indices) > 4
            if tail_bias_applied:
                tail_candidate_indices = eligible_indices[len(eligible_indices) // 2 :]
            else:
                tail_candidate_indices = eligible_indices

            tail_candidate_samples = [
                samples_by_index[index] for index in tail_candidate_indices
            ]
            representative_sample = max(
                tail_candidate_samples,
                key=lambda sample: (
                    sample["laplacian_variance"],
                    -sample["sample_index"],
                ),
            )

            segment_results.append(
                {
                    "segment_index": segment["segment_index"],
                    "anchor_sample_index": anchor_sample_index,
                    "representative_sample_index": representative_sample["sample_index"],
                    "representative_frame_index": representative_sample["frame_index"],
                    "representative_target_timestamp_seconds": representative_sample[
                        "target_timestamp_seconds"
                    ],
                    "representative_analysis_timestamp_seconds": representative_sample[
                        "analysis_timestamp_seconds"
                    ],
                    "representative_laplacian_variance": representative_sample[
                        "laplacian_variance"
                    ],
                    "margin_applied": margin_applied,
                    "eligible_start_sample": eligible_indices[0],
                    "eligible_end_sample": eligible_indices[-1],
                    "eligible_sample_count": len(eligible_indices),
                    "tail_candidate_start_sample": tail_candidate_indices[0],
                    "tail_candidate_end_sample": tail_candidate_indices[-1],
                    "tail_candidate_count": len(tail_candidate_indices),
                    "tail_bias_applied": tail_bias_applied,
                    "sample_count": segment["sample_count"],
                    "laplacian_ranking": self._laplacian_ranking(
                        tail_candidate_samples
                    ),
                    "sample_comparisons": comparisons_by_segment.get(
                        segment["segment_index"], []
                    ),
                }
            )

        return {
            "representative_margin_samples": REPRESENTATIVE_MARGIN_SAMPLES,
            "representative_rule": "Select maximum laplacian_variance within the eligible candidate segment samples; ties use the smallest sample_index.",
            "segment_results": segment_results,
            "sample_comparisons": anchor_comparison_report["sample_comparisons"],
            "summary": {
                "segment_count": len(segment_results),
                "representative_count": len(segment_results),
                "tail_bias_applied_count": sum(
                    1 for segment in segment_results if segment["tail_bias_applied"]
                ),
            },
        }

    def _comparisons_by_segment(
        self,
        comparisons: list[dict[str, Any]],
    ) -> dict[int, list[dict[str, Any]]]:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for comparison in comparisons:
            grouped.setdefault(comparison["segment_index"], []).append(comparison)
        return grouped

    def _laplacian_ranking(
        self,
        samples: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ranked_samples = sorted(
            samples,
            key=lambda sample: (
                -sample["laplacian_variance"],
                sample["sample_index"],
            ),
        )
        return [
            {
                "rank": rank,
                "sample_index": sample["sample_index"],
                "frame_index": sample["frame_index"],
                "laplacian_variance": sample["laplacian_variance"],
            }
            for rank, sample in enumerate(ranked_samples, start=1)
        ]
