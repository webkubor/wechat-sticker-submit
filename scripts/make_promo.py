#!/usr/bin/env python3
"""表情推广视频（1080×1920 竖版）—— 发朋友圈 / 视频号用。

    make_promo.py <系列目录> [--out promo.mp4] [--captions 文案.txt] [--music bgm.mp3]
    make_promo.py ~/.wechat-stickers/albums/莓啾/02-莓啾日常

## 这个脚本现在只做一件事：读 album.yml → 拼参数 → 调 `museav slideshow`

排版、放大、拼接、配乐处理全部下沉到了 museav CLI（`museav slideshow`），
因为「一组图 + 文案 + 配乐 → 竖版视频」跟表情包没关系，别的场景（产品图、
作品集、日报）一样要用。留在这里的只有表情包特有的部分：从 album.yml
取专辑名/形象名/文案，以及 `表情图/` 的目录约定。

museav 那边踩过的坑都在 `src/local-slideshow.ts` 顶部注释里（小图要显式放大、
配乐不能直接 -shortest、concat 末页要重复列一次），这里不再重复。

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_assets import parse_copy  # noqa: E402


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
    ap.add_argument("--theme", default="light", choices=["light", "dark"], help="配色，默认 light")
    args = ap.parse_args()

    if not shutil.which("museav"):
        print("❌ 需要 museav CLI：npm install -g museav-cli", file=sys.stderr)
        return 1
    if not shutil.which("ffmpeg"):
        print("❌ 需要 ffmpeg（museav slideshow 依赖它）", file=sys.stderr)
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

    out = args.out or os.path.join(d, f"推广视频-{title}.mp4")
    cmd = ["museav", "slideshow", pics_dir,
           "--title", title, "--footer", args.footer,
           "--sec", str(args.sec), "--theme", args.theme, "--out", out]
    if subtitle:
        cmd += ["--subtitle", subtitle]
    for cap in caps[:len(pics)]:
        cmd += ["--caption", cap]
    if args.music:
        cmd += ["--music", os.path.expanduser(args.music)]

    print(f"标题「{title}」· {len(pics)} 页 · 每页 {args.sec}s ≈ {len(pics)*args.sec:.0f}s")
    for p, cap in zip(pics, caps):
        print(f"  · {os.path.basename(p)}  「{cap}」")
    # 必须 flush：Python 的 stdout 有缓冲，而子进程直接写终端 ——
    # 不 flush 的话 museav 的输出会跑到这段清单前面，看起来像顺序错乱
    print(flush=True)

    # museav 的进度打 stderr、产物路径打 stdout，直接透传即可
    r = subprocess.run(cmd)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
