from __future__ import annotations

import re
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk
from typing import Any

import cv2
import yaml
from PIL import Image, ImageTk

ARGUS_ROOT = Path(__file__).resolve().parent
if str(ARGUS_ROOT) not in sys.path:
    sys.path.insert(0, str(ARGUS_ROOT))

from src.video_reader import find_single_video, format_duration, read_metadata


PAGE_PATTERN = re.compile(r"page_(\d{3})\.png$")


class ManualFramePicker:
    def __init__(
        self,
        root: tk.Tk,
        video_path: Path,
        output_dir: Path,
        initial_step_seconds: float,
        minimum_step_seconds: float,
        step_adjustment_seconds: float,
    ) -> None:
        self.root = root
        self.video_path = video_path
        self.output_dir = output_dir
        self.step_seconds = initial_step_seconds
        self.minimum_step_seconds = minimum_step_seconds
        self.step_adjustment_seconds = step_adjustment_seconds
        self.capture = cv2.VideoCapture(str(video_path))
        self.metadata = read_metadata(video_path)
        self.duration_seconds = self.metadata.duration_seconds
        self.total_frames = self.metadata.total_frames
        self.fps = self.metadata.fps
        self.current_frame_index = 0
        self.current_time_seconds = 0.0
        self.current_frame = None
        self.preview_image = None
        self.last_saved_filename = ""
        self.saved_message_until = 0.0
        self.space_pressed = False
        self.next_page_number = next_page_number(output_dir)
        self.saved_page_count = existing_page_count(output_dir)

        if not self.capture.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        if self.total_frames <= 0 or self.fps <= 0:
            raise ValueError(f"Invalid video metadata: {video_path}")

        self.root.title("FF 手動選頁工具")
        self.root.geometry("1100x850")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.preview_canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas_image_id = None
        self.progress = ttk.Progressbar(
            root,
            orient="horizontal",
            mode="determinate",
            maximum=max(1, self.total_frames - 1),
        )
        self.progress.pack(fill=tk.X, padx=8, pady=(8, 2))
        self.hint_label = tk.Label(
            root,
            anchor="center",
            font=("Microsoft JhengHei UI", 12, "bold"),
            fg="#116329",
            pady=2,
        )
        self.hint_label.pack(fill=tk.X)
        self.status_label = tk.Label(
            root,
            anchor="w",
            justify="left",
            font=("Microsoft JhengHei UI", 10),
            padx=8,
            pady=6,
        )
        self.status_label.pack(fill=tk.X)
        self.status_label.configure(height=8)

        self.root.bind("<Left>", self.on_left)
        self.root.bind("<Right>", self.on_right)
        self.root.bind("<Up>", self.on_up)
        self.root.bind("<Down>", self.on_down)
        self.root.bind("<Home>", self.on_home)
        self.root.bind("<End>", self.on_end)
        self.root.bind("<Escape>", self.on_escape)
        self.root.bind("<KeyPress-space>", self.on_space_press)
        self.root.bind("<KeyRelease-space>", self.on_space_release)
        self.preview_canvas.bind("<Configure>", self.on_resize)

        self.seek_to_time(0.0)

    def on_left(self, _event: tk.Event) -> None:
        self.seek_to_time(max(0.0, self.current_time_seconds - self.step_seconds))

    def on_right(self, _event: tk.Event) -> None:
        self.seek_to_time(
            min(self.duration_seconds, self.current_time_seconds + self.step_seconds)
        )

    def on_up(self, _event: tk.Event) -> None:
        self.step_seconds = round(self.step_seconds + self.step_adjustment_seconds, 1)
        self.update_status()

    def on_down(self, _event: tk.Event) -> None:
        self.step_seconds = round(
            max(
                self.minimum_step_seconds,
                self.step_seconds - self.step_adjustment_seconds,
            ),
            1,
        )
        self.update_status()

    def on_home(self, _event: tk.Event) -> None:
        self.seek_to_time(0.0)

    def on_end(self, _event: tk.Event) -> None:
        self.seek_to_frame(self.total_frames - 1)

    def on_escape(self, _event: tk.Event) -> None:
        self.close()

    def on_space_press(self, _event: tk.Event) -> None:
        if self.space_pressed:
            return
        self.space_pressed = True
        self.save_current_frame()

    def on_space_release(self, _event: tk.Event) -> None:
        self.space_pressed = False

    def on_resize(self, _event: tk.Event) -> None:
        self.update_preview()

    def seek_to_time(self, target_time_seconds: float) -> None:
        frame_index = int(round(target_time_seconds * self.fps))
        self.seek_to_frame(frame_index)

    def seek_to_frame(self, frame_index: int) -> None:
        target_frame = min(max(0, frame_index), self.total_frames - 1)
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ok, frame = self.capture.read()
        if not ok or frame is None:
            return
        actual_frame_index = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        self.current_frame_index = max(0, actual_frame_index)
        self.current_time_seconds = self.current_frame_index / self.fps
        self.current_frame = frame
        self.update_preview()
        self.update_status()

    def update_preview(self) -> None:
        if self.current_frame is None:
            return
        width = max(1, self.preview_canvas.winfo_width())
        height = max(1, self.preview_canvas.winfo_height())
        rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        preview_width, preview_height = scaled_size(
            source_width=image.width,
            source_height=image.height,
            max_width=width,
            max_height=height,
        )
        image = image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
        self.preview_image = ImageTk.PhotoImage(image)
        x = width // 2
        y = height // 2
        if self.preview_canvas_image_id is None:
            self.preview_canvas_image_id = self.preview_canvas.create_image(
                x,
                y,
                image=self.preview_image,
                anchor="center",
            )
        else:
            self.preview_canvas.coords(self.preview_canvas_image_id, x, y)
            self.preview_canvas.itemconfigure(
                self.preview_canvas_image_id,
                image=self.preview_image,
            )

    def update_status(self) -> None:
        saved_text = "已截圖" if time.monotonic() < self.saved_message_until else ""
        progress_percent = (
            self.current_frame_index / max(1, self.total_frames - 1) * 100.0
        )
        self.progress.configure(value=self.current_frame_index)
        self.hint_label.configure(
            text=(
                f"{saved_text}：{self.last_saved_filename}"
                if saved_text and self.last_saved_filename
                else "空白鍵截圖，左右鍵巡覽，上下鍵調整步進"
            )
        )
        self.status_label.configure(
            text=(
                f"影片檔名：{self.video_path.name}\n"
                f"目前時間 / 總時長：{format_time(self.current_time_seconds)} / "
                f"{format_time(self.duration_seconds)} "
                f"({format_duration(self.duration_seconds)})\n"
                f"目前 Frame Index / Total Frames：{self.current_frame_index} / "
                f"{self.total_frames - 1}\n"
                f"目前進度：{progress_percent:.2f}%\n"
                f"目前幀率：{self.fps:.3f} FPS\n"
                f"目前 Step Seconds：{self.step_seconds:.1f}\n"
                f"已保存頁數：{self.saved_page_count}\n"
                f"最後保存檔名：{self.last_saved_filename or '-'}"
            )
        )
        if saved_text:
            self.root.after(700, self.update_status)

    def save_current_frame(self) -> None:
        if self.current_frame is None:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        image_path = self.next_output_path()
        ok = cv2.imwrite(str(image_path), self.current_frame)
        if not ok:
            messagebox.showerror("Save failed", f"Could not write {image_path}")
            return
        self.last_saved_filename = image_path.name
        self.saved_message_until = time.monotonic() + 0.7
        self.next_page_number += 1
        self.saved_page_count += 1
        self.update_status()

    def next_output_path(self) -> Path:
        while True:
            image_path = self.output_dir / f"page_{self.next_page_number:03d}.png"
            if not image_path.exists():
                return image_path
            self.next_page_number += 1

    def close(self) -> None:
        self.capture.release()
        self.root.destroy()


