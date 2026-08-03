from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .best_frame_selector import BestFrameSelector, CandidateFrame


@dataclass(frozen=True)
class SampledFrame:
    sample_index: int
    frame_index: int
    timestamp_seconds: float
    timestamp_formatted: str
    laplacian_variance: float


@dataclass(frozen=True)
class FrameBufferItem:
    frame_index: int
    timestamp_seconds: float
    frame: np.ndarray


@dataclass(frozen=True)
class StableRelation:
    relation_index: int
    from_sample_index: int
    to_sample_index: int
    from_frame_index: int
    to_frame_index: int
    from_time_seconds: float
    to_time_seconds: float
    adjacent_difference_score: float
    adjacent_pass: bool
    lookback_frame_index: int | None
    lookback_time_seconds: float | None
    lookback_time_gap_seconds: float | None
    lookback_difference_score: float | None
    lookback_pass: bool
    anchor_frame_index: int | None
    anchor_time_seconds: float | None
    anchor_difference_score: float | None
    anchor_pass: bool
    qualification_reason: str
    ssim: float


@dataclass(frozen=True)
class FinalizeResult:
    next_page_number: int
    completed_segment_count: int
    discarded_short_segment_count: int
    output_image_count: int


class StableSequenceState:
    def __init__(self, sequence_id: int) -> None:
        self.sequence_id = sequence_id
        self.candidate_frames: dict[int, dict[str, Any]] = {}
        self.candidate_images: dict[int, np.ndarray] = {}
        self.stable_relations: list[dict[str, Any]] = []
        self.selected_frame: dict[str, Any] | None = None
        self.selected_frame_image: np.ndarray | None = None
        self.boundary_before: tuple[SampledFrame, np.ndarray] | None = None
        self.boundary_after: tuple[SampledFrame, np.ndarray] | None = None
        self.anchor_frame: dict[str, Any] | None = None
        self.anchor_image: np.ndarray | None = None
        self.first_relation_index: int | None = None
        self.last_relation_index: int | None = None
        self.fail_start_time_seconds: float | None = None
        self.maximum_grace_period_seconds = 0.0
        self.grace_period_count = 0
        self.last_qualifying_frame_index: int | None = None
        self.last_qualifying_time_seconds: float | None = None
        self.is_confirmed = False
        self.confirmed_time_seconds: float | None = None
        self.confirmed_relation_index: int | None = None

    @property
    def stable_duration_seconds(self) -> float:
        candidates = sorted(self.candidate_frames.values(), key=lambda item: item["frame_index"])
        if len(candidates) < 2:
            return 0.0
        return float(candidates[-1]["timestamp_seconds"] - candidates[0]["timestamp_seconds"])

    def add_relation(
        self,
        previous_sample: SampledFrame,
        previous_frame: np.ndarray,
        current_sample: SampledFrame,
        current_frame: np.ndarray,
        relation: StableRelation,
        boundary_before: tuple[SampledFrame, np.ndarray] | None,
    ) -> None:
        if not self.candidate_frames:
            self.boundary_before = boundary_before
            self.first_relation_index = relation.relation_index
            self._add_candidate(previous_sample, previous_frame)
            self.anchor_frame = previous_sample.__dict__
            self.anchor_image = previous_frame.copy()
        self._add_candidate(current_sample, current_frame)
        self.stable_relations.append(relation.__dict__)
        self.last_relation_index = relation.relation_index
        self.last_qualifying_frame_index = current_sample.frame_index
        self.last_qualifying_time_seconds = current_sample.timestamp_seconds

    def enter_grace_period(self, fail_start_time_seconds: float) -> None:
        if self.fail_start_time_seconds is None:
            self.fail_start_time_seconds = fail_start_time_seconds
            self.grace_period_count += 1

    def grace_elapsed_seconds(self, current_time_seconds: float) -> float | None:
        if self.fail_start_time_seconds is None:
            return None
        elapsed = float(current_time_seconds - self.fail_start_time_seconds)
        self.maximum_grace_period_seconds = max(self.maximum_grace_period_seconds, elapsed)
        return elapsed

    def recover_from_grace_period(self) -> None:
        self.fail_start_time_seconds = None

    def confirm(self, relation: StableRelation) -> None:
        if not self.is_confirmed:
            self.is_confirmed = True
            self.confirmed_time_seconds = relation.to_time_seconds
            self.confirmed_relation_index = relation.relation_index

    def select_best_frame(self, selector: BestFrameSelector, exclusion_seconds: float) -> None:
        candidates = [
            CandidateFrame(sample=sample, image=self.candidate_images[sample["frame_index"]])
            for sample in self.candidate_frames.values()
        ]
        selected = selector.select(candidates, exclusion_seconds=exclusion_seconds)
        self.selected_frame = selected.sample
        self.selected_frame_image = selected.image.copy()

    def to_segment(
        self,
        segment_index: int,
        page_path: Path,
        preceding_motion_id: int | None,
        motion_end_time_seconds: float | None,
    ) -> dict[str, Any]:
        candidates = sorted(self.candidate_frames.values(), key=lambda item: item["frame_index"])
        if not candidates or self.selected_frame is None:
            raise ValueError("Cannot finalize an empty stable sequence")

        return {
            "segment_index": segment_index,
            "segment_id": segment_index,
            "sequence_id": self.sequence_id,
            "segment_start_time_seconds": candidates[0]["timestamp_seconds"],
            "segment_end_time_seconds": candidates[-1]["timestamp_seconds"],
            "start_time_seconds": candidates[0]["timestamp_seconds"],
            "end_time_seconds": candidates[-1]["timestamp_seconds"],
            "segment_start_time_formatted": candidates[0]["timestamp_formatted"],
            "segment_end_time_formatted": candidates[-1]["timestamp_formatted"],
            "start_sample_index": candidates[0]["sample_index"],
            "end_sample_index": candidates[-1]["sample_index"],
            "start_frame_index": candidates[0]["frame_index"],
            "end_frame_index": candidates[-1]["frame_index"],
            "sample_count": len(candidates),
            "stable_duration_seconds": self.stable_duration_seconds,
            "confirmed_time_seconds": self.confirmed_time_seconds,
            "confirmed_relation_index": self.confirmed_relation_index,
            "preceding_motion_id": preceding_motion_id,
            "motion_end_time_seconds": motion_end_time_seconds,
            "stable_start_time_seconds": candidates[0]["timestamp_seconds"],
            "stable_confirmation_duration": self.stable_duration_seconds,
            "candidate_frames": candidates,
            "stable_relations": self.stable_relations,
            "selected_frame": self.selected_frame,
            "selected_frame_index": self.selected_frame["frame_index"],
            "selected_frame_time_seconds": self.selected_frame["timestamp_seconds"],
            "selected_laplacian": self.selected_frame["laplacian_variance"],
            "selected_laplacian_variance": self.selected_frame["laplacian_variance"],
            "output_page": str(page_path),
        }

    def _add_candidate(self, sample: SampledFrame, frame: np.ndarray) -> None:
        if sample.frame_index not in self.candidate_frames:
            self.candidate_frames[sample.frame_index] = sample.__dict__
            self.candidate_images[sample.frame_index] = frame.copy()

    def to_manifest(
        self,
        status: str,
        termination_reason: str,
        trigger_relation: dict[str, Any] | None,
        previous_sequence_id: int | None,
        gap_from_previous_seconds: float | None,
        preceding_motion_id: int | None = None,
        motion_end_time_seconds: float | None = None,
        rejection_reason: str | None = None,
    ) -> dict[str, Any]:
        candidates = sorted(self.candidate_frames.values(), key=lambda item: item["frame_index"])
        first = candidates[0] if candidates else None
        last = candidates[-1] if candidates else None
        manifest = {
            "sequence_id": self.sequence_id,
            "status": status,
            "start_frame_index": first["frame_index"] if first else None,
            "end_frame_index": last["frame_index"] if last else None,
            "start_time_seconds": first["timestamp_seconds"] if first else None,
            "end_time_seconds": last["timestamp_seconds"] if last else None,
            "duration_seconds": self.stable_duration_seconds,
            "confirmed_time_seconds": self.confirmed_time_seconds,
            "confirmed_relation_index": self.confirmed_relation_index,
            "preceding_motion_id": preceding_motion_id,
            "motion_end_time_seconds": motion_end_time_seconds,
            "stable_start_time_seconds": first["timestamp_seconds"] if first else None,
            "stable_confirmation_duration": self.stable_duration_seconds,
            "first_relation_index": self.first_relation_index,
            "last_relation_index": self.last_relation_index,
            "relation_count": len(self.stable_relations),
            "qualifying_relation_count": len(self.stable_relations),
            "anchor_frame_index": self.anchor_frame["frame_index"] if self.anchor_frame else None,
            "anchor_time_seconds": self.anchor_frame["timestamp_seconds"] if self.anchor_frame else None,
            "grace_period_count": self.grace_period_count,
            "maximum_grace_period_seconds": self.maximum_grace_period_seconds,
            "last_qualifying_frame_index": self.last_qualifying_frame_index,
            "last_qualifying_time_seconds": self.last_qualifying_time_seconds,
            "finalized_after_fail_tolerance": termination_reason == "fail_tolerance_timeout",
            "termination_reason": termination_reason,
            "trigger_relation": trigger_relation,
            "previous_sequence_id": previous_sequence_id,
            "next_sequence_id": None,
            "gap_from_previous_seconds": gap_from_previous_seconds,
        }
        if rejection_reason is not None:
            manifest["rejection_reason"] = rejection_reason
        return manifest

    def debug_frames(self) -> dict[str, np.ndarray]:
        ordered = sorted(self.candidate_frames.values(), key=lambda item: item["frame_index"])
        frames: dict[str, np.ndarray] = {}
        if ordered:
            first = ordered[0]
            middle = ordered[len(ordered) // 2]
            last = ordered[-1]
            frames["first"] = self.candidate_images[first["frame_index"]]
            frames["middle"] = self.candidate_images[middle["frame_index"]]
            frames["last"] = self.candidate_images[last["frame_index"]]
        if self.boundary_before is not None:
            frames["before"] = self.boundary_before[1]
        if self.boundary_after is not None:
            frames["after"] = self.boundary_after[1]
        if self.anchor_image is not None:
            frames["anchor"] = self.anchor_image
        return frames
