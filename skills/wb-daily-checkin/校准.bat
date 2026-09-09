@echo off
chcp 65001 >nul
cd /d "%~dp0scripts"
echo ============================================
echo  WorkBuddy 积分领取 - 后台监控校准
echo ============================================
echo.
echo  启动后立即开始记录：
echo    手动完成四步（点头像 - 点签到 - 点弹窗签到按钮 - 关闭弹窗）
echo    完成后鼠标停住 3 秒不动，即自动结束生成配置
echo.
python -u calibrate_wb_points.py 2>&1
echo.
echo ============ 程序结束 (退出码 %errorlevel%) ============
pause
