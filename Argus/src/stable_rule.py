from __future__ import annotations

from typing import Any

from .stable_state import StableRelation


class StableRule:
    def __init__(self, config: dict[str, Any]) -> None:
        stable_config = config.get("stable_frame", {})
        self.ssim_minimum = float(stable_config.get("ssim_minimum", 0.995))
        self.adjacent_difference_maximum = float(
            stable_config.get("adjacent_difference_maximum", stable_config.get("difference_score_maximum", 0.005))
        )
        self.lookback_seconds = float(stable_config.get("lookback_seconds", 0.5))
        self.lookback_difference_maximum = float(
            stable_config.get("lookback_difference_maximum", self.adjacent_difference_maximum)
        )
        self.anchor_difference_maximum = float(
            stable_config.get("anchor_difference_maximum", self.lookback_difference_maximum)
        )
        self.motion_difference_threshold = float(
            stable_config.get("motion_difference_threshold", max(self.adjacent_difference_maximum, self.lookback_difference_maximum) * 2)
        )
        self.motion_minimum_duration_seconds = float(stable_config.get("motion_minimum_duration_seconds", 0.2))
        self.minimum_stable_duration_seconds = float(
            stable_config.get("minimum_stable_duration_seconds", 0.5)
        )
        self.fail_tolerance_seconds = float(stable_config.get("fail_tolerance_seconds", 0.0))
        if self.lookback_seconds <= 0:
            raise ValueError("stable_frame.lookback_seconds must be greater than zero")
        if self.minimum_stable_duration_seconds < 0:
            raise ValueError("stable_frame.minimum_stable_duration_seconds must be zero or greater")
        if self.motion_minimum_duration_seconds < 0:
            raise ValueError("stable_frame.motion_minimum_duration_seconds must be zero or greater")
        if self.fail_tolerance_seconds < 0:
            raise ValueError("stable_frame.fail_tolerance_seconds must be zero or greater")

        self.decision_metrics = list(stable_config.get("decision_metrics", ["adjacent_difference_score"]))
        self.diagnostic_metrics = list(stable_config.get("diagnostic_metrics", ["ssim"]))

    def is_qualifying_relation(self, relation: StableRelation) -> bool:
        checks = {
            "adjacent_difference_score": relation.adjacent_pass,
            "lookback_difference_score": relation.lookback_pass,
            "anchor_difference_score": relation.anchor_pass,
            "ssim": relation.ssim >= self.ssim_minimum,
        }
        return all(checks[metric] for metric in self.decision_metrics)

    def is_start_relation(self, relation: StableRelation) -> bool:
        return relation.adjacent_pass and relation.lookback_pass

    def is_sequence_relation(self, relation: StableRelation) -> bool:
        return self.is_qualifying_relation(relation)

    def is_complete_sequence(self, stable_duration_seconds: float) -> bool:
        return stable_duration_seconds >= self.minimum_stable_duration_seconds

    def motion_difference_score(self, relation: StableRelation) -> float:
        scores = [relation.adjacent_difference_score]
        if relation.lookback_difference_score is not None:
            scores.append(relation.lookback_difference_score)
        return max(scores)

    def is_motion_relation(self, relation: StableRelation) -> bool:
        return self.motion_difference_score(relation) >= self.motion_difference_threshold
