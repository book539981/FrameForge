from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import median
from typing import Any


class StableSegmentReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(
        self,
        report: dict[str, Any],
        stable_config: dict[str, Any],
    ) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "stable_candidate_segments.json"
        markdown_path = self.artifacts_dir / "stable_candidate_segments.md"
        csv_path = self.artifacts_dir / "stable_candidate_segments.csv"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        markdown_path.write_text(
            self._to_markdown(report, stable_config),
            encoding="utf-8",
        )
        self._write_csv(csv_path, report["candidate_segments"])
        return json_path, markdown_path, csv_path

    def _to_markdown(
        self,
        report: dict[str, Any],
        stable_config: dict[str, Any],
    ) -> str:
        summary = report["summary"]
        segments = report["candidate_segments"]
        stats = self._rule_statistics(summary, segments)
        histogram = self._segment_histogram(segments)
        sorted_segments = sorted(
            segments,
            key=lambda segment: (-segment["sample_count"], segment["segment_index"]),
        )

        lines = [
            "# Stable Candidate Segments Debug Report",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Adjacent difference maximum | {fmt(stable_config['adjacent_difference_maximum'])} |",
            f"| Long lookback difference maximum | {fmt(stable_config['long_lookback_difference_maximum'])} |",
            f"| Sample Count | {summary['sample_count']} |",
            f"| Adjacent PASS | {summary['adjacent_pass_count']} |",
            f"| Lookback PASS | {summary['lookback_pass_count']} |",
            f"| Stable Candidate Samples | {summary['stable_candidate_sample_count']} |",
            f"| Candidate Segment Count | {summary['candidate_segment_count']} |",
            "",
            "## Segment Summary",
            "",
            "| Segment # | Start Sample | End Sample | Sample Count | Start Target Time | End Target Time | Target Duration | Analysis Duration |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]

        for segment in sorted_segments:
            lines.append(
                f"| {segment['segment_index']} | {segment['start_sample_index']} | "
                f"{segment['end_sample_index']} | {segment['sample_count']} | "
                f"{fmt(segment['start_target_timestamp_seconds'])} | "
                f"{fmt(segment['end_target_timestamp_seconds'])} | "
                f"{fmt(segment['target_duration_seconds'])} | "
                f"{fmt(segment['analysis_duration_seconds'])} |"
            )

        lines.extend(
            [
                "",
                "## Rule Statistics",
                "",
                "| Field | Value |",
                "| --- | ---: |",
                f"| Adjacent PASS % | {fmt_percent(stats['adjacent_pass_ratio'])} |",
                f"| Lookback PASS % | {fmt_percent(stats['lookback_pass_ratio'])} |",
                f"| Stable Candidate % | {fmt_percent(stats['stable_candidate_ratio'])} |",
                f"| Average Segment Length | {fmt(stats['average_segment_length'])} |",
                f"| Median Segment Length | {fmt(stats['median_segment_length'])} |",
                f"| Longest Segment | {fmt(stats['longest_segment'])} |",
                f"| Shortest Segment | {fmt(stats['shortest_segment'])} |",
                "",
                "## Segment Histogram",
                "",
                "| Sample Count Range | Segment Count |",
                "| --- | ---: |",
            ]
        )

        for label, count in histogram.items():
            lines.append(f"| {label} | {count} |")

        lines.append("")
        return "\n".join(lines)

    def _write_csv(self, csv_path: Path, segments: list[dict[str, Any]]) -> None:
        fieldnames = [
            "segment_index",
            "start_sample_index",
            "end_sample_index",
            "sample_count",
            "start_target_timestamp_seconds",
            "end_target_timestamp_seconds",
            "target_duration_seconds",
            "analysis_duration_seconds",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for segment in segments:
                writer.writerow({field: segment[field] for field in fieldnames})

    def _rule_statistics(
        self,
        summary: dict[str, Any],
        segments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sample_count = summary["sample_count"]
        segment_lengths = [segment["sample_count"] for segment in segments]
        return {
            "adjacent_pass_ratio": ratio(summary["adjacent_pass_count"], sample_count),
            "lookback_pass_ratio": ratio(summary["lookback_pass_count"], sample_count),
            "stable_candidate_ratio": ratio(
                summary["stable_candidate_sample_count"],
                sample_count,
            ),
            "average_segment_length": (
                sum(segment_lengths) / len(segment_lengths) if segment_lengths else None
            ),
            "median_segment_length": median(segment_lengths) if segment_lengths else None,
            "longest_segment": max(segment_lengths) if segment_lengths else None,
            "shortest_segment": min(segment_lengths) if segment_lengths else None,
        }

    def _segment_histogram(self, segments: list[dict[str, Any]]) -> dict[str, int]:
        histogram = {
            "1 sample": 0,
            "2~5 samples": 0,
            "6~10 samples": 0,
            "11~20 samples": 0,
            "21~30 samples": 0,
            "31+ samples": 0,
        }
        for segment in segments:
            sample_count = segment["sample_count"]
            if sample_count == 1:
                histogram["1 sample"] += 1
            elif 2 <= sample_count <= 5:
                histogram["2~5 samples"] += 1
            elif 6 <= sample_count <= 10:
                histogram["6~10 samples"] += 1
            elif 11 <= sample_count <= 20:
                histogram["11~20 samples"] += 1
            elif 21 <= sample_count <= 30:
                histogram["21~30 samples"] += 1
            else:
                histogram["31+ samples"] += 1
        return histogram


def ratio(part: int, total: int) -> float | None:
    return part / total if total else None


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def fmt_percent(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"
