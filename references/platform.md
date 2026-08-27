# 平台地图（真实 URL，别猜）

微信表情开放平台的路径分两套 CGI 前缀，**猜不出来**：
文档类走 `mmemoticon-bin/readtemplate?t=...`，站点页面走 `mmemoticonwebnode-bin/pages/...`。
我第一次凭常识拼了 `/cgi-bin/mmemoticon-bin/index`，直接 404。所以路径一律照抄这里。

探测时间 2026-08-27。**未登录状态**能确认的部分已标注；登录后的路径待首次投稿时补。

## 免登录可达

| 用途 | URL |
|---|---|
| 首页 / 登录入口 | <https://sticker.weixin.qq.com/cgi-bin/mmemoticonwebnode-bin/pages/home> |
| 注册 | <https://sticker.weixin.qq.com/cgi-bin/mmemoticonwebnode-bin/pages/signup> |
| 制作规范（数字真源） | <https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications> |
| 审核标准 | <https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/auditingStandards> |
| 注册指引 | 同上 `#/loginGuides` |
| 常见问题 | 同上 `#/commonQuestions` |
| 权利说明（版权/肖像权） | 同上 `#/noteRights` |
| 表情推广（视频号/公众号/小程序/红包封面） | 同上 `#/promotion` |
| 平台公告 | <https://sticker.weixin.qq.com/cgi-bin/mmemoticonwebnode-bin/pages/ver/bulletin/list> |
| 表情热度榜 | <https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/emoticonview?oper=billboard&t=rank> |
| 服务协议 | `readtemplate?t=deal/service` |
| 侵权投诉 | `readtemplate?t=complain/index` |

规范页是 hash 路由的 SPA：`WebFetch` 只能拿到空壳，**必须用浏览器打开再取 `document.body.innerText`**。

## 登录

首页右上「登录」是 `javascript:;`，点开是个弹层，两个选项：

- **使用微信扫码登录** —— 弹层里的二维码是 `data:image/png;base64,...` 内嵌图
- **账号密码登录**

扫码这步只能账号本人做，agent 代不了。用 `ego-browser` 的 `handOffTaskSpace` 把浏览器交还给人，
等对方确认登录完成后再 `takeOverTaskSpace` 接手填表单。

顺带一条定位经验：「登录」这个词在页面里出现多次（导航项、弹层标题都有），
按 `snapshotText` 的 ref 去点容易点空。稳的做法是按精确文本 + `offsetParent` 非空筛出可见元素，
拿它的中心坐标点：

```js
[...document.querySelectorAll('a,button,div,span')]
  .find(e => (e.innerText || '').trim() === '登录' && e.offsetParent)
```

## 登录后（2026-08-27 实测）

| 用途 | URL |
|---|---|
| 工作台「我的表情」 | `/cgi-bin/mmemoticon-bin/readtemplate?t=home/index` |
| 专辑详情 | `/cgi-bin/mmemoticonwebnode-bin/pages/stickerPage/setting?stikerid=<id>` |
| 专辑编辑（含完整表单） | `/cgi-bin/mmemoticonwebnode-bin/pages/stickerPage/detail?stikerid=<id>` |
| 艺术家资料 | `/cgi-bin/mmemoticon-bin/userpage` |
| 账号信息（实名） | `/cgi-bin/mmemoticon-bin/realnamepage?t=account/message&action=refill` |
| 账号收入 / 提现 | `/cgi-bin/mmemoticon-bin/realnamepage?t=income/index` |
| 修改密码 | `/cgi-bin/mmemoticon-bin/changepwd?t=account/change_pwd` |
| 站内通知 | `/cgi-bin/mmemoticon-bin/readtemplate?t=notify/index` |
| 表情形象说明 | `/cgi-bin/mmemoticon-bin/readtemplate?t=notify/ip` |

工作台上「创建形象」「提交作品」「详情」都是 `javascript:;` 的按钮，没有独立 URL，
只能按可见文本定位点击。

**审核不通过的原因不在站内**：专辑详情页只显示「未通过审核」四个字，
编辑页也没有驳回说明，站内通知里只有红包封面奖励之类。
拒因走「微信表情开放平台」公众号推送 —— 要问作者本人看手机。

## 提交表单的完整字段（编辑页实测）

⚠️ 规范文档里只讲了素材规格与文案字数，**「附加信息」这一整块分类字段文档里没写**，
但提交时必填。字段与选项照抄如下。

### 上传表情
- 类型：`静态表情` / `动态表情`（同一套只能选一种）
- 表情文件：JPG、PNG 或 GIF，支持批量拖拽

### 基本信息
| 字段 | 上限 | 格式 |
|---|---|---|
| 名称 | 8 字 | — |
| 介绍 | 80 字 | — |
| 版权 | 10 字 | — |
| 横幅 | — | JPG 或 PNG |
| 封面 | — | PNG |
| 图标 | — | PNG |

### 附加信息（文档里没有，实际必填）

- **类型**：`真人拍摄` / `表情截图` / `表情卡通` / `表情其他`
- **角色/内容**：先选大类再选具体（如 `宠物/动物角色` → `猫`）
  > ⚠️ 硬约束：**角色出现在表情里的个数不少于表情总个数的三分之一**
- **表情风格**：选 1~2 项
  `日常` `软萌可爱` `二次元` `长辈风` `搞笑` `丧/佛系` `魔性鬼畜` `恶搞`
  `简笔画` `赛博朋克` `蒸汽波` `像素` `暗黑` `复古`
- **表情主题**：
  `万能通用` `网络热点` `节日` `考试/学习` `工作/职场` `情侣` `毕业` `刷屏`
  `红包相关` `游戏` `运动/健身` `怼人/斗图` `群聊必备` `节气` `邀约/约起来` `励志鼓舞`
  > ⚠️ 硬约束：**与主题相关的表情个数应不少于表情总数的一半**
- **上架地区**：中国大陆
- **下载地区**：`全球` / `中国大陆`
- **表情赞赏**（选填）：接受赞赏 + 引导语（≤15 字）+ 引导图 + 致谢图
- **版权证明**（选填）：`涉及肖像权授权` / `涉及版权授权` + 证明文件
  （JPG/PNG/BMP/PDF，每个 ≤10MB，可批量）

页面底部是「保存」和「提交」两个按钮 —— **保存是草稿，提交才进审核队列**。

## 重投规则（踩过的坑）

官方明文「平台不允许提交重复的表情」。所以一套审核未通过的专辑要重投，
**是在原专辑上编辑后再提交，不是新建一套**。新建会撞重复。

## 账号前置条件

投稿前这些得先有，不然填到一半卡住：

- 注册过平台账号（个人 / 企业），个人号要实名信息并绑定微信号
- 开赞赏还要：艺术家资料审核通过、微信号满足接收赞赏资金要求（企业号绑商户号）
- 开付费还要：至少 1 套已上架专辑、近三个月无违规、大陆储蓄卡（个人）或对公账户（企业）
