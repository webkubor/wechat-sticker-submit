#!/usr/bin/env bash
# 一键跑完整套静态表情：填文案 → 出图 → 切图 → 机检 → 提交清单
#
#   new_album.sh ~/Desktop/my-album --ip ~/Desktop/ip.png
#   new_album.sh ~/Desktop/my-album              # 自己画好图放进 my-album/raw/ 也行
#
# 幂等：同一条命令可以反复跑。第一次跑生成 album.yml 就停下让你填文案，
# 填完再跑同一条命令，它会自动接着往下走；中途失败修完再跑，不会重做已完成的部分。
set -euo pipefail

DIR="" IP="" EMOTIONS="" STYLE="" FORCE_GEN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ip) IP="$2"; shift 2 ;;
    --emotions) EMOTIONS="$2"; shift 2 ;;
    --style) STYLE="$2"; shift 2 ;;
    --regen) FORCE_GEN=1; shift ;;
    -*) echo "未知参数 $1" >&2; exit 2 ;;
    *) DIR="$1"; shift ;;
  esac
done
[[ -n "$DIR" ]] || { echo "用法: new_album.sh <目录> [--ip <IP正面照>]" >&2; exit 2; }

S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$S")"
mkdir -p "$DIR"
COPY="$DIR/album.yml"

# ── 第 1 段：文案 ─────────────────────────────────────────────
if [[ ! -f "$COPY" ]]; then
  cp "$ROOT/templates/album.yml" "$COPY"
  cat <<EOF

已生成文案模板：$COPY

请先填这 5 项（字数上限已写在文件注释里）：
  ip_name     形象名，≤8 字，须能对应到具体角色（不要用「治愈系日常」这种风格名）
  ip_desc     形象简介，≤80 字，三句式：它是谁 → 什么性格 → 在做什么
  album_name  专辑名，≤8 字
  album_desc  专辑介绍，≤80 字
  meanings    含义词，每条 ≤4 字、同套不重复 —— 这是用户在表情面板里搜的词，不是画面台词
              条数就是要出的表情张数（8~24 张任意数量，默认 9 条）

写法与反面例子见：$ROOT/references/ip-design.md

填完再跑同一条命令即可继续。
EOF
  exit 0
fi

if grep -q '^ip_name: 莓啾' "$COPY"; then
  echo "⚠️  $COPY 还是模板默认值，先把文案改成你自己的形象再跑。" >&2
  exit 1
fi

COUNT=$(grep -cE '^[[:space:]]+- ' "$COPY" || true)
[[ "$COUNT" -ge 8 ]] || { echo "⚠️  含义词只有 $COUNT 条，官方要求 8~24 张，先在 $COPY 里补齐。" >&2; exit 1; }
echo "✓ 文案就绪：$COUNT 条含义词 → 出 $COUNT 张表情"

# ── 第 2 段：原图 ─────────────────────────────────────────────
RAW="$DIR/raw"
mkdir -p "$RAW"
HAVE=$(find "$RAW" -maxdepth 1 -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' \) \
       ! -name 'banner-src.*' | wc -l | tr -d ' ')

if [[ "$HAVE" -lt 8 || "$FORCE_GEN" -eq 1 ]]; then
  if [[ -n "$IP" && -f "$IP" ]] && command -v museav >/dev/null; then
    ARGS=(--ip "$IP" --out "$DIR" --count "$COUNT")
    [[ -n "$EMOTIONS" ]] && ARGS+=(--emotions "$EMOTIONS")
    [[ -n "$STYLE" ]] && ARGS+=(--style "$STYLE")
    echo "▶ 用 museav 出图（约 $((COUNT * 50 / 3 + 60)) 秒）..."
    "$S/gen_album.sh" "${ARGS[@]}"
  else
    reason="没给 --ip"
    [[ -n "$IP" ]] && ! command -v museav >/dev/null && reason="本机没有 museav 出图 CLI"
    cat >&2 <<EOF
⚠️  $RAW 里只有 $HAVE 张图，需要 $COUNT 张（$reason）。

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
FIT=(--cover "$FIRST" --icon "$FIRST")
[[ -f "$RAW/banner-src.png" ]] && FIT+=(--banner "$RAW/banner-src.png")
echo "▶ 切图 → 240×240 / 50×50 / 750×400"
python3 "$S/fit_assets.py" "$RAW" "$DIR" "${FIT[@]}"

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

# ── 第 5 段：提交清单 ─────────────────────────────────────────
python3 "$S/make_submit.py" "$DIR" --copy "$COPY"
cat <<EOF

✅ 全部就绪。打开 $DIR/submit.md，照着表格在平台逐项填写。
   平台入口：https://sticker.weixin.qq.com/
EOF
