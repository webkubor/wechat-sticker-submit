#!/usr/bin/env bash
# 一张 IP 正面照 → 整套静态表情原图（museav 出图中台，透明背景 PNG）
#
#   gen_album.sh --ip ~/Desktop/mochi.png --out ~/Desktop/mochi-album
#   gen_album.sh --ip ip.png --out out/ --count 8 --emotions "开心,委屈,好困,生气,疑问,收到,拜托,无语"
#   gen_album.sh --ip ip.png --out out/ --banner-only        # 只补出横幅底图
#
# 出的是原始大图（out/raw/），下一步必须过 fit_assets.py 切成 240/50 合规尺寸。
set -euo pipefail

# JOBS 默认 2：并发 3 连跑几轮会撞上游频次限制（「出图太频繁了」），
# 2 路 + 失败退避比 3 路更快跑完一整套
IP="" OUT="" COUNT=9 STYLE="" BANNER_ONLY=0 JOBS=2 REGEN=0
# 情绪里带上姿势/视角差异（站/侧/躺/只露头），否则垫图会让 8 张全是同一个正面坐姿 ——
# 形象一致是好事，构图一致就是「整套差异不足」的高发区
EMOTIONS="开心大笑并举起双手,委屈流泪侧身低头,好困打哈欠躺着伸懒腰,生气跺脚站立,疑问歪头只露上半身特写,收到点头站直敬礼,拜托合手跪坐仰视,无语摊手背对回头,害羞捂脸蹲下"

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

# 垫图是透明 PNG 时，读图常把透明区读成 "against a black background" /
# "in front of a black background" —— 这句会让出图带实底，与「须透明背景」冲突，必须剥掉。
# 不枚举介词（against/on/in front of/over… 永远列不全），直接按逗号分段丢掉含 background 的子句。
IP_DESC="$(awk -v RS=',' 'BEGIN{sep=""} tolower($0) !~ /background/ {
  gsub(/^[[:space:]]+|[[:space:]]+$/, ""); if ($0 != "") { printf "%s%s", sep, $0; sep=", " }
}' <<< "$IP_DESC")"
echo "IP 特征: $IP_DESC"

# 出图硬约束：官方要求透明背景、无白描边、无方框、无文字、主体居中不留白
GUARD="chibi sticker of the SAME character, full body centered, single clear emotion,\
 clean flat colors, crisp anti-aliased edges, NO white outline stroke, NO square frame or border,\
 NO text NO watermark, transparent background, subject fills most of the canvas, minimal empty margin"

gen() {  # gen <序号> <情绪>
  local idx="$1" emo="$2" url n out err wait
  local tag; tag=$(printf %02d "$idx")
  # 已出过就跳过：重跑只补失败的那几张，不重复烧 credits（--regen 强制重出）
  if [[ -f "$RAW/$tag.png" && $REGEN -eq 0 ]]; then
    echo "  ↷ $tag $emo 已存在，跳过"
    return 0
  fi
  # 失败要分两类：上游限流（退避后必然能成）与真错误（重试无用，得看原文）。
  # 所以合并 stderr 而不是 2>/dev/null —— 丢掉上游错误信息会让人误判成 prompt 有问题。
  for n in 1 2 3; do
    # `|| true` 不可省：出图失败时 museav 以非零码退出，而它是命令替换里唯一的命令，
    # 于是命令替换本身返回非零 → set -e 静默杀掉这个子 shell，下面的错误分支永远跑不到。
    # （旧版把 museav 放在管道里，退出码取自末尾的 tail 才碰巧没暴露这个问题。）
    out=$(museav gen --ref "$IP" --transparent -r 1:1 \
          -p "$IP_DESC. $GUARD. emotion: ${emo}. ${STYLE}" 2>&1 || true)
    # 排除 /refs/ ——那是垫图的上传地址，失败时它仍在输出里，会被误当成出图结果
    # `|| true` 同样不可省：pipefail 下 grep -v 过滤光全部输入会返回 1，管道即非零
    url=$(grep -oE 'https://[^ ]+\.(png|jpg|jpeg|webp)' <<< "$out" | grep -v '/refs/' | tail -1 || true)
    if [[ -n "$url" ]]; then
      curl -sL -o "$RAW/$tag.png" "$url"
      echo "  ✓ $tag $emo → raw/$tag.png$([[ $n -gt 1 ]] && echo "（第 $n 次成功）")"
      return 0
    fi
    err=$(grep -oE '❌.*' <<< "$out" | head -1 || true)
    if grep -qiE '频繁|rate.?limit|429|too many|quota' <<< "$out"; then
      wait=$((n * 45))
      echo "  ⏳ $tag $emo 被上游限流，等 ${wait}s 再试（$n/3）" >&2
      sleep "$wait"
    else
      echo "  … $tag $emo 失败（$n/3）：${err:-上游未返回图片地址}" >&2
      if [[ $n -lt 3 ]]; then sleep 5; fi
    fi
  done
  echo "  ✗ $tag $emo 三次都失败：${err:-未知错误}" >&2
  echo "    → 补一张放进 raw/$tag.png，或稍后重跑同一条命令（只会补缺失的）" >&2
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
  BOUT=$(museav gen --ref "$IP" -r 16:9 \
    -p "$IP_DESC. Wide banner illustration, the SAME character in a lively scene,\
 rich colorful background clearly different from white, NO text NO watermark,\
 no stretched or squashed elements, storytelling composition" 2>&1 || true)
  BURL=$(grep -oE 'https://[^ ]+\.(png|jpg|jpeg|webp)' <<< "$BOUT" | grep -v '/refs/' | tail -1 || true)
  if [[ -n "$BURL" ]]; then
    curl -sL -o "$RAW/banner-src.png" "$BURL"
    echo "  ✓ raw/banner-src.png"
  else
    echo "  ✗ 横幅底图失败：$(grep -oE '❌.*' <<< "$BOUT" | head -1 || true)" >&2
    echo "    → 自备一张放到 $RAW/banner-src.png，或稍后重跑" >&2
  fi
fi

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat <<EOF

原图已就位：$RAW
下一步（切图 → 机检 → 提交清单）：
  python3 $SKILL_DIR/fit_assets.py $RAW $OUT --copy $OUT/album.yml --cover $RAW/01.png --icon $RAW/01.png --banner $RAW/banner-src.png
  python3 $SKILL_DIR/check_assets.py $OUT --copy $OUT/album.yml
  python3 $SKILL_DIR/make_submit.py $OUT --copy $OUT/album.yml
EOF
