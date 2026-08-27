#!/usr/bin/env python3
"""生成提交清单 submit.md —— 平台表单每个字段填什么、传哪张图，照抄即可。

    make_submit.py <素材目录> [--copy album.yml]

这是「最后一公里」：机检通过之后，人还得去平台一个个字段填。
清单按平台表单的实际顺序排，每行给出「字段 → 值 / 文件」，避免对着一堆 PNG 猜编号。
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_assets import parse_copy  # noqa: E402


def find(d, *pats):
    """按候选模式找素材，兼容中文命名与英文命名两套。"""
    for pat in pats:
        hit = sorted(glob.glob(os.path.join(d, pat)))
        if hit:
            return os.path.basename(hit[0])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--copy", default="album.yml")
    args = ap.parse_args()
    d = args.dir
    copy_path = args.copy if os.path.exists(args.copy) else os.path.join(d, args.copy)
    c = parse_copy(copy_path)

    main_dir = next((p for p in ("表情图", "main_240") if os.path.isdir(os.path.join(d, p))), "表情图")
    mains = sorted(f for f in os.listdir(os.path.join(d, main_dir)) if not f.startswith("."))
    words = c.get("meanings", [])
    rows = "\n".join(
        f"| {i} | `{main_dir}/{f}` | {words[i-1] if i <= len(words) else '⚠️ 缺'} |"
        for i, f in enumerate(mains, 1)
    )
    cover = find(d, "封面图*.png", "cover_240.png") or "（缺失）"
    icon = find(d, "聊天图标*.png", "icon_50.png") or "（缺失）"
    banner = find(d, "详情页横幅*.jpg", "详情页横幅*.png", "banner_750x400.*") or "（缺失）"
    guide = find(d, "赞赏引导图*.png", "reward-guide_750x560.png")
    thanks = find(d, "赞赏致谢图*.png", "reward-thanks_750x750.png")
    has_reward = bool(guide)

    out = f"""# 提交清单 — {c.get('album_name', '(未填专辑名)')}

机检通过后按此表在[微信表情开放平台](https://sticker.weixin.qq.com/)逐项填写。
素材目录：`{os.path.abspath(d)}`

## 一、表情形象（第一次投稿要先建形象）

| 字段 | 填写内容 |
|---|---|
| 形象名称 | {c.get('ip_name', '')} |
| 形象简介 | {c.get('ip_desc', '')} |
| 形象头像 | `{cover}`（240×240 PNG，透明） |
| 形象图标 | `{icon}`（50×50 PNG，透明） |

> ⚠️ **唯一不可逆的一步**：作品挂到形象后只有 **1 次**改到其他形象的机会，
> 且要先从原形象删除再加到新形象。挂之前确认清楚。

## 二、表情专辑

| 字段 | 填写内容 |
|---|---|
| 表情名称 | {c.get('album_name', '')} |
| 表情介绍 | {c.get('album_desc', '')} |
| 版权信息 | {c.get('copyright', '')} |
| 表情封面图 | `{cover}` |
| 聊天面板图标 | `{icon}` |
| 详情页横幅 | `{banner}` |
| 表情类型 | 静态 |

## 三、表情图与含义词（按编号顺序上传，一一对应）

| # | 上传文件 | 含义词 |
|---|---|---|
{rows}

共 {len(mains)} 张（官方允许 8~24 张任意数量）。

## 四、赞赏（可选）

{'| 字段 | 填写内容 |' if has_reward else '本套未准备赞赏素材。开通条件：艺术家资料审核通过 + 绑定微信号/商户号 + 无违规行为。'}
{'|---|---|' if has_reward else ''}
{f"| 赞赏引导语 | {c.get('reward_guide_text', '')} |" if has_reward else ''}
{f'| 赞赏引导图 | `{guide}` |' if has_reward else ''}
{f'| 赞赏致谢图 | `{thanks}` |' if has_reward and thanks else ''}

## 五、提交前最后三看

1. 逐张看一遍画面里有没有**多余文字、水印、签名** —— 机检不认识画面里的字。
2. 确认所有素材是**你原创或拥有版权**；垫图用的是自己的原图。
3. 确认 9 张（或 N 张）**画面差异足够大** —— 整套差异不足是第一大拒因。
"""
    path = os.path.join(d, "submit.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"提交清单已生成：{path}")


if __name__ == "__main__":
    main()
