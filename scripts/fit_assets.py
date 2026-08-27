#!/usr/bin/env python3
"""源图 → 微信表情合规素材切图流水线（仅 PIL）。

    # 一次出全套：8~9 张主图 + 封面 + 图标（图标默认取第 1 张的头部）
    fit_assets.py raw/ out/ --cover raw/03.png --icon raw/01.png

    # 宣传图单独出（不透明、白底压平）
    fit_assets.py --banner raw/banner-src.png out/
    fit_assets.py --reward-guide raw/g.png --reward-thanks raw/t.png out/

默认对无 alpha 且四角近白的源图自动抠白底；抠不干净时改用 `museav remove-bg <file>`
（ISNet 模型，边缘带抗锯氏，比阈值抠白稳）。
"""
import argparse
import os
import sys
from PIL import Image

PAD = 0.94          # 主体占画面比例，留一点边避免贴边直角
WHITE_CUT = 238     # 抠白底阈值


def dewhite(im):
    """四角近白且无有效 alpha → 按阈值抠成透明，边缘做一档羽化。"""
    im = im.convert("RGBA")
    if min(im.getchannel("A").tobytes()) < 250:
        return im
    w, h = im.size
    k = max(2, min(w, h) // 20)
    corners = [im.crop(c).convert("RGB").tobytes() for c in ((0, 0, k, k), (w - k, 0, w, k),
                                                             (0, h - k, k, h), (w - k, h - k, w, h))]
    if not all(min(c[i:i + 3]) >= 230 for c in corners for i in range(0, len(c), 3)):
        return im
    px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            m = min(r, g, b)
            px[x, y] = (r, g, b, 0) if m >= WHITE_CUT else (r, g, b, min(255, (WHITE_CUT - m) * 12))
    return im


def trim(im):
    box = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    return im.crop(box) if box else im


def fit_square(im, side, pad=PAD):
    """等比缩放居中贴到透明方形画布。"""
    im = trim(dewhite(im))
    limit = int(side * pad)
    im.thumbnail((limit, limit), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return canvas


def fit_head(im, side):
    """取主体上部正方形当头像图标（50×50 放不下全身）。
    pad 留到 0.88：图标铺满四角会被判成「正方形边框 / 生硬直角」。"""
    im = trim(dewhite(im))
    w, h = im.size
    s = min(w, int(h * 0.62)) if h > w else w
    left = max(0, (w - s) // 2)
    return fit_square(im.crop((left, 0, left + s, min(h, s))), side, pad=0.88)


def cover_crop(im, size):
    """宣传图：覆盖裁切 + 白底压平（横幅与赞赏图不得透明）。"""
    im = im.convert("RGBA")
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left, top = (im.width - tw) // 2, (im.height - th) // 2
    im = im.crop((left, top, left + tw, top + th))
    flat = Image.new("RGB", size, (255, 255, 255))
    flat.paste(im, (0, 0), im)
    return flat


def save(im, path, max_kb, jpeg=False):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if jpeg:
        for q in (92, 86, 78, 70, 60):
            im.save(path, "JPEG", quality=q, optimize=True, progressive=True)
            if os.path.getsize(path) / 1024 <= max_kb:
                break
    else:
        im.save(path, "PNG", optimize=True)
        for colors in (256, 192, 128):
            if os.path.getsize(path) / 1024 <= max_kb:
                break
            im.convert("RGBA").quantize(colors=colors, method=Image.FASTOCTREE).save(path, "PNG", optimize=True)
    print(f"  → {path}  {os.path.getsize(path)/1024:.0f}KB")


def naming(copy_path):
    """有文案就用中文命名（形象名 + 含义词），产物自解释，不用回头对编号。
    没文案则退回英文命名，方便单独当工具用。"""
    if not copy_path or not os.path.exists(copy_path):
        return None
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_assets import parse_copy
    c = parse_copy(copy_path)
    ip = (c.get("ip_name") or "形象").strip()
    album = (c.get("album_name") or ip).strip()
    return {"ip": ip, "album": album, "meanings": c.get("meanings", [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help="源图目录（批量切表情图）")
    ap.add_argument("out")
    ap.add_argument("--copy", help="album.yml —— 给出则用「形象名+含义词」中文命名产物")
    ap.add_argument("--cover", help="封面源图（正面半身/全身，不要只用头部）")
    ap.add_argument("--icon", help="图标源图（自动取头部正面）")
    ap.add_argument("--banner", help="详情页横幅源图 → 750×400 JPG")
    ap.add_argument("--reward-guide", help="赞赏引导图源图 → 750×560 PNG")
    ap.add_argument("--reward-thanks", help="赞赏致谢图源图 → 750×750 PNG")
    args = ap.parse_args()
    out = args.out
    n = naming(args.copy)
    sub = "表情图" if n else "main_240"

    if args.src:
        # 横幅底图与 IP 原照混在同一个 raw/ 里，不能被当成表情图切进表情图目录
        skip = ("banner-src", "banner_", "ip.", "ip-", "00-")
        files = sorted(os.path.join(args.src, f) for f in os.listdir(args.src)
                       if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                       and not f.lower().startswith(skip))
        if not 8 <= len(files) <= 24:
            print(f"⚠️  源图 {len(files)} 张 — 官方要求 8~24 张，先补齐再切", file=sys.stderr)
        print(f"表情图 {len(files)} 张 → {out}/{sub}/")
        words = n["meanings"] if n else []
        for i, f in enumerate(files, 1):
            # 编号前缀保证排序与上传顺序一致，后缀带含义词让人一眼看懂
            label = f"-{words[i-1]}" if i <= len(words) else ""
            save(fit_square(Image.open(f), 240), f"{out}/{sub}/{i:02d}{label}.png", 500)

    if args.cover:
        print("封面图 240×240（透明）")
        name = f"封面图-{n['ip']}.png" if n else "cover_240.png"
        save(fit_square(Image.open(args.cover), 240), f"{out}/{name}", 500)
    if args.icon:
        print("聊天面板图标 50×50（透明·头部正面）")
        name = f"聊天图标-{n['ip']}.png" if n else "icon_50.png"
        save(fit_head(Image.open(args.icon), 50), f"{out}/{name}", 100)
    if args.banner:
        print("详情页横幅 750×400（不透明·避免文字）")
        name = f"详情页横幅-{n['album']}.jpg" if n else "banner_750x400.jpg"
        save(cover_crop(Image.open(args.banner), (750, 400)), f"{out}/{name}", 500, jpeg=True)
    if args.reward_guide:
        print("赞赏引导图 750×560（不透明）")
        name = f"赞赏引导图-{n['ip']}.png" if n else "reward-guide_750x560.png"
        save(cover_crop(Image.open(args.reward_guide), (750, 560)).convert("RGB"), f"{out}/{name}", 500)
    if args.reward_thanks:
        print("赞赏致谢图 750×750（不透明）")
        name = f"赞赏致谢图-{n['ip']}.png" if n else "reward-thanks_750x750.png"
        save(cover_crop(Image.open(args.reward_thanks), (750, 750)).convert("RGB"), f"{out}/{name}", 500)

    print(f"\n切图完成，立刻机检：check_assets.py {out}")


if __name__ == "__main__":
    main()
