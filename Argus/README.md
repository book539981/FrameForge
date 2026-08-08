# Argus

Argus is the current FF M2 runtime for automatic page extraction.

## Runtime Flow

```text
Video
↓
Sequential Decode
↓
Frame Timeline Analyzer
↓
Page Change Rule
↓
Timestamp-based Event Merge
↓
Page Segment Builder
↓
Laplacian Representative Selector
↓
PNG Export
```

## Current Facts

- `frame_index`
- `decoded_timestamp_seconds`
- `changed_area_ratio`
- `ssim`
- `ecc_converged`
- `ecc_score`
- `ecc_dx`
- `ecc_dy`
- `laplacian_variance`

## Artifacts

- `output/artifacts/frame_difference_timeline.*`
- `output/artifacts/page_change_events.*`
- `output/page_export/page_*.png`
