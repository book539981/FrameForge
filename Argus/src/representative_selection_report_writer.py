from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class RepresentativeSelectionReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "representative_selection.json"
        markdown_path = self.artifacts_dir / "representative_selection.md"
        csv_path = self.artifacts_dir / "representative_selection.csv"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        self._write_csv(csv_path, report["segment_results"])
        return json_path, markdown_path, csv_path

    def _to_markdown(self, report: dict[str, Any]) -> str:
        lines = [
            "# Representative Selection Debug Report",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Segment Count | {report['summary']['segment_count']} |",
            f"| Representative Count | {report['summary']['representative_count']} |",
            f"| Tail Bias Applied Count | {report['summary']['tail_bias_applied_count']} |",
            f"| Representative Margin Samples | {report['representative_margin_samples']} |",
            "",
            "## Segment Summary",
            "",
            "| Segment | Anchor | Representative | Representative Frame | Laplacian | Margin Applied | Eligible Start | Eligible End | Eligible Count | Tail Start | Tail End | Tail Count | Tail Bias Applied |",
            "| ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]

        for segment in report["segment_results"]:
            lines.append(
                f"| {segment['segment_index']} | "
                f"{segment['anchor_sample_index']} | "
                f"{segment['representative_sample_index']} | "
                f"{segment['representative_frame_index']} | "
                f"{fmt(segment['representative_laplacian_variance'])} | "
                f"{segment['margin_applied']} | "
                f"{segment['eligible_start_sample']} | "
                f"{segment['eligible_end_sample']} | "
                f"{segment['eligible_sample_count']} | "
                f"{segment['tail_candidate_start_sample']} | "
                f"{segment['tail_candidate_end_sample']} | "
                f"{segment['tail_candidate_count']} | "
                f"{segment['tail_bias_applied']} |"
            )

        lines.extend(["", "## Laplacian Ranking", ""])
        for segment in report["segment_results"]:
            lines.extend(
                [
                    f"### Segment {segment['segment_index']}",
                    "",
                    "| Rank | Sample | Frame | Laplacian |",
                    "| ---: | ---: | ---: | ---: |",
                ]
            )
            for row in segment["laplacian_ranking"]:
                lines.append(
                    f"| {row['rank']} | {row['sample_index']} | "
                    f"{row['frame_index']} | {fmt(row['laplacian_variance'])} |"
                )
            lines.append("")

        return "\n".join(lines)

    def _write_csv(self, csv_path: Path, segments: list[dict[str, Any]]) -> None:
        fieldnames = [
            "segment_index",
            "anchor_sample",
            "representative_sample",
            "representative_frame",
            "laplacian",
            "margin_applied",
            "eligible_start_sample",
            "eligible_end_sample",
            "eligible_sample_count",
            "tail_candidate_start_sample",
            "tail_candidate_end_sample",
            "tail_candidate_count",
            "tail_bias_applied",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for segment in segments:
                writer.writerow(
                    {
                        "segment_index": segment["segment_index"],
                        "anchor_sample": segment["anchor_sample_index"],
                        "representative_sample": segment[
                            "representative_sample_index"
                        ],
                        "representative_frame": segment[
                            "representative_frame_index"
                        ],
                        "laplacian": segment["representative_laplacian_variance"],
                        "margin_applied": segment["margin_applied"],
                        "eligible_start_sample": segment["eligible_start_sample"],
                        "eligible_end_sample": segment["eligible_end_sample"],
                        "eligible_sample_count": segment["eligible_sample_count"],
                        "tail_candidate_start_sample": segment[
                            "tail_candidate_start_sample"
                        ],
                        "tail_candidate_end_sample": segment[
                            "tail_candidate_end_sample"
                        ],
                        "tail_candidate_count": segment["tail_candidate_count"],
                        "tail_bias_applied": segment["tail_bias_applied"],
                    }
                )


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
