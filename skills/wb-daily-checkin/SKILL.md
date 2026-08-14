---
name: wb-daily-checkin
description: 使用本机 WorkBuddy 日志中的现有登录态，通过后台 HTTP 请求领取每日签到积分，不移动鼠标或依赖界面坐标。用于用户要求领取或自动领取 WorkBuddy 每日积分、配置 WorkBuddy 加油站签到、daily checkin，或要求以不抢鼠标的方式完成签到时。仅可用于用户本人的本机账号；不得输出、上传或记录完整 JWT。
---

# wb-daily-checkin — WorkBuddy 每日积分自动领取

## 功能

通过 WorkBuddy 内部 API 自动领取每日签到积分（Buddy 加油站），全程后台 HTTP 请求，不移动鼠标、不占用界面、不依赖分辨率/DPI。

## 原理（已逆向 app.asar 并实机验证）

| 用途 | 接口 | 方法 |
|---|---|---|
| 查签到状态 | `https://copilot.tencent.com/v2/billing/meter/checkin-activity-status` | POST |
| 领取积分 | `https://copilot.tencent.com/v2/billing/meter/daily-checkin` | POST |
| v1 兜底领取 | `https://copilot.tencent.com/billing/meter/daily-checkin` | POST |

鉴权头（来自前端 `buildHeaders(session)`）：
- `Authorization: Bearer <JWT>`
- `X-User-Id: <sub>` （JWT payload 的 sub 字段）
- `X-Domain: copilot.tencent.com`
- `Accept / Content-Type: application/json`

JWT 来源：WorkBuddy 运行日志目录（`%APPDATA%\WorkBuddy\logs` 下的 `.log` 文件），Keycloak 签发，有效期约 1 年。

每日刷新时间：**北京时间 00:00**（Asia/Shanghai 自然日翻面）。依据：状态接口 `checkin_dates` 返回北京日历日期，asar 全量使用 `Asia/Shanghai / UTC+8`，含 `setHours(0,0,0,0)` 零点归一化逻辑。

## 前置条件

1. 本机已安装 WorkBuddy 桌面客户端并至少登录过一次（产生日志文件含 JWT）。
2. 本机网络可访问 `copilot.tencent.com`（HTTPS 443）。
3. Python 3.8+（仅用标准库，无需 pip install）。

## 使用方法

### 手动执行

```bash
python scripts/claim_wb_points_api.py
```

退出码：
- `0`：成功（领取成功 / 今日已签到 / 活动未开启自动跳过）
- `1`：领取接口异常
- `2`：JWT 未找到或已过期（需重新登录 WorkBuddy）

### 配合 WorkBuddy 自动化

创建 recurring automation，每天 08:00 执行：
```
python scripts/claim_wb_points_api.py
```
08:00 在 00:00 刷新之后，可验证刷新机制是否生效。

### 调研刷新时间（可选）

```bash
python scripts/investigate_reset.py
```
输出完整的签到状态 JSON 和时区信息，用于确认刷新机制。

## 脚本行为

1. 扫描 `%APPDATA%\WorkBuddy\logs` 下所有 `.log` 文件，提取最新 JWT。
2. 解码 JWT 验证未过期，取出 `sub` 作为 `X-User-Id`。
3. 调 v2 状态接口：
   - `active=false` → 活动未开启，跳过（退出码 0）。
   - `today_checked_in=true` → 今日已签，跳过（退出码 0）。
4. 调 v2 领取接口（v1 兜底）：
   - `code=0` → 领取成功。
   - `msg` 含"已签到" → 服务端防重，跳过。
5. 写日志到 `scripts/claim_api.log`。

## 注意事项

- JWT 过期后脚本会明确报错（退出码 2），不会静默失败。届时需重新打开 WorkBuddy 登录一次以刷新日志。
- `www.codebuddy.cn` 域名在本机会被服务器重置（WinError 10054），唯一可用 API 域是 `copilot.tencent.com`。
- 活动有周期性（如 2026-08-06 ~ 2026-08-13），结束后若官方不开新一期，`active=false` 时脚本自动跳过。
- 脚本幂等：服务端有每日一次防重，多次调用安全。