def scaled_size(
    source_width: int,
    source_height: int,
    max_width: int,
    max_height: int,
) -> tuple[int, int]:
    scale = min(max_width / source_width, max_height / source_height)
    return max(1, int(source_width * scale)), max(1, int(source_height * scale))


def next_page_number(output_dir: Path) -> int:
    if not output_dir.exists():
        return 1
    highest = 0
    for path in output_dir.iterdir():
        match = PAGE_PATTERN.fullmatch(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def existing_page_count(output_dir: Path) -> int:
    if not output_dir.exists():
        return 0
    return sum(1 for path in output_dir.iterdir() if PAGE_PATTERN.fullmatch(path.name))


def format_time(seconds: float) -> str:
    minutes, remainder = divmod(max(0.0, seconds), 60.0)
    return f"{int(minutes):02d}:{remainder:05.2f}"


def load_config(argus_root: Path) -> dict[str, Any]:
    config_path = argus_root / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> int:
    argus_root = Path(__file__).resolve().parent
    try:
        config = load_config(argus_root)
        picker_config = config["manual_frame_picker"]
        video_path = find_single_video(argus_root / config["input"]["directory"])
        output_dir = argus_root / picker_config["output_directory"]

        root = tk.Tk()
        ManualFramePicker(
            root=root,
            video_path=video_path,
            output_dir=output_dir,
            initial_step_seconds=float(picker_config["initial_step_seconds"]),
            minimum_step_seconds=float(picker_config["minimum_step_seconds"]),
            step_adjustment_seconds=float(picker_config["step_adjustment_seconds"]),
        )
        root.mainloop()
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        try:
            messagebox.showerror("Manual Frame Picker", str(exc))
        except tk.TclError:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
