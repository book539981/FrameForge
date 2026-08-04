# Argus

Argus 是 FF 的 M1 Video Analyzer。

## Current Phase

目前正式流程：

- 找到單一輸入影片
- 讀取影片 metadata
- 依 sampling 設定抽樣 frame
- 計算亮度、對比、Laplacian、黑邊比例等 metrics
- 產生 Video Analyzer JSON report
- 產生 Video Analyzer Markdown report
