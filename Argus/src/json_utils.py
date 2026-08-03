from __future__ import annotations

from typing import Any

import numpy as np


def scrub_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: scrub_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_json(item) for item in value]
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value
