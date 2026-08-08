from __future__ import annotations

from typing import Any

from .page_change_rule import PageChangeRule, required_float


class PageChangeEventMerger:
    def __init__(
        self,
        page_change_rule: PageChangeRule,
        page_change_config: dict[str, Any],
    ) -> None:
        self.page_change_rule = page_change_rule
        self.event_merge_gap_seconds = required_float(
            page_change_config,
            "event_merge_gap_seconds",
        )

    def merge(self, frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        current_run: list[dict[str, Any]] = []
        previous_change_frame: dict[str, Any] | None = None

        for frame in frames:
            if not self.page_change_rule.is_page_change(frame):
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
                events.append(build_event(len(events), current_run))
                current_run = [frame]
            previous_change_frame = frame

        if current_run:
            events.append(build_event(len(events), current_run))
        return events

    def summary(self) -> dict[str, Any]:
        return {
            "event_merge_gap_seconds": self.event_merge_gap_seconds,
            "merge_rule": "Positive Page Change frames are merged into one Page Change Event only when the actual decoded timestamp gap from the previous positive Change Frame is <= event_merge_gap_seconds.",
        }

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


def build_event(event_index: int, run: list[dict[str, Any]]) -> dict[str, Any]:
    score_frame = trough_frame(run, "ecc_score")
    return {
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
        "ecc_score_minimum": score_frame["ecc_score"],
        "ecc_score_minimum_frame": score_frame["frame_index"],
        "ecc_dx_at_score_minimum": score_frame["ecc_dx"],
        "ecc_dy_at_score_minimum": score_frame["ecc_dy"],
    }


def peak_frame(run: list[dict[str, Any]], field: str) -> dict[str, Any]:
    return max(run, key=lambda frame: frame[field])


def trough_frame(run: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [frame for frame in run if frame[field] is not None]
    if not values:
        return run[0]
    return min(values, key=lambda frame: frame[field])
