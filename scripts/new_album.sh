#!/usr/bin/env bash
# 一键跑完整套静态表情：填文案 → 出图 → 切图 → 机检 → 提交清单
#
#   new_album.sh --ip 团子 --series 日常     # 推荐：自动放到 <专辑根>/团子/01-日常/
#   new_album.sh ~/Desktop/团子日常 --ip 团子  # 也可显式指定目录
#   new_album.sh ~/Desktop/团子日常           # 自己画好图放进 raw/ 也行
#
# 微信的模型是「一个形象 → 多个系列」：形象配置唯一（在 IP 库里一份），
# 系列可以有好几套。所以目录也按 <形象>/<序号-系列名>/ 分组，序号自动递增。
#
# --ip 给名字时从 IP 库取形象（正面照 + 读图 prompt + 形象名/简介都复用），
# 一个 IP 出多套专辑就靠这个保持一致。注册形象：ip.py add <名称> <正面照>
#
# 幂等：同一条命令可以反复跑。第一次跑生成 album.yml 就停下让你填文案，
# 填完再跑同一条命令，它会自动接着往下走；中途失败修完再跑，不会重做已完成的部分。
set -euo pipefail

STICKER_HOME="${STICKER_HOME:-$HOME/.wechat-stickers}"
STICKER_ALBUMS="${STICKER_ALBUMS:-$HOME/Pictures/表情包系列}"
DIR="" IP="" SERIES="" EMOTIONS="" STYLE="" FORCE_GEN=0 COVER_SRC="" ICON_SRC=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ip) IP="$2"; shift 2 ;;
    --series) SERIES="$2"; shift 2 ;;
    --cover-from) COVER_SRC="$2"; shift 2 ;;
    --icon-from) ICON_SRC="$2"; shift 2 ;;
    --emotions) EMOTIONS="$2"; shift 2 ;;
    --style) STYLE="$2"; shift 2 ;;
    --regen) FORCE_GEN=1; shift ;;
    -*) echo "未知参数 $1" >&2; exit 2 ;;
    *) DIR="$1"; shift ;;
  esac
done
# 给了 --series 就自动推导目录：<专辑根>/<形象>/<下一个序号>-<系列名>
if [[ -z "$DIR" && -n "$SERIES" ]]; then
  if [[ -z "$IP" || -f "$IP" ]]; then
    echo "⚠️  --series 要配合 --ip <已入库的形象名> 使用" >&2
    exit 2
  fi
  BASE="$STICKER_ALBUMS/$IP"
  mkdir -p "$BASE"
  # 已存在同名系列就直接复用它（幂等：反复跑同一条命令不会新建一堆空目录）
  EXIST=$(find "$BASE" -maxdepth 1 -type d -name "*-${SERIES}" | head -1)
  if [[ -n "$EXIST" ]]; then
    DIR="$EXIST"
  else
    NEXT=$(( $(find "$BASE" -maxdepth 1 -type d -name '[0-9][0-9]-*' | wc -l | tr -d ' ') + 1 ))
    DIR="$BASE/$(printf %02d "$NEXT")-${SERIES}"
  fi
  echo "📁 系列目录：$DIR"
fi
[[ -n "$DIR" ]] || { echo "用法: new_album.sh --ip <形象名> --series <系列名>   或   new_album.sh <目录> [--ip ...]" >&2; exit 2; }

S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$S")"
mkdir -p "$DIR"
COPY="$DIR/album.yml"

# ── 第 0 段：解析 --ip 是「库里的形象名」还是「一张正面照」────────
IP_NAME="" IP_PHOTO=""
if [[ -n "$IP" ]]; then
  if [[ -f "$IP" ]]; then
    IP_PHOTO="$IP"          # 直给照片：一次性用法，形象信息不入库
  else
    IP_NAME="$IP"
    IP_PHOTO="$STICKER_HOME/ips/$IP_NAME/ip.png"
    if [[ ! -f "$IP_PHOTO" ]]; then
      cat >&2 <<EOF
⚠️  IP 库里没有形象「${IP_NAME}」（找的是 ${IP_PHOTO}）

先注册，之后所有专辑都能复用这一个形象：
  python3 $S/ip.py add $IP_NAME <正面照路径> --desc "形象简介，≤80 字"

已注册的形象：$(python3 "$S/ip.py" list 2>/dev/null | grep -oE '^  [^ ]+' | tr -d ' ' | tr '\n' ' ' || true)
EOF
      exit 1
    fi
    echo "🎭 形象「${IP_NAME}」（来自 IP 库 ${STICKER_HOME}）"
  fi
fi

