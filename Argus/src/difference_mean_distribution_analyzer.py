from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


HISTOGRAM_THRESHOLDS = [
    0.100,
    0.080,
    0.050,
    0.030,
    0.020,
    0.015,
    0.010,
    0.008,
    0.005,
    0.003,
    0.002,
    0.001,
]

THRESHOLD_SWEEP_VALUES = [
    0.001,
    0.002,
    0.003,
    0.005,
    0.008,
    0.010,
    0.015,
    0.020,
    0.030,
    0.050,
]

PERCENTILE_DEFINITIONS = [
    ("minimum", 0),
    ("p5", 5),
    ("p10", 10),
    ("p25", 25),
    ("median", 50),
    ("p75", 75),
    ("p90", 90),
    ("p95", 95),
    ("maximum", 100),
]


class DifferenceMeanDistributionAnalyzer:
    """Builds facts-only difference_mean distribution reports from existing artifacts."""

    def analyze(
        self,
        page_change_report: dict[str, Any],
        frame_difference_timeline: dict[str, Any],
    ) -> dict[str, Any]:
        frame_by_index = {
            frame["frame_index"]: frame
            for frame in frame_difference_timeline.get("frames", [])
            if frame.get("frame_index") is not None
        }

        events = []
        for event in page_change_report.get("events", []):
            difference_mean = event.get("difference_mean_peak")
            difference_mean_frame = event.get("difference_mean_peak_frame")
            frame = frame_by_index.get(difference_mean_frame)
            if difference_mean is None and frame is not None:
                difference_mean = frame.get("difference_mean")

            changed_area_ratio = event.get("changed_area_peak")
            changed_area_frame = event.get("changed_area_peak_frame")
            if changed_area_ratio is None:
                area_frame = frame_by_index.get(changed_area_frame)
                if area_frame is not None:
                    changed_area_ratio = area_frame.get("changed_area_ratio")

            events.append(
                {
                    "event_index": event.get("event_index"),
                    "start_frame": event.get("start_frame"),
                    "end_frame": event.get("end_frame"),
                    "frame_count": event.get("frame_count"),
                    "changed_area_ratio": changed_area_ratio,
                    "changed_area_peak_frame": changed_area_frame,
                    "difference_mean": difference_mean,
                    "difference_mean_peak_frame": difference_mean_frame,
                }
            )

        sorted_events = sorted(
            events,
            key=lambda item: (
                item["difference_mean"] is not None,
                item["difference_mean"] if item["difference_mean"] is not None else -1,
            ),
            reverse=True,
        )
        difference_values = [
            event["difference_mean"]
            for event in events
            if event["difference_mean"] is not None
        ]

        return {
            "source_artifacts": {
                "page_change_events": "page_change_events.json",
                "frame_difference_timeline": "frame_difference_timeline.json",
            },
            "summary": {
                "event_count": len(events),
                "difference_mean_value_count": len(difference_values),
            },
            "events_sorted_by_difference_mean": sorted_events,
            "histogram": self._count_by_threshold(
                difference_values,
                HISTOGRAM_THRESHOLDS,
            ),
            "percentile": self._build_percentiles(difference_values),
            "threshold_sweep": self._count_by_threshold(
                difference_values,
                THRESHOLD_SWEEP_VALUES,
            ),
        }

    def _count_by_threshold(
        self,
        values: list[float],
        thresholds: list[float],
    ) -> list[dict[str, Any]]:
        return [
            {
                "difference_mean_greater_equal": threshold,
                "event_count": sum(1 for value in values if value >= threshold),
            }
            for threshold in thresholds
        ]

    def _build_percentiles(self, values: list[float]) -> dict[str, float | None]:
        return {
            name: self._percentile(values, percentile)
            for name, percentile in PERCENTILE_DEFINITIONS
        }

    def _percentile(self, values: list[float], percentile: int) -> float | None:
        if not values:
            return None

        sorted_values = sorted(values)
        if percentile == 0:
            return sorted_values[0]
        if percentile == 100:
            return sorted_values[-1]

        position = (len(sorted_values) - 1) * (percentile / 100)
        lower_index = int(position)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)
        fraction = position - lower_index
        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        return lower_value + ((upper_value - lower_value) * fraction)


