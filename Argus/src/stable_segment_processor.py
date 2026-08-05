from __future__ import annotations

from typing import Any

from .stable_rules import StableCandidateRule


class StableSegmentProcessor:
    def __init__(self, rule: StableCandidateRule) -> None:
        self.rule = rule

    def process(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        sample_results: list[dict[str, Any]] = []
        segments: list[dict[str, Any]] = []
        current_segment_samples: list[dict[str, Any]] | None = None

        for sample in samples:
            rule_result = self.rule.evaluate(sample)
            sample_results.append(rule_result)

            if rule_result["is_stable_candidate"]:
                if current_segment_samples is None:
                    current_segment_samples = []
                current_segment_samples.append(rule_result)
            elif current_segment_samples is not None:
                segments.append(self._build_segment(len(segments), current_segment_samples))
                current_segment_samples = None

        if current_segment_samples is not None:
            segments.append(self._build_segment(len(segments), current_segment_samples))

        return {
            "sample_rule_results": sample_results,
            "candidate_segments": segments,
            "summary": {
                "sample_count": len(sample_results),
                "adjacent_pass_count": sum(
                    1 for result in sample_results if result["adjacent_pass"]
                ),
                "lookback_pass_count": sum(
                    1 for result in sample_results if result["lookback_pass"]
                ),
                "stable_candidate_sample_count": sum(
                    1 for result in sample_results if result["is_stable_candidate"]
                ),
                "candidate_segment_count": len(segments),
            },
        }

    def _build_segment(
        self,
        segment_index: int,
        segment_samples: list[dict[str, Any]],
    ) -> dict[str, Any]:
        first_sample = segment_samples[0]
        last_sample = segment_samples[-1]
        return {
            "segment_index": segment_index,
            "start_sample_index": first_sample["sample_index"],
            "end_sample_index": last_sample["sample_index"],
            "start_target_timestamp_seconds": first_sample["target_timestamp_seconds"],
            "end_target_timestamp_seconds": last_sample["target_timestamp_seconds"],
            "start_analysis_timestamp_seconds": first_sample["analysis_timestamp_seconds"],
            "end_analysis_timestamp_seconds": last_sample["analysis_timestamp_seconds"],
            "sample_count": len(segment_samples),
            "sample_indices": [sample["sample_index"] for sample in segment_samples],
            "target_duration_seconds": round(
                last_sample["target_timestamp_seconds"]
                - first_sample["target_timestamp_seconds"],
                6,
            ),
            "analysis_duration_seconds": round(
                last_sample["analysis_timestamp_seconds"]
                - first_sample["analysis_timestamp_seconds"],
                6,
            ),
            "sample_count_matches_sample_indices": len(segment_samples)
            == len([sample["sample_index"] for sample in segment_samples]),
            "sample_count_matches_index_span": len(segment_samples)
            == last_sample["sample_index"] - first_sample["sample_index"] + 1,
        }
