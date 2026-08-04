# Argus

Argus is the FF Video Analyzer.

## Current Milestone

```text
M2 architecture alignment
Analyzer semantic correction
```

Argus reads one video from `input`, decodes frames sequentially, builds a sample sequence through the Sampling layer, computes frame metrics, and writes facts to JSON and Markdown reports.

## Analyzer Workflow

```text
Sequential Decode

↓

Time-based Sampling

↓

Frame Metrics Analysis

↓

Facts Output
```

## Frame Metrics Facts

Current frame metrics:

- Brightness mean
- Contrast standard deviation
- Laplacian variance
- Adjacent difference score against the previous successful sample
- Lookback difference score against the sample `analysis.lookback_sample_offset` positions earlier

Reader diagnostics record metadata-derived duration, sequential decode results, sample request ranges, EOF status, and failed sample requests.

Analyzer does not perform Stable decisions, thresholds, rules, state transitions, or representative frame selection.

## Run

```powershell
python .\Argus\argus.py
```

Reports are written to:

```text
Argus/output/artifacts/video_report.json
Argus/output/artifacts/video_report.md
```
