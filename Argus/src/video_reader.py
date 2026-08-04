from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".avi"}


@dataclass(frozen=True)
class VideoMetadata:
    filename: str
    path: str
    size_bytes: int
    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float
    duration_formatted: str
    codec_fourcc: str
    is_opened: bool


def find_single_video(input_dir: Path) -> Path:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    videos = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
    )

    if not videos:
        raise FileNotFoundError(f"No supported video found in {input_dir}")
    if len(videos) > 1:
        names = ", ".join(path.name for path in videos)
        raise ValueError(f"Expected exactly one video in {input_dir}, found {len(videos)}: {names}")
    return videos[0]


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def decode_fourcc(value: float) -> str:
    code = int(value)
    chars = [chr((code >> 8 * index) & 0xFF) for index in range(4)]
    decoded = "".join(chars).strip("\x00").strip()
    return decoded or "unknown"


def read_metadata(video_path: Path) -> VideoMetadata:
    capture = cv2.VideoCapture(str(video_path))
    try:
        is_opened = bool(capture.isOpened())
        if not is_opened:
            raise ValueError(f"Could not open video: {video_path}")

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fourcc = decode_fourcc(capture.get(cv2.CAP_PROP_FOURCC) or 0)
        duration = total_frames / fps if fps > 0 else 0.0

        return VideoMetadata(
            filename=video_path.name,
            path=str(video_path),
            size_bytes=video_path.stat().st_size,
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            duration_seconds=duration,
            duration_formatted=format_duration(duration),
            codec_fourcc=fourcc,
            is_opened=is_opened,
        )
    finally:
        capture.release()

def timestamp_for_frame(frame_index: int, fps: float) -> float:
    return round(frame_index / fps, 6) if fps > 0 else 0.0
