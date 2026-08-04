from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import yaml

from src.analyzer import VideoAnalyzer
from src.report_writer import ReportWriter
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
        analyzer = VideoAnalyzer(config=config, argus_root=argus_root)
        report = analyzer.analyze(video_path)

        writer = ReportWriter(config=config, argus_root=argus_root)
        json_path, markdown_path = writer.write(report)

        elapsed = time.perf_counter() - started_at
        metadata = report["video_metadata"]
        sampling = report["sampling"]
        roi = report["roi_recommendation"]

        print()
        print("Argus Video Analyzer")
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
        print(f"  {sampling['sampling_rate']:g} samples/second")
        print(f"  {sampling['sampled_frames']} sampled frames")
        print()
        print("ROI recommendation:")
        print(f"  Top: {roi['top_crop_recommendation']} px")
        print(f"  Bottom: {roi['bottom_crop_recommendation']} px")
        print(f"  Confidence: {roi['confidence']}")
        print()
        print("Reports:")
        print(f"  {json_path.relative_to(argus_root)}")
        print(f"  {markdown_path.relative_to(argus_root)}")
        print()
        print(f"Completed in {elapsed:.1f} seconds.")
        return 0
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
