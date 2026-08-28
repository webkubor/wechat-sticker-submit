# wechat-sticker-submit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-d97757)](https://claude.com/claude-code)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Deps: Pillow only](https://img.shields.io/badge/Deps-Pillow%20only-2ea44f)](https://python-pillow.org/)
[![静态 + 动态](https://img.shields.io/badge/%E9%9D%99%E6%80%81-%E5%B7%B2%E6%94%B6%E6%95%9B-2ea44f)](references/animated.md)
[![官方规范同步](https://img.shields.io/badge/%E5%AE%98%E6%96%B9%E8%A7%84%E8%8C%83%E5%90%8C%E6%AD%A5-2026--08--27-orange)](https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications)
[![Stars](https://img.shields.io/github/stars/webkubor/wechat-sticker-submit?style=flat&color=yellow)](https://github.com/webkubor/wechat-sticker-submit/stargazers)
[![出片: reel-kit](https://img.shields.io/badge/%E5%87%BA%E7%89%87-reel--kit-8b5cf6)](https://github.com/webkubor/reel-kit)
[![版本](https://img.shields.io/badge/version-1.3.0-blue)](CHANGELOG.md)

**一张 IP 正面照，出一整套能直接提交的微信表情素材。**

微信表情开放平台的投稿门槛不在画功，在规格：240×240 的表情图、750×400 的横幅、
必须透明背景的封面与图标、每张 ≤4 字且不许重复的含义词……
而超规格的素材平台**不拒收、不报错，直接压缩裁剪** —— 主体被裁掉才发现就白做了。

这是一个 [Claude Code](https://claude.com/claude-code) skill：形象管理、出图、切图、机检、
文案校验、提交清单全部脚本化，零美术基础也能跑完。上架之后还能一条命令把整套串成
1080×1920 竖版推广视频发朋友圈 / 视频号 —— 合成委托 [reel-kit](https://github.com/webkubor/reel-kit)，
本 skill 只负责读 `album.yml` 拼参数，出片和排版的事不在这里重造。

**规范与拒因都是实测的，不是抄文档**：官方规范全文抓取归档，登录后的真实 URL 与提交表单
逐字段记录，还有一条真实驳回记录（画面里写「微信」二字会被判推广非自有版权的应用程序）——
这些在官方文档里读不到。

## 产物演示

一整套真跑出来的 —— 输入只有一张正面照，一条命令产出表情图 + 封面 + 图标 + 横幅，机检 FAIL 0：

![表情图 8 张](https://img.webkubor.online/skills/wechat-sticker-demo-stickers.jpg)

文件名自带含义词（`01-开心.png`、`02-委屈.png`…），编号即上传顺序，不用回头对映射表。

![封面图与聊天图标与详情页横幅](https://img.webkubor.online/skills/wechat-sticker-demo-assets.jpg)

三件套的要求彼此矛盾，所以流水线分开处理：封面用正面半身像 + 透明背景，
图标用头部特写 + 透明背景，横幅要不透明、有场景、画面内不得有文字。

### 照片型表情 → 透明贴纸

不透明的白底照片发到微信就是一个白方块，深色模式下边缘生硬。抠图 + 重绘文字之后：

![照片转贴纸前后对比](https://img.webkubor.online/skills/wechat-sticker-demo-restyle.jpg)

关键是**顺序：先擦字再抠图**。反过来的话，压在主体身上的文字会随主体保留，
和重绘的新文字叠在一起 —— 抠图按「主体/背景」二分，文字归哪边取决于它压在什么上面，不可控。

### 推广视频（1080×1920 竖版）

一条命令把整套表情串成朋友圈 / 视频号能发的竖版视频，版式对齐官方秒剪模板：

```bash
scripts/make_promo.py <系列目录>                    # 配乐默认「儿童轻快」
scripts/make_promo.py <系列目录> --sec 1.8          # 张数多时压缩每张停留
scripts/make_promo.py <系列目录> --voice narrator   # 加配音，镜长由念白决定
```

文案的真源是 `album.yml` 的 `captions` 段，写「什么时候发这张」而不是重复画面文字，
传播力更强。配乐走配乐库别名（`reel bgm` 看清单），出片时会打印授权。

出视频的能力在 **[reel-kit](https://github.com/webkubor/reel-kit)**（`reel` 命令），
这个脚本只负责读 `album.yml` 拼参数。要改版式就去改 reel-kit 的 `templates/*.html`，
丢一个 HTML 进去就是一个新版式，不用改代码。

> 前置：`cd ~/dev/github/devtool/reel-kit && pnpm install && npm link`（需 ffmpeg + Chrome）
>
> **`museav slideshow` 已下线**。2026-08-28 曾在 museav-cli 里做过一个，
> 后来发现 reel-kit 早就做了同一件事且更好（HTML/CSS 排版能换行、支持配音驱动镜长、
> 本地 TTS 零成本），已收敛到一处。

### 动态表情（透明 GIF）

240×240 / 20 帧 / 465KB / 循环，深浅底都不出白边：

![动图关键帧](https://img.webkubor.online/skills/wechat-sticker-demo-gif.jpg)

GIF 只有 1-bit 透明（每像素要么全透明要么全不透明），半透明像素必须二选一。
方案取阈值 128 + 主体腐蚀 1px，思路来自 [hackerb9/mktrans](https://github.com/hackerb9/mktrans)。
**别用 PS 教程常说的「杂边设为白色」** —— 浅色模式干净，深色模式每张镶白边。
详见 [`references/animated.md`](references/animated.md)。

## 它替你解决什么

| 你会踩的坑 | skill 怎么拦 |
|---|---|
| 素材超尺寸被平台静默裁掉 | 切图流水线统一归一到规格尺寸并压到体积上限 |
| 封面/图标忘了透明背景 | 机检对封面/图标判 FAIL，表情图判 WARN，横幅反过来 |
| 「四角透明」当成抠过图 | 切图留的几像素透明边会骗过四角检测 → 改判主体外接框是否「实心矩形」 |
| 主体一圈白描边 | 比对「轮廓 vs 主体内部」亮度 —— 白猫这类白色系角色不会误报 |
| 整套画面差异不足（**第一大拒因**） | 裁到主体后算差分哈希两两比对，太像就 FAIL |
| 不同专辑用了同一张封面/图标 | 跨专辑差分哈希比对（官方明文禁止） |
| 把台词当含义词（「555…我没事」） | 校验 ≤4 字、无标点、同套不重复、条数与张数一一对应 |
| 图标裁成方块、四角发硬 | 自动取头部正面并留 12% 边 |
| 竖构图素材居中裁切掉主体 | `--anchor top/center/bottom`；赞赏引导图必须 top（下半部会叠加金额 UI） |
| 出图偶发失败导致张数不足 | 单张重试；上游限流识别 + 三级退避；重跑只补缺失的 |
| 多个 IP 混着做，简介/头像串了 | IP 库分层存放；形象名重复、不同形象同头像都会被拒 |
| 作品挂错表情形象 | `album.yml` 的 ip_name 与 `--ip` 不一致直接拦下（改归属只有 1 次机会） |
| 形象母版只存在本地，丢了合集就断 | `ip.py sync` 推私有仓库版本化，换机 clone 即恢复 |
| **画面里写「微信」二字** | 机检拦不住 —— 这条只能靠人眼，已写进红线清单 |

## 安装

```bash
git clone https://github.com/webkubor/wechat-sticker-submit.git \
  ~/.claude/skills/wechat-sticker-submit
```

装完在 Claude Code 里说「帮我做一套微信表情」即可触发；也可以只当命令行工具用。

> ⚠️ 必须 clone 到 `~/.claude/skills/` 下的**真目录**。Claude Code
> **不跟随 symlink 加载 skill** —— 把真目录放别处、这里放软链会导致 skill 直接消失。

## 数据模型：形象唯一，系列多套

微信那边是两个独立配置，且一对多：

```
表情形象（唯一）                表情系列 / 专辑（多套）
名称·简介·头像·图标  ──┬── 系列 A：表情图 8~24 张 + 封面 + 横幅 + 含义词
                      ├── 系列 B：另一套，复用同一个形象
                      └── 系列 C：…
```

本地照这个分层，**并按「能不能再生」决定是否进版本库**：

```
~/.wechat-stickers/                        ← 数据唯一根（git 私有仓库）
├── ips/<形象>/                            不可再生 → 版本化
│   ├── ip.yml · ip.png · ip-reverse.txt
│   ├── 形象头像-<名>.png · 形象图标-<名>.png
│   └── source/                            原始画稿池，多套系列从这里挑图
├── albums/<形象>/<NN-系列名>/               产物，可再生 → gitignore
│   ├── 表情图/ · 封面 · 图标 · 横幅
│   └── album.yml · submit.md · raw/
└── outbox/                                待上传中转 → gitignore
```

反过来只备份产物的话，真正贵的东西（画不回来的原稿）反而没保住。
`STICKER_HOME` / `STICKER_ALBUMS` 可覆盖位置。

## IP 库

```bash
S=~/.claude/skills/wechat-sticker-submit/scripts

python3 $S/ip.py add 团子 正面照.png --desc "简介，≤80 字" --source 画稿目录/
python3 $S/ip.py list                    # 所有形象 + 系列 + 完善进度
python3 $S/ip.py show 团子                # 逐项核对 + 待办 + 已挂系列
python3 $S/ip.py page                    # 生成 HTML 进度面板并打开
python3 $S/ip.py rename 团子 团团          # 改名（同步目录/文件名/album.yml）
python3 $S/ip.py update 团子 --photo 新正面照.png   # 换母版并重做头像图标
python3 $S/ip.py sync                    # 备份到私有仓库（首次自动建仓）
```

`show` 逐项核对官方对「表情形象」的要求，不合规的地方说清原因：

```console
🎭 莓啾    完善进度 4/7
  ✅ 形象名称             莓啾（2 字）
  ✅ 形象简介             40 字
  ✅ 正面照母版            351×460
  ✅ 读图 prompt          已生成，多套专辑复用
  ✅ 原始素材池            source/ 33 个原稿（不可再生，跟着 git 走）
  ⚠️  形象头像 240×240     主体是实心矩形 → 只是缩放贴上的照片，没抠出轮廓
  ⚠️  形象图标 50×50       主体是实心矩形 → 只是缩放贴上的照片，没抠出轮廓
```

三条官方跨形象约束自动生效：**形象名不得重复**、**不同形象不得用同一张头像**
（差分哈希比对）、**一套作品只能挂一个形象且改归属只有 1 次机会**。

## 出一套系列

```bash
$S/new_album.sh --ip 团子 --series 日常      # → albums/团子/01-日常/
$S/new_album.sh --ip 团子 --series 打工      # → albums/团子/02-打工（序号自动递增）
```

幂等，卡住就修完再跑同一条：

1. 第一次跑 → 生成 `album.yml` 并停下让你填文案（唯一需要动脑的环节）
2. 填完再跑 → 出图 → 切图 → 机检 → 生成 `submit.md`
3. 机检报 FAIL → 打印「这条该怎么修」，修完再跑

自己画好图也能用 —— 丢进 `<系列目录>/raw/`，不加 `--ip` 直接跑，从切图接管。

## 机检输出

三级判定 —— `FAIL` 必改、`WARN` 人工确认、`OK` 通过，退出码等于 FAIL 条数：

```console
$ python3 scripts/check_assets.py <系列目录> --copy <系列目录>/album.yml
✅ 01-委屈.png: PNG 240×240 55KB
✅ 封面图-莓啾.png: PNG 240×240 67KB
✅ 详情页横幅-莓啾日常.jpg: JPEG 750×400 37KB
✅ copy: 文案字数全部合规（9 条含义词）

可以提交 — FAIL 0 / WARN 0
```

不合规时的口径（每条都是开发中真实触发过的）：

```console
❌ 聊天图标-莓啾.png: 四角不透明（66%）— 白底或正方形边框，官方明文「须设置为透明背景」
❌ 06.png vs 08.png: 画面几乎相同（差分哈希距离 0/64）— 整套差异不足是最高频拒因
❌ 01.png: 主体轮廓 100% 近白、内部仅 53% — 白色描边，须去掉
❌ copy: 含义词 9 条 ≠ 表情图 8 张，须一一对应
⚠️  10-等饭饭.png: 主体是实心矩形 — 只是缩放贴上的照片，没抠出轮廓
```

**机检拦不住画面里写了什么** —— 有一套就栽在这上面（横幅印了「微信表情包专辑」被判
推广非自有版权的应用程序），而那几张图机检全是 ✅。对外展示图必须人眼再过一遍。

## 踩坑记录

[`references/pitfalls.md`](references/pitfalls.md) 共 15 条，每条给出**症状 → 根因 → 修法**。
前四条与表情包无关，是写中文 shell 脚本的通用陷阱：

- 变量后紧跟全角标点（`"并发 $JOBS，"`）→ 标点字节被吞进变量名，`set -u` 报 unbound variable
- `set -e` 下独立的 `(( i++ ))` 在 `i=0` 时返回 1 → 脚本静默 exit 0、循环一次不跑、无报错
- 同族的另两个入口：命令替换里单个命令的非零退出码、`pipefail` 下 `grep` 无匹配 ——
  后者**只在出错路径上炸**，正常流程测一百遍都测不出来
- 别照终端显示写 CLI 输出解析（那份报告往往走 stderr），也别 `2>/dev/null` 吞掉错误原文

领域特有的：均值哈希对同底色图集体失效、白描边检测会把白猫全判违规、
PIL 转 `P` 模式会丢 alpha、`sharp` 单通道 resize 返回 3 通道导致错位采样、
上游频次限制下「改一版跑一轮」的验证节奏行不通。

其中一条做成了可执行门禁 —— [`scripts/lint.sh`](scripts/lint.sh)：

```console
$ ./scripts/lint.sh
✅ 变量与全角标点边界
✅ 算术自增写法
✅ 并发等待兼容性
✅ 命令替换的失败兜底
✅ pipefail 下的 grep 管道
✅ 外部命令的错误可见性
✅ 全部脚本语法
门禁通过。
```

加它的原因很实在：全角标点那条，我在写完文档之后又犯了一次 —— **文档拦不住重犯，检查能**。

## 依赖

- **机检 / 切图 / 合成 GIF**：Python 3 + [Pillow](https://python-pillow.org/)，无其他依赖，不需要 ImageMagick
- **出图 / 抠图 / 擦字**：[museav](https://www.npmjs.com/package/museav-cli) CLI
  （`--ref` 垫图、`--transparent` 透明输出、`remove-bg` 抠图默认 BiRefNet、`remove-watermark` LaMa 修复）。
  没有它也不影响其余步骤 —— 自己画好图直接从切图开始

## 目录

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 主流程（Claude Code 读这个） |
| `scripts/ip.py` | **IP 库**：注册 / 完善进度 / 跨形象约束 / 改名 / HTML 面板 / 备份 |
| `scripts/new_album.sh` | **一键入口**（幂等）：文案 → 出图 → 切图 → 机检 → 提交清单 |
| `scripts/gen_album.sh` | 一张正面照 → 整套原图（含重试、限流退避、补差集） |
| `scripts/restyle.py` | 照片型表情图 → 透明贴纸（先擦字再抠图，重绘统一文字） |
| `scripts/make_gif.py` | 透明 PNG 序列 → 240×240 透明 GIF，自适应压到 500KB |
| `scripts/make_promo.py` | 整套表情 → 1080×1920 竖版推广视频（读 `album.yml` → 调 `reel make`） |
| `scripts/fit_assets.py` | 源图 → 合规尺寸素材（抠白底 / 去留白 / 居中 / 压体积 / `--anchor`） |
| `scripts/check_assets.py` | 素材 + 文案机检，退出码 = FAIL 数 |
| `scripts/make_submit.py` | 生成 `submit.md`：平台表单字段 → 值/文件对照表 |
| `scripts/page_tpl.py` | 进度面板的样式与渲染 |
| `scripts/lint.sh` | 脚本门禁：把 pitfalls 里踩过的坑变成能跑的检查 |
| `references/specs.md` | 官方制作规范全文（表情/形象/特效/艺术家/赞赏/付费）— 数字真源 |
| `references/audit.md` | 官方审核标准全文 + **实战拒因** + 高频拒因 |
| `references/platform.md` | **平台地图**：真实 URL、登录方式、提交表单完整字段、账号前置条件 |
| `references/animated.md` | **动态表情**：1-bit 透明约束、四步流水线、IP 适配判断 |
| `references/ip-design.md` | IP 命名 / 简介 / 情绪选题 / 含义词写法 |
| `references/pitfalls.md` | 踩坑记录 15 条（症状 → 根因 → 修法） |
| `templates/album.yml` | 可被机检解析的文案模板 |
| `CHANGELOG.md` | 版本演进 |
| `examples/` | 真实跑出来的 `submit.md` 与 `album.yml` |

## 免责

规范内容抓取自[微信表情开放平台官方文档](https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications)（2026-08-27），
官方声明其为动态文档。**如与平台当前页面冲突，以平台页面为准。**
本项目不隶属于腾讯，也不保证审核通过 —— 机检只能拦规格问题，创意与权利问题得靠你自己。

投稿素材必须为你原创或拥有版权。垫图请用自己的原图，不要垫他人作品或知名 IP。

## License

MIT
