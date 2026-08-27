---
name: wechat-sticker-submit
description: 微信表情开放平台静态表情投稿全流程 SOP —— 一张 IP 正面照进，整套可提交素材出。覆盖 IP 命名与简介文案、9 情绪选题、museav 中台批量出图、240×240 表情图 / 750×400 详情页横幅 / 240×240 封面 / 50×50 聊天面板图标切图、透明背景与白描边机检、含义词字数校验、赞赏三件套、付费表情（10 微信豆）、审核红线与高频拒因。触发词：微信表情、表情包、表情专辑、表情投稿、提交表情、表情形象、微信表情开放平台、sticker、表情审核、含义词、赞赏引导图、付费表情、微信豆、表情封面、聊天面板图标。
metadata:
  version: "1.0.0"
  updated: "2026-08-26"
  scope: "静态表情（动态 GIF 与视频号特效不在本版范围）"
  source: "https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications"
---

# 微信表情投稿 SOP（静态表情）

**输入：一张 IP 正面照。输出：一个能直接往平台表单里填的目录。**
零美术基础也能跑完 —— 出图、切图、校验、文案全部有脚本兜着，不需要打开 PS。

本版只做**静态表情**（PNG）。动态 GIF 与视频号特效的规范已归档在 `references/specs.md`，
但流水线不覆盖，别混着做：官方要求同一套专辑必须统一动/静。

```
SKILL_DIR=~/.claude/skills/wechat-sticker-submit
```

## 数据模型：形象唯一，系列多套

微信那边是两个独立配置，且是一对多：

```
表情形象（唯一）              表情系列 / 专辑（多套）
名称 · 简介 · 头像 · 图标  ──┬── 系列 A：表情图 8~24 张 + 封面 + 横幅 + 含义词
                          ├── 系列 B：另一套，复用同一个形象
                          └── 系列 C：...
```

所以本地也照这个分两处存，**按「能不能再生」决定备份策略**：

```
~/.wechat-stickers/ips/<形象>/          ← 形象配置 + 原始画稿，丢了画不回来 → git 备份
├── ip.yml            名称/简介/系列清单/待办
├── ip.png            正面照母版（出图垫图用，多套系列形象才不漂）
├── ip-reverse.txt    读图 prompt（一个形象只读一次）
├── 形象头像-<名>.png   240×240 透明
├── 形象图标-<名>.png   50×50 透明
└── source/           原始画稿池，多套系列都从这里挑图

~/Pictures/表情包系列/<形象>/<序号>-<系列名>/   ← 产物，有画稿+脚本就能重跑 → 不备份
├── 表情图/01-开心.png … NN-xxx.png
├── 封面图-<形象>.png · 聊天图标-<形象>.png · 详情页横幅-<系列>.jpg
├── album.yml · submit.md
└── raw/              切图前的中间件
```

两个根目录都可用环境变量覆盖：`STICKER_HOME`、`STICKER_ALBUMS`。

## 最快路径

```bash
# 形象只建一次
python3 $SKILL_DIR/scripts/ip.py add 团子 ~/Desktop/正面照.png --desc "简介，≤80 字" \
    --source ~/Desktop/团子画稿          # 原始画稿一并收进库
python3 $SKILL_DIR/scripts/ip.py sync    # 备份到私有仓库

# 之后每出一套系列，一条命令（目录自动放对位置、序号自动递增）
$SKILL_DIR/scripts/new_album.sh --ip 团子 --series 日常
$SKILL_DIR/scripts/new_album.sh --ip 团子 --series 打工     # 第二套，自动变 02-打工

# 随时看全局
python3 $SKILL_DIR/scripts/ip.py list          # 每个形象几套系列、每套什么状态
python3 $SKILL_DIR/scripts/ip.py show 团子      # 单个形象逐项核对
python3 $SKILL_DIR/scripts/ip.py page          # 生成 HTML 面板并打开（缩略图一览）
```

`new_album.sh` 幂等：同名系列反复跑会复用同一个目录，不会新建一堆空壳。
第一次跑生成 `album.yml` 停下让你填文案，填完再跑同一条命令就继续往下走。

下面是每一步在做什么、以及为什么这么定 —— 出问题时看这里。

---

