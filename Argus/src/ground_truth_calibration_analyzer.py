from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .ground_truth_statistics import GROUND_TRUTH_WINDOWS


RAW_TIMELINE_METRICS = [
    "adjacent_difference",
    "lookback_difference",
    "laplacian",
]


class GroundTruthCalibrationAnalyzer:
    def analyze(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        windows = [self._window_report(index, window, samples) for index, window in enumerate(GROUND_TRUTH_WINDOWS)]
        return {
            "input": "approximate",
            "calibration_decision": "pending_bryan_manual_decision",
            "metrics": RAW_TIMELINE_METRICS,
            "windows": windows,
            "summary": {
                "original_window_count": len(windows),
                "calibrated_window_count": count_calibrated_windows(windows),
                "stable_window_count": count_windows("Stable"),
                "transition_window_count": count_windows("Transition"),
                "blank_window_count": count_windows("Blank"),
                "garbage_window_count": count_windows("Garbage"),
                "total_assigned_samples": sum(window["sample_count"] for window in windows),
                "window_duration_before_calibration": round(
                    sum(window["original_duration_seconds"] for window in windows),
                    6,
                ),
                "window_duration_after_calibration": duration_after_calibration(windows),
            },
        }

    def _window_report(
        self,
        window_index: int,
        window: Any,
        samples: list[dict[str, Any]],
    ) -> dict[str, Any]:
        window_samples = [
            sample
            for sample in samples
            if window.start_seconds
            <= sample["analysis_timestamp_seconds"]
            <= window.end_seconds
        ]
        return {
            "window_index": window_index,
            "window": window.window,
            "window_type": window.type,
            "note": window.note,
            "original_start_seconds": window.start_seconds,
            "original_end_seconds": window.end_seconds,
            "original_duration_seconds": round(
                window.end_seconds - window.start_seconds,
                6,
            ),
            "calibrated_start_seconds": None,
            "calibrated_end_seconds": None,
            "calibrated_duration_seconds": None,
            "sample_count": len(window_samples),
            "samples": [sample_row(sample) for sample in window_samples],
        }


class GroundTruthCalibrationWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "calibrated_ground_truth.json"
        csv_path = self.artifacts_dir / "calibrated_ground_truth.csv"
        markdown_path = self.artifacts_dir / "calibrated_ground_truth.md"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        self._write_csv(csv_path, report)
        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        return json_path, csv_path, markdown_path

    def _write_csv(self, csv_path: Path, report: dict[str, Any]) -> None:
        fieldnames = [
            "row_type",
            "window_index",
            "window",
            "window_type",
            "original_start_seconds",
            "original_end_seconds",
            "calibrated_start_seconds",
            "calibrated_end_seconds",
            "sample_count",
            "sample_index",
            "analysis_timestamp_seconds",
            "frame_index",
            "target_frame_index",
            "target_timestamp_seconds",
            "adjacent_difference",
            "lookback_difference",
            "laplacian",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for window in report["windows"]:
                writer.writerow(window_csv_row(window))
                for sample in window["samples"]:
                    writer.writerow(
                        {
                            "row_type": "sample",
                            "window_index": window["window_index"],
                            "window": window["window"],
                            "window_type": window["window_type"],
                            "original_start_seconds": window[
                                "original_start_seconds"
                            ],
                            "original_end_seconds": window["original_end_seconds"],
                            "calibrated_start_seconds": window[
                                "calibrated_start_seconds"
                            ],
                            "calibrated_end_seconds": window[
                                "calibrated_end_seconds"
                            ],
                            **sample,
                        }
                    )

    def _to_markdown(self, report: dict[str, Any]) -> str:
        summary = report["summary"]
        lines = [
            "# Ground Truth Calibration Observation",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Original Window Count | {summary['original_window_count']} |",
            f"| Calibrated Window Count | {summary['calibrated_window_count']} |",
            f"| Stable Window Count | {summary['stable_window_count']} |",
            f"| Transition Window Count | {summary['transition_window_count']} |",
            f"| Blank Window Count | {summary['blank_window_count']} |",
            f"| Garbage Window Count | {summary['garbage_window_count']} |",
            f"| Total Assigned Samples | {summary['total_assigned_samples']} |",
            f"| Window Duration Before Calibration | {fmt(summary['window_duration_before_calibration'])} |",
            f"| Window Duration After Calibration | {fmt(summary['window_duration_after_calibration'])} |",
            "",
            "## Windows",
            "",
        ]
        for window in report["windows"]:
            lines.extend(
                [
                    f"### {window['window']} {window['window_type']}",
                    "",
                    "| Field | Value |",
                    "| --- | ---: |",
                    f"| Original Start | {fmt(window['original_start_seconds'])} |",
                    f"| Original End | {fmt(window['original_end_seconds'])} |",
                    f"| Calibrated Start | {fmt(window['calibrated_start_seconds'])} |",
                    f"| Calibrated End | {fmt(window['calibrated_end_seconds'])} |",
                    f"| Sample Count | {window['sample_count']} |",
                    "",
                    "| Sample | Analysis Timestamp | Adjacent Difference | Lookback Difference | Laplacian |",
                    "| ---: | ---: | ---: | ---: | ---: |",
                ]
            )
            for sample in window["samples"]:
                lines.append(
                    f"| {sample['sample_index']} | "
                    f"{fmt(sample['analysis_timestamp_seconds'])} | "
                    f"{fmt(sample['adjacent_difference'])} | "
                    f"{fmt(sample['lookback_difference'])} | "
                    f"{fmt(sample['laplacian'])} |"
                )
            lines.append("")
        return "\n".join(lines)


def sample_row(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_index": sample["sample_index"],
        "analysis_timestamp_seconds": sample["analysis_timestamp_seconds"],
        "frame_index": sample["frame_index"],
        "target_frame_index": sample["target_frame_index"],
        "target_timestamp_seconds": sample["target_timestamp_seconds"],
        "adjacent_difference": sample["adjacent_difference_score"],
        "lookback_difference": sample["lookback_difference_score"],
        "laplacian": sample["laplacian_variance"],
    }


def window_csv_row(window: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_type": "window",
        "window_index": window["window_index"],
        "window": window["window"],
        "window_type": window["window_type"],
        "original_start_seconds": window["original_start_seconds"],
        "original_end_seconds": window["original_end_seconds"],
        "calibrated_start_seconds": window["calibrated_start_seconds"],
        "calibrated_end_seconds": window["calibrated_end_seconds"],
        "sample_count": window["sample_count"],
    }


def count_windows(window_type: str) -> int:
    return sum(1 for window in GROUND_TRUTH_WINDOWS if window.type == window_type)


def count_calibrated_windows(windows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for window in windows
        if window["calibrated_start_seconds"] is not None
        and window["calibrated_end_seconds"] is not None
    )


def duration_after_calibration(windows: list[dict[str, Any]]) -> float | None:
    durations = [
        window["calibrated_duration_seconds"]
        for window in windows
        if window["calibrated_duration_seconds"] is not None
    ]
    if not durations:
        return None
    return round(sum(durations), 6)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
