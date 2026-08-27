#!/usr/bin/env python3
"""IP 库 —— 表情形象的统一存放处，多套专辑复用同一个形象。

    ip.py add 团子 ~/Desktop/photo.png --desc "顶着粉蝴蝶结的白团子猫，情绪全写在脸上"
    ip.py list
    ip.py show 团子
    ip.py link 团子 ~/Desktop/团子日常      # 记录专辑归属（new_album.sh 会自动调）

库位置默认 ~/.wechat-stickers，可用环境变量 STICKER_HOME 覆盖：

    $STICKER_HOME/ips/<IP名>/
    ├── ip.yml           名称 / 简介 / 正面照来源 / 已挂专辑 / 待办
    ├── ip.png           正面照母版（出图垫图用这张，保证多套专辑形象一致）
    ├── ip-reverse.txt   读图逆向出的英文 prompt（一个 IP 只读一次，省时间省配额）
    ├── 形象头像-<IP>.png  240×240 透明 —— 形象主页用，与专辑封面是两回事
    ├── 形象图标-<IP>.png  50×50 透明
    └── source/          原始画稿池（不可再生，多套专辑从这里挑图）

分层的依据是**能不能再生**，不是「哪个更重要」：

    IP 库（这里）        原始画稿 + 形象母版 —— 丢了画不回来 → 全部 git 版本化
    专辑目录            表情图/封面/横幅/submit.md —— 有画稿加脚本就能重跑 → 不进 git

所以 ip.py sync 备份的是 IP 库，专辑产物不备份。要是反过来只备份产物，
真正贵的东西反而没保住。

另一条分层依据来自官方模型：「表情形象」是账号级资产（自己的名称/简介/头像/图标），
一个形象可挂多套专辑；封面图、横幅、含义词才是专辑级的。混在一起就会出现
「同一个 IP 的两套专辑简介不一致」「两个形象用了同一张头像」这类必被打回的问题。
"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_assets import parse_copy, dhash  # noqa: E402
from PIL import Image  # noqa: E402

HOME = os.path.expanduser(os.environ.get("STICKER_HOME", "~/.wechat-stickers"))
IPS = os.path.join(HOME, "ips")
# 系列（专辑）产物根目录，默认就在库里（albums/）。
# 微信的模型是「一个形象 → 多个系列」，所以按 <形象>/<序号-系列名>/ 分组，
# 看文件夹就知道谁属于谁。albums/ 进了 .gitignore —— 产物可再生，不占版本库。
ALBUMS = os.path.expanduser(os.environ.get("STICKER_ALBUMS", os.path.join(HOME, "albums")))
PUNCT = "，。！？、；：“”‘’（）…—,.!?;:'\"()"


def ip_dir(name):
    return os.path.join(IPS, name)


def load(name):
    p = os.path.join(ip_dir(name), "ip.yml")
    return parse_copy(p) if os.path.exists(p) else None


def all_ips():
    if not os.path.isdir(IPS):
        return []
    return sorted(d for d in os.listdir(IPS) if os.path.isdir(ip_dir(d)) and not d.startswith("."))


def save(name, data):
    os.makedirs(ip_dir(name), exist_ok=True)
    lines = [f"# 表情形象「{name}」—— 由 ip.py 维护，可手改", ""]
    for k in ("name", "desc", "type", "source", "created"):
        if data.get(k):
            lines.append(f"{k}: {data[k]}")
    lines.append("")
    lines.append("# 这个形象下的系列（只存系列名，不存绝对路径，搬目录不断链）")
    lines.append("# 官方规则：一套作品只能挂一个形象，改归属只有 1 次机会")
    lines.append("albums:")
    for a in data.get("albums", []):
        lines.append(f"  - {a}")
    lines.append("")
    lines.append("# 待办：还差什么才算这个形象完整（ip.py show 会连同自动核对一起显示）")
    lines.append("todo:")
    for t in data.get("todo", []):
        lines.append(f"  - {t}")
    with open(os.path.join(ip_dir(name), "ip.yml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def asset_state(path, size, need_alpha=True):
    """返回 (状态, 说明)：ok / warn / missing。形象头像与图标官方强制透明背景。"""
    if not path or not os.path.exists(path):
        return "missing", "缺失"
    try:
        im = Image.open(path)
        fmt, wh = im.format, im.size
        im = im.convert("RGBA")
    except Exception as e:
        return "warn", f"读不出：{e}"
    notes = []
    if wh != size:
        notes.append(f"{wh[0]}×{wh[1]} ≠ {size[0]}×{size[1]}")
    kb = os.path.getsize(path) / 1024
    if need_alpha:
        a = im.getchannel("A")
        k = max(2, min(wh) // 16)
        corners = [a.crop(c) for c in ((0, 0, k, k), (wh[0] - k, 0, wh[0], k),
                                       (0, wh[1] - k, k, wh[1]), (wh[0] - k, wh[1] - k, wh[0], wh[1]))]
        if max(sum(c.tobytes()) / (k * k) for c in corners) / 255 > 0.6:
            notes.append("四角不透明 → 官方明文「须设置为透明背景」")
        else:
            # 光看四角会被骗：切图时留了几个像素的透明边，中间仍是一整块没抠过的照片。
            # 真正要看的是主体外接框里是不是「实心矩形」。
            mask = a.point(lambda v: 255 if v > 16 else 0)
            box = mask.getbbox()
            if box:
                area = (box[2] - box[0]) * (box[3] - box[1])
                solid = sum(1 for v in mask.crop(box).tobytes() if v) / area if area else 0
                if solid > 0.95:
                    notes.append("主体是实心矩形 → 只是缩放贴上的照片，没抠出轮廓")
    return ("warn" if notes else "ok"), "；".join(notes) or f"{fmt} {wh[0]}×{wh[1]} {kb:.0f}KB"


def progress(name):
    """形象完善进度：官方对「表情形象」要求的每一项，逐条自动核对。"""
    d = ip_dir(name)
    meta = load(name) or {}
    items = []
    nm = meta.get("name", name)
    items.append(("ok" if len(nm) <= 8 and not any(c in nm for c in PUNCT) else "warn",
                  "形象名称", f"{nm}（{len(nm)} 字）"))
    desc = meta.get("desc", "")
    items.append(("ok" if 0 < len(desc) <= 80 else "missing" if not desc else "warn",
                  "形象简介", f"{len(desc)} 字" if desc else "缺失，≤80 字"))
    photo = os.path.join(d, "ip.png")
    items.append(("ok" if os.path.exists(photo) else "missing", "正面照母版",
                  f"{Image.open(photo).size[0]}×{Image.open(photo).size[1]}" if os.path.exists(photo) else "缺失"))
    rev = os.path.join(d, "ip-reverse.txt")
    items.append(("ok" if os.path.exists(rev) and os.path.getsize(rev) else "missing",
                  "读图 prompt", "已生成，多套专辑复用" if os.path.exists(rev) else "缺失，出图时会现读"))
    src_dir = os.path.join(d, "source")
    n_src = sum(1 for r, _, fs in os.walk(src_dir) for f in fs if not f.startswith(".")) if os.path.isdir(src_dir) else 0
    items.append(("ok" if n_src else "missing", "原始素材池",
                  f"source/ {n_src} 个原稿（不可再生，跟着 git 走）" if n_src else "缺失 —— 原始画稿只在别处的话就没备份"))
    st, note = asset_state(avatar_of(name), (240, 240))
    items.append((st, "形象头像 240×240", note))
    icon = next((os.path.join(d, f) for f in (os.listdir(d) if os.path.isdir(d) else [])
                 if f.startswith("形象图标")), None)
    st, note = asset_state(icon, (50, 50))
    items.append((st, "形象图标 50×50", note))
    return items, meta


def check_name(name):
    """官方对形象名称的硬约束。"""
    errs = []
    if len(name) > 8:
        errs.append(f"「{name}」{len(name)} 字，超出 8 字上限")
    if any(c in name for c in PUNCT):
        errs.append(f"「{name}」含标点，官方要求无标点")
    if " " in name or "　" in name:
        errs.append(f"「{name}」含空格")
    if name in all_ips():
        errs.append(f"「{name}」已存在 —— 同一作者的形象名不得重复；改名或用 ip.py show {name} 查看")
    return errs


def avatar_of(name):
    d = ip_dir(name)
    for f in os.listdir(d) if os.path.isdir(d) else []:
        if f.startswith("形象头像"):
            return os.path.join(d, f)
    return None


def clash_check(name, avatar_path):
    """官方：不同形象不得使用同一张头像/图标。注册时就查，别等审核打回。"""
    if not avatar_path or not os.path.exists(avatar_path):
        return []
    h = dhash(Image.open(avatar_path).convert("RGBA"))
    hits = []
    for other in all_ips():
        if other == name:
            continue
        p = avatar_of(other)
        if not p:
            continue
        if bin(h ^ dhash(Image.open(p).convert("RGBA"))).count("1") < 6:
            hits.append(other)
    return hits


def cmd_add(args):
    name, photo = args.name, os.path.expanduser(args.photo)
    errs = check_name(name)
    if not os.path.isfile(photo):
        errs.append(f"正面照不存在：{photo}")
    if args.desc and len(args.desc) > 80:
        errs.append(f"简介 {len(args.desc)} 字，超出 80 字上限")
    if errs:
        for e in errs:
            print(f"❌ {e}", file=sys.stderr)
        return 1

    d = ip_dir(name)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(photo, os.path.join(d, "ip.png"))
    print(f"✓ 正面照母版 → {d}/ip.png")

    # 读图只做一次：后续每套专辑出图都复用这份 prompt，形象才不会漂
    rev = os.path.join(d, "ip-reverse.txt")
    if not os.path.exists(rev) and shutil.which("museav"):
        print("▶ 读图逆向 IP 特征（只做这一次）...")
        with open(rev, "w", encoding="utf-8") as f:
            subprocess.run(["museav", "reverse", os.path.join(d, "ip.png")],
                           stdout=f, stderr=subprocess.DEVNULL, check=False)
        if os.path.getsize(rev) == 0:
            os.remove(rev)
            print("  ⚠️  读图没拿到结果，出图时会自动重试", file=sys.stderr)
        else:
            print(f"✓ 读图 prompt → {rev}")

    # 形象头像与图标：形象主页用，与专辑封面/图标是不同字段，但规格与要求一致
    fit = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fit_assets.py")
    r = subprocess.run([sys.executable, fit, d, "--cover", os.path.join(d, "ip.png"),
                        "--icon", os.path.join(d, "ip.png")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"⚠️  形象头像/图标生成失败：{r.stderr.strip()[:200]}", file=sys.stderr)
    for src, dst in (("cover_240.png", f"形象头像-{name}.png"), ("icon_50.png", f"形象图标-{name}.png")):
        s = os.path.join(d, src)
        if os.path.exists(s):
            os.replace(s, os.path.join(d, dst))
            print(f"✓ {dst}")

    clash = clash_check(name, avatar_of(name))
    if clash:
        print(f"⚠️  头像与已有形象 {'、'.join(clash)} 几乎相同 —— 官方要求不同形象不得用同一张头像，"
              f"换一张更有区分度的正面照重做", file=sys.stderr)

    if getattr(args, "source", None):
        sd = os.path.expanduser(args.source)
        if os.path.isdir(sd):
            dst = os.path.join(d, "source")
            os.makedirs(dst, exist_ok=True)
            n = 0
            for root, _, fs in os.walk(sd):
                for f in fs:
                    if f.startswith("."):
                        continue
                    rel = os.path.relpath(os.path.join(root, f), sd)
                    target = os.path.join(dst, rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(os.path.join(root, f), target)
                    n += 1
            print(f"✓ 原始画稿 {n} 个 → {dst}")
        else:
            print(f"⚠️  --source 不是目录：{sd}", file=sys.stderr)
    todo = [t for t in (args.todo or [])]
    save(name, {"name": name, "desc": args.desc or "", "type": args.type or "",
                "source": photo, "created": args.today or "", "albums": [], "todo": todo})
    print(f"\n形象「{name}」已入库：{d}")
    print(f"下一步：new_album.sh <专辑目录> --ip {name}")
    print(f"      备份：ip.py sync   ← 形象母版不可再生，别只留本地一份")
    return 0


def cmd_list(_args):
    ips = all_ips()
    if not ips:
        print(f"IP 库还是空的（{IPS}）\n用 ip.py add <名称> <正面照> 注册第一个形象")
        return 0
    print(f"🎭 表情形象 {len(ips)} 个  —— {HOME}")
    print("─" * 68)
    pending = 0
    for n in ips:
        items, meta = progress(n)          # 与 show 用同一套判定，避免两处口径不一致
        done = sum(1 for s, _, _ in items if s == "ok")
        on_disk = list_series(n)
        flag = "✅" if done == len(items) else "🚧"
        if done != len(items):
            pending += 1
        print(f"  {flag} {n:<8} 形象 {done}/{len(items)}   系列 {len(on_disk)} 套")
        if meta.get("desc"):
            print(f"      {meta['desc'][:44]}")
        for st, label, note in items:
            if st != "ok":
                print(f"      ↳ {label}：{note}")
        for sname in on_disk:
            cnt, ready = series_state(n, sname)
            state, _ = platform_status(n, sname)
            icon = PLATFORM_STATES.get(state, ("❔",))[0]
            print(f"      {icon} {sname}（{cnt} 张）· {state}")
    print("─" * 68)
    if pending:
        print(f"{pending} 个形象还没齐 —— ip.py show <名称> 看待办")
    else:
        print("形象资产都已齐备")
    return 0


def cmd_show(args):
    name = args.name
    if not load(name):
        print(f"❌ 没有形象「{name}」，现有：{'、'.join(all_ips()) or '（空）'}", file=sys.stderr)
        return 1
    items, meta = progress(name)
    done = sum(1 for s, _, _ in items if s == "ok")
    mark = {"ok": "✅", "warn": "⚠️ ", "missing": "❌"}

    print(f"🎭 {name}    完善进度 {done}/{len(items)}")
    print(f"   {ip_dir(name)}")
    if meta.get("desc"):
        print(f"   {meta['desc']}")
    print()
    for st, label, note in items:
        print(f"  {mark[st]} {label:<16} {note}")

    # 系列以磁盘为准，ip.yml 的记录只用来对账 —— 目录才是真相，记录会漂
    on_disk = list_series(name)
    recorded = meta.get("albums", [])
    print(f"\n  系列 {len(on_disk)} 套    {os.path.join(ALBUMS, name)}")
    for sname in on_disk:
        cnt, ready = series_state(name, sname)
        state, when = platform_status(name, sname)
        icon, desc = PLATFORM_STATES.get(state, ("❔", state))
        local = f"{cnt} 张" + ("，素材就绪" if ready else "，素材未就绪")
        print(f"    {icon} {sname:<16} {state}{'（' + when + '）' if when else ''}　{local}　{desc}")
    for g in [r for r in recorded if r not in on_disk]:
        print(f"    ❌ {g:<16} ip.yml 有记录，磁盘上没有")
    if not on_disk:
        print(f"    （还没有；new_album.sh --ip {name} --series <系列名> 出第一套）")

    todo = meta.get("todo", [])
    blockers = [f"{label}：{note}" for st, label, note in items if st != "ok"]
    if todo or blockers:
        print("\n  待办：")
        for b in blockers:
            print(f"    · {b}")
        for t in todo:
            print(f"    · {t}")
    else:
        print("\n  形象资产已齐备，可以在平台创建表情形象了。")
    return 0


def build_avatar(name, photo=None):
    """由正面照母版生成形象头像 240×240 与形象图标 50×50（都透明）。"""
    d = ip_dir(name)
    src = photo or os.path.join(d, "ip.png")
    fit = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fit_assets.py")
    r = subprocess.run([sys.executable, fit, d, "--cover", src, "--icon", src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"⚠️  头像/图标生成失败：{r.stderr.strip()[:200]}", file=sys.stderr)
        return
    for tmp, dst in (("cover_240.png", f"形象头像-{name}.png"), ("icon_50.png", f"形象图标-{name}.png")):
        p = os.path.join(d, tmp)
        if os.path.exists(p):
            os.replace(p, os.path.join(d, dst))
            print(f"✓ {dst}")


def cmd_update(args):
    """换正面照母版并重做头像/图标 —— 原来那张抠得不好、或换了更合适的取景时用。"""
    name = args.name
    meta = load(name)
    if not meta:
        print(f"❌ 没有形象「{name}」", file=sys.stderr)
        return 1
    d = ip_dir(name)
    if args.photo:
        photo = os.path.expanduser(args.photo)
        if not os.path.isfile(photo):
            print(f"❌ 正面照不存在：{photo}", file=sys.stderr)
            return 1
        shutil.copy2(photo, os.path.join(d, "ip.png"))
        meta["source"] = photo
        print(f"✓ 正面照母版已换 → {d}/ip.png")
        if args.rereverse:
            rev = os.path.join(d, "ip-reverse.txt")
            if shutil.which("museav"):
                print("▶ 重新读图 ...")
                with open(rev, "w", encoding="utf-8") as f:
                    subprocess.run(["museav", "reverse", os.path.join(d, "ip.png")],
                                   stdout=f, stderr=subprocess.DEVNULL, check=False)
        build_avatar(name)
    if args.desc:
        if len(args.desc) > 80:
            print(f"❌ 简介 {len(args.desc)} 字，超出 80 字上限", file=sys.stderr)
            return 1
        meta["desc"] = args.desc
    if getattr(args, "add_source", None):
        sd = os.path.expanduser(args.add_source)
        if os.path.isdir(sd):
            dst = os.path.join(d, "source")
            os.makedirs(dst, exist_ok=True)
            n = 0
            for root, _, fs in os.walk(sd):
                for f in fs:
                    if f.startswith("."):
                        continue
                    rel = os.path.relpath(os.path.join(root, f), sd)
                    target = os.path.join(dst, rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(os.path.join(root, f), target)
                    n += 1
            print(f"✓ 原始画稿 {n} 个 → {dst}")
        else:
            print(f"⚠️  --add-source 不是目录：{sd}", file=sys.stderr)
    if args.clear_todo:
        meta["todo"] = []
    for t in (args.todo or []):
        meta.setdefault("todo", []).append(t)
    save(name, meta)

    clash = clash_check(name, avatar_of(name))
    if clash:
        print(f"⚠️  头像与已有形象 {'、'.join(clash)} 几乎相同 —— 官方要求不同形象不得用同一张头像",
              file=sys.stderr)
    print()
    return cmd_show(args)


def cmd_rename(args):
    """改形象名 —— 平台上的形象名才是真源，本地对不上就得改过来。
    要动的地方比想象的多：库目录、ip.yml、形象头像/图标文件名、
    系列根目录、每套系列里的封面/图标文件名、每份 album.yml 的 ip_name。
    漏一处就会出现「文件名写着旧名、清单写着新名」这种半吊子状态。"""
    old, new = args.old, args.new
    meta = load(old)
    if not meta:
        print(f"❌ 没有形象「{old}」", file=sys.stderr)
        return 1
    errs = [e for e in check_name(new) if "已存在" not in e or new in all_ips()]
    if new in all_ips():
        print(f"❌ 「{new}」已存在，不能改成同名", file=sys.stderr)
        return 1
    if errs:
        for e in errs:
            print(f"❌ {e}", file=sys.stderr)
        return 1

    changed = []
    # 1) 库目录内的文件名
    d_old, d_new = ip_dir(old), ip_dir(new)
    for f in os.listdir(d_old):
        if old in f:
            os.rename(os.path.join(d_old, f), os.path.join(d_old, f.replace(old, new)))
            changed.append(f"{f} → {f.replace(old, new)}")
    # 2) 库目录本身
    os.rename(d_old, d_new)
    changed.append(f"ips/{old}/ → ips/{new}/")
    # 3) ip.yml 里的 name
    meta["name"] = new
    save(new, meta)
    changed.append("ip.yml: name")

    # 4) 系列根目录 + 每套系列里的素材名与 album.yml
    a_old, a_new = os.path.join(ALBUMS, old), os.path.join(ALBUMS, new)
    if os.path.isdir(a_old):
        os.rename(a_old, a_new)
        changed.append(f"{old}/ → {new}/（系列根目录）")
        for sname in list_series(new):
            sd = series_dir(new, sname)
            for f in os.listdir(sd):
                if old in f:
                    os.rename(os.path.join(sd, f), os.path.join(sd, f.replace(old, new)))
                    changed.append(f"{sname}/{f} → {f.replace(old, new)}")
            copy_path = os.path.join(sd, "album.yml")
            if os.path.exists(copy_path):
                txt = open(copy_path, encoding="utf-8").read()
                if f"ip_name: {old}" in txt:
                    open(copy_path, "w", encoding="utf-8").write(
                        txt.replace(f"ip_name: {old}", f"ip_name: {new}"))
                    changed.append(f"{sname}/album.yml: ip_name")

    print(f"✓ 「{old}」→「{new}」，共动了 {len(changed)} 处：")
    for c in changed:
        print(f"    {c}")
    print("\n提交清单里带了文件名，记得重新生成：")
    for sname in list_series(new):
        print(f"    python3 make_submit.py {series_dir(new, sname)!r}")
    return 0


def cmd_page(args):
    """生成自包含 HTML 面板 —— 图片内嵌 base64，双击就能看，不依赖任何外链或服务。"""
    from page_tpl import CSS, render, thumb_b64
    ips = []
    for name in all_ips():
        items, meta = progress(name)
        d = ip_dir(name)
        av = avatar_of(name)
        icon = next((os.path.join(d, f) for f in os.listdir(d) if f.startswith("形象图标")), None)
        assets = []
        if av:
            assets.append({"src": thumb_b64(av, 96, "PNG"), "w": 76, "h": 76, "label": "形象头像 240×240"})
        if icon:
            assets.append({"src": thumb_b64(icon, 50, "PNG"), "w": 50, "h": 50, "label": "形象图标 50×50"})
        series = []
        for sname in list_series(name):
            sd = series_dir(name, sname)
            cnt, ready = series_state(name, sname)
            pics_dir = os.path.join(sd, "表情图")
            if not os.path.isdir(pics_dir):
                pics_dir = os.path.join(sd, "main_240")
            pics = []
            if os.path.isdir(pics_dir):
                for f in sorted(x for x in os.listdir(pics_dir) if not x.startswith(".")):
                    pics.append({"src": thumb_b64(os.path.join(pics_dir, f), 96),
                                 "label": os.path.splitext(f)[0]})
            sassets = []
            for pat, label, box in (("封面图-", "封面图 240×240", 76), ("聊天图标-", "聊天图标 50×50", 50),
                                    ("详情页横幅-", "详情页横幅 750×400", 190)):
                hit = next((os.path.join(sd, f) for f in os.listdir(sd) if f.startswith(pat)), None)
                if hit:
                    im_w, im_h = Image.open(hit).size
                    h = round(box * im_h / im_w)
                    sassets.append({"src": thumb_b64(hit, max(box, 190), "PNG" if pat != "详情页横幅-" else "JPEG"),
                                    "w": box, "h": h, "label": label})
            copy_path = os.path.join(sd, "album.yml")
            c = parse_copy(copy_path) if os.path.exists(copy_path) else {}
            series.append({"name": sname, "count": cnt, "ready": ready, "pics": pics,
                           "assets": sassets, "album_name": c.get("album_name", "")})
        ips.append({"name": name, "desc": meta.get("desc", ""), "items": items,
                    "todo": meta.get("todo", []), "avatar": assets[0]["src"] if assets else "",
                    "assets": assets, "series": series})

    body = render(ips, ALBUMS, args.stamp or "")
    html = ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>表情形象进度</title><style>" + CSS + "</style></head><body>" + body + "</body></html>")
    out = args.out or os.path.join(HOME, "进度面板.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ 面板已生成：{out}（{os.path.getsize(out)/1024:.0f}KB，自包含）")
    if not args.no_open and shutil.which("open"):
        subprocess.run(["open", out], check=False)
    return 0


def git(*a, **kw):
    return subprocess.run(["git", "-C", HOME, *a], capture_output=True, text=True, **kw)


def cmd_sync(args):
    """把 IP 库推到私有 GitLab 仓库 —— 形象母版是这套流程里最不可再生的资产，
    本地单点存储必丢。图片与 ip.yml 一起版本化，换机 clone 即恢复。"""
    if not os.path.isdir(HOME):
        print(f"❌ IP 库还不存在：{HOME}", file=sys.stderr)
        return 1
    if not shutil.which("git"):
        print("❌ 没有 git", file=sys.stderr)
        return 1

    first = not os.path.isdir(os.path.join(HOME, ".git"))
    if first:
        print(f"▶ 首次同步：把 {HOME} 初始化为 git 仓库")
        git("init", "-b", "main")
        with open(os.path.join(HOME, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(".DS_Store\n")
        with open(os.path.join(HOME, "README.md"), "w", encoding="utf-8") as f:
            f.write("# 微信表情形象库（私有）\n\n"
                    "由 wechat-sticker-submit skill 的 `ip.py` 维护，存放表情形象的母版资产：\n\n"
                    "- `ips/<形象名>/ip.png` —— 正面照母版，出图垫图用这张\n"
                    "- `ips/<形象名>/ip-reverse.txt` —— 读图逆向的英文 prompt，一个形象只读一次\n"
                    "- `ips/<形象名>/形象头像-*.png` / `形象图标-*.png` —— 形象主页用（240×240 / 50×50，透明）\n"
                    "- `ips/<形象名>/ip.yml` —— 名称 / 简介 / 已挂专辑\n\n"
                    "换机恢复：\n\n"
                    "```bash\ngit clone <本仓库> ~/.wechat-stickers\n```\n\n"
                    "⚠️ 私有仓库：形象母版属未公开作品，且 `ip.yml` 记录了作品归属关系。\n")

    remote = args.remote
    if not git("remote", "get-url", "origin").returncode == 0:
        if not remote:
            if not shutil.which("glab"):
                print("❌ 没有 glab，无法自动建仓。用 --remote <git-url> 指定已有仓库", file=sys.stderr)
                return 1
            print("▶ 在 GitLab 创建私有仓库 wechat-sticker-ips ...")
            r = subprocess.run(["glab", "repo", "create", "wechat-sticker-ips", "--private",
                                "--description", "微信表情形象库（母版资产，由 wechat-sticker-submit skill 维护）",
                                "--defaultBranch", "main"],
                               capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip()
            print("  " + out.splitlines()[-1] if out else "")
            if r.returncode != 0 and "已存在" not in out and "already" not in out.lower():
                print(f"❌ 建仓失败：{out[:300]}", file=sys.stderr)
                return 1
            remote = "git@gitlab.com:webkubor/wechat-sticker-ips.git"
        git("remote", "add", "origin", remote)
        print(f"✓ origin → {remote}")

    git("add", "-A")
    st = git("status", "--porcelain").stdout.strip()
    if not st:
        print("库无变化，无需提交")
    else:
        n_ip = len(all_ips())
        n_alb = sum(len((load(n) or {}).get("albums", [])) for n in all_ips())
        msg = args.message or f"chore: 同步形象库（{n_ip} 个形象 / {n_alb} 套专辑）"
        r = git("-c", "user.name=webkubor", "commit", "-q", "-m", msg)
        if r.returncode != 0:
            print(f"❌ commit 失败：{(r.stdout + r.stderr)[:300]}", file=sys.stderr)
            return 1
        print(f"✓ {msg}")

    r = git("push", "-u", "origin", "main")
    if r.returncode != 0:
        print(f"❌ push 失败：{(r.stdout + r.stderr).strip()[:400]}", file=sys.stderr)
        return 1
    print("✓ 已推送到远端 —— 换机恢复：git clone <remote> ~/.wechat-stickers")
    return 0


PLATFORM_STATES = {
    "未提交": ("📦", "本地就绪，还没投"),
    "审核中": ("⏳", "已提交，等平台审核"),
    "已上架": ("✅", "线上可下载"),
    "未通过": ("❌", "被驳回，需改后重投"),
    "已下架": ("⛔", "已从线上移除"),
}


def album_yml(ip, series):
    return os.path.join(series_dir(ip, series), "album.yml")


def platform_status(ip, series):
    """读某套系列的平台状态。存在它自己的 album.yml 里 ——
    一套系列的配置（文案/含义词/附加信息/推广文案/平台状态）全在一个文件，
    不要散成 ip.yml 一处、captions/ 一处。"""
    p = album_yml(ip, series)
    if not os.path.exists(p):
        return "未提交", ""
    c = parse_copy(p)
    return c.get("platform_status", "未提交"), c.get("platform_date", "")


def set_album_field(ip, series, field, value):
    """就地改 album.yml 的一个字段，没有就追加 —— 保留注释与其余内容。"""
    p = album_yml(ip, series)
    lines = open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else []
    hit = False
    for i, ln in enumerate(lines):
        if ln.startswith(field + ":"):
            lines[i] = f"{field}: {value}"
            hit = True
            break
    if not hit:
        lines += ["", f"{field}: {value}"]
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def cmd_status(args):
    """标记某套系列在平台上的状态。
    本地机检通过只代表素材合规，跟平台是否上架是两件事 —— 混在一起看会误判进度。"""
    meta = load(args.name)
    if not meta:
        print(f"❌ 没有形象「{args.name}」", file=sys.stderr)
        return 1
    if args.state not in PLATFORM_STATES:
        print(f"❌ 状态只能是：{' / '.join(PLATFORM_STATES)}", file=sys.stderr)
        return 1
    on_disk = list_series(args.name)
    if args.series not in on_disk:
        print(f"❌ 磁盘上没有系列「{args.series}」，现有：{'、'.join(on_disk) or '（无）'}", file=sys.stderr)
        return 1
    set_album_field(args.name, args.series, "platform_status", args.state)
    if args.date:
        set_album_field(args.name, args.series, "platform_date", args.date)
    icon = PLATFORM_STATES[args.state][0]
    print(f"{icon} 「{args.name} / {args.series}」→ {args.state}"
          f"　（写入 {os.path.relpath(album_yml(args.name, args.series), HOME)}）")
    return 0


def series_dir(ip, series):
    return os.path.join(ALBUMS, ip, series)


def list_series(ip):
    """磁盘上这个形象有哪几套系列 —— 目录即真相，不依赖 ip.yml 里的记录。"""
    d = os.path.join(ALBUMS, ip)
    if not os.path.isdir(d):
        return []
    return sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and not x.startswith("."))


def series_state(ip, series):
    """一套系列的成色：表情图张数 + 提交清单在不在。"""
    d = series_dir(ip, series)
    pics = os.path.join(d, "表情图")
    if not os.path.isdir(pics):
        pics = os.path.join(d, "main_240")
    n = len([f for f in os.listdir(pics) if not f.startswith(".")]) if os.path.isdir(pics) else 0
    ready = os.path.exists(os.path.join(d, "submit.md")) and 8 <= n <= 24
    return n, ready


def cmd_link(args):
    """记录系列归属。只存系列名（不存绝对路径）—— 整棵树搬走也不会断链。"""
    name = args.name
    d = load(name)
    if not d:
        print(f"❌ 没有形象「{name}」", file=sys.stderr)
        return 1
    p = os.path.abspath(os.path.expanduser(args.album))
    series = os.path.basename(p.rstrip("/"))
    albums = d.get("albums", [])
    if series not in albums:
        albums.append(series)
        d["albums"] = albums
        save(name, d)
        print(f"✓ 系列「{series}」已记入形象「{name}」（第 {len(albums)} 套）")
    return 0


def main():
    ap = argparse.ArgumentParser(description="表情形象库")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="注册新形象")
    a.add_argument("name")
    a.add_argument("photo")
    a.add_argument("--desc", help="形象简介，≤80 字")
    a.add_argument("--type", choices=["photo", "illustration"], help="照片型 / 插画型")
    a.add_argument("--todo", action="append", help="待办事项，可重复传")
    a.add_argument("--source", help="原始画稿目录，一并收进 IP 库的 source/（不可再生资产别只留在别处）")
    a.add_argument("--today", help="创建日期，由调用方传入（脚本不取系统时间）")
    a.set_defaults(func=cmd_add)

    sub.add_parser("list", help="列出所有形象").set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="查看形象详情")
    s.add_argument("name")
    s.set_defaults(func=cmd_show)

    li = sub.add_parser("link", help="记录专辑归属")
    li.add_argument("name")
    li.add_argument("album")
    li.set_defaults(func=cmd_link)

    up = sub.add_parser("update", help="换正面照母版 / 改简介 / 增删待办，并重做头像图标")
    up.add_argument("name")
    up.add_argument("--photo", help="新的正面照（建议正面半身或全身、透明背景、无文字装饰）")
    up.add_argument("--desc", help="新简介，≤80 字")
    up.add_argument("--todo", action="append", help="追加待办")
    up.add_argument("--clear-todo", action="store_true", help="清空待办")
    up.add_argument("--rereverse", action="store_true", help="换图后重新读图出 prompt")
    up.add_argument("--add-source", help="把一个目录的原始画稿补进 IP 库的 source/")
    up.set_defaults(func=cmd_update)

    rn = sub.add_parser("rename", help="改形象名（同步库目录/文件名/系列目录/album.yml）")
    rn.add_argument("old")
    rn.add_argument("new")
    rn.set_defaults(func=cmd_rename)

    st = sub.add_parser("status", help="标记系列在平台上的状态（未提交/审核中/已上架/未通过/已下架）")
    st.add_argument("name")
    st.add_argument("series")
    st.add_argument("state", choices=list(PLATFORM_STATES))
    st.add_argument("--date", help="状态发生日期，如 2026-08-27")
    st.set_defaults(func=cmd_status)

    pg = sub.add_parser("page", help="生成 HTML 进度面板（自包含，双击可看）")
    pg.add_argument("--out", help="输出路径，默认 $STICKER_HOME/进度面板.html")
    pg.add_argument("--stamp", help="页面上显示的时间戳（脚本不取系统时间，由调用方传）")
    pg.add_argument("--no-open", action="store_true", help="生成后不自动打开")
    pg.set_defaults(func=cmd_page)

    sy = sub.add_parser("sync", help="备份形象库到私有 GitLab 仓库（首次自动建仓）")
    sy.add_argument("--remote", help="已有仓库的 git URL；不给则用 glab 建 wechat-sticker-ips")
    sy.add_argument("-m", "--message", help="提交说明")
    sy.set_defaults(func=cmd_sync)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
