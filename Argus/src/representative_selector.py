from __future__ import annotations

from typing import Any


class RepresentativeSelector:
    def select(
        self,
        frames: list[dict[str, Any]],
        pages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [select_representative(frames, page) for page in pages]


def select_representative(
    frames: list[dict[str, Any]],
    page: dict[str, Any],
) -> dict[str, Any]:
    page_frames = frames[page["start_frame"] : page["end_frame"] + 1]
    representative = max(
        page_frames,
        key=lambda frame: (frame["laplacian_variance"], -frame["frame_index"]),
    )
    return {
        **page,
        "representative_frame": representative["frame_index"],
        "laplacian_variance": representative["laplacian_variance"],
    }
