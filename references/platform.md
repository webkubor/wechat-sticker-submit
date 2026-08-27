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

## 登录后（待补）

首次投稿跑通后把这几条填上，别让下一次又去摸索：

- [ ] 投稿入口（「提交表情」按钮实际跳到哪）
- [ ] 表情形象的创建/管理页
- [ ] 账号信息 / 付费功能信息（开通付费的入口在这）
- [ ] 账号收入 / 提现
- [ ] 「提交特效」入口

## 账号前置条件

投稿前这些得先有，不然填到一半卡住：

- 注册过平台账号（个人 / 企业），个人号要实名信息并绑定微信号
- 开赞赏还要：艺术家资料审核通过、微信号满足接收赞赏资金要求（企业号绑商户号）
- 开付费还要：至少 1 套已上架专辑、近三个月无违规、大陆储蓄卡（个人）或对公账户（企业）