## Step 1 · 把形象存进 IP 库（一次，之后长期复用）

```bash
python3 $SKILL_DIR/scripts/ip.py add <形象名> <正面照> --desc "简介，≤80 字"
python3 $SKILL_DIR/scripts/ip.py list        # 有哪些形象
python3 $SKILL_DIR/scripts/ip.py show 团子    # 完善进度 + 待办 + 已挂专辑
python3 $SKILL_DIR/scripts/ip.py sync        # 备份到私有 GitLab 仓库
```

**为什么要有 IP 库**：官方的「表情形象」是账号级资产（自己的名称/简介/头像/图标），
一个形象可以挂多套专辑；封面图、横幅、含义词才是专辑级的。混在一起必然出现
「同一个 IP 两套专辑简介不一致」「两个形象用了同一张头像」这类会被打回的问题。
而且官方有三条跨形象的硬约束，只有集中存放才查得了：

- 同一作者的形象名不得重复 → `ip.py add` 直接拒绝重名
- 不同形象不得用同一张头像/图标 → 注册时按差分哈希比对已有形象，太像就警告
- **一套作品只能挂一个形象，改归属只有 1 次机会** → `new_album.sh` 会校验
  `album.yml` 里的 `ip_name` 与 `--ip` 一致，不一致直接拦下

**库在哪**：默认 `~/.wechat-stickers/`，用环境变量 `STICKER_HOME` 覆盖。结构：

```
~/.wechat-stickers/ips/<形象名>/
├── ip.png            正面照母版 —— 出图垫图用这张，多套专辑形象才不会漂
├── ip-reverse.txt    读图逆向的英文 prompt，一个形象只读一次（省时间省配额）
├── 形象头像-<名>.png   240×240 透明，形象主页用
├── 形象图标-<名>.png   50×50 透明
└── ip.yml            名称 / 简介 / 已挂专辑 / 待办
```

**备份不是可选项**：形象母版丢了，整条形象合集就断了（表情图丢了还能重出）。
`ip.py sync` 把整个库推到私有 GitLab 仓库，图片与元数据一起版本化；
换机恢复就是 `git clone <仓库> ~/.wechat-stickers`。首次 sync 会自动建仓。

对正面照的要求只有一条：**角色正面、完整、你拥有版权**。手绘扫描、AI 出的、自家宠物照都行；
别拿他人作品或知名 IP 垫图 —— 那属于审核明文禁止的「权利所属不明」。

照片型（真宠物照）和插画型都能投，但差别要知道：
**照片型的表情图可以不透明，插画型建议透明** —— 而两者的**封面图与聊天面板图标都必须透明背景**，
这是官方明文，没有例外。照片型要做封面就得先抠图（`museav remove-bg <file>`，默认 birefnet 模型，白色/低对比主体也能抠干净）。

## Step 2 · 写 IP 文案（5 分钟，先写再出图）

复制模板改字：

```bash
mkdir -p ~/Desktop/my-album && cp $SKILL_DIR/templates/album.yml ~/Desktop/my-album/
```

七个字段的写法、命名反面例子、9 情绪选题表、含义词与台词的区别，全在
`references/ip-design.md` —— **给小白看的部分主要是这一篇**。

最容易错的一条先讲：**含义词是用户在表情面板里搜的词，不是画面里的台词**。
画面写「555…我没事」，含义词要写「我没事」（≤4 字、无标点、同套不重复）。

先写文案再出图，因为文案里的 9 个情绪就是出图的 prompt 清单。

## Step 3 · 批量出图（一条命令，约 3 分钟）

```bash
$SKILL_DIR/scripts/gen_album.sh --ip ~/Desktop/ip.png --out ~/Desktop/my-album
```

脚本做三件事：`museav reverse` 把 IP 外形逆向成英文 prompt（这是整套风格一致的锚）→
按 9 个情绪并发出图（`--ref` 垫图 + `--transparent` 透明 PNG）→ 顺手出一张横幅底图。

常用参数：`--count 8`（8~24 张任意数量都合规，8 张最省）、
`--emotions "开心,委屈,好困,..."`（换题材整组换，别混搭）、`--style "水彩风"`、`--jobs 3`（并发）。

