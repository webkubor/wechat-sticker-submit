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

机检通过后按此表在[微信表情开放平台](https://sticker.weixin.qq.com/cgi-bin/mmemoticonwebnode-bin/pages/home)逐项填写。
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

## 四、附加信息（官方规范文档里没写，但提交时必填）

| 字段 | 建议填 | 约束 |
|---|---|---|
| 类型 | {c.get('sticker_type', '（待定）真人拍摄 / 表情截图 / 表情卡通 / 表情其他')} | 单选 |
| 角色/内容 | {c.get('role', '（待定）如：宠物/动物角色 → 猫')} | ⚠️ 角色出现的表情数 ≥ 总数 1/3（本套 {len(mains)} 张 → 至少 {(len(mains) + 2) // 3} 张要有该角色） |
| 表情风格 | {c.get('style', '（待定）选 1~2 项')} | 日常·软萌可爱·二次元·长辈风·搞笑·丧/佛系·魔性鬼畜·恶搞·简笔画·赛博朋克·蒸汽波·像素·暗黑·复古 |
| 表情主题 | {c.get('theme', '（待定）')} | ⚠️ 与主题相关的表情数 ≥ 总数一半（本套至少 {(len(mains) + 1) // 2} 张）。可选：万能通用·网络热点·节日·考试/学习·工作/职场·情侣·毕业·刷屏·红包相关·游戏·运动/健身·怼人/斗图·群聊必备·节气·邀约/约起来·励志鼓舞 |
| 上架地区 | {c.get('region_publish', '中国大陆')} | — |
| 下载地区 | {c.get('region_download', '中国大陆')} | 全球 / 中国大陆 |
| 版权证明 | {c.get('copyright_proof', '（选填）涉及肖像权或版权授权时上传')} | JPG/PNG/BMP/PDF，每个 ≤10MB |

## 五、赞赏（可选）

{'| 字段 | 填写内容 |' if has_reward else '本套未准备赞赏素材。开通条件：艺术家资料审核通过 + 绑定微信号/商户号 + 无违规行为。'}
{'|---|---|' if has_reward else ''}
{f"| 赞赏引导语 | {c.get('reward_guide_text', '')} |" if has_reward else ''}
{f'| 赞赏引导图 | `{guide}` |' if has_reward else ''}
{f'| 赞赏致谢图 | `{thanks}` |' if has_reward and thanks else ''}

## 六、提交前最后三看

1. 逐张看一遍画面里有没有**多余文字、水印、签名** —— 机检不认识画面里的字。
2. 确认所有素材是**你原创或拥有版权**；垫图用的是自己的原图。
3. 确认 {len(mains)} 张**画面差异足够大** —— 整套差异不足是第一大拒因。
4. ⚠️ **横幅 / 赞赏引导图 / 赞赏致谢图里不能有任何 App 名、品牌名、平台名 ——
   包括「微信」自己**。曾有一套因横幅印了「微信表情包专辑」被判
   「推广非自有版权的应用程序」驳回，而那几张图机检全是 ✅。
"""
    path = os.path.join(d, "submit.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"提交清单已生成：{path}")


if __name__ == "__main__":
    main()
