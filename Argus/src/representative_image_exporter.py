from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2


class RepresentativeImageExporter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def export(
        self,
        video_path: Path,
        representative_report: dict[str, Any],
    ) -> tuple[list[Path], Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for old_page in self.output_dir.glob("page_*.png"):
            old_page.unlink()

        representatives = representative_report["segment_results"]
        frame_targets = {
            representative["representative_frame_index"]: representative
            for representative in representatives
        }
        exported_paths: list[Path] = []

        capture = cv2.VideoCapture(str(video_path))
        try:
            frame_index = 0
            while frame_targets:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                representative = frame_targets.pop(frame_index, None)
                if representative is not None:
                    image_path = self.output_dir / page_filename(
                        representative["segment_index"]
                    )
                    cv2.imwrite(str(image_path), frame)
                    exported_paths.append(image_path)
                frame_index += 1
        finally:
            capture.release()

        markdown_path = self.output_dir / "representative_pages.md"
        markdown_path.write_text(
            self._to_markdown(representatives),
            encoding="utf-8",
        )
        return exported_paths, markdown_path

    def _to_markdown(self, representatives: list[dict[str, Any]]) -> str:
        lines = [
            "# Representative Pages Debug Export",
            "",
        ]
        for representative in representatives:
            lines.extend(
                [
                    f"## Segment {representative['segment_index']}",
                    "",
                    "Representative",
                    "",
                    f"`{page_filename(representative['segment_index'])}`",
                    "",
                    f"- frame_index = {representative['representative_frame_index']}",
                    f"- sample_index = {representative['representative_sample_index']}",
                    f"- laplacian = {representative['representative_laplacian_variance']}",
                    "",
                ]
            )
        return "\n".join(lines)


def page_filename(segment_index: int) -> str:
    return f"page_{segment_index + 1:03d}.png"
