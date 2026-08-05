from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class SpatialComparisonReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "spatial_comparison.json"
        markdown_path = self.artifacts_dir / "spatial_comparison.md"
        csv_path = self.artifacts_dir / "spatial_comparison.csv"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        self._write_csv(csv_path, report["sample_comparisons"])
        return json_path, markdown_path, csv_path

    def _to_markdown(self, report: dict[str, Any]) -> str:
        lines = [
            "# Spatial Comparison Facts",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Sample Comparisons | {report['summary']['sample_comparison_count']} |",
            f"| Representative Comparisons | {report['summary']['representative_comparison_count']} |",
            "",
            "## ROI",
            "",
            "| ROI | Definition |",
            "| --- | --- |",
        ]
        for name, definition in report["roi_definition"].items():
            lines.append(f"| {name} | {definition} |")

        lines.extend(["", "## Representatives", ""])
        for representative in report["representative_comparisons"]:
            comparison = representative["comparison"]
            lines.extend(
                [
                    f"### Segment {representative['segment_index']}",
                    "",
                    f"- Representative Sample = {representative['representative_sample_index']}",
                    f"- Representative Frame = {representative['representative_frame_index']}",
                    f"- Anchor Sample = {representative['anchor_sample_index']}",
                    "",
                    "| Region | Difference | SSIM |",
                    "| --- | ---: | ---: |",
                    f"| Whole | {fmt(comparison['whole']['difference'])} | {fmt(comparison['whole']['ssim'])} |",
                    f"| Left | {fmt(comparison['left']['difference'])} | {fmt(comparison['left']['ssim'])} |",
                    f"| Center | {fmt(comparison['center']['difference'])} | {fmt(comparison['center']['ssim'])} |",
                    f"| Right | {fmt(comparison['right']['difference'])} | {fmt(comparison['right']['ssim'])} |",
                    "",
                ]
            )
        return "\n".join(lines)

    def _write_csv(self, csv_path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames = [
            "sample_index",
            "whole_difference",
            "left_difference",
            "center_difference",
            "right_difference",
            "whole_ssim",
            "left_ssim",
            "center_ssim",
            "right_ssim",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row[field] for field in fieldnames})


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
