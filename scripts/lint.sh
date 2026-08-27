#!/usr/bin/env bash
# 脚本自检门禁 —— 改完脚本先跑这个，再跑真流程
#
#   lint.sh
#
# 检的都是 references/pitfalls.md 里真踩过的坑。写进文档拦不住重犯，
# 做成能跑的检查才拦得住 —— 第 1 条我在写完文档之后又犯了一次，所以有了这个脚本。
set -uo pipefail

S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$S"
FAIL=0
# 只检业务脚本，不检门禁自身（它的提示文本里就带着这些反面写法）
TARGETS="gen_album.sh new_album.sh"

say() { printf '%s %s\n' "$1" "$2"; }

# 1) 变量名紧跟全角标点 → 标点字节被吞进变量名，set -u 报 unbound variable
hits=$(grep -nP '\$\{?[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7F]' $TARGETS 2>/dev/null | grep -v '${' || true)
if [[ -n "$hits" ]]; then
  say "❌" "变量名后紧跟全角标点，须写 \${VAR}："
  echo "$hits" | sed 's/^/     /'
  FAIL=$((FAIL + 1))
else
  say "✅" "变量与全角标点边界"
fi

# 2) 独立的 (( i++ )) → i=0 时返回 1，set -e 静默终止脚本
hits=$(grep -nE '^[[:space:]]*\(\([^)]*\+\+[^)]*\)\)[[:space:]]*$' $TARGETS 2>/dev/null || true)
if [[ -n "$hits" ]]; then
  say "❌" "独立的 (( i++ )) 在 i=0 时会终止脚本，改 i=\$((i + 1))："
  echo "$hits" | sed 's/^/     /'
  FAIL=$((FAIL + 1))
else
  say "✅" "算术自增写法"
fi

# 3) wait -n 需要 bash 4.3+，macOS 自带 3.2
hits=$(grep -n 'wait -n' $TARGETS 2>/dev/null | grep -vE '#|say ' || true)
if [[ -n "$hits" ]]; then
  say "❌" "wait -n 需 bash 4.3+（macOS 是 3.2），改分批 wait："
  echo "$hits" | sed 's/^/     /'
  FAIL=$((FAIL + 1))
else
  say "✅" "并发等待兼容性"
fi

# 4) 命令替换里只有一个外部命令且没 || true → 它失败就带走整个子 shell
hits=$(grep -nE '^[[:space:]]*[A-Za-z_]+=\$\((museav|curl|gh|glab|cs) [^|]*\)[[:space:]]*$' $TARGETS 2>/dev/null | grep -vE '\|\| *true' || true)
if [[ -n "$hits" ]]; then
  say "❌" "命令替换缺 || true，命令失败会被 set -e 静默带走："
  echo "$hits" | sed 's/^/     /'
  FAIL=$((FAIL + 1))
else
  say "✅" "命令替换的失败兜底"
fi

# 5) pipefail 下含 grep 的管道赋值缺 || true → 无匹配即整个管道失败
hits=$(grep -nE '^[[:space:]]*[A-Za-z_]+=\$\(.*\| *grep [^)]*\)[[:space:]]*$' $TARGETS 2>/dev/null | grep -vE '\|\| *true' || true)
if [[ -n "$hits" ]]; then
  say "❌" "pipefail 下 grep 无匹配会让管道失败，赋值需 || true："
  echo "$hits" | sed 's/^/     /'
  FAIL=$((FAIL + 1))
else
  say "✅" "pipefail 下的 grep 管道"
fi

# 6) 2>/dev/null 吞掉外部命令的错误原文 → 排障时看不到根因
hits=$(grep -nE '(museav|curl|gh|glab) [^|]*2>/dev/null' $TARGETS 2>/dev/null || true)
if [[ -n "$hits" ]]; then
  say "❌" "别静音外部命令的 stderr，改 2>&1 后提取原文："
  echo "$hits" | sed 's/^/     /'
  FAIL=$((FAIL + 1))
else
  say "✅" "外部命令的错误可见性"
fi

# 7) 数据分层：不允许在数据根下随手新建旁挂目录
# 加这条的原因：新增能力时容易「就近落盘」——加推广文案就建 captions/、
# 加平台状态就写 ip.yml，每一步单看都合理，攒起来就是配置散落一地。
# 约定：形象级 → ips/<形象>/；系列级 → albums/<形象>/<系列>/album.yml；
#       全局依赖 → 白名单里的那几个。新增位置要先改这里的白名单。
H="${STICKER_HOME:-$HOME/.wechat-stickers}"
if [[ -d "$H" ]]; then
  ALLOW="ips albums outbox bgm"
  stray=""
  for d in "$H"/*/; do
    n=$(basename "$d")
    [[ " $ALLOW " == *" $n "* ]] || stray="$stray $n"
  done
  if [[ -n "$stray" ]]; then
    say "❌" "数据根下有未登记的目录：$stray"
    echo "     形象级配置进 ips/<形象>/，系列级配置进 albums/<形象>/<系列>/album.yml，" 
    echo "     确实是全局依赖才加进 lint.sh 的 ALLOW 白名单"
    FAIL=$((FAIL + 1))
  else
    say "✅" "数据分层无旁挂目录"
  fi
fi

# 8) 语法
for f in ./*.sh; do
  bash -n "$f" || { say "❌" "$f 语法错误"; FAIL=$((FAIL + 1)); }
done
python3 - <<'PY' || FAIL=$((FAIL + 1))
import ast, glob, sys
bad = []
for f in glob.glob('*.py'):
    try:
        ast.parse(open(f, encoding='utf-8').read())
    except SyntaxError as e:
        bad.append(f'{f}:{e.lineno} {e.msg}')
if bad:
    print('❌ Python 语法错误：'); [print('    ' + b) for b in bad]; sys.exit(1)
print('✅ 全部脚本语法')
PY

echo
if [[ "$FAIL" -eq 0 ]]; then
  echo "门禁通过。"
else
  echo "$FAIL 项待修（每条对应 references/pitfalls.md 里的一次真实翻车）。"
fi
exit "$FAIL"
