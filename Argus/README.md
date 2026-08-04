# Argus

Argus 是 FF 的穩定頁面擷取引擎。

## Current Phase

目前正式流程：

- 找到單一輸入影片
- 使用 sequential frame source 逐幀讀取
- 以秒為尺度建立 frame relation
- 偵測 stable segment
- 在 confirmed segment 內持續收集 candidate frames
- 於 next motion 或 EOF 後選出最佳影格
- 輸出 `output/pages/page_xxx.png`
- 輸出 `output/artifacts/stable_segments.json`

## Recording Protocol

Processor 僅面向符合 FF V1 Recording Protocol 的影片：

- 固定縮放
- 固定裁切
- 每頁停留約 5 秒
- 翻頁期間保持不穩定
- 空白頁快速略過
