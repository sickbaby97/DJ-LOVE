<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python" />
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" />
</p>

<h1 align="center">🎧 DJ-LOVE</h1>
<p align="center">
  <b>自动定时下载 Spotify & SoundCloud 收藏到本地 · MP3 320kbps · 桌面程序 + 命令行</b><br>
  <sub>Automated download of your Spotify & SoundCloud likes to local storage — 320kbps MP3, with a native macOS desktop app.</sub>
</p>

<p align="center">
  <img src="desktop/cover.png" width="280" alt="DJ LOVE cover" />
</p>

---

## 🖥️ 桌面程序 / Desktop App

双击即用的 macOS 应用，界面直观，点按钮就下载。

A native macOS app — double-click to launch, click a button to download.

| 按钮 / Button | 作用 / Action |
|---------------|---------------|
| 🆕 **立即下载新收藏** | 下载所有未下载的（自动去重）/ Download all new likes |
| 📅 **下载今日喜欢** | 只下载今天点心的歌 / Download only today's likes |
| 📋 **实时日志** | 滚动显示下载进度 / Live download log |

> 打包成 `DJ LOVE.app`，带自绘封面 + `.icns` 图标。双击桌面图标即用。
> Packaged as `DJ LOVE.app` with a custom cover and `.icns` icon.

---

## 💡 它做什么 / What It Does

你在 Spotify / SoundCloud 点喜欢的歌，**它每周自动下载到你电脑里**。不需要每次手动操作，配好一次就一直在后台跑。

You like songs on Spotify or SoundCloud → **DJ-LOVE automatically downloads them to your local machine every week.** Set it up once, it runs forever in the background.

```
你的操作                      DJ-LOVE 自动完成
─────────                    ─────────────────
🎧 周一～周日                   （什么都不用管）
  在 Spotify 点心 ❤️
  在 SoundCloud 点心 ❤️
                              ⏰ 周一凌晨 3:00
                              ↓ 扫描本周新收藏
                              ↓ 下载 MP3 320kbps
                              ↓ 按日期归档
                              ↓ 生成歌单
                              
📁 电脑里就有了                  ✅ 完成
  ~/Music/DJ-LOVE/
  └── 2026-08-10/
      ├── xxx - yyy.mp3
      ├── ...
      └── playlist.txt
```

---

## ✨ 特性 / Features

| 特性 / Feature | 说明 / Description |
|---------------|-------------------|
| 🖥️ **桌面程序** | macOS `.app`，双击即用，点按钮下载 |
| ⏰ **定时自动** | launchd 定时 + 自动唤醒，错过开机补跑 |
| 🎵 **双平台** | Spotify 收藏 + SoundCloud 喜欢 |
| 📦 **MP3 320kbps** | ffmpeg 最高质量转码 |
| 🆕 **手动触发** | `djlove` / `djlove --today` 随时下载 |
| 📅 **按日期归档** | 每天一个文件夹，日期命名 |
| 🔁 **智能去重** | `.state.json` 追踪，绝不下重 |
| 🏷️ **ID3 标签** | 封面、艺人、专辑信息自动写入 |
| 📋 **歌单导出** | 每期自动生成 TXT 歌单 |
| 🪶 **轻量** | 纯 Python，无需数据库 |

---

## 🚀 5 分钟部署 / 5-Minute Setup

### 1. 安装 / Install

```bash
# Python 依赖
pip install spotipy yt-dlp

# ffmpeg（MP3 转码必需 / required for MP3 encoding）
# macOS:
curl -fSL "https://evermeet.cx/ffmpeg/getrelease/zip" -o /tmp/ffmpeg.zip
unzip /tmp/ffmpeg.zip -d ~/.local/bin/
chmod +x ~/.local/bin/ffmpeg
export PATH="$HOME/.local/bin:$PATH"
```

### 2. 首次配置 / First-time Setup

运行向导，按提示输入 Spotify 凭证和 SoundCloud 用户名：

```bash
djlove-setup
```

向导会：
- 自动检测本地代理（Clash/V2Ray）
- 引导你创建 Spotify App 并填入 Client ID / Secret
- 打开浏览器完成 Spotify OAuth 授权
- 写入 `~/.hermes/.env`

#### YouTube 下载 / YouTube Download

Spotify 歌曲通过 YouTube 搜索下载。需要浏览器 cookies：

