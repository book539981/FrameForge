from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReportWriter:
    def __init__(self, config: dict[str, Any], argus_root: Path) -> None:
        self.config = config
        self.argus_root = argus_root
        self.artifacts_dir = argus_root / config["output"]["artifacts_directory"]

    def write(self, report: dict[str, Any]) -> tuple[Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / self.config["report"]["json_filename"]
        markdown_path = self.artifacts_dir / self.config["report"]["markdown_filename"]

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        return json_path, markdown_path

    def _to_markdown(self, report: dict[str, Any]) -> str:
        metadata = report["video_metadata"]
        sampling = report["sampling"]
        stats = report["frame_statistics"]
        black_border = report["black_border_analysis"]
        roi = report["roi_recommendation"]
        warnings = report["warnings"]
        errors = report["errors"]

        lines = [
            "# Argus Video Analysis Report",
            "",
            "## 1. Execution Summary",
            "",
            f"- Input: `{metadata['filename']}`",
            f"- Resolution: {metadata['width']} x {metadata['height']}",
            f"- Duration: {metadata['duration_seconds']:.3f} seconds ({metadata['duration_formatted']})",
            f"- Sampled frames: {sampling['sampled_frames']}",
            f"- ROI: top {roi['top_crop_recommendation']} px, bottom {roi['bottom_crop_recommendation']} px",
            f"- ROI confidence: {roi['confidence']}",
            "",
            "## 2. Video Metadata",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Filename | `{metadata['filename']}` |",
            f"| Path | `{metadata['path']}` |",
            f"| Size bytes | {metadata['size_bytes']} |",
            f"| Codec FOURCC | {metadata['codec_fourcc']} |",
            f"| Width | {metadata['width']} |",
            f"| Height | {metadata['height']} |",
            f"| FPS | {metadata['fps']:.6f} |",
            f"| Total frames | {metadata['total_frames']} |",
            f"| Duration seconds | {metadata['duration_seconds']:.6f} |",
            f"| Duration formatted | {metadata['duration_formatted']} |",
            f"| Opened | {metadata['is_opened']} |",
            "",
            "## 3. Sampling Configuration",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Sampling rate | {sampling['sampling_rate']:g} samples/second |",
            f"| Frame interval | {sampling['frame_interval']} |",
            f"| First sampled frame | {sampling['first_sampled_frame_index']} |",
            f"| Last sampled frame | {sampling['last_sampled_frame_index']} |",
            f"| Failed frame count | {sampling['failed_frame_count']} |",
            "",
            "## 4. Frame Statistics",
            "",
            self._statistics_table(stats),
            "",
            "## 5. Black Border Analysis",
            "",
            self._black_border_table(black_border),
            "",
            "## 6. ROI Recommendation",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Top crop recommendation | {roi['top_crop_recommendation']} px |",
            f"| Bottom crop recommendation | {roi['bottom_crop_recommendation']} px |",
            f"| Confidence | {roi['confidence']} |",
            "",
            "## 7. Per-Second Summary",
            "",
            self._per_second_table(report["per_second_summary"]),
            "",
            "## 8. Warnings and Errors",
            "",
            self._messages(warnings, errors),
            "",
        ]
        return "\n".join(lines)

    def _statistics_table(self, stats: dict[str, dict[str, Any]]) -> str:
        rows = [
            "| Metric | Min | Max | Mean | Median | Std Dev | P10 | P25 | P75 | P90 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        labels = {
            "brightness": "Brightness",
            "contrast": "Contrast",
            "laplacian_variance": "Laplacian variance",
            "black_pixel_ratio": "Black pixel ratio",
        }
        for key, label in labels.items():
            item = stats[key]
            rows.append(
                f"| {label} | {fmt(item['minimum'])} | {fmt(item['maximum'])} | {fmt(item['mean'])} | "
                f"{fmt(item['median'])} | {fmt(item['standard_deviation'])} | {fmt(item['p10'])} | "
                f"{fmt(item['p25'])} | {fmt(item['p75'])} | {fmt(item['p90'])} |"
            )
        return "\n".join(rows)

    def _black_border_table(self, black_border: dict[str, dict[str, Any]]) -> str:
        rows = [
            "| Border | Min | Max | Mean | Median | Mode | P10 | P90 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for key, label in (("top_black_rows", "Top black rows"), ("bottom_black_rows", "Bottom black rows")):
            item = black_border[key]
            rows.append(
                f"| {label} | {fmt(item['minimum'])} | {fmt(item['maximum'])} | {fmt(item['mean'])} | "
                f"{fmt(item['median'])} | {fmt(item['mode'])} | {fmt(item['p10'])} | {fmt(item['p90'])} |"
            )
        return "\n".join(rows)

    def _per_second_table(self, rows: list[dict[str, Any]]) -> str:
        table = [
            "| Second | Frame Indices | Samples | Brightness Mean | Contrast Mean | Laplacian Mean | Laplacian Min | Black Ratio Mean | Top Rows Median | Bottom Rows Median |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in rows:
            indices = ", ".join(str(index) for index in row["frame_indices"])
            table.append(
                f"| {row['second']} | {indices} | {row['sample_count']} | {fmt(row['brightness_mean'])} | "
                f"{fmt(row['contrast_mean'])} | {fmt(row['laplacian_variance_mean'])} | "
                f"{fmt(row['laplacian_variance_minimum'])} | {fmt(row['black_pixel_ratio_mean'])} | "
                f"{fmt(row['top_black_rows_median'])} | {fmt(row['bottom_black_rows_median'])} |"
            )
        return "\n".join(table)

    def _messages(self, warnings: list[str], errors: list[str]) -> str:
        if not warnings and not errors:
            return "- No warnings or errors."

        lines: list[str] = []
        for warning in warnings:
            lines.append(f"- Warning: {warning}")
        for error in errors:
            lines.append(f"- Error: {error}")
        return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
