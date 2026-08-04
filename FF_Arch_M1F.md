# FF Architecture M1F

Generated for the current FF M1F codebase.

Scope:

- Project structure under `D:\TTT\FF`
- M1F Argus execution pipeline
- Python classes, functions, and direct call references

Excluded from structural expansion:

- `.git`
- `.venv`
- `__pycache__`

---

## 1. Current Milestone

```text
M1
Video Analyzer
```

M1F current implementation focuses on Analyzer facts only:

- Sequential video decoding
- Sequential frame sampling
- Brightness
- Contrast
- Laplacian variance
- Adjacent difference
- Lookback difference
- JSON report
- Markdown report

No M2 behavior is part of this architecture file.

---

## 2. Project Structure

```text
FF/
├─ .gitignore
├─ README.md
├─ FF_Arch_M1F.md
├─ Argus/
│  ├─ argus.py
│  ├─ config.yaml
│  ├─ README.md
│  ├─ requirements.txt
│  ├─ input/
│  │  ├─ .gitkeep
│  │  └─ 5秒AP搖高版17-2頁測試檔.MP4
│  ├─ output/
│  │  └─ artifacts/
│  │     ├─ .gitkeep
│  │     ├─ video_report.json
│  │     └─ video_report.md
│  ├─ src/
│  │  ├─ __init__.py
│  │  ├─ analyzer.py
│  │  ├─ report_writer.py
│  │  └─ video_reader.py
│  └─ tests/
│     ├─ __init__.py
│     └─ video fixtures (*.MP4, *.MOV)
└─ Proto/
   ├─ FF_Constitution_V1.0.md
   ├─ FF_Dev_Workflow_V1.1.md
   └─ FF_Project_Reference.md
```

---

## 3. Module Responsibilities

| Path | Responsibility |
| --- | --- |
| `Argus/argus.py` | CLI entrypoint. Loads config, finds input video, runs analyzer, writes reports, prints execution summary. |
| `Argus/src/video_reader.py` | Video file discovery, metadata extraction, duration formatting, FOURCC decoding, timestamp conversion. |
| `Argus/src/analyzer.py` | M1F Analyzer. Sequentially decodes video, samples frames, computes metrics, builds report facts and diagnostics. |
| `Argus/src/report_writer.py` | Writes JSON report and renders Markdown report from analyzer facts. |
| `Argus/config.yaml` | M1F runtime config: input, output, sampling rate, lookback sample offset, report filenames. |
| `Argus/README.md` | Argus M1 usage and fact summary. |
| `Proto/*.md` | FF governance, project reference, and development workflow documents. |

---

## 4. M1F Pipeline

```text
Video

↓

Sequential Video Reader

↓

Sequential Frame Sampling

↓

Brightness
Contrast
Laplacian
Adjacent Difference
Lookback Difference

↓

Analyzer

↓

JSON Report
Markdown Report
```

---

## 5. Runtime Flow

```text
argus.py main()

↓

_load_config()

↓

find_single_video()

↓

VideoAnalyzer.analyze()

↓

read_metadata()

↓

VideoAnalyzer._sample_frames()

↓

VideoAnalyzer._analyze_frame()

↓

ReportWriter.write()

↓

ReportWriter._to_markdown()
```

---

## 6. Config Shape

```yaml
input:
  directory: input

output:
  artifacts_directory: output/artifacts

sampling:
  samples_per_second: 5

analysis:
  lookback_sample_offset: 2

report:
  json_filename: video_report.json
  markdown_filename: video_report.md
```

---

## 7. Function And Class Inventory

### `Argus/argus.py`

| Symbol | Line | Kind | Responsibility |
| --- | ---: | --- | --- |
| `_configure_logging` | 15 | function | Configure process logging. |
| `_load_config` | 19 | function | Read `Argus/config.yaml` with UTF-8 and parse YAML. |
| `main` | 25 | function | Run the full Argus CLI workflow and return exit code. |

### `Argus/src/video_reader.py`

