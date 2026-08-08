from __future__ import annotations

from typing import Any


class PageSegmentBuilder:
    def build(
        self,
        frames: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        page_start = 0
        previous_event = None

        for event in events:
            page_end = event["start_frame"] - 1
            if page_start <= page_end:
                pages.append(
                    build_page_segment(
                        page_index=len(pages) + 1,
                        start_frame=page_start,
                        end_frame=page_end,
                        previous_event=previous_event,
                    )
                )
            elif previous_event is not None:
                pages.append(
                    build_page_segment(
                        page_index=len(pages) + 1,
                        start_frame=previous_event["end_frame"],
                        end_frame=previous_event["end_frame"],
                        previous_event=previous_event,
                    )
                )
            page_start = event["end_frame"] + 1
            previous_event = event

        if frames and page_start <= frames[-1]["frame_index"]:
            pages.append(
                build_page_segment(
                    page_index=len(pages) + 1,
                    start_frame=page_start,
                    end_frame=frames[-1]["frame_index"],
                    previous_event=previous_event,
                )
            )
        return pages


def build_page_segment(
    page_index: int,
    start_frame: int,
    end_frame: int,
    previous_event: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "page_index": page_index,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_count": end_frame - start_frame + 1,
        "changed_area_peak": previous_event["changed_area_peak"]
        if previous_event is not None
        else None,
        "ssim_minimum": previous_event["ssim_minimum"]
        if previous_event is not None
        else None,
        "ecc_score_minimum": previous_event["ecc_score_minimum"]
        if previous_event is not None
        else None,
        "ecc_dx_at_score_minimum": previous_event["ecc_dx_at_score_minimum"]
        if previous_event is not None
        else None,
        "ecc_dy_at_score_minimum": previous_event["ecc_dy_at_score_minimum"]
        if previous_event is not None
        else None,
        "source_event_index": previous_event["event_index"]
        if previous_event is not None
        else None,
    }
