from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from src.rapidocr_calibration import OCRPageFacts, RapidOCRCalibration


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run RapidOCR PP-OCRv5 on specified page PNG files."
    )
    parser.add_argument(
        "images",
        nargs="+",
        type=Path,
        help="One or more page image paths, for example output/page_export/page_001.png.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "artifacts" / "ocr_calibration",
        help="Directory for UTF-8 raw OCR output and debug facts.",
    )
    parser.add_argument(
        "--model-root-dir",
        type=Path,
        default=None,
        help="Optional RapidOCR model cache directory.",
    )
    return parser.parse_args()


def main() -> int:
    _configure_logging()
    started_at = time.perf_counter()
    argus_root = Path(__file__).resolve().parent
    args = _parse_args()
    output_dir = _resolve_path(argus_root, args.output_dir)
    model_root_dir = (
        _resolve_path(argus_root, args.model_root_dir)
        if args.model_root_dir is not None
        else None
    )

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        engine = RapidOCRCalibration(model_root_dir=model_root_dir)
        page_facts = [
            engine.read_image(_resolve_path(argus_root, image_path))
            for image_path in args.images
        ]
        raw_text_path = output_dir / "raw_ocr_text.txt"
        debug_json_path = output_dir / "raw_ocr_debug_facts.json"

        raw_text_path.write_text(_format_raw_text(page_facts), encoding="utf-8")
        with debug_json_path.open("w", encoding="utf-8") as handle:
            json.dump(
                [page.to_debug_dict() for page in page_facts],
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")

        elapsed = time.perf_counter() - started_at
        print()
        print("RapidOCR Calibration")
        print()
        print("Input:")
        for page in page_facts:
            print(f"  {page.source_image.name}")
        print()
        print("Output:")
        print(f"  {raw_text_path.relative_to(argus_root)}")
        print(f"  {debug_json_path.relative_to(argus_root)}")
        print()
        print(f"Completed in {elapsed:.1f} seconds.")
        return 0
    except Exception as exc:
        logging.error("%s", exc)
        return 1


def _resolve_path(argus_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return argus_root / path


def _format_raw_text(page_facts: list[OCRPageFacts]) -> str:
    sections: list[str] = []
    for page in page_facts:
        sections.append(f"{page.source_image.name}\n{page.raw_text}")
    return "\n\n".join(sections) + "\n"


if __name__ == "__main__":
    sys.exit(main())
