from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReportWriter:
    def __init__(self, config: dict[str, Any], argus_root: Path) -> None:
        self.config = config
        self.argus_root = argus_root
        self.artifacts_dir = argus_root / config["output"]["artifacts_directory"]

    def write_stable_segments(self, report: dict[str, Any]) -> Path:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.artifacts_dir / self.config["report"]["stable_segments_filename"]
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        return json_path
