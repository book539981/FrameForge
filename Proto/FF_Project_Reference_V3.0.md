# FF Project Reference（FF 專案參考文件）

Version：V3.0（Formal）

---

# 一、Milestone Roadmap

```text
M0
Project Bootstrap
✅ Closed

↓

M1
Video Analyzer
✅ Closed

↓

M2
Automatic Page Extraction
✅ Closed

↓

M3
OCR
← Current

↓

M4
Markdown Export

↓

M5
Book Export
```

---

# 二、Current Architecture

```text
Video
↓
Sequential Decode
↓
Adjacent Frame Comparison
↓
Facts
↓
Page Change Detection
↓
Page Segment
↓
Representative Frame
↓
page_xxx.png
↓
OCR
↓
Text Result
```

目前 M2 正式輸出：

```text
page_export/
page_001.png
page_002.png
...
```

上述圖片為 M3 OCR 的正式 Input。

---

# 三、Roles

## Bryan

負責：

* 定義 Problem
* 判讀 Facts
* 建立 Rule
* 決定架構
* 驗收結果

## 協作 AI

負責：

* 分析與整理
* 推演方案
* Review 架構
* 協助制定 Rule
* 協助定位問題

不直接決定 Rule。

## Coding Agent（CX）

負責：

* 實作已定義需求
* 修改與重構程式
* 清理技術債

不負責：

* 建立 Problem
* 建立 Rule
* 決定架構方向

---

# 四、Glossary

**Facts**
經 Analyzer 產生且可驗證的客觀資料。

**Rule**
根據 Facts 建立，交由 Processor 執行的正式規則。

**Analyzer**
負責分析資料與建立 Facts，不負責正式輸出。

**Processor**
執行已確認 Rule 並產生正式輸出。

**Page Change Event**
由連續 Frame Change 合併形成的一次換頁事件。

**Page Segment**
代表正式頁面存在範圍的 Segment。

**Representative Frame**
Page Segment 最終選出的代表圖片。

**Debug Report**
供分析、驗證與除錯使用，不屬正式成果。

---
