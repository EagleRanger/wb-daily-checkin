#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 每日积分领取 - 坐标校准（后台监控 + 自动拟合，纯鼠标无键盘）

用法：
  1. 双击「校准.bat」或运行本脚本
  2. 脚本自动置前 WorkBuddy 窗口，立即开始记录
  3. 手动完成四步：点头像 → 点签到领积分 → 点弹窗签到按钮 → 关闭弹窗
  4. 鼠标停住 3 秒不动 → 自动结束
  5. 脚本自动聚类成 4 个目标坐标，存 wb_points_config.json（相对比例，抗缩放）

原理：监听鼠标左键点击（GetAsyncKeyState 边沿检测，无钩子），按坐标/时间聚类成 4 簇。
路径：全部自动检测，无硬编码。
"""
import os, sys, time, json
import ctypes
import win32gui, win32con, win32api

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_SCRIPT_DIR, "wb_points_config.json")
DEBUG_PATH = os.path.join(_SCRIPT_DIR, "calibrate_debug.log")
SPOT_NAMES = ["avatar", "checkin_menu", "checkin_btn", "close_popup"]

VK_LBUTTON = 0x01


def find_wb_window():
    wins = []
    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.GetClassName(hwnd) == 'Chrome_WidgetWin_1' and 'WorkBuddy' in win32gui.GetWindowText(hwnd):
            wins.append((hwnd, win32gui.GetWindowRect(hwnd)))
    win32gui.EnumWindows(cb, None)
    if not wins:
        return None
    return max(wins, key=lambda x: (x[1][2]-x[1][0]) * (x[1][3]-x[1][1]))


def cluster_4(points):
    import math
    dedup = []
    for x, y, t in points:
        if dedup and abs(x - dedup[-1][0]) < 15 and abs(y - dedup[-1][1]) < 15 and (t - dedup[-1][2]) < 0.4:
            continue
        dedup.append((x, y, t))
    if len(dedup) < 4:
        return None
    clusters = []
    for x, y, t in dedup:
        placed = False
        for c in clusters:
            cx = sum(p[0] for p in c) / len(c)
            cy = sum(p[1] for p in c) / len(c)
            if math.hypot(x - cx, y - cy) < 60:
                c.append((x, y, t))
                placed = True
                break
        if not placed:
            clusters.append([(x, y, t)])
    clusters.sort(key=len, reverse=True)
    top4 = clusters[:4]
    top4.sort(key=lambda c: min(p[2] for p in c))
    return [(sum(p[0] for p in c) / len(c), sum(p[1] for p in c) / len(c)) for c in top4]


def main():
    wb = find_wb_window()
    if not wb:
        print("[!] 未找到 WorkBuddy 窗口，请先打开并显示主界面", flush=True)
        sys.exit(1)
    hwnd, rect = wb
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    rect = win32gui.GetWindowRect(hwnd)
    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    print(f"[*] 窗口尺寸={w}x{h}", flush=True)
    print("=" * 62, flush=True)
    print(" 已开始记录（纯鼠标，无需键盘）", flush=True)
    print(" 手动完成四步：1头像 → 2签到 → 3签到按钮 → 4关闭弹窗", flush=True)
    print(" 完成四步后，鼠标停住 3 秒不动，即自动结束生成配置", flush=True)
    print("=" * 62, flush=True)

    clicks = []
    btn_prev = False
    last_click_time = time.time()

    with open(DEBUG_PATH, "w", encoding="utf-8") as df:
        df.write("开始记录\n")

    while True:
        x, y = win32api.GetCursorPos()

        btn_now = win32api.GetAsyncKeyState(VK_LBUTTON) & 0x8000
        if btn_now and not btn_prev:
            clicks.append((int(x), int(y), time.time()))
            last_click_time = time.time()
            with open(DEBUG_PATH, "a", encoding="utf-8") as df:
                df.write(f"点击 #{len(clicks)}: ({x},{y})\n")
        btn_prev = bool(btn_now)

        if clicks and time.time() - last_click_time >= 3.0:
            print(f"\n>>> 检测到 3 秒无操作，结束记录，共 {len(clicks)} 次点击", flush=True)
            with open(DEBUG_PATH, "a", encoding="utf-8") as df:
                df.write(f"结束记录(3秒无操作)，共 {len(clicks)} 次点击\n")
            break

        time.sleep(0.02)

    print(f"\n[分析] 共 {len(clicks)} 次点击", flush=True)
    for i, (x, y, t) in enumerate(clicks):
        print(f"    {i+1}. ({x},{y})", flush=True)

    centers = cluster_4(clicks)
    if not centers or len(centers) < 4:
        print("[-] 有效点击不足 4 次，无法拟合。请重跑。", flush=True)
        sys.exit(1)

    print("\n[拟合] 4 个目标点：", flush=True)
    cfg = {"_window_size": [w, h], "_note": "相对窗口比例(0~1)"}
    for i, (cx, cy) in enumerate(centers):
        rx = round((cx - x1) / w, 4)
        ry = round((cy - y1) / h, 4)
        cfg[SPOT_NAMES[i]] = [rx, ry]
        print(f"    {SPOT_NAMES[i]}: 绝对({cx:.0f},{cy:.0f}) 相对({rx},{ry})", flush=True)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"\n[+] 配置已保存: {CONFIG_PATH}", flush=True)
    print(json.dumps(cfg, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        err_path = os.path.join(_SCRIPT_DIR, "calibrate_error.log")
        with open(err_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        print("\n[-] 脚本异常，详见 calibrate_error.log", flush=True)
