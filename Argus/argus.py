from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import yaml

from src.anchor_comparison_processor import AnchorComparisonProcessor
from src.anchor_comparison_report_writer import AnchorComparisonReportWriter
from src.analyzer import VideoAnalyzer
from src.candidate_timeline_report_writer import CandidateTimelineReportWriter
from src.comparison_engine import ComparisonEngine
from src.ground_truth_statistics import (
    GroundTruthStatistics,
    GroundTruthStatisticsWriter,
)
from src.ground_truth_calibration_analyzer import (
    GroundTruthCalibrationAnalyzer,
    GroundTruthCalibrationWriter,
)
from src.metric_separation_analyzer import (
    MetricSeparationAnalyzer,
    MetricSeparationWriter,
)
from src.report_writer import ReportWriter
from src.representative_image_exporter import RepresentativeImageExporter
from src.representative_selection_processor import RepresentativeSelectionProcessor
from src.representative_selection_report_writer import RepresentativeSelectionReportWriter
from src.stable_segment_report_writer import StableSegmentReportWriter
from src.stable_rules import StableCandidateRule
from src.stable_segment_processor import StableSegmentProcessor
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

        stable_config = config["stable_candidate"]
        stable_rule = StableCandidateRule(
            adjacent_difference_maximum=float(
                stable_config["adjacent_difference_maximum"]
            ),
            long_lookback_difference_maximum=float(
                stable_config["long_lookback_difference_maximum"]
            ),
        )
        stable_processor = StableSegmentProcessor(rule=stable_rule)
        stable_segments_report = stable_processor.process(report["sampled_frames"])
        anchor_comparison_processor = AnchorComparisonProcessor(
            comparison_engine=ComparisonEngine()
        )
        anchor_comparison_report = anchor_comparison_processor.process(
            samples=report["sampled_frames"],
            sample_grays=analyzer.sample_grays,
            candidate_segments=stable_segments_report["candidate_segments"],
        )
        representative_selection_report = RepresentativeSelectionProcessor().process(
            samples=report["sampled_frames"],
            candidate_segments=stable_segments_report["candidate_segments"],
            anchor_comparison_report=anchor_comparison_report,
        )
        candidate_timeline_writer = CandidateTimelineReportWriter(
            artifacts_dir=artifacts_dir
        )
        candidate_timeline_rows = candidate_timeline_writer.build_rows(
            samples=report["sampled_frames"],
            stable_segments_report=stable_segments_report,
        )
        ground_truth_statistics_report = GroundTruthStatistics(
            comparison_engine=ComparisonEngine()
        ).build(
            samples=report["sampled_frames"],
            sample_grays=analyzer.sample_grays,
        )
        metric_separation_report = MetricSeparationAnalyzer().analyze(
            ground_truth_statistics_report=ground_truth_statistics_report,
            config=config,
        )
        ground_truth_calibration_report = GroundTruthCalibrationAnalyzer().analyze(
            samples=report["sampled_frames"],
        )

        writer = ReportWriter(config=config, argus_root=argus_root)
        json_path, markdown_path = writer.write(report)
        stable_writer = StableSegmentReportWriter(artifacts_dir=artifacts_dir)
        (
            stable_segments_path,
            stable_segments_markdown_path,
            stable_segments_csv_path,
        ) = stable_writer.write(stable_segments_report, stable_config)
        anchor_comparison_writer = AnchorComparisonReportWriter(artifacts_dir=artifacts_dir)
        (
            anchor_comparison_path,
            anchor_comparison_markdown_path,
            anchor_comparison_csv_path,
        ) = anchor_comparison_writer.write(anchor_comparison_report)
        representative_selection_writer = RepresentativeSelectionReportWriter(
            artifacts_dir=artifacts_dir
        )
        (
            representative_selection_path,
            representative_selection_markdown_path,
            representative_selection_csv_path,
        ) = representative_selection_writer.write(representative_selection_report)
        (
            candidate_timeline_path,
            candidate_timeline_markdown_path,
            candidate_timeline_csv_path,
        ) = candidate_timeline_writer.write(
            candidate_timeline_rows,
            stable_segments_report,
        )
        ground_truth_statistics_writer = GroundTruthStatisticsWriter(
            artifacts_dir=artifacts_dir
        )
        (
            ground_truth_statistics_path,
            ground_truth_statistics_csv_path,
            ground_truth_statistics_markdown_path,
        ) = ground_truth_statistics_writer.write(ground_truth_statistics_report)
        metric_separation_writer = MetricSeparationWriter(artifacts_dir=artifacts_dir)
        (
            metric_separation_path,
            metric_separation_csv_path,
            metric_separation_markdown_path,
        ) = metric_separation_writer.write(metric_separation_report)
        ground_truth_calibration_writer = GroundTruthCalibrationWriter(
            artifacts_dir=artifacts_dir
        )
        (
            calibrated_ground_truth_path,
            calibrated_ground_truth_csv_path,
            calibrated_ground_truth_markdown_path,
        ) = ground_truth_calibration_writer.write(ground_truth_calibration_report)
        representative_pages_dir = argus_root / "output" / "representative_pages"
        representative_page_paths, representative_pages_markdown_path = (
            RepresentativeImageExporter(output_dir=representative_pages_dir).export(
                video_path=video_path,
                representative_report=representative_selection_report,
            )
        )

        elapsed = time.perf_counter() - started_at
        metadata = report["video_metadata"]
        sampling = report["sampling"]
        diagnostics = report["reader_diagnostics"]
        stable_summary = stable_segments_report["summary"]

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
        print(f"  {diagnostics['failed_sample_count']} failed samples")
        print()
        print("Reader diagnostics:")
        print(f"  {diagnostics['decoded_frame_count']} sequential decoded frames")
        print(f"  Last successful frame: {diagnostics['last_successful_frame_index']}")
        print(f"  First failed frame: {diagnostics['first_failed_frame_index']}")
        print()
        print("Reports:")
        print(f"  {json_path.relative_to(argus_root)}")
        print(f"  {markdown_path.relative_to(argus_root)}")
        print(f"  {stable_segments_path.relative_to(argus_root)}")
        print(f"  {stable_segments_markdown_path.relative_to(argus_root)}")
        print(f"  {stable_segments_csv_path.relative_to(argus_root)}")
        print(f"  {anchor_comparison_path.relative_to(argus_root)}")
        print(f"  {anchor_comparison_markdown_path.relative_to(argus_root)}")
        print(f"  {anchor_comparison_csv_path.relative_to(argus_root)}")
        print(f"  {representative_selection_path.relative_to(argus_root)}")
        print(f"  {representative_selection_markdown_path.relative_to(argus_root)}")
        print(f"  {representative_selection_csv_path.relative_to(argus_root)}")
        print(f"  {candidate_timeline_path.relative_to(argus_root)}")
        print(f"  {candidate_timeline_markdown_path.relative_to(argus_root)}")
        print(f"  {candidate_timeline_csv_path.relative_to(argus_root)}")
        print(f"  {ground_truth_statistics_path.relative_to(argus_root)}")
        print(f"  {ground_truth_statistics_markdown_path.relative_to(argus_root)}")
        print(f"  {ground_truth_statistics_csv_path.relative_to(argus_root)}")
        print(f"  {metric_separation_path.relative_to(argus_root)}")
        print(f"  {metric_separation_markdown_path.relative_to(argus_root)}")
        print(f"  {metric_separation_csv_path.relative_to(argus_root)}")
        print(f"  {calibrated_ground_truth_path.relative_to(argus_root)}")
        print(f"  {calibrated_ground_truth_markdown_path.relative_to(argus_root)}")
        print(f"  {calibrated_ground_truth_csv_path.relative_to(argus_root)}")
        print(f"  {representative_pages_markdown_path.relative_to(argus_root)}")
        print()
        print("Stable Candidate Segments:")
        print(f"  {stable_summary['candidate_segment_count']} candidate segments")
        print(f"  {stable_summary['stable_candidate_sample_count']} stable candidate samples")
        print(f"  {len(candidate_timeline_rows) - stable_summary['stable_candidate_sample_count']} rejected samples")
        print(
            f"  {ground_truth_statistics_report['summary']['window_count']} ground truth windows"
        )
        print(
            f"  {ground_truth_calibration_report['summary']['total_assigned_samples']} calibration observation samples"
        )
        print(f"  {len(representative_page_paths)} representative PNG files")
        print()
        print(f"Completed in {elapsed:.1f} seconds.")
        return 0
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
