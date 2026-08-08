from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .comparison_engine import changed_area_ratio, ssim_score
from .image_registration import ecc_translation_facts, finite_float_or_none
from .video_reader import read_metadata


class FrameTimelineAnalyzer:
    def analyze(self, video_path: Path) -> dict[str, Any]:
        metadata = read_metadata(video_path)
        capture = cv2.VideoCapture(str(video_path))
        frames: list[dict[str, Any]] = []
        previous_gray: np.ndarray | None = None
        decoded_frame_count = 0

        try:
            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break

                decoded_timestamp_seconds = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frames.append(
                    frame_fact(
                        frame_index=frame_index,
                        gray=gray,
                        previous_gray=previous_gray,
                        decoded_timestamp_seconds=decoded_timestamp_seconds,
                    )
                )
                previous_gray = gray
                decoded_frame_count += 1
                frame_index += 1
        finally:
            capture.release()

        return {
            "schema_version": "1.0",
            "video_metadata": {
                "filename": metadata.filename,
                "path": metadata.path,
                "width": metadata.width,
                "height": metadata.height,
                "fps": metadata.fps,
                "total_frames": metadata.total_frames,
                "duration_seconds": metadata.duration_seconds,
                "codec_fourcc": metadata.codec_fourcc,
            },
            "timeline_definition": {
                "decode": "Sequential Decode Every Frame",
                "comparison_reference": "frame[n] vs frame[n-1]",
                "decoded_timestamp_seconds": "actual decoded timestamp from cv2.CAP_PROP_POS_MSEC / 1000; official runtime time coordinate",
                "changed_area_ratio": "count of changed grayscale pixels / total pixel count",
                "ssim": "structural similarity score for frame[n] vs frame[n-1]",
                "ecc_translation": "translation-only alignment facts from cv2.findTransformECC with MOTION_TRANSLATION",
                "laplacian_variance": "sharpness fact used for representative frame selection",
            },
            "summary": {
                "decoded_frame_count": decoded_frame_count,
                "frame_fact_count": len(frames),
            },
            "frames": frames,
        }


def frame_fact(
    frame_index: int,
    gray: np.ndarray,
    previous_gray: np.ndarray | None,
    decoded_timestamp_seconds: float,
) -> dict[str, Any]:
    fact: dict[str, Any] = {
        "frame_index": frame_index,
        "previous_frame_index": frame_index - 1 if previous_gray is not None else None,
        "decoded_timestamp_seconds": finite_float_or_none(decoded_timestamp_seconds),
        "changed_area_ratio": None,
        "ssim": None,
        "ecc_converged": None,
        "ecc_score": None,
        "ecc_dx": None,
        "ecc_dy": None,
        "ecc_error": None,
        "laplacian_variance": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
    }

    if previous_gray is None:
        return fact

    fact.update(
        {
            "changed_area_ratio": changed_area_ratio(previous_gray, gray),
            "ssim": ssim_score(previous_gray, gray),
        }
    )
    fact.update(ecc_translation_facts(previous_gray, gray))
    return fact
