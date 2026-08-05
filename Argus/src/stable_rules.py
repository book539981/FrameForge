from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StableRuleResult:
    sample_index: int
    target_grid_index: int
    target_frame_index: int
    target_timestamp_seconds: float
    analysis_timestamp_seconds: float
    frame_index: int
    adjacent_difference_score: float | None
    lookback_difference_score: float | None
    adjacent_pass: bool
    lookback_pass: bool
    is_stable_candidate: bool


class StableCandidateRule:
    def __init__(
        self,
        adjacent_difference_maximum: float,
        long_lookback_difference_maximum: float,
    ) -> None:
        self.adjacent_difference_maximum = adjacent_difference_maximum
        self.long_lookback_difference_maximum = long_lookback_difference_maximum

    def evaluate(self, sample: dict[str, Any]) -> dict[str, Any]:
        adjacent_score = sample["adjacent_difference_score"]
        lookback_score = sample["lookback_difference_score"]

        adjacent_pass = (
            adjacent_score is not None
            and adjacent_score <= self.adjacent_difference_maximum
        )
        lookback_pass = (
            lookback_score is not None
            and lookback_score <= self.long_lookback_difference_maximum
        )

        return asdict(
            StableRuleResult(
                sample_index=sample["sample_index"],
                target_grid_index=sample["target_grid_index"],
                target_frame_index=sample["target_frame_index"],
                target_timestamp_seconds=sample["target_timestamp_seconds"],
                analysis_timestamp_seconds=sample["analysis_timestamp_seconds"],
                frame_index=sample["frame_index"],
                adjacent_difference_score=adjacent_score,
                lookback_difference_score=lookback_score,
                adjacent_pass=adjacent_pass,
                lookback_pass=lookback_pass,
                is_stable_candidate=adjacent_pass and lookback_pass,
            )
        )
