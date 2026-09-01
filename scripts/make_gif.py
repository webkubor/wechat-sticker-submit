#!/usr/bin/env python3
"""透明 PNG 序列 → 微信动态表情 GIF（240×240，≤500KB，循环播放）。

    make_gif.py <帧目录> <输出.gif> [--fps 12] [--max-kb 500]
    make_gif.py frames/ 01-开心.gif --fps 12
    make_gif.py frames/ 01-在呀.gif --fps 8 --bg "#F3E6D4"   # 照片型：实色底，不抠透明

帧目录里放按文件名排序的 PNG（任意尺寸，会统一切成 240×240）。
插画型默认 1-bit 透明；照片型加 --bg 把画布填实，绕开 GIF 对毛发半透明的短板。

## GIF 只有 1-bit 透明，这是绕不过去的

PNG 的 alpha 是 0~255 连续的，GIF 的透明只有「是/否」两种。所以每个半透明像素
必须二选一，两种选法各有代价：

    判为不透明 → 边缘残留原背景色，在微信深色模式下就是一圈白边/灰边
    判为透明   → 边缘变硬（锯齿），但不会出现异色描边

本脚本取阈值 128 再把主体收缩 1px（mktrans 的思路），实测在浅底和深底上
都不出 halo，代价是边缘略硬。**别用「杂边设为白色」那种预乘白底的做法** ——
浅色模式看着干净，深色模式下每张图都镶一圈白边。

## 官方对动态表情的要求（references/specs.md）

- GIF 格式，240×240，单张 ≤500KB
- 同一套专辑必须统一动/静，不能混
- 须设置循环播放，节奏流畅不卡顿
- ⚠️ **动作必须有意义**：官方明文「仅为了满足动态要求而进行无意义的缩放、
  平移、晃动、闪烁，脱离了实际含义或创意，不能通过审核」。
  所以不要拿一张图程序化地缩放位移充数，要真的有动作差异的多帧。
"""
import argparse
import glob
import os
import sys
from PIL import Image, ImageFilter

TRANSP = 255          # 保留最后一个调色板索引给透明色
SIDE = 240
ALPHA_CUT = 128       # 半透明像素的二值化阈值


def parse_bg(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        print(f"❌ --bg 须为 #RGB 或 #RRGGBB，收到 {s!r}", file=sys.stderr)
        sys.exit(2)
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return (r, g, b, 255)


def load_frames(src, side=SIDE, pad=0.94, bg=None):
    files = sorted(f for f in glob.glob(os.path.join(src, "*"))
                   if f.lower().endswith((".png", ".webp", ".gif", ".jpg", ".jpeg")))
    if not files:
        print(f"❌ {src} 里没有 PNG 帧", file=sys.stderr)
        sys.exit(2)
    out = []
    fill = bg if bg else (0, 0, 0, 0)
    for f in files:
        im = Image.open(f).convert("RGBA")
        if bg is None:
            box = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
            if box:
                im = im.crop(box)
            limit = int(side * pad)
            im.thumbnail((limit, limit), Image.LANCZOS)
        else:
            # 实色底：铺满 240，不留透明边。视频帧本身带背景，按短边居中裁方再缩放。
            w, h = im.size
            side_src = min(w, h)
            left, top = (w - side_src) // 2, (h - side_src) // 2
            im = im.crop((left, top, left + side_src, top + side_src))
            im = im.resize((side, side), Image.LANCZOS)
        c = Image.new("RGBA", (side, side), fill)
        if bg is None:
            c.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
        else:
            c.paste(im, (0, 0), im)
        out.append(c)
    return files, out


def rgba_to_p(im, colors=TRANSP, erode=True):
    """RGBA → P 模式且真正带透明索引。
    注意：直接 im.convert("P") 会丢掉 alpha —— 透明区会被填成实色，
    光设 info["transparency"] 是没用的，必须把透明像素 paste 成保留索引。"""
    a = im.getchannel("A")
    solid = a.point(lambda v: 255 if v >= ALPHA_CUT else 0)
    if erode:
        solid = solid.filter(ImageFilter.MinFilter(3))   # 收 1px，消 halo
    p = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=colors)
    p.paste(TRANSP, mask=solid.point(lambda v: 255 if v == 0 else 0))
    p.info["transparency"] = TRANSP
    return p


def rgb_to_p(im, colors=255):
    return im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=colors)


def write_gif(frames, out, fps, colors, keep_every=1, opaque=False, erode=True):
    seq = frames[::keep_every] if keep_every > 1 else frames
    if opaque:
        conv = [rgb_to_p(f, colors=colors) for f in seq]
        conv[0].save(out, save_all=True, append_images=conv[1:],
                     duration=max(20, int(1000 / fps * keep_every)),
                     loop=0, disposal=1, optimize=True)
    else:
        conv = [rgba_to_p(f, colors=colors, erode=erode) for f in seq]
        conv[0].save(out, save_all=True, append_images=conv[1:],
                     duration=max(20, int(1000 / fps * keep_every)),
                     loop=0, transparency=TRANSP, disposal=2, optimize=True)
    return len(seq), os.path.getsize(out) / 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="透明 PNG 帧目录")
    ap.add_argument("out", help="输出 GIF 路径")
    ap.add_argument("--fps", type=int, default=12, help="帧率，默认 12")
    ap.add_argument("--max-kb", type=int, default=500, help="体积上限，默认 500KB")
    ap.add_argument("--no-erode", action="store_true", help="不收缩 1px（边缘更满但可能有 halo）")
    ap.add_argument("--bg", default=None,
                    help="实色底 #RRGGBB。照片型动图用这个，输出不透明 GIF，不走 1-bit 透明")
    args = ap.parse_args()

    bg = parse_bg(args.bg) if args.bg else None
    files, frames = load_frames(args.src, bg=bg)
    mode = f"实色底 {args.bg}" if bg else "1-bit 透明"
    print(f"读入 {len(frames)} 帧 → {SIDE}×{SIDE}（{mode}）")

    # 先按原帧数试；超限就依次降色深、再抽帧 —— 抽帧最后做，因为它直接损伤动作流畅度
    plan = [(255, 1), (192, 1), (128, 1), (96, 1), (255, 2), (192, 2), (128, 2), (255, 3)]
    for colors, keep in plan:
        n, kb = write_gif(frames, args.out, args.fps, colors, keep,
                          opaque=bg is not None, erode=not args.no_erode)
        tag = f"{colors} 色" + (f"，每 {keep} 帧取 1（{n} 帧）" if keep > 1 else f"，{n} 帧")
        if kb <= args.max_kb:
            print(f"✓ {args.out}  {tag}  {kb:.0f}KB")
            if keep > 1:
                print(f"  ⚠️ 为压到 {args.max_kb}KB 抽掉了帧，动作可能变顿 —— "
                      f"更好的办法是减少原始帧数或简化画面")
            return 0
        print(f"  … {tag} → {kb:.0f}KB，超出 {args.max_kb}KB，继续压")

    print(f"❌ 压不到 {args.max_kb}KB 以内。降帧数（建议 ≤20 帧）或让画面更简洁后重试", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
