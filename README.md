# WorkBuddy 每日签到 Skill（坐标点击版）

`wb-daily-checkin` 是一个供 Codex 等 Agent Skills 兼容工具使用的 Windows 本地 Skill。它在 WorkBuddy 客户端中按顺序点击“头像 → 签到领积分 → 签到按钮 → 关闭弹窗”。

当前版本：`v2.0.0`

> v1.0.0 使用的 WorkBuddy 内部接口已随软件更新失效。v2.0.0 改用本地界面坐标点击，不再读取 JWT，也不直接调用签到接口。

## 关键边界：每台电脑都要先校准

脚本保存的是按钮相对 WorkBuddy 窗口的宽高比例，可以吸收一部分窗口移动和等比缩放差异，但不能保证跨机器直接通用。接收方不应复制别人的 `wb_points_config.json`，而应在自己电脑、自己常用的窗口状态下重新校准。

以下情况都应重新校准：

- 更换屏幕、分辨率、Windows 显示缩放比例或主显示器；
- 改变 WorkBuddy 窗口大小、最大化状态或界面缩放；
- WorkBuddy 升级后菜单、按钮、弹窗或文字位置发生变化；
- 更换系统语言、主题、侧边栏状态，或发现试跑坐标与按钮不再对齐。

## 安装

1. 安装 Windows 10/11、WorkBuddy 桌面客户端和 Python 3.8+。
2. 将 [`skills/wb-daily-checkin`](skills/wb-daily-checkin) 整个目录复制到 Codex Skills 目录。也可以从 Releases 下载 ZIP，解压后安装其中的 `wb-daily-checkin` 文件夹。
3. 进入复制后的 `wb-daily-checkin` 目录并安装依赖：

```powershell
Set-Location "$env:USERPROFILE\.codex\skills\wb-daily-checkin"
python -m pip install -r requirements.txt
```

## 首次对接流程

1. 打开并登录本人的 WorkBuddy，把窗口调整到以后定时执行时会保持的常用大小和屏幕。
2. 双击 Skill 目录下的 `校准.bat`。
3. 校准开始后，手动依次点击：头像、签到领积分、弹窗签到按钮、关闭弹窗。期间不要点其他位置；完成后将鼠标停住 3 秒。
4. 确认 `scripts/wb_points_config.json` 已生成，且四个点的比例都介于 0 和 1 之间。若记录了额外点击或顺序不对，直接重新校准，不要手猜坐标。
5. 先做无点击试跑：

```powershell
python scripts/claim_wb_points.py --dry
```

6. `--dry` 只会计算和打印坐标，不能证明按钮真实对齐。首次真实执行必须由本人在场观察；确认四步均点中正确控件后，再放入定时任务。

## 每日执行

```powershell
python scripts/claim_wb_points.py
```

运行时会移动鼠标、抢占前台并点击界面。执行期间不要操作鼠标，也不要让其他窗口遮挡 WorkBuddy。锁屏、断开的远程桌面或无交互桌面可能使界面点击失效。

退出码 `0` 只代表四步点击序列已执行，不代表脚本已识别服务端签到结果。需要通过 WorkBuddy 页面上的当日状态或积分变化完成验收。

## 隐私与安全

- 仅用于用户本人已登录且有权操作的本机 WorkBuddy 账号。
- 发布包不包含账号、JWT、个人坐标配置或运行日志。
- `wb_points_config.json`、`claim_ui.log`、`calibrate_debug.log` 和 `calibrate_error.log` 只应保留在当地。
- 坐标点击依赖界面稳定性；任何版式变化都可能导致误点，不能把脚本运行完成当作签到成功。

## 版本说明

- `v1.0.0`：内部 API/JWT 版，已因 WorkBuddy 升级失效，仅作历史留档。
- `v2.0.0`：坐标校准与界面点击版，为当前主分支。

## 贡献

- EagleRanger：坐标点击方案、实机开发与需求验收。
- OpenAI Codex：Skill 规范化、迁移引导、风险边界、打包验证与发布协作。

## 许可证

[MIT](LICENSE)
