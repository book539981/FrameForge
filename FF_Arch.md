# FF_Arch

Generated: 2026-08-03 22:38:44
Workspace: `D:\TTT\FF`

## Git Status

```text
M Argus/README.md
 M Argus/config.yaml
 M Argus/src/stable_page_processor.py
```

## Project Structure

Excluded from traversal: `.git`, `.venv`, `__pycache__`, `.pytest_cache`. Binary/media files are listed by path but not parsed.

```text
.
|-- Argus/
|   |-- input/
|   |   |-- .gitkeep
|   |   `-- 5秒AP搖高版17-2頁測試檔.MP4
|   |-- output/
|   |   |-- artifacts/
|   |   |   |-- stable_signature_calibration/
|   |   |   |   |-- accepted_plateau_summary.json
|   |   |   |   |-- candidate_timeline_events.csv
|   |   |   |   |-- sequence_1_plateau.csv
|   |   |   |   `-- sequence_7_plateau.csv
|   |   |   |-- .gitkeep
|   |   |   `-- stable_segments.json
|   |   |-- debug/
|   |   |   |-- segments/
|   |   |   |   |-- segment_001_after.png
|   |   |   |   |-- segment_001_anchor.png
|   |   |   |   |-- segment_001_before.png
|   |   |   |   |-- segment_001_first.png
|   |   |   |   |-- segment_001_last.png
|   |   |   |   |-- segment_001_middle.png
|   |   |   |   |-- segment_002_after.png
|   |   |   |   |-- segment_002_anchor.png
|   |   |   |   |-- segment_002_before.png
|   |   |   |   |-- segment_002_first.png
|   |   |   |   |-- segment_002_last.png
|   |   |   |   |-- segment_002_middle.png
|   |   |   |   |-- segment_003_after.png
|   |   |   |   |-- segment_003_anchor.png
|   |   |   |   |-- segment_003_before.png
|   |   |   |   |-- segment_003_first.png
|   |   |   |   |-- segment_003_last.png
|   |   |   |   `-- segment_003_middle.png
|   |   |   `-- .gitkeep
|   |   |-- pages/
|   |   |   |-- .gitkeep
|   |   |   |-- page_001.png
|   |   |   |-- page_002.png
|   |   |   `-- page_003.png
|   |   `-- temp/
|   |       `-- .gitkeep
|   |-- src/
|   |   |-- __init__.py
|   |   |-- best_frame_selector.py
|   |   |-- frame_metrics.py
|   |   |-- frame_source.py
|   |   |-- json_utils.py
|   |   |-- report_writer.py
|   |   |-- stable_page_processor.py
|   |   |-- stable_rule.py
|   |   |-- stable_state.py
|   |   `-- video_reader.py
|   |-- tests/
|   |   |-- 1秒AP版行政學(上)[第一章一節-行政學本質與發展].MP4
|   |   |-- 1秒TG版行政學(上)[第一章一節-行政學本質與發展].MP4
|   |   |-- 2秒AP版行政學(上)[第一章一節-行政學本質與發展].MP4
|   |   |-- 2秒AP行政學(上)[行政學本質與發展].MP4
|   |   |-- 2秒AP高版15頁測試檔.MP4
|   |   |-- 2秒TG版15頁測試檔.MP4
|   |   |-- 2秒TG版行政學(上)[第一章一節-行政學本質與發展].MOV
|   |   |-- 2秒沒裁AP版行政學(上)[第一章一節-行政學本質與發展].MOV
|   |   |-- 3秒AP容版行政學(上)[第一章一節-行政學本質與發展].MP4
|   |   |-- 3秒AP高版行政學(上)[第一章一節-行政學本質與發展].MP4
|   |   |-- 3秒TG版行政學(上)[第一章一節-行政學本質與發展].MP4
|   |   `-- __init__.py
|   |-- argus.py
|   |-- config.yaml
|   |-- README.md
|   `-- requirements.txt
|-- Proto/
|   `-- FF_[FrameForge]MVP開發原則V1.2.md
|-- .gitignore
`-- README.md
```

## File Inventory

| Path | Kind | Size |
| --- | --- | ---: |
| `.gitignore` | other | 683 |
| `Argus/argus.py` | python | 2434 |
| `Argus/config.yaml` | config | 760 |
| `Argus/input/.gitkeep` | other | 0 |
| `Argus/input/5秒AP搖高版17-2頁測試檔.MP4` | binary/generated/media | 45827682 |
| `Argus/output/artifacts/.gitkeep` | other | 0 |
| `Argus/output/artifacts/stable_segments.json` | artifact/data | 838113 |
| `Argus/output/artifacts/stable_signature_calibration/accepted_plateau_summary.json` | artifact/data | 2014 |
| `Argus/output/artifacts/stable_signature_calibration/candidate_timeline_events.csv` | artifact/data | 105796 |
| `Argus/output/artifacts/stable_signature_calibration/sequence_1_plateau.csv` | artifact/data | 13211 |
| `Argus/output/artifacts/stable_signature_calibration/sequence_7_plateau.csv` | artifact/data | 43630 |
| `Argus/output/debug/.gitkeep` | other | 0 |
| `Argus/output/debug/segments/segment_001_after.png` | binary/generated/media | 277810 |
| `Argus/output/debug/segments/segment_001_anchor.png` | binary/generated/media | 233317 |
| `Argus/output/debug/segments/segment_001_before.png` | binary/generated/media | 234827 |
| `Argus/output/debug/segments/segment_001_first.png` | binary/generated/media | 233317 |
| `Argus/output/debug/segments/segment_001_last.png` | binary/generated/media | 195201 |
| `Argus/output/debug/segments/segment_001_middle.png` | binary/generated/media | 200383 |
| `Argus/output/debug/segments/segment_002_after.png` | binary/generated/media | 90530 |
| `Argus/output/debug/segments/segment_002_anchor.png` | binary/generated/media | 130088 |
| `Argus/output/debug/segments/segment_002_before.png` | binary/generated/media | 131217 |
| `Argus/output/debug/segments/segment_002_first.png` | binary/generated/media | 130088 |
| `Argus/output/debug/segments/segment_002_last.png` | binary/generated/media | 38637 |
| `Argus/output/debug/segments/segment_002_middle.png` | binary/generated/media | 94586 |
| `Argus/output/debug/segments/segment_003_after.png` | binary/generated/media | 399751 |
| `Argus/output/debug/segments/segment_003_anchor.png` | binary/generated/media | 329515 |
| `Argus/output/debug/segments/segment_003_before.png` | binary/generated/media | 336426 |
| `Argus/output/debug/segments/segment_003_first.png` | binary/generated/media | 329515 |
| `Argus/output/debug/segments/segment_003_last.png` | binary/generated/media | 326943 |
| `Argus/output/debug/segments/segment_003_middle.png` | binary/generated/media | 326757 |
| `Argus/output/pages/.gitkeep` | other | 1 |
| `Argus/output/pages/page_001.png` | binary/generated/media | 189617 |
| `Argus/output/pages/page_002.png` | binary/generated/media | 98568 |
| `Argus/output/pages/page_003.png` | binary/generated/media | 328371 |
| `Argus/output/temp/.gitkeep` | other | 0 |
| `Argus/README.md` | docs | 619 |
| `Argus/requirements.txt` | other | 27 |
| `Argus/src/__init__.py` | python | 0 |
| `Argus/src/best_frame_selector.py` | python | 1007 |
| `Argus/src/frame_metrics.py` | python | 843 |
| `Argus/src/frame_source.py` | python | 1862 |
| `Argus/src/json_utils.py` | python | 405 |
| `Argus/src/report_writer.py` | python | 766 |
| `Argus/src/stable_page_processor.py` | python | 63722 |
| `Argus/src/stable_rule.py` | python | 3447 |
| `Argus/src/stable_state.py` | python | 11403 |
| `Argus/src/video_reader.py` | python | 2691 |
| `Argus/tests/1秒AP版行政學(上)[第一章一節-行政學本質與發展].MP4` | binary/generated/media | 58641216 |
| `Argus/tests/1秒TG版行政學(上)[第一章一節-行政學本質與發展].MP4` | binary/generated/media | 15699507 |
| `Argus/tests/2秒AP版行政學(上)[第一章一節-行政學本質與發展].MP4` | binary/generated/media | 44043127 |
| `Argus/tests/2秒AP行政學(上)[行政學本質與發展].MP4` | binary/generated/media | 61744372 |
| `Argus/tests/2秒AP高版15頁測試檔.MP4` | binary/generated/media | 26838103 |
| `Argus/tests/2秒TG版15頁測試檔.MP4` | binary/generated/media | 18021096 |
| `Argus/tests/2秒TG版行政學(上)[第一章一節-行政學本質與發展].MOV` | binary/generated/media | 33720314 |
| `Argus/tests/2秒沒裁AP版行政學(上)[第一章一節-行政學本質與發展].MOV` | binary/generated/media | 50739968 |
| `Argus/tests/3秒AP容版行政學(上)[第一章一節-行政學本質與發展].MP4` | binary/generated/media | 36983340 |
| `Argus/tests/3秒AP高版行政學(上)[第一章一節-行政學本質與發展].MP4` | binary/generated/media | 36983340 |
| `Argus/tests/3秒TG版行政學(上)[第一章一節-行政學本質與發展].MP4` | binary/generated/media | 42776235 |
| `Argus/tests/__init__.py` | python | 0 |
| `Proto/FF_[FrameForge]MVP開發原則V1.2.md` | docs | 10938 |
| `README.md` | docs | 356 |

## Config Keys

### `Argus/config.yaml`

| Key | Value |
| --- | --- |
| `__parse_error__` | `No module named 'yaml'` |

## Python Modules

### `Argus/argus.py`

Module: `Argus.argus`

#### Imports
- L1: `from __future__ import annotations`
- L3: `import logging`
- L4: `import sys`
- L5: `import time`
- L6: `from pathlib import Path`
- L8: `import yaml`
- L10: `from src.report_writer import ReportWriter`
- L11: `from src.stable_page_processor import StablePageProcessor`
- L12: `from src.video_reader import find_single_video`

#### Classes / Functions
- L15: def `Argus.argus._configure_logging()`
- L19: def `Argus.argus._load_config(argus_root)`
- L25: def `Argus.argus.main()`

#### Function Call References
- `Argus.argus._configure_logging`
  - L16: `logging.basicConfig()`
- `Argus.argus._load_config`
  - L21: `config_path.open()`
  - L22: `yaml.safe_load()`
- `Argus.argus.main`
  - L26: `_configure_logging()`
  - L27: `time.perf_counter()`
  - L28: `Path.resolve()`
  - L28: `Path()`
  - L31: `_load_config()`
  - L34: `artifacts_dir.mkdir()`
  - L36: `find_single_video()`
  - L37: `StablePageProcessor.process()`
  - L37: `StablePageProcessor()`
  - L39: `ReportWriter()`
  - L40: `writer.write_stable_segments()`
  - L42: `time.perf_counter()`
  - L46: `print()`
  - L47: `print()`
  - L48: `print()`
  - L49: `print()`
  - L50: `print()`
  - L51: `print()`
  - L52: `print()`
  - L53: `print()`
  - L54: `print()`
  - L55: `print()`
  - L56: `print()`
  - L57: `print()`
  - L58: `print()`
  - L59: `print()`
  - L60: `print()`
  - L61: `print()`
  - L62: `print()`
  - L63: `print()`
  - L63: `stable_segments_path.relative_to()`
  - L64: `print()`
  - L64: `Path()`
  - L65: `print()`
  - L66: `print()`
  - L69: `logging.error()`

### `Argus/src/__init__.py`

Module: `Argus.src.__init__`

#### Imports
- none

#### Classes / Functions
- none

#### Function Call References
- none

### `Argus/src/best_frame_selector.py`

Module: `Argus.src.best_frame_selector`

#### Imports
- L1: `from __future__ import annotations`
- L3: `from dataclasses import dataclass`
- L4: `from typing import Any`
- L6: `import numpy as np`

#### Classes / Functions
- L10: class `Argus.src.best_frame_selector.CandidateFrame` bases: `object`
- L15: class `Argus.src.best_frame_selector.BestFrameSelector` bases: `object`
- L16: def `Argus.src.best_frame_selector.BestFrameSelector.select(self, candidates, exclusion_seconds)`

#### Function Call References
- `Argus.src.best_frame_selector.BestFrameSelector.select`
  - L22: `ValueError()`
  - L23: `min()`
  - L32: `max()`

### `Argus/src/frame_metrics.py`

Module: `Argus.src.frame_metrics`

#### Imports
- L1: `from __future__ import annotations`
- L3: `import cv2`
- L4: `import numpy as np`

#### Classes / Functions
- L7: def `Argus.src.frame_metrics.difference_score(from_gray, to_gray)`
- L11: def `Argus.src.frame_metrics.ssim(from_gray, to_gray)`

#### Function Call References
- `Argus.src.frame_metrics.difference_score`
  - L8: `float()`
  - L8: `np.mean()`
  - L8: `cv2.absdiff()`
- `Argus.src.frame_metrics.ssim`
  - L12: `from_gray.astype()`
  - L13: `to_gray.astype()`
  - L17: `float()`
  - L17: `np.mean()`
  - L18: `float()`
  - L18: `np.mean()`
  - L19: `float()`
  - L19: `np.var()`
  - L20: `float()`
  - L20: `np.var()`
  - L21: `float()`
  - L21: `np.mean()`
  - L25: `float()`

### `Argus/src/frame_source.py`

Module: `Argus.src.frame_source`

#### Imports
- L1: `from __future__ import annotations`
- L3: `from dataclasses import dataclass`
- L4: `from pathlib import Path`
- L5: `from typing import Iterator`
- L7: `import cv2`
- L8: `import numpy as np`

#### Classes / Functions
- L12: class `Argus.src.frame_source.DecodedFrame` bases: `object`
- L18: class `Argus.src.frame_source.SequentialFrameSource` bases: `object`
- L19: def `Argus.src.frame_source.SequentialFrameSource.__init__(self, video_path, fps, expected_total_frames)`
- L27: def `Argus.src.frame_source.SequentialFrameSource.__iter__(self)`
- L58: def `Argus.src.frame_source.SequentialFrameSource._timestamp(self, frame_index)`

#### Function Call References
- `Argus.src.frame_source.SequentialFrameSource.__init__`
  - no calls
- `Argus.src.frame_source.SequentialFrameSource.__iter__`
  - L28: `cv2.VideoCapture()`
  - L28: `str()`
  - L30: `capture.isOpened()`
  - L31: `ValueError()`
  - L35: `capture.read()`
  - L39: `self._timestamp()`
  - L42: `DecodedFrame()`
  - L49: `capture.release()`
- `Argus.src.frame_source.SequentialFrameSource._timestamp`
  - no calls

### `Argus/src/json_utils.py`

Module: `Argus.src.json_utils`

#### Imports
- L1: `from __future__ import annotations`
- L3: `from typing import Any`
- L5: `import numpy as np`

#### Classes / Functions
- L8: def `Argus.src.json_utils.scrub_json(value)`

#### Function Call References
- `Argus.src.json_utils.scrub_json`
  - L9: `isinstance()`
  - L10: `scrub_json()`
  - L10: `value.items()`
  - L11: `isinstance()`
  - L12: `scrub_json()`
  - L13: `isinstance()`
  - L14: `np.isfinite()`

### `Argus/src/report_writer.py`

Module: `Argus.src.report_writer`

#### Imports
- L1: `from __future__ import annotations`
- L3: `import json`
- L4: `from pathlib import Path`
- L5: `from typing import Any`

#### Classes / Functions
- L8: class `Argus.src.report_writer.ReportWriter` bases: `object`
- L9: def `Argus.src.report_writer.ReportWriter.__init__(self, config, argus_root)`
- L14: def `Argus.src.report_writer.ReportWriter.write_stable_segments(self, report)`

#### Function Call References
- `Argus.src.report_writer.ReportWriter.__init__`
  - no calls
- `Argus.src.report_writer.ReportWriter.write_stable_segments`
  - L15: `self.artifacts_dir.mkdir()`
  - L17: `json_path.open()`
  - L18: `json.dump()`
  - L19: `handle.write()`

### `Argus/src/stable_page_processor.py`

Module: `Argus/src/stable_page_processor.py`

#### Imports
- none

#### Classes / Functions
- L0: parse_error `invalid non-printable character U+FEFF (stable_page_processor.py, line 1)`

#### Function Call References
- none

### `Argus/src/stable_rule.py`

Module: `Argus.src.stable_rule`

#### Imports
- L1: `from __future__ import annotations`
- L3: `from typing import Any`
- L5: `from .stable_state import StableRelation`

#### Classes / Functions
- L8: class `Argus.src.stable_rule.StableRule` bases: `object`
- L9: def `Argus.src.stable_rule.StableRule.__init__(self, config)`
- L42: def `Argus.src.stable_rule.StableRule.is_qualifying_relation(self, relation)`
- L51: def `Argus.src.stable_rule.StableRule.is_start_relation(self, relation)`
- L54: def `Argus.src.stable_rule.StableRule.is_sequence_relation(self, relation)`
- L57: def `Argus.src.stable_rule.StableRule.is_complete_sequence(self, stable_duration_seconds)`
- L60: def `Argus.src.stable_rule.StableRule.motion_difference_score(self, relation)`
- L66: def `Argus.src.stable_rule.StableRule.is_motion_relation(self, relation)`

#### Function Call References
- `Argus.src.stable_rule.StableRule.__init__`
  - L10: `config.get()`
  - L11: `float()`
  - L11: `stable_config.get()`
  - L12: `float()`
  - L13: `stable_config.get()`
  - L13: `stable_config.get()`
  - L15: `float()`
  - L15: `stable_config.get()`
  - L16: `float()`
  - L17: `stable_config.get()`
  - L19: `float()`
  - L20: `stable_config.get()`
  - L22: `float()`
  - L23: `stable_config.get()`
  - L23: `max()`
  - L25: `float()`
  - L25: `stable_config.get()`
  - L26: `float()`
  - L27: `stable_config.get()`
  - L29: `float()`
  - L29: `stable_config.get()`
  - L31: `ValueError()`
  - L33: `ValueError()`
  - L35: `ValueError()`
  - L37: `ValueError()`
  - L39: `list()`
  - L39: `stable_config.get()`
  - L40: `list()`
  - L40: `stable_config.get()`
- `Argus.src.stable_rule.StableRule.is_qualifying_relation`
  - L49: `all()`
- `Argus.src.stable_rule.StableRule.is_start_relation`
  - no calls
- `Argus.src.stable_rule.StableRule.is_sequence_relation`
  - L55: `self.is_qualifying_relation()`
- `Argus.src.stable_rule.StableRule.is_complete_sequence`
  - no calls
- `Argus.src.stable_rule.StableRule.motion_difference_score`
  - L63: `scores.append()`
  - L64: `max()`
- `Argus.src.stable_rule.StableRule.is_motion_relation`
  - L67: `self.motion_difference_score()`

### `Argus/src/stable_state.py`

Module: `Argus.src.stable_state`

#### Imports
- L1: `from __future__ import annotations`
- L3: `from dataclasses import dataclass`
- L4: `from pathlib import Path`
- L5: `from typing import Any`
- L7: `import numpy as np`
- L9: `from .best_frame_selector import BestFrameSelector`
- L9: `from .best_frame_selector import CandidateFrame`

#### Classes / Functions
- L13: class `Argus.src.stable_state.SampledFrame` bases: `object`
- L22: class `Argus.src.stable_state.FrameBufferItem` bases: `object`
- L29: class `Argus.src.stable_state.StableRelation` bases: `object`
- L53: class `Argus.src.stable_state.FinalizeResult` bases: `object`
- L60: class `Argus.src.stable_state.StableSequenceState` bases: `object`
- L61: def `Argus.src.stable_state.StableSequenceState.__init__(self, sequence_id)`
- L84: def `Argus.src.stable_state.StableSequenceState.stable_duration_seconds(self)`
- L90: def `Argus.src.stable_state.StableSequenceState.add_relation(self, previous_sample, previous_frame, current_sample, current_frame, relation, boundary_before)`
- L111: def `Argus.src.stable_state.StableSequenceState.enter_grace_period(self, fail_start_time_seconds)`
- L116: def `Argus.src.stable_state.StableSequenceState.grace_elapsed_seconds(self, current_time_seconds)`
- L123: def `Argus.src.stable_state.StableSequenceState.recover_from_grace_period(self)`
- L126: def `Argus.src.stable_state.StableSequenceState.confirm(self, relation)`
- L132: def `Argus.src.stable_state.StableSequenceState.select_best_frame(self, selector, exclusion_seconds)`
- L141: def `Argus.src.stable_state.StableSequenceState.to_segment(self, segment_index, page_path, preceding_motion_id, motion_end_time_seconds)`
- L184: def `Argus.src.stable_state.StableSequenceState._add_candidate(self, sample, frame)`
- L189: def `Argus.src.stable_state.StableSequenceState.to_manifest(self, status, termination_reason, trigger_relation, previous_sequence_id, gap_from_previous_seconds, preceding_motion_id, motion_end_time_seconds, rejection_reason)`
- L238: def `Argus.src.stable_state.StableSequenceState.debug_frames(self)`

#### Function Call References
- `Argus.src.stable_state.StableSequenceState.__init__`
  - no calls
- `Argus.src.stable_state.StableSequenceState.stable_duration_seconds`
  - L85: `sorted()`
  - L85: `self.candidate_frames.values()`
  - L86: `len()`
  - L88: `float()`
- `Argus.src.stable_state.StableSequenceState.add_relation`
  - L102: `self._add_candidate()`
  - L104: `previous_frame.copy()`
  - L105: `self._add_candidate()`
  - L106: `self.stable_relations.append()`
- `Argus.src.stable_state.StableSequenceState.enter_grace_period`
  - no calls
- `Argus.src.stable_state.StableSequenceState.grace_elapsed_seconds`
  - L119: `float()`
  - L120: `max()`
- `Argus.src.stable_state.StableSequenceState.recover_from_grace_period`
  - no calls
- `Argus.src.stable_state.StableSequenceState.confirm`
  - no calls
- `Argus.src.stable_state.StableSequenceState.select_best_frame`
  - L134: `CandidateFrame()`
  - L135: `self.candidate_frames.values()`
  - L137: `selector.select()`
  - L139: `selected.image.copy()`
- `Argus.src.stable_state.StableSequenceState.to_segment`
  - L148: `sorted()`
  - L148: `self.candidate_frames.values()`
  - L150: `ValueError()`
  - L166: `len()`
  - L181: `str()`
- `Argus.src.stable_state.StableSequenceState._add_candidate`
  - L187: `frame.copy()`
- `Argus.src.stable_state.StableSequenceState.to_manifest`
  - L200: `sorted()`
  - L200: `self.candidate_frames.values()`
  - L219: `len()`
  - L220: `len()`
- `Argus.src.stable_state.StableSequenceState.debug_frames`
  - L239: `sorted()`
  - L239: `self.candidate_frames.values()`
  - L243: `len()`

### `Argus/src/video_reader.py`

Module: `Argus.src.video_reader`

#### Imports
- L1: `from __future__ import annotations`
- L3: `from dataclasses import dataclass`
- L4: `from pathlib import Path`
- L6: `import cv2`

#### Classes / Functions
- L13: class `Argus.src.video_reader.VideoMetadata` bases: `object`
- L27: def `Argus.src.video_reader.find_single_video(input_dir)`
- L45: def `Argus.src.video_reader.format_duration(seconds)`
- L54: def `Argus.src.video_reader.decode_fourcc(value)`
- L61: def `Argus.src.video_reader.read_metadata(video_path)`

#### Function Call References
- `Argus.src.video_reader.find_single_video`
  - L28: `input_dir.exists()`
  - L29: `FileNotFoundError()`
  - L31: `sorted()`
  - L33: `input_dir.iterdir()`
  - L34: `path.is_file()`
  - L34: `path.suffix.lower()`
  - L38: `FileNotFoundError()`
  - L39: `len()`
  - L40: `', '.join()`
  - L41: `ValueError()`
  - L41: `len()`
- `Argus.src.video_reader.format_duration`
  - L46: `max()`
  - L46: `int()`
  - L46: `round()`
  - L47: `divmod()`
  - L48: `divmod()`
- `Argus.src.video_reader.decode_fourcc`
  - L55: `int()`
  - L56: `chr()`
  - L56: `range()`
  - L57: `''.join.strip.strip()`
  - L57: `''.join.strip()`
  - L57: `''.join()`
- `Argus.src.video_reader.read_metadata`
  - L62: `cv2.VideoCapture()`
  - L62: `str()`
  - L64: `bool()`
  - L64: `capture.isOpened()`
  - L66: `ValueError()`
  - L68: `float()`
  - L68: `capture.get()`
  - L69: `int()`
  - L69: `capture.get()`
  - L70: `int()`
  - L70: `capture.get()`
  - L71: `int()`
  - L71: `capture.get()`
  - L72: `decode_fourcc()`
  - L72: `capture.get()`
  - L75: `VideoMetadata()`
  - L77: `str()`
  - L78: `video_path.stat()`
  - L84: `format_duration()`
  - L89: `capture.release()`

### `Argus/tests/__init__.py`

Module: `Argus.tests.__init__`

#### Imports
- none

#### Classes / Functions
- none

#### Function Call References
- none

## Reverse Project References

Static AST match. Dynamic dispatch and same short-name ambiguity may produce multiple candidates.

### `Argus.argus._configure_logging`
- `Argus.argus.main` L26: `_configure_logging()`

### `Argus.argus._load_config`
- `Argus.argus.main` L31: `_load_config()`

### `Argus.argus.main`
- no internal call references found

### `Argus.src.best_frame_selector.BestFrameSelector`
- no internal call references found

### `Argus.src.best_frame_selector.BestFrameSelector.select`
- `Argus.src.stable_state.StableSequenceState.select_best_frame` L137: `selector.select()`

### `Argus.src.best_frame_selector.CandidateFrame`
- `Argus.src.stable_state.StableSequenceState.select_best_frame` L134: `CandidateFrame()`

### `Argus.src.frame_metrics.difference_score`
- no internal call references found

### `Argus.src.frame_metrics.ssim`
- no internal call references found

### `Argus.src.frame_source.DecodedFrame`
- `Argus.src.frame_source.SequentialFrameSource.__iter__` L42: `DecodedFrame()`

### `Argus.src.frame_source.SequentialFrameSource`
- no internal call references found

### `Argus.src.frame_source.SequentialFrameSource.__init__`
- no internal call references found

### `Argus.src.frame_source.SequentialFrameSource.__iter__`
- no internal call references found

### `Argus.src.frame_source.SequentialFrameSource._timestamp`
- `Argus.src.frame_source.SequentialFrameSource.__iter__` L39: `self._timestamp()`

### `Argus.src.json_utils.scrub_json`
- `Argus.src.json_utils.scrub_json` L10: `scrub_json()`
- `Argus.src.json_utils.scrub_json` L12: `scrub_json()`

### `Argus.src.report_writer.ReportWriter`
- `Argus.argus.main` L39: `ReportWriter()`

### `Argus.src.report_writer.ReportWriter.__init__`
- no internal call references found

### `Argus.src.report_writer.ReportWriter.write_stable_segments`
- `Argus.argus.main` L40: `writer.write_stable_segments()`

### `Argus.src.stable_rule.StableRule`
- no internal call references found

### `Argus.src.stable_rule.StableRule.__init__`
- no internal call references found

### `Argus.src.stable_rule.StableRule.is_complete_sequence`
- no internal call references found

### `Argus.src.stable_rule.StableRule.is_motion_relation`
- no internal call references found

### `Argus.src.stable_rule.StableRule.is_qualifying_relation`
- `Argus.src.stable_rule.StableRule.is_sequence_relation` L55: `self.is_qualifying_relation()`

### `Argus.src.stable_rule.StableRule.is_sequence_relation`
- no internal call references found

### `Argus.src.stable_rule.StableRule.is_start_relation`
- no internal call references found

### `Argus.src.stable_rule.StableRule.motion_difference_score`
- `Argus.src.stable_rule.StableRule.is_motion_relation` L67: `self.motion_difference_score()`

### `Argus.src.stable_state.FinalizeResult`
- no internal call references found

### `Argus.src.stable_state.FrameBufferItem`
- no internal call references found

### `Argus.src.stable_state.SampledFrame`
- no internal call references found

### `Argus.src.stable_state.StableRelation`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.__init__`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState._add_candidate`
- `Argus.src.stable_state.StableSequenceState.add_relation` L102: `self._add_candidate()`
- `Argus.src.stable_state.StableSequenceState.add_relation` L105: `self._add_candidate()`

### `Argus.src.stable_state.StableSequenceState.add_relation`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.confirm`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.debug_frames`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.enter_grace_period`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.grace_elapsed_seconds`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.recover_from_grace_period`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.select_best_frame`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.stable_duration_seconds`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.to_manifest`
- no internal call references found

### `Argus.src.stable_state.StableSequenceState.to_segment`
- no internal call references found

### `Argus.src.video_reader.VideoMetadata`
- `Argus.src.video_reader.read_metadata` L75: `VideoMetadata()`

### `Argus.src.video_reader.decode_fourcc`
- `Argus.src.video_reader.read_metadata` L72: `decode_fourcc()`

### `Argus.src.video_reader.find_single_video`
- `Argus.argus.main` L36: `find_single_video()`

### `Argus.src.video_reader.format_duration`
- `Argus.src.video_reader.read_metadata` L84: `format_duration()`

### `Argus.src.video_reader.read_metadata`
- no internal call references found
