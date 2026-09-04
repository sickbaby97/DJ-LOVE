#!/usr/bin/env python3
"""DJ-LOVE 配置向导 —— 首次运行引导用户设置 Spotify 和 SoundCloud。"""
import os
import sys
import json
import urllib.parse
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

ENV_FILE = Path.home() / ".hermes" / ".env"
PROXY = "http://127.0.0.1:7897"


def log(msg):
    print(f"\n{'=' * 50}\n{msg}\n{'=' * 50}")


def ask(prompt, default=""):
    val = input(f"{prompt} [{default}]: ").strip()
    return val or default


def detect_proxy():
    """尝试常见代理端口。"""
    import socket
    for port in [7897, 7890, 10809, 1087, 7891]:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return f"http://127.0.0.1:{port}"
        except OSError:
            pass
    return PROXY


def check_proxy():
    log("🔍 检测网络代理")
    proxy = detect_proxy()
    if proxy != PROXY:
        print(f"   ✅ 检测到代理: {proxy}")
        return proxy
    print("   ⚠️  未检测到本地代理 (Clash/V2Ray 等)")
    if ask("需要配置自定义代理？(回车跳过)", "") == "":
        return PROXY
    return ask("代理地址", "http://127.0.0.1:7897")


def spotify_setup():
    log("🎵 配置 Spotify")
    print("1. 打开 https://developer.spotify.com/dashboard")
    print("2. 点 'Create App'")
    print("   - App name: DJ-LOVE")
    print("   - Redirect URI: http://127.0.0.1:8888 (勾选 Web API)")
    print("3. 打开 App 的 Settings，把 Client ID 和 Client Secret 复制给我\n")

    client_id = ask("Client ID").strip()
    if not client_id:
        print("❌ 未填，跳过 Spotify")
        return None, None
    client_secret = ask("Client Secret").strip()
    return client_id, client_secret


def spotify_auth(client_id, client_secret):
    """OAuth 授权，弹浏览器。"""
    log("🔐 Spotify 授权")
    if not client_id or not client_secret:
        print("跳过（未填凭证）")
        return False

    CLIENT_ID = client_id
    CLIENT_SECRET = client_secret
    REDIRECT_URI = "http://127.0.0.1:8888"
    SCOPE = "user-library-read"
    CACHE_PATH = str(Path.home() / "Music" / "BIXY DJ" / ".state.json")
    HOST, PORT = "127.0.0.1", 8888

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    }
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

    auth_code = None

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            qs = urllib.parse.urlparse(self.path).query
            p = urllib.parse.parse_qs(qs)
            if "code" in p:
                auth_code = p["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>OK! You can close this tab.</h1>")
            elif "error" in p:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Error: {p['error']}".encode())
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Waiting...")
        def log_message(self, *a):
            pass

    server = HTTPServer((HOST, PORT), Handler)
    print(f"🔗 浏览器已打开授权页面...")
    webbrowser.open(auth_url)
    print("⏳ 等待你点「同意」...")
    server.handle_request()
    server.server_close()

    if not auth_code:
        print("❌ 未获取到授权码")
        return False

    # 换 token
    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request("https://accounts.spotify.com/api/token",
                                 data=token_data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = urllib.request.urlopen(req)
        token = json.loads(resp.read())
    except Exception as e:
        print(f"❌ Token 交换失败: {e}")
        return False

    # 保存 token 到 cache
    cache_path = str(Path.home() / "Music" / "BIXY DJ" / "Archive" / "spotify" / ".spotify_oauth_cache")
    cache_path = str(Path(cache_path).expanduser())
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    import time
    token["expires_at"] = int(time.time()) + token.get("expires_in", 3600)
    Path(cache_path).write_text(json.dumps(token))
    print("✅ Spotify 授权完成！")
    return True


def soundcloud_setup():
    log("☁️  配置 SoundCloud")
    print("你的 SoundCloud 个人主页用户名，例如:")
    print("   https://soundcloud.com/sickbabewolf → 用户名是 sickbabewolf\n")
    username = ask("SoundCloud 用户名").strip()
    return username


def write_env(proxy, spotify_id, spotify_secret, sc_username):
    """写入 .env 文件。"""
    lines = []
    if ENV_FILE.exists():
        existing = ENV_FILE.read_text()
        for key in ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET",
                    "SPOTIFY_REDIRECT_URI", "SOUNDCLOUD_USERNAME", "YTDLP_PROXY"]:
            for line in existing.splitlines():
                if line.startswith(key + "="):
                    existing = existing.replace(line, "")
                    break

    if proxy:
        lines.append(f"YTDLP_PROXY={proxy}")
    if spotify_id:
        lines.append(f"SPOTIFY_CLIENT_ID={spotify_id}")
        lines.append("SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888")
    if spotify_secret:
        lines.append(f"SPOTIFY_CLIENT_SECRET={spotify_secret}")
    if sc_username:
        lines.append(f"SOUNDCLOUD_USERNAME={sc_username}")

    # 保留其他原行
    others = []
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.strip() and not any(line.startswith(k + "=") for k in
                                       ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET",
                                        "SPOTIFY_REDIRECT_URI", "SOUNDCLOUD_USERNAME",
                                        "YTDLP_PROXY"]):
                others.append(line)

    ENV_FILE.write_text("\n".join(others + lines) + "\n")
    ENV_FILE.chmod(0o600)
    print(f"✅ 配置已保存到 {ENV_FILE}")


def main():
    log("🎧 DJ-LOVE 首次配置向导")
    print("这个脚本会引导你完成首次配置。\n")

    proxy = check_proxy()
    sc_username = soundcloud_setup()

    spotify_id = ""
    spotify_secret = ""
    if ask("\n要配置 Spotify 吗？(y/N)", "y").lower().startswith("y"):
        spotify_id, spotify_secret = spotify_setup()
        if spotify_id and spotify_secret:
            spotify_auth(spotify_id, spotify_secret)

    write_env(proxy, spotify_id, spotify_secret, sc_username)

    log("🎉 配置完成！")
    print("接下来你可以:")
    print("  • 双击 DJ LOVE.app")
    print("  • 终端运行: djlove")
    print("  • 终端运行: djlove --today")


if __name__ == "__main__":
    main()
