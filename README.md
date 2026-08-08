# FF - FrameForge

FF is a video-to-page extraction project.

## Current Milestone

```text
M2 | Automatic Page Extraction
```

## Current Runtime

```text
Input Video
↓
Sequential Decode
↓
Frame Timeline Facts
↓
Page Change Rule
↓
Page Change Event Merge
↓
Page Segment Build
↓
Representative Selection
↓
page_export PNG
```

Run:

```powershell
python .\Argus\argus.py
```
