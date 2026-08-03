from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CandidateFrame:
    sample: dict[str, Any]
    image: np.ndarray


class BestFrameSelector:
    def select(
        self,
        candidates: list[CandidateFrame],
        exclusion_seconds: float = 0.0,
    ) -> CandidateFrame:
        if not candidates:
            raise ValueError("Cannot select a best frame from an empty candidate list")
        start_time = min(candidate.sample["timestamp_seconds"] for candidate in candidates)
        selection_start_time = start_time + exclusion_seconds
        eligible_candidates = [
            candidate
            for candidate in candidates
            if candidate.sample["timestamp_seconds"] >= selection_start_time
        ]
        if not eligible_candidates:
            eligible_candidates = candidates
        return max(eligible_candidates, key=lambda candidate: candidate.sample["laplacian_variance"])
