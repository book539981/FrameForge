from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .comparison_engine import ssim_score
from .gray_histogram_distance_analyzer import normalized_gray_histogram
from .regional_gray_histogram_distance_analyzer import (
    METHODS as HISTOGRAM_METHODS,
    REGION_NAMES,
    compare_histograms,
    split_2x2,
)
from .video_reader import read_metadata


class FrameDifferenceTimelineAnalyzer:
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
                    frame_difference_fact(
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
                "difference_mean": "mean absolute grayscale difference normalized by 255",
                "changed_pixel_count": "count of grayscale pixels where absolute adjacent-frame difference is non-zero",
                "changed_area_ratio": "changed_pixel_count / total_pixel_count",
                "ssim": "structural similarity score for frame[n] vs frame[n-1]; observation only, not used by rules",
                "binary_pixel_change_count": "count of pixels whose dark/light class changed between adjacent grayscale frames; dark is gray < 127, light is gray >= 127",
                "binary_pixel_change_ratio": "binary_pixel_change_count / total_pixel_count; observation only, not used by rules",
                "regional_gray_histogram": "2x2 regional grayscale histogram distances for adjacent frames.",
                "phase_correlation": "translation-only alignment facts from cv2.phaseCorrelate for adjacent grayscale frames; observation only, not used by rules",
                "ecc_translation": "translation-only alignment facts from cv2.findTransformECC with MOTION_TRANSLATION; observation only, not used by rules",
                "post_alignment": "difference facts after translation alignment; observation only, not used by rules",
                "rules": [],
            },
            "summary": {
                "decoded_frame_count": decoded_frame_count,
                "frame_fact_count": len(frames),
                "has_page_change_rule": False,
                "has_threshold": False,
                "has_long_lookback": False,
                "has_stable_rule": False,
            },
            "frames": frames,
        }


def frame_difference_fact(
    frame_index: int,
    gray: np.ndarray,
    previous_gray: np.ndarray | None,
    decoded_timestamp_seconds: float,
) -> dict[str, Any]:
    total_pixel_count = int(gray.size)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    regional_histograms = regional_gray_histograms(gray)

    if previous_gray is None:
        fact = {
            "frame_index": frame_index,
            "previous_frame_index": None,
            "decoded_timestamp_seconds": finite_float_or_none(
                decoded_timestamp_seconds
            ),
            "difference_mean": None,
            "changed_pixel_count": None,
            "total_pixel_count": total_pixel_count,
            "changed_area_ratio": None,
            "laplacian_variance": laplacian_variance,
            "ssim": None,
            "binary_pixel_change_count": None,
            "binary_pixel_change_ratio": None,
        }
        add_empty_alignment_facts(fact)
        add_empty_regional_histogram_distances(fact)
        return fact

    difference = cv2.absdiff(previous_gray, gray)
    changed_pixel_count = int(np.count_nonzero(difference))
    binary_pixel_change_count = binary_pixel_change_count_between(
        previous_gray,
        gray,
    )
    fact = {
        "frame_index": frame_index,
        "previous_frame_index": frame_index - 1,
        "decoded_timestamp_seconds": finite_float_or_none(decoded_timestamp_seconds),
        "difference_mean": float(np.mean(difference)) / 255.0,
        "changed_pixel_count": changed_pixel_count,
        "total_pixel_count": total_pixel_count,
        "changed_area_ratio": changed_pixel_count / total_pixel_count
        if total_pixel_count
        else None,
        "laplacian_variance": laplacian_variance,
        "ssim": ssim_score(previous_gray, gray),
        "binary_pixel_change_count": binary_pixel_change_count,
        "binary_pixel_change_ratio": binary_pixel_change_count / total_pixel_count
        if total_pixel_count
        else None,
    }
    add_alignment_facts(fact, previous_gray=previous_gray, current_gray=gray)
    add_regional_histogram_distances(
        fact,
        previous=regional_gray_histograms(previous_gray),
        current=regional_histograms,
    )
    return fact


def binary_pixel_change_count_between(
    previous_gray: np.ndarray,
    current_gray: np.ndarray,
) -> int:
    previous_dark = previous_gray < 127
    current_dark = current_gray < 127
    return int(np.count_nonzero(previous_dark != current_dark))


def add_empty_alignment_facts(fact: dict[str, Any]) -> None:
    fact.update(
        {
            "phase_dx": None,
            "phase_dy": None,
            "phase_response": None,
            "ecc_converged": None,
            "ecc_score": None,
            "ecc_dx": None,
            "ecc_dy": None,
            "ecc_error": None,
            "post_alignment_difference_mean": None,
            "post_alignment_changed_area_ratio": None,
            "post_alignment_ssim": None,
        }
    )


