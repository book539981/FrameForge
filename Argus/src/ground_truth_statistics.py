from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

from .comparison_engine import ComparisonEngine
from .spatial_comparison_processor import split_regions


METRICS = [
    "adjacent_difference",
    "lookback_difference",
    "whole_difference",
    "left_difference",
    "center_difference",
    "right_difference",
    "whole_ssim",
    "left_ssim",
    "center_ssim",
    "right_ssim",
    "laplacian",
]


@dataclass(frozen=True)
class GroundTruthWindow:
    window: str
    start_seconds: float
    end_seconds: float
    type: str
    note: str


GROUND_TRUTH_WINDOWS = [
    GroundTruthWindow("GT00", 0.0, 3.0, "Garbage", "起始垃圾頁"),
    GroundTruthWindow("GT01", 3.0, 8.0, "Stable", "P1"),
    GroundTruthWindow("GT02", 8.0, 10.0, "Transition", "P1 -> P2"),
    GroundTruthWindow("GT03", 10.0, 15.0, "Stable", "P2"),
    GroundTruthWindow("GT04", 15.0, 17.0, "Transition", "P2 -> P3"),
    GroundTruthWindow("GT05", 17.0, 22.0, "Stable", "P3"),
    GroundTruthWindow("GT06", 22.0, 23.0, "Transition", "P3 -> Blank"),
    GroundTruthWindow("GT07", 23.0, 24.0, "Blank", "Blank"),
    GroundTruthWindow("GT08", 24.0, 25.0, "Transition", "Blank -> P4"),
    GroundTruthWindow("GT09", 25.0, 30.0, "Stable", "P4"),
    GroundTruthWindow("GT10", 30.0, 32.0, "Transition", "P4 -> Blank"),
    GroundTruthWindow("GT11", 32.0, 33.0, "Blank", "Blank"),
    GroundTruthWindow("GT12", 33.0, 35.0, "Transition", "Blank -> P5"),
    GroundTruthWindow("GT13", 35.0, 40.0, "Stable", "P5"),
    GroundTruthWindow("GT14", 42.0, 47.0, "Stable", "P6"),
    GroundTruthWindow("GT15", 49.0, 54.0, "Stable", "P7"),
    GroundTruthWindow("GT16", 56.0, 61.0, "Stable", "P8"),
    GroundTruthWindow("GT17", 63.0, 68.0, "Stable", "P9"),
    GroundTruthWindow("GT18", 70.0, 75.0, "Stable", "P10"),
    GroundTruthWindow("GT19", 77.0, 82.0, "Stable", "P11"),
    GroundTruthWindow("GT20", 84.0, 89.0, "Stable", "P12"),
    GroundTruthWindow("GT21", 91.0, 96.0, "Stable", "P13"),
    GroundTruthWindow("GT22", 98.0, 103.0, "Stable", "P14"),
    GroundTruthWindow("GT23", 105.0, 108.5, "Stable", "最後穩定頁"),
]