| Symbol | Line | Kind | Responsibility |
| --- | ---: | --- | --- |
| `VideoMetadata` | 13 | dataclass | Store OpenCV-derived video metadata facts. |
| `find_single_video` | 27 | function | Locate exactly one supported video file in input directory. |
| `format_duration` | 45 | function | Format seconds as `MM:SS` or `HH:MM:SS`. |
| `decode_fourcc` | 54 | function | Convert numeric FOURCC to readable codec string. |
| `read_metadata` | 61 | function | Open video once and collect metadata facts. |
| `timestamp_for_frame` | 91 | function | Convert frame index to timestamp seconds. |

### `Argus/src/analyzer.py`

| Symbol | Line | Kind | Responsibility |
| --- | ---: | --- | --- |
| `FrameMetrics` | 19 | dataclass | Store per-sampled-frame M1 facts. |
| `SampleFailure` | 42 | dataclass | Store failed sample request facts when sequential decode fails before metadata end. |
| `VideoAnalyzer` | 49 | class | Coordinate M1 analysis for a single video. |
| `VideoAnalyzer.__init__` | 50 | method | Read sampling and analysis config. |
| `VideoAnalyzer.analyze` | 60 | method | Build full JSON-ready analyzer report. |
| `VideoAnalyzer._frame_interval` | 134 | method | Convert FPS and sample rate into frame interval. |
| `VideoAnalyzer._sample_frames` | 139 | method | Sequentially decode frames and analyze frames matching the sample interval. |
| `VideoAnalyzer._analyze_frame` | 241 | method | Compute metrics for one sampled frame. |
| `VideoAnalyzer._unsampled_tail_frame_count` | 308 | method | Count legal tail frames not selected by interval sampling. |
| `VideoAnalyzer._unsampled_tail_duration_seconds` | 316 | method | Convert unsampled tail frame count to seconds. |
| `VideoAnalyzer._failed_tail_frame_count` | 324 | method | Count failed sample requests after the last successful sample. |
| `VideoAnalyzer._failed_tail_duration_seconds` | 332 | method | Convert failed tail sample count to seconds. |
| `VideoAnalyzer._per_second_summary` | 339 | method | Aggregate sampled metrics by integer second. |
| `VideoAnalyzer._warnings` | 367 | method | Produce report warnings for missing metadata or no samples. |
| `normalized_mean_absolute_difference` | 378 | function | Compute grayscale mean absolute difference normalized to 0..1. |
| `summarize_values` | 382 | function | Compute min, max, mean, median, std dev, and percentiles while ignoring nulls. |
| `mean` | 411 | function | Compute mean while ignoring nulls. |
| `scrub_json` | 416 | function | Recursively replace non-finite floats with JSON-safe null. |

### `Argus/src/report_writer.py`

| Symbol | Line | Kind | Responsibility |
| --- | ---: | --- | --- |
| `ReportWriter` | 8 | class | Write analyzer facts to JSON and Markdown artifacts. |
| `ReportWriter.__init__` | 9 | method | Resolve output artifacts directory. |
| `ReportWriter.write` | 14 | method | Write `video_report.json` and `video_report.md`. |
| `ReportWriter._to_markdown` | 26 | method | Render the full Markdown report. |
| `ReportWriter._statistics_table` | 111 | method | Render multi-metric statistics table. |
| `ReportWriter._single_statistics_table` | 132 | method | Render one metric statistics table. |
| `ReportWriter._reader_diagnostics_table` | 144 | method | Render reader diagnostics table. |
| `ReportWriter._failed_samples_table` | 175 | method | Render failed samples table. |
| `ReportWriter._per_second_table` | 190 | method | Render per-second summary table. |
| `ReportWriter._messages` | 205 | method | Render warnings and errors. |
| `fmt` | 217 | function | Format report values for Markdown tables. |

---

## 8. Import References

### `Argus/argus.py`

```text
logging
sys
time
pathlib.Path
yaml
src.analyzer.VideoAnalyzer
src.report_writer.ReportWriter
src.video_reader.find_single_video
```

### `Argus/src/video_reader.py`