def add_alignment_facts(
    fact: dict[str, Any],
    previous_gray: np.ndarray,
    current_gray: np.ndarray,
) -> None:
    phase = phase_correlation_facts(previous_gray, current_gray)
    ecc = ecc_translation_facts(previous_gray, current_gray)
    post_alignment = post_alignment_facts(
        previous_gray=previous_gray,
        current_gray=current_gray,
        alignment_matrix=ecc["warp_matrix"]
        if ecc["ecc_converged"]
        else phase_translation_matrix(phase["phase_dx"], phase["phase_dy"]),
    )
    fact.update(
        {
            "phase_dx": phase["phase_dx"],
            "phase_dy": phase["phase_dy"],
            "phase_response": phase["phase_response"],
            "ecc_converged": ecc["ecc_converged"],
            "ecc_score": ecc["ecc_score"],
            "ecc_dx": ecc["ecc_dx"],
            "ecc_dy": ecc["ecc_dy"],
            "ecc_error": ecc["ecc_error"],
            "post_alignment_difference_mean": post_alignment[
                "post_alignment_difference_mean"
            ],
            "post_alignment_changed_area_ratio": post_alignment[
                "post_alignment_changed_area_ratio"
            ],
            "post_alignment_ssim": post_alignment["post_alignment_ssim"],
        }
    )


def phase_correlation_facts(
    previous_gray: np.ndarray,
    current_gray: np.ndarray,
) -> dict[str, float | None]:
    shift, response = cv2.phaseCorrelate(
        previous_gray.astype(np.float32),
        current_gray.astype(np.float32),
    )
    return {
        "phase_dx": finite_float_or_none(shift[0]),
        "phase_dy": finite_float_or_none(shift[1]),
        "phase_response": finite_float_or_none(response),
    }


def ecc_translation_facts(
    previous_gray: np.ndarray,
    current_gray: np.ndarray,
) -> dict[str, Any]:
    warp_matrix = np.eye(2, 3, dtype=np.float32)
    try:
        score, warp_matrix = cv2.findTransformECC(
            previous_gray.astype(np.float32),
            current_gray.astype(np.float32),
            warp_matrix,
            cv2.MOTION_TRANSLATION,
        )
    except cv2.error as exc:
        return {
            "ecc_converged": False,
            "ecc_score": None,
            "ecc_dx": None,
            "ecc_dy": None,
            "ecc_error": str(exc),
            "warp_matrix": None,
        }

    if not np.isfinite(score) or not np.all(np.isfinite(warp_matrix)):
        return {
            "ecc_converged": False,
            "ecc_score": finite_float_or_none(score),
            "ecc_dx": finite_float_or_none(warp_matrix[0, 2]),
            "ecc_dy": finite_float_or_none(warp_matrix[1, 2]),
            "ecc_error": "ECC returned non-finite score or warp matrix.",
            "warp_matrix": None,
        }

    return {
        "ecc_converged": True,
        "ecc_score": finite_float_or_none(score),
        "ecc_dx": finite_float_or_none(warp_matrix[0, 2]),
        "ecc_dy": finite_float_or_none(warp_matrix[1, 2]),
        "ecc_error": None,
        "warp_matrix": warp_matrix,
    }


def phase_translation_matrix(dx: float | None, dy: float | None) -> np.ndarray | None:
    if dx is None or dy is None:
        return None
    return np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)


def post_alignment_facts(
    previous_gray: np.ndarray,
    current_gray: np.ndarray,
    alignment_matrix: np.ndarray | None,
) -> dict[str, float | None]:
    if alignment_matrix is None:
        return {
            "post_alignment_difference_mean": None,
            "post_alignment_changed_area_ratio": None,
            "post_alignment_ssim": None,
        }

    aligned_current = cv2.warpAffine(
        current_gray,
        alignment_matrix,
        (previous_gray.shape[1], previous_gray.shape[0]),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
    )
    difference = cv2.absdiff(previous_gray, aligned_current)
    total_pixel_count = int(previous_gray.size)
    changed_pixel_count = int(np.count_nonzero(difference))
    return {
        "post_alignment_difference_mean": finite_float_or_none(
            float(np.mean(difference)) / 255.0
        ),
        "post_alignment_changed_area_ratio": changed_pixel_count / total_pixel_count
        if total_pixel_count
        else None,
        "post_alignment_ssim": finite_float_or_none(
            ssim_score(previous_gray, aligned_current)
        ),
    }


def finite_float_or_none(value: Any) -> float | None:
    number = float(value)
    if not np.isfinite(number):
        return None
    return number


def regional_gray_histograms(gray: np.ndarray) -> dict[str, np.ndarray]:
    return {
        region: normalized_gray_histogram(gray_region)
        for region, gray_region in split_2x2(gray).items()
    }


def add_empty_regional_histogram_distances(fact: dict[str, Any]) -> None:
    for region in REGION_NAMES:
        for method in HISTOGRAM_METHODS:
            fact[regional_histogram_field(region, method)] = None


def add_regional_histogram_distances(
    fact: dict[str, Any],
    previous: dict[str, np.ndarray],
    current: dict[str, np.ndarray],
) -> None:
    for region in REGION_NAMES:
        distances = compare_histograms(previous[region], current[region])
        for method, value in distances.items():
            fact[regional_histogram_field(region, method)] = value


def regional_histogram_field(region: str, method: str) -> str:
    return f"{region}_histogram_{method}"