class GroundTruthStatistics:
    def __init__(self, comparison_engine: ComparisonEngine) -> None:
        self.comparison_engine = comparison_engine

    def build(
        self,
        samples: list[dict[str, Any]],
        sample_grays: dict[int, np.ndarray],
    ) -> dict[str, Any]:
        assignments = self._assign_samples(samples)
        sample_rows = self._sample_rows(samples, sample_grays, assignments)
        window_reports = self._window_reports(sample_rows)
        category_reports = self._category_reports(sample_rows)
        separation_report = self._separation_report(category_reports)
        assigned_count = sum(1 for row in sample_rows if row["window"] is not None)
        unassigned_count = len(sample_rows) - assigned_count

        return {
            "ground_truth_windows": [
                asdict(window) for window in GROUND_TRUTH_WINDOWS
            ],
            "metrics": METRICS,
            "sample_assignments": sample_rows,
            "windows": window_reports,
            "categories": category_reports,
            "metric_separation": separation_report,
            "summary": {
                "window_count": len(GROUND_TRUTH_WINDOWS),
                "stable_window_count": count_windows("Stable"),
                "transition_window_count": count_windows("Transition"),
                "blank_window_count": count_windows("Blank"),
                "garbage_window_count": count_windows("Garbage"),
                "total_samples": len(samples),
                "assigned_sample_count": assigned_count,
                "unassigned_sample_count": unassigned_count,
                "metrics_count": len(METRICS),
                "sample_window_membership_maximum": max(
                    (len(assignment["windows"]) for assignment in assignments),
                    default=0,
                ),
            },
        }

    def _assign_samples(
        self,
        samples: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        assignments: list[dict[str, Any]] = []
        for sample in samples:
            timestamp = sample["analysis_timestamp_seconds"]
            matched_windows = [
                window
                for window in GROUND_TRUTH_WINDOWS
                if window.start_seconds <= timestamp <= window.end_seconds
            ]
            if len(matched_windows) > 1:
                names = ", ".join(window.window for window in matched_windows)
                raise ValueError(
                    f"sample {sample['sample_index']} belongs to multiple Ground Truth Windows: {names}"
                )
            assignments.append(
                {
                    "sample_index": sample["sample_index"],
                    "windows": [window.window for window in matched_windows],
                    "window": matched_windows[0] if matched_windows else None,
                }
            )
        return assignments

    def _sample_rows(
        self,
        samples: list[dict[str, Any]],
        sample_grays: dict[int, np.ndarray],
        assignments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        assignment_by_sample = {
            assignment["sample_index"]: assignment for assignment in assignments
        }
        rows: list[dict[str, Any]] = []
        previous_window = None
        previous_gray = None

        for sample in samples:
            assignment = assignment_by_sample[sample["sample_index"]]
            window = assignment["window"]
            gray = sample_grays[sample["sample_index"]]
            spatial = (
                self._spatial_compare(previous_gray, gray)
                if previous_gray is not None
                and window is not None
                and previous_window is not None
                and previous_window.window == window.window
                else empty_spatial_comparison()
            )
            rows.append(
                {
                    "sample_index": sample["sample_index"],
                    "window": window.window if window else None,
                    "type": window.type if window else None,
                    "note": window.note if window else None,
                    "analysis_timestamp_seconds": sample[
                        "analysis_timestamp_seconds"
                    ],
                    "frame_index": sample["frame_index"],
                    "target_frame_index": sample["target_frame_index"],
                    "target_timestamp_seconds": sample["target_timestamp_seconds"],
                    "adjacent_difference": sample["adjacent_difference_score"],
                    "lookback_difference": sample["lookback_difference_score"],
                    "whole_difference": spatial["whole"]["difference"],
                    "left_difference": spatial["left"]["difference"],
                    "center_difference": spatial["center"]["difference"],
                    "right_difference": spatial["right"]["difference"],
                    "whole_ssim": spatial["whole"]["ssim"],
                    "left_ssim": spatial["left"]["ssim"],
                    "center_ssim": spatial["center"]["ssim"],
                    "right_ssim": spatial["right"]["ssim"],
                    "laplacian": sample["laplacian_variance"],
                    "window_membership_count": len(assignment["windows"]),
                }
            )
            previous_window = window
            previous_gray = gray

        return rows

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

    def _window_reports(self, sample_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for window in GROUND_TRUTH_WINDOWS:
            rows = [row for row in sample_rows if row["window"] == window.window]
            reports.append(
                {
                    **asdict(window),
                    "sample_count": len(rows),
                    "statistics": metric_statistics(rows),
                }
            )
        return reports

    def _category_reports(
        self,
        sample_rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        reports: dict[str, dict[str, Any]] = {}
        for category in ("Stable", "Transition", "Blank", "Garbage"):
            rows = [row for row in sample_rows if row["type"] == category]
            reports[category] = {
                "sample_count": len(rows),
                "statistics": metric_statistics(rows),
            }
        return reports

    def _separation_report(
        self,
        category_reports: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        stable_stats = category_reports["Stable"]["statistics"]
        transition_stats = category_reports["Transition"]["statistics"]
        rows: list[dict[str, Any]] = []
        for metric in METRICS:
            rows.append(
                {
                    "metric": metric,
                    "stable_median": stable_stats[metric]["median"],
                    "transition_median": transition_stats[metric]["median"],
                    "stable_p90": stable_stats[metric]["p90"],
                    "transition_p10": transition_stats[metric]["p10"],
                    "note": "",
                }
            )
        return rows


class GroundTruthStatisticsWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "ground_truth_statistics.json"
        csv_path = self.artifacts_dir / "ground_truth_statistics.csv"
        markdown_path = self.artifacts_dir / "ground_truth_statistics.md"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        self._write_csv(csv_path, report)
        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        return json_path, csv_path, markdown_path

    def _write_csv(self, csv_path: Path, report: dict[str, Any]) -> None:
        fieldnames = [
            "section",
            "window",
            "type",
            "metric",
            "count",
            "minimum",
            "maximum",
            "average",
            "median",
            "std",
            "p10",
            "p25",
            "p75",
            "p90",
            "stable_median",
            "transition_median",
            "stable_p90",
            "transition_p10",
            "note",
        ]
        rows: list[dict[str, Any]] = []
        for window in report["windows"]:
            for metric, stats in window["statistics"].items():
                rows.append(
                    {
                        "section": "window",
                        "window": window["window"],
                        "type": window["type"],
                        "metric": metric,
                        **stats,
                        "note": window["note"],
                    }
                )
        for category, category_report in report["categories"].items():
            for metric, stats in category_report["statistics"].items():
                rows.append(
                    {
                        "section": "category",
                        "window": "",
                        "type": category,
                        "metric": metric,
                        **stats,
                        "note": "",
                    }
                )
        for row in report["metric_separation"]:
            rows.append(
                {
                    "section": "separation",
                    "window": "",
                    "type": "Stable_vs_Transition",
                    **row,
                }
            )

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field) for field in fieldnames})

    def _to_markdown(self, report: dict[str, Any]) -> str:
        summary = report["summary"]
        lines = [
            "# Ground Truth Statistics",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Window Count | {summary['window_count']} |",
            f"| Stable Window Count | {summary['stable_window_count']} |",
            f"| Transition Window Count | {summary['transition_window_count']} |",
            f"| Blank Window Count | {summary['blank_window_count']} |",
            f"| Garbage Window Count | {summary['garbage_window_count']} |",
            f"| Total Samples | {summary['total_samples']} |",
            f"| Assigned Samples | {summary['assigned_sample_count']} |",
            f"| Unassigned Samples | {summary['unassigned_sample_count']} |",
            f"| Metrics Count | {summary['metrics_count']} |",
            f"| Sample Window Membership Maximum | {summary['sample_window_membership_maximum']} |",
            "",
            "## Window Statistics",
            "",
        ]
        for window in report["windows"]:
            lines.extend(
                [
                    f"### {window['window']} {window['type']}",
                    "",
                    f"Note: {window['note']}",
                    "",
                    f"Sample Count: {window['sample_count']}",
                    "",
                    stats_table(window["statistics"]),
                    "",
                ]
            )
        lines.extend(["## Category Summary", ""])
        for category, category_report in report["categories"].items():
            lines.extend(
                [
                    f"### {category}",
                    "",
                    f"Sample Count: {category_report['sample_count']}",
                    "",
                    stats_table(category_report["statistics"]),
                    "",
                ]
            )
        lines.extend(
            [
                "## Metric Separation Report",
                "",
                "| Metric | Stable Median | Transition Median | Stable P90 | Transition P10 | Note |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in report["metric_separation"]:
            lines.append(
                f"| {row['metric']} | {fmt(row['stable_median'])} | "
                f"{fmt(row['transition_median'])} | {fmt(row['stable_p90'])} | "
                f"{fmt(row['transition_p10'])} | {row['note']} |"
            )
        lines.append("")
        return "\n".join(lines)


def metric_statistics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    return {metric: statistics(row[metric] for row in rows) for metric in METRICS}


def statistics(values: Any) -> dict[str, float | int | None]:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return empty_statistics()
    return {
        "count": len(numbers),
        "minimum": min(numbers),
        "maximum": max(numbers),
        "average": sum(numbers) / len(numbers),
        "median": median(numbers),
        "std": float(np.std(np.array(numbers, dtype=np.float64), ddof=0)),
        "p10": percentile(numbers, 10),
        "p25": percentile(numbers, 25),
        "p75": percentile(numbers, 75),
        "p90": percentile(numbers, 90),
    }


def percentile(values: list[float], percent: float) -> float:
    return float(np.percentile(np.array(values, dtype=np.float64), percent))


def empty_statistics() -> dict[str, None | int]:
    return {
        "count": 0,
        "minimum": None,
        "maximum": None,
        "average": None,
        "median": None,
        "std": None,
        "p10": None,
        "p25": None,
        "p75": None,
        "p90": None,
    }


def empty_spatial_comparison() -> dict[str, dict[str, None]]:
    return {
        "whole": {"difference": None, "ssim": None},
        "left": {"difference": None, "ssim": None},
        "center": {"difference": None, "ssim": None},
        "right": {"difference": None, "ssim": None},
    }


def count_windows(category: str) -> int:
    return sum(1 for window in GROUND_TRUTH_WINDOWS if window.type == category)


def stats_table(statistics_by_metric: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| Metric | Count | Min | Max | Average | Median | Std | P10 | P25 | P75 | P90 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric in METRICS:
        stats = statistics_by_metric[metric]
        lines.append(
            f"| {metric} | {stats['count']} | {fmt(stats['minimum'])} | "
            f"{fmt(stats['maximum'])} | {fmt(stats['average'])} | "
            f"{fmt(stats['median'])} | {fmt(stats['std'])} | "
            f"{fmt(stats['p10'])} | {fmt(stats['p25'])} | "
            f"{fmt(stats['p75'])} | {fmt(stats['p90'])} |"
        )
    return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
