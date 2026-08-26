# wechat-sticker-submit

**一张 IP 正面照，出一整套能直接提交的微信表情素材。**

微信表情开放平台的投稿门槛不在画功，在规格：240×240 的表情图、750×400 的横幅、
必须透明背景的封面与图标、每张 ≤4 字且不许重复的含义词……
超规格的素材平台不会拒，会**静默压缩裁剪**，主体被裁掉才发现就白做了。

这是一个 [Claude Code](https://claude.com/claude-code) skill：把官方规范拆成 7 步可执行流程，
出图、切图、机检、文案校验全部脚本化，零美术基础也能跑完。

> 当前版本只做**静态表情**。动态 GIF 与视频号特效的规范已归档，但流水线不覆盖 ——
> 官方要求同一套专辑必须统一动/静，别混着做。

## 它替你解决什么

| 你会踩的坑 | skill 怎么拦 |
|---|---|
| 封面/图标忘了透明背景 | 机检对封面/图标判 FAIL，表情图判 WARN（照片型可忽略），横幅反过来 |
| 主体一圈白描边 | 比对「轮廓 vs 主体内部」亮度 —— 白猫这类白色系角色不会误报 |
| 整套画面差异不足（**第一大拒因**） | 裁到主体后算差分哈希两两比对，太像就 FAIL |
| 把台词当含义词（「555…我没事」） | 校验 ≤4 字、无标点、同套不重复、条数与张数一一对应 |
| 图标裁成方块、四角发硬 | 自动取头部正面并留 12% 边 |
| 素材超尺寸被平台裁掉 | 切图流水线统一归一到规格尺寸并压到体积上限 |
| 作品挂错表情形象 | 流程里标出这是**唯一不可逆**的一步（只有 1 次改的机会） |

## 安装

```bash
git clone https://github.com/webkubor/wechat-sticker-submit.git \
  ~/.claude/skills/wechat-sticker-submit
```

装完在 Claude Code 里说「帮我做一套微信表情」即可触发；也可以只当命令行工具用。

## 用法：一条命令，反复跑

```bash
SKILL_DIR=~/.claude/skills/wechat-sticker-submit

$SKILL_DIR/scripts/new_album.sh ~/Desktop/my-album --ip ~/Desktop/ip.png
```

这条命令幂等，卡住就修完再跑同一条：

1. 第一次跑 → 生成 `album.yml` 并停下让你填文案（唯一需要动脑的环节）
2. 填完再跑 → 按含义词条数出图 → 切图 → 机检 → 生成 `submit.md`
3. 机检报 FAIL → 打印「这条该怎么修」，修完再跑

产出的 `submit.md` 是平台表单的逐字段对照表（哪个字段填什么、传哪张图），照抄即可。

自己画好图也能用 —— 8~24 张丢进 `my-album/raw/`，不加 `--ip` 直接跑，从切图接管：

```bash
# 也可以只用单个环节
python3 $SKILL_DIR/scripts/fit_assets.py raw/ out/ --cover raw/01.png --icon raw/01.png
python3 $SKILL_DIR/scripts/check_assets.py out/ --copy out/album.yml   # 退出码 = FAIL 条数
```

## 依赖

- **机检与切图**：Python 3 + [Pillow](https://python-pillow.org/)，无其他依赖，不需要 ImageMagick。
- **批量出图**：`gen_album.sh` 走 [MUSE AV](https://github.com/webkubor) 出图中台 CLI（`museav`）。
  没有这个 CLI 也不影响其余步骤 —— 自己画好图直接从第 3 步切图开始即可。

## 目录

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 7 步主流程 |
| `scripts/new_album.sh` | **一键入口**（幂等）：文案 → 出图 → 切图 → 机检 → 提交清单 |
| `scripts/make_submit.py` | 生成 `submit.md`：平台表单字段 → 值/文件对照表 |
| `references/specs.md` | 官方制作规范全文（表情/形象/特效/艺术家/赞赏/付费）— 数字真源 |
| `references/audit.md` | 官方审核标准全文 + 高频拒因 |
| `references/ip-design.md` | IP 命名 / 简介 / 9 情绪选题 / 含义词写法 |
| `templates/album.yml` | 可被机检解析的文案模板 |
| `scripts/gen_album.sh` | 一张正面照 → 整套原图 |
| `scripts/fit_assets.py` | 源图 → 合规尺寸素材 |
| `scripts/check_assets.py` | 素材 + 文案机检 |

## 免责

规范内容抓取自[微信表情开放平台官方文档](https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications)（2026-08-26），
官方声明其为动态文档。**如与平台当前页面冲突，以平台页面为准。**
本项目不隶属于腾讯，也不保证审核通过 —— 机检只能拦规格问题，创意与权利问题得靠你自己。

投稿素材必须为你原创或拥有版权。垫图请用自己的原图，不要垫他人作品或知名 IP。

## License

MIT
