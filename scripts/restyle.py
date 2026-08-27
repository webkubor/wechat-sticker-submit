#!/usr/bin/env python3
"""照片型表情图 → 透明贴纸（抠图 + 重绘文字）。

    restyle.py <源目录> <输出目录> --texts texts.tsv --start 9

texts.tsv 每行三列（Tab 分隔）：源文件名、画面文字、含义词

    B-01.png<TAB>等饭饭～<TAB>等饭饭
    B-02.png<TAB>困死咯～<TAB>困死咯

输出 `<起始序号+i>-<含义词>.png`，240×240 透明 PNG。

## 为什么要重绘文字而不是保留原文字

照片型表情的文字通常压在照片背景上（毯子、桌面、墙）。抠图必然把背景连文字
一起去掉 —— 实测 birefnet 抠完只剩猫，文字和粉毯都没了。所以文字只能重绘。

重绘反而是好事：原素材往往每张字体、字号、描边都不一致（有白字黑边、有黑字、
有的字特别小），重绘之后整套统一。

## 为什么要抠透明

官方对表情图**不强制**透明背景（只强制封面与图标）。但不透明的白底照片发到微信
就是一个白方块，深色模式下边缘生硬 —— 用户会描述成「有白色毛边」「不像贴纸」。
注意这个问题**查文件参数查不出来**（尺寸、四边像素全正常），必须贴到深色底上才现形。
"""
import argparse
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_INDEX = 2          # W6 粗体 —— 表情包文字要够粗才压得住浅色背景
SIDE = 240
TEXT_BAND = 0.22        # 文字占底部比例
FILL = (255, 255, 255, 255)
STROKE = (74, 58, 52, 255)


def load_font(size):
    for path, idx in ((FONT, FONT_INDEX), (FONT, 0), ("/System/Library/Fonts/STHeiti Medium.ttc", 0)):
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


def text_mask(path, top_ratio=0.55, dilate=17):
    """定位画面里的描边文字。特征是「白笔画」与「深描边」在小邻域内共存。
    只在下半部找 —— 猫眼睛也是高对比黑白，整幅搜会把眼睛当成文字擦掉。"""
    from PIL import ImageChops
    im = Image.open(path).convert("L")
    w, h = im.size
    white = im.point(lambda v: 255 if v > 236 else 0)
    dark = im.point(lambda v: 255 if v < 100 else 0)
    both = ImageChops.multiply(white.filter(ImageFilter.MaxFilter(9)),
                               dark.filter(ImageFilter.MaxFilter(9)))
    m = both.filter(ImageFilter.MaxFilter(dilate))
    px = m.load()
    for y in range(int(h * top_ratio)):
        for x in range(w):
            px[x, y] = 0
    return m


