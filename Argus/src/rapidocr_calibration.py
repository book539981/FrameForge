from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OCRLineFact:
    recognized_text: str
    confidence: float | None
    bounding_box: list[list[float]] | None


@dataclass(frozen=True)
class OCRPageFacts:
    source_image: Path
    recognized_lines: list[OCRLineFact]

    @property
    def raw_text(self) -> str:
        return "\n".join(line.recognized_text for line in self.recognized_lines)

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "source_image": str(self.source_image),
            "recognized_text": self.raw_text,
            "lines": [
                {
                    "recognized_text": line.recognized_text,
                    "confidence": line.confidence,
                    "bounding_box": line.bounding_box,
                }
                for line in self.recognized_lines
            ],
        }


class RapidOCRCalibration:
    def __init__(self, model_root_dir: Path | None = None) -> None:
        try:
            from rapidocr import RapidOCR
            from rapidocr.utils.typings import EngineType, LangCls, LangDet, LangRec
            from rapidocr.utils.typings import ModelType, OCRVersion
        except ImportError as exc:
            raise RuntimeError(
                "RapidOCR is not installed. Install the minimal local OCR runtime "
                "with: python -m pip install rapidocr onnxruntime"
            ) from exc

        params: dict[str, Any] = {
            "Global.log_level": "warning",
            "Global.text_score": 0.0,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet.CH,
            "Det.model_type": ModelType.MOBILE,
            "Det.ocr_version": OCRVersion.PPOCRV5,
            "Cls.engine_type": EngineType.ONNXRUNTIME,
            "Cls.lang_type": LangCls.CH,
            "Cls.model_type": ModelType.MOBILE,
            "Cls.ocr_version": OCRVersion.PPOCRV5,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.lang_type": LangRec.CH,
            "Rec.model_type": ModelType.MOBILE,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
        }
        if model_root_dir is not None:
            params["Global.model_root_dir"] = str(model_root_dir)

        self.engine = RapidOCR(params=params)

    def read_image(self, image_path: Path) -> OCRPageFacts:
        source_image = image_path.resolve()
        if not source_image.exists():
            raise FileNotFoundError(f"Image not found: {source_image}")
        if not source_image.is_file():
            raise ValueError(f"Image path is not a file: {source_image}")

        result = self.engine(source_image)
        return OCRPageFacts(
            source_image=source_image,
            recognized_lines=_extract_line_facts(result),
        )


def _extract_line_facts(result: Any) -> list[OCRLineFact]:
    texts = _as_list(getattr(result, "txts", None))
    scores = _as_list(getattr(result, "scores", None))
    boxes = _as_list(getattr(result, "boxes", None))

    lines: list[OCRLineFact] = []
    for index, text in enumerate(texts):
        lines.append(
            OCRLineFact(
                recognized_text=str(text),
                confidence=_maybe_float(_get_optional(scores, index)),
                bounding_box=_normalize_box(_get_optional(boxes, index)),
            )
        )
    return lines


def _as_list(value: Any | None) -> list[Any]:
    if value is None:
        return []
    return list(value)


def _get_optional(values: list[Any], index: int) -> Any | None:
    if index >= len(values):
        return None
    return values[index]


def _maybe_float(value: Any | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _normalize_box(value: Any | None) -> list[list[float]] | None:
    if value is None:
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [[float(point[0]), float(point[1])] for point in value]
