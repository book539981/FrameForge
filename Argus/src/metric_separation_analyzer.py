from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np


ANALYZED_METRICS = [
    "adjacent_difference",
    "lookback_difference",
    "laplacian",
]

THRESHOLD_STEP = 0.001


class MetricSeparationAnalyzer:
    def analyze(
        self,
        ground_truth_statistics_report: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        rows = [
            row
            for row in ground_truth_statistics_report["sample_assignments"]
            if row["type"] in ("Stable", "Transition")
        ]
        metric_reports = [
            self._metric_report(metric, rows, config) for metric in ANALYZED_METRICS
        ]
        ranked_metrics = sorted(
            metric_reports,
            key=lambda report: (
                -(report["best_threshold"]["f1_score"] or 0.0),
                -(report["best_threshold"]["accuracy"] or 0.0),
                report["metric"],
            ),
        )
        return {
            "analyzed_metrics": ANALYZED_METRICS,
            "positive_class": "Stable",
            "negative_class": "Transition",
            "threshold_step": THRESHOLD_STEP,
            "threshold_sweep_source": "Ground Truth sample metric values rounded to the 0.001 threshold grid between observed minimum and maximum.",
            "metrics": metric_reports,
            "easiest_metric": ranked_metrics[0]["metric"] if ranked_metrics else None,
            "summary": {
                "metric_count": len(ANALYZED_METRICS),
                "stable_sample_count": sum(1 for row in rows if row["type"] == "Stable"),
                "transition_sample_count": sum(
                    1 for row in rows if row["type"] == "Transition"
                ),
            },
        }

    def _metric_report(
        self,
        metric: str,
        rows: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        stable_values = [
            float(row[metric])
            for row in rows
            if row["type"] == "Stable" and row[metric] is not None
        ]
        transition_values = [
            float(row[metric])
            for row in rows
            if row["type"] == "Transition" and row[metric] is not None
        ]
        combined = stable_values + transition_values
        best = best_threshold(stable_values, transition_values)
        current_threshold = current_config_threshold(metric, config)
        sweep_minimum = floor_to_step(min(combined)) if combined else None
        sweep_maximum = ceil_to_step(max(combined)) if combined else None
        return {
            "metric": metric,
            "stable_values": stable_values,
            "transition_values": transition_values,
            "stable_distribution": distribution(stable_values),
            "transition_distribution": distribution(transition_values),
            "overlap": overlap_report(stable_values, transition_values),
            "best_threshold": best,
            "current_threshold": current_threshold,
            "current_threshold_delta": (
                round(best["threshold"] - current_threshold, 6)
                if best["threshold"] is not None and current_threshold is not None
                else None
            ),
            "threshold_sweep": {
                "minimum": sweep_minimum,
                "maximum": sweep_maximum,
                "step": THRESHOLD_STEP,
                "row_count": sweep_row_count(sweep_minimum, sweep_maximum),
            },
        }


class MetricSeparationWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path, Path]:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / "metric_separation.json"
        csv_path = self.artifacts_dir / "metric_separation.csv"
        markdown_path = self.artifacts_dir / "metric_separation.md"

        json_report = {
            **report,
            "metrics": [
                {
                    key: value
                    for key, value in metric.items()
                    if key not in ("stable_values", "transition_values")
                }
                for metric in report["metrics"]
            ],
        }
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(json_report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")

        self._write_csv(csv_path, report)
        markdown_path.write_text(self._to_markdown(json_report), encoding="utf-8")
        return json_path, csv_path, markdown_path

    def _write_csv(self, csv_path: Path, report: dict[str, Any]) -> None:
        fieldnames = [
            "section",
            "metric",
            "direction",
            "threshold",
            "tp",
            "fp",
            "tn",
            "fn",
            "precision",
            "recall",
            "f1_score",
            "accuracy",
            "stable_min",
            "stable_max",
            "stable_mean",
            "stable_median",
            "stable_std",
            "transition_min",
            "transition_max",
            "transition_mean",
            "transition_median",
            "transition_std",
            "overlap_minimum",
            "overlap_maximum",
            "overlap_ratio",
            "perfect_separation",
            "current_threshold",
            "current_threshold_delta",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for metric in report["metrics"]:
                writer.writerow(summary_csv_row(metric))
                for row in threshold_sweep(
                    metric["stable_values"],
                    metric["transition_values"],
                ):
                    writer.writerow(
                        {
                            "section": "threshold_sweep",
                            "metric": metric["metric"],
                            **row,
                        }
                    )

    def _to_markdown(self, report: dict[str, Any]) -> str:
        lines = [
            "# Metric Separation Analyzer",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | ---: |",
            f"| Metric Count | {report['summary']['metric_count']} |",
            f"| Stable Sample Count | {report['summary']['stable_sample_count']} |",
            f"| Transition Sample Count | {report['summary']['transition_sample_count']} |",
            f"| Threshold Step | {fmt(report['threshold_step'])} |",
            f"| Easiest Metric | {report['easiest_metric']} |",
            "",
            "## Best Threshold",
            "",
            "| Metric | Direction | Best Threshold | Best F1 | Best Precision | Best Recall | Accuracy | Current Threshold | Delta |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for metric in report["metrics"]:
            best = metric["best_threshold"]
            lines.append(
                f"| {metric['metric']} | {best['direction']} | "
                f"{fmt(best['threshold'])} | {fmt(best['f1_score'])} | "
                f"{fmt(best['precision'])} | {fmt(best['recall'])} | "
                f"{fmt(best['accuracy'])} | {fmt(metric['current_threshold'])} | "
                f"{fmt(metric['current_threshold_delta'])} |"
            )
        lines.extend(
            [
                "",
                "## Separation Report",
                "",
                "| Metric | Stable Min | Stable Max | Stable Mean | Stable Median | Stable Std | Transition Min | Transition Max | Transition Mean | Transition Median | Transition Std | Overlap Range | Overlap Ratio | Perfect Separation |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |",
            ]
        )
        for metric in report["metrics"]:
            stable = metric["stable_distribution"]
            transition = metric["transition_distribution"]
            overlap = metric["overlap"]
            lines.append(
                f"| {metric['metric']} | {fmt(stable['minimum'])} | "
                f"{fmt(stable['maximum'])} | {fmt(stable['mean'])} | "
                f"{fmt(stable['median'])} | {fmt(stable['std'])} | "
                f"{fmt(transition['minimum'])} | {fmt(transition['maximum'])} | "
                f"{fmt(transition['mean'])} | {fmt(transition['median'])} | "
                f"{fmt(transition['std'])} | {overlap_range_text(overlap)} | "
                f"{fmt(overlap['overlap_ratio'])} | {overlap['perfect_separation']} |"
            )
        lines.append("")
        return "\n".join(lines)


def threshold_sweep(
    stable_values: list[float],
    transition_values: list[float],
) -> Any:
    combined = stable_values + transition_values
    if not combined:
        return
    start = floor_to_step(min(combined))
    end = ceil_to_step(max(combined))
    stable_sorted = sorted(stable_values)
    transition_sorted = sorted(transition_values)
    total_stable = len(stable_sorted)
    total_transition = len(transition_sorted)
    threshold_int = int(round(start / THRESHOLD_STEP))
    end_int = int(round(end / THRESHOLD_STEP))

    stable_le = 0
    transition_le = 0
    for value_int in range(threshold_int, end_int + 1):
        threshold = round(value_int * THRESHOLD_STEP, 6)
        while stable_le < total_stable and stable_sorted[stable_le] <= threshold:
            stable_le += 1
        while (
            transition_le < total_transition
            and transition_sorted[transition_le] <= threshold
        ):
            transition_le += 1

        yield metric_row(
            direction="stable_when_less_than_or_equal",
            threshold=threshold,
            tp=stable_le,
            fp=transition_le,
            tn=total_transition - transition_le,
            fn=total_stable - stable_le,
        )
        yield metric_row(
            direction="stable_when_greater_than_or_equal",
            threshold=threshold,
            tp=total_stable - stable_le,
            fp=total_transition - transition_le,
            tn=transition_le,
            fn=stable_le,
        )


def metric_row(
    direction: str,
    threshold: float,
    tp: int,
    fp: int,
    tn: int,
    fn: int,
) -> dict[str, Any]:
    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    return {
        "direction": direction,
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score(precision, recall),
        "accuracy": ratio(tp + tn, tp + fp + tn + fn),
    }


def best_threshold(
    stable_values: list[float],
    transition_values: list[float],
) -> dict[str, Any]:
    best = None
    for row in threshold_sweep(stable_values, transition_values):
        if best is None or threshold_rank(row) > threshold_rank(best):
            best = row
    if best is None:
        return {
            "direction": None,
            "threshold": None,
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "accuracy": None,
        }
    return best


def threshold_rank(row: dict[str, Any]) -> tuple[float, float, float, float, float]:
    return (
        row["f1_score"] or 0.0,
        row["accuracy"] or 0.0,
        row["precision"] or 0.0,
        row["recall"] or 0.0,
        -row["threshold"],
    )


def distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
            "std": None,
        }
    return {
        "count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": sum(values) / len(values),
        "median": median(values),
        "std": float(np.std(np.array(values, dtype=np.float64), ddof=0)),
    }


def overlap_report(
    stable_values: list[float],
    transition_values: list[float],
) -> dict[str, Any]:
    if not stable_values or not transition_values:
        return {
            "minimum": None,
            "maximum": None,
            "overlap_ratio": None,
            "perfect_separation": False,
        }
    stable_min = min(stable_values)
    stable_max = max(stable_values)
    transition_min = min(transition_values)
    transition_max = max(transition_values)
    overlap_minimum = max(stable_min, transition_min)
    overlap_maximum = min(stable_max, transition_max)
    has_overlap = overlap_minimum <= overlap_maximum
    union_minimum = min(stable_min, transition_min)
    union_maximum = max(stable_max, transition_max)
    union_width = union_maximum - union_minimum
    overlap_width = overlap_maximum - overlap_minimum if has_overlap else 0.0
    return {
        "minimum": overlap_minimum if has_overlap else None,
        "maximum": overlap_maximum if has_overlap else None,
        "overlap_ratio": overlap_width / union_width if union_width else 0.0,
        "perfect_separation": not has_overlap,
    }


def current_config_threshold(metric: str, config: dict[str, Any]) -> float | None:
    stable_config = config["stable_candidate"]
    if metric == "adjacent_difference":
        return float(stable_config["adjacent_difference_maximum"])
    if metric == "lookback_difference":
        return float(stable_config["long_lookback_difference_maximum"])
    return None


def sweep_row_count(
    minimum: float | None,
    maximum: float | None,
) -> int:
    if minimum is None or maximum is None:
        return 0
    return (int(round(maximum / THRESHOLD_STEP)) - int(round(minimum / THRESHOLD_STEP)) + 1) * 2


def summary_csv_row(metric: dict[str, Any]) -> dict[str, Any]:
    stable = metric["stable_distribution"]
    transition = metric["transition_distribution"]
    overlap = metric["overlap"]
    return {
        "section": "metric_summary",
        "metric": metric["metric"],
        "direction": metric["best_threshold"]["direction"],
        "threshold": metric["best_threshold"]["threshold"],
        "precision": metric["best_threshold"]["precision"],
        "recall": metric["best_threshold"]["recall"],
        "f1_score": metric["best_threshold"]["f1_score"],
        "accuracy": metric["best_threshold"]["accuracy"],
        "stable_min": stable["minimum"],
        "stable_max": stable["maximum"],
        "stable_mean": stable["mean"],
        "stable_median": stable["median"],
        "stable_std": stable["std"],
        "transition_min": transition["minimum"],
        "transition_max": transition["maximum"],
        "transition_mean": transition["mean"],
        "transition_median": transition["median"],
        "transition_std": transition["std"],
        "overlap_minimum": overlap["minimum"],
        "overlap_maximum": overlap["maximum"],
        "overlap_ratio": overlap["overlap_ratio"],
        "perfect_separation": overlap["perfect_separation"],
        "current_threshold": metric["current_threshold"],
        "current_threshold_delta": metric["current_threshold_delta"],
    }


def floor_to_step(value: float) -> float:
    return round(math.floor(value / THRESHOLD_STEP) * THRESHOLD_STEP, 6)


def ceil_to_step(value: float) -> float:
    return round(math.ceil(value / THRESHOLD_STEP) * THRESHOLD_STEP, 6)


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def f1_score(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)


def overlap_range_text(overlap: dict[str, Any]) -> str:
    if overlap["minimum"] is None or overlap["maximum"] is None:
        return ""
    return f"{fmt(overlap['minimum'])}~{fmt(overlap['maximum'])}"


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
