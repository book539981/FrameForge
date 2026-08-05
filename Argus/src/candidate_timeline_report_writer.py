from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class CandidateTimelineReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def build_rows(
        self,
        samples: list[dict[str, Any]],
        stable_segments_report: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rule_result_by_sample = {
            result["sample_index"]: result
            for result in stable_segments_report["sample_rule_results"]
        }
        segment_by_sample = self._segment_by_sample(
            stable_segments_report["candidate_segments"]
        )
        rows: list[dict[str, Any]] = []

        for sample in samples:
            sample_index = sample["sample_index"]
            rule_result = rule_result_by_sample[sample_index]
            segment = segment_by_sample.get(sample_index)
            rows.append(
                {
                    "sample_index": sample_index,
                    "segment_index": segment["segment_index"] if segment else None,
                    "frame_index": sample["frame_index"],
                    "target_frame_index": sample["target_frame_index"],
                    "analysis_timestamp_seconds": sample[
                        "analysis_timestamp_seconds"
                    ],
                    "target_timestamp_seconds": sample["target_timestamp_seconds"],
                    "adjacent_difference_score": sample[
                        "adjacent_difference_score"
                    ],
                    "lookback_difference_score": sample[
                        "lookback_difference_score"
                    ],
                    "adjacent_pass": rule_result["adjacent_pass"],
                    "lookback_pass": rule_result["lookback_pass"],
                    "is_stable_candidate": rule_result["is_stable_candidate"],
                    "segment_start": (
                        sample_index == segment["start_sample_index"]
                        if segment
                        else False
                    ),
                    "segment_end": (
                        sample_index == segment["end_sample_index"]
                        if segment
                        else False
                    ),
                    "sample_count_in_segment": (
                        segment["sample_count"] if segment else None
                    ),
                }
            )

        return rows

    def write(
        self,
        rows: list[dict[str, Any]],
        stable_segments_report: dict[str, Any],
    ) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "candidate_timeline.json"
        markdown_path = self.artifacts_dir / "candidate_timeline.md"
        csv_path = self.artifacts_dir / "candidate_timeline.csv"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        self._write_csv(csv_path, rows)
        markdown_path.write_text(
            self._to_markdown(rows, stable_segments_report["candidate_segments"]),
            encoding="utf-8",
        )
        return json_path, markdown_path, csv_path

    def _segment_by_sample(
        self,
        candidate_segments: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        segment_by_sample: dict[int, dict[str, Any]] = {}
        for segment in candidate_segments:
            for sample_index in segment["sample_indices"]:
                segment_by_sample[sample_index] = segment
        return segment_by_sample

    def _write_csv(self, csv_path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames = [
            "sample_index",
            "segment_index",
            "frame_index",
            "target_frame_index",
            "analysis_timestamp_seconds",
            "target_timestamp_seconds",
            "adjacent_difference_score",
            "lookback_difference_score",
            "adjacent_pass",
            "lookback_pass",
            "is_stable_candidate",
            "segment_start",
            "segment_end",
            "sample_count_in_segment",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted(rows, key=lambda item: item["sample_index"]):
                writer.writerow({field: row[field] for field in fieldnames})

    def _to_markdown(
        self,
        rows: list[dict[str, Any]],
        candidate_segments: list[dict[str, Any]],
    ) -> str:
        stable_candidate_count = sum(1 for row in rows if row["is_stable_candidate"])
        lines = [
            "# Candidate Timeline Debug Report",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Total Samples | {len(rows)} |",
            f"| Stable Candidate Samples | {stable_candidate_count} |",
            f"| Rejected Samples | {len(rows) - stable_candidate_count} |",
            f"| Segment Count | {len(candidate_segments)} |",
            "",
        ]
        rows_by_sample = {row["sample_index"]: row for row in rows}

        for segment in candidate_segments:
            lines.extend(
                [
                    f"## Segment {segment['segment_index']:02d}",
                    "",
                    "| Field | Value |",
                    "| --- | ---: |",
                    f"| Samples | {segment['start_sample_index']}~{segment['end_sample_index']} |",
                    f"| Count | {segment['sample_count']} |",
                    "",
                    "| Sample | Adjacent | Lookback | Adjacent PASS | Lookback PASS | Stable Candidate | Start | End |",
                    "| ---: | ---: | ---: | --- | --- | --- | --- | --- |",
                ]
            )
            for sample_index in segment["sample_indices"]:
                row = rows_by_sample[sample_index]
                lines.append(
                    f"| {row['sample_index']} | "
                    f"{fmt(row['adjacent_difference_score'])} | "
                    f"{fmt(row['lookback_difference_score'])} | "
                    f"{row['adjacent_pass']} | "
                    f"{row['lookback_pass']} | "
                    f"{row['is_stable_candidate']} | "
                    f"{row['segment_start']} | "
                    f"{row['segment_end']} |"
                )
            lines.append("")
        return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