# ── 第 1 段：文案 ─────────────────────────────────────────────
if [[ ! -f "$COPY" ]]; then
  cp "$ROOT/templates/album.yml" "$COPY"
  # 库里有形象就把形象名/简介预填进去 —— 同一个 IP 的多套专辑，这两项必须一致
  if [[ -n "$IP_NAME" ]]; then
    python3 - "$COPY" "$STICKER_HOME/ips/$IP_NAME/ip.yml" <<'PY'
import re, sys
copy_path, ip_path = sys.argv[1], sys.argv[2]
ip = {}
for line in open(ip_path, encoding='utf-8'):
    if ':' in line and not line.startswith((' ', '#')):
        k, v = line.split(':', 1); ip[k.strip()] = v.strip()
s = open(copy_path, encoding='utf-8').read()
s = re.sub(r'^ip_name: \S+', 'ip_name: ' + ip.get('name', ''), s, count=1, flags=re.M)
if ip.get('desc'):
    s = re.sub(r'^ip_desc: .*$', 'ip_desc: ' + ip['desc'], s, count=1, flags=re.M)
open(copy_path, 'w', encoding='utf-8').write(s)
PY
    echo "✓ 已按形象「${IP_NAME}」预填 ip_name / ip_desc"
  fi
  cat <<EOF

已生成文案模板：$COPY

