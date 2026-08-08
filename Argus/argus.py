from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import yaml

from src.frame_difference_timeline_analyzer import FrameDifferenceTimelineAnalyzer
from src.frame_difference_timeline_report_writer import (
    FrameDifferenceTimelineReportWriter,
)
from src.minimal_page_change_processor import MinimalPageChangeProcessor
from src.page_change_events_report_writer import PageChangeEventsReportWriter
from src.page_exporter import PageExporter
from src.video_reader import find_single_video


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _load_config(argus_root: Path) -> dict:
    config_path = argus_root / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> int:
    _configure_logging()
    started_at = time.perf_counter()
    argus_root = Path(__file__).resolve().parent

    try:
        config = _load_config(argus_root)
        input_dir = argus_root / config["input"]["directory"]
        artifacts_dir = argus_root / config["output"]["artifacts_directory"]
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        video_path = find_single_video(input_dir)
        report = FrameDifferenceTimelineAnalyzer().analyze(video_path)
        page_change_config = config["page_change"]
        page_change_report = MinimalPageChangeProcessor(page_change_config).process(
            report["frames"]
        )
        (
            json_path,
            csv_path,
            markdown_path,
        ) = FrameDifferenceTimelineReportWriter(artifacts_dir=artifacts_dir).write(
            report
        )
        (
            page_change_events_path,
            page_change_events_csv_path,
            page_change_events_markdown_path,
        ) = PageChangeEventsReportWriter(artifacts_dir=artifacts_dir).write(
            page_change_report
        )
        page_export_paths = PageExporter(
            output_dir=argus_root / page_change_config["output_directory"]
        ).export(
            video_path=video_path,
            pages=page_change_report["pages"],
        )

        elapsed = time.perf_counter() - started_at
        metadata = report["video_metadata"]
        summary = report["summary"]

        print()
        print("Argus Frame Difference Timeline")
        print()
        print("Input:")
        print(f"  {video_path.name}")
        print()
        print("Video:")
        print(f"  {metadata['width']} x {metadata['height']}")
        print(f"  {metadata['fps']:.3f} FPS")
        print(f"  {metadata['duration_seconds']:.1f} seconds")
        print(f"  {metadata['total_frames']} metadata frames")
        print()
        print("Frame Difference Facts:")
        print(f"  {summary['decoded_frame_count']} decoded frames")
        print(f"  {summary['frame_fact_count']} frame facts")
        print(f"  Page Change Rule: {summary['has_page_change_rule']}")
        print(f"  Threshold: {summary['has_threshold']}")
        print(f"  Long Lookback: {summary['has_long_lookback']}")
        print(f"  Stable Rule: {summary['has_stable_rule']}")
        print()
        print("Reports:")
        print(f"  {json_path.relative_to(argus_root)}")
        print(f"  {markdown_path.relative_to(argus_root)}")
        print(f"  {csv_path.relative_to(argus_root)}")
        print(f"  {page_change_events_path.relative_to(argus_root)}")
        print(f"  {page_change_events_markdown_path.relative_to(argus_root)}")
        print(f"  {page_change_events_csv_path.relative_to(argus_root)}")
        print()
        print("Minimal Page Change:")
        print(
            f"  ecc_score_minimum: {page_change_report['rule']['ecc_score_minimum']:.6f}"
        )
        print(
            "  alignment_translation_maximum_pixels: "
            f"{page_change_report['rule']['alignment_translation_maximum_pixels']:.6f}"
        )
        print(
            f"  {page_change_report['summary']['page_change_event_count']} page change events"
        )
        print(
            f"  {page_change_report['summary']['representative_count']} representatives"
        )
        print(f"  {len(page_export_paths)} exported PNG files")
        print()
        print(f"Completed in {elapsed:.1f} seconds.")
        return 0
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
