from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


@dataclass(frozen=True)
class DecodedFrame:
    frame_index: int
    timestamp_seconds: float
    frame: np.ndarray


class SequentialFrameSource:
    def __init__(self, video_path: Path, fps: float, expected_total_frames: int | None = None) -> None:
        self.video_path = video_path
        self.fps = fps
        self.expected_total_frames = expected_total_frames
        self.decoded_frame_count = 0
        self.last_decoded_frame_index: int | None = None
        self.decode_failure_count = 0

    def __iter__(self) -> Iterator[DecodedFrame]:
        capture = cv2.VideoCapture(str(self.video_path))
        try:
            if not capture.isOpened():
                raise ValueError(f"Could not open video: {self.video_path}")

            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break

                timestamp = self._timestamp(frame_index)
                self.decoded_frame_count += 1
                self.last_decoded_frame_index = frame_index
                yield DecodedFrame(
                    frame_index=frame_index,
                    timestamp_seconds=timestamp,
                    frame=frame,
                )
                frame_index += 1
        finally:
            capture.release()

        if (
            self.expected_total_frames is not None
            and self.expected_total_frames > 0
            and self.decoded_frame_count < self.expected_total_frames
        ):
            self.decode_failure_count = 1

    def _timestamp(self, frame_index: int) -> float:
        if self.fps <= 0:
            return 0.0
        return frame_index / self.fps
