#!/usr/bin/env python3
"""
DJ-LOVE 音乐下载：Spotify + SoundCloud 收藏 → MP3 320kbps

Spotify 歌曲通过 YouTube 搜索下载（需要浏览器 cookies）。

用法:
  python3 music_weekly.py            # 下载所有未下载的新收藏
  python3 music_weekly.py --today    # 只下载今天点心的歌
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE_DIR = Path.home() / "Music" / "BIXY DJ"
STATE_FILE = ARCHIVE_DIR / ".state.json"
SPOTIFY_CACHE = Path.home() / "Music" / "Archive" / "spotify" / ".spotify_oauth_cache"
COOKIES_FILE = ARCHIVE_DIR / ".yt_cookies.txt"
# 代理（国内访问 YouTube/SoundCloud 必需，默认 Clash）
PROXY = os.getenv("YTDLP_PROXY", "http://127.0.0.1:7897")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"spotify_ids": {}, "soundcloud_ids": {}, "last_run": None}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_folder():
    """返回当天日期文件夹名: 2026-08-24"""
    return datetime.now(timezone.utc).date().strftime("%Y-%m-%d")


def get_new_spotify_likes(state, today_only=False):
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return []

    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888"),
        scope="user-library-read",
        cache_path=str(SPOTIFY_CACHE),
    )
    token = auth.get_cached_token()
    if not token:
        return []

    sp = spotipy.Spotify(auth_manager=auth, requests_timeout=30)
    known_ids = state.setdefault("spotify_ids", {})
    new_tracks = []
    offset, limit = 0, 50

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("[Spotify] 扫描 Liked Songs ...")
    while True:
        results = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = results.get("items", [])
        if not items:
            break
        for item in items:
            t = item["track"]
            if t is None:
                continue
            tid = t["id"]
            if tid in known_ids:
                continue
            added_at = item["added_at"]
            # 注意：这里不标记 known_ids，下载成功后才标记
            # --today 模式：只保留今天收藏的
            if today_only and not added_at.startswith(today_str):
                continue
            new_tracks.append({
                "id": tid,
                "name": t["name"],
                "artists": [a["name"] for a in t["artists"]],
                "album": t["album"]["name"],
                "added_at": added_at,
                "url": t["external_urls"].get("spotify", ""),
            })
        offset += limit
        if len(items) < limit:
            break

    print(f"[Spotify] {len(new_tracks)} 首新增")
    return new_tracks


def get_soundcloud_playlists(state):
    """获取 SoundCloud 用户的所有公开歌单（playlist/set）。"""
    username = os.getenv("SOUNDCLOUD_USERNAME")
    if not username:
        return []

    cmd = [
        "python3", "-m", "yt_dlp",
        "--flat-playlist", "--dump-json",
        "--ignore-errors", "--no-progress",
        f"https://soundcloud.com/{username}/sets",
    ]

    print("[SoundCloud] 扫描歌单 ...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return []

    known_ids = state.setdefault("soundcloud_playlist_ids", {})
    playlists = []

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            info = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = str(info.get("id", ""))
        if not sid or sid in known_ids:
            continue
        known_ids[sid] = info.get("upload_date", "")
        playlists.append({
            "id": sid,
            "title": info.get("title", "?"),
            "uploader": info.get("uploader", "?"),
            "webpage_url": info.get("webpage_url", ""),
        })

    print(f"[SoundCloud] 发现 {len(playlists)} 个新歌单")
    return playlists


def download_soundcloud_playlist(track, folder):
    """下载 SoundCloud 歌单里的所有曲目。"""
    url = track.get("webpage_url", "")
    if not url:
        return False

    cmd = [
        "python3", "-m", "yt_dlp",
        "--proxy", PROXY,
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "320K",
        "--embed-metadata",
        "--output", f"{folder}/%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s",
        "--no-progress", "--quiet",
        url,
    ]
    return _run_download(cmd)


def _run_download(cmd, retries=2):
    """运行下载命令，失败自动重试（应对 429 限流/网络波动）。"""
    for attempt in range(retries):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                return True
            if attempt < retries - 1:
                print("         🔄 重试...")
                time.sleep(5)
            else:
                err = (r.stderr or r.stdout or "").strip()
                print(f"         ❌ {err[-400:]}")
                return False
        except subprocess.TimeoutExpired:
            if attempt < retries - 1:
                print("         ⏱️ 超时，重试...")
                time.sleep(5)
            else:
                print("         ⏱️ 超时(180s)")
                return False
    return False


def download_soundcloud(track, folder):
    """下载 SoundCloud → MP3 320kbps。"""
    url = track.get("webpage_url", "")
    if not url:
        return False

    cmd = [
        "python3", "-m", "yt_dlp",
        "--proxy", PROXY,
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "320K",
        "--embed-metadata",
        "--output", f"{folder}/%(uploader)s - %(title)s.%(ext)s",
        "--no-playlist", "--no-progress", "--quiet",
        url,
    ]
    return _run_download(cmd)


def download_spotify_via_youtube(track, folder):
    """YouTube 搜索 → MP3 320kbps。"""
    artists = " ".join(track.get("artists", []))
    query = f"ytsearch1:{artists} - {track['name']}"

    cmd = [
        "python3", "-m", "yt_dlp",
        "--proxy", PROXY,
        "--cookies-from-browser", "edge",
        "--js-runtimes", "node",
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "320K",
        "--embed-metadata",
        "--retries", "8",
        "--sleep-requests", "1",
        "--output", f"{folder}/%(title)s.%(ext)s",
        "--no-playlist", "--no-progress", "--quiet",
        query,
    ]
    return _run_download(cmd)


def main():
    today_only = "--today" in sys.argv

    state = load_state()
    folder = ARCHIVE_DIR / get_folder()
    folder.mkdir(parents=True, exist_ok=True)

    mode = "📅 仅今日收藏" if today_only else "🆕 所有新收藏"
    print(f"\n📁 {folder.name}  ·  {mode}\n{'=' * 40}")

    # ── SoundCloud (下载歌单) ──
    new_sc = get_soundcloud_playlists(state)
    sc_ok = 0
    for i, t in enumerate(new_sc):
        label = f"{t['uploader']} - {t['title']}"
        print(f"  [{i+1}/{len(new_sc)}] ☁️  {label[:60]}")
        if download_soundcloud_playlist(t, folder):
            sc_ok += 1
            state["soundcloud_playlist_ids"][t["id"]] = t.get("upload_date", "")
        else:
            print(f"         ⚠️ 失败")

    # ── Spotify ──
    new_sp = get_new_spotify_likes(state, today_only=today_only)
    sp_ok = 0
    for i, t in enumerate(new_sp):
        artists = ", ".join(t["artists"])
        label = f"{artists} - {t['name']}"
        print(f"  [{i+1}/{len(new_sp)}] 🎵 {label[:60]}")
        if download_spotify_via_youtube(t, folder):
            sp_ok += 1
            state["spotify_ids"][t["id"]] = t["added_at"]
        else:
            print(f"         ⚠️ 失败")

    # ── 导出 Spotify 歌单 (供手动下载) ──
    if new_sp:
        urls_file = folder / "Spotify歌单_URLs.txt"
        lines = ["# Spotify 新增 — 用 spotisaver.net 逐首下载", ""]
        for t in new_sp:
            artists = ", ".join(t["artists"])
            lines.append(f"{artists} - {t['name']}")
            lines.append(f"  {t['url']}")
            lines.append("")
        urls_file.write_text("\n".join(lines), encoding="utf-8")

    # ── 歌单摘要 ──
    if new_sc or new_sp:
        summary = folder / "歌单.txt"
        lines = [f"BIXY DJ — 新收藏 {folder.name}", "=" * 40, ""]
        if new_sp:
            lines.append(f"[Spotify] {sp_ok}/{len(new_sp)} 下载成功")
            for t in new_sp:
                lines.append(f"  {', '.join(t['artists'])} — {t['name']}")
            lines.append("")
        if new_sc:
            lines.append(f"[SoundCloud] {sc_ok}/{len(new_sc)} 个歌单下载成功")
            for t in new_sc:
                lines.append(f"  {t['uploader']} — {t['title']}")
        summary.write_text("\n".join(lines), encoding="utf-8")

    # ── 保存状态 ──
    state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_state(state)

    total = len(new_sp) + len(new_sc)
    print(f"\n{'=' * 40}")
    print(f"📊 新增 {total} 项")
    print(f"   SoundCloud: {sc_ok}/{len(new_sc)} 个歌单下载成功")
    print(f"   Spotify:    {sp_ok}/{len(new_sp)} 首下载成功")
    print(f"📁 {folder}")
    if new_sc or new_sp:
        print(f"📁 歌单保存在: {folder}")
    if new_sp and sp_ok < len(new_sp):
        print(f"💡 失败的 Spotify 歌曲见 Spotify歌单_URLs.txt")


if __name__ == "__main__":
    main()
