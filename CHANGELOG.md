# Changelog

## 1.2.0 (2026-08-28)

### 出片改走 reel-kit（`museav slideshow` 已下线）

1.1.1 刚把出片能力下沉到 museav-cli 的 `slideshow`，当天就发现
**[reel-kit](https://github.com/webkubor/reel-kit) 早就做了同一件事，而且更好**：

- 版式用 HTML/CSS —— 文字能换行、能做阴影渐变，SVG 那版做不到
- 支持配音，且**镜头时长由念白长度决定**（念快的不干等，念慢的不被切）
- 默认走本地 voxcraft TTS，批量出片零成本
- 加版式 = 往 `templates/` 丢一个 HTML，不用改代码

所以 museav 的 slideshow 下线，能力收敛到 reel-kit 一处。`make_promo.py` 接口没变
（还是读 `album.yml` 拼参数），内部改调 `reel make --template sticker-promo`。

用法上的变化：

- `--music` 现在收**配乐库别名**（默认「儿童轻快」，`reel bgm` 看清单），也仍接受本地路径。
  配乐真源是 web-assets 的 `manifest/music.json`，出片时会打印授权。
- 新增 `--voice <音色>` 透传给 reel-kit 开配音；`--template` 换版式
- 前置依赖从 museav 变成 reel-kit（`npm link` 一次）+ ffmpeg + Chrome

迁移时顺手修了 reel-kit 的 `sticker-promo` 模板：`.stage img` 用的是 `max-width`，
**只限上限不放大小图**，240×240 的表情在 900px 宽的舞台里只占一小块 ——
跟 PIL 的 `thumbnail` 是同一个坑换成了 CSS 皮。

教训写进了 `references/animated.md`：**动手前先 `cs repo <关键词>` 搜一遍**。

## 1.1.1 (2026-08-28)

### 出视频的能力下沉到 museav CLI

`make_promo.py` 原本自己实现了整套排版（PIL 画页 + ffmpeg 拼接）。但「一组图 + 逐张文案 +
配乐 → 竖版视频」跟表情包没关系，产品图、作品集、日报一样要用 —— 留在这个 skill 里
等于把通用能力锁死在一个场景。

现在拆成两层：

- **`museav slideshow`**（museav-cli ≥ 2.9.0）：通用的图集转竖版视频，排版走 sharp + SVG，合成走 ffmpeg
- **`make_promo.py`**：只做表情包特有的部分 —— 读 `album.yml` 取专辑名/形象名/文案，按 `表情图/` 约定拼参数

三个坑的修法跟着能力一起搬过去了（小图要显式放大且先裁透明留白、配乐要 atrim+afade、
concat 末页要多列一次），`references/animated.md` 里仍留有记录，因为它们值得别的场景也知道。

用法上的唯一变化：文案不再需要 `--captions 文案.txt`，直接读 `album.yml` 的 `captions` 段。

## 1.1.0 (2026-08-27)

第一版只覆盖「静态表情投稿」。这一版补上了形象管理、动态表情、照片转贴纸，
并把平台上真实跑过一轮拿到的信息（登录后 URL、完整表单字段、一条真实驳回记录）落成文档。

### 新增：IP 库（`scripts/ip.py`）

微信那边「表情形象」是账号级配置、一个形象挂多套系列。原来形象信息散在每套专辑的
`album.yml` 里，多个 IP 一起做必乱，而官方三条跨形象约束也无从检查。

- `add` / `list` / `show` / `update` / `rename` / `link` / `sync` / `page`
- `show` 逐项核对官方对形象的要求（名称/简介/母版/读图 prompt/画稿池/头像/图标），
  不合规写明原因
- 三条官方约束自动生效：形象名不得重复、不同形象不得同头像（差分哈希）、
  作品挂形象只有 1 次改机会（`new_album.sh` 校验 `ip_name` 与 `--ip` 一致）
- `page` 生成自包含 HTML 进度面板（图片内嵌 base64，双击可看，支持深浅色）
- `sync` 把整库推私有 GitLab 仓库，首次自动建仓

### 新增：动态表情（`references/animated.md` + `scripts/make_gif.py`）

- GIF 只有 1-bit 透明，半透明像素必须二选一。取阈值 128 + 主体腐蚀 1px
  （思路来自 [hackerb9/mktrans](https://github.com/hackerb9/mktrans)），实测深浅底都不出 halo
- 自适应压到 500KB：先降色深（255→192→128→96 色），压不下去才抽帧
  —— 抽帧放最后，因为它直接损伤流畅度
- 四步流水线：图生视频 → 抽帧 → 逐帧抠图 → 合成。官方明文禁止「无意义的缩放平移晃动闪烁」，
  所以不能拿单张图程序化动画充数
- 实测：240×240 / 20 帧 / 465KB。照片型 IP 不建议做动图（毛发边缘在 1-bit 透明下两头难看）

### 新增：照片型表情 → 透明贴纸（`scripts/restyle.py`）

不透明白底照片发到微信就是白方块，深色模式下边缘生硬。

- 关键是**顺序：先擦字再抠图**。反过来的话，压在主体身上的文字会随主体保留，
  跟重绘的新文字叠在一起 —— 抠图按「主体/背景」二分，文字归哪边取决于它压在什么上面
- 擦字用 `museav remove-watermark` + 自制 mask（它的自动定位只认角标式半透明水印，
  不认大号描边文字）。mask 靠「白笔画 + 深描边紧邻」定位，且只在下半部搜 ——
  猫眼睛也是高对比黑白，全图搜会把眼睛当文字擦掉
- 重绘文字顺带统一了字体字号描边（原素材往往每张都不一样）

### 新增：平台地图（`references/platform.md`）

原来项目里只有规范文档的 URL 和一个裸域名，要用的时候只能靠常识拼，第一次就拼出 404。

- 平台路径分两套 CGI 前缀（`mmemoticon-bin/readtemplate` 与 `mmemoticonwebnode-bin/pages`），猜不出来
- 免登录 11 个入口 + 登录后 9 个入口，全部实测
- **提交表单的完整字段** —— 「附加信息」那一整块官方文档里没写但必填，
  且带两条比例硬约束：角色出现的表情数 ≥ 总数 1/3、与主题相关的表情数 ≥ 总数一半
- 重投规则：审核未通过的专辑要在原专辑上编辑后提交，新建会撞「不允许重复提交」

### 新增：实战拒因（`references/audit.md`）

一条真实驳回记录：

```
详情页横幅    不应含有任何非自有版权的应用程序、产品、节目等推广信息。【微信】
赞赏引导图    同上。【微信】
```

宣传图上印了「微信表情包专辑」，**画面里出现「微信」字样就被判成推广非自有版权的应用程序**
—— 写自己这套作品也算。官方原文只写了「含有明显广告、商业推广性质的内容」，读不出这层。

延伸：这类带标题的宣传图适合发朋友圈/小红书，但不能填进平台字段，两种用途要备两张图。

### 改进

- `check_assets.py`：新增「主体是实心矩形」检测 —— 切图留的几像素透明边会骗过
  「四角是否透明」，中间仍是整块未抠图的照片
- `fit_assets.py`：新增 `--anchor top/center/bottom`。竖构图素材居中裁会切掉顶部主体，
  赞赏引导图必须 `top`（平台会在下半部叠加金额选择 UI）；
  源图已是合规 240×240 时不再重切（原逻辑会把铺满的构图凭空缩小一圈）
- `new_album.sh`：`--series` 自动推导目录并递增序号，同名系列复用（幂等）；
  新增 `--cover-from` / `--icon-from`（照片型专辑的表情图是白底的，不能拿来做封面）
- `gen_album.sh`：识别上游限流并三级退避；重跑只补缺失的，不重复烧配额
- `templates/album.yml`：占位符改成「待填…」—— 原来直接写了某个真实 IP 名当示例，
  那个 IP 真要投稿时被「还是模板默认值」的检测拦住
- `scripts/lint.sh`：把 pitfalls 里的坑做成可执行门禁（全角标点吞变量名、`(( i++ ))`、
  `wait -n`、命令替换缺 `|| true`、`pipefail` 下的 grep、`2>/dev/null` 吞错误）

### 结构收敛

- **代码一份**：这个 skill 目录本身就是 git 仓库，`~/dev/github/agent/` 下放软链。
  早先是两份副本靠手动 rsync，已经漂了 8 个文件才发现。
  ⚠️ Claude Code **不跟随 symlink 加载 skill**，真目录必须在 `~/.claude/skills/` 下
- **数据一根**：全收进 `~/.wechat-stickers`，git 只版本化 `ips/`（不可再生的画稿与母版），
  `albums/`（产物）与 `outbox/`（待上传）进 `.gitignore`。
  `~/Pictures/表情包系列` 改为指向 `albums/` 的软链

## 1.0.0 (2026-08-26)

首版，覆盖静态表情投稿：

- 官方制作规范与审核标准全文抓取归档（`references/specs.md` / `audit.md`）
- `new_album.sh` 幂等一键入口：文案 → 出图 → 切图 → 机检 → 提交清单
- `check_assets.py` 机检：格式/尺寸/体积/透明背景/白描边/留白/张数/画面相似度/文案字数
- `fit_assets.py` 切图、`gen_album.sh` 批量出图、`make_submit.py` 提交清单
- 产物按「形象名 + 含义词」中文命名
