# Page Change Events

## Rule

| Field | Value |
| --- | --- |
| Page Change Condition | Decision Tree: changed_area_ratio <= changed_area_ratio_threshold => Same Page; otherwise ssim < ssim_threshold => Page Change; otherwise ECC Translation decides Same Page only when ecc_converged is true, ecc_score >= ecc_score_minimum, abs(ecc_dx) <= alignment_translation_maximum_pixels, and abs(ecc_dy) <= alignment_translation_maximum_pixels. |
| Changed Area Ratio Threshold | 0.100000 |
| SSIM Threshold | 0.500000 |
| ECC Score Minimum | 0.900000 |
| Alignment Translation Maximum Pixels | 2.000000 |
| Event Merge Gap Seconds | 0.300000 |
| Merge Rule | Positive Page Change frames are merged into one Page Change Event only when the actual decoded timestamp gap from the previous positive Change Frame is <= event_merge_gap_seconds. |
| Representative Frame Rule | For each Page Segment, select the frame with maximum laplacian_variance. |

## Summary

| Field | Value |
| --- | ---: |
| Page Change Event Count | 0 |
| Representative Count | 1 |
| Exported Page Count | 1 |

## Pages

| Page | Start Frame | End Frame | Representative Frame | Laplacian | Changed Area Peak | SSIM Minimum | ECC Score Minimum | ECC dx | ECC dy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 23 | 3 | 3865.727370 |  |  |  |  |  |
