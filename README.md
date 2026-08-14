# WorkBuddy 每日签到 Skill

`wb-daily-checkin` 是一个供 Codex 等 Agent Skills 兼容工具使用的本地 Skill。它从本机 WorkBuddy 日志读取现有登录态，通过后台 HTTP 请求检查并领取每日签到积分，不移动鼠标，也不依赖窗口、分辨率或界面坐标。

当前版本：`v1.0.0`

## 功能

- 检查签到活动是否开启；
- 今日已签到时自动跳过；
- 自动领取当日积分；
- v2 接口失败时尝试 v1 领取接口；
- 仅使用 Python 标准库；
- 可配合 Codex recurring automation 定时执行。

## 安装

将 [`skills/wb-daily-checkin`](skills/wb-daily-checkin) 整个目录复制到 Codex Skills 目录，并保持 `SKILL.md` 位于该 Skill 根目录。

也可以从 Releases 下载 ZIP，解压后安装其中的 `wb-daily-checkin` 文件夹。

## 使用

本机需要已经安装并登录过 WorkBuddy，并具备 Python 3.8 或更高版本。

在 Skill 根目录运行：

```powershell
python scripts/claim_wb_points_api.py
```

退出码：

- `0`：领取成功、今日已经签到，或当前没有活动；
- `1`：领取接口未返回成功；
- `2`：未找到有效登录态，需要重新登录 WorkBuddy。

可选的状态调查脚本：

```powershell
python scripts/investigate_reset.py
```

## 隐私与安全边界

- 仓库和发布包不包含任何真实 JWT、账号、昵称或本机日志。
- 脚本只在运行时读取本机 `%APPDATA%\WorkBuddy\logs`。
- 完整 JWT 仅用于向 WorkBuddy 服务发送鉴权请求，不应输出、上传或分享。
- `scripts/claim_api.log` 会在本机记录 UID、昵称和账号字段；请勿公开该运行日志。
- 本项目调用 WorkBuddy 客户端当前使用的内部接口，接口、活动规则或服务条款变化后可能失效。
- 仅用于用户本人已经登录并有权操作的本机账号。

## 许可证

[MIT](LICENSE)
