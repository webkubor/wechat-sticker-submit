#!/usr/bin/env bash
# 一张 IP 正面照 → 整套静态表情原图（museav 出图中台，透明背景 PNG）
#
#   gen_album.sh --ip ~/Desktop/mochi.png --out ~/Desktop/mochi-album
#   gen_album.sh --ip ip.png --out out/ --count 8 --emotions "开心,委屈,好困,生气,疑问,收到,拜托,无语"
#   gen_album.sh --ip ip.png --out out/ --banner-only        # 只补出横幅底图
#
# 出的是原始大图（out/raw/），下一步必须过 fit_assets.py 切成 240/50 合规尺寸。
set -euo pipefail

IP="" OUT="" COUNT=9 STYLE="" BANNER_ONLY=0 JOBS=3 REGEN=0
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
    --regen) REGEN=1; shift ;;
    *) echo "未知参数 $1" >&2; exit 2 ;;
  esac
done
[[ -f "$IP" && -n "$OUT" ]] || { echo "用法: gen_album.sh --ip <正面照> --out <目录>" >&2; exit 2; }

RAW="$OUT/raw"; mkdir -p "$RAW"
command -v museav >/dev/null || { echo "缺 museav CLI（出图中台入口）" >&2; exit 1; }

# 1) 读图逆向：把 IP 的外形特征固化成英文 prompt，这是整套风格一致的锚
BASE="$RAW/ip-reverse.txt"   # 留档区，与产物区分开
if [[ ! -s "$BASE" ]]; then
  echo "▶ 读图逆向 IP 特征 ..."
  museav reverse "$IP" > "$BASE"
fi

# museav reverse 的 stdout 就是纯英文 prompt（终端上那份 SCULPT 报告走 stderr）。
# 万一将来改成报告格式，兼容取「英文 prompt:」的下一行。
if grep -q '^英文 prompt:' "$BASE" 2>/dev/null; then
  IP_DESC="$(awk '/^英文 prompt:/{getline; gsub(/^[[:space:]]+/,""); print; exit}' "$BASE")"
else
  IP_DESC="$(tr '\n' ' ' < "$BASE" | cut -c1-600)"
fi
[[ -n "${IP_DESC// /}" ]] || { echo "读图没拿到可用的 prompt，检查 $BASE" >&2; exit 1; }

# 垫图是透明 PNG 时，读图常把透明区读成 "against a black background" ——
# 这句会让出图带实底，与「须透明背景」直接冲突，必须剥掉。
IP_DESC="$(sed -E 's/,?[[:space:]]*([Aa]gainst|[Oo]n)[[:space:]]+a[[:space:]]+[A-Za-z ]*[Bb]ackground[A-Za-z ]*//g' <<< "$IP_DESC")"
echo "IP 特征: $IP_DESC"

# 出图硬约束：官方要求透明背景、无白描边、无方框、无文字、主体居中不留白
GUARD="chibi sticker of the SAME character, full body centered, single clear emotion,\
 clean flat colors, crisp anti-aliased edges, NO white outline stroke, NO square frame or border,\
 NO text NO watermark, transparent background, subject fills most of the canvas, minimal empty margin"

gen() {  # gen <序号> <情绪>
  local idx="$1" emo="$2" url n
  local tag; tag=$(printf %02d "$idx")
  # 已出过就跳过：重跑只补失败的那几张，不重复烧 credits（--regen 强制重出）
  if [[ -f "$RAW/$tag.png" && $REGEN -eq 0 ]]; then
    echo "  ↷ $tag $emo 已存在，跳过"
    return 0
  fi
  # 出图偶发失败（上游超时/审核拦截），重试一次 —— 少一张就会卡在「张数不足」上
  for n in 1 2; do
    url=$(museav gen --ref "$IP" --transparent -r 1:1 \
          -p "$IP_DESC. $GUARD. emotion: ${emo}. ${STYLE}" 2>/dev/null \
          | grep -oE 'https://[^ ]+\.(png|jpg|jpeg|webp)' | tail -1)
    if [[ -n "$url" ]]; then
      curl -sL -o "$RAW/$tag.png" "$url"
      echo "  ✓ $tag $emo → raw/$tag.png$([[ $n -eq 2 ]] && echo '（重试后成功）')"
      return 0
    fi
    [[ $n -eq 1 ]] && echo "  … $tag $emo 出图失败，重试" >&2
  done
  echo "  ✗ $tag $emo 两次都失败 —— 张数会不足，补一张放进 raw/$tag.png 或重跑 --regen" >&2
}

if [[ $BANNER_ONLY -eq 0 ]]; then
  # 变量后紧跟中文标点必须写 ${VAR}：全角字符的 UTF-8 字节会被 bash 吞进变量名
  echo "▶ 出 $COUNT 张表情原图（并发 ${JOBS}，单张约 50s）..."
  i=0
  IFS=',' read -ra LIST <<< "$EMOTIONS"
  for emo in "${LIST[@]}"; do
    i=$((i + 1))
    if (( i > COUNT )); then break; fi
    gen "$i" "$emo" &
    # 分批 wait 而不是 wait -n：wait -n 要 bash 4.3+，macOS 自带的是 3.2。
    # 条件判断一律写在 if 里 —— set -e 下裸 (( expr )) 为假会返回 1 并终止整个脚本。
    if (( i % JOBS == 0 )); then wait; fi
  done
  wait
fi

# 2) 横幅底图：不透明、有场景、无文字 —— 与表情图的要求正好相反，必须单独出
if [[ -f "$RAW/banner-src.png" && $REGEN -eq 0 ]]; then
  echo "▶ 横幅底图已存在，跳过"
else
  echo "▶ 出详情页横幅底图（16:9，不透明）..."
  BURL=$(museav gen --ref "$IP" -r 16:9 \
    -p "$IP_DESC. Wide banner illustration, the SAME character in a lively scene,\
 rich colorful background clearly different from white, NO text NO watermark,\
 no stretched or squashed elements, storytelling composition" 2>/dev/null \
    | grep -oE 'https://[^ ]+\.(png|jpg|jpeg|webp)' | tail -1)
  if [[ -n "$BURL" ]]; then
    curl -sL -o "$RAW/banner-src.png" "$BURL"
    echo "  ✓ raw/banner-src.png"
  else
    echo "  ✗ 横幅底图出图失败 —— 自备一张放到 $RAW/banner-src.png" >&2
  fi
fi

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat <<EOF

原图已就位：$RAW
下一步（切图 → 机检）：
  python3 $SKILL_DIR/fit_assets.py $RAW $OUT --cover $RAW/01.png --icon $RAW/01.png --banner $RAW/banner-src.png
  python3 $SKILL_DIR/check_assets.py $OUT --copy $OUT/album.yml
EOF