```text
dataclasses.dataclass
pathlib.Path
cv2
```

### `Argus/src/analyzer.py`

```text
collections.defaultdict
dataclasses.asdict
dataclasses.dataclass
pathlib.Path
typing.Any
cv2
numpy as np
video_reader.format_duration
video_reader.read_metadata
video_reader.timestamp_for_frame
```

### `Argus/src/report_writer.py`

```text
json
pathlib.Path
typing.Any
```

---

## 9. Direct Function Call References

### `Argus/argus.py`

| Caller | Direct calls |
| --- | --- |
| `_configure_logging` | `logging.basicConfig` |
| `_load_config` | `config_path.open`, `yaml.safe_load` |
| `main` | `_configure_logging`, `time.perf_counter`, `Path`, `resolve`, `_load_config`, `mkdir`, `find_single_video`, `VideoAnalyzer`, `analyzer.analyze`, `ReportWriter`, `writer.write`, `relative_to`, `print`, `logging.error` |
| module guard | `sys.exit`, `main` |

### `Argus/src/video_reader.py`

| Caller | Direct calls |
| --- | --- |
| `find_single_video` | `input_dir.exists`, `input_dir.iterdir`, `path.is_file`, `path.suffix.lower`, `sorted`, `len`, `join`, `FileNotFoundError`, `ValueError` |
| `format_duration` | `max`, `round`, `int`, `divmod` |
| `decode_fourcc` | `int`, `range`, `chr`, `join`, `strip` |
| `read_metadata` | `cv2.VideoCapture`, `str`, `capture.isOpened`, `ValueError`, `capture.get`, `float`, `int`, `decode_fourcc`, `video_path.stat`, `VideoMetadata`, `format_duration`, `capture.release` |
| `timestamp_for_frame` | `round` |

### `Argus/src/analyzer.py`

| Caller | Direct calls |
| --- | --- |
| `VideoAnalyzer.__init__` | `float`, `int`, `ValueError` |
| `VideoAnalyzer.analyze` | `read_metadata`, `_frame_interval`, `range`, `list`, `_sample_frames`, `asdict`, `reader_diagnostics.update`, `len`, `_unsampled_tail_frame_count`, `_unsampled_tail_duration_seconds`, `_failed_tail_frame_count`, `_failed_tail_duration_seconds`, `summarize_values`, `_per_second_summary`, `_warnings`, `scrub_json` |
| `VideoAnalyzer._frame_interval` | `max`, `int`, `round` |
| `VideoAnalyzer._sample_frames` | `cv2.VideoCapture`, `str`, `capture.read`, `timestamp_for_frame`, `capture.get`, `float`, `_analyze_frame`, `frames.append`, `successful_history.append`, `capture.release`, `range`, `failed_samples.append`, `SampleFailure`, `max`, `round` |
| `VideoAnalyzer._analyze_frame` | `cv2.cvtColor`, `timestamp_for_frame`, `normalized_mean_absolute_difference`, `round`, `FrameMetrics`, `format_duration`, `int`, `float`, `np.mean`, `np.std`, `cv2.Laplacian`, `var` |
| `VideoAnalyzer._unsampled_tail_frame_count` | `max` |
| `VideoAnalyzer._unsampled_tail_duration_seconds` | `_unsampled_tail_frame_count`, `round` |
| `VideoAnalyzer._failed_tail_frame_count` | `sum` |
| `VideoAnalyzer._failed_tail_duration_seconds` | `_failed_tail_frame_count`, `round` |
| `VideoAnalyzer._per_second_summary` | `defaultdict`, `sorted`, `rows.append`, `len`, `mean`, `min` |
| `VideoAnalyzer._warnings` | `warnings.append` |
| `normalized_mean_absolute_difference` | `cv2.absdiff`, `np.mean`, `float` |
| `summarize_values` | `float`, `np.array`, `np.min`, `np.max`, `np.mean`, `np.median`, `np.std`, `np.percentile` |
| `mean` | `float`, `sum`, `len` |
| `scrub_json` | `isinstance`, `value.items`, recursive `scrub_json`, `np.isfinite` |

