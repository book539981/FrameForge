from __future__ import annotations

import os
import queue
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from src.desktop_ocr_runner import OCRBatchCancelled, run_ocr_batch
from src.desktop_page_extraction_runner import (
    PageExtractionCancelled,
    run_page_extraction,
)


def _resolve_argus_roots() -> tuple[Path, Path]:
    if not getattr(sys, "frozen", False):
        argus_root = Path(__file__).resolve().parent
        return argus_root, argus_root

    resource_root = Path(getattr(sys, "_MEIPASS")) / "Argus"
    writable_root = Path(sys.executable).resolve().parent / "Argus"
    writable_root.mkdir(parents=True, exist_ok=True)

    bundled_config = resource_root / "config.yaml"
    writable_config = writable_root / "config.yaml"
    if not writable_config.exists():
        shutil.copy2(bundled_config, writable_config)

    return writable_root, resource_root


ARGUS_ROOT, RESOURCE_ARGUS_ROOT = _resolve_argus_roots()
DEFAULT_PAGE_EXPORT_DIR = ARGUS_ROOT / "output" / "page_export"
MODEL_ROOT_DIR = RESOURCE_ARGUS_ROOT / "output" / "artifacts" / "ocr_calibration" / "models"


class FFDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("FrameForge")
        self.root.minsize(760, 360)

        self.video_path = tk.StringVar()
        self.image_dir = tk.StringVar(value=str(DEFAULT_PAGE_EXPORT_DIR))
        self.output_text_path = tk.StringVar()
        self.stage = tk.StringVar(value="待機")
        self.progress_text = tk.StringVar(value="0 / 0")
        self.current_file = tk.StringVar(value="")

        self.worker_thread: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.messages: queue.Queue[dict[str, object]] = queue.Queue()

        self._build_ui()
        self.root.after(100, self._poll_messages)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        ttk.Label(outer, text="影片：").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(outer, textvariable=self.video_path).grid(
            row=0, column=1, sticky="ew", padx=(8, 8), pady=6
        )
        ttk.Button(outer, text="選擇影片", command=self._choose_video).grid(
            row=0, column=2, sticky="ew", pady=6
        )

        ttk.Label(outer, text="圖片資料夾：").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(outer, textvariable=self.image_dir).grid(
            row=1, column=1, sticky="ew", padx=(8, 8), pady=6
        )
        folder_buttons = ttk.Frame(outer)
        folder_buttons.grid(row=1, column=2, sticky="ew", pady=6)
        ttk.Button(folder_buttons, text="選擇資料夾", command=self._choose_image_dir).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(folder_buttons, text="開啟資料夾", command=self._open_image_dir).grid(
            row=0, column=1
        )

        action_bar = ttk.Frame(outer)
        action_bar.grid(row=2, column=0, columnspan=3, sticky="w", pady=(14, 10))
        self.extract_button = ttk.Button(
            action_bar, text="擷取圖片", command=self._start_page_extraction
        )
        self.extract_button.grid(row=0, column=0, padx=(0, 8))
        self.ocr_button = ttk.Button(action_bar, text="開始 OCR", command=self._start_ocr)
        self.ocr_button.grid(row=0, column=1, padx=(0, 8))
        self.cancel_button = ttk.Button(
            action_bar, text="中止", command=self._cancel_current, state="disabled"
        )
        self.cancel_button.grid(row=0, column=2)

        ttk.Separator(outer).grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(outer, text="目前階段：").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Label(outer, textvariable=self.stage).grid(
            row=4, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=4
        )

        ttk.Label(outer, text="目前進度：").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Label(outer, textvariable=self.progress_text).grid(
            row=5, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=4
        )

        ttk.Label(outer, text="目前檔案：").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Label(outer, textvariable=self.current_file).grid(
            row=6, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=4
        )

        self.progress_bar = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress_bar.grid(
            row=7, column=0, columnspan=3, sticky="ew", pady=(8, 12)
        )

        ttk.Label(outer, text="輸出文字：").grid(row=8, column=0, sticky="w", pady=6)
        ttk.Entry(outer, textvariable=self.output_text_path).grid(
            row=8, column=1, sticky="ew", padx=(8, 8), pady=6
        )
        ttk.Button(
            outer, text="開啟輸出資料夾", command=self._open_output_dir
        ).grid(row=8, column=2, sticky="ew", pady=6)

    def _choose_video(self) -> None:
        path = filedialog.askopenfilename(
            title="選擇影片",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.m4v *.mkv *.avi"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.video_path.set(path)

    def _choose_image_dir(self) -> None:
        path = filedialog.askdirectory(title="選擇圖片資料夾")
        if path:
            self.image_dir.set(path)

    def _open_image_dir(self) -> None:
        self._open_folder(Path(self.image_dir.get()))

    def _open_output_dir(self) -> None:
        output = Path(self.output_text_path.get())
        folder = output.parent if output.name else Path(self.image_dir.get())
        self._open_folder(folder)

    def _open_folder(self, folder: Path) -> None:
        if not folder.exists():
            messagebox.showerror("無法開啟資料夾", f"資料夾不存在：\n{folder}")
            return
        os.startfile(folder)

    def _start_page_extraction(self) -> None:
        video = Path(self.video_path.get())
        if not video.exists() or not video.is_file():
            messagebox.showerror("無法擷取圖片", "請先選擇有效影片。")
            return
        self._start_worker(
            lambda: run_page_extraction(
                argus_root=ARGUS_ROOT,
                video_path=video,
                cancel_event=self.cancel_event,
                progress_callback=self.messages.put,
            ),
            success_kind="m2_done",
            cancelled_exception=PageExtractionCancelled,
        )

    def _start_ocr(self) -> None:
        image_dir = Path(self.image_dir.get())
        if not image_dir.exists() or not image_dir.is_dir():
            messagebox.showerror("無法開始 OCR", "請先選擇有效圖片資料夾。")
            return
        self._start_worker(
            lambda: run_ocr_batch(
                image_dir=image_dir,
                model_root_dir=MODEL_ROOT_DIR,
                cancel_event=self.cancel_event,
                progress_callback=self.messages.put,
            ),
            success_kind="ocr_done",
            cancelled_exception=OCRBatchCancelled,
        )

    def _start_worker(
        self,
        work: Callable[[], object],
        success_kind: str,
        cancelled_exception: type[Exception],
    ) -> None:
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.cancel_event.clear()
        self._set_busy(True)
        self.stage.set("準備中")
        self.progress_text.set("0 / 0")
        self.current_file.set("")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start(12)

        def run() -> None:
            try:
                result = work()
            except cancelled_exception:
                self.messages.put({"kind": "cancelled"})
            except Exception as exc:
                self.messages.put({"kind": "error", "message": str(exc)})
            else:
                self.messages.put({"kind": success_kind, "result": result})

        self.worker_thread = threading.Thread(target=run, daemon=True)
        self.worker_thread.start()

    def _cancel_current(self) -> None:
        self.cancel_event.set()
        self.stage.set("正在中止")

    def _poll_messages(self) -> None:
        while True:
            try:
                message = self.messages.get_nowait()
            except queue.Empty:
                break
            self._handle_message(message)
        self.root.after(100, self._poll_messages)

    def _handle_message(self, message: dict[str, object]) -> None:
        kind = message.get("kind")
        if kind == "progress":
            self._handle_progress(message)
        elif kind == "m2_done":
            result = message["result"]
            page_export_dir = getattr(result, "page_export_dir")
            page_count = getattr(result, "page_count")
            self.image_dir.set(str(page_export_dir))
            self.stage.set("圖片擷取完成")
            self.progress_text.set(f"{page_count} / {page_count}")
            self.current_file.set("")
            self._finish_worker()
        elif kind == "ocr_done":
            result = message["result"]
            self.output_text_path.set(str(getattr(result, "output_text_path")))
            page_count = getattr(result, "page_count")
            self.stage.set("OCR 完成")
            self.progress_text.set(f"{page_count} / {page_count}")
            self._finish_worker()
        elif kind == "cancelled":
            self.stage.set("已中止")
            self._finish_worker()
        elif kind == "error":
            self.stage.set("錯誤")
            self._finish_worker()
            messagebox.showerror("執行失敗", str(message.get("message", "")))

    def _handle_progress(self, message: dict[str, object]) -> None:
        status = str(message.get("status") or "")
        stage = str(message.get("stage") or "")
        current = message.get("current")
        total = message.get("total")
        filename = message.get("filename")
        self.stage.set(f"{stage}｜{status}" if status else stage)
        self.current_file.set(str(filename or ""))

        if isinstance(current, int) and isinstance(total, int) and total > 0:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar["value"] = int((current / total) * 100)
            self.progress_text.set(f"{current} / {total}")
        else:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_text.set("執行中")
            self.progress_bar.start(12)

    def _finish_worker(self) -> None:
        self.progress_bar.stop()
        if self.progress_bar["mode"] == "indeterminate":
            self.progress_bar.configure(mode="determinate")
        self.worker_thread = None
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        normal = "disabled" if busy else "normal"
        cancel = "normal" if busy else "disabled"
        self.extract_button.configure(state=normal)
        self.ocr_button.configure(state=normal)
        self.cancel_button.configure(state=cancel)


def main() -> None:
    if "--packaging-smoke-test" in sys.argv:
        raise SystemExit(_run_packaging_smoke_test())

    root = tk.Tk()
    FFDesktopApp(root)
    root.mainloop()


def _run_packaging_smoke_test() -> int:
    try:
        import cv2
        import numpy as np

        ARGUS_ROOT.mkdir(parents=True, exist_ok=True)
        output_dir = ARGUS_ROOT / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        test_video = output_dir / "packaging_smoke_test.mp4"

        writer = cv2.VideoWriter(
            str(test_video),
            cv2.VideoWriter_fourcc(*"mp4v"),
            5.0,
            (320, 240),
        )
        for page_index, text in enumerate(["PAGE 1", "PAGE 2", "PAGE 3"]):
            frame = np.full((240, 320, 3), 255, dtype=np.uint8)
            cv2.putText(
                frame,
                text,
                (60, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 0),
                3,
                cv2.LINE_AA,
            )
            cv2.rectangle(
                frame,
                (20, 20),
                (300, 220),
                (page_index * 70 % 255, page_index * 40 % 255, page_index * 110 % 255),
                3,
            )
            for _ in range(8):
                writer.write(frame)
        writer.release()

        m2_messages: list[dict[str, object]] = []
        m2_result = run_page_extraction(
            argus_root=ARGUS_ROOT,
            video_path=test_video,
            cancel_event=threading.Event(),
            progress_callback=m2_messages.append,
        )
        if m2_result.page_count < 1:
            raise RuntimeError("M2 smoke test produced no page images.")

        first_page = m2_result.page_export_dir / "page_001.png"
        second_page = m2_result.page_export_dir / "page_002.png"
        if first_page.exists() and not second_page.exists():
            shutil.copy2(first_page, second_page)

        ocr_messages: list[dict[str, object]] = []
        ocr_result = run_ocr_batch(
            image_dir=m2_result.page_export_dir,
            model_root_dir=MODEL_ROOT_DIR,
            cancel_event=threading.Event(),
            progress_callback=ocr_messages.append,
        )
        if not ocr_result.output_text_path.exists():
            raise RuntimeError("OCR smoke test did not produce raw_ocr_text.txt.")

        cancel_event = threading.Event()
        cancel_messages: list[dict[str, object]] = []

        def cancel_after_first_page(message: dict[str, object]) -> None:
            cancel_messages.append(message)
            if message.get("current") == 1:
                cancel_event.set()

        try:
            run_ocr_batch(
                image_dir=m2_result.page_export_dir,
                model_root_dir=MODEL_ROOT_DIR,
                cancel_event=cancel_event,
                progress_callback=cancel_after_first_page,
            )
        except OCRBatchCancelled:
            pass
        else:
            raise RuntimeError("OCR cancellation smoke test did not cancel.")

        report_path = output_dir / "packaging_smoke_result.txt"
        report_path.write_text(
            "\n".join(
                [
                    "PASS",
                    f"argus_root={ARGUS_ROOT}",
                    f"model_root={MODEL_ROOT_DIR}",
                    f"page_export={m2_result.page_export_dir}",
                    f"ocr_output={ocr_result.output_text_path}",
                    f"m2_progress_events={len(m2_messages)}",
                    f"ocr_progress_events={len(ocr_messages)}",
                    f"cancel_progress_events={len(cancel_messages)}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        report_path = ARGUS_ROOT / "output" / "packaging_smoke_result.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(f"FAIL\n{exc}\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    main()
