from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .video_reader import (
    format_duration,
    read_metadata,
)


@dataclass(frozen=True)
class FrameMetrics:
    sample_index: int
    frame_index: int
    target_timestamp_seconds: float
    timestamp_seconds: float
    timestamp_formatted: str
    second: int
    brightness_mean: float
    contrast_std: float
    laplacian_variance: float
    adjacent_difference_score: float | None
    adjacent_sample_index: int | None
    adjacent_frame_index: int | None
    adjacent_timestamp_seconds: float | None
    adjacent_actual_seconds: float | None
    lookback_difference_score: float | None
    lookback_sample_offset: int
    lookback_sample_index: int | None
    lookback_frame_index: int | None
    lookback_timestamp_seconds: float | None
    lookback_actual_seconds: float | None


@dataclass(frozen=True)
class SampleFailure:
    requested_frame_index: int
    expected_timestamp_seconds: float
    capture_position_frames: float
    capture_position_msec: float


class VideoAnalyzer:
    def __init__(self, config: dict[str, Any], argus_root: Path) -> None:
        self.config = config
        self.argus_root = argus_root
        self.samples_per_second = float(config["sampling"]["samples_per_second"])
        if self.samples_per_second <= 0:
            raise ValueError("sampling.samples_per_second must be greater than zero")
        self.lookback_sample_offset = int(config["analysis"]["lookback_sample_offset"])
        if self.lookback_sample_offset <= 0:
            raise ValueError("analysis.lookback_sample_offset must be greater than zero")

    def analyze(self, video_path: Path) -> dict[str, Any]:
        metadata = read_metadata(video_path)
        sample_period_seconds = 1.0 / self.samples_per_second

        frames, failed_samples, reader_diagnostics = self._sample_frames(
            video_path=video_path,
            sample_period_seconds=sample_period_seconds,
            metadata_total_frames=metadata.total_frames,
            fps=metadata.fps,
        )
        sampled_indices = [frame.frame_index for frame in frames]
        frame_dicts = [asdict(frame) for frame in frames]
        failed_sample_dicts = [asdict(sample) for sample in failed_samples]
        reader_diagnostics.update(
            {
                "requested_sample_count": len(sampled_indices),
                "successful_sample_count": len(frames),
                "failed_sample_count": len(failed_samples),
            }
        )

        report = {
            "schema_version": "1.0",
            "video_metadata": asdict(metadata),
            "config": self.config,
            "reader_diagnostics": reader_diagnostics,
            "sampling": {
                "total_frames": metadata.total_frames,
                "sampled_frames": len(frames),
                "sampling_method": "time_based_sampling",
                "sample_timestamp_source": "cv2.CAP_PROP_POS_MSEC",
                "timestamp_seconds_definition": "Actual decoded video timestamp from CAP_PROP_POS_MSEC.",
                "target_timestamp_seconds_definition": "Sample target time: sample_index * sample_period_seconds.",
                "sampling_rate": self.samples_per_second,
                "sample_period_seconds": sample_period_seconds,
                "first_sampled_frame_index": frames[0].frame_index if frames else None,
                "last_sampled_frame_index": frames[-1].frame_index if frames else None,
                "all_requested_frames_read": len(frames) == len(sampled_indices),
                "first_requested_frame_index": sampled_indices[0] if sampled_indices else None,
                "last_requested_frame_index": sampled_indices[-1] if sampled_indices else None,
                "first_successful_sample_frame_index": frames[0].frame_index if frames else None,
                "last_successful_sample_frame_index": frames[-1].frame_index if frames else None,
                "first_failed_sample_frame_index": failed_samples[0].requested_frame_index
                if failed_samples
                else None,
                "last_failed_sample_frame_index": failed_samples[-1].requested_frame_index
                if failed_samples
                else None,
                "unsampled_tail_frame_count": self._unsampled_tail_frame_count(
                    metadata.total_frames, sampled_indices
                ),
                "unsampled_tail_duration_seconds": self._unsampled_tail_duration_seconds(
                    metadata.fps, metadata.total_frames, sampled_indices
                ),
                "failed_tail_frame_count": self._failed_tail_frame_count(failed_samples, frames),
                "failed_tail_duration_seconds": self._failed_tail_duration_seconds(
                    metadata.fps, failed_samples, frames
                ),
            },
            "frame_statistics": {
                "brightness": summarize_values(frame.brightness_mean for frame in frames),
                "contrast": summarize_values(frame.contrast_std for frame in frames),
                "laplacian_variance": summarize_values(frame.laplacian_variance for frame in frames),
                "adjacent_difference_score": summarize_values(
                    frame.adjacent_difference_score for frame in frames
                ),
                "lookback_difference_score": summarize_values(
                    frame.lookback_difference_score for frame in frames
                ),
            },
            "sampled_frames": frame_dicts,
            "failed_samples": failed_sample_dicts,
            "per_second_summary": self._per_second_summary(frames),
            "warnings": self._warnings(metadata, frames),
            "errors": [],
        }
        return scrub_json(report)

    def _sample_frames(
        self, video_path: Path, sample_period_seconds: float, metadata_total_frames: int, fps: float
    ) -> tuple[list[FrameMetrics], list[SampleFailure], dict[str, Any]]:
        capture = cv2.VideoCapture(str(video_path))
        frames: list[FrameMetrics] = []
        failed_samples: list[SampleFailure] = []
        decoded_frame_count = 0
        decode_attempt_count = 0
        first_failed_frame_index = None
        first_failed_timestamp_seconds = None
        capture_position_frames_at_failure = None
        capture_position_msec_at_failure = None
        last_decoded_timestamp_seconds = None
        successful_history: list[tuple[FrameMetrics, np.ndarray]] = []
        next_sample_number = 0
        sample_epsilon = 1e-9
        try:
            while True:
                ok, frame = capture.read()
                decode_attempt_count += 1
                if not ok or frame is None:
                    first_failed_frame_index = decoded_frame_count
                    capture_position_frames_at_failure = float(
                        capture.get(cv2.CAP_PROP_POS_FRAMES) or 0.0
                    )
                    capture_position_msec_at_failure = float(
                        capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0
                    )
                    first_failed_timestamp_seconds = self._capture_position_timestamp_seconds(capture)
                    break

                frame_index = decoded_frame_count
                decoded_frame_count += 1
                actual_timestamp = self._actual_timestamp_seconds(capture)
                last_decoded_timestamp_seconds = actual_timestamp
                while actual_timestamp + sample_epsilon >= next_sample_number * sample_period_seconds:
                    target_timestamp = round(next_sample_number * sample_period_seconds, 6)
                    sample_index = len(frames)
                    metrics, gray = self._analyze_frame(
                        frame=frame,
                        sample_index=sample_index,
                        frame_index=frame_index,
                        target_timestamp_seconds=target_timestamp,
                        actual_timestamp_seconds=actual_timestamp,
                        successful_history=successful_history,
                    )
                    frames.append(metrics)
                    successful_history.append((metrics, gray))
                    next_sample_number += 1
        finally:
            capture.release()

        if first_failed_frame_index is not None and first_failed_frame_index < metadata_total_frames:
            duration_seconds = metadata_total_frames / fps if fps > 0 else 0.0
            while next_sample_number * sample_period_seconds <= duration_seconds:
                failed_samples.append(
                    SampleFailure(
                        requested_frame_index=first_failed_frame_index,
                        expected_timestamp_seconds=round(
                            next_sample_number * sample_period_seconds, 6
                        ),
                        capture_position_frames=capture_position_frames_at_failure or 0.0,
                        capture_position_msec=capture_position_msec_at_failure or 0.0,
                    )
                )
                next_sample_number += 1

        expected_last_frame_index = metadata_total_frames - 1 if metadata_total_frames > 0 else None
        last_successful_frame_index = decoded_frame_count - 1 if decoded_frame_count > 0 else None
        normal_eof_count = 1 if first_failed_frame_index == metadata_total_frames else 0
        unexpected_decode_failure_count = (
            1
            if first_failed_frame_index is not None and first_failed_frame_index < metadata_total_frames
            else 0
        )
        missing_tail_frame_count = (
            max(0, metadata_total_frames - decoded_frame_count)
            if metadata_total_frames > 0
            else None
        )
        missing_tail_duration_seconds = (
            round(missing_tail_frame_count / fps, 6)
            if missing_tail_frame_count is not None and fps > 0
            else None
        )

        diagnostics = {
            "metadata_total_frames": metadata_total_frames,
            "metadata_fps": fps,
            "metadata_duration_seconds": metadata_total_frames / fps if fps > 0 else 0.0,
            "duration_from_frame_count_seconds": metadata_total_frames / fps if fps > 0 else 0.0,
            "decode_attempt_count": decode_attempt_count,
            "decoded_frame_count": decoded_frame_count,
            "normal_eof_count": normal_eof_count,
            "unexpected_decode_failure_count": unexpected_decode_failure_count,
            "last_successful_frame_index": last_successful_frame_index,
            "last_successful_timestamp_seconds": last_decoded_timestamp_seconds,
            "first_failed_frame_index": first_failed_frame_index,
            "first_failed_timestamp_seconds": first_failed_timestamp_seconds,
            "capture_position_frames_at_failure": capture_position_frames_at_failure,
            "capture_position_msec_at_failure": capture_position_msec_at_failure,
            "expected_last_frame_index": expected_last_frame_index,
            "missing_tail_frame_count": missing_tail_frame_count,
            "missing_tail_duration_seconds": missing_tail_duration_seconds,
        }
        return frames, failed_samples, diagnostics

    def _actual_timestamp_seconds(self, capture: cv2.VideoCapture) -> float:
        return round(float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0) / 1000.0, 6)

    def _capture_position_timestamp_seconds(self, capture: cv2.VideoCapture) -> float | None:
        position_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
        if position_msec <= 0:
            return None
        return round(position_msec / 1000.0, 6)

    def _analyze_frame(
        self,
        frame: np.ndarray,
        sample_index: int,
        frame_index: int,
        target_timestamp_seconds: float,
        actual_timestamp_seconds: float,
        successful_history: list[tuple[FrameMetrics, np.ndarray]],
    ) -> tuple[FrameMetrics, np.ndarray]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        timestamp = actual_timestamp_seconds

        adjacent = successful_history[-1] if successful_history else None
        if adjacent is None:
            adjacent_difference_score = None
            adjacent_sample_index = None
            adjacent_frame_index = None
            adjacent_timestamp_seconds = None
            adjacent_actual_seconds = None
        else:
            adjacent_metrics, adjacent_gray = adjacent
            adjacent_difference_score = normalized_mean_absolute_difference(adjacent_gray, gray)
            adjacent_sample_index = adjacent_metrics.sample_index
            adjacent_frame_index = adjacent_metrics.frame_index
            adjacent_timestamp_seconds = adjacent_metrics.timestamp_seconds
            adjacent_actual_seconds = round(timestamp - adjacent_metrics.timestamp_seconds, 6)

        lookback = (
            successful_history[-self.lookback_sample_offset]
            if len(successful_history) >= self.lookback_sample_offset
            else None
        )
        if lookback is None:
            lookback_difference_score = None
            lookback_sample_index = None
            lookback_frame_index = None
            lookback_timestamp_seconds = None
            lookback_actual_seconds = None
        else:
            lookback_metrics, lookback_gray = lookback
            lookback_difference_score = normalized_mean_absolute_difference(lookback_gray, gray)
            lookback_sample_index = lookback_metrics.sample_index
            lookback_frame_index = lookback_metrics.frame_index
            lookback_timestamp_seconds = lookback_metrics.timestamp_seconds
            lookback_actual_seconds = round(timestamp - lookback_metrics.timestamp_seconds, 6)

        return FrameMetrics(
            sample_index=sample_index,
            frame_index=frame_index,
            target_timestamp_seconds=target_timestamp_seconds,
            timestamp_seconds=timestamp,
            timestamp_formatted=format_duration(timestamp),
            second=int(timestamp),
            brightness_mean=float(np.mean(gray)),
            contrast_std=float(np.std(gray)),
            laplacian_variance=float(cv2.Laplacian(gray, cv2.CV_64F).var()),
            adjacent_difference_score=adjacent_difference_score,
            adjacent_sample_index=adjacent_sample_index,
            adjacent_frame_index=adjacent_frame_index,
            adjacent_timestamp_seconds=adjacent_timestamp_seconds,
            adjacent_actual_seconds=adjacent_actual_seconds,
            lookback_difference_score=lookback_difference_score,
            lookback_sample_offset=self.lookback_sample_offset,
            lookback_sample_index=lookback_sample_index,
            lookback_frame_index=lookback_frame_index,
            lookback_timestamp_seconds=lookback_timestamp_seconds,
            lookback_actual_seconds=lookback_actual_seconds,
        ), gray

    def _unsampled_tail_frame_count(
        self, total_frames: int, sampled_indices: list[int]
    ) -> int | None:
        if total_frames <= 0 or not sampled_indices:
            return None
        expected_last_frame_index = total_frames - 1
        return max(0, expected_last_frame_index - sampled_indices[-1])

    def _unsampled_tail_duration_seconds(
        self, fps: float, total_frames: int, sampled_indices: list[int]
    ) -> float | None:
        tail_frames = self._unsampled_tail_frame_count(total_frames, sampled_indices)
        if tail_frames is None or fps <= 0:
            return None
        return round(tail_frames / fps, 6)

    def _failed_tail_frame_count(
        self, failed_samples: list[SampleFailure], frames: list[FrameMetrics]
    ) -> int:
        if not failed_samples:
            return 0
        last_successful_sample = frames[-1].frame_index if frames else -1
        return sum(1 for sample in failed_samples if sample.requested_frame_index > last_successful_sample)

    def _failed_tail_duration_seconds(
        self, fps: float, failed_samples: list[SampleFailure], frames: list[FrameMetrics]
    ) -> float | None:
        if fps <= 0:
            return None
        return round(self._failed_tail_frame_count(failed_samples, frames) / fps, 6)

    def _per_second_summary(self, frames: list[FrameMetrics]) -> list[dict[str, Any]]:
        grouped: dict[int, list[FrameMetrics]] = defaultdict(list)
        for frame in frames:
            grouped[frame.second].append(frame)

        rows: list[dict[str, Any]] = []
        for second in sorted(grouped):
            items = grouped[second]
            laplacian_values = [item.laplacian_variance for item in items]
            rows.append(
                {
                    "second": second,
                    "frame_indices": [item.frame_index for item in items],
                    "sample_count": len(items),
                    "brightness_mean": mean(item.brightness_mean for item in items),
                    "contrast_mean": mean(item.contrast_std for item in items),
                    "laplacian_variance_mean": mean(laplacian_values),
                    "laplacian_variance_minimum": min(laplacian_values) if laplacian_values else None,
                    "adjacent_difference_mean": mean(
                        item.adjacent_difference_score for item in items
                    ),
                    "lookback_difference_mean": mean(
                        item.lookback_difference_score for item in items
                    ),
                }
            )
        return rows

    def _warnings(self, metadata: Any, frames: list[FrameMetrics]) -> list[str]:
        warnings: list[str] = []
        if metadata.fps <= 0:
            warnings.append("Video FPS is unavailable or zero; duration and timestamps may be inaccurate.")
        if metadata.total_frames <= 0:
            warnings.append("Video total frame count is unavailable or zero.")
        if not frames:
            warnings.append("No frames were sampled successfully.")
        return warnings


def normalized_mean_absolute_difference(previous_gray: np.ndarray, current_gray: np.ndarray) -> float:
    return float(np.mean(cv2.absdiff(previous_gray, current_gray))) / 255.0


def summarize_values(values: Any) -> dict[str, Any]:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return {
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
            "standard_deviation": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
        }

    array = np.array(numbers, dtype=float)
    return {
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "standard_deviation": float(np.std(array)),
        "p10": float(np.percentile(array, 10)),
        "p25": float(np.percentile(array, 25)),
        "p75": float(np.percentile(array, 75)),
        "p90": float(np.percentile(array, 90)),
    }


def mean(values: Any) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return float(sum(numbers) / len(numbers)) if numbers else None


def scrub_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: scrub_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_json(item) for item in value]
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value