- 安装 **Edge** 或 **Chrome**
- 浏览器登录 **YouTube**
- 保持登录状态即可，脚本自动读取 cookies

> Spotify tracks are downloaded by searching YouTube. Browser cookies from Edge/Chrome are used automatically.

### 3. 运行 / Run

```bash
# 手动下载所有新收藏
python3 music_weekly.py

# 只下载今天点心的歌
python3 music_weekly.py --today

# 或使用快捷命令
djlove            # 下载所有新收藏
djlove --today    # 只下载今天喜欢的
```

### 4. 定时 / Schedule

```bash
# macOS 用 launchd（定时 + 错过补跑 + 自动唤醒）
cp com.bixy.dj-love.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.bixy.dj-love.plist

# Linux 用 cron（每周一凌晨 3:00 / Every Monday 3am）
echo "0 3 * * 1 /path/to/music_archive_weekly.sh" | crontab -
```

---

## 🧠 工作原理 / How It Works

```
┌─────────────────────────────────────────────────────┐
│  每周一 3:00 AM / Every Monday 3am                   │
├─────────────────────────────────────────────────────┤
│  Spotify API        SoundCloud API                   │
│       ↓                    ↓                         │
│  扫描 Liked Songs    扫描 Likes                       │
│       ↓                    ↓                         │
│  过滤已下载 ←── .state.json ──→ 过滤已下载            │
│       ↓                    ↓                         │
│  YouTube 搜索          yt-dlp 直连                    │
│       ↓                    ↓                         │
│  ffmpeg → MP3 320kbps    ffmpeg → MP3 320kbps       │
│       ↓                    ↓                         │
│  ~/Music/DJ-LOVE/2026-08-10/                        │
└─────────────────────────────────────────────────────┘
```

| 平台 | 下载方式 | 格式 | 依赖 |
|------|---------|------|------|
| **Spotify** | Spotify API 获取元数据 → YouTube 搜索 → yt-dlp 下载 | MP3 320kbps | Edge/Chrome cookies |
| **SoundCloud** | yt-dlp 直连下载 | MP3 320kbps | 无需额外配置 |

---

## 📂 文件说明

```
DJ-LOVE/
├── music_weekly.py           # 主程序 / Main script
├── spotify_auth.py           # Spotify 一次性授权 / One-time OAuth
├── music_archive_weekly.sh   # launchd/cron 包装脚本
├── djlove                    # 命令行快捷方式 / CLI shortcut
├── com.bixy.dj-love.plist    # macOS launchd 配置
├── desktop/                  # 桌面程序 / Desktop app
│   ├── djlove_app.py         # Tkinter GUI
│   ├── make_cover.py         # 封面生成 / Cover generator
│   ├── cover.png             # 程序封面
│   ├── Info.plist            # macOS app 配置
│   └── launcher.sh           # .app 启动器
├── .hermes.md                # AI agent 项目规则
├── .gitignore
└── README.md
```

---

## ❓ FAQ

**Q: 为什么 Spotify 需要浏览器？**
A: YouTube 反爬要求登录凭证，脚本通过读取 Edge/Chrome 的 cookies 验证身份。

**Q: SoundCloud 为什么不需要？**
A: SoundCloud 对 yt-dlp 的下载请求不做验证。

**Q: 会重复下载同一首歌吗？**
A: 不会。`.state.json` 记录所有已下载的 track ID。

**Q: 支持 Apple Music 吗？**
A: 暂不支持。欢迎 PR。

---

## 🛠 技术栈 / Stack

- [spotipy](https://github.com/spotipy-dev/spotipy) — Spotify Web API
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 音频下载引擎
- [ffmpeg](https://ffmpeg.org) — 音频转码
- [Tkinter](https://docs.python.org/3/library/tkinter.html) — 桌面 GUI
- [Pillow](https://python-pillow.org) — 封面生成与图像处理
- Python 3.11+

---

## 📄 License

MIT © 2024 — 仅供个人使用，请遵守各平台服务条款。

---

<!-- 搜索关键词 / Search Keywords -->
<!-- Spotify downloader, SoundCloud downloader, MP3 downloader, music archiver, -->
<!-- 自动下载, 音乐归档, DJ tools, 定时下载, 收藏下载, liked songs downloader, -->
<!-- automated music download, weekly music backup, cron music downloader -->
