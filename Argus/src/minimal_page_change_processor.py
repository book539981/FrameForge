from __future__ import annotations

from typing import Any


class MinimalPageChangeProcessor:
    def __init__(self, page_change_config: dict[str, Any]) -> None:
        self.changed_area_ratio_threshold = required_float(
            page_change_config,
            "changed_area_ratio_threshold",
        )
        self.ssim_threshold = required_float(page_change_config, "ssim_threshold")
        self.ecc_score_minimum = required_float(
            page_change_config,
            "ecc_score_minimum",
        )
        self.alignment_translation_maximum_pixels = required_float(
            page_change_config,
            "alignment_translation_maximum_pixels",
        )
        self.event_merge_gap_seconds = required_float(
            page_change_config,
            "event_merge_gap_seconds",
        )

    def process(self, frames: list[dict[str, Any]]) -> dict[str, Any]:
        events = self._page_change_events(frames)
        pages = self._pages(frames, events)
        return {
            "rule": {
                "page_change_condition": "Decision Tree: changed_area_ratio <= changed_area_ratio_threshold => Same Page; otherwise ssim < ssim_threshold => Page Change; otherwise ECC Translation decides Same Page only when ecc_converged is true, ecc_score >= ecc_score_minimum, abs(ecc_dx) <= alignment_translation_maximum_pixels, and abs(ecc_dy) <= alignment_translation_maximum_pixels.",
                "changed_area_ratio_threshold": self.changed_area_ratio_threshold,
                "ssim_threshold": self.ssim_threshold,
                "ecc_score_minimum": self.ecc_score_minimum,
                "alignment_translation_maximum_pixels": self.alignment_translation_maximum_pixels,
                "event_merge_gap_seconds": self.event_merge_gap_seconds,
                "merge_rule": "Positive Page Change frames are merged into one Page Change Event only when the actual decoded timestamp gap from the previous positive Change Frame is <= event_merge_gap_seconds.",
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

    def _page_change_events(self, frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        current_run: list[dict[str, Any]] = []
        previous_change_frame: dict[str, Any] | None = None

        for frame in frames:
            if not self._is_page_change_frame(frame):
                continue

            if not current_run:
                current_run.append(frame)
                previous_change_frame = frame
                continue

            if self._is_same_event_change_frame(
                previous_change_frame=previous_change_frame,
                current_change_frame=frame,
            ):
                current_run.append(frame)
            else:
                events.append(self._build_event(len(events), current_run))
                current_run = [frame]
            previous_change_frame = frame

        if current_run:
            events.append(self._build_event(len(events), current_run))
        return events

    def _is_same_event_change_frame(
        self,
        previous_change_frame: dict[str, Any] | None,
        current_change_frame: dict[str, Any],
    ) -> bool:
        if previous_change_frame is None:
            return False
        previous_timestamp = previous_change_frame["decoded_timestamp_seconds"]
        current_timestamp = current_change_frame["decoded_timestamp_seconds"]
        if previous_timestamp is None or current_timestamp is None:
            return False
        return (
            current_timestamp - previous_timestamp
        ) <= self.event_merge_gap_seconds

    def _is_page_change_frame(self, frame: dict[str, Any]) -> bool:
        changed_area_ratio = frame["changed_area_ratio"]
        if (
            changed_area_ratio is None
            or changed_area_ratio <= self.changed_area_ratio_threshold
        ):
            return False

        ssim = frame["ssim"]
        if ssim is not None and ssim < self.ssim_threshold:
            return True

        return not self._has_same_page_alignment(frame)

    def _has_same_page_alignment(self, frame: dict[str, Any]) -> bool:
        return (
            frame["ecc_converged"] is True
            and frame["ecc_score"] is not None
            and frame["ecc_score"] >= self.ecc_score_minimum
            and frame["ecc_dx"] is not None
            and abs(frame["ecc_dx"]) <= self.alignment_translation_maximum_pixels
            and frame["ecc_dy"] is not None
            and abs(frame["ecc_dy"]) <= self.alignment_translation_maximum_pixels
        )

    def _build_event(
        self,
        event_index: int,
        run: list[dict[str, Any]],
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "event_index": event_index,
            "start_frame": run[0]["frame_index"],
            "end_frame": run[-1]["frame_index"],
            "frame_count": len(run),
            "changed_area_peak": peak_frame(run, "changed_area_ratio")[
                "changed_area_ratio"
            ],
            "changed_area_peak_frame": peak_frame(run, "changed_area_ratio")[
                "frame_index"
            ],
            "ssim_minimum": trough_frame(run, "ssim")["ssim"],
            "ssim_minimum_frame": trough_frame(run, "ssim")["frame_index"],
            "ecc_score_minimum": trough_frame(run, "ecc_score")["ecc_score"],
            "ecc_score_minimum_frame": trough_frame(run, "ecc_score")["frame_index"],
            "ecc_dx_at_score_minimum": trough_frame(run, "ecc_score")["ecc_dx"],
            "ecc_dy_at_score_minimum": trough_frame(run, "ecc_score")["ecc_dy"],
        }
        return event

    def _pages(
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
                    build_page(
                        page_index=len(pages) + 1,
                        start_frame=page_start,
                        end_frame=page_end,
                        frames=frames,
                        previous_event=previous_event,
                    )
                )
            page_start = event["end_frame"] + 1
            previous_event = event

        if frames and page_start <= frames[-1]["frame_index"]:
            pages.append(
                build_page(
                    page_index=len(pages) + 1,
                    start_frame=page_start,
                    end_frame=frames[-1]["frame_index"],
                    frames=frames,
                    previous_event=previous_event,
                )
            )
        return pages


def build_page(
    page_index: int,
    start_frame: int,
    end_frame: int,
    frames: list[dict[str, Any]],
    previous_event: dict[str, Any] | None,
) -> dict[str, Any]:
    page_frames = frames[start_frame : end_frame + 1]
    representative = max(
        page_frames,
        key=lambda frame: (frame["laplacian_variance"], -frame["frame_index"]),
    )
    return {
        "page_index": page_index,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_count": len(page_frames),
        "representative_frame": representative["frame_index"],
        "laplacian_variance": representative["laplacian_variance"],
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


def required_float(config: dict[str, Any], key: str) -> float:
    value = config.get(key)
    if value is None:
        raise ValueError(f"page_change.{key} is required.")
    return float(value)


def peak_frame(run: list[dict[str, Any]], field: str) -> dict[str, Any]:
    return max(run, key=lambda frame: frame[field])


def trough_frame(run: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [frame for frame in run if frame[field] is not None]
    if not values:
        return run[0]
    return min(values, key=lambda frame: frame[field])
