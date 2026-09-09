#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 每日积分领取 - UI 点击版（相对比例坐标，抗窗口缩放）

四步：
  1. 点头像（左下角）展开菜单
  2. 点「签到领积分 / Buddy 加油站」那一行
  3. 点弹窗里的签到按钮
  4. 关闭弹窗

窗口定位：Chrome_WidgetWin_1 + 标题 WorkBuddy（Electron）。
坐标：读取 calibrate_wb_points.py 生成的相对比例配置，按当前窗口 rect 换算绝对坐标。
路径：全部自动检测，无硬编码。坐标配置必须由每台机器自行校准。
"""
import json, os, sys, time, datetime, argparse
import win32gui, win32con, win32api
import ctypes

# --- 路径自动检测（无硬编码） ---
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_SCRIPT_DIR, "wb_points_config.json")
LOG_PATH = os.path.join(_SCRIPT_DIR, "claim_ui.log")

# WorkBuddy.exe 安装路径（标准位置 + 注册表回退）
def find_wb_exe():
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Programs", "WorkBuddy", "WorkBuddy.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""),
                     "AppData", "Local", "Programs", "WorkBuddy", "WorkBuddy.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]  # 返回标准路径（即使不存在，用于错误提示）

WB_EXE = find_wb_exe()

try:
    import pyautogui
except Exception:
    print("[-] 请先安装 pyautogui: pip install pyautogui")
    sys.exit(1)

# FAILSAFE 会在鼠标位于屏幕左上角时中止脚本。
# 无人值守定点点击不需要这个保护，反而会因鼠标恰好停在左上角而误伤
# （实测 09-02 发生过一次 FailSafe 误中止），故显式关闭。
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def find_wb_window():
    """找最大可见的 WorkBuddy 主窗口。"""
    wins = []
    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        cls = win32gui.GetClassName(hwnd)
        text = win32gui.GetWindowText(hwnd)
        if cls == 'Chrome_WidgetWin_1' and 'WorkBuddy' in text:
            rect = win32gui.GetWindowRect(hwnd)
            wins.append((hwnd, text, rect))
    win32gui.EnumWindows(cb, None)
    if not wins:
        return None
    return max(wins, key=lambda x: (x[2][2]-x[2][0]) * (x[2][3]-x[2][1]))


def find_wb_window_any():
    """找 WorkBuddy 窗口，不要求可见（含最小化/被移到屏幕外的情况）。"""
    wins = []
    def cb(hwnd, _):
        cls = win32gui.GetClassName(hwnd)
        text = win32gui.GetWindowText(hwnd)
        if cls == 'Chrome_WidgetWin_1' and 'WorkBuddy' in text:
            rect = win32gui.GetWindowRect(hwnd)
            wins.append((hwnd, text, rect))
    win32gui.EnumWindows(cb, None)
    if not wins:
        return None
    return max(wins, key=lambda x: (x[2][2]-x[2][0]) * (x[2][3]-x[2][1]))


def count_wb_processes():
    """统计 WorkBuddy 进程数。
    注意：tasklist 在中文 Windows 输出 GBK 编码，不能用 text=True，
    否则 UnicodeDecodeError 导致始终返回 -1，进程判断失效。
    """
    import subprocess
    try:
        raw = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WorkBuddy.exe"],
            capture_output=True, timeout=15
        ).stdout
        out = raw.decode("gbk", errors="ignore")
        return sum(1 for line in out.splitlines()
                   if line.lower().startswith("workbuddy.exe"))
    except Exception:
        return -1


def ensure_workbuddy_running(timeout=90):
    """三级自愈：有可见窗口 → 还原隐藏窗口 → 启动 exe。"""
    wb = find_wb_window()
    if wb:
        log("[*] WorkBuddy 已有可见窗口")
        return wb[0], wb[1]

    hidden = find_wb_window_any()
    if hidden:
        hwnd, text, _ = hidden
        log(f"[*] 发现不可见/最小化窗口 {text!r}，尝试还原")
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(1.0)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(1.0)
        except Exception as e:
            log(f"   还原失败: {e}")
        if find_wb_window():
            log("[+] 窗口已还原")
            return hwnd, text
        log("   还原后仍不可见，继续尝试启动")

    n = count_wb_processes()
    log(f"[!] 未找到可见窗口；WorkBuddy 进程数={n}")

    if n == 0:
        if not os.path.exists(WB_EXE):
            log(f"[-] 未找到 WorkBuddy.exe: {WB_EXE}")
            return None
        log(f"[*] 启动 WorkBuddy: {WB_EXE}")
        try:
            import subprocess
            subprocess.Popen([WB_EXE], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True)
        except Exception as e:
            log(f"[-] 启动失败: {e}")
            return None
    else:
        log("[*] 进程已在运行，等待窗口出现")

    log(f"[*] 轮询等待窗口出现（最多 {timeout}s）...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        wb = find_wb_window()
        if wb:
            elapsed = int(time.time() - t0)
            log(f"[+] 窗口已出现（等待 {elapsed}s）: {wb[1]!r}")
            return wb[0], wb[1]
        time.sleep(2)
    log("[-] 等待超时，窗口仍未出现")
    return None


def bring_to_front(hwnd):
    """强制置前（5 层组合拳绕过 Windows 后台抢焦点限制）。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.3)

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    try:
        fg = win32gui.GetForegroundWindow()
        cur_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        fg_thread = ctypes.windll.user32.GetWindowThreadProcessId(fg, None)
        target_thread = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        ctypes.windll.user32.AttachThreadInput(cur_thread, fg_thread, True)
        ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, True)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        ctypes.windll.user32.AttachThreadInput(cur_thread, fg_thread, False)
        ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, False)
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001)
        time.sleep(0.2)
        ctypes.windll.user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0002 | 0x0001)
    except Exception:
        pass

    try:
        win32api.keybd_event(0x12, 0, 0, 0)
        win32api.keybd_event(0x12, 0, 2, 0)
    except Exception:
        pass

    time.sleep(0.8)
    return win32gui.GetWindowRect(hwnd)


