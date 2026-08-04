# Argus

Argus is the FF M1 Video Analyzer.

## Current Milestone

```text
M1
Video Analyzer
```

Argus reads one video from `input`, decodes frames sequentially, samples matching frames, and writes analyzer facts to JSON and Markdown reports.

## M1 Facts

Current frame metrics:

- Brightness mean
- Contrast standard deviation
- Laplacian variance
- Adjacent difference score against the previous successful sample
- Lookback difference score against the sample `analysis.lookback_sample_offset` positions earlier

Reader diagnostics record metadata-derived duration, sequential decode results, sample request ranges, EOF status, and failed sample requests.

## Run

```powershell
python .\Argus\argus.py
```

Reports are written to:

```text
Argus/output/artifacts/video_report.json
Argus/output/artifacts/video_report.md
```