def erase_text(src, dst, work):
    """擦掉原画面文字。顺序很关键：必须先擦字再抠图。
    反过来的话，压在主体身上的文字会随主体一起保留，跟重绘的新文字叠在一起。
    museav 的自动定位只认角标式半透明水印，这种大号描边文字要自己给 mask。"""
    if not shutil.which("museav"):
        return False
    mask = os.path.join(work, os.path.basename(src).replace(".png", "-mask.png"))
    m = text_mask(src)
    if not m.getbbox():
        shutil.copy2(src, dst)          # 没检测到文字，原图直接过
        return True
    m.save(mask)
    r = subprocess.run(["museav", "remove-watermark", src, "--mask", mask, "--out", dst, "--overwrite"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst):
        print(f"⚠️  擦字失败 {os.path.basename(src)}：{(r.stdout + r.stderr).strip()[:140]}", file=sys.stderr)
        shutil.copy2(src, dst)
        return True
    return True


def cutout(src, dst):
    """抠图。museav remove-bg 默认 birefnet —— 毛发边缘明显好于 isnet/u2net。"""
    if not shutil.which("museav"):
        print("❌ 需要 museav CLI 做抠图（或自己抠好后用 --skip-cutout）", file=sys.stderr)
        sys.exit(1)
    r = subprocess.run(["museav", "remove-bg", src, "--model", "birefnet", "--out", dst, "--overwrite"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst):
        print(f"⚠️  抠图失败 {os.path.basename(src)}：{(r.stdout + r.stderr).strip()[:160]}", file=sys.stderr)
        return False
    return True


def compose(nobg, text, side=SIDE, pad=0.92):
    im = Image.open(nobg).convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if box:
        im = im.crop(box)

    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    band = int(side * TEXT_BAND) if text else 0
    art_h = side - band
    scale = min(int(side * pad) / im.width, int(art_h * 0.98) / im.height)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    canvas.paste(im, ((side - im.width) // 2, max(0, art_h - im.height)), im)

    if text:
        # 按「实际渲染宽度」往下收字号，而不是按字数估算 ——
        # 估算会让「开心到飞起！」这种长句超出画面被裁掉。
        d = ImageDraw.Draw(canvas)
        max_w = side * 0.94
        size = int(band * 0.92)
        while size > 10:
            f = load_font(size)
            stroke = max(2, size // 9)
            if d.textlength(text, font=f) + stroke * 2 <= max_w:
                break
            size -= 1
        f = load_font(size)
        stroke = max(2, size // 9)
        tw = d.textlength(text, font=f)
        d.text(((side - tw) / 2, side - band - 2), text, font=f, fill=FILL,
               stroke_width=stroke, stroke_fill=STROKE)
    return canvas


def save(im, path, max_kb=500):
    im.save(path, "PNG", optimize=True)
    for colors in (256, 192, 128):
        if os.path.getsize(path) / 1024 <= max_kb:
            break
        im.quantize(colors=colors, method=Image.FASTOCTREE).save(path, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="原稿目录")
    ap.add_argument("out", help="输出目录")
    ap.add_argument("--texts", required=True, help="TSV：源文件名 / 画面文字 / 含义词")
    ap.add_argument("--start", type=int, default=1, help="输出起始编号，默认 1")
    ap.add_argument("--skip-cutout", action="store_true", help="源图已是透明 PNG，跳过擦字与抠图")
    ap.add_argument("--keep-text", action="store_true", help="不擦原画面文字（原文字压在主体上时会与新文字重叠）")
    ap.add_argument("--workdir", help="抠图中间件目录，默认放输出目录的 .cut/")
    args = ap.parse_args()

    rows = []
    for line in open(args.texts, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            print(f"⚠️  跳过格式不对的行：{line[:60]}", file=sys.stderr)
            continue
        rows.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))

    os.makedirs(args.out, exist_ok=True)
    work = args.workdir or os.path.join(args.out, ".cut")
    os.makedirs(work, exist_ok=True)

    print(f"共 {len(rows)} 张，起始编号 {args.start:02d}")
    ok = 0
    for i, (fname, text, word) in enumerate(rows):
        src = os.path.join(args.src, fname)
        if not os.path.exists(src):
            print(f"  ✗ 源图不存在：{fname}", file=sys.stderr)
            continue
        if args.skip_cutout:
            nobg = src
        else:
            clean = os.path.join(work, "clean-" + fname)
            if not (os.path.exists(clean) and os.path.getsize(clean) > 1000):
                if not args.keep_text:
                    erase_text(src, clean, work)
                else:
                    shutil.copy2(src, clean)
            nobg = os.path.join(work, fname)
            if not (os.path.exists(nobg) and os.path.getsize(nobg) > 1000):
                if not cutout(clean, nobg):
                    continue
        dst = os.path.join(args.out, f"{args.start + i:02d}-{word}.png")
        save(compose(nobg, text), dst)
        print(f"  ✓ {os.path.basename(dst)}  「{text}」  {os.path.getsize(dst)/1024:.0f}KB")
        ok += 1

    print(f"\n完成 {ok}/{len(rows)} 张 → {args.out}")
    print("抠图中间件留在 " + work + "（重跑会复用，删掉即重新抠）")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
