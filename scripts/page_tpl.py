"""IP 进度面板 —— 由 ip.py page 生成，自包含 HTML（图片内嵌 base64，不依赖外链）。"""
import base64
import io
import os
from PIL import Image


def thumb_b64(path, size, fmt="JPEG", quality=72):
    """缩略图转 base64。表情图数量多，缩到小尺寸再内嵌，避免页面几十 MB。"""
    try:
        im = Image.open(path)
    except Exception:
        return ""
    im = im.convert("RGBA")
    im.thumbnail((size, size), Image.LANCZOS)
    if fmt == "PNG":                       # 透明图保 PNG
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    flat = Image.new("RGB", im.size, (255, 255, 255))
    flat.paste(im, (0, 0), im)
    buf = io.BytesIO()
    flat.save(buf, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#f6f7f9; --card:#fff; --ink:#1c1f23; --muted:#6b7280; --line:#e6e8eb;
  --ok:#16a34a; --warn:#d97706; --bad:#dc2626; --accent:#d97757;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#15171a; --card:#1e2126; --ink:#e8eaed; --muted:#9aa1a9; --line:#2b2f36;
  --ok:#4ade80; --warn:#fbbf24; --bad:#f87171;
}}
:root[data-theme="dark"]{--bg:#15171a;--card:#1e2126;--ink:#e8eaed;--muted:#9aa1a9;--line:#2b2f36;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171}
:root[data-theme="light"]{--bg:#f6f7f9;--card:#fff;--ink:#1c1f23;--muted:#6b7280;--line:#e6e8eb;--ok:#16a34a;--warn:#d97706;--bad:#dc2626}
body{margin:0;padding:28px 20px 60px;background:var(--bg);color:var(--ink);
  font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",sans-serif}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:24px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13px;margin-bottom:24px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:26px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 18px;min-width:104px}
.stat b{display:block;font-size:24px;line-height:1.2;font-variant-numeric:tabular-nums}
.stat span{font-size:12px;color:var(--muted)}
.ip{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin-bottom:20px}
.ip-head{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}
.avatar{width:76px;height:76px;border-radius:14px;background:
  linear-gradient(45deg,#0000000a 25%,#0000 25%,#0000 75%,#0000000a 75%) 0 0/12px 12px,
  linear-gradient(45deg,#0000000a 25%,#0000 25%,#0000 75%,#0000000a 75%) 6px 6px/12px 12px;
  flex:0 0 auto;object-fit:contain}
.ip-name{font-size:19px;font-weight:600;margin:0 0 2px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.pill{font-size:11px;padding:2px 9px;border-radius:99px;border:1px solid var(--line);color:var(--muted);font-weight:500}
.pill.ok{color:var(--ok);border-color:currentColor}
.pill.warn{color:var(--warn);border-color:currentColor}
.desc{color:var(--muted);font-size:13px;margin:4px 0 0;max-width:60ch}
.checks{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:6px 18px;margin:16px 0 0;
  padding:14px 0 0;border-top:1px solid var(--line);font-size:13px}
.chk{display:flex;gap:8px;align-items:baseline}
.chk i{font-style:normal;flex:0 0 auto}
.chk .lbl{flex:0 0 92px;color:var(--muted)}
.chk .val{color:var(--ink);word-break:break-word}
.chk.bad .val{color:var(--bad)}
.chk.warn .val{color:var(--warn)}
.series{margin-top:18px;padding-top:16px;border-top:1px solid var(--line)}
.series h3{font-size:13px;color:var(--muted);margin:0 0 12px;font-weight:600;letter-spacing:.02em}
.s-card{border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px}
.s-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.s-name{font-weight:600;font-size:15px}
.s-meta{color:var(--muted);font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:8px}
.cell{text-align:center}
.cell img{width:100%;aspect-ratio:1;border-radius:9px;border:1px solid var(--line);object-fit:cover;display:block}
.cell span{display:block;font-size:10px;color:var(--muted);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.assets{display:flex;gap:14px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px dashed var(--line)}
.asset{text-align:center}
.asset img{border-radius:8px;border:1px solid var(--line);display:block;background:#fff}
.asset span{display:block;font-size:10px;color:var(--muted);margin-top:4px}
.todo{margin:14px 0 0;padding:12px 14px;border-radius:10px;background:#d977571a;border:1px solid #d9775740;font-size:13px}
.todo b{display:block;font-size:12px;margin-bottom:4px;color:var(--accent)}
.todo ul{margin:0;padding-left:18px}
.spec{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin-top:8px}
.spec h2{font-size:15px;margin:0 0 12px}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:520px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:600;font-size:12px}
td.n{font-variant-numeric:tabular-nums}
footer{color:var(--muted);font-size:12px;margin-top:22px;text-align:center}
code{background:#8881;padding:1px 5px;border-radius:4px;font-size:12px}
"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def render(ips, albums_root, stamp):
    """ips: [{name, desc, dir, items:[(st,label,note)], todo:[...], series:[{...}]}]"""
    n_ip = len(ips)
    n_series = sum(len(x["series"]) for x in ips)
    n_ready = sum(1 for x in ips for s in x["series"] if s["ready"])
    n_pics = sum(s["count"] for x in ips for s in x["series"])
    mark = {"ok": ("✅", ""), "warn": ("⚠️", "warn"), "missing": ("❌", "bad")}

    out = [f'<div class="wrap"><h1>表情形象进度</h1>',
           f'<p class="sub">{esc(stamp)} · 形象库 <code>~/.wechat-stickers</code> · '
           f'系列产物 <code>{esc(albums_root.replace(os.path.expanduser("~"), "~"))}</code></p>',
           '<div class="stats">',
           f'<div class="stat"><b>{n_ip}</b><span>表情形象</span></div>',
           f'<div class="stat"><b>{n_series}</b><span>系列</span></div>',
           f'<div class="stat"><b>{n_ready}</b><span>可提交</span></div>',
           f'<div class="stat"><b>{n_pics}</b><span>表情图</span></div>',
           '</div>']

    for ip in ips:
        done = sum(1 for st, _, _ in ip["items"] if st == "ok")
        total = len(ip["items"])
        cls = "ok" if done == total else "warn"
        out.append('<div class="ip"><div class="ip-head">')
        if ip.get("avatar"):
            out.append(f'<img class="avatar" src="{ip["avatar"]}" alt="{esc(ip["name"])}">')
        out.append('<div style="flex:1 1 240px">')
        out.append(f'<p class="ip-name">{esc(ip["name"])}'
                   f'<span class="pill {cls}">形象 {done}/{total}</span>'
                   f'<span class="pill">系列 {len(ip["series"])} 套</span></p>')
        if ip.get("desc"):
            out.append(f'<p class="desc">{esc(ip["desc"])}</p>')
        out.append('</div></div>')

        out.append('<div class="checks">')
        for st, label, note in ip["items"]:
            icon, c = mark[st]
            out.append(f'<div class="chk {c}"><i>{icon}</i><span class="lbl">{esc(label)}</span>'
                       f'<span class="val">{esc(note)}</span></div>')
        out.append('</div>')

        if ip.get("assets"):
            out.append('<div class="assets">')
            for a in ip["assets"]:
                out.append(f'<div class="asset"><img src="{a["src"]}" width="{a["w"]}" height="{a["h"]}" '
                           f'alt="{esc(a["label"])}"><span>{esc(a["label"])}</span></div>')
            out.append('</div>')

        if ip["todo"]:
            out.append('<div class="todo"><b>待办</b><ul>'
                       + "".join(f"<li>{esc(t)}</li>" for t in ip["todo"]) + '</ul></div>')

        out.append('<div class="series"><h3>系列（一个形象可挂多套，作品挂错只有 1 次改机会）</h3>')
        if not ip["series"]:
            out.append(f'<p class="desc">还没有系列。<code>new_album.sh --ip {esc(ip["name"])} '
                       f'--series &lt;系列名&gt;</code></p>')
        for s in ip["series"]:
            flag = "✅ 可提交" if s["ready"] else "🚧 未就绪"
            pc = "ok" if s["ready"] else "warn"
            out.append('<div class="s-card"><div class="s-head">'
                       f'<span class="s-name">{esc(s["name"])}</span>'
                       f'<span class="pill {pc}">{flag}</span>'
                       f'<span class="s-meta">{s["count"]} 张表情图'
                       + (f' · {esc(s["album_name"])}' if s.get("album_name") else "")
                       + '</span></div>')
            if s["pics"]:
                out.append('<div class="grid">')
                for p in s["pics"]:
                    out.append(f'<div class="cell"><img src="{p["src"]}" alt="{esc(p["label"])}">'
                               f'<span>{esc(p["label"])}</span></div>')
                out.append('</div>')
            if s.get("assets"):
                out.append('<div class="assets">')
                for a in s["assets"]:
                    out.append(f'<div class="asset"><img src="{a["src"]}" width="{a["w"]}" height="{a["h"]}" '
                               f'alt="{esc(a["label"])}"><span>{esc(a["label"])}</span></div>')
                out.append('</div>')
            out.append('</div>')
        out.append('</div></div>')

    out.append('''<div class="spec"><h2>官方规格速查</h2><div class="tw"><table>
<tr><th>素材</th><th>数量</th><th>格式</th><th>尺寸</th><th>大小</th><th>关键要求</th></tr>
<tr><td>表情图</td><td class="n">8～24</td><td>PNG/JPG/GIF</td><td class="n">240×240</td><td class="n">≤500KB</td><td>同套统一动/静，彼此差异要足够</td></tr>
<tr><td>详情页横幅</td><td class="n">1</td><td>PNG/JPG</td><td class="n">750×400</td><td class="n">≤500KB</td><td>不得有任何文字，不透明，避免白底</td></tr>
<tr><td>表情封面图</td><td class="n">1</td><td>PNG</td><td class="n">240×240</td><td class="n">≤500KB</td><td>须透明背景，正面半身/全身</td></tr>
<tr><td>聊天面板图标</td><td class="n">1</td><td>PNG</td><td class="n">50×50</td><td class="n">≤100KB</td><td>须透明背景，头部正面</td></tr>
<tr><td>赞赏引导图</td><td class="n">1</td><td>PNG/GIF</td><td class="n">750×560</td><td class="n">≤500KB</td><td>不透明，仅开赞赏时需要</td></tr>
<tr><td>赞赏致谢图</td><td class="n">1</td><td>PNG/GIF</td><td class="n">750×750</td><td class="n">≤500KB</td><td>不透明，仅开赞赏时需要</td></tr>
</table></div></div>
<footer>由 wechat-sticker-submit skill 的 <code>ip.py page</code> 生成 · 数字以官方文档为准</footer></div>''')
    return "\n".join(out)
