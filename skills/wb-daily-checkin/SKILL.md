---
name: wb-daily-checkin
description: 在 Windows 本机通过用户自行校准的 WorkBuddy 界面坐标执行每日签到积分领取。用于用户要求配置、校准、试跑或执行 WorkBuddy 签到自动化；不得直接复用其他机器的坐标，也不得把点击序列完成当作签到结果已验证。
---

# WorkBuddy 每日签到（界面坐标版）

## 当前路线

WorkBuddy 更新后，旧版内部 API/JWT 路线已失效。当前版本只通过本地桌面界面完成四步点击：头像、签到领积分、签到按钮、关闭弹窗。不要调用旧版 `claim_wb_points_api.py`，也不要搜索、读取或上传 WorkBuddy JWT。

## 运行前置

- 仅操作用户本人已登录的 Windows 本机 WorkBuddy。
- 真实点击会移动鼠标、切换前台窗口并产生账号侧效果。只在用户已明确要求执行签到，或有效的定时任务已明确授权时运行真实点击。
- 确认 Python 3.8+ 可用，并从 Skill 根目录执行 `python -m pip install -r requirements.txt`。
- 不得携带或发布 `wb_points_config.json`、`claim_ui.log`、`calibrate_debug.log` 或 `calibrate_error.log`。

## 首次配置

1. 让用户打开并登录 WorkBuddy，选定以后定时执行时使用的屏幕、分辨率、Windows 缩放比例和窗口大小。
2. 运行 `校准.bat` 或 `python -u scripts/calibrate_wb_points.py`。
3. 校准脚本启动后，请用户手动完成四步点击，期间不要点击其他位置；完成后将鼠标静置 3 秒。
4. 读回 `scripts/wb_points_config.json`：必须包含 `avatar`、`checkin_menu`、`checkin_btn`、`close_popup`，每个点都是两个 0–1 之间的数值。任何额外点击、顺序错误、缺点或越界都应重新校准，不应手猜修改。
5. 运行 `python scripts/claim_wb_points.py --dry`。这只验证配置能被读取并计算当前窗口坐标，不会点击，也不证明按钮对齐。
6. 首次真实试跑必须由用户在场观察。确认四步均点中正确控件，并从 WorkBuddy 页面确认当日状态或积分变化后，才能把这台机器的配置标记为可用。

## 坐标重校准规则

相对比例只是减少窗口移动和等比缩放的影响，不是界面识别。遇到以下任一情况，停止真实点击并重新校准：

- 另一台电脑或另一个 Windows 用户；
- 分辨率、显示缩放、主显示器、WorkBuddy 界面缩放或窗口常用尺寸改变；
- WorkBuddy 版本、菜单、弹窗、语言、主题或侧边栏状态变化；
- 打印的坐标与目标控件不再对齐，或一次试跑发生误点。

定时执行时保持与校准时相同的常用窗口状态，并确保桌面未锁定、远程桌面未断开且执行期间无人操作鼠标。

## 每日执行与验收

执行 `python scripts/claim_wb_points.py`。

- 无配置、缺少坐标、找不到 WorkBuddy 窗口或启动失败时，本次应停止并报告，不得猜测默认坐标。
- 退出码 `0` 只表示点击序列执行完毕。脚本没有视觉识别或服务端状态校验，因此不能据此声称签到成功。
- 在定时任务中保留 `scripts/claim_ui.log`，用于区分未启动、未找到窗口、坐标序列已执行和尚未验证签到结果。

## 文件

- `scripts/calibrate_wb_points.py`：监控鼠标点击并生成本机坐标配置。
- `scripts/claim_wb_points.py`：置前 WorkBuddy 并执行四步点击。
- `校准.bat`：Windows 双击校准入口。
- `requirements.txt`：Python 依赖。
