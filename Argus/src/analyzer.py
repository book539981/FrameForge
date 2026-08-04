from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

import cv2
import numpy as np

from .video_reader import format_duration, read_metadata


@dataclass(frozen=True)
class FrameMetrics:
    frame_index: int
    timestamp_seconds: float
    timestamp_formatted: str
    second: int
    brightness_mean: float
    contrast_std: float
    laplacian_variance: float
    black_pixel_ratio: float
    top_black_rows: int
    bottom_black_rows: int


class VideoAnalyzer:
    def __init__(self, config: dict[str, Any], argus_root: Path) -> None:
        self.config = config
        self.argus_root = argus_root
        self.samples_per_second = float(config["sampling"]["samples_per_second"])
        if self.samples_per_second <= 0:
            raise ValueError("sampling.samples_per_second must be greater than zero")
        self.black_threshold = int(config["analysis"]["black_threshold"])
        self.black_row_mean_threshold = float(config["analysis"]["black_row_mean_threshold"])
        self.black_row_required_ratio = float(config["analysis"]["black_row_required_ratio"])

    def analyze(self, video_path: Path) -> dict[str, Any]:
        metadata = read_metadata(video_path)
        frame_interval = self._frame_interval(metadata.fps)
        sampled_indices = list(range(0, metadata.total_frames, frame_interval))

        frames = self._sample_frames(video_path, sampled_indices, metadata.fps)
        frame_dicts = [asdict(frame) for frame in frames]
        black_border = self._black_border_summary(frames)

        report = {
            "schema_version": "1.0",
            "video_metadata": asdict(metadata),
            "config": self.config,
            "sampling": {
                "total_frames": metadata.total_frames,
                "sampled_frames": len(frames),
                "sampling_rate": self.samples_per_second,
                "frame_interval": frame_interval,
                "first_sampled_frame_index": frames[0].frame_index if frames else None,
                "last_sampled_frame_index": frames[-1].frame_index if frames else None,
                "all_requested_frames_read": len(frames) == len(sampled_indices),
                "failed_frame_count": len(sampled_indices) - len(frames),
            },
            "frame_statistics": {
                "brightness": summarize_values(frame.brightness_mean for frame in frames),
                "contrast": summarize_values(frame.contrast_std for frame in frames),
                "laplacian_variance": summarize_values(frame.laplacian_variance for frame in frames),
                "black_pixel_ratio": summarize_values(frame.black_pixel_ratio for frame in frames),
            },
            "sampled_frames": frame_dicts,
            "per_second_summary": self._per_second_summary(frames),
            "black_border_analysis": black_border,
            "roi_recommendation": self._roi_recommendation(black_border, len(frames)),
            "warnings": self._warnings(metadata, frames),
            "errors": [],
        }
        return scrub_json(report)

    def _frame_interval(self, fps: float) -> int:
        if fps <= 0:
            return 1
        return max(1, int(round(fps / self.samples_per_second)))

    def _sample_frames(self, video_path: Path, frame_indices: list[int], fps: float) -> list[FrameMetrics]:
        capture = cv2.VideoCapture(str(video_path))
        frames: list[FrameMetrics] = []
        try:
            for frame_index in frame_indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                frames.append(self._analyze_frame(frame, frame_index, fps))
        finally:
            capture.release()
        return frames

    def _analyze_frame(self, frame: np.ndarray, frame_index: int, fps: float) -> FrameMetrics:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        timestamp = frame_index / fps if fps > 0 else 0.0
        black_pixels = gray < self.black_threshold
        top_rows, bottom_rows = self._black_row_counts(gray)

        return FrameMetrics(
            frame_index=frame_index,
            timestamp_seconds=round(timestamp, 6),
            timestamp_formatted=format_duration(timestamp),
            second=int(timestamp),
            brightness_mean=float(np.mean(gray)),
            contrast_std=float(np.std(gray)),
            laplacian_variance=float(cv2.Laplacian(gray, cv2.CV_64F).var()),
            black_pixel_ratio=float(np.mean(black_pixels)),
            top_black_rows=top_rows,
            bottom_black_rows=bottom_rows,
        )

    def _black_row_counts(self, gray: np.ndarray) -> tuple[int, int]:
        row_means = np.mean(gray, axis=1)
        row_black_ratio = np.mean(gray < self.black_threshold, axis=1)
        black_rows = (row_means <= self.black_row_mean_threshold) & (
            row_black_ratio >= self.black_row_required_ratio
        )

        top = 0
        for is_black in black_rows:
            if not is_black:
                break
            top += 1

        bottom = 0
        for is_black in reversed(black_rows):
            if not is_black:
                break
            bottom += 1

        return top, bottom

    def _black_border_summary(self, frames: list[FrameMetrics]) -> dict[str, Any]:
        return {
            "top_black_rows": summarize_values((frame.top_black_rows for frame in frames), include_mode=True),
            "bottom_black_rows": summarize_values((frame.bottom_black_rows for frame in frames), include_mode=True),
        }

    def _roi_recommendation(self, black_border: dict[str, Any], frame_count: int) -> dict[str, Any]:
        top_stats = black_border["top_black_rows"]
        bottom_stats = black_border["bottom_black_rows"]
        top = int(round(top_stats.get("median") or 0))
        bottom = int(round(bottom_stats.get("median") or 0))

        confidence = "unknown"
        if frame_count:
            top_spread = (top_stats.get("p90") or 0) - (top_stats.get("p10") or 0)
            bottom_spread = (bottom_stats.get("p90") or 0) - (bottom_stats.get("p10") or 0)
            if top == 0 and bottom == 0:
                confidence = "low"
            elif top_spread <= 2 and bottom_spread <= 2:
                confidence = "high"
            elif top_spread <= 10 and bottom_spread <= 10:
                confidence = "medium"
            else:
                confidence = "low"

        return {
            "top_crop_recommendation": top,
            "bottom_crop_recommendation": bottom,
            "confidence": confidence,
        }

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
                    "black_pixel_ratio_mean": mean(item.black_pixel_ratio for item in items),
                    "top_black_rows_median": safe_median(item.top_black_rows for item in items),
                    "bottom_black_rows_median": safe_median(item.bottom_black_rows for item in items),
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


def summarize_values(values: Any, include_mode: bool = False) -> dict[str, Any]:
    numbers = [float(value) for value in values]
    if not numbers:
        summary: dict[str, Any] = {
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
        if include_mode:
            summary["mode"] = None
        return summary

    array = np.array(numbers, dtype=float)
    summary = {
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
    if include_mode:
        counts = Counter(int(round(value)) for value in numbers)
        summary["mode"] = counts.most_common(1)[0][0]
    return summary


def mean(values: Any) -> float | None:
    numbers = [float(value) for value in values]
    return float(sum(numbers) / len(numbers)) if numbers else None


def safe_median(values: Any) -> float | None:
    numbers = [float(value) for value in values]
    return float(median(numbers)) if numbers else None


def scrub_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: scrub_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_json(item) for item in value]
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value
