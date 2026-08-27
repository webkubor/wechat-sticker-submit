# wechat-sticker-submit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-d97757)](https://claude.com/claude-code)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Deps: Pillow only](https://img.shields.io/badge/Deps-Pillow%20only-2ea44f)](https://python-pillow.org/)
[![官方规范同步](https://img.shields.io/badge/%E5%AE%98%E6%96%B9%E8%A7%84%E8%8C%83%E5%90%8C%E6%AD%A5-2026--08--26-orange)](https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications)
[![Stars](https://img.shields.io/github/stars/webkubor/wechat-sticker-submit?style=flat&color=yellow)](https://github.com/webkubor/wechat-sticker-submit/stargazers)

**一张 IP 正面照，出一整套能直接提交的微信表情素材。**

微信表情开放平台的投稿门槛不在画功，在规格：240×240 的表情图、750×400 的横幅、
必须透明背景的封面与图标、每张 ≤4 字且不许重复的含义词……
而超规格的素材平台**不拒收、不报错，直接压缩裁剪** —— 主体被裁掉才发现就白做了。

这是一个 [Claude Code](https://claude.com/claude-code) skill：出图、切图、机检、文案校验、
提交清单全部脚本化，零美术基础也能跑完。

## 产物演示

下面这一整套是真跑出来的 —— 输入只有一张白猫正面照，一条命令产出
8 张表情图 + 封面 + 图标 + 横幅，机检 FAIL 0：

![表情图 8 张](https://img.webkubor.online/skills/wechat-sticker-demo-stickers.jpg)

文件名自带含义词（`01-开心.png`、`02-委屈.png`…），编号即上传顺序，不用回头对映射表。

![封面图与聊天图标与详情页横幅](https://img.webkubor.online/skills/wechat-sticker-demo-assets.jpg)

三件套的要求彼此矛盾，所以流水线分开处理：封面用正面半身像 + 透明背景，
图标用头部特写 + 透明背景，横幅要不透明、有场景、画面内不得有文字。

> 当前版本只做**静态表情**。动态 GIF 与视频号特效的规范已归档，但流水线不覆盖 ——
> 官方要求同一套专辑必须统一动/静，别混着做。

## 它替你解决什么

| 你会踩的坑 | skill 怎么拦 |
|---|---|
| 素材超尺寸被平台静默裁掉 | 切图流水线统一归一到规格尺寸并压到体积上限 |
| 封面/图标忘了透明背景 | 机检对封面/图标判 FAIL，表情图判 WARN（照片型可忽略），横幅反过来 |
| 主体一圈白描边 | 比对「轮廓 vs 主体内部」亮度 —— 白猫这类白色系角色不会误报 |
| 整套画面差异不足（**第一大拒因**） | 裁到主体后算差分哈希两两比对，太像就 FAIL |
| 把台词当含义词（「555…我没事」） | 校验 ≤4 字、无标点、同套不重复、条数与张数一一对应 |
| 图标裁成方块、四角发硬 | 自动取头部正面并留 12% 边 |
| 出图偶发失败导致张数不足 | 单张重试一次；重跑只补缺失的，不重复烧配额 |
| 作品挂错表情形象 | `album.yml` 的 ip_name 与 `--ip` 不一致直接拦下（改归属只有 1 次机会） |
| 多个 IP 混着做，简介/头像串了 | IP 库分层存放；形象名重复、不同形象同头像都会被拒 |
| 形象母版只存在本地，丢了合集就断 | `ip.py sync` 推私有仓库版本化，换机 clone 即恢复 |

## 安装

```bash
git clone https://github.com/webkubor/wechat-sticker-submit.git \
  ~/.claude/skills/wechat-sticker-submit
```

装完在 Claude Code 里说「帮我做一套微信表情」即可触发；也可以只当命令行工具用。

## IP 库：形象入库一次，多套专辑复用

官方的「表情形象」是账号级资产（自己的名称/简介/头像/图标），一个形象可以挂多套专辑；
封面图、横幅、含义词才是专辑级的。这两层混在一起，就会出现「同一个 IP 两套专辑简介不一致」
「两个形象用了同一张头像」这类必被打回的问题。所以形象单独存一份：

```bash
SKILL_DIR=~/.claude/skills/wechat-sticker-submit

python3 $SKILL_DIR/scripts/ip.py add 团子 ~/Desktop/正面照.png --desc "简介，≤80 字"
python3 $SKILL_DIR/scripts/ip.py list          # 有哪些形象
python3 $SKILL_DIR/scripts/ip.py show 团子      # 完善进度 + 待办 + 已挂专辑
python3 $SKILL_DIR/scripts/ip.py sync          # 备份到私有 GitLab 仓库（首次自动建仓）
```

`show` 会逐项核对官方对「表情形象」的要求，并把不合规的地方说清楚：

```console
🎭 莓啾    完善进度 4/6
  ✅ 形象名称             莓啾（2 字）
  ✅ 形象简介             40 字
  ✅ 正面照母版            351×460
  ✅ 读图 prompt          已生成，多套专辑复用
  ⚠️  形象头像 240×240     主体是实心矩形 → 只是缩放贴上的照片，没抠出轮廓
  ⚠️  形象图标 50×50       主体是实心矩形 → 只是缩放贴上的照片，没抠出轮廓

  待办：
    · 形象头像/图标需抠透明背景
```

三条官方跨形象约束在这里自动生效：**形象名不得重复**（重名直接拒绝）、
**不同形象不得用同一张头像**（按差分哈希比对已有形象）、
**一套作品只能挂一个形象且改归属只有 1 次机会**（`new_album.sh` 校验 `album.yml`
里的 `ip_name` 与 `--ip` 是否一致，不一致就拦下）。

库默认在 `~/.wechat-stickers/`（`STICKER_HOME` 可覆盖）。
**形象母版丢了整条形象合集就断了**（表情图丢了还能重出），所以 `ip.py sync`
把图片与元数据一起推到私有仓库版本化，换机恢复就是 `git clone <仓库> ~/.wechat-stickers`。

## 用法：一条命令，反复跑

```bash
$SKILL_DIR/scripts/new_album.sh ~/Desktop/团子日常 --ip 团子      # 用库里的形象
$SKILL_DIR/scripts/new_album.sh ~/Desktop/团子日常 --ip ~/ip.png  # 或直接给正面照
```

这条命令幂等，卡住就修完再跑同一条：

1. 第一次跑 → 生成 `album.yml` 并停下让你填文案（唯一需要动脑的环节）
2. 填完再跑 → 按含义词条数出图 → 切图 → 机检 → 生成 `submit.md`
3. 机检报 FAIL → 打印「这条该怎么修」，修完再跑

自己画好图也能用 —— 8~24 张丢进 `团子日常/raw/`，不加 `--ip` 直接跑，从切图接管。
单个环节也能拆开用：

```bash
python3 $SKILL_DIR/scripts/fit_assets.py raw/ out/ --copy out/album.yml --cover raw/01.png --icon raw/01.png
python3 $SKILL_DIR/scripts/check_assets.py out/ --copy out/album.yml   # 退出码 = FAIL 条数
```

## 产物目录

产物按**形象名 + 含义词中文命名**，打开文件夹就知道哪张是哪张。平台表单要的每一项都在这，
`raw/` 只留档、不提交：

```
团子日常/
├── 表情图/                                                 ← 按编号顺序上传
│   ├── 01-开心.png       240×240  PNG  ≤500KB
│   ├── 02-委屈.png       240×240  PNG  ≤500KB
│   └── ... 08-无语.png                                     8~24 张任意数量
├── 封面图-团子.png        240×240  PNG  ≤500KB   透明背景（官方强制）
├── 聊天图标-团子.png       50×50   PNG  ≤100KB   透明背景（官方强制）
├── 详情页横幅-团子日常.jpg  750×400  JPG  ≤500KB   不透明·画面内不得有文字
├── album.yml            文案：形象名/简介/专辑名/介绍/版权/含义词
├── submit.md            ★ 提交清单：平台表单字段 → 值/文件对照表
└── raw/                 出图原件与读图 prompt（留档，不提交）
    ├── 01..08.png       出图原尺寸（如 1240×1269）
    ├── banner-src.png   横幅底图
    └── ip-reverse.txt   IP 读图逆向出的英文 prompt（整套风格一致的锚）
```

开通赞赏时再多两张（都不透明、≤500KB）：`赞赏引导图-团子.png`（750×560）、
`赞赏致谢图-团子.png`（750×750）。

真实生成的提交清单见 [`examples/submit.md`](examples/submit.md)（未手改）。

> 单独当命令行工具用、不给 `--copy album.yml` 时退回英文命名
> （`main_240/01.png`、`cover_240.png`…）。机检与清单脚本两套命名都认。

## 机检输出

三级判定 —— `FAIL` 必改、`WARN` 人工确认、`OK` 通过，退出码等于 FAIL 条数，可直接串进脚本。
上面那套的真实输出：

```console
$ python3 scripts/check_assets.py 团子日常 --copy 团子日常/album.yml
⚠️  赞赏引导图: 缺失 — 仅开通赞赏时需要
⚠️  赞赏致谢图: 缺失 — 仅开通赞赏时需要
✅ 01-开心.png: PNG 240×240 68KB
✅ 02-委屈.png: PNG 240×240 71KB
✅ 03-好困.png: PNG 240×240 66KB
✅ 04-生气.png: PNG 240×240 68KB
✅ 05-疑问.png: PNG 240×240 60KB
✅ 06-收到.png: PNG 240×240 67KB
✅ 07-拜托.png: PNG 240×240 67KB
✅ 08-无语.png: PNG 240×240 68KB
✅ 封面图-团子.png: PNG 240×240 68KB
✅ 聊天图标-团子.png: PNG 50×50 4KB
✅ 详情页横幅-团子日常.jpg: JPEG 750×400 77KB
✅ copy: 文案字数全部合规（8 条含义词）

可以提交 — FAIL 0 / WARN 2
```

不合规时是这种口径（以下每条都是开发过程中真实触发过的）：

```console
❌ 聊天图标-团子.png: 四角不透明（66%）— 白底或正方形边框，官方明文「须设置为透明背景」
❌ 06.png vs 08.png: 画面几乎相同（差分哈希距离 0/64）— 整套差异不足是最高频拒因
❌ 01.png: 主体轮廓 100% 近白、内部仅 53% — 白色描边，须去掉
❌ copy: 含义词 9 条 ≠ 表情图 8 张，须一一对应
❌ 表情图/: 6 张，须为 8~24 张
⚠️  01.png: 主体只占画面 55% — 留白过多，建议放大到 70% 以上
```

## 踩坑记录

开发过程中的翻车都写进了 [`references/pitfalls.md`](references/pitfalls.md)，
每条给出**症状 → 根因 → 修法**。其中前四条与表情包无关，是写中文 shell 脚本的通用陷阱：

- 变量后紧跟全角标点（`"并发 $JOBS，"`）→ 标点字节被吞进变量名，`set -u` 报 unbound variable
- `set -e` 下独立的 `(( i++ ))` 在 `i=0` 时返回退出码 1 → 脚本静默 exit 0、循环一次不跑、无报错
- `wait -n` 需要 bash 4.3+，macOS 自带的是 3.2.57
- 别照着终端显示写 CLI 输出解析 —— 那份好看的报告往往走 stderr，stdout 只有结果本身

领域特有的几条：均值哈希对同底色图集体失效、白描边检测会把白猫全判违规、
透明 PNG 垫图会被读图逆向成 "black background"、幂等重跑要补差集而不是重做全集。

## 依赖

- **机检与切图**：Python 3 + [Pillow](https://python-pillow.org/)，无其他依赖，不需要 ImageMagick。
- **批量出图**：`gen_album.sh` 走 MUSE AV 出图中台 CLI（`museav`，含 `--ref` 垫图、
  `--transparent` 透明输出、本地 `remove-bg` 抠图）。没有它也不影响其余步骤 ——
  自己画好图直接从切图开始。

## 目录

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 主流程（Claude Code 读这个） |
| `scripts/ip.py` | **IP 库**：注册形象 / 完善进度 / 跨形象约束 / 备份到私有仓库 |
| `scripts/new_album.sh` | **一键入口**（幂等）：文案 → 出图 → 切图 → 机检 → 提交清单 |
| `scripts/gen_album.sh` | 一张正面照 → 整套原图（含重试与补差集） |
| `scripts/fit_assets.py` | 源图 → 合规尺寸素材（抠白底 / 去留白 / 居中 / 压体积） |
| `scripts/check_assets.py` | 素材 + 文案机检，退出码 = FAIL 数 |
| `scripts/make_submit.py` | 生成 `submit.md`：平台表单字段 → 值/文件对照表 |
| `scripts/lint.sh` | 脚本门禁：把 pitfalls 里踩过的坑变成能跑的检查 |
| `references/specs.md` | 官方制作规范全文（表情/形象/特效/艺术家/赞赏/付费）— 数字真源 |
| `references/audit.md` | 官方审核标准全文 + 高频拒因 |
| `references/ip-design.md` | IP 命名 / 简介 / 9 情绪选题 / 含义词写法 |
| `references/pitfalls.md` | 踩坑记录（中文 bash 三坑 / CLI 输出通道 / 图像机检误报） |
| `templates/album.yml` | 可被机检解析的文案模板 |
| `examples/` | 真实跑出来的 `submit.md` 与 `album.yml` |

## 免责

规范内容抓取自[微信表情开放平台官方文档](https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications)（2026-08-26），
官方声明其为动态文档。**如与平台当前页面冲突，以平台页面为准。**
本项目不隶属于腾讯，也不保证审核通过 —— 机检只能拦规格问题，创意与权利问题得靠你自己。

投稿素材必须为你原创或拥有版权。垫图请用自己的原图，不要垫他人作品或知名 IP。

## License

MIT
