from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import yaml

from src.report_writer import ReportWriter
from src.stable_page_processor import StablePageProcessor
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
        stable_segments_report = StablePageProcessor(config=config, argus_root=argus_root).process(video_path)

        writer = ReportWriter(config=config, argus_root=argus_root)
        stable_segments_path = writer.write_stable_segments(stable_segments_report)

        elapsed = time.perf_counter() - started_at
        metadata = stable_segments_report["video_metadata"]
        summary = stable_segments_report["execution_summary"]

        print()
        print("Argus Stable Page Extraction")
        print()
        print("Input:")
        print(f"  {video_path.name}")
        print()
        print("Video:")
        print(f"  {metadata['width']} x {metadata['height']}")
        print(f"  {metadata['fps']:.3f} FPS")
        print(f"  {metadata['duration_seconds']:.1f} seconds")
        print(f"  {metadata['total_frames']} frames")
        print()
        print("Sampling:")
        print(f"  frame interval: {summary['frame_interval']}")
        print(f"  {summary['sampled_frame_count']} sampled frames")
        print()
        print("Outputs:")
        print(f"  {stable_segments_path.relative_to(argus_root)}")
        print(f"  {Path(config['output']['pages_directory']) / 'page_001.png'} ...")
        print()
        print(f"Completed in {elapsed:.1f} seconds.")
        return 0
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
