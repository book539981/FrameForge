from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .comparison_engine import ComparisonEngine


OBSERVATION_START_TIME_SECONDS = 6.8
OBSERVATION_END_TIME_SECONDS = 9.2
OBSERVATION_SAMPLES_PER_SECOND = 10


class TransitionObservation:
    def __init__(self, comparison_engine: ComparisonEngine) -> None:
        self.comparison_engine = comparison_engine

    def observe(
        self,
        video_path: Path,
        total_frames: int,
        duration_seconds: float,
        lookback_sample_offset: int,
    ) -> dict[str, Any]:
        sample_period_seconds = 1.0 / OBSERVATION_SAMPLES_PER_SECOND
        targets = observation_targets(
            start_time_seconds=OBSERVATION_START_TIME_SECONDS,
            end_time_seconds=OBSERVATION_END_TIME_SECONDS,
            sample_period_seconds=sample_period_seconds,
            total_frames=total_frames,
            duration_seconds=duration_seconds,
        )
        rows: list[dict[str, Any]] = []
        gray_history: list[np.ndarray] = []
        next_target_index = 0

        capture = cv2.VideoCapture(str(video_path))
        try:
            frame_index = 0
            while next_target_index < len(targets):
                ok, frame = capture.read()
                if not ok or frame is None:
                    break

                target = targets[next_target_index]
                if frame_index >= target["target_frame_index"]:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    previous_gray = gray_history[-1] if gray_history else None
                    lookback_gray = (
                        gray_history[-lookback_sample_offset]
                        if len(gray_history) >= lookback_sample_offset
                        else None
                    )

                    adjacent = (
                        self._spatial_compare(previous_gray, gray)
                        if previous_gray is not None
                        else empty_spatial_comparison()
                    )
                    lookback = (
                        self.comparison_engine.compare(lookback_gray, gray)
                        if lookback_gray is not None
                        else None
                    )

                    row = {
                        "sample_index": len(rows),
                        "target_timestamp_seconds": target["target_timestamp_seconds"],
                        "analysis_timestamp_seconds": analysis_timestamp_seconds(
                            frame_index=frame_index,
                            total_frames=total_frames,
                            duration_seconds=duration_seconds,
                        ),
                        "frame_index": frame_index,
                        "adjacent_difference_score": adjacent["whole"]["difference"],
                        "lookback_difference_score": lookback["difference_score"]
                        if lookback is not None
                        else None,
                        "whole_difference": adjacent["whole"]["difference"],
                        "left_difference": adjacent["left"]["difference"],
                        "center_difference": adjacent["center"]["difference"],
                        "right_difference": adjacent["right"]["difference"],
                        "whole_ssim": adjacent["whole"]["ssim"],
                        "left_ssim": adjacent["left"]["ssim"],
                        "center_ssim": adjacent["center"]["ssim"],
                        "right_ssim": adjacent["right"]["ssim"],
                        "laplacian_variance": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                    }
                    rows.append(row)
                    gray_history.append(gray)
                    next_target_index += 1

                frame_index += 1
        finally:
            capture.release()

        return {
            "observation": {
                "start_time_seconds": OBSERVATION_START_TIME_SECONDS,
                "end_time_seconds": OBSERVATION_END_TIME_SECONDS,
                "duration_seconds": round(
                    OBSERVATION_END_TIME_SECONDS - OBSERVATION_START_TIME_SECONDS,
                    6,
                ),
                "samples_per_second": OBSERVATION_SAMPLES_PER_SECOND,
                "sample_period_seconds": sample_period_seconds,
                "lookback_sample_offset": lookback_sample_offset,
            },
            "samples": rows,
            "summary": summary(rows),
        }

    def _spatial_compare(
        self,
        previous_gray: np.ndarray,
        current_gray: np.ndarray,
    ) -> dict[str, dict[str, float]]:
        previous_regions = split_regions(previous_gray)
        current_regions = split_regions(current_gray)
        comparisons: dict[str, dict[str, float]] = {}
        for region_name in ("whole", "left", "center", "right"):
            result = self.comparison_engine.compare(
                previous_regions[region_name],
                current_regions[region_name],
            )
            comparisons[region_name] = {
                "difference": result["difference_score"],
                "ssim": result["ssim_score"],
            }
        return comparisons


class TransitionObservationWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "transition_observation.json"
        csv_path = self.artifacts_dir / "transition_observation.csv"
        markdown_path = self.artifacts_dir / "transition_observation.md"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        self._write_csv(csv_path, report["samples"])
        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        return json_path, csv_path, markdown_path

    def _write_csv(self, csv_path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames = [
            "sample_index",
            "analysis_timestamp_seconds",
            "target_timestamp_seconds",
            "frame_index",
            "adjacent_difference_score",
            "lookback_difference_score",
            "whole_difference",
            "left_difference",
            "center_difference",
            "right_difference",
            "whole_ssim",
            "left_ssim",
            "center_ssim",
            "right_ssim",
            "laplacian_variance",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row[field] for field in fieldnames})

    def _to_markdown(self, report: dict[str, Any]) -> str:
        observation = report["observation"]
        stats = report["summary"]["statistics"]
        lines = [
            "# Transition Observation Facts",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Sample Count | {report['summary']['sample_count']} |",
            f"| Duration | {fmt(observation['duration_seconds'])} |",
            f"| Sampling Rate | {observation['samples_per_second']} |",
            f"| Start Time | {fmt(observation['start_time_seconds'])} |",
            f"| End Time | {fmt(observation['end_time_seconds'])} |",
            "",
            "## Statistics",
            "",
            "| Field | Minimum | Maximum |",
            "| --- | ---: | ---: |",
        ]
        for field, values in stats.items():
            lines.append(f"| {field} | {fmt(values['minimum'])} | {fmt(values['maximum'])} |")
        lines.append("")
        return "\n".join(lines)


def observation_targets(
    start_time_seconds: float,
    end_time_seconds: float,
    sample_period_seconds: float,
    total_frames: int,
    duration_seconds: float,
) -> list[dict[str, float | int]]:
    targets: list[dict[str, float | int]] = []
    index = 0
    epsilon = 1e-9
    while start_time_seconds + index * sample_period_seconds <= end_time_seconds + epsilon:
        target_timestamp = round(start_time_seconds + index * sample_period_seconds, 6)
        targets.append(
            {
                "target_timestamp_seconds": target_timestamp,
                "target_frame_index": target_frame_index(
                    target_timestamp_seconds=target_timestamp,
                    duration_seconds=duration_seconds,
                    total_frames=total_frames,
                ),
            }
        )
        index += 1
    return targets


def target_frame_index(
    target_timestamp_seconds: float,
    duration_seconds: float,
    total_frames: int,
) -> int:
    if duration_seconds <= 0 or total_frames <= 1:
        return 0
    return int(round(target_timestamp_seconds / duration_seconds * (total_frames - 1)))


def analysis_timestamp_seconds(
    frame_index: int,
    total_frames: int,
    duration_seconds: float,
) -> float:
    if total_frames <= 1:
        return 0.0
    return round(frame_index / (total_frames - 1) * duration_seconds, 6)


def split_regions(gray: np.ndarray) -> dict[str, np.ndarray]:
    width = gray.shape[1]
    first_cut = width // 3
    second_cut = (width * 2) // 3
    return {
        "whole": gray,
        "left": gray[:, :first_cut],
        "center": gray[:, first_cut:second_cut],
        "right": gray[:, second_cut:],
    }


def empty_spatial_comparison() -> dict[str, dict[str, None]]:
    return {
        "whole": {"difference": None, "ssim": None},
        "left": {"difference": None, "ssim": None},
        "center": {"difference": None, "ssim": None},
        "right": {"difference": None, "ssim": None},
    }


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "adjacent_difference_score",
        "lookback_difference_score",
        "whole_difference",
        "left_difference",
        "center_difference",
        "right_difference",
        "whole_ssim",
        "left_ssim",
        "center_ssim",
        "right_ssim",
        "laplacian_variance",
    ]
    return {
        "sample_count": len(rows),
        "statistics": {field: min_max(row[field] for row in rows) for field in fields},
    }


def min_max(values: Any) -> dict[str, float | None]:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return {"minimum": None, "maximum": None}
    return {"minimum": min(numbers), "maximum": max(numbers)}


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
