from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class AnchorComparisonReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "anchor_comparison.json"
        markdown_path = self.artifacts_dir / "anchor_comparison.md"
        csv_path = self.artifacts_dir / "anchor_comparison.csv"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        self._write_csv(csv_path, report["sample_comparisons"])
        return json_path, markdown_path, csv_path

    def _to_markdown(self, report: dict[str, Any]) -> str:
        comparisons_by_segment: dict[int, list[dict[str, Any]]] = {}
        for row in report["sample_comparisons"]:
            comparisons_by_segment.setdefault(row["segment_index"], []).append(row)

        lines = [
            "# Anchor Comparison Facts",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Segment Count | {report['summary']['segment_count']} |",
            f"| Comparison Sample Count | {report['summary']['comparison_sample_count']} |",
            "",
            "## Difference Statistics",
            "",
            statistics_table(report["summary"]["difference_statistics"]),
            "",
            "## SSIM Statistics",
            "",
            statistics_table(report["summary"]["ssim_statistics"]),
            "",
            "## Difference Histogram",
            "",
            histogram_table(report["histograms"]["difference"]),
            "",
            "## SSIM Histogram",
            "",
            histogram_table(report["histograms"]["ssim"]),
            "",
            "## Segment Comparisons",
            "",
        ]

        for segment in report["segment_summaries"]:
            lines.extend(
                [
                    f"### Segment {segment['segment_index']}",
                    "",
                    "| Field | Value |",
                    "| --- | ---: |",
                    f"| Anchor Sample | {segment['anchor_sample_index']} |",
                    f"| Sample Count | {segment['sample_count']} |",
                    "",
                    "| Sample # | Difference | SSIM | Laplacian |",
                    "| ---: | ---: | ---: | ---: |",
                ]
            )
            for row in comparisons_by_segment.get(segment["segment_index"], []):
                lines.append(
                    f"| {row['sample_index']} | "
                    f"{fmt(row['anchor_difference_score'])} | "
                    f"{fmt(row['anchor_ssim_score'])} | "
                    f"{fmt(row['laplacian_variance'])} |"
                )
            lines.extend(
                [
                    "",
                    "Difference",
                    "",
                    statistics_table(segment["difference_statistics"]),
                    "",
                    "SSIM",
                    "",
                    statistics_table(segment["ssim_statistics"]),
                    "",
                ]
            )

        return "\n".join(lines)

    def _write_csv(self, csv_path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames = [
            "segment_index",
            "sample_index",
            "frame_index",
            "analysis_timestamp_seconds",
            "target_timestamp_seconds",
            "laplacian_variance",
            "anchor_sample_index",
            "anchor_difference_score",
            "anchor_ssim_score",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row[field] for field in fieldnames})


def statistics_table(stats: dict[str, Any]) -> str:
    return "\n".join(
        [
            "| Metric | Min | Max | Average |",
            "| --- | ---: | ---: | ---: |",
            f"| Value | {fmt(stats['minimum'])} | {fmt(stats['maximum'])} | {fmt(stats['average'])} |",
        ]
    )


def histogram_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Range | Count |",
        "| --- | ---: |",
    ]
    for row in rows:
        lines.append(f"| {row['range']} | {row['count']} |")
    return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
