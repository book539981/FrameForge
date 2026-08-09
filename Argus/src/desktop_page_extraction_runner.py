from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

import yaml

from .frame_timeline_analyzer import FrameTimelineAnalyzer
from .frame_timeline_report_writer import FrameTimelineReportWriter
from .page_change_event_merger import PageChangeEventMerger
from .page_change_events_report_writer import PageChangeEventsReportWriter
from .page_change_rule import PageChangeRule
from .page_exporter import PageExporter
from .page_segment_builder import PageSegmentBuilder
from .representative_selector import RepresentativeSelector


ProgressCallback = Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class PageExtractionResult:
    page_export_dir: Path
    exported_paths: list[Path]
    frame_count: int
    page_count: int


class PageExtractionCancelled(RuntimeError):
    pass


def run_page_extraction(
    argus_root: Path,
    video_path: Path,
    cancel_event: Event,
    progress_callback: ProgressCallback,
) -> PageExtractionResult:
    argus_root = argus_root.resolve()
    source_video = video_path.resolve()
    config = _load_config(argus_root)
    artifacts_dir = argus_root / config["output"]["artifacts_directory"]
    page_change_config = config["page_change"]
    page_export_dir = argus_root / page_change_config["output_directory"]

    _check_cancelled(cancel_event)
    _emit(progress_callback, "圖片擷取", "讀取影片", filename=source_video.name)

    _check_cancelled(cancel_event)
    _emit(progress_callback, "圖片擷取", "分析影片 Frames")
    report = FrameTimelineAnalyzer().analyze(source_video)

    _check_cancelled(cancel_event)
    _emit(progress_callback, "圖片擷取", "套用既有 Page Change Rule")
    page_change_rule = PageChangeRule(page_change_config)
    event_merger = PageChangeEventMerger(page_change_rule, page_change_config)
    events = event_merger.merge(report["frames"])

    _check_cancelled(cancel_event)
    _emit(progress_callback, "圖片擷取", "建立 Page Segments")
    page_segments = PageSegmentBuilder().build(report["frames"], events)

    _check_cancelled(cancel_event)
    _emit(progress_callback, "圖片擷取", "選擇 Representative Frames")
    pages = RepresentativeSelector().select(report["frames"], page_segments)

    page_change_report = {
        "rule": {
            **page_change_rule.summary(),
            **event_merger.summary(),
            "representative_frame_rule": "For each Page Segment, select the frame with maximum laplacian_variance.",
        },
        "events": events,
        "pages": pages,
        "summary": {
            "page_change_event_count": len(events),
            "representative_count": len(pages),
            "exported_page_count": len(pages),
        },
    }

    _check_cancelled(cancel_event)
    _emit(progress_callback, "圖片擷取", "寫入 Reports")
    FrameTimelineReportWriter(artifacts_dir=artifacts_dir).write(report)
    PageChangeEventsReportWriter(artifacts_dir=artifacts_dir).write(page_change_report)

    _check_cancelled(cancel_event)
    _emit(
        progress_callback,
        "圖片擷取",
        "輸出 page_export",
        current=0,
        total=len(pages),
    )
    exported_paths = PageExporter(output_dir=page_export_dir).export(
        video_path=source_video,
        pages=page_change_report["pages"],
    )

    _check_cancelled(cancel_event)
    _emit(
        progress_callback,
        "圖片擷取",
        "完成",
        current=len(exported_paths),
        total=len(pages),
    )
    return PageExtractionResult(
        page_export_dir=page_export_dir,
        exported_paths=exported_paths,
        frame_count=len(report["frames"]),
        page_count=len(exported_paths),
    )


def _load_config(argus_root: Path) -> dict:
    config_path = argus_root / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _check_cancelled(cancel_event: Event) -> None:
    if cancel_event.is_set():
        raise PageExtractionCancelled("Page extraction cancelled.")


def _emit(
    progress_callback: ProgressCallback,
    stage: str,
    status: str,
    current: int | None = None,
    total: int | None = None,
    filename: str | None = None,
) -> None:
    progress_callback(
        {
            "kind": "progress",
            "stage": stage,
            "status": status,
            "current": current,
            "total": total,
            "filename": filename,
        }
    )
