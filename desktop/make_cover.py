#!/usr/bin/env python3
"""生成 DJ LOVE 程序封面 + 图标。"""
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1024


def lerp(a, b, t):
    return a + (b - a) * t


def make_cover(path, size=SIZE):
    """生成 DJ LOVE 封面。"""
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── 渐变背景：深紫 → 黑 ──
    top = (30, 10, 60)      # 深紫
    bottom = (0, 0, 0)      # 黑
    for y in range(size):
        t = y / size
        r = int(lerp(top[0], bottom[0], t))
        g = int(lerp(top[1], bottom[1], t))
        b = int(lerp(top[2], bottom[2], t))
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # ── 径向光晕（中心粉紫） ──
    glow = Image.new("RGB", (size, size), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    cx, cy = size // 2, size // 2
    for r in range(size // 2, 0, -1):
        t = r / (size // 2)
        # 粉紫光晕
        col = (int(80 * (1 - t)), int(20 * (1 - t)), int(120 * (1 - t)))
        gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img = Image.blend(img, glow, 0.6)
    draw = ImageDraw.Draw(img)

    # ── 黑胶唱片（左上，半透明装饰） ──
    vinyl_r = 150
    vx, vy = size // 5, size // 5
    vinyl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vinyl)
    vdraw.ellipse([vx - vinyl_r, vy - vinyl_r, vx + vinyl_r, vy + vinyl_r],
                  fill=(20, 20, 30, 255))
    # 唱片纹路
    for i in range(1, 8):
        rr = int(vinyl_r * (1 - i * 0.11))
        vdraw.ellipse([vx - rr, vy - rr, vx + rr, vy + rr],
                      outline=(50, 50, 70, 255), width=2)
    # 中心标签
    vdraw.ellipse([vx - 45, vy - 45, vx + 45, vy + 45], fill=(255, 60, 120, 255))
    vdraw.ellipse([vx - 12, vy - 12, vx + 12, vy + 12], fill=(0, 0, 0, 255))
    img = Image.alpha_composite(img.convert("RGBA"), vinyl).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── 均衡器条（底部） ──
    eq_y = int(size * 0.78)
    eq_bottom = int(size * 0.92)
    bar_w = 14
    gap = 10
    total_bars = 40
    start_x = (size - total_bars * (bar_w + gap)) // 2
    colors = [(255, 60, 140), (90, 220, 255), (255, 120, 60), (150, 90, 255)]
    for i in range(total_bars):
        # 随机高度（用伪随机固定模式）
        h = int((eq_bottom - eq_y) * (0.3 + 0.7 * abs(math.sin(i * 1.7 + 3))))
        x0 = start_x + i * (bar_w + gap)
        col = colors[i % len(colors)]
        draw.rounded_rectangle(
            [x0, eq_bottom - h, x0 + bar_w, eq_bottom],
            radius=bar_w // 2, fill=col)

    # ── 声波圆环（中心装饰） ──
    for ring in range(5):
        rr = 260 + ring * 22
        alpha = int(90 - ring * 15)
        col = (120, 90, 255) if ring % 2 == 0 else (255, 60, 140)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                     outline=col, width=3)

    # ── 主文字 "DJ LOVE" ──
    # 尝试加载粗体字体
    font_paths = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/ArialHB.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 170)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    text = "DJ LOVE"

    # 发光效果：多层绘制
    def draw_text_centered(d, text, font, cy_, fill, glow=0, glow_color=None):
        bbox = d.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (size - w) // 2 - bbox[0]
        y = cy_ - h // 2 - bbox[1]
        if glow > 0 and glow_color:
            for g in range(glow, 0, -4):
                d.text((x, y), text, font=font,
                       fill=glow_color, stroke_width=g)
        d.text((x, y), text, font=font, fill=fill, stroke_width=2,
               stroke_fill=(0, 0, 0))
        return x, y

    # 粉色 + 青色霓虹发光文字
    text_cy = int(size * 0.44)
    # 青紫光晕
    draw_text_centered(draw, text, font, text_cy, (255, 255, 255),
                       glow=40, glow_color=(80, 40, 160))
    draw_text_centered(draw, text, font, text_cy, (255, 80, 160),
                       glow=24, glow_color=(255, 40, 120))
    draw_text_centered(draw, text, font, text_cy, (255, 220, 240),
                       glow=0)

    img.save(path, quality=95)
    print(f"✅ 封面已生成: {path} ({size}x{size})")


def make_icon(cover_path, icon_path):
    """从封面生成 macOS .icns 图标。"""
    import subprocess
    img = Image.open(cover_path)
    # 生成多尺寸 PNG
    iconset = "/tmp/DJLOVE.iconset"
    subprocess.run(["rm", "-rf", iconset])
    subprocess.run(["mkdir", "-p", iconset])
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        im = img.resize((s, s), Image.LANCZOS)
        im.save(f"{iconset}/icon_{s}x{s}.png")
        if s <= 512:
            im2 = img.resize((s * 2, s * 2), Image.LANCZOS)
            im2.save(f"{iconset}/icon_{s}x{s}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icon_path],
                   check=True)
    subprocess.run(["rm", "-rf", iconset])
    print(f"✅ 图标已生成: {icon_path}")


if __name__ == "__main__":
    import os
    out_dir = os.path.expanduser("~/.djlove")
    cover_path = os.path.join(out_dir, "cover.png")
    icon_path = os.path.join(out_dir, "DJLOVE.icns")
    make_cover(cover_path)
    make_icon(cover_path, icon_path)
