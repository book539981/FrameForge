from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .best_frame_selector import BestFrameSelector
from .frame_metrics import difference_score, ssim
from .frame_source import SequentialFrameSource
from .json_utils import scrub_json
from .stable_rule import StableRule
from .stable_state import FinalizeResult, FrameBufferItem, SampledFrame, StableRelation, StableSequenceState
from .video_reader import format_duration, read_metadata

class StablePageProcessor:
    def __init__(self, config: dict[str, Any], argus_root: Path) -> None:
        self.config = config
        self.argus_root = argus_root
        self.frame_interval = int(config["sampling"].get("frame_interval", 1))
        if self.frame_interval < 1:
            raise ValueError("sampling.frame_interval must be at least one")

        self.rule = StableRule(config)
        self.best_frame_selector = BestFrameSelector()
        stable_config = config.get("stable_frame", {})
        self.best_frame_exclusion_seconds = float(
            stable_config.get("best_frame_exclusion_seconds", 0.8)
        )
        if self.best_frame_exclusion_seconds < 0:
            raise ValueError("stable_frame.best_frame_exclusion_seconds must be zero or greater")
        self.pages_dir = argus_root / config["output"]["pages_directory"]
        self.debug_segments_dir = argus_root / config["output"]["debug_directory"] / "segments"

    def process(self, video_path: Path) -> dict[str, Any]:
        metadata = read_metadata(video_path)
        frame_interval = self.frame_interval
        expected_sampled_frames = (
            (metadata.total_frames + frame_interval - 1) // frame_interval
            if metadata.total_frames > 0
            else None
        )
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.debug_segments_dir.mkdir(parents=True, exist_ok=True)
        self._clear_previous_pages()
        self._clear_previous_debug_segments()

        stable_segments: list[dict[str, Any]] = []
        frame_source = SequentialFrameSource(
            video_path=video_path,
            fps=metadata.fps,
            expected_total_frames=metadata.total_frames,
        )

        previous: tuple[SampledFrame, np.ndarray] | None = None
        previous_previous: tuple[SampledFrame, np.ndarray] | None = None
        current_sequence: StableSequenceState | None = None
        frame_buffer: list[FrameBufferItem] = []
        page_number = 1
        next_sequence_id = 1
        processed_samples: list[SampledFrame] = []
        relation_diagnostics: list[dict[str, Any]] = []
        decoded_frame_count = 0
        last_decoded_frame_index: int | None = None
        midstream_decode_failure_count = 0
        relation_count = 0
        qualifying_relation_count = 0
        non_qualifying_relation_count = 0
        candidate_sequence_count = 0
        completed_segment_count = 0
        discarded_short_segment_count = 0
        output_image_count = 0
        rejected_sequences: list[dict[str, Any]] = []
        image_output_failures: list[dict[str, Any]] = []
        segment_manifest: list[dict[str, Any]] = []
        state_machine_trace: list[dict[str, Any]] = []
        grace_period_enter_count = 0
        grace_period_recovered_count = 0
        grace_period_timeout_count = 0
        processor_state = "initial_search"
        motion_candidate: dict[str, Any] | None = None
        active_motion: dict[str, Any] | None = None
        motion_events: list[dict[str, Any]] = []
        next_motion_id = 1
        preceding_motion_id: int | None = None
        motion_end_time_seconds: float | None = None
        stable_plateau_count = 0
        accepted_after_motion_count = 0
        initial_page_count = 0
        motion_reentry_count = 0
        plateau_cancelled_by_motion_count = 0
        final_flush_performed = False
        stopped_reason = "completed"

        sample_index = 0
        for decoded_frame in frame_source:
                frame = decoded_frame.frame
                frame_index = decoded_frame.frame_index
                timestamp = decoded_frame.timestamp_seconds
                lookback_frame = self._find_lookback_frame(
                    frame_buffer=frame_buffer,
                    target_time_seconds=timestamp - self.rule.lookback_seconds,
                )
                frame_buffer.append(
                    FrameBufferItem(
                        frame_index=frame_index,
                        timestamp_seconds=timestamp,
                        frame=frame.copy(),
                    )
                )
                self._trim_frame_buffer(frame_buffer, timestamp)
                decoded_frame_count += 1
                last_decoded_frame_index = frame_index

                if frame_index % frame_interval != 0:
                    continue

                sampled = self._sampled_frame(frame, sample_index, frame_index, metadata.fps)
                processed_samples.append(sampled)
                sample_index += 1
                if previous is None:
                    previous = (sampled, frame)
                    continue

                relation = self._relation(
                    relation_index=relation_count,
                    previous_sample=previous[0],
                    previous_frame=previous[1],
                    current_sample=sampled,
                    current_frame=frame,
                    lookback_frame=lookback_frame,
                    current_sequence=current_sequence,
                )
                state_before = processor_state
                relation_count += 1
                motion_signal = self.rule.is_motion_relation(relation)
                motion_difference = self.rule.motion_difference_score(relation)
                relation_is_qualifying = False
                if processor_state in ("initial_search", "searching_stable_plateau"):
                    relation_is_qualifying = self.rule.is_start_relation(relation)
                elif processor_state == "building_stable_plateau" and current_sequence is not None:
                    relation_is_qualifying = self.rule.is_sequence_relation(relation)
                diagnostic = self._relation_diagnostic(relation, relation_is_qualifying)
                diagnostic["motion_difference_score"] = motion_difference
                diagnostic["motion_signal"] = motion_signal

                action = "none"
                grace_elapsed_for_diagnostic: float | None = None
                active_sequence_id = current_sequence.sequence_id if current_sequence else None
                if processor_state == "waiting_motion":
                    motion_candidate = self._update_motion_candidate(
                        motion_candidate,
                        diagnostic,
                        motion_difference,
                        reentered_from_state=state_before,
                    )
                    if motion_signal:
                        candidate_duration = diagnostic["to_time_seconds"] - motion_candidate["start_time_seconds"]
                        if candidate_duration >= self.rule.motion_minimum_duration_seconds:
                            active_motion = self._start_motion_event(next_motion_id, motion_candidate, diagnostic)
                            next_motion_id += 1
                            processor_state = "tracking_motion"
                            action = "motion_detected"
                    else:
                        motion_candidate = None

                elif processor_state == "tracking_motion":
                    if motion_signal and active_motion is not None:
                        self._extend_motion_event(active_motion, diagnostic, motion_difference)
                        action = "track_motion"
                    elif active_motion is not None:
                        motion_event = self._finish_motion_event(active_motion, diagnostic)
                        motion_events.append(motion_event)
                        preceding_motion_id = motion_event["motion_id"]
                        motion_end_time_seconds = motion_event["end_time"]
                        active_motion = None
                        motion_candidate = None
                        processor_state = "searching_stable_plateau"
                        action = "motion_end"

                elif processor_state in ("searching_stable_plateau", "building_stable_plateau"):
                    motion_candidate = self._update_motion_candidate(
                        motion_candidate,
                        diagnostic,
                        motion_difference,
                        reentered_from_state=state_before,
                    )
                    if motion_signal:
                        candidate_duration = diagnostic["to_time_seconds"] - motion_candidate["start_time_seconds"]
                        if candidate_duration >= self.rule.motion_minimum_duration_seconds:
                            if current_sequence is not None and current_sequence.is_confirmed:
                                finalize_result = self._finalize_sequence(
                                    current_sequence=current_sequence,
                                    stable_segments=stable_segments,
                                    page_number=page_number,
                                    termination_reason="next_motion_detected",
                                    trigger_relation=diagnostic,
                                    boundary_after=(sampled, frame),
                                    rejected_sequences=rejected_sequences,
                                    image_output_failures=image_output_failures,
                                    segment_manifest=segment_manifest,
                                    preceding_motion_id=preceding_motion_id,
                                    motion_end_time_seconds=motion_end_time_seconds,
                                )
                                page_number = finalize_result.next_page_number
                                completed_segment_count += finalize_result.completed_segment_count
                                discarded_short_segment_count += finalize_result.discarded_short_segment_count
                                output_image_count += finalize_result.output_image_count
                                cancelled_count = 0
                            else:
                                cancelled_count = self._cancel_plateau_sequence(
                                    current_sequence=current_sequence,
                                    trigger_relation=diagnostic,
                                    boundary_after=(sampled, frame),
                                    rejected_sequences=rejected_sequences,
                                    segment_manifest=segment_manifest,
                                    preceding_motion_id=preceding_motion_id,
                                    motion_end_time_seconds=motion_end_time_seconds,
                                )
                                discarded_short_segment_count += cancelled_count
                                plateau_cancelled_by_motion_count += cancelled_count
                            motion_reentry_count += 1
                            current_sequence = None
                            active_motion = self._start_motion_event(next_motion_id, motion_candidate, diagnostic)
                            next_motion_id += 1
                            processor_state = "tracking_motion"
                            action = "motion_reentry" if cancelled_count == 0 else "cancel_plateau"
                        else:
                            action = "motion_candidate"
                    else:
                        motion_candidate = None

                if (
                    action == "none"
                    and processor_state in ("initial_search", "searching_stable_plateau", "building_stable_plateau")
                    and diagnostic["final_qualifying"]
                ):
                    qualifying_relation_count += 1
                    if current_sequence is None:
                        current_sequence = StableSequenceState(sequence_id=next_sequence_id)
                        next_sequence_id += 1
                        candidate_sequence_count += 1
                        action = "start_sequence"
                        processor_state = "building_stable_plateau"
                    else:
                        action = "append_relation"
                    if current_sequence.fail_start_time_seconds is not None:
                        current_sequence.recover_from_grace_period()
                        grace_period_recovered_count += 1
                    current_sequence.add_relation(previous[0], previous[1], sampled, frame, relation, previous_previous)

                    if (
                        not current_sequence.is_confirmed
                        and self.rule.is_complete_sequence(current_sequence.stable_duration_seconds)
                    ):
                        stable_plateau_count += 1
                        current_sequence.confirm(relation)
                        if preceding_motion_id is not None:
                            accepted_after_motion_count += 1
                        else:
                            initial_page_count += 1
                        action = "stable_page_confirmed"
                    elif current_sequence.is_confirmed:
                        action = "collect_confirmed_candidate"
                elif (
                    action == "none"
                    and processor_state in ("initial_search", "searching_stable_plateau", "building_stable_plateau")
                ):
                    non_qualifying_relation_count += 1
                    if current_sequence is None:
                        action = "none"
                    elif processor_state == "building_stable_plateau":
                        if current_sequence.is_confirmed:
                            action = "confirmed_candidate_hold"
                        elif current_sequence.fail_start_time_seconds is None:
                            current_sequence.enter_grace_period(diagnostic["to_time_seconds"])
                            grace_period_enter_count += 1
                            action = "enter_grace_period"
                        else:
                            grace_elapsed_for_diagnostic = current_sequence.grace_elapsed_seconds(
                                diagnostic["to_time_seconds"]
                            )
                            if (
                                grace_elapsed_for_diagnostic is not None
                                and grace_elapsed_for_diagnostic <= self.rule.fail_tolerance_seconds
                            ):
                                action = "continue_grace_period"
                            else:
                                finalize_result = self._finalize_sequence(
                                    current_sequence=current_sequence,
                                    stable_segments=stable_segments,
                                    page_number=page_number,
                                    termination_reason="fail_tolerance_timeout",
                                    trigger_relation=diagnostic,
                                    boundary_after=(sampled, frame),
                                    rejected_sequences=rejected_sequences,
                                    image_output_failures=image_output_failures,
                                    segment_manifest=segment_manifest,
                                    preceding_motion_id=preceding_motion_id,
                                    motion_end_time_seconds=motion_end_time_seconds,
                                )
                                page_number = finalize_result.next_page_number
                                completed_segment_count += finalize_result.completed_segment_count
                                discarded_short_segment_count += finalize_result.discarded_short_segment_count
                                output_image_count += finalize_result.output_image_count
                                grace_period_timeout_count += 1
                                action = self._finalize_action(finalize_result)
                                current_sequence = None
                                processor_state = "initial_search" if preceding_motion_id is None else "searching_stable_plateau"
                    else:
                        finalize_result = self._finalize_sequence(
                            current_sequence=current_sequence,
                            stable_segments=stable_segments,
                            page_number=page_number,
                            termination_reason="stable_plateau_interrupted",
                            trigger_relation=diagnostic,
                            boundary_after=(sampled, frame),
                            rejected_sequences=rejected_sequences,
                            image_output_failures=image_output_failures,
                            segment_manifest=segment_manifest,
                            preceding_motion_id=preceding_motion_id,
                            motion_end_time_seconds=motion_end_time_seconds,
                        )
                        page_number = finalize_result.next_page_number
                        completed_segment_count += finalize_result.completed_segment_count
                        discarded_short_segment_count += finalize_result.discarded_short_segment_count
                        output_image_count += finalize_result.output_image_count
                        action = self._finalize_action(finalize_result)
                        current_sequence = None
                        processor_state = "initial_search" if preceding_motion_id is None else "searching_stable_plateau"
                else:
                    non_qualifying_relation_count += 1

                state_after = processor_state
                diagnostic["motion_candidate_active"] = motion_candidate is not None
                diagnostic["active_motion_id"] = active_motion["motion_id"] if active_motion else None
                diagnostic["preceding_motion_id"] = preceding_motion_id
                diagnostic["motion_end_time_seconds"] = motion_end_time_seconds
                fail_grace_active = (
                    current_sequence is not None
                    and current_sequence.fail_start_time_seconds is not None
                )
                diagnostic["fail_grace_active"] = fail_grace_active
                diagnostic["fail_grace_start_time_seconds"] = (
                    current_sequence.fail_start_time_seconds
                    if current_sequence is not None
                    else None
                )
                diagnostic["fail_grace_elapsed_seconds"] = (
                    grace_elapsed_for_diagnostic
                    if grace_elapsed_for_diagnostic is not None
                    else current_sequence.grace_elapsed_seconds(diagnostic["to_time_seconds"])
                    if fail_grace_active
                    else None
                )
                diagnostic["state_before"] = state_before
                diagnostic["state_after"] = state_after
                relation_diagnostics.append(diagnostic)
                self._append_state_trace(
                    state_machine_trace=state_machine_trace,
                    relation=diagnostic,
                    state_before=state_before,
                    state_after=state_after,
                    active_sequence_id=active_sequence_id if "active_sequence_id" in locals() else (
                        current_sequence.sequence_id if current_sequence else None
                    ),
                    action=action,
                )
                if "active_sequence_id" in locals():
                    del active_sequence_id

                previous_previous = previous
                previous = (sampled, frame)

        midstream_decode_failure_count = frame_source.decode_failure_count
        if midstream_decode_failure_count:
            stopped_reason = "completed_with_decode_failure"

        if active_motion is not None:
            motion_events.append(self._finish_motion_event_at_eof(active_motion))
            active_motion = None

        final_flush_performed = current_sequence is not None
        final_flush_result = self._finalize_sequence(
            current_sequence=current_sequence,
            stable_segments=stable_segments,
            page_number=page_number,
            termination_reason="end_of_video",
            trigger_relation=None,
            boundary_after=None,
            rejected_sequences=rejected_sequences,
            image_output_failures=image_output_failures,
            segment_manifest=segment_manifest,
            preceding_motion_id=preceding_motion_id,
            motion_end_time_seconds=motion_end_time_seconds,
        )
        completed_segment_count += final_flush_result.completed_segment_count
        discarded_short_segment_count += final_flush_result.discarded_short_segment_count
        output_image_count += final_flush_result.output_image_count

        return scrub_json(
            {
                "schema_version": "1.0",
                "report_name": "Stable Page Processor",
                "video_metadata": metadata.__dict__,
                "execution_summary": self._execution_summary(
                    metadata=metadata,
                    expected_sampled_frames=expected_sampled_frames,
                    processed_samples=processed_samples,
                    decoded_frame_count=decoded_frame_count,
                    last_decoded_frame_index=last_decoded_frame_index,
                    midstream_decode_failure_count=midstream_decode_failure_count,
                    relation_count=relation_count,
                    relation_diagnostics=relation_diagnostics,
                    qualifying_relation_count=qualifying_relation_count,
                    non_qualifying_relation_count=non_qualifying_relation_count,
                    candidate_sequence_count=candidate_sequence_count,
                    stable_segment_count=len(stable_segments),
                    completed_segment_count=completed_segment_count,
                    discarded_short_segment_count=discarded_short_segment_count,
                    output_image_count=output_image_count,
                    grace_period_enter_count=grace_period_enter_count,
                    grace_period_recovered_count=grace_period_recovered_count,
                    grace_period_timeout_count=grace_period_timeout_count,
                    motion_event_count=len(motion_events),
                    stable_plateau_count=stable_plateau_count,
                    accepted_after_motion_count=accepted_after_motion_count,
                    initial_page_count=initial_page_count,
                    motion_reentry_count=motion_reentry_count,
                    plateau_cancelled_by_motion_count=plateau_cancelled_by_motion_count,
                    final_flush_performed=final_flush_performed,
                    stopped_reason=stopped_reason,
                ),
                "config": {
                    "frame_interval": frame_interval,
                    "ssim_minimum": self.rule.ssim_minimum,
                    "adjacent_difference_maximum": self.rule.adjacent_difference_maximum,
                    "lookback_seconds": self.rule.lookback_seconds,
                    "lookback_difference_maximum": self.rule.lookback_difference_maximum,
                    "anchor_difference_maximum": self.rule.anchor_difference_maximum,
                    "motion_difference_threshold": self.rule.motion_difference_threshold,
                    "motion_minimum_duration_seconds": self.rule.motion_minimum_duration_seconds,
                    "minimum_stable_duration_seconds": self.rule.minimum_stable_duration_seconds,
                    "fail_tolerance_seconds": self.rule.fail_tolerance_seconds,
                    "best_frame_exclusion_seconds": self.best_frame_exclusion_seconds,
                    "decision_metrics": self.rule.decision_metrics,
                    "diagnostic_metrics": self.rule.diagnostic_metrics,
                    "pages_directory": str(self.pages_dir),
                },
                "metric_statistics": self._metric_statistics(relation_diagnostics),
                "threshold_nearest_relations": self._threshold_nearest_relations(relation_diagnostics),
                "relations": [self._relation_report_item(item) for item in relation_diagnostics],
                "first_50_relations": [self._relation_report_item(item) for item in relation_diagnostics[:50]],
                "first_15_seconds_relations": [
                    self._relation_report_item(item)
                    for item in relation_diagnostics
                    if item["to_time_seconds"] <= 15.0
                ],
                "stable_segments": stable_segments,
                "motion_events": motion_events,
                "segment_manifest": self._linked_segment_manifest(segment_manifest),
                "state_machine_trace": state_machine_trace,
                "sequence_timeline": self._sequence_timeline(
                    metadata_duration_seconds=metadata.duration_seconds,
                    segment_manifest=segment_manifest,
                ),
                "rejected_sequences": rejected_sequences,
                "image_output_failures": image_output_failures,
                "warnings": self._warnings(metadata, stable_segments),
                "errors": [],
            }
        )

    def _clear_previous_pages(self) -> None:
        for path in self.pages_dir.glob("page_*.png"):
            if path.is_file():
                path.unlink()

    def _clear_previous_debug_segments(self) -> None:
        for path in self.debug_segments_dir.glob("segment_*.png"):
            if path.is_file():
                path.unlink()

    def _timestamp(self, frame_index: int, fps: float) -> float:
        return round(frame_index / fps, 6) if fps > 0 else 0.0

    def _sampled_frame(self, frame: np.ndarray, sample_index: int, frame_index: int, fps: float) -> SampledFrame:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        timestamp = self._timestamp(frame_index, fps)
        laplacian = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return SampledFrame(
            sample_index=sample_index,
            frame_index=frame_index,
            timestamp_seconds=timestamp,
            timestamp_formatted=format_duration(timestamp),
            laplacian_variance=laplacian,
        )

    def _find_lookback_frame(
        self,
        frame_buffer: list[FrameBufferItem],
        target_time_seconds: float,
    ) -> FrameBufferItem | None:
        candidates = [item for item in frame_buffer if item.timestamp_seconds <= target_time_seconds]
        if not candidates:
            return None
        return min(candidates, key=lambda item: abs(item.timestamp_seconds - target_time_seconds))

    def _trim_frame_buffer(self, frame_buffer: list[FrameBufferItem], current_time_seconds: float) -> None:
        keep_after = current_time_seconds - self.rule.lookback_seconds - 1.0
        while frame_buffer and frame_buffer[0].timestamp_seconds < keep_after:
            frame_buffer.pop(0)

    def _relation(
        self,
        relation_index: int,
        previous_sample: SampledFrame,
        previous_frame: np.ndarray,
        current_sample: SampledFrame,
        current_frame: np.ndarray,
        lookback_frame: FrameBufferItem | None,
        current_sequence: StableSequenceState | None,
    ) -> StableRelation:
        previous_gray = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
        current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        adjacent_score = difference_score(previous_gray, current_gray)
        adjacent_pass = adjacent_score <= self.rule.adjacent_difference_maximum
        lookback_score = None
        lookback_pass = False
        lookback_gap = None
        qualification_reason = "lookback_not_available"
        if lookback_frame is not None:
            lookback_gray = cv2.cvtColor(lookback_frame.frame, cv2.COLOR_BGR2GRAY)
            lookback_score = difference_score(lookback_gray, current_gray)
            lookback_pass = lookback_score <= self.rule.lookback_difference_maximum
            lookback_gap = round(current_sample.timestamp_seconds - lookback_frame.timestamp_seconds, 6)
            qualification_reason = "qualified" if adjacent_pass and lookback_pass else "threshold_not_met"

        anchor_score = None
        anchor_pass = False
        anchor_frame_index = None
        anchor_time_seconds = None
        if current_sequence is not None and current_sequence.anchor_image is not None and current_sequence.anchor_frame:
            anchor_gray = cv2.cvtColor(current_sequence.anchor_image, cv2.COLOR_BGR2GRAY)
            anchor_score = difference_score(anchor_gray, current_gray)
            anchor_pass = anchor_score <= self.rule.anchor_difference_maximum
            anchor_frame_index = current_sequence.anchor_frame["frame_index"]
            anchor_time_seconds = current_sequence.anchor_frame["timestamp_seconds"]
            if not anchor_pass:
                qualification_reason = "anchor_threshold_not_met"

        return StableRelation(
            relation_index=relation_index,
            from_sample_index=previous_sample.sample_index,
            to_sample_index=current_sample.sample_index,
            from_frame_index=previous_sample.frame_index,
            to_frame_index=current_sample.frame_index,
            from_time_seconds=previous_sample.timestamp_seconds,
            to_time_seconds=current_sample.timestamp_seconds,
            adjacent_difference_score=adjacent_score,
            adjacent_pass=adjacent_pass,
            lookback_frame_index=lookback_frame.frame_index if lookback_frame else None,
            lookback_time_seconds=lookback_frame.timestamp_seconds if lookback_frame else None,
            lookback_time_gap_seconds=lookback_gap,
            lookback_difference_score=lookback_score,
            lookback_pass=lookback_pass,
            anchor_frame_index=anchor_frame_index,
            anchor_time_seconds=anchor_time_seconds,
            anchor_difference_score=anchor_score,
            anchor_pass=anchor_pass,
            qualification_reason=qualification_reason,
            ssim=ssim(previous_gray, current_gray),
        )

    def _relation_diagnostic(self, relation: StableRelation, final_qualifying: bool) -> dict[str, Any]:
        ssim_pass = relation.ssim >= self.rule.ssim_minimum
        return {
            **relation.__dict__,
            "lookback_available": relation.lookback_difference_score is not None,
            "anchor_available": relation.anchor_difference_score is not None,
            "ssim_pass": ssim_pass,
            "final_qualifying": final_qualifying,
        }

    def _state_name(self, current_sequence: StableSequenceState | None) -> str:
        if current_sequence is None:
            return "searching"
        if current_sequence.fail_start_time_seconds is not None:
            return "grace_period"
        return "building"

    def _finalize_action(self, result: FinalizeResult) -> str:
        if result.completed_segment_count:
            return "finalize_accepted"
        if result.discarded_short_segment_count:
            return "finalize_rejected"
        return "none"

    def _append_state_trace(
        self,
        state_machine_trace: list[dict[str, Any]],
        relation: dict[str, Any],
        state_before: str,
        state_after: str,
        active_sequence_id: int | None,
        action: str,
    ) -> None:
        if relation["to_time_seconds"] > 30.0:
            return
        state_machine_trace.append(
            {
                "relation_index": relation["relation_index"],
                "from_frame_index": relation["from_frame_index"],
                "to_frame_index": relation["to_frame_index"],
                "from_time_seconds": relation["from_time_seconds"],
                "to_time_seconds": relation["to_time_seconds"],
                "adjacent_difference_score": relation["adjacent_difference_score"],
                "lookback_difference_score": relation["lookback_difference_score"],
                "motion_difference_score": relation["motion_difference_score"],
                "motion_signal": relation["motion_signal"],
                "motion_candidate_active": relation["motion_candidate_active"],
                "active_motion_id": relation["active_motion_id"],
                "preceding_motion_id": relation["preceding_motion_id"],
                "motion_end_time_seconds": relation["motion_end_time_seconds"],
                "anchor_frame_index": relation["anchor_frame_index"],
                "anchor_time_seconds": relation["anchor_time_seconds"],
                "anchor_difference_score": relation["anchor_difference_score"],
                "anchor_pass": relation["anchor_pass"],
                "fail_grace_active": relation["state_before"] == "grace_period"
                or relation["state_after"] == "grace_period",
                "fail_grace_start_time_seconds": relation.get("fail_grace_start_time_seconds"),
                "fail_grace_elapsed_seconds": relation.get("fail_grace_elapsed_seconds"),
                "adjacent_pass": relation["adjacent_pass"],
                "lookback_pass": relation["lookback_pass"],
                "final_qualifying": relation["final_qualifying"],
                "state_before": state_before,
                "state_after": state_after,
                "active_sequence_id": active_sequence_id,
                "action": action,
            }
        )

    def _update_motion_candidate(
        self,
        motion_candidate: dict[str, Any] | None,
        relation: dict[str, Any],
        motion_difference: float,
        reentered_from_state: str,
    ) -> dict[str, Any] | None:
        if not relation["motion_signal"]:
            return None
        if motion_candidate is None:
            return {
                "start_frame_index": relation["from_frame_index"],
                "start_time_seconds": relation["from_time_seconds"],
                "maximum_difference": motion_difference,
                "reentered_from_state": reentered_from_state,
            }
        motion_candidate["maximum_difference"] = max(motion_candidate["maximum_difference"], motion_difference)
        return motion_candidate

    def _start_motion_event(
        self,
        motion_id: int,
        motion_candidate: dict[str, Any],
        relation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "motion_id": motion_id,
            "start_frame_index": motion_candidate["start_frame_index"],
            "start_time": motion_candidate["start_time_seconds"],
            "end_frame_index": relation["to_frame_index"],
            "end_time": relation["to_time_seconds"],
            "duration": relation["to_time_seconds"] - motion_candidate["start_time_seconds"],
            "maximum_difference": max(motion_candidate["maximum_difference"], relation["motion_difference_score"]),
            "end_reason": "tracking",
            "reentered_from_state": motion_candidate["reentered_from_state"],
        }

    def _extend_motion_event(
        self,
        active_motion: dict[str, Any],
        relation: dict[str, Any],
        motion_difference: float,
    ) -> None:
        active_motion["end_frame_index"] = relation["to_frame_index"]
        active_motion["end_time"] = relation["to_time_seconds"]
        active_motion["duration"] = active_motion["end_time"] - active_motion["start_time"]
        active_motion["maximum_difference"] = max(active_motion["maximum_difference"], motion_difference)

    def _finish_motion_event(self, active_motion: dict[str, Any], trigger_relation: dict[str, Any]) -> dict[str, Any]:
        finished = dict(active_motion)
        finished["end_frame_index"] = trigger_relation["from_frame_index"]
        finished["end_time"] = trigger_relation["from_time_seconds"]
        finished["duration"] = finished["end_time"] - finished["start_time"]
        finished["end_reason"] = "difference_below_threshold"
        return finished

    def _finish_motion_event_at_eof(self, active_motion: dict[str, Any]) -> dict[str, Any]:
        finished = dict(active_motion)
        finished["end_reason"] = "end_of_video"
        return finished

    def _finalize_sequence(
        self,
        current_sequence: StableSequenceState | None,
        stable_segments: list[dict[str, Any]],
        page_number: int,
        termination_reason: str,
        trigger_relation: dict[str, Any] | None,
        boundary_after: tuple[SampledFrame, np.ndarray] | None,
        rejected_sequences: list[dict[str, Any]],
        image_output_failures: list[dict[str, Any]],
        segment_manifest: list[dict[str, Any]],
        preceding_motion_id: int | None = None,
        motion_end_time_seconds: float | None = None,
    ) -> FinalizeResult:
        if current_sequence is None:
            return FinalizeResult(page_number, 0, 0, 0)

        current_sequence.boundary_after = boundary_after
        previous_sequence_id = segment_manifest[-1]["sequence_id"] if segment_manifest else None
        gap_from_previous_seconds = self._gap_from_previous(segment_manifest, current_sequence)

        if not self.rule.is_complete_sequence(current_sequence.stable_duration_seconds):
            segment_manifest.append(
                current_sequence.to_manifest(
                    status="rejected",
                    termination_reason=termination_reason,
                    trigger_relation=self._manifest_relation(trigger_relation),
                    previous_sequence_id=previous_sequence_id,
                    gap_from_previous_seconds=gap_from_previous_seconds,
                    preceding_motion_id=preceding_motion_id,
                    motion_end_time_seconds=motion_end_time_seconds,
                    rejection_reason="minimum_stable_duration_not_met",
                )
            )
            rejected_sequences.append(
                self._rejected_sequence(
                    current_sequence=current_sequence,
                    rejection_reason="minimum_stable_duration_not_met",
                    termination_reason=termination_reason,
                )
            )
            return FinalizeResult(page_number, 0, 1, 0)

        current_sequence.select_best_frame(
            self.best_frame_selector,
            exclusion_seconds=self.best_frame_exclusion_seconds,
        )
        page_path = self.pages_dir / f"page_{page_number:03d}.png"
        if current_sequence.selected_frame_image is None:
            segment_manifest.append(
                current_sequence.to_manifest(
                    status="rejected",
                    termination_reason=termination_reason,
                    trigger_relation=self._manifest_relation(trigger_relation),
                    previous_sequence_id=previous_sequence_id,
                    gap_from_previous_seconds=gap_from_previous_seconds,
                    preceding_motion_id=preceding_motion_id,
                    motion_end_time_seconds=motion_end_time_seconds,
                    rejection_reason="no_candidate_frame",
                )
            )
            rejected_sequences.append(
                self._rejected_sequence(
                    current_sequence=current_sequence,
                    rejection_reason="no_candidate_frame",
                    termination_reason=termination_reason,
                )
            )
            return FinalizeResult(page_number, 0, 1, 0)

        ok = cv2.imwrite(str(page_path), current_sequence.selected_frame_image)
        stable_segments.append(
            current_sequence.to_segment(
                len(stable_segments) + 1,
                page_path,
                preceding_motion_id=preceding_motion_id,
                motion_end_time_seconds=motion_end_time_seconds,
            )
        )
        segment_index = len(stable_segments)
        manifest_item = current_sequence.to_manifest(
            status="accepted",
            termination_reason=termination_reason,
            trigger_relation=self._manifest_relation(trigger_relation),
            previous_sequence_id=previous_sequence_id,
            gap_from_previous_seconds=gap_from_previous_seconds,
            preceding_motion_id=preceding_motion_id,
            motion_end_time_seconds=motion_end_time_seconds,
        )
        self._write_debug_segment_images(current_sequence, segment_index)
        manifest_item["debug_image_paths"] = self._debug_image_paths(current_sequence, segment_index)
        segment_manifest.append(manifest_item)
        if not ok:
            image_output_failures.append(
                self._rejected_sequence(
                    current_sequence=current_sequence,
                    rejection_reason="write_failed",
                    termination_reason=termination_reason,
                )
            )
        return FinalizeResult(page_number + 1, 1, 0, 1 if ok else 0)

    def _cancel_plateau_sequence(
        self,
        current_sequence: StableSequenceState | None,
        trigger_relation: dict[str, Any],
        boundary_after: tuple[SampledFrame, np.ndarray],
        rejected_sequences: list[dict[str, Any]],
        segment_manifest: list[dict[str, Any]],
        preceding_motion_id: int | None,
        motion_end_time_seconds: float | None,
    ) -> int:
        if current_sequence is None:
            return 0

        current_sequence.boundary_after = boundary_after
        previous_sequence_id = segment_manifest[-1]["sequence_id"] if segment_manifest else None
        gap_from_previous_seconds = self._gap_from_previous(segment_manifest, current_sequence)
        segment_manifest.append(
            current_sequence.to_manifest(
                status="rejected",
                termination_reason="new_motion_detected",
                trigger_relation=self._manifest_relation(trigger_relation),
                previous_sequence_id=previous_sequence_id,
                gap_from_previous_seconds=gap_from_previous_seconds,
                preceding_motion_id=preceding_motion_id,
                motion_end_time_seconds=motion_end_time_seconds,
                rejection_reason="cancelled_by_new_motion",
            )
        )
        rejected_sequences.append(
            self._rejected_sequence(
                current_sequence=current_sequence,
                rejection_reason="cancelled_by_new_motion",
                termination_reason="new_motion_detected",
            )
        )
        return 1

    def _write_debug_segment_images(self, current_sequence: StableSequenceState, segment_index: int) -> None:
        for label, frame in current_sequence.debug_frames().items():
            path = self.debug_segments_dir / f"segment_{segment_index:03d}_{label}.png"
            cv2.imwrite(str(path), frame)

    def _debug_image_paths(self, current_sequence: StableSequenceState, segment_index: int) -> dict[str, str]:
        return {
            label: str(self.debug_segments_dir / f"segment_{segment_index:03d}_{label}.png")
            for label in current_sequence.debug_frames()
        }

    def _gap_from_previous(
        self,
        segment_manifest: list[dict[str, Any]],
        current_sequence: StableSequenceState,
    ) -> float | None:
        if not segment_manifest:
            return None
        previous_end = segment_manifest[-1].get("end_time_seconds")
        candidates = sorted(current_sequence.candidate_frames.values(), key=lambda item: item["frame_index"])
        if previous_end is None or not candidates:
            return None
        return float(candidates[0]["timestamp_seconds"] - previous_end)

    def _manifest_relation(self, relation: dict[str, Any] | None) -> dict[str, Any] | None:
        if relation is None:
            return None
        return {
            "from_frame_index": relation["from_frame_index"],
            "to_frame_index": relation["to_frame_index"],
            "adjacent_difference_score": relation["adjacent_difference_score"],
            "lookback_difference_score": relation["lookback_difference_score"],
            "motion_difference_score": relation["motion_difference_score"],
            "motion_signal": relation["motion_signal"],
            "anchor_frame_index": relation["anchor_frame_index"],
            "anchor_time_seconds": relation["anchor_time_seconds"],
            "anchor_difference_score": relation["anchor_difference_score"],
            "adjacent_pass": relation["adjacent_pass"],
            "lookback_pass": relation["lookback_pass"],
            "anchor_pass": relation["anchor_pass"],
            "final_qualifying": relation["final_qualifying"],
        }

    def _rejected_sequence(
        self,
        current_sequence: StableSequenceState,
        rejection_reason: str,
        termination_reason: str,
    ) -> dict[str, Any]:
        candidates = sorted(current_sequence.candidate_frames.values(), key=lambda item: item["sample_index"])
        first = candidates[0] if candidates else None
        last = candidates[-1] if candidates else None
        relation_count = len(current_sequence.stable_relations)
        return {
            "sequence_id": current_sequence.sequence_id,
            "start_sample_index": first["sample_index"] if first else None,
            "end_sample_index": last["sample_index"] if last else None,
            "sample_count": len(candidates),
            "relation_count": relation_count,
            "qualified_relation_count": relation_count,
            "stable_duration_seconds": current_sequence.stable_duration_seconds,
            "rejection_reason": rejection_reason,
            "termination_reason": termination_reason,
        }

    def _warnings(self, metadata: Any, stable_segments: list[dict[str, Any]]) -> list[str]:
        warnings: list[str] = []
        if metadata.fps <= 0:
            warnings.append("Video FPS is unavailable or zero; sampled frame timestamps may be inaccurate.")
        if not stable_segments:
            warnings.append("No stable segments were extracted.")
        return warnings

    def _linked_segment_manifest(self, segment_manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
        linked = [dict(item) for item in segment_manifest]
        for index, item in enumerate(linked):
            item["next_sequence_id"] = linked[index + 1]["sequence_id"] if index + 1 < len(linked) else None
        return linked

    def _sequence_timeline(
        self,
        metadata_duration_seconds: float,
        segment_manifest: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        timeline: list[dict[str, Any]] = []
        cursor = 0.0
        ordered = sorted(
            segment_manifest,
            key=lambda item: (
                item["start_time_seconds"] is None,
                item["start_time_seconds"] if item["start_time_seconds"] is not None else 0.0,
            ),
        )
        for item in ordered:
            start_time = item["start_time_seconds"]
            end_time = item["end_time_seconds"]
            if start_time is None or end_time is None:
                continue
            if start_time > cursor:
                timeline.append(
                    {
                        "start_time_seconds": cursor,
                        "end_time_seconds": start_time,
                        "type": "no_candidate",
                        "sequence_id": None,
                    }
                )
            timeline.append(
                {
                    "start_time_seconds": start_time,
                    "end_time_seconds": end_time,
                    "type": item["status"],
                    "sequence_id": item["sequence_id"],
                }
            )
            cursor = max(cursor, end_time)

        if metadata_duration_seconds > cursor:
            timeline.append(
                {
                    "start_time_seconds": cursor,
                    "end_time_seconds": metadata_duration_seconds,
                    "type": "no_candidate",
                    "sequence_id": None,
                }
            )
        return timeline

    def _execution_summary(
        self,
        metadata: Any,
        expected_sampled_frames: int | None,
        processed_samples: list[SampledFrame],
        decoded_frame_count: int,
        last_decoded_frame_index: int | None,
        midstream_decode_failure_count: int,
        relation_count: int,
        relation_diagnostics: list[dict[str, Any]],
        qualifying_relation_count: int,
        non_qualifying_relation_count: int,
        candidate_sequence_count: int,
        stable_segment_count: int,
        completed_segment_count: int,
        discarded_short_segment_count: int,
        output_image_count: int,
        grace_period_enter_count: int,
        grace_period_recovered_count: int,
        grace_period_timeout_count: int,
        motion_event_count: int,
        stable_plateau_count: int,
        accepted_after_motion_count: int,
        initial_page_count: int,
        motion_reentry_count: int,
        plateau_cancelled_by_motion_count: int,
        final_flush_performed: bool,
        stopped_reason: str,
    ) -> dict[str, Any]:
        first = processed_samples[0] if processed_samples else None
        last = processed_samples[-1] if processed_samples else None
        signal_counts = self._signal_counts(relation_diagnostics)

        return {
            "metadata_total_frames": metadata.total_frames,
            "total_frames": metadata.total_frames,
            "total_video_frames": metadata.total_frames,
            "frame_interval": self.frame_interval,
            "expected_sampled_frames": expected_sampled_frames,
            "decoded_frame_count": decoded_frame_count,
            "processed_sampled_frames": len(processed_samples),
            "sampled_frame_count": len(processed_samples),
            "relation_count": relation_count,
            "last_decoded_frame_index": last_decoded_frame_index,
            "first_processed_frame_index": first.frame_index if first else None,
            "last_processed_frame_index": last.frame_index if last else None,
            "first_processed_time_seconds": first.timestamp_seconds if first else None,
            "last_processed_time_seconds": last.timestamp_seconds if last else None,
            "qualifying_relation_count": qualifying_relation_count,
            "non_qualifying_relation_count": non_qualifying_relation_count,
            "stable_relation_count": qualifying_relation_count,
            "unstable_relation_count": non_qualifying_relation_count,
            "midstream_decode_failure_count": midstream_decode_failure_count,
            **signal_counts,
            "candidate_sequence_count": candidate_sequence_count,
            "stable_segment_count": stable_segment_count,
            "accepted_segment_count": stable_segment_count,
            "rejected_sequence_count": discarded_short_segment_count,
            "completed_segment_count": completed_segment_count,
            "discarded_short_segment_count": discarded_short_segment_count,
            "output_image_count": output_image_count,
            "grace_period_enter_count": grace_period_enter_count,
            "grace_period_recovered_count": grace_period_recovered_count,
            "grace_period_timeout_count": grace_period_timeout_count,
            "motion_event_count": motion_event_count,
            "stable_plateau_count": stable_plateau_count,
            "accepted_after_motion_count": accepted_after_motion_count,
            "initial_page_count": initial_page_count,
            "motion_reentry_count": motion_reentry_count,
            "plateau_cancelled_by_motion_count": plateau_cancelled_by_motion_count,
            "final_flush_performed": final_flush_performed,
            "decision_metrics": self.rule.decision_metrics,
            "diagnostic_metrics": self.rule.diagnostic_metrics,
            "stopped_reason": stopped_reason,
        }

    def _signal_counts(self, relation_diagnostics: list[dict[str, Any]]) -> dict[str, int]:
        adjacent_pass_count = 0
        lookback_pass_count = 0
        both_pass_count = 0
        adjacent_only_pass_count = 0
        lookback_only_pass_count = 0
        both_fail_count = 0
        lookback_available_relation_count = 0
        anchor_available_relation_count = 0
        anchor_pass_count = 0

        for item in relation_diagnostics:
            adjacent_pass = bool(item["adjacent_pass"])
            lookback_available = item["lookback_difference_score"] is not None
            lookback_pass = bool(item["lookback_pass"])
            anchor_available = item["anchor_difference_score"] is not None
            anchor_pass = bool(item["anchor_pass"])
            if adjacent_pass:
                adjacent_pass_count += 1
            if lookback_available:
                lookback_available_relation_count += 1
            if lookback_pass:
                lookback_pass_count += 1
            if anchor_available:
                anchor_available_relation_count += 1
            if anchor_pass:
                anchor_pass_count += 1

            if adjacent_pass and lookback_pass:
                both_pass_count += 1
            elif adjacent_pass:
                adjacent_only_pass_count += 1
            elif lookback_pass:
                lookback_only_pass_count += 1
            else:
                both_fail_count += 1

        relation_count = len(relation_diagnostics)
        return {
            "lookback_available_relation_count": lookback_available_relation_count,
            "lookback_unavailable_relation_count": relation_count - lookback_available_relation_count,
            "adjacent_pass_count": adjacent_pass_count,
            "adjacent_fail_count": relation_count - adjacent_pass_count,
            "lookback_pass_count": lookback_pass_count,
            "lookback_fail_count": relation_count - lookback_pass_count,
            "anchor_available_relation_count": anchor_available_relation_count,
            "anchor_pass_count": anchor_pass_count,
            "anchor_fail_count": relation_count - anchor_pass_count,
            "both_pass_count": both_pass_count,
            "adjacent_only_pass_count": adjacent_only_pass_count,
            "lookback_only_pass_count": lookback_only_pass_count,
            "both_fail_count": both_fail_count,
        }

    def _metric_statistics(self, relation_diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "adjacent_difference_statistics": self._distribution(
                [item["adjacent_difference_score"] for item in relation_diagnostics],
                self.rule.adjacent_difference_maximum,
            ),
            "lookback_difference_statistics": self._distribution(
                [
                    item["lookback_difference_score"]
                    for item in relation_diagnostics
                    if item["lookback_difference_score"] is not None
                ],
                self.rule.lookback_difference_maximum,
            ),
            "anchor_difference_statistics": self._distribution(
                [
                    item["anchor_difference_score"]
                    for item in relation_diagnostics
                    if item["anchor_difference_score"] is not None
                ],
                self.rule.anchor_difference_maximum,
            ),
            "motion_difference_statistics": self._distribution(
                [item["motion_difference_score"] for item in relation_diagnostics],
                self.rule.motion_difference_threshold,
            ),
            "ssim": self._distribution(
                [item["ssim"] for item in relation_diagnostics],
                self.rule.ssim_minimum,
            ),
        }

    def _distribution(self, values: list[float], threshold: float) -> dict[str, Any]:
        if not values:
            return {
                "minimum": None,
                "p01": None,
                "p05": None,
                "p10": None,
                "p25": None,
                "median": None,
                "p75": None,
                "p90": None,
                "p95": None,
                "p99": None,
                "maximum": None,
                "threshold": threshold,
            }

        array = np.array(values, dtype=float)
        return {
            "minimum": float(np.min(array)),
            "p01": float(np.percentile(array, 1)),
            "p05": float(np.percentile(array, 5)),
            "p10": float(np.percentile(array, 10)),
            "p25": float(np.percentile(array, 25)),
            "median": float(np.percentile(array, 50)),
            "p75": float(np.percentile(array, 75)),
            "p90": float(np.percentile(array, 90)),
            "p95": float(np.percentile(array, 95)),
            "p99": float(np.percentile(array, 99)),
            "maximum": float(np.max(array)),
            "threshold": threshold,
        }

    def _threshold_nearest_relations(self, relation_diagnostics: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        return {
            "adjacent_difference_score": self._nearest_relations(
                relation_diagnostics,
                "adjacent_difference_score",
                self.rule.adjacent_difference_maximum,
            ),
            "lookback_difference_score": self._nearest_relations(
                [item for item in relation_diagnostics if item["lookback_difference_score"] is not None],
                "lookback_difference_score",
                self.rule.lookback_difference_maximum,
            ),
            "anchor_difference_score": self._nearest_relations(
                [item for item in relation_diagnostics if item["anchor_difference_score"] is not None],
                "anchor_difference_score",
                self.rule.anchor_difference_maximum,
            ),
            "motion_difference_score": self._nearest_relations(
                relation_diagnostics,
                "motion_difference_score",
                self.rule.motion_difference_threshold,
            ),
            "ssim": self._nearest_relations(relation_diagnostics, "ssim", self.rule.ssim_minimum),
        }

    def _nearest_relations(
        self,
        relation_diagnostics: list[dict[str, Any]],
        metric: str,
        threshold: float,
    ) -> list[dict[str, Any]]:
        ranked = sorted(relation_diagnostics, key=lambda item: abs(float(item[metric]) - threshold))
        return [self._relation_report_item(item) for item in ranked[:20]]

    def _relation_report_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "relation_index": item["relation_index"],
            "from_frame_index": item["from_frame_index"],
            "to_frame_index": item["to_frame_index"],
            "from_sample_index": item["from_sample_index"],
            "to_sample_index": item["to_sample_index"],
            "from_time_seconds": item["from_time_seconds"],
            "to_time_seconds": item["to_time_seconds"],
            "adjacent_difference_score": item["adjacent_difference_score"],
            "adjacent_pass": item["adjacent_pass"],
            "motion_difference_score": item["motion_difference_score"],
            "motion_signal": item["motion_signal"],
            "motion_candidate_active": item["motion_candidate_active"],
            "active_motion_id": item["active_motion_id"],
            "preceding_motion_id": item["preceding_motion_id"],
            "motion_end_time_seconds": item["motion_end_time_seconds"],
            "lookback_frame_index": item["lookback_frame_index"],
            "lookback_time_seconds": item["lookback_time_seconds"],
            "lookback_time_gap_seconds": item["lookback_time_gap_seconds"],
            "lookback_available": item["lookback_available"],
            "lookback_difference_score": item["lookback_difference_score"],
            "lookback_pass": item["lookback_pass"],
            "anchor_frame_index": item["anchor_frame_index"],
            "anchor_time_seconds": item["anchor_time_seconds"],
            "anchor_available": item["anchor_available"],
            "anchor_difference_score": item["anchor_difference_score"],
            "anchor_pass": item["anchor_pass"],
            "fail_grace_active": item["fail_grace_active"],
            "fail_grace_start_time_seconds": item["fail_grace_start_time_seconds"],
            "fail_grace_elapsed_seconds": item["fail_grace_elapsed_seconds"],
            "state_before": item["state_before"],
            "state_after": item["state_after"],
            "ssim": item["ssim"],
            "ssim_pass": item["ssim_pass"],
            "final_qualifying": item["final_qualifying"],
            "qualification_reason": item["qualification_reason"],
        }
