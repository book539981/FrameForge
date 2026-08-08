from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class PageChangeEventsReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "page_change_events.json"
        csv_path = self.artifacts_dir / "page_change_events.csv"
        markdown_path = self.artifacts_dir / "page_change_events.md"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        self._write_csv(csv_path, report["pages"])
        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        return json_path, csv_path, markdown_path

    def _write_csv(self, csv_path: Path, pages: list[dict[str, Any]]) -> None:
        fieldnames = [
            "page_index",
            "start_frame",
            "end_frame",
            "representative_frame",
            "laplacian_variance",
            "changed_area_peak",
            "ssim_minimum",
            "ecc_score_minimum",
            "ecc_dx_at_score_minimum",
            "ecc_dy_at_score_minimum",
            "source_event_index",
            "frame_count",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for page in pages:
                writer.writerow({field: page[field] for field in fieldnames})

    def _to_markdown(self, report: dict[str, Any]) -> str:
        rule = report["rule"]
        summary = report["summary"]
        lines = [
            "# Page Change Events",
            "",
            "## Rule",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Page Change Condition | {rule['page_change_condition']} |",
            f"| Changed Area Ratio Threshold | {fmt(rule['changed_area_ratio_threshold'])} |",
            f"| SSIM Threshold | {fmt(rule['ssim_threshold'])} |",
            f"| ECC Score Minimum | {fmt(rule['ecc_score_minimum'])} |",
            f"| Alignment Translation Maximum Pixels | {fmt(rule['alignment_translation_maximum_pixels'])} |",
            f"| Event Merge Gap Seconds | {fmt(rule['event_merge_gap_seconds'])} |",
            f"| Merge Rule | {rule['merge_rule']} |",
            f"| Representative Frame Rule | {rule['representative_frame_rule']} |",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Page Change Event Count | {summary['page_change_event_count']} |",
            f"| Representative Count | {summary['representative_count']} |",
            f"| Exported Page Count | {summary['exported_page_count']} |",
            "",
            "## Pages",
            "",
            "| Page | Start Frame | End Frame | Representative Frame | Laplacian | Changed Area Peak | SSIM Minimum | ECC Score Minimum | ECC dx | ECC dy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for page in report["pages"]:
            lines.append(
                f"| {page['page_index']} | {page['start_frame']} | "
                f"{page['end_frame']} | {page['representative_frame']} | "
                f"{fmt(page['laplacian_variance'])} | "
                f"{fmt(page['changed_area_peak'])} | "
                f"{fmt(page['ssim_minimum'])} | "
                f"{fmt(page['ecc_score_minimum'])} | "
                f"{fmt(page['ecc_dx_at_score_minimum'])} | "
                f"{fmt(page['ecc_dy_at_score_minimum'])} |"
            )
        lines.append("")
        return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
