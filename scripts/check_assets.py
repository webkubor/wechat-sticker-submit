#!/usr/bin/env python3
"""微信表情素材机检 — 按官方规范逐项判定，零依赖（仅 PIL）。

用法:
    check_assets.py <素材目录> [--copy album.yml] [--json]

判定分三级：FAIL(必须改) / WARN(人工确认) / OK。退出码 = FAIL 条数。
"""
import argparse
import glob
import json
import os
import sys
from PIL import Image, ImageFilter

# ---- 官方规格（references/specs.md） ----
# alpha: "must" = 官方明文「须设置为透明背景」→ FAIL；"prefer" = 未强制但插画型强烈建议 → WARN；
#        "no" = 明文「避免使用透明背景」→ FAIL
SPEC = {
    "main":   {"size": (240, 240), "max_kb": 500, "fmt": ("PNG", "JPEG", "GIF"), "alpha": "prefer"},
    "cover":  {"size": (240, 240), "max_kb": 500, "fmt": ("PNG",),               "alpha": "must"},
    "icon":   {"size": (50, 50),   "max_kb": 100, "fmt": ("PNG",),               "alpha": "must"},
    "banner": {"size": (750, 400), "max_kb": 500, "fmt": ("PNG", "JPEG"),        "alpha": "no"},
    "reward_guide":  {"size": (750, 560), "max_kb": 500, "fmt": ("PNG", "GIF"), "alpha": "no"},
    "reward_thanks": {"size": (750, 750), "max_kb": 500, "fmt": ("PNG", "GIF"), "alpha": "no"},
}
MAIN_MIN, MAIN_MAX = 8, 24


class Report:
    def __init__(self):
        self.rows = []

    def add(self, level, target, msg):
        self.rows.append({"level": level, "target": target, "msg": msg})

    fail = lambda self, t, m: self.add("FAIL", t, m)
    warn = lambda self, t, m: self.add("WARN", t, m)
    ok   = lambda self, t, m: self.add("OK", t, m)

    @property
    def fails(self):
        return sum(1 for r in self.rows if r["level"] == "FAIL")


def kb(path):
    return os.path.getsize(path) / 1024


def load(path):
    im = Image.open(path)
    fmt, n_frames = im.format, getattr(im, "n_frames", 1)
    return im.convert("RGBA"), fmt, n_frames


