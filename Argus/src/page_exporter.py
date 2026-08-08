from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2


class PageExporter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def export(
        self,
        video_path: Path,
        pages: list[dict[str, Any]],
    ) -> list[Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for old_page in self.output_dir.glob("page_*.png"):
            old_page.unlink()

        targets = {
            page["representative_frame"]: page
            for page in pages
        }
        exported_paths: list[Path] = []

        capture = cv2.VideoCapture(str(video_path))
        try:
            frame_index = 0
            while targets:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                page = targets.pop(frame_index, None)
                if page is not None:
                    image_path = self.output_dir / page_filename(page["page_index"])
                    cv2.imwrite(str(image_path), frame)
                    exported_paths.append(image_path)
                frame_index += 1
        finally:
            capture.release()

        return exported_paths


def page_filename(page_index: int) -> str:
    return f"page_{page_index:03d}.png"
