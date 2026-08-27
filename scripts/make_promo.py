#!/usr/bin/env python3
"""表情推广视频（1080×1920 竖版）—— 发朋友圈 / 视频号用。

    make_promo.py <系列目录> [--out promo.mp4] [--captions 文案.txt] [--music bgm.mp3]
    make_promo.py ~/.wechat-stickers/albums/莓啾/02-莓啾日常

版式对齐官方秒剪模板（实测其示例视频：1080×1920 / 30fps / 约 20 秒 / H.264+AAC）：

    白底 + 粉青装饰弧
      ↓
    顶部：专辑名（大）+ 形象名（小）
      ↓
    中间：一张表情图
      ↓
    下方：这张的文字说明
      ↓
    每张停 2.5 秒，全程配乐

## 和平台素材的关键区别

推广视频**不是平台素材字段**，所以可以有文字、可以写「微信」——
官方示例视频标题就是「微信气泡狗宅家篇」。
而详情页横幅里出现「微信」二字会被判「推广非自有版权的应用程序」直接驳回。
两种物料要分开准备，别拿同一张图两头用。

## 文案

推广文案的真源是 `album.yml` 的 `captions` 段（一套系列的配置全在一个文件里）：

```yaml
captions:
  - 需要被安慰的时候
  - 催外卖 / 催开饭
```

写「什么时候发这张」而不是重复画面文字，传播力更强。没写 `captions` 就退回用含义词。
`--captions` 只作临时覆盖，试不同文案时用。
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_assets import parse_copy  # noqa: E402

W, H = 1080, 1920
FONTS = ["/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"]
INK = (43, 45, 49)
MUTED = (140, 146, 155)
PINK = (255, 214, 226)
MINT = (186, 235, 226)


def font(size, bold=True):
    for p in FONTS:
        for idx in ((2, 0) if bold else (0, 2)):
            try:
                return ImageFont.truetype(p, size, index=idx)
            except Exception:
                continue
    return ImageFont.load_default()


def center(d, y, text, f, fill=INK):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)
    return w


def page(sticker_path, title, subtitle, caption, footer):
    """一页 = 一张表情 + 说明。装饰弧模仿官方模板的粉青色块。"""
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    # 左上粉弧、右下青弧 —— 位置固定，整套视频看起来是同一个模板
    d.ellipse([-320, -560, 700, 300], fill=PINK)
    d.ellipse([W - 260, H - 300, W + 320, H + 260], fill=MINT)

    center(d, 330, title, font(84))
    if subtitle:
        center(d, 460, subtitle, font(44, bold=False), MUTED)

    art = Image.open(sticker_path).convert("RGBA")
    box = art.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if box:
        art = art.crop(box)
    # 表情图源只有 240×240，而画面宽 1080 —— 必须放大。
    # 注意别用 thumbnail：它只缩小不放大，小图会原样贴上去，在竖屏里只占两成宽。
    # 目标 520（约占画面 48%），对齐官方示例里表情图的视觉比例。
    ART = 520
    scale = min(ART / art.width, ART / art.height)
    art = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))), Image.LANCZOS)
    zone_top, zone_h = 660, 700          # 表情图在这个区域内垂直居中，图大图小都不会偏
    im.paste(art, ((W - art.width) // 2, zone_top + (zone_h - art.height) // 2), art)

    if caption:
        # 字号按实际宽度收敛，长句不会溢出画面
        size = 72
        while size > 30:
            f = font(size)
            if d.textlength(caption, font=f) <= W * 0.86:
                break
            size -= 2
        center(d, 1520, caption, font(size))
    if footer:
        center(d, 1740, footer, font(34, bold=False), MUTED)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("series", help="系列目录（含 表情图/ 与 album.yml）")
    ap.add_argument("--out", help="输出 mp4，默认放系列目录下 推广视频-<专辑名>.mp4")
    ap.add_argument("--captions", help="临时覆盖用的文案文件（每行一条）。"
                                       "常规请写在 album.yml 的 captions 段里")
    ap.add_argument("--music", help="配乐音频。会自动裁到视频长度并加首尾淡入淡出。"
                                    "免费免署名来源：mixkit.co/free-stock-music（直链 "
                                    "assets.mixkit.co/music/<id>/<id>.mp3）")
    ap.add_argument("--sec", type=float, default=2.5, help="每张停留秒数，默认 2.5")
    ap.add_argument("--footer", default="微信搜索表情名，添加整套", help="底部引导语")
    ap.add_argument("--keep-pages", action="store_true", help="保留中间页面图，便于逐页检查")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        print("❌ 需要 ffmpeg", file=sys.stderr)
        return 1

    d = args.series
    pics_dir = next((os.path.join(d, x) for x in ("表情图", "main_240")
                     if os.path.isdir(os.path.join(d, x))), None)
    if not pics_dir:
        print(f"❌ {d} 下没有 表情图/ 或 main_240/", file=sys.stderr)
        return 1
    pics = sorted(f for f in glob.glob(os.path.join(pics_dir, "*.png")) if not os.path.basename(f).startswith("."))

    copy_path = os.path.join(d, "album.yml")
    c = parse_copy(copy_path) if os.path.exists(copy_path) else {}
    title = c.get("album_name") or os.path.basename(d)
    subtitle = c.get("ip_name", "")
    words = c.get("meanings", [])

    # 推广文案的真源是 album.yml 的 captions 段 —— 一套系列的配置全在一个文件里。
    # --captions 只作临时覆盖（试不同文案时用），不作为常规存放位置。
    caps = list(c.get("captions", []))
    if args.captions:
        caps = [ln.strip() for ln in open(args.captions, encoding="utf-8") if ln.strip()]
    if len(caps) < len(pics):
        # 文案不够就用含义词补；含义词也不够就用文件名里的词
        for i in range(len(caps), len(pics)):
            w = words[i] if i < len(words) else os.path.splitext(os.path.basename(pics[i]))[0].split("-", 1)[-1]
            caps.append(w)

    work = tempfile.mkdtemp(prefix="promo-")
    print(f"标题「{title}」· {len(pics)} 页 · 每页 {args.sec}s ≈ {len(pics)*args.sec:.0f}s")
    for i, p in enumerate(pics):
        page(p, title, subtitle, caps[i], args.footer).save(os.path.join(work, f"p{i:03d}.png"))
        print(f"  · {os.path.basename(p)}  「{caps[i]}」")

    # concat demuxer：最后一张要再列一次，否则它的 duration 会被忽略
    lst = os.path.join(work, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for i in range(len(pics)):
            f.write(f"file '{os.path.join(work, f'p{i:03d}.png')}'\nduration {args.sec}\n")
        f.write(f"file '{os.path.join(work, f'p{len(pics)-1:03d}.png')}'\n")

    out = args.out or os.path.join(d, f"推广视频-{title}.mp4")
    total = len(pics) * args.sec
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst]
    if args.music:
        cmd += ["-i", os.path.expanduser(args.music)]
    cmd += ["-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "22"]
    if args.music:
        # 配乐通常比视频长得多，直接 -shortest 会在中途硬切断。
        # 裁到视频时长并做首尾淡入淡出，收尾才不突兀。
        fade_out_at = max(0.0, total - 1.5)
        cmd += ["-af", f"atrim=0:{total},afade=t=in:st=0:d=1,afade=t=out:st={fade_out_at}:d=1.5",
                "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd.append(out)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ ffmpeg 失败：{(r.stdout + r.stderr).strip()[:400]}", file=sys.stderr)
        return 1

    kb = os.path.getsize(out) / 1024
    print(f"\n✓ {out}  {W}×{H}  {kb/1024:.1f}MB" + ("" if args.music else "  （无配乐，用 --music 加）"))
    if args.keep_pages:
        pages = os.path.join(d, "promo-pages")
        shutil.rmtree(pages, ignore_errors=True)
        shutil.copytree(work, pages, ignore=shutil.ignore_patterns("list.txt"))
        print(f"  页面图留在 {pages}")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