def click_at(x, y):
    pyautogui.moveTo(x, y, duration=0.25)
    time.sleep(0.15)
    pyautogui.click(x, y)
    time.sleep(0.25)


def run_claim(dry=False):
    if not os.path.exists(CONFIG_PATH):
        log("[-] 未找到坐标配置，请先运行 calibrate_wb_points.py")
        return False
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    required = ["avatar", "checkin_menu", "checkin_btn", "close_popup"]
    missing = [k for k in required if k not in cfg]
    if missing:
        log(f"[-] 配置缺少坐标: {missing}")
        return False

    got = ensure_workbuddy_running()
    if not got:
        log("[-] 无法获取 WorkBuddy 窗口，本次领取失败")
        return False
    hwnd, text = got
    log(f"[*] 窗口: {text!r}")

    if dry:
        rect = win32gui.GetWindowRect(hwnd)
    else:
        rect = bring_to_front(hwnd)

    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    log(f"[*] 窗口 rect={rect} 尺寸={w}x{h}")

    steps = [
        ("avatar",       "点头像展开菜单"),
        ("checkin_menu", "点签到领积分"),
        ("checkin_btn",  "点弹窗签到按钮"),
        ("close_popup",  "关闭弹窗"),
    ]
    for key, desc in steps:
        rx, ry = cfg[key]
        ax = int(x1 + rx * w)
        ay = int(y1 + ry * h)
        if dry:
            log(f"[DRY] {desc} -> 绝对({ax},{ay}) 相对({rx},{ry})")
        else:
            log(f"[*] {desc} -> 绝对({ax},{ay}) 相对({rx},{ry})")
            click_at(ax, ay)
            time.sleep(1.0)
    log("[+] 点击序列执行完毕；尚未验证 WorkBuddy 签到状态")
    return True


def main():
    parser = argparse.ArgumentParser(description="WorkBuddy 每日积分领取（UI 点击版）")
    parser.add_argument("--dry", action="store_true", help="只打印坐标，不点击")
    args = parser.parse_args()
    try:
        ok = run_claim(dry=args.dry)
        sys.exit(0 if ok else 1)
    except Exception as e:
        log(f"[-] 异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