class DifferenceMeanDistributionReportWriter:
    def __init__(
        self,
        artifacts_directory: Path,
        json_filename: str = "difference_mean_distribution.json",
        csv_filename: str = "difference_mean_distribution.csv",
        markdown_filename: str = "difference_mean_distribution.md",
    ) -> None:
        self.artifacts_directory = artifacts_directory
        self.json_filename = json_filename
        self.csv_filename = csv_filename
        self.markdown_filename = markdown_filename

    def write(self, report: dict[str, Any]) -> dict[str, Path]:
        self.artifacts_directory.mkdir(parents=True, exist_ok=True)

        json_path = self.artifacts_directory / self.json_filename
        csv_path = self.artifacts_directory / self.csv_filename
        markdown_path = self.artifacts_directory / self.markdown_filename

        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        self._write_csv(csv_path, report)
        self._write_markdown(markdown_path, report)

        return {
            "json": json_path,
            "csv": csv_path,
            "markdown": markdown_path,
        }

    def _write_csv(self, path: Path, report: dict[str, Any]) -> None:
        fieldnames = [
            "section",
            "event_index",
            "start_frame",
            "end_frame",
            "frame_count",
            "changed_area_ratio",
            "changed_area_peak_frame",
            "difference_mean",
            "difference_mean_peak_frame",
            "difference_mean_greater_equal",
            "event_count",
            "percentile",
            "value",
        ]

        with path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for event in report["events_sorted_by_difference_mean"]:
                writer.writerow({"section": "event", **event})

            for row in report["histogram"]:
                writer.writerow({"section": "histogram", **row})

            for name, value in report["percentile"].items():
                writer.writerow(
                    {
                        "section": "percentile",
                        "percentile": name,
                        "value": value,
                    }
                )

            for row in report["threshold_sweep"]:
                writer.writerow({"section": "threshold_sweep", **row})

    def _write_markdown(self, path: Path, report: dict[str, Any]) -> None:
        lines = [
            "# Difference Mean Distribution",
            "",
            "## Summary",
            "",
            f"- Event Count: {report['summary']['event_count']}",
            f"- Difference Mean Value Count: {report['summary']['difference_mean_value_count']}",
            "",
            "## Events Sorted By Difference Mean",
            "",
            "| Event | Changed Area Ratio | Difference Mean |",
            "| ----: | -----------------: | --------------: |",
        ]

        for event in report["events_sorted_by_difference_mean"]:
            lines.append(
                "| "
                f"{event['event_index']} | "
                f"{self._format_number(event['changed_area_ratio'])} | "
                f"{self._format_number(event['difference_mean'])} |"
            )

        lines.extend(
            [
                "",
                "## Histogram",
                "",
                "| difference_mean >= | Event Count |",
                "| -----------------: | ----------: |",
            ]
        )
        for row in report["histogram"]:
            lines.append(
                "| "
                f"{row['difference_mean_greater_equal']:.3f} | "
                f"{row['event_count']} |"
            )

        lines.extend(
            [
                "",
                "## Percentile",
                "",
                "| Percentile | Value |",
                "| ---------- | ----: |",
            ]
        )
        for name, value in report["percentile"].items():
            lines.append(f"| {name} | {self._format_number(value)} |")

        lines.extend(
            [
                "",
                "## Threshold Sweep",
                "",
                "| Threshold | Remaining Events |",
                "| --------: | ---------------: |",
            ]
        )
        for row in report["threshold_sweep"]:
            lines.append(
                "| "
                f"{row['difference_mean_greater_equal']:.3f} | "
                f"{row['event_count']} |"
            )

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _format_number(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, float):
            return f"{value:.9f}"
        return str(value)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    argus_root = Path(__file__).resolve().parents[1]
    artifacts_directory = argus_root / "output" / "artifacts"

    page_change_report = load_json(artifacts_directory / "page_change_events.json")
    frame_difference_timeline = load_json(
        artifacts_directory / "frame_difference_timeline.json"
    )

    analyzer = DifferenceMeanDistributionAnalyzer()
    report = analyzer.analyze(page_change_report, frame_difference_timeline)

    writer = DifferenceMeanDistributionReportWriter(artifacts_directory)
    paths = writer.write(report)

    print("difference_mean_distribution artifacts:")
    for artifact_type, artifact_path in paths.items():
        print(f"{artifact_type}: {artifact_path}")


if __name__ == "__main__":
    main()
