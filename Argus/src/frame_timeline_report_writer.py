from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class FrameTimelineReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "frame_difference_timeline.json"
        csv_path = self.artifacts_dir / "frame_difference_timeline.csv"
        markdown_path = self.artifacts_dir / "frame_difference_timeline.md"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        self._write_csv(csv_path, report["frames"])
        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        return json_path, csv_path, markdown_path

    def _write_csv(self, csv_path: Path, frames: list[dict[str, Any]]) -> None:
        fieldnames = [
            "frame_index",
            "previous_frame_index",
            "decoded_timestamp_seconds",
            "changed_area_ratio",
            "ssim",
            "ecc_converged",
            "ecc_score",
            "ecc_dx",
            "ecc_dy",
            "ecc_error",
            "laplacian_variance",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for frame in frames:
                writer.writerow({field: frame[field] for field in fieldnames})

    def _to_markdown(self, report: dict[str, Any]) -> str:
        metadata = report["video_metadata"]
        summary = report["summary"]
        lines = [
            "# Frame Difference Timeline",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Filename | {metadata['filename']} |",
            f"| Width | {metadata['width']} |",
            f"| Height | {metadata['height']} |",
            f"| FPS | {fmt(metadata['fps'])} |",
            f"| Total Frames Metadata | {metadata['total_frames']} |",
            f"| Decoded Frame Count | {summary['decoded_frame_count']} |",
            f"| Frame Fact Count | {summary['frame_fact_count']} |",
            "",
            "## First 20 Frames",
            "",
            "| Frame | Previous | Timestamp | Changed Area Ratio | SSIM | ECC Converged | ECC Score | ECC dx | ECC dy | Laplacian |",
            "| ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
        for frame in report["frames"][:20]:
            lines.append(
                f"| {frame['frame_index']} | {fmt(frame['previous_frame_index'])} | "
                f"{fmt(frame['decoded_timestamp_seconds'])} | "
                f"{fmt(frame['changed_area_ratio'])} | "
                f"{fmt(frame['ssim'])} | "
                f"{fmt(frame['ecc_converged'])} | "
                f"{fmt(frame['ecc_score'])} | "
                f"{fmt(frame['ecc_dx'])} | "
                f"{fmt(frame['ecc_dy'])} | "
                f"{fmt(frame['laplacian_variance'])} |"
            )
        lines.append("")
        return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
