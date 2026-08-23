#!/usr/bin/env python3
"""
每周增量下载：SoundCloud 直接下载 + Spotify 导出歌单

Spotify 歌曲通过 YouTube 搜索下载（需要浏览器 cookies）。
如果 cookies 不可用，则仅导出 Spotify 歌单为 URL 列表供手动下载。

用法:
  python3 music_weekly.py
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ARCHIVE_DIR = Path.home() / "Music" / "BIXY DJ"
STATE_FILE = ARCHIVE_DIR / ".state.json"
SPOTIFY_CACHE = Path.home() / "Music" / "Archive" / "spotify" / ".spotify_oauth_cache"
COOKIES_FILE = ARCHIVE_DIR / ".yt_cookies.txt"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"spotify_ids": {}, "soundcloud_ids": {}, "last_run": None}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_week_folder():
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")


def get_new_spotify_likes(state):
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
            known_ids[tid] = item["added_at"]
            new_tracks.append({
                "id": tid,
                "name": t["name"],
                "artists": [a["name"] for a in t["artists"]],
                "album": t["album"]["name"],
                "added_at": item["added_at"],
                "url": t["external_urls"].get("spotify", ""),
            })
        offset += limit
        if len(items) < limit:
            break

    print(f"[Spotify] {len(new_tracks)} 首新增")
    return new_tracks


def get_new_soundcloud_likes(state):
    username = os.getenv("SOUNDCLOUD_USERNAME")
    if not username:
        return []

    cmd = [
        "python3", "-m", "yt_dlp",
        "--flat-playlist", "--dump-json",
        "--ignore-errors", "--no-progress",
        f"https://soundcloud.com/{username}/likes",
    ]

    print("[SoundCloud] 扫描 Likes ...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return []

    known_ids = state.setdefault("soundcloud_ids", {})
    new_tracks = []

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
        new_tracks.append({
            "id": sid,
            "title": info.get("title", "?"),
            "uploader": info.get("uploader", "?"),
            "webpage_url": info.get("webpage_url", ""),
            "duration": info.get("duration"),
        })

    print(f"[SoundCloud] {len(new_tracks)} 首新增")
    return new_tracks


def download_soundcloud(track, folder):
    """下载 SoundCloud → MP3 320kbps。"""
    url = track.get("webpage_url", "")
    if not url:
        return False

    cmd = [
        "python3", "-m", "yt_dlp",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "320K",
        "--embed-metadata",
        "--output", f"{folder}/%(uploader)s - %(title)s.%(ext)s",
        "--no-playlist", "--no-progress", "--quiet",
        url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def download_spotify_via_youtube(track, folder):
    """YouTube 搜索 → MP3 320kbps。"""
    artists = " ".join(track.get("artists", []))
    query = f"ytsearch1:{artists} - {track['name']}"

    cmd = [
        "python3", "-m", "yt_dlp",
        "--cookies-from-browser", "edge",
        "--js-runtimes", "node",
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "320K",
        "--embed-metadata",
        "--output", f"{folder}/%(title)s.%(ext)s",
        "--no-playlist", "--no-progress", "--quiet",
        query,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def main():
    state = load_state()
    week = get_week_folder()
    folder = ARCHIVE_DIR / week
    folder.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 {week}\n{'=' * 40}")

    # ── SoundCloud (直接下载) ──
    new_sc = get_new_soundcloud_likes(state)
    sc_ok = 0
    for i, t in enumerate(new_sc):
        label = f"{t['uploader']} - {t['title']}"
        print(f"  [{i+1}/{len(new_sc)}] ☁️  {label[:60]}")
        if download_soundcloud(t, folder):
            sc_ok += 1
        else:
            print(f"         ⚠️ 失败")

    # ── Spotify ──
    new_sp = get_new_spotify_likes(state)
    sp_ok = 0
    for i, t in enumerate(new_sp):
        artists = ", ".join(t["artists"])
        label = f"{artists} - {t['name']}"
        print(f"  [{i+1}/{len(new_sp)}] 🎵 {label[:60]}")
        if download_spotify_via_youtube(t, folder):
            sp_ok += 1
        else:
            print(f"         ⚠️ 失败")

    # ── 导出 Spotify 歌单 (供手动下载) ──
    if new_sp:
        urls_file = folder / "Spotify歌单_URLs.txt"
        lines = ["# Spotify 本周新增 — 用 spotisaver.net 逐首下载", ""]
        for t in new_sp:
            artists = ", ".join(t["artists"])
            lines.append(f"{artists} - {t['name']}")
            lines.append(f"  {t['url']}")
            lines.append("")
        urls_file.write_text("\n".join(lines), encoding="utf-8")

    # ── 歌单摘要 ──
    if new_sc or new_sp:
        summary = folder / "歌单.txt"
        lines = [f"BIXY DJ — 本周新收藏 {week}", "=" * 40, ""]
        if new_sp:
            lines.append(f"[Spotify] {sp_ok}/{len(new_sp)} 下载成功")
            for t in new_sp:
                lines.append(f"  {', '.join(t['artists'])} — {t['name']}")
            lines.append("")
        if new_sc:
            lines.append(f"[SoundCloud] {sc_ok}/{len(new_sc)} 下载成功")
            for t in new_sc:
                lines.append(f"  {t['uploader']} — {t['title']}")
        summary.write_text("\n".join(lines), encoding="utf-8")

    # ── 保存状态 ──
    state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_state(state)

    total = len(new_sp) + len(new_sc)
    print(f"\n{'=' * 40}")
    print(f"📊 本周新增 {total} 首")
    print(f"   SoundCloud: {sc_ok}/{len(new_sc)} 下载成功")
    print(f"   Spotify:    {sp_ok}/{len(new_sp)} 下载成功")
    print(f"📁 {folder}")
    if new_sp and sp_ok < len(new_sp):
        print(f"💡 失败的 Spotify 歌曲见 Spotify歌单_URLs.txt")


if __name__ == "__main__":
    main()
