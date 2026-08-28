#!/usr/bin/env python3
"""表情推广视频（1080×1920 竖版）—— 发朋友圈 / 视频号用。

    make_promo.py <系列目录> [--out promo.mp4] [--music 儿童轻快] [--voice <音色>]
    make_promo.py ~/.wechat-stickers/albums/莓啾/02-莓啾日常

## 这个脚本只做一件事：读 album.yml → 拼参数 → 调 `reel make`

出片能力在 **reel-kit**（`reel` 命令），不在这里，也不在 museav。
留在这里的只有表情包特有的部分：从 album.yml 取专辑名/形象名/文案，
以及 `表情图/` 的目录约定。

### 为什么是 reel-kit 而不是 museav

2026-08-28 走过一次弯路：先在 museav-cli 里做了个 `slideshow` 命令，
后来才发现 reel-kit 早就做了同一件事，而且更好 ——

  · 版式用 HTML/CSS（文字能换行、能做阴影渐变），museav 那版用 SVG 做不到
  · 支持配音，且**镜头时长由念白长度决定**（念快的不干等，念慢的不被切）
  · 默认走本地 voxcraft TTS，批量出片零成本

museav 的 slideshow 已下线。**要改版式就去 reel-kit 的 `templates/*.html`**，
丢一个 HTML 进去就是一个新版式，不用改代码。

## 和平台素材的关键区别

推广视频**不是平台素材字段**，所以可以有文字、可以写「微信」——
官方示例视频标题就是「微信气泡狗宅家篇」。
而详情页横幅里出现「微信」二字会被判「推广非自有版权的应用程序」直接驳回。
两种物料要分开准备，别拿同一张图两头用。

## 文案

真源是 `album.yml` 的 `captions` 段（一套系列的配置全在一个文件里）：

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_assets import parse_copy  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("series", help="系列目录（含 表情图/ 与 album.yml）")
    ap.add_argument("--out", help="输出 mp4，默认放系列目录下 推广视频-<专辑名>.mp4")
    ap.add_argument("--captions", help="临时覆盖用的文案文件（每行一条）。"
                                       "常规请写在 album.yml 的 captions 段里")
    ap.add_argument("--music", default="儿童轻快",
                    help="配乐：配乐库别名（默认 儿童轻快，见 reel bgm）或本地文件路径。"
                         "传空字符串则不加配乐")
    ap.add_argument("--sec", type=float, default=2.5, help="每张停留秒数，默认 2.5；开了 --voice 时由念白长度决定")
    ap.add_argument("--footer", default="微信搜索表情名，添加整套", help="底部引导语")
    ap.add_argument("--voice", help="开启配音的音色名（需 voxcraft 已注册音色，见 reel-kit README）。"
                                    "开了之后镜头时长由念白决定，不再用 --sec")
    ap.add_argument("--template", default="sticker-promo", help="reel-kit 版式模板名，默认 sticker-promo")
    ap.add_argument("--keep-frames", action="store_true", help="保留中间产物，排版调试用")
    args = ap.parse_args()

    if not shutil.which("reel"):
        print("❌ 需要 reel-kit：cd ~/dev/github/devtool/reel-kit && pnpm install && npm link\n"
              "   （出片能力在 reel-kit，museav 的 slideshow 已下线）", file=sys.stderr)
        return 1
    if not shutil.which("ffmpeg"):
        print("❌ 需要 ffmpeg（reel-kit 依赖它合成）", file=sys.stderr)
        return 1

    d = args.series
    pics_dir = next((os.path.join(d, x) for x in ("表情图", "main_240")
                     if os.path.isdir(os.path.join(d, x))), None)
    if not pics_dir:
        print(f"❌ {d} 下没有 表情图/ 或 main_240/", file=sys.stderr)
        return 1
    pics = sorted(f for f in glob.glob(os.path.join(pics_dir, "*.png"))
                  if not os.path.basename(f).startswith("."))
    if not pics:
        print(f"❌ {pics_dir} 里没有 png", file=sys.stderr)
        return 1

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
    caps = caps[:len(pics)]

    out = args.out or os.path.join(d, f"推广视频-{title}.mp4")

    print(f"标题「{title}」· {len(pics)} 页 · 版式 {args.template}"
          + (f" · 配音 {args.voice}" if args.voice else f" · 每页 {args.sec}s"))
    for p, cap in zip(pics, caps):
        print(f"  · {os.path.basename(p)}  「{cap}」")
    print(flush=True)  # 必须 flush：子进程直接写终端，不 flush 会让输出顺序看起来是乱的

    # reel 的文案走文件（一行一句，行数决定镜头数），所以这里落一个临时文件。
    # 用 delete=False + finally 删：Windows 上打开着的临时文件不能被子进程读。
    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        tmp.write("\n".join(caps) + "\n")
        tmp.close()

        cmd = ["reel", "make", "--template", args.template,
               "--assets", pics_dir, "--caps", tmp.name,
               "--title", title, "--footer", args.footer,
               "--per-shot", str(args.sec), "--out", out]
        if subtitle:
            cmd += ["--subtitle", subtitle]
        if args.music:
            cmd += ["--bgm", os.path.expanduser(args.music) if os.sep in args.music else args.music]
        if args.voice:
            cmd += ["--voice", args.voice]
        if args.keep_frames:
            cmd.append("--keep-frames")

        return subprocess.run(cmd).returncode
    finally:
        os.unlink(tmp.name)


if __name__ == "__main__":
    sys.exit(main())
