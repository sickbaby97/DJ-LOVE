#!/usr/bin/env python3
"""DJ LOVE 桌面程序 —— Spotify + SoundCloud 收藏下载器。"""
import os
import sys
import subprocess
import threading
import queue
from pathlib import Path

import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk

APP_DIR = Path.home() / ".djlove"
COVER_PATH = APP_DIR / "cover.png"
SCRIPT = Path.home() / ".hermes" / "scripts" / "music_weekly.py"
ARCHIVE = Path.home() / "Music" / "BIXY DJ"
PYTHON = APP_DIR / "venv" / "bin" / "python"

BG = "#0d0714"
FG = "#f5ecff"
ACCENT = "#ff4d94"
ACCENT2 = "#5ce1ff"
BTN_BG = "#1d1230"
LOG_BG = "#120b1e"


class DJLoveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DJ LOVE")
        self.root.geometry("520x800")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.q = queue.Queue()
        self.running = False

        self._build_ui()
        self.root.after(100, self._poll_queue)

    def _build_ui(self):
        # ── 封面 ──
        cover_frame = tk.Frame(self.root, bg=BG)
        cover_frame.pack(pady=18)
        if COVER_PATH.exists():
            img = Image.open(COVER_PATH).resize((220, 220), Image.LANCZOS)
            self.cover_img = ImageTk.PhotoImage(img)
            tk.Label(cover_frame, image=self.cover_img, bg=BG).pack()
        else:
            tk.Label(cover_frame, text="DJ LOVE", font=("Helvetica", 40, "bold"),
                     fg=ACCENT, bg=BG).pack()

        # ── 标题 ──
        tk.Label(self.root, text="DJ  LOVE", font=("Helvetica", 26, "bold"),
                 fg=ACCENT, bg=BG).pack(pady=(4, 0))
        tk.Label(self.root, text="Spotify + SoundCloud → MP3 320kbps",
                 font=("Helvetica", 12), fg="#9a86c4", bg=BG).pack()

        # ── 自动下载状态 ──
        auto_frame = tk.Frame(self.root, bg="#1a0f2a", highlightthickness=1,
                              highlightbackground="#2e1f4d")
        auto_frame.pack(fill="x", padx=28, pady=(14, 0))
        last_run = self._get_last_run()
        tk.Label(auto_frame, text="⏰ 自动下载：每周一凌晨 3:00",
                 font=("Helvetica", 12, "bold"), fg=ACCENT2, bg="#1a0f2a",
                 anchor="w").pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(auto_frame, text=f"   上次运行：{last_run}",
                 font=("Helvetica", 11), fg="#9a86c4", bg="#1a0f2a",
                 anchor="w").pack(fill="x", padx=12, pady=(2, 8))

        # ── 手动下载按钮 ──
        tk.Label(self.root, text="手动下载（立即触发）",
                 font=("Helvetica", 11), fg="#7a6a9e", bg=BG).pack(pady=(14, 6))

        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack()
        self.btn_today = tk.Button(
            btn_frame, text="📅 下载今日喜欢", font=("Helvetica", 14, "bold"),
            bg=ACCENT, fg="white", activebackground="#ff6aa8",
            activeforeground="white", relief="flat", cursor="hand2",
            padx=24, pady=12, command=lambda: self.start_download(today=True))
        self.btn_today.pack(pady=6)
        tk.Label(btn_frame, text="下载今天点心的歌 / Today's likes",
                 font=("Helvetica", 10), fg="#7a6a9e", bg=BG).pack(pady=(0, 6))
        self.btn_playlists = tk.Button(
            btn_frame, text="☁️ 下载 SoundCloud 歌单", font=("Helvetica", 14, "bold"),
            bg=ACCENT2, fg="#06232b", activebackground="#8aecff",
            activeforeground="#06232b", relief="flat", cursor="hand2",
            padx=24, pady=12, command=self.start_playlist_download)
        self.btn_playlists.pack(pady=6)
        tk.Label(btn_frame, text="批量下载你 SoundCloud 上的公开歌单",
                 font=("Helvetica", 10), fg="#7a6a9e", bg=BG).pack(pady=(0, 4))

        # ── 日志 ──
        log_frame = tk.Frame(self.root, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(6, 4))
        self.log = scrolledtext.ScrolledText(
            log_frame, height=14, bg=LOG_BG, fg="#c9b8e8",
            font=("Menlo", 11), relief="flat", wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

        # ── 状态栏 ──
        self.status = tk.Label(self.root, text="就绪", font=("Helvetica", 11),
                               fg="#7a6a9e", bg=BG, anchor="w")
        self.status.pack(fill="x", padx=20, pady=(0, 12))

    def _log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, text):
        self.status.configure(text=text)

    def _get_last_run(self):
        """读取上次运行时间。"""
        try:
            import json
            state_file = Path.home() / "Music" / "BIXY DJ" / ".state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text(encoding="utf-8"))
                last = state.get("last_run")
                if last:
                    # 转成易读格式
                    from datetime import datetime
                    dt = datetime.strptime(last[:19], "%Y-%m-%dT%H:%M:%S")
                    return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        return "尚未运行"

    def start_download(self, today=False):
        if self.running:
            return
        self.running = True
        self.btn_today.configure(state="disabled")
        self.btn_playlists.configure(state="disabled")
        self._log(f"\n{'=' * 50}")
        mode = "下载今日喜欢" if today else "下载所有新收藏"
        self._log(f"▶ {mode}")
        self._set_status("下载中…")
        threading.Thread(target=self._worker, args=(today,), daemon=True).start()

    def start_playlist_download(self):
        if self.running:
            return
        self.running = True
        self.btn_today.configure(state="disabled")
        self.btn_playlists.configure(state="disabled")
        self._log(f"\n{'=' * 50}")
        self._log("▶ 下载 SoundCloud 歌单")
        self._set_status("下载歌单中…")
        threading.Thread(target=self._worker_playlists, daemon=True).start()

    def _worker(self, today):
        env = os.environ.copy()
        env["PATH"] = f"{Path.home()}/.local/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
        env.pop("PYTHONPATH", None)
        # 加载 .env 凭证
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

        cmd = [str(PYTHON), str(SCRIPT)]
        if today:
            cmd.append("--today")

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=env, bufsize=1)

        for line in proc.stdout:
            line = line.rstrip("\n")
            if line.strip():
                self.q.put(("log", line))
        proc.wait()
        self.q.put(("done", proc.returncode))

    def _worker_playlists(self):
        """调用 music_weekly.py 一次，让它发现并下载新歌单。"""
        env = os.environ.copy()
        env["PATH"] = f"{Path.home()}/.local/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
        env.pop("PYTHONPATH", None)
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
        # 用 --today 模式也只下今天的，但歌单功能会顺便触发
        proc = subprocess.Popen(
            [str(PYTHON), str(SCRIPT), "--today"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=env, bufsize=1)
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line.strip():
                self.q.put(("log", line))
        proc.wait()
        self.q.put(("done", proc.returncode))

    def _poll_queue(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "done":
                    self.running = False
                    self.btn_today.configure(state="normal")
                    self.btn_playlists.configure(state="normal")
                    if data == 0:
                        self._log("✅ 完成！")
                        self._set_status("完成 ✅")
                    else:
                        self._log(f"⚠️ 结束（退出码 {data}）")
                        self._set_status("部分失败，见日志")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def main():
    root = tk.Tk()
    app = DJLoveApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