请先填这几项（字数上限已写在文件注释里）：$(if [[ -n "$IP_NAME" ]]; then echo "
  （ip_name / ip_desc 已按 IP 库预填，不用改）"; else echo "
  ip_name     形象名，≤8 字，须能对应到具体角色（不要用「治愈系日常」这种风格名）
  ip_desc     形象简介，≤80 字，三句式：它是谁 → 什么性格 → 在做什么"; fi)
  album_name  专辑名，≤8 字
  album_desc  专辑介绍，≤80 字
  meanings    含义词，每条 ≤4 字、同套不重复 —— 这是用户在表情面板里搜的词，不是画面台词
              条数就是要出的表情张数（8~24 张任意数量，默认 9 条）

写法与反面例子见：$ROOT/references/ip-design.md

填完再跑同一条命令即可继续。
EOF
  exit 0
fi

# 占位符特意用「待填」开头这种真实形象名不会撞的写法 ——
# 早先模板默认值直接写了某个真实 IP 名，结果那个 IP 真要投稿时被误判成「还没填」。
if grep -qE '^(ip_name|album_name): 待填' "$COPY"; then
  echo "⚠️  $COPY 还有「待填」字段，先把文案改完再跑。" >&2
  grep -nE ': 待填' "$COPY" | sed 's/^/    /' >&2
  exit 1
fi

COUNT=$(grep -cE '^[[:space:]]+- ' "$COPY" || true)
[[ "$COUNT" -ge 8 ]] || { echo "⚠️  含义词只有 $COUNT 条，官方要求 8~24 张，先在 $COPY 里补齐。" >&2; exit 1; }
echo "✓ 文案就绪：$COUNT 条含义词 → 出 $COUNT 张表情"

# 用了 IP 库就校验一致性：形象名写错会把作品挂到别的形象上，而改归属只有 1 次机会
if [[ -n "$IP_NAME" ]]; then
  COPY_IP=$(grep -m1 '^ip_name:' "$COPY" | sed 's/^ip_name:[[:space:]]*//; s/[[:space:]]*#.*//' || true)
  if [[ "$COPY_IP" != "$IP_NAME" ]]; then
    echo "⚠️  $COPY 里的 ip_name「${COPY_IP}」与 --ip「${IP_NAME}」不一致。" >&2
    echo "    形象挂错后只有 1 次改的机会，先改成一致再跑。" >&2
    exit 1
  fi
fi

# ── 第 2 段：原图 ─────────────────────────────────────────────
RAW="$DIR/raw"
mkdir -p "$RAW"
# 复用 IP 库里的读图 prompt：一个形象只读一次图，多套专辑风格才不会漂
if [[ -n "$IP_NAME" && -s "$STICKER_HOME/ips/$IP_NAME/ip-reverse.txt" && ! -s "$RAW/ip-reverse.txt" ]]; then
  cp "$STICKER_HOME/ips/$IP_NAME/ip-reverse.txt" "$RAW/ip-reverse.txt"
  echo "✓ 复用形象「${IP_NAME}」的读图 prompt（不再重复读图）"
fi
HAVE=$(find "$RAW" -maxdepth 1 -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' \) \
       ! -name 'banner-src.*' | wc -l | tr -d ' ')

if [[ "$HAVE" -lt 8 || "$FORCE_GEN" -eq 1 ]]; then
  if [[ -n "$IP_PHOTO" && -f "$IP_PHOTO" ]] && command -v museav >/dev/null; then
    ARGS=(--ip "$IP_PHOTO" --out "$DIR" --count "$COUNT")
    [[ -n "$EMOTIONS" ]] && ARGS+=(--emotions "$EMOTIONS")
    [[ -n "$STYLE" ]] && ARGS+=(--style "$STYLE")
    [[ "$FORCE_GEN" -eq 1 ]] && ARGS+=(--regen)
    echo "▶ 用 museav 出图（约 $((COUNT * 50 / 2 + 60)) 秒）..."
    "$S/gen_album.sh" "${ARGS[@]}"
  else
    reason="没给 --ip"
    [[ -n "$IP" ]] && ! command -v museav >/dev/null && reason="本机没有 museav 出图 CLI"
    cat >&2 <<EOF
⚠️  $RAW 里只有 $HAVE 张图，需要 $COUNT 张（${reason}）。

两条路，选一条：
  A. 自己画好/已有图 → 把 $COUNT 张原图放进 $RAW/（任意尺寸，命名随意，会按文件名排序）
     另可放一张 banner-src.png 作横幅底图；不放则跳过横幅，需自行准备 750×400。
  B. 用 museav 出图 → 装好 museav CLI 后加 --ip <IP正面照> 重跑本命令
EOF
    exit 1
  fi
fi

# ── 第 3 段：切图 ─────────────────────────────────────────────
FIRST=$(find "$RAW" -maxdepth 1 -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' \) \
        ! -name 'banner-src.*' | sort | head -1)
# 照片型专辑的表情图往往是白底的，不能拿来做封面/图标（那两项官方强制透明背景）。
# 用 --cover-from / --icon-from 指定单独抠好的透明图；没给就退回 raw 第一张。
# 形象已入库时，默认就用库里的形象头像/图标源，省得每次手填。
if [[ -z "$COVER_SRC" && -n "$IP_NAME" && -f "$STICKER_HOME/ips/$IP_NAME/ip.png" ]]; then
  COVER_SRC="$STICKER_HOME/ips/$IP_NAME/ip.png"
fi
[[ -n "$ICON_SRC" ]] || ICON_SRC="$COVER_SRC"
FIT=(--cover "${COVER_SRC:-$FIRST}" --icon "${ICON_SRC:-$FIRST}")
[[ -f "$RAW/banner-src.png" ]] && FIT+=(--banner "$RAW/banner-src.png")
echo "▶ 切图 → 240×240 / 50×50 / 750×400（按形象名与含义词中文命名）"
python3 "$S/fit_assets.py" "$RAW" "$DIR" --copy "$COPY" "${FIT[@]}"

# ── 第 4 段：机检 ─────────────────────────────────────────────
echo "▶ 机检"
set +e
python3 "$S/check_assets.py" "$DIR" --copy "$COPY"
FAILS=$?
set -e

if [[ "$FAILS" -ne 0 ]]; then
  cat >&2 <<EOF

还有 $FAILS 项必须修复，常见修法：
  透明背景不合规   → museav remove-bg <原图>，把抠好的图放回 $RAW/ 再跑本命令
  白色描边         → 抠图时关掉描边/羽化白边，或让出图 prompt 明确 "no white outline stroke"
  画面差异不足     → 换姿势和视角重出那两张（只改表情细节不算差异），--regen 可重出全套
  封面/图标想换图  → 换 $RAW/01.png，或直接跑 fit_assets.py --cover/--icon 指定别的图
  含义词条数不符   → 改 $COPY 的 meanings，条数必须等于表情张数
修完再跑同一条命令。
EOF
  exit "$FAILS"
fi

# ── 第 5 段：提交清单 + 回写形象归属 ──────────────────────────
python3 "$S/make_submit.py" "$DIR" --copy "$COPY"
if [[ -n "$IP_NAME" ]]; then
  python3 "$S/ip.py" link "$IP_NAME" "$DIR" || true
fi
cat <<EOF

✅ 全部就绪。打开 $DIR/submit.md，照着表格在平台逐项填写。
   平台入口：https://sticker.weixin.qq.com/cgi-bin/mmemoticonwebnode-bin/pages/home
EOF
if [[ -n "$IP_NAME" ]]; then
  echo "   形象头像/图标（形象主页用，与专辑封面是不同字段）："
  ls "$STICKER_HOME/ips/$IP_NAME" | grep -E '^形象' | sed "s|^|     $STICKER_HOME/ips/$IP_NAME/|" || true
fi
