#!/usr/bin/env bash
# 一张 IP 正面照 → 整套静态表情原图（museav 出图中台，透明背景 PNG）
#
#   gen_album.sh --ip ~/Desktop/mochi.png --out ~/Desktop/mochi-album
#   gen_album.sh --ip ip.png --out out/ --count 8 --emotions "开心,委屈,好困,生气,疑问,收到,拜托,无语"
#   gen_album.sh --ip ip.png --out out/ --banner-only        # 只补出横幅底图
#
# 出的是原始大图（out/raw/），下一步必须过 fit_assets.py 切成 240/50 合规尺寸。
set -euo pipefail

IP="" OUT="" COUNT=9 STYLE="" BANNER_ONLY=0 JOBS=3
EMOTIONS="开心大笑,委屈流泪,好困打哈欠,生气跺脚,疑问歪头,收到点头,拜托合手,无语摊手,害羞捂脸"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ip) IP="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --count) COUNT="$2"; shift 2 ;;
    --emotions) EMOTIONS="$2"; shift 2 ;;
    --style) STYLE="$2"; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --banner-only) BANNER_ONLY=1; shift ;;
    *) echo "未知参数 $1" >&2; exit 2 ;;
  esac
done
[[ -f "$IP" && -n "$OUT" ]] || { echo "用法: gen_album.sh --ip <正面照> --out <目录>" >&2; exit 2; }

RAW="$OUT/raw"; mkdir -p "$RAW"
command -v museav >/dev/null || { echo "缺 museav CLI（出图中台入口）" >&2; exit 1; }

# 1) 读图逆向：把 IP 的外形特征固化成英文 prompt，这是整套风格一致的锚
BASE="$OUT/ip-prompt.txt"
if [[ ! -s "$BASE" ]]; then
  echo "▶ 读图逆向 IP 特征 ..."
  museav reverse "$IP" > "$BASE"
fi
IP_DESC="$(tr '\n' ' ' < "$BASE" | cut -c1-600)"
echo "IP 特征: ${IP_DESC:0:120}..."

# 出图硬约束：官方要求透明背景、无白描边、无方框、无文字、主体居中不留白
GUARD="chibi sticker of the SAME character, full body centered, single clear emotion,\
 clean flat colors, crisp anti-aliased edges, NO white outline stroke, NO square frame or border,\
 NO text NO watermark, transparent background, subject fills most of the canvas, minimal empty margin"

gen() {  # gen <序号> <情绪>
  local idx="$1" emo="$2" url
  url=$(museav gen --ref "$IP" --transparent -r 1:1 \
        -p "$IP_DESC. $GUARD. emotion: ${emo}. ${STYLE}" 2>/dev/null | grep -oE 'https://[^ ]+\.(png|jpg|jpeg|webp)' | tail -1)
  if [[ -z "$url" ]]; then echo "  ✗ $(printf %02d "$idx") $emo 出图失败" >&2; return 0; fi
  curl -sL -o "$RAW/$(printf %02d "$idx").png" "$url"
  echo "  ✓ $(printf %02d "$idx") $emo → raw/$(printf %02d "$idx").png"
}

if [[ $BANNER_ONLY -eq 0 ]]; then
  echo "▶ 出 $COUNT 张表情原图（并发 $JOBS，单张约 50s）..."
  i=0
  IFS=',' read -ra LIST <<< "$EMOTIONS"
  for emo in "${LIST[@]}"; do
    (( i++ )); (( i > COUNT )) && break
    gen "$i" "$emo" &
    (( $(jobs -rp | wc -l) >= JOBS )) && wait -n
  done
  wait
fi

# 2) 横幅底图：不透明、有场景、无文字 —— 与表情图的要求正好相反，必须单独出
echo "▶ 出详情页横幅底图（16:9，不透明）..."
BURL=$(museav gen --ref "$IP" -r 16:9 \
  -p "$IP_DESC. Wide banner illustration, the SAME character in a lively scene,\
 rich colorful background clearly different from white, NO text NO watermark,\
 no stretched or squashed elements, storytelling composition" 2>/dev/null \
  | grep -oE 'https://[^ ]+\.(png|jpg|jpeg|webp)' | tail -1)
[[ -n "$BURL" ]] && curl -sL -o "$RAW/banner-src.png" "$BURL" && echo "  ✓ raw/banner-src.png"

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat <<EOF

原图已就位：$RAW
下一步（切图 → 机检）：
  python3 $SKILL_DIR/fit_assets.py $RAW $OUT --cover $RAW/01.png --icon $RAW/01.png --banner $RAW/banner-src.png
  python3 $SKILL_DIR/check_assets.py $OUT --copy $OUT/album.yml
EOF
