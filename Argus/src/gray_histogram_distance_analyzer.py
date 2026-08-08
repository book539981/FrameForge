from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.video_reader import find_single_video, read_metadata
else:
    from .video_reader import find_single_video, read_metadata


HISTOGRAM_BIN_COUNT = 256
HISTOGRAM_RANGE = [0, 256]
P30_P31_START_SECONDS = 67.0
P30_P31_END_SECONDS = 69.0
EARLY_DEBUG_START_SECONDS = 0.0
EARLY_DEBUG_END_SECONDS = 4.0


class GrayHistogramDistanceAnalyzer:
    def analyze(
        self,
        video_path: Path,
        page_change_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = read_metadata(video_path)
        event_frames = page_change_event_frames(page_change_report)
        frames: list[dict[str, Any]] = []
        previous_histogram: np.ndarray | None = None

        capture = cv2.VideoCapture(str(video_path))
        try:
            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                histogram = normalized_gray_histogram(gray)
                frames.append(
                    frame_histogram_fact(
                        frame_index=frame_index,
                        total_frames=metadata.total_frames,
                        duration_seconds=metadata.duration_seconds,
                        histogram=histogram,
                        previous_histogram=previous_histogram,
                        event_frames=event_frames,
                    )
                )
                previous_histogram = histogram
                frame_index += 1
        finally:
            capture.release()

        analysis = observation_analysis(frames)
        return {
            "schema_version": "1.0",
            "video_metadata": {
                "filename": metadata.filename,
                "path": metadata.path,
                "width": metadata.width,
                "height": metadata.height,
                "fps": metadata.fps,
                "total_frames": metadata.total_frames,
                "duration_seconds": metadata.duration_seconds,
                "codec_fourcc": metadata.codec_fourcc,
            },
            "histogram_definition": {
                "grayscale_conversion": "OpenCV cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)",
                "histogram": "OpenCV cv2.calcHist over grayscale levels 0..255 with 256 bins",
                "normalization": "Each bin is divided by total pixel count.",
                "comparison_reference": "Histogram[n] vs Histogram[n-1]",
                "opencv_comparison_methods": [
                    "BHATTACHARYYA",
                    "CHISQR",
                    "CORREL",
                ],
                "additional_observation_methods": ["L1"],
                "rules": [],
            },
            "summary": {
                "frame_count": len(frames),
                "event_frame_count": sum(1 for frame in frames if frame["is_page_change_candidate"]),
                "same_page_frame_count": sum(
                    1
                    for frame in frames
                    if frame["previous_frame_index"] is not None
                    and not frame["is_page_change_candidate"]
                ),
            },
            "frames": frames,
            "analysis": analysis,
        }


class GrayHistogramDistanceReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "gray_histogram_timeline.json"
        csv_path = self.artifacts_dir / "gray_histogram_timeline.csv"
        markdown_path = self.artifacts_dir / "gray_histogram_timeline.md"

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
            "timestamp_seconds",
            "is_page_change_candidate",
            "gray_histogram_distance",
            "gray_histogram_bhattacharyya",
            "gray_histogram_chi_square",
            "gray_histogram_correlation",
            "gray_histogram_l1",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for frame in frames:
                writer.writerow({field: frame[field] for field in fieldnames})

    def _to_markdown(self, report: dict[str, Any]) -> str:
        metadata = report["video_metadata"]
        analysis = report["analysis"]
        lines = [
            "# Gray Histogram Distance Timeline",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Filename | {metadata['filename']} |",
            f"| Frame Count | {report['summary']['frame_count']} |",
            f"| Page Change Candidate Frames | {report['summary']['event_frame_count']} |",
            f"| Same Page Frames | {report['summary']['same_page_frame_count']} |",
            "",
            "## First 20 Frames",
            "",
            "| Frame | Previous | Timestamp | Candidate | Bhattacharyya | Chi-Square | Correlation | L1 |",
            "| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
        for frame in report["frames"][:20]:
            lines.append(frame_table_row(frame))

        lines.extend(
            [
                "",
                "## Observation Analysis",
                "",
                "Grouping: Page Change Candidate uses the existing `page_change_events.json` event frame ranges for observation only. It does not define a new rule.",
                "",
                "### Same Page vs Page Change Candidate",
                "",
                "| Method | Same Page Median | Page Change Candidate Median | Dynamic Range | Overlap Ratio | Separation Note |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for method in analysis["methods"]:
            lines.append(
                f"| {method['method']} | {fmt(method['same_page']['median'])} | "
                f"{fmt(method['page_change_candidate']['median'])} | "
                f"{fmt(method['dynamic_range'])} | {fmt(method['overlap_ratio'])} | "
                f"{method['separation_note']} |"
            )

        lines.extend(
            [
                "",
                "### P30 to P31 Debug Window",
                "",
                f"Window: {P30_P31_START_SECONDS:g}s to {P30_P31_END_SECONDS:g}s",
                "",
                debug_window_table(analysis["p30_p31_window"]),
                "",
                "### Early Debug Window",
                "",
                f"Window: {EARLY_DEBUG_START_SECONDS:g}s to {EARLY_DEBUG_END_SECONDS:g}s",
                "",
                debug_window_table(analysis["early_debug_window"]),
                "",
                "### Answers",
                "",
                f"- Same Page Median: {analysis['answers']['same_page_median']}",
                f"- Page Change Candidate Median: {analysis['answers']['page_change_candidate_median']}",
                f"- Dynamic Range: {analysis['answers']['dynamic_range']}",
                f"- Clear Separation: {analysis['answers']['clear_separation']}",
                f"- P30 to P31 Spike: {analysis['answers']['p30_p31_spike']}",
                f"- Same Page False Positive Spike: {analysis['answers']['same_page_false_positive_spike']}",
                f"- Cleanest Separation Method: {analysis['answers']['cleanest_method']}",
                "",
            ]
        )
        return "\n".join(lines)


def normalized_gray_histogram(gray: np.ndarray) -> np.ndarray:
    histogram = cv2.calcHist(
        [gray],
        [0],
        None,
        [HISTOGRAM_BIN_COUNT],
        HISTOGRAM_RANGE,
    ).astype(np.float32)
    total = float(gray.size)
    return (histogram / total).reshape(-1)


def frame_histogram_fact(
    frame_index: int,
    total_frames: int,
    duration_seconds: float,
    histogram: np.ndarray,
    previous_histogram: np.ndarray | None,
    event_frames: set[int],
) -> dict[str, Any]:
    timestamp = analysis_timestamp_seconds(
        frame_index=frame_index,
        total_frames=total_frames,
        duration_seconds=duration_seconds,
    )
    if previous_histogram is None:
        return {
            "frame_index": frame_index,
            "previous_frame_index": None,
            "timestamp_seconds": timestamp,
            "is_page_change_candidate": frame_index in event_frames,
            "gray_histogram_distance": None,
            "gray_histogram_bhattacharyya": None,
            "gray_histogram_chi_square": None,
            "gray_histogram_correlation": None,
            "gray_histogram_l1": None,
        }

    bhattacharyya = float(
        cv2.compareHist(
            previous_histogram,
            histogram,
            cv2.HISTCMP_BHATTACHARYYA,
        )
    )
    return {
        "frame_index": frame_index,
        "previous_frame_index": frame_index - 1,
        "timestamp_seconds": timestamp,
        "is_page_change_candidate": frame_index in event_frames,
        "gray_histogram_distance": bhattacharyya,
        "gray_histogram_bhattacharyya": bhattacharyya,
        "gray_histogram_chi_square": float(
            cv2.compareHist(previous_histogram, histogram, cv2.HISTCMP_CHISQR)
        ),
        "gray_histogram_correlation": float(
            cv2.compareHist(previous_histogram, histogram, cv2.HISTCMP_CORREL)
        ),
        "gray_histogram_l1": float(np.sum(np.abs(previous_histogram - histogram))),
    }


def observation_analysis(frames: list[dict[str, Any]]) -> dict[str, Any]:
    method_specs = [
        ("gray_histogram_bhattacharyya", "higher_distance_means_more_change"),
        ("gray_histogram_chi_square", "higher_distance_means_more_change"),
        ("gray_histogram_correlation", "lower_correlation_means_more_change"),
        ("gray_histogram_l1", "higher_distance_means_more_change"),
    ]
    method_reports = [
        method_analysis(frames, field, direction) for field, direction in method_specs
    ]
    ranked = sorted(
        method_reports,
        key=lambda item: (
            item["overlap_ratio"] if item["overlap_ratio"] is not None else 1.0,
            -(
                item["median_gap_over_dynamic_range"]
                if item["median_gap_over_dynamic_range"] is not None
                else 0.0
            ),
        ),
    )
    cleanest = ranked[0] if ranked else None
    primary = next(
        method
        for method in method_reports
        if method["method"] == "gray_histogram_bhattacharyya"
    )
    p30_window = debug_window(
        frames,
        P30_P31_START_SECONDS,
        P30_P31_END_SECONDS,
    )
    early_window = debug_window(
        frames,
        EARLY_DEBUG_START_SECONDS,
        EARLY_DEBUG_END_SECONDS,
    )
    return {
        "methods": method_reports,
        "p30_p31_window": p30_window,
        "early_debug_window": early_window,
        "answers": {
            "same_page_median": fmt(primary["same_page"]["median"]),
            "page_change_candidate_median": fmt(
                primary["page_change_candidate"]["median"]
            ),
            "dynamic_range": fmt(primary["dynamic_range"]),
            "clear_separation": clear_separation_text(primary),
            "p30_p31_spike": spike_text(p30_window, primary["method"]),
            "same_page_false_positive_spike": false_positive_spike_text(
                method_reports,
                frames,
            ),
            "cleanest_method": cleanest["method"] if cleanest else "",
        },
    }


def method_analysis(
    frames: list[dict[str, Any]],
    field: str,
    direction: str,
) -> dict[str, Any]:
    same = values_for(frames, field, is_candidate=False)
    candidates = values_for(frames, field, is_candidate=True)
    combined = same + candidates
    same_stats = distribution(same)
    candidate_stats = distribution(candidates)
    combined_stats = distribution(combined)
    dynamic_range = (
        combined_stats["maximum"] - combined_stats["minimum"]
        if combined_stats["maximum"] is not None
        and combined_stats["minimum"] is not None
        else None
    )
    median_gap = (
        abs(candidate_stats["median"] - same_stats["median"])
        if candidate_stats["median"] is not None
        and same_stats["median"] is not None
        else None
    )
    overlap = overlap_ratio(same_stats, candidate_stats)
    return {
        "method": field,
        "direction": direction,
        "same_page": same_stats,
        "page_change_candidate": candidate_stats,
        "dynamic_range": dynamic_range,
        "median_gap": median_gap,
        "median_gap_over_dynamic_range": median_gap / dynamic_range
        if median_gap is not None and dynamic_range
        else None,
        "overlap_ratio": overlap,
        "separation_note": separation_note(overlap),
    }


def values_for(
    frames: list[dict[str, Any]],
    field: str,
    is_candidate: bool,
) -> list[float]:
    return [
        float(frame[field])
        for frame in frames
        if frame["previous_frame_index"] is not None
        and frame["is_page_change_candidate"] == is_candidate
        and frame[field] is not None
    ]


def distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "maximum": None,
            "p90": None,
            "p95": None,
        }
    array = np.array(values, dtype=np.float64)
    return {
        "count": len(values),
        "minimum": float(np.min(array)),
        "median": float(np.percentile(array, 50)),
        "maximum": float(np.max(array)),
        "p90": float(np.percentile(array, 90)),
        "p95": float(np.percentile(array, 95)),
    }


def overlap_ratio(
    same_stats: dict[str, Any],
    candidate_stats: dict[str, Any],
) -> float | None:
    if same_stats["minimum"] is None or candidate_stats["minimum"] is None:
        return None
    union_minimum = min(same_stats["minimum"], candidate_stats["minimum"])
    union_maximum = max(same_stats["maximum"], candidate_stats["maximum"])
    union_width = union_maximum - union_minimum
    if not union_width:
        return 0.0
    overlap_minimum = max(same_stats["minimum"], candidate_stats["minimum"])
    overlap_maximum = min(same_stats["maximum"], candidate_stats["maximum"])
    overlap_width = max(0.0, overlap_maximum - overlap_minimum)
    return overlap_width / union_width


def debug_window(
    frames: list[dict[str, Any]],
    start_seconds: float,
    end_seconds: float,
) -> dict[str, Any]:
    rows = [
        frame
        for frame in frames
        if frame["previous_frame_index"] is not None
        and start_seconds <= frame["timestamp_seconds"] <= end_seconds
    ]
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "rows": rows,
        "maximums": {
            "gray_histogram_bhattacharyya": max_value(rows, "gray_histogram_bhattacharyya"),
            "gray_histogram_chi_square": max_value(rows, "gray_histogram_chi_square"),
            "gray_histogram_l1": max_value(rows, "gray_histogram_l1"),
            "gray_histogram_correlation_minimum": min_value(
                rows,
                "gray_histogram_correlation",
            ),
        },
    }


def max_value(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row[field] is not None]
    return max(values) if values else None


def min_value(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row[field] is not None]
    return min(values) if values else None


def page_change_event_frames(report: dict[str, Any] | None) -> set[int]:
    if not report:
        return set()
    frames: set[int] = set()
    for event in report.get("events", []):
        frames.update(range(event["start_frame"], event["end_frame"] + 1))
    return frames


def analysis_timestamp_seconds(
    frame_index: int,
    total_frames: int,
    duration_seconds: float,
) -> float:
    if total_frames <= 1:
        return 0.0
    return round(frame_index / (total_frames - 1) * duration_seconds, 6)


def frame_table_row(frame: dict[str, Any]) -> str:
    return (
        f"| {frame['frame_index']} | {fmt(frame['previous_frame_index'])} | "
        f"{fmt(frame['timestamp_seconds'])} | {frame['is_page_change_candidate']} | "
        f"{fmt(frame['gray_histogram_bhattacharyya'])} | "
        f"{fmt(frame['gray_histogram_chi_square'])} | "
        f"{fmt(frame['gray_histogram_correlation'])} | "
        f"{fmt(frame['gray_histogram_l1'])} |"
    )


def debug_window_table(window: dict[str, Any]) -> str:
    rows = [
        "| Frame | Timestamp | Candidate | Bhattacharyya | Chi-Square | Correlation | L1 |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for frame in window["rows"]:
        rows.append(
            f"| {frame['frame_index']} | {fmt(frame['timestamp_seconds'])} | "
            f"{frame['is_page_change_candidate']} | "
            f"{fmt(frame['gray_histogram_bhattacharyya'])} | "
            f"{fmt(frame['gray_histogram_chi_square'])} | "
            f"{fmt(frame['gray_histogram_correlation'])} | "
            f"{fmt(frame['gray_histogram_l1'])} |"
        )
    return "\n".join(rows)


def clear_separation_text(method: dict[str, Any]) -> str:
    overlap = method["overlap_ratio"]
    if overlap is None:
        return "No grouping data."
    if overlap <= 0.05:
        return "Clear separation in this grouping."
    if overlap <= 0.25:
        return "Partial separation with some overlap."
    return "No clean separation; distributions overlap."


def spike_text(window: dict[str, Any], field: str) -> str:
    value = window["maximums"].get(field)
    if value is None:
        return "No samples in debug window."
    return f"Maximum {field} in window = {fmt(value)}."


def false_positive_spike_text(
    method_reports: list[dict[str, Any]],
    frames: list[dict[str, Any]],
) -> str:
    primary = next(
        method
        for method in method_reports
        if method["method"] == "gray_histogram_bhattacharyya"
    )
    same_p95 = primary["same_page"]["p95"]
    candidate_median = primary["page_change_candidate"]["median"]
    if same_p95 is None or candidate_median is None:
        return "Insufficient data."
    same_spikes = [
        frame
        for frame in frames
        if frame["previous_frame_index"] is not None
        and not frame["is_page_change_candidate"]
        and frame["gray_histogram_bhattacharyya"] is not None
        and frame["gray_histogram_bhattacharyya"] >= candidate_median
    ]
    return (
        f"{len(same_spikes)} same-page frames are at or above the page-change "
        f"candidate median Bhattacharyya distance."
    )


def separation_note(overlap: float | None) -> str:
    if overlap is None:
        return "No data"
    if overlap <= 0.05:
        return "clean"
    if overlap <= 0.25:
        return "partial"
    return "overlap"


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    argus_root = Path(__file__).resolve().parents[1]
    artifacts_dir = argus_root / "output" / "artifacts"
    video_path = find_single_video(argus_root / "input")
    page_change_report = load_json(artifacts_dir / "page_change_events.json")
    report = GrayHistogramDistanceAnalyzer().analyze(
        video_path=video_path,
        page_change_report=page_change_report,
    )
    paths = GrayHistogramDistanceReportWriter(artifacts_dir).write(report)
    print("gray_histogram_timeline artifacts:")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
