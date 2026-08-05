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
    target_grid_index: int
    target_frame_index: int
    frame_index: int
    target_timestamp_seconds: float
    analysis_timestamp_seconds: float
    analysis_timestamp_formatted: str
    analysis_second: int
    brightness_mean: float
    contrast_std: float
    laplacian_variance: float
    adjacent_difference_score: float | None
    adjacent_sample_index: int | None
    adjacent_frame_index: int | None
    adjacent_analysis_timestamp_seconds: float | None
    adjacent_analysis_delta_seconds: float | None
    lookback_difference_score: float | None
    lookback_sample_offset: int
    lookback_sample_index: int | None
    lookback_frame_index: int | None
    lookback_analysis_timestamp_seconds: float | None
    lookback_analysis_delta_seconds: float | None


@dataclass(frozen=True)
class SampleFailure:
    target_grid_index: int
    target_timestamp_seconds: float
    target_frame_index: int
    capture_position_frames: float


class VideoAnalyzer:
    def __init__(self, config: dict[str, Any], argus_root: Path) -> None:
        self.config = config
        self.argus_root = argus_root
        self.sample_grays: dict[int, np.ndarray] = {}
        self.samples_per_second = float(config["sampling"]["samples_per_second"])
        if self.samples_per_second <= 0:
            raise ValueError("sampling.samples_per_second must be greater than zero")
        self.lookback_sample_offset = int(config["analysis"]["lookback_sample_offset"])
        if self.lookback_sample_offset <= 0:
            raise ValueError("analysis.lookback_sample_offset must be greater than zero")

    def analyze(self, video_path: Path) -> dict[str, Any]:
        metadata = read_metadata(video_path)
        sample_period_seconds = 1.0 / self.samples_per_second
        target_grid = self._target_grid(
            duration_seconds=metadata.duration_seconds,
            sample_period_seconds=sample_period_seconds,
            total_frames=metadata.total_frames,
        )

        frames, failed_samples, reader_diagnostics = self._sample_frames(
            video_path=video_path,
            metadata_total_frames=metadata.total_frames,
            duration_seconds=metadata.duration_seconds,
            target_grid=target_grid,
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
                "expected_sample_count": len(target_grid),
                "sampling_method": "uniform_analysis_timeline",
                "analysis_timeline_definition": "FF standardized analysis timeline: frame_index / (total_frames - 1) * duration_seconds.",
                "target_timestamp_seconds_definition": "Fixed analysis time grid target: target_grid_index * sample_period_seconds.",
                "target_frame_index_definition": "round(target_timestamp_seconds / duration_seconds * (total_frames - 1)).",
                "sampling_rate": self.samples_per_second,
                "sample_period_seconds": sample_period_seconds,
                "first_sampled_frame_index": frames[0].frame_index if frames else None,
                "last_sampled_frame_index": frames[-1].frame_index if frames else None,
                "all_expected_samples_created": len(frames) == len(target_grid),
                "first_requested_frame_index": sampled_indices[0] if sampled_indices else None,
                "last_requested_frame_index": sampled_indices[-1] if sampled_indices else None,
                "first_successful_sample_frame_index": frames[0].frame_index if frames else None,
                "last_successful_sample_frame_index": frames[-1].frame_index if frames else None,
                "first_failed_sample_frame_index": failed_samples[0].target_frame_index
                if failed_samples
                else None,
                "last_failed_sample_frame_index": failed_samples[-1].target_frame_index
                if failed_samples
                else None,
                "unsampled_tail_frame_count": self._unsampled_tail_frame_count(
                    metadata.total_frames, sampled_indices
                ),
                "unsampled_tail_duration_seconds": self._unsampled_tail_duration_seconds(
                    metadata.duration_seconds, metadata.total_frames, sampled_indices
                ),
                "failed_tail_frame_count": self._failed_tail_frame_count(failed_samples, frames),
                "failed_tail_duration_seconds": self._failed_tail_duration_seconds(
                    metadata.duration_seconds, metadata.total_frames, failed_samples, frames
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
        self,
        video_path: Path,
        metadata_total_frames: int,
        duration_seconds: float,
        target_grid: list[dict[str, float | int]],
    ) -> tuple[list[FrameMetrics], list[SampleFailure], dict[str, Any]]:
        capture = cv2.VideoCapture(str(video_path))
        self.sample_grays = {}
        frames: list[FrameMetrics] = []
        failed_samples: list[SampleFailure] = []
        decoded_frame_count = 0
        decode_attempt_count = 0
        first_failed_frame_index = None
        first_failed_analysis_timestamp_seconds = None
        capture_position_frames_at_failure = None
        last_decoded_analysis_timestamp_seconds = None
        successful_history: list[tuple[FrameMetrics, np.ndarray]] = []
        next_target_grid_index = 0
        try:
            while True:
                ok, frame = capture.read()
                decode_attempt_count += 1
                if not ok or frame is None:
                    first_failed_frame_index = decoded_frame_count
                    capture_position_frames_at_failure = float(
                        capture.get(cv2.CAP_PROP_POS_FRAMES) or 0.0
                    )
                    first_failed_analysis_timestamp_seconds = self._analysis_timestamp_seconds(
                        frame_index=first_failed_frame_index,
                        total_frames=metadata_total_frames,
                        duration_seconds=duration_seconds,
                    )
                    break

                frame_index = decoded_frame_count
                decoded_frame_count += 1
                analysis_timestamp = self._analysis_timestamp_seconds(
                    frame_index=frame_index,
                    total_frames=metadata_total_frames,
                    duration_seconds=duration_seconds,
                )
                last_decoded_analysis_timestamp_seconds = analysis_timestamp
                if next_target_grid_index < len(target_grid):
                    target = target_grid[next_target_grid_index]
                    target_frame_index = int(target["target_frame_index"])
                else:
                    target = None
                    target_frame_index = metadata_total_frames + 1
                if target is not None and frame_index >= target_frame_index:
                    target_timestamp = float(target["target_timestamp_seconds"])
                    sample_index = len(frames)
                    metrics, gray = self._analyze_frame(
                        frame=frame,
                        sample_index=sample_index,
                        target_grid_index=int(target["target_grid_index"]),
                        target_frame_index=target_frame_index,
                        frame_index=frame_index,
                        target_timestamp_seconds=target_timestamp,
                        analysis_timestamp_seconds=analysis_timestamp,
                        successful_history=successful_history,
                    )
                    frames.append(metrics)
                    self.sample_grays[sample_index] = gray
                    successful_history.append((metrics, gray))
                    next_target_grid_index += 1
                    while (
                        next_target_grid_index < len(target_grid)
                        and int(target_grid[next_target_grid_index]["target_frame_index"])
                        <= frame_index
                    ):
                        next_target_grid_index += 1
        finally:
            capture.release()

        if first_failed_frame_index is not None and first_failed_frame_index < metadata_total_frames:
            while next_target_grid_index < len(target_grid):
                target = target_grid[next_target_grid_index]
                failed_samples.append(
                    SampleFailure(
                        target_grid_index=int(target["target_grid_index"]),
                        target_timestamp_seconds=float(target["target_timestamp_seconds"]),
                        target_frame_index=int(target["target_frame_index"]),
                        capture_position_frames=capture_position_frames_at_failure or 0.0,
                    )
                )
                next_target_grid_index += 1

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
            self._frame_count_analysis_duration(
                frame_count=missing_tail_frame_count,
                total_frames=metadata_total_frames,
                duration_seconds=duration_seconds,
            )
            if missing_tail_frame_count is not None
            else None
        )

        diagnostics = {
            "metadata_total_frames": metadata_total_frames,
            "metadata_duration_seconds": duration_seconds,
            "decode_attempt_count": decode_attempt_count,
            "decoded_frame_count": decoded_frame_count,
            "normal_eof_count": normal_eof_count,
            "unexpected_decode_failure_count": unexpected_decode_failure_count,
            "last_successful_frame_index": last_successful_frame_index,
            "last_successful_analysis_timestamp_seconds": last_decoded_analysis_timestamp_seconds,
            "first_failed_frame_index": first_failed_frame_index,
            "first_failed_analysis_timestamp_seconds": first_failed_analysis_timestamp_seconds,
            "capture_position_frames_at_failure": capture_position_frames_at_failure,
            "expected_last_frame_index": expected_last_frame_index,
            "missing_tail_frame_count": missing_tail_frame_count,
            "missing_tail_duration_seconds": missing_tail_duration_seconds,
        }
        return frames, failed_samples, diagnostics

    def _target_grid(
        self,
        duration_seconds: float,
        sample_period_seconds: float,
        total_frames: int,
    ) -> list[dict[str, float | int]]:
        if duration_seconds < 0 or sample_period_seconds <= 0 or total_frames <= 0:
            return []

        target_grid: list[dict[str, float | int]] = []
        target_grid_index = 0
        sample_epsilon = 1e-9
        while target_grid_index * sample_period_seconds <= duration_seconds + sample_epsilon:
            target_timestamp = round(target_grid_index * sample_period_seconds, 6)
            target_frame_index = self._target_frame_index(
                target_timestamp_seconds=target_timestamp,
                duration_seconds=duration_seconds,
                total_frames=total_frames,
            )
            target_grid.append(
                {
                    "target_grid_index": target_grid_index,
                    "target_timestamp_seconds": target_timestamp,
                    "target_frame_index": target_frame_index,
                }
            )
            target_grid_index += 1
        return target_grid

    def _target_frame_index(
        self,
        target_timestamp_seconds: float,
        duration_seconds: float,
        total_frames: int,
    ) -> int:
        if duration_seconds <= 0 or total_frames <= 1:
            return 0
        return int(round(target_timestamp_seconds / duration_seconds * (total_frames - 1)))

    def _analysis_timestamp_seconds(
        self,
        frame_index: int,
        total_frames: int,
        duration_seconds: float,
    ) -> float:
        if total_frames <= 1:
            return 0.0
        return round(frame_index / (total_frames - 1) * duration_seconds, 6)

    def _analyze_frame(
        self,
        frame: np.ndarray,
        sample_index: int,
        target_grid_index: int,
        target_frame_index: int,
        frame_index: int,
        target_timestamp_seconds: float,
        analysis_timestamp_seconds: float,
        successful_history: list[tuple[FrameMetrics, np.ndarray]],
    ) -> tuple[FrameMetrics, np.ndarray]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        analysis_timestamp = analysis_timestamp_seconds

        adjacent = successful_history[-1] if successful_history else None
        if adjacent is None:
            adjacent_difference_score = None
            adjacent_sample_index = None
            adjacent_frame_index = None
            adjacent_analysis_timestamp_seconds = None
            adjacent_analysis_delta_seconds = None
        else:
            adjacent_metrics, adjacent_gray = adjacent
            adjacent_difference_score = normalized_mean_absolute_difference(adjacent_gray, gray)
            adjacent_sample_index = adjacent_metrics.sample_index
            adjacent_frame_index = adjacent_metrics.frame_index
            adjacent_analysis_timestamp_seconds = adjacent_metrics.analysis_timestamp_seconds
            adjacent_analysis_delta_seconds = round(
                analysis_timestamp - adjacent_metrics.analysis_timestamp_seconds, 6
            )

        lookback = (
            successful_history[-self.lookback_sample_offset]
            if len(successful_history) >= self.lookback_sample_offset
            else None
        )
        if lookback is None:
            lookback_difference_score = None
            lookback_sample_index = None
            lookback_frame_index = None
            lookback_analysis_timestamp_seconds = None
            lookback_analysis_delta_seconds = None
        else:
            lookback_metrics, lookback_gray = lookback
            lookback_difference_score = normalized_mean_absolute_difference(lookback_gray, gray)
            lookback_sample_index = lookback_metrics.sample_index
            lookback_frame_index = lookback_metrics.frame_index
            lookback_analysis_timestamp_seconds = lookback_metrics.analysis_timestamp_seconds
            lookback_analysis_delta_seconds = round(
                analysis_timestamp - lookback_metrics.analysis_timestamp_seconds, 6
            )

        return FrameMetrics(
            sample_index=sample_index,
            target_grid_index=target_grid_index,
            target_frame_index=target_frame_index,
            frame_index=frame_index,
            target_timestamp_seconds=target_timestamp_seconds,
            analysis_timestamp_seconds=analysis_timestamp,
            analysis_timestamp_formatted=format_duration(analysis_timestamp),
            analysis_second=int(analysis_timestamp),
            brightness_mean=float(np.mean(gray)),
            contrast_std=float(np.std(gray)),
            laplacian_variance=float(cv2.Laplacian(gray, cv2.CV_64F).var()),
            adjacent_difference_score=adjacent_difference_score,
            adjacent_sample_index=adjacent_sample_index,
            adjacent_frame_index=adjacent_frame_index,
            adjacent_analysis_timestamp_seconds=adjacent_analysis_timestamp_seconds,
            adjacent_analysis_delta_seconds=adjacent_analysis_delta_seconds,
            lookback_difference_score=lookback_difference_score,
            lookback_sample_offset=self.lookback_sample_offset,
            lookback_sample_index=lookback_sample_index,
            lookback_frame_index=lookback_frame_index,
            lookback_analysis_timestamp_seconds=lookback_analysis_timestamp_seconds,
            lookback_analysis_delta_seconds=lookback_analysis_delta_seconds,
        ), gray

    def _unsampled_tail_frame_count(
        self, total_frames: int, sampled_indices: list[int]
    ) -> int | None:
        if total_frames <= 0 or not sampled_indices:
            return None
        expected_last_frame_index = total_frames - 1
        return max(0, expected_last_frame_index - sampled_indices[-1])

    def _unsampled_tail_duration_seconds(
        self, duration_seconds: float, total_frames: int, sampled_indices: list[int]
    ) -> float | None:
        tail_frames = self._unsampled_tail_frame_count(total_frames, sampled_indices)
        if tail_frames is None:
            return None
        return self._frame_count_analysis_duration(
            frame_count=tail_frames,
            total_frames=total_frames,
            duration_seconds=duration_seconds,
        )

    def _failed_tail_frame_count(
        self, failed_samples: list[SampleFailure], frames: list[FrameMetrics]
    ) -> int:
        if not failed_samples:
            return 0
        last_successful_sample = frames[-1].frame_index if frames else -1
        return sum(1 for sample in failed_samples if sample.target_frame_index > last_successful_sample)

    def _failed_tail_duration_seconds(
        self,
        duration_seconds: float,
        total_frames: int,
        failed_samples: list[SampleFailure],
        frames: list[FrameMetrics],
    ) -> float | None:
        return self._frame_count_analysis_duration(
            frame_count=self._failed_tail_frame_count(failed_samples, frames),
            total_frames=total_frames,
            duration_seconds=duration_seconds,
        )

    def _frame_count_analysis_duration(
        self,
        frame_count: int,
        total_frames: int,
        duration_seconds: float,
    ) -> float | None:
        if total_frames <= 1:
            return None
        return round(frame_count / (total_frames - 1) * duration_seconds, 6)

    def _per_second_summary(self, frames: list[FrameMetrics]) -> list[dict[str, Any]]:
        grouped: dict[int, list[FrameMetrics]] = defaultdict(list)
        for frame in frames:
            grouped[frame.analysis_second].append(frame)

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