出图会偶发失败（上游超时/审核拦截），单张自动重试一次。**重跑只补缺失的那几张**，
已出的直接跳过 —— 补 2 张不会重烧 8 次配额。要整套重出加 `--regen`。

出图不满意就重跑单张，别将就 —— **整套差异不足是第一大拒因**，宁可多出几张挑。
横幅要求和表情图正好相反（不透明、有场景、无任何文字），所以它单独出、单独裁。

**没有 museav 的路径**：自己画好或已有图，放进 `<目录>/raw/`（8~24 张，任意尺寸，按文件名排序），
横幅底图命名 `banner-src.png`。切图会自动跳过 `banner-src.*` / `ip.*` / `00-*` 这类非表情图文件。

## Step 4 · 切图（一条命令，秒级）

出图是 1240×1269 这种随机尺寸，必须切成规格尺寸 —— 直接传超规格图，
**平台不会拒，会静默压缩裁剪**，主体被裁掉才发现就晚了。

```bash
python3 $SKILL_DIR/scripts/fit_assets.py ~/Desktop/my-album/raw ~/Desktop/my-album \
  --cover ~/Desktop/my-album/raw/01.png \
  --icon  ~/Desktop/my-album/raw/01.png \
  --banner ~/Desktop/my-album/raw/banner-src.png
```

自动完成：抠白底 → 裁掉多余留白 → 等比缩放居中贴透明画布 → 压到体积上限。
封面取正面半身/全身（官方明确「避免只使用头部图片」），图标自动取头部正面并留 12% 边
（铺满四角会被判成「正方形边框、生硬直角」）。

## Step 5 · 机检（FAIL 必须清零）

```bash
python3 $SKILL_DIR/scripts/check_assets.py ~/Desktop/my-album --copy ~/Desktop/my-album/album.yml
```

逐项判定格式 / 尺寸 / 体积 / 透明背景 / 白描边 / 锯齿 / 留白比例 / 张数 /
**画面两两相似度** / 文案字数与含义词重复。三级结果：`FAIL` 必改、`WARN` 人工确认、`OK` 通过。
退出码等于 FAIL 条数，可以直接串进脚本。

几条判定的分寸（都是实测调出来的，别当成过严去绕过）：

- **白描边**：只有「轮廓明显比主体内部更白」才判 FAIL。白猫、雪人这类白色系角色不会被误报。
- **相似度**：先裁到主体再算差分哈希 —— 否则大片白底会把 8 张不同表情算成同一张。
  距离 <6/64 判 FAIL，6~10 判 WARN。**用 AI 出图几乎必然出现几条 WARN** ——
  垫图保证了形象一致，代价是姿势也跟着一致（都是正面坐姿，只有表情和手位在变）。
  实测一套 8 张就有 3 对落在 WARN 区（距离 6、10、10）。
  对策是在情绪里绑姿势/视角（站起来、侧身、躺着、只露头），默认情绪列表已经这么写了。
  ⚠️ **这个对策本身没跑通对照实验** —— 改完后连续几轮都撞上出图中台的频次限制，
  没拿到可比的一套。所以它是「对症的推断」，不是「已验证的结论」，
  真值请自己跑一次对比 WARN 条数。
- **透明背景**：封面/图标 FAIL，表情图 WARN（照片型可忽略），横幅/赞赏图反过来，透明才 FAIL。

## Step 6 · 填表提交（照着 submit.md 抄）

机检通过后自动生成 `submit.md` —— 平台表单每个字段填什么、传哪张图，一行一项：

```bash
python3 $SKILL_DIR/scripts/make_submit.py ~/Desktop/my-album   # new_album.sh 会自动跑
```

素材按**形象名 + 含义词中文命名**，打开文件夹就知道哪张是哪张，不用对编号映射：

```
团子日常/
├── 表情图/01-开心.png … 08-无语.png   240×240  ≤500KB  ← 按编号顺序传
├── 封面图-团子.png                    240×240  ≤500KB  透明
├── 聊天图标-团子.png                   50×50   ≤100KB  透明
├── 详情页横幅-团子日常.jpg              750×400 ≤500KB  不透明·无文字
├── album.yml                         文案（名称/介绍/版权/含义词）
├── submit.md                         提交清单 ← 照着这个填表
└── raw/                              出图原件（不提交，留档用）
```