def alpha_stats(im):
    """返回 (主体掩码, bbox 占比, 四角不透明度, 半透明边缘占比)。"""
    a = im.getchannel("A")
    mask = a.point(lambda v: 255 if v > 16 else 0)
    bbox = mask.getbbox()
    w, h = im.size
    fill = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) / (w * h)) if bbox else 0.0

    k = max(2, min(w, h) // 16)
    corners = [a.crop(c) for c in ((0, 0, k, k), (w - k, 0, w, k), (0, h - k, k, h), (w - k, h - k, w, h))]
    corner_op = max(sum(c.tobytes()) / (k * k) for c in corners) / 255

    px = a.tobytes()
    edge = sum(1 for v in px if 16 < v < 240)
    solid = sum(1 for v in px if v >= 240)
    soft = edge / solid if solid else 0.0
    return mask, fill, corner_op, soft


def white_fringe(im, mask):
    """返回 (轮廓近白比例, 主体内部近白比例)。
    只有轮廓明显比内部更白才是白描边 —— 白色系角色（白猫、雪人）内部本身就近白，
    单看轮廓比例会误报。"""
    inner_mask = mask.filter(ImageFilter.MinFilter(5))
    rim, inner = [], []
    for y in range(im.height):
        for x in range(im.width):
            if not mask.getpixel((x, y)):
                continue
            (inner if inner_mask.getpixel((x, y)) else rim).append(min(im.getpixel((x, y))[:3]))
    if not rim:
        return 0.0, 0.0
    white = lambda vs: sum(1 for v in vs if v >= 235) / len(vs) if vs else 0.0
    return white(rim), white(inner)


def subject_box(im):
    """主体外接框：优先按 alpha，全不透明的照片型则按「非白」像素找。"""
    box = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if box and box != (0, 0, *im.size):
        return box
    return im.convert("L").point(lambda v: 255 if v < 235 else 0).getbbox() or (0, 0, *im.size)


def dhash(im):
    """差分哈希：只看相邻像素的明暗关系，比均值哈希更能区分同底色的不同画面。
    先裁到主体再算 —— 否则大片白/透明背景会把两张不同的图算成一样。"""
    g = im.crop(subject_box(im)).convert("L").resize((9, 8), Image.LANCZOS)
    px = g.tobytes()
    bits = 0
    for y in range(8):
        for x in range(8):
            if px[y * 9 + x] > px[y * 9 + x + 1]:
                bits |= 1 << (y * 8 + x)
    return bits


def check_one(path, kind, rep):
    name = os.path.basename(path)
    spec = SPEC[kind]
    try:
        im, fmt, frames = load(path)
    except Exception as e:
        rep.fail(name, f"无法读取：{e}")
        return None

    if fmt not in spec["fmt"]:
        rep.fail(name, f"格式 {fmt} 不合规，须为 {'/'.join(spec['fmt'])}")
    if im.size != spec["size"]:
        rep.fail(name, f"尺寸 {im.size[0]}×{im.size[1]} ≠ {spec['size'][0]}×{spec['size'][1]}（超规格会被平台静默压缩裁剪）")
    size_kb = kb(path)
    if size_kb > spec["max_kb"]:
        rep.fail(name, f"{size_kb:.0f}KB 超出 {spec['max_kb']}KB")
    if frames > 1:
        rep.fail(name, f"{frames} 帧动图 — 本 SOP 只做静态表情，同一套须统一动/静")

    mask, fill, corner_op, soft = alpha_stats(im)
    opaque = fmt == "JPEG" or corner_op > 0.6

    if spec["alpha"] in ("must", "prefer"):
        if opaque:
            # 不透明就没有轮廓可谈，后续抠图相关检测全部跳过，避免刷屏误报
            hint = ("官方明文「须设置为透明背景」" if spec["alpha"] == "must"
                    else "官方未强制，但插画型表情建议透明；照片型表情可忽略")
            msg = f"四角不透明（{corner_op:.0%}）— 白底或正方形边框，{hint}"
            (rep.fail if spec["alpha"] == "must" else rep.warn)(name, msg)
        else:
            fr, fr_inner = white_fringe(im, mask)
            if fr > 0.30 and fr - fr_inner > 0.30:
                rep.fail(name, f"主体轮廓 {fr:.0%} 近白、内部仅 {fr_inner:.0%} — 白色描边，须去掉")
            elif fr > 0.45:
                rep.warn(name, f"轮廓 {fr:.0%} 近白（内部 {fr_inner:.0%}）— 白色系角色属正常，人工确认没有多余白边")
            if soft < 0.015:
                rep.warn(name, f"边缘半透明过渡仅 {soft:.1%} — 可能有锯齿，建议用 museav remove-bg 重抠")
            if fill < 0.55:
                rep.warn(name, f"主体只占画面 {fill:.0%} — 留白过多，建议放大到 70% 以上")
            if fill > 0.99:
                rep.warn(name, "主体铺满画面 — 检查是否被裁到边缘、出现生硬直角")
    else:
        if not opaque:
            rep.fail(name, "横幅/赞赏图不得使用透明背景（官方明文「避免使用透明背景」）")
        raw = im.convert("RGB").resize((32, 32), Image.LANCZOS).tobytes()
        whites = sum(1 for i in range(0, len(raw), 3) if min(raw[i:i + 3]) >= 240)
        if whites / 1024 > 0.5:
            rep.warn(name, "过半画面接近白色 — 与微信底色区分不足，官方要求色调活泼明朗")

    if not [r for r in rep.rows if r["target"] == name and r["level"] == "FAIL"]:
        rep.ok(name, f"{fmt} {im.size[0]}×{im.size[1]} {size_kb:.0f}KB")
    return im


def parse_copy(path):
    """零依赖解析 album.yml（key: value 与 - 列表行两种形态）。make_submit.py 也用它。"""
    data, key = {}, None
    for raw in open(path, encoding="utf-8"):
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and key:
            data.setdefault(key, []).append(line.lstrip()[2:].strip())
        elif ":" in line and not line.startswith(" "):
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip().strip('"\'')
            data[key] = val if val else []
    return data


def check_copy(path, n_main, rep):
    """校验文案字数。"""
    limits = {"ip_name": 8, "ip_desc": 80, "album_name": 8, "album_desc": 80, "copyright": 10}
    data = parse_copy(path)

    for field, lim in limits.items():
        val = data.get(field)
        if not val:
            rep.fail("copy", f"缺字段 {field}")
        elif len(val) > lim:
            rep.fail("copy", f"{field}「{val}」{len(val)} 字，超出 {lim} 字上限")
        elif field in ("ip_name", "album_name"):
            if any(c in val for c in "，。！？、；：""''（）…—,.!?;:"):
                rep.fail("copy", f"{field}「{val}」含标点，官方要求无标点")
            if " " in val or "　" in val:
                rep.fail("copy", f"{field}「{val}」含空格")
            if len(val) > 5:
                rep.warn("copy", f"{field}「{val}」{len(val)} 字，5 字以内显示效果最佳")

    words = data.get("meanings", [])
    if len(words) != n_main:
        rep.fail("copy", f"含义词 {len(words)} 条 ≠ 表情图 {n_main} 张，须一一对应")
    for w in words:
        if len(w) > 4:
            rep.fail("copy", f"含义词「{w}」{len(w)} 字，超出 4 字上限")
        if any(c in w for c in "，。！？、；：…—,.!?"):
            rep.warn("copy", f"含义词「{w}」含标点，官方建议避免")
    dup = {w for w in words if words.count(w) > 1}
    if dup:
        rep.fail("copy", f"含义词重复：{'、'.join(dup)} — 同一套内不得重复")

    guide = data.get("reward_guide_text")
    if guide and not 5 <= len(guide) <= 15:
        rep.fail("copy", f"赞赏引导语「{guide}」{len(guide)} 字，须 5~15 字")
    if not rep.fails:
        rep.ok("copy", f"文案字数全部合规（{len(words)} 条含义词）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--copy", help="文案文件（album.yml）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    d, rep = args.dir, Report()

    # 兼容两套命名：中文（表情图/01-开心.png）与英文（main_240/01.png）
    main_dir = next((p for p in (os.path.join(d, "表情图"), os.path.join(d, "main_240"))
                     if os.path.isdir(p)), None)
    mains = sorted(f for f in os.listdir(main_dir)
                   if not f.startswith(".")) if main_dir else []
    label = os.path.basename(main_dir) + "/" if main_dir else "表情图/"
    if not mains:
        rep.fail(label, "缺少表情图目录（表情图/ 或 main_240/）")
    elif not MAIN_MIN <= len(mains) <= MAIN_MAX:
        rep.fail(label, f"{len(mains)} 张，须为 {MAIN_MIN}~{MAIN_MAX} 张")

    hashes = {}
    for f in mains:
        im = check_one(os.path.join(main_dir, f), "main", rep)
        if im:
            hashes[f] = dhash(im)

    names = list(hashes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            dist = bin(hashes[a] ^ hashes[b]).count("1")
            if dist < 6:
                rep.fail(f"{a} vs {b}", f"画面几乎相同（差分哈希距离 {dist}/64）— 整套差异不足是最高频拒因")
            elif dist < 11:
                rep.warn(f"{a} vs {b}", f"构图偏接近（距离 {dist}/64）— 建议换姿势或视角，别只改表情细节")

    for kind, desc, pats in (
        ("cover", "表情封面图", ["封面图*.png", "cover_240.png"]),
        ("icon", "聊天面板图标", ["聊天图标*.png", "icon_50.png"]),
        ("banner", "详情页横幅", ["详情页横幅*.jpg", "详情页横幅*.png", "banner_750x400.*"]),
        ("reward_guide", "赞赏引导图", ["赞赏引导图*.png", "reward-guide_750x560.png"]),
        ("reward_thanks", "赞赏致谢图", ["赞赏致谢图*.png", "reward-thanks_750x750.png"]),
    ):
        hit = next((p for pat in pats for p in sorted(glob.glob(os.path.join(d, pat)))), None)
        if hit:
            check_one(hit, kind, rep)
        elif kind.startswith("reward"):
            rep.warn(desc, "缺失 — 仅开通赞赏时需要")
        else:
            rep.fail(desc, "必需素材缺失")

    if args.copy:
        check_copy(args.copy if os.path.exists(args.copy) else os.path.join(d, args.copy), len(mains), rep)

    if args.json:
        print(json.dumps(rep.rows, ensure_ascii=False, indent=2))
    else:
        icon = {"FAIL": "❌", "WARN": "⚠️ ", "OK": "✅"}
        for lvl in ("FAIL", "WARN", "OK"):
            for r in [x for x in rep.rows if x["level"] == lvl]:
                print(f"{icon[lvl]} {r['target']}: {r['msg']}")
        print(f"\n{'可以提交' if not rep.fails else f'{rep.fails} 项必须修复'}"
              f" — FAIL {rep.fails} / WARN {sum(1 for r in rep.rows if r['level']=='WARN')}")
    return min(rep.fails, 125)


if __name__ == "__main__":
    sys.exit(main())
