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
        diagnostics = report["reader_diagnostics"]
        stats = report["frame_statistics"]
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
            f"- Failed samples: {diagnostics['failed_sample_count']}",
            f"- Last decoded frame: {diagnostics['last_successful_frame_index']}",
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
            f"| Sampling method | {sampling['sampling_method']} |",
            f"| Sample timestamp source | {sampling['sample_timestamp_source']} |",
            f"| Timestamp seconds definition | {sampling['timestamp_seconds_definition']} |",
            f"| Target timestamp seconds definition | {sampling['target_timestamp_seconds_definition']} |",
            f"| Sampling rate | {sampling['sampling_rate']:g} samples/second |",
            f"| Sample period seconds | {fmt(sampling['sample_period_seconds'])} |",
            f"| Lookback sample offset | {report['config']['analysis']['lookback_sample_offset']} |",
            f"| First requested frame | {sampling['first_requested_frame_index']} |",
            f"| Last requested frame | {sampling['last_requested_frame_index']} |",
            f"| First sampled frame | {sampling['first_sampled_frame_index']} |",
            f"| Last sampled frame | {sampling['last_sampled_frame_index']} |",
            f"| First failed sample frame | {sampling['first_failed_sample_frame_index']} |",
            f"| Last failed sample frame | {sampling['last_failed_sample_frame_index']} |",
            f"| Unsampled tail frame count | {sampling['unsampled_tail_frame_count']} |",
            f"| Unsampled tail duration seconds | {fmt(sampling['unsampled_tail_duration_seconds'])} |",
            f"| Failed tail frame count | {sampling['failed_tail_frame_count']} |",
            f"| Failed tail duration seconds | {fmt(sampling['failed_tail_duration_seconds'])} |",
            "",
            "## 4. Reader Diagnostics",
            "",
            self._reader_diagnostics_table(diagnostics),
            "",
            "## 5. Frame Statistics",
            "",
            self._statistics_table(stats),
            "",
            "## 6. Adjacent Difference Statistics",
            "",
            self._single_statistics_table("Adjacent Difference", stats["adjacent_difference_score"]),
            "",
            "## 7. Lookback Difference Statistics",
            "",
            self._single_statistics_table("Lookback Difference", stats["lookback_difference_score"]),
            "",
            "## 8. Failed Samples",
            "",
            self._failed_samples_table(report["failed_samples"]),
            "",
            "## 9. Per-Second Summary",
            "",
            self._per_second_table(report["per_second_summary"]),
            "",
            "## 10. Warnings and Errors",
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
            "adjacent_difference_score": "Adjacent difference",
            "lookback_difference_score": "Lookback difference",
        }
        for key, label in labels.items():
            item = stats[key]
            rows.append(
                f"| {label} | {fmt(item['minimum'])} | {fmt(item['maximum'])} | {fmt(item['mean'])} | "
                f"{fmt(item['median'])} | {fmt(item['standard_deviation'])} | {fmt(item['p10'])} | "
                f"{fmt(item['p25'])} | {fmt(item['p75'])} | {fmt(item['p90'])} |"
            )
        return "\n".join(rows)

    def _single_statistics_table(self, label: str, item: dict[str, Any]) -> str:
        rows = [
            "| Metric | Min | Max | Mean | Median | Std Dev | P10 | P25 | P75 | P90 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        rows.append(
            f"| {label} | {fmt(item['minimum'])} | {fmt(item['maximum'])} | {fmt(item['mean'])} | "
            f"{fmt(item['median'])} | {fmt(item['standard_deviation'])} | {fmt(item['p10'])} | "
            f"{fmt(item['p25'])} | {fmt(item['p75'])} | {fmt(item['p90'])} |"
        )
        return "\n".join(rows)

    def _reader_diagnostics_table(self, diagnostics: dict[str, Any]) -> str:
        rows = [
            "| Field | Value |",
            "| --- | ---: |",
        ]
        keys = [
            "metadata_total_frames",
            "metadata_fps",
            "metadata_duration_seconds",
            "duration_from_frame_count_seconds",
            "decode_attempt_count",
            "decoded_frame_count",
            "normal_eof_count",
            "unexpected_decode_failure_count",
            "last_successful_frame_index",
            "last_successful_timestamp_seconds",
            "first_failed_frame_index",
            "first_failed_timestamp_seconds",
            "capture_position_frames_at_failure",
            "capture_position_msec_at_failure",
            "expected_last_frame_index",
            "missing_tail_frame_count",
            "missing_tail_duration_seconds",
            "requested_sample_count",
            "successful_sample_count",
            "failed_sample_count",
        ]
        for key in keys:
            rows.append(f"| {key} | {fmt(diagnostics.get(key))} |")
        return "\n".join(rows)

    def _failed_samples_table(self, failed_samples: list[dict[str, Any]]) -> str:
        if not failed_samples:
            return "- No failed samples."

        rows = [
            "| Requested Frame | Expected Timestamp Seconds | Capture Position Frames | Capture Position Msec |",
            "| ---: | ---: | ---: | ---: |",
        ]
        for sample in failed_samples:
            rows.append(
                f"| {sample['requested_frame_index']} | {fmt(sample['expected_timestamp_seconds'])} | "
                f"{fmt(sample['capture_position_frames'])} | {fmt(sample['capture_position_msec'])} |"
            )
        return "\n".join(rows)

    def _per_second_table(self, rows: list[dict[str, Any]]) -> str:
        table = [
            "| Second | Frame Indices | Samples | Brightness Mean | Contrast Mean | Laplacian Mean | Laplacian Min | Adjacent Difference Mean | Lookback Difference Mean |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in rows:
            indices = ", ".join(str(index) for index in row["frame_indices"])
            table.append(
                f"| {row['second']} | {indices} | {row['sample_count']} | {fmt(row['brightness_mean'])} | "
                f"{fmt(row['contrast_mean'])} | {fmt(row['laplacian_variance_mean'])} | "
                f"{fmt(row['laplacian_variance_minimum'])} | {fmt(row['adjacent_difference_mean'])} | "
                f"{fmt(row['lookback_difference_mean'])} |"
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