不传 `--copy album.yml` 时退回英文命名（`main_240/01.png`、`cover_240.png`…），
机检与清单脚本两套都认。

投稿入口（路径分两套 CGI 前缀，猜必 404，全部记在 `references/platform.md`）：

```
首页/登录  https://sticker.weixin.qq.com/cgi-bin/mmemoticonwebnode-bin/pages/home
注册       https://sticker.weixin.qq.com/cgi-bin/mmemoticonwebnode-bin/pages/signup
```

登录只有「微信扫码」和「账号密码」两种，扫码这步 agent 代不了 ——
用 `ego-browser` 的 `handOffTaskSpace` 把浏览器交还给人。

**唯一不可逆的一步在这里**：作品挂到表情形象后，只有 **1 次**改到其他形象的机会
（且要先从原形象删除再加到新形象）。挂之前把形象确认清楚 —— 形象合集是拿关联推荐流量的入口。

## Step 7 · 归档与通知

素材母版按全局约定上 R2（`cs image upload`），**不要往 picx 加新图**。
桌面目录只当临时切图区。投稿结果用 `cs notify` 广播。

---

## 变现（可选，有前置条件，别等提交时才发现）

**赞赏**：需艺术家资料审核通过 + 绑定微信号/商户号 + 无违规，提交时要带引导语（5~15 字）、
引导图 750×560、致谢图 750×750（都不透明、≤500KB）。用 emoji 素材二创的作品**不能开赞赏**。

```bash
python3 $SKILL_DIR/scripts/fit_assets.py ~/Desktop/my-album \
  --reward-guide raw/banner-src.png --reward-thanks raw/02.png
```

**付费**：需至少 1 套已上架 + 近三个月无违规；价格固定每套 10 微信豆不可自定义；
免费↔付费**双向不可转**；付费与特效作品**不可在其他平台重复投稿**；
个人号一旦申请，身份信息不可再改、不可升企业号。细则见 `references/specs.md` 第六节。

## 审核红线速查

整套差异不足（最高频）· 纯文字表情缺创意 · 权利不明（二次创作/同人/拼接素材）·
真人肖像未授权 · 与微信官方作品雷同 · 画面出现二维码/联系方式/社交账号/银行账户 ·
受限题材（医疗药品烟酒金融虚拟币枪支、国旗国歌国徽人民币政府文件；军旗党旗团徽需授权书）。

全文与 AI 出图的额外注意事项见 `references/audit.md`。

## 文件索引

| 文件 | 用途 |
|---|---|
| `references/specs.md` | 官方制作规范全文（表情/形象/特效/艺术家/赞赏/付费）— **数字真源** |
| `references/audit.md` | 官方审核标准全文 + 高频拒因清单 |
| `references/ip-design.md` | IP 命名 / 简介 / 情绪选题 / 含义词写法（小白主要看这篇） |
| `references/platform.md` | **平台地图**：真实 URL、登录方式、账号前置条件（路径猜不出来，别拼） |
| `references/pitfalls.md` | 开发本 skill 时踩过的坑：中文 bash 三坑、CLI 输出通道、图像机检误报 |
| `templates/album.yml` | 文案模板，可被机检脚本解析 |
| `scripts/ip.py` | **IP 库**：注册形象 / 完善进度 / 跨形象约束校验 / HTML 面板 / 备份到私有仓库 |
| `scripts/page_tpl.py` | 面板的样式与渲染（被 `ip.py page` 调用） |
| `scripts/new_album.sh` | **一键入口**，幂等：文案 → 出图 → 切图 → 机检 → 清单 |
| `scripts/lint.sh` | 脚本门禁：把 pitfalls 里踩过的坑变成能跑的检查 |
| `scripts/gen_album.sh` | 一张正面照 → 整套原图（museav 出图中台） |
| `scripts/fit_assets.py` | 源图 → 合规尺寸素材（仅依赖 PIL） |
| `scripts/check_assets.py` | 素材 + 文案机检，退出码 = FAIL 数 |
| `scripts/make_submit.py` | 生成 `submit.md` 提交清单（字段 → 值/文件对照） |

规范是动态文档，官方会改。数字以 `references/` 为准，若与平台当前页面冲突，**以平台页面为准**并回来更新本 skill。
