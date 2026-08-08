# FF Project Reference（FF 專案參考文件）

Version：V2.0（Formal）

---

# 一、Milestone Roadmap

目前規劃：

```text
M0
Project Bootstrap

↓

M1
Video Analyzer

↓

M2
Automatic Page Extraction

↓

M3
OCR

↓

M4
Markdown Export

↓

M5
Book Export
```

各 Milestone 完成後，

才可進入下一階段。

不得跨越 Milestone 提前開發。

---

# 二、Current Architecture

目前 FF 架構：

```text
Video

↓

Sequential Decode

↓

Adjacent Frame Comparison

↓

Facts

Difference Mean
Changed Area Ratio
Laplacian
SSIM（Observation）

↓

Page Change Detection

↓

Representative Frame

↓

page_xxx.png
```

目前正式輸出：

```text
page_001.png
page_002.png
...
```
---

# 三、Roles

## Bryan

負責：

* 定義 Problem
* 判讀 Facts
* 建立 Rule
* 決定架構
* 驗收結果

---

## 協作 AI

負責：

* 分析問題
* 整理資訊
* 推演方案
* Review 架構
* 協助制定 Rule
* 協助定位問題

不直接決定 Rule。

---

## Coding Agent（CX）

負責：

* 修改程式
* 重構程式
* 清理技術債
* 完成已定義需求

不負責：

* 建立 Problem
* 建立 Rule
* 決定架構方向

---

# 四、名詞定義（Glossary）

## Candidate

Analyzer 保留下來、

等待判讀的候選結果。

---

## Facts

經 Analyzer 分析，

且可被驗證的客觀事實。

---

## Rule

根據 Facts 建立，

正式進入 Processor 執行的規則。

---

## Metric

用來量測畫面特徵的數值。

例如：

* Difference Mean
* Changed Area Ratio
* Laplacian
* SSIM

---

## Analyzer

負責分析資料、

建立 Facts。

不負責正式輸出。

---

## Processor

負責執行已驗證 Rule，

產生正式輸出。

---

## Page Change Event

由連續 Frame Change

合併後形成的一次換頁事件。

---

## Representative Frame

同一個 Page Change Event

最終輸出的代表圖片。

---

## Debug Report

供分析、

驗證、

除錯使用。

不屬正式成果。

---