### `Argus/src/report_writer.py`

| Caller | Direct calls |
| --- | --- |
| `ReportWriter.__init__` | path composition only |
| `ReportWriter.write` | `mkdir`, `json_path.open`, `json.dump`, `handle.write`, `_to_markdown`, `markdown_path.write_text` |
| `ReportWriter._to_markdown` | `_reader_diagnostics_table`, `_statistics_table`, `_single_statistics_table`, `_failed_samples_table`, `_per_second_table`, `_messages`, `join`, `fmt` |
| `ReportWriter._statistics_table` | `labels.items`, `rows.append`, `fmt`, `join` |
| `ReportWriter._single_statistics_table` | `rows.append`, `fmt`, `join` |
| `ReportWriter._reader_diagnostics_table` | `diagnostics.get`, `fmt`, `rows.append`, `join` |
| `ReportWriter._failed_samples_table` | `rows.append`, `fmt`, `join` |
| `ReportWriter._per_second_table` | `str`, `join`, `table.append`, `fmt` |
| `ReportWriter._messages` | `lines.append`, `join` |
| `fmt` | `isinstance`, `str` |

---

## 10. Key Data Structures

### `VideoMetadata`

```text
filename
path
size_bytes
width
height
fps
total_frames
duration_seconds
duration_formatted
codec_fourcc
is_opened
```

### `FrameMetrics`

```text
sample_index
frame_index
timestamp_seconds
timestamp_formatted
second
brightness_mean
contrast_std
laplacian_variance
adjacent_difference_score
adjacent_sample_index
adjacent_frame_index
adjacent_timestamp_seconds
adjacent_actual_seconds
lookback_difference_score
lookback_sample_offset
lookback_sample_index
lookback_frame_index
lookback_timestamp_seconds
lookback_actual_seconds
```

### `SampleFailure`

```text
requested_frame_index
expected_timestamp_seconds
capture_position_frames
capture_position_msec
```

---

## 11. Report Top-Level Shape

```text
schema_version
video_metadata
config
reader_diagnostics
sampling
frame_statistics
sampled_frames
failed_samples
per_second_summary
warnings
errors
```

---

## 12. Reader Diagnostics Shape

```text
metadata_total_frames
metadata_fps
metadata_duration_seconds
duration_from_frame_count_seconds
decode_attempt_count
decoded_frame_count
normal_eof_count
unexpected_decode_failure_count
last_successful_frame_index
last_successful_timestamp_seconds
first_failed_frame_index
first_failed_timestamp_seconds
capture_position_frames_at_failure
capture_position_msec_at_failure
expected_last_frame_index
missing_tail_frame_count
missing_tail_duration_seconds
requested_sample_count
successful_sample_count
failed_sample_count
```

---

## 13. Sampling Semantics

Formal M1F sampling is sequential decode-driven:

```text
Open one VideoCapture
↓
capture.read() from frame 0 forward
↓
frame_index = decoded_frame_count before increment
↓
if frame_index % frame_interval == 0
  analyze sampled frame
else
  discard frame
↓
normal EOF ends loop
```

Formal sampling does not use random frame seek.

`CAP_PROP_POS_FRAMES` is only read in diagnostics to record OpenCV's position at EOF or decode failure.

---

## 14. Difference Semantics

Adjacent Difference:

```text
sample[n]
vs
sample[n-1]
```

Lookback Difference:

```text
sample[n]
vs
sample[n - analysis.lookback_sample_offset]
```

Current config:

```text
analysis.lookback_sample_offset = 2
```

Both metrics use grayscale mean absolute difference:

```python
float(np.mean(cv2.absdiff(previous_gray, current_gray))) / 255.0
```

---

## 15. M1 Boundary Check

This architecture describes current M1F facts and diagnostics only.

Not part of M1F:

- Stable Rule
- Threshold
- State Machine
- Processor
- Best Frame
- Page Export
- SSIM
- Anchor Difference
- Motion Detection
