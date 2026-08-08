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
    from src.gray_histogram_distance_analyzer import (
        P30_P31_END_SECONDS,
        P30_P31_START_SECONDS,
        analysis_timestamp_seconds,
        fmt,
        load_json,
        normalized_gray_histogram,
        page_change_event_frames,
    )
    from src.video_reader import find_single_video, read_metadata
else:
    from .gray_histogram_distance_analyzer import (
        P30_P31_END_SECONDS,
        P30_P31_START_SECONDS,
        analysis_timestamp_seconds,
        fmt,
        load_json,
        normalized_gray_histogram,
        page_change_event_frames,
    )
    from .video_reader import find_single_video, read_metadata


REGION_NAMES = ["region_00", "region_01", "region_10", "region_11"]
REGION_LABELS = {
    "region_00": "Region00",
    "region_01": "Region01",
    "region_10": "Region10",
    "region_11": "Region11",
}
METHODS = [
    "bhattacharyya",
    "chi_square",
    "correlation",
    "l1",
]


class RegionalGrayHistogramDistanceAnalyzer:
    def analyze(
        self,
        video_path: Path,
        page_change_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = read_metadata(video_path)
        event_frames = page_change_event_frames(page_change_report)
        frames: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None

        capture = cv2.VideoCapture(str(video_path))
        try:
            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                current = {
                    "regions": {
                        name: normalized_gray_histogram(region)
                        for name, region in split_2x2(gray).items()
                    },
                }
                frames.append(
                    frame_fact(
                        frame_index=frame_index,
                        total_frames=metadata.total_frames,
                        duration_seconds=metadata.duration_seconds,
                        current=current,
                        previous=previous,
                        event_frames=event_frames,
                    )
                )
                previous = current
                frame_index += 1
        finally:
            capture.release()

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
                "level": "2x2 grayscale histograms: region_00 top-left, region_01 top-right, region_10 bottom-left, region_11 bottom-right.",
                "histogram": "Reuses normalized_gray_histogram from gray_histogram_distance_analyzer.py, backed by OpenCV cv2.calcHist.",
                "comparison": "OpenCV cv2.compareHist for Bhattacharyya, Chi-Square, Correlation; NumPy L1 on normalized histograms.",
                "rules": [],
            },
            "summary": {
                "frame_count": len(frames),
                "page_change_candidate_frames": sum(
                    1 for frame in frames if frame["is_page_change_candidate"]
                ),
                "same_page_frames": sum(
                    1
                    for frame in frames
                    if frame["previous_frame_index"] is not None
                    and not frame["is_page_change_candidate"]
                ),
            },
            "frames": frames,
            "analysis": observation_analysis(frames),
        }


class RegionalGrayHistogramDistanceReportWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "regional_gray_histogram_timeline.json"
        csv_path = self.artifacts_dir / "regional_gray_histogram_timeline.csv"
        markdown_path = self.artifacts_dir / "regional_gray_histogram_timeline.md"

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
        ]
        for method in METHODS:
            for region in REGION_NAMES:
                fieldnames.append(f"{region}_{method}")

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for frame in frames:
                writer.writerow({field: frame[field] for field in fieldnames})

    def _to_markdown(self, report: dict[str, Any]) -> str:
        analysis = report["analysis"]
        lines = [
            "# Regional Gray Histogram Distance Timeline",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Frame Count | {report['summary']['frame_count']} |",
            f"| Same Page Frames | {report['summary']['same_page_frames']} |",
            f"| Page Change Candidate Frames | {report['summary']['page_change_candidate_frames']} |",
            "",
            "## Region Timeline",
            "",
            "| Frame | Previous | Timestamp | Candidate | Region | Bhattacharyya | Chi-Square | Correlation | L1 |",
            "| ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for frame in report["frames"]:
            for region in REGION_NAMES:
                lines.append(region_timeline_row(frame, region))

        lines.extend(
            [
                "",
                "## Observation Analysis",
                "",
                "Grouping: Page Change Candidate uses the existing `page_change_events.json` event frame ranges for observation only.",
                "",
                "### Same Page",
                "",
                "| Region | Method | Count | Minimum | Median | P90 | P95 |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in analysis["same_page"]:
            lines.append(
                f"| {REGION_LABELS[row['region']]} | {row['method']} | "
                f"{row['stats']['count']} | {fmt(row['stats']['minimum'])} | "
                f"{fmt(row['stats']['median'])} | {fmt(row['stats']['p90'])} | "
                f"{fmt(row['stats']['p95'])} |"
            )

        lines.extend(
            [
                "",
                "### Normal Page Change",
                "",
                "| Region | Method | Count | Minimum | Median | P90 | P95 |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in analysis["page_change_candidate"]:
            lines.append(
                f"| {REGION_LABELS[row['region']]} | {row['method']} | "
                f"{row['stats']['count']} | {fmt(row['stats']['minimum'])} | "
                f"{fmt(row['stats']['median'])} | {fmt(row['stats']['p90'])} | "
                f"{fmt(row['stats']['p95'])} |"
            )

        lines.extend(
            [
                "",
                "### P30 to P31 Debug Window",
                "",
                f"Window: {P30_P31_START_SECONDS:g}s to {P30_P31_END_SECONDS:g}s",
                "",
                region_debug_window_table(analysis["p30_p31_window"]),
                "",
            ]
        )
        return "\n".join(lines)


def split_2x2(gray: np.ndarray) -> dict[str, np.ndarray]:
    height, width = gray.shape
    y_cut = height // 2
    x_cut = width // 2
    return {
        "region_00": gray[:y_cut, :x_cut],
        "region_01": gray[:y_cut, x_cut:],
        "region_10": gray[y_cut:, :x_cut],
        "region_11": gray[y_cut:, x_cut:],
    }


def frame_fact(
    frame_index: int,
    total_frames: int,
    duration_seconds: float,
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    event_frames: set[int],
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "frame_index": frame_index,
        "previous_frame_index": frame_index - 1 if previous is not None else None,
        "timestamp_seconds": analysis_timestamp_seconds(
            frame_index,
            total_frames,
            duration_seconds,
        ),
        "is_page_change_candidate": frame_index in event_frames,
    }
    if previous is None:
        for method in METHODS:
            for region in REGION_NAMES:
                base[f"{region}_{method}"] = None
        return base

    for region in REGION_NAMES:
        distances = compare_histograms(
            previous["regions"][region],
            current["regions"][region],
        )
        for method, value in distances.items():
            base[f"{region}_{method}"] = value
    return base


def compare_histograms(previous: np.ndarray, current: np.ndarray) -> dict[str, float]:
    return {
        "bhattacharyya": float(
            cv2.compareHist(previous, current, cv2.HISTCMP_BHATTACHARYYA)
        ),
        "chi_square": float(cv2.compareHist(previous, current, cv2.HISTCMP_CHISQR)),
        "correlation": float(cv2.compareHist(previous, current, cv2.HISTCMP_CORREL)),
        "l1": float(np.sum(np.abs(previous - current))),
    }


def observation_analysis(frames: list[dict[str, Any]]) -> dict[str, Any]:
    same_page: list[dict[str, Any]] = []
    page_change_candidate: list[dict[str, Any]] = []
    for region in REGION_NAMES:
        for method in METHODS:
            field = f"{region}_{method}"
            same_page.append(
                {
                    "region": region,
                    "method": method,
                    "stats": observation_distribution(
                        values_for(frames, field, is_candidate=False)
                    ),
                }
            )
            page_change_candidate.append(
                {
                    "region": region,
                    "method": method,
                    "stats": observation_distribution(
                        values_for(frames, field, is_candidate=True)
                    ),
                }
            )
    p30_window = debug_window(frames, P30_P31_START_SECONDS, P30_P31_END_SECONDS)
    return {
        "same_page": same_page,
        "page_change_candidate": page_change_candidate,
        "p30_p31_window": p30_window,
    }


def observation_distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "p90": None,
            "p95": None,
        }
    array = np.array(values, dtype=np.float64)
    return {
        "count": len(values),
        "minimum": float(np.min(array)),
        "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
        "p95": float(np.percentile(array, 95)),
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
    }


def region_timeline_row(frame: dict[str, Any], region: str) -> str:
    return (
        f"| {frame['frame_index']} | {fmt(frame['previous_frame_index'])} | "
        f"{fmt(frame['timestamp_seconds'])} | {frame['is_page_change_candidate']} | "
        f"{REGION_LABELS[region]} | "
        f"{fmt(frame[f'{region}_bhattacharyya'])} | "
        f"{fmt(frame[f'{region}_chi_square'])} | "
        f"{fmt(frame[f'{region}_correlation'])} | "
        f"{fmt(frame[f'{region}_l1'])} |"
    )


def region_debug_window_table(window: dict[str, Any]) -> str:
    lines = [
        "| Frame | Time | Candidate | Region | Bhattacharyya | Chi-Square | Correlation | L1 |",
        "| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for frame in window["rows"]:
        for region in REGION_NAMES:
            lines.append(region_timeline_row(frame, region))
    return "\n".join(lines)


def main() -> int:
    argus_root = Path(__file__).resolve().parents[1]
    artifacts_dir = argus_root / "output" / "artifacts"
    video_path = find_single_video(argus_root / "input")
    page_change_report = load_json(artifacts_dir / "page_change_events.json")
    report = RegionalGrayHistogramDistanceAnalyzer().analyze(
        video_path=video_path,
        page_change_report=page_change_report,
    )
    paths = RegionalGrayHistogramDistanceReportWriter(artifacts_dir).write(report)
    print("regional_gray_histogram_timeline artifacts:")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
