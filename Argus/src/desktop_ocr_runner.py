from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from .rapidocr_calibration import OCRPageFacts, RapidOCRCalibration


ProgressCallback = Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class OCRBatchResult:
    output_text_path: Path
    page_count: int


class OCRBatchCancelled(RuntimeError):
    pass


def run_ocr_batch(
    image_dir: Path,
    model_root_dir: Path,
    cancel_event: Event,
    progress_callback: ProgressCallback,
) -> OCRBatchResult:
    source_dir = image_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Image folder does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise ValueError(f"Image path is not a folder: {source_dir}")

    images = sorted(source_dir.glob("page_*.png"))
    if not images:
        raise FileNotFoundError(f"No page_*.png files found in {source_dir}")

    output_text_path = source_dir / "raw_ocr_text.txt"
    _emit(progress_callback, "OCR", "初始化 RapidOCR", current=0, total=len(images))
    engine = RapidOCRCalibration(model_root_dir=model_root_dir)

    page_facts: list[OCRPageFacts] = []
    for index, image_path in enumerate(images, start=1):
        _check_cancelled(cancel_event)
        _emit(
            progress_callback,
            "OCR",
            "辨識圖片",
            current=index - 1,
            total=len(images),
            filename=image_path.name,
        )
        page_facts.append(engine.read_image(image_path))
        _emit(
            progress_callback,
            "OCR",
            "完成一張圖片",
            current=index,
            total=len(images),
            filename=image_path.name,
        )

    _check_cancelled(cancel_event)
    output_text_path.write_text(_format_raw_text(page_facts), encoding="utf-8")
    _emit(
        progress_callback,
        "OCR",
        "完成",
        current=len(images),
        total=len(images),
        filename=output_text_path.name,
    )
    return OCRBatchResult(output_text_path=output_text_path, page_count=len(images))


def _format_raw_text(page_facts: list[OCRPageFacts]) -> str:
    sections: list[str] = []
    for page in page_facts:
        sections.append(f"{page.source_image.name}\n{page.raw_text}")
    return "\n\n".join(sections) + "\n"


def _check_cancelled(cancel_event: Event) -> None:
    if cancel_event.is_set():
        raise OCRBatchCancelled("OCR cancelled.")


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
