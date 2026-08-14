#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 每日积分领取 — 内部 API 版（不抢鼠标，不依赖界面坐标）

原理（已逆向 app.asar 并实机验证）：
  - 签到状态: POST https://copilot.tencent.com/v2/billing/meter/checkin-activity-status
  - 领取积分: POST https://copilot.tencent.com/v2/billing/meter/daily-checkin  (v1 /billing/meter/daily-checkin 兜底)
  - 鉴权头(来自前端 buildHeaders):
        Authorization: Bearer <JWT>
        X-User-Id: <sub>
        X-Domain: copilot.tencent.com
        Accept / Content-Type: application/json
  - JWT 取自 WorkBuddy 运行日志（Keycloak realm=copilot，exp 约 1 年）

特点：
  - 全程后台 HTTP 请求，不移动/占用鼠标，不要求窗口可见，不依赖 DPI/分辨率。
  - 幂等：今日已签到则自动跳过（服务端也有每日一次防重）。
  - 活动未开启时自动跳过。
  - 仅用 Python 标准库，无需 pip install。
"""

import os
import re
import sys
import json
import ssl
import base64
import datetime
import urllib.request
import urllib.error

# --- 自动检测 WorkBuddy 日志目录（兼容 Windows） ---
_APPDATA = os.environ.get("APPDATA", "")
if _APPDATA:
    LOGS_DIR = os.path.join(_APPDATA, "WorkBuddy", "logs")
else:
    _USERPROFILE = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    LOGS_DIR = os.path.join(_USERPROFILE, "AppData", "Roaming", "WorkBuddy", "logs")

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "claim_api.log")
API_HOST = "copilot.tencent.com"
DOMAIN = "copilot.tencent.com"
# 每日刷新时间（已逆向 app.asar 并实机核验）：服务端按 Asia/Shanghai 自然日结算，
# 零点归一化 setHours(0,0,0,0)，签到态在 北京时间 00:00 翻日刷新。
RESET_NOTE = "每日刷新时间: 北京时间 00:00 (Asia/Shanghai 自然日翻面)"


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def b64url_decode(b):
    b += "=" * (-len(b) % 4)
    return base64.urlsafe_b64decode(b)


def extract_jwt():
    """扫描 WorkBuddy 日志，取最新出现的 JWT。"""
    jwt_re = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
    candidates = []
    if not os.path.isdir(LOGS_DIR):
        return None
    for root, _, files in os.walk(LOGS_DIR):
        for fn in files:
            if not fn.endswith(".log"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    data = fh.read()
            except Exception:
                continue
            for m in jwt_re.finditer(data):
                candidates.append((os.path.getmtime(fp), m.group(0)))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def decode_claims(jwt):
    try:
        return json.loads(b64url_decode(jwt.split(".")[1]))
    except Exception:
        return {}


def post(path, jwt, uid, body=b"{}"):
    url = f"https://{API_HOST}{path}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {jwt}")
    req.add_header("X-User-Id", str(uid))
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Domain", DOMAIN)
    ctx = ssl.create_default_context()
    try:
        r = urllib.request.urlopen(req, timeout=20, context=ctx)
        return r.status, json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "ignore"))
        except Exception:
            return e.code, {"raw": e.read().decode("utf-8", "ignore")[:300]}
    except Exception as e:
        return "ERR", {"error": repr(e)}


def main():
    jwt = extract_jwt()
    if not jwt:
        log("ERROR: 未在日志中找到 JWT 登录态，无法领取。请先打开一次 WorkBuddy 产生日志。")
        return 2
    claims = decode_claims(jwt)
    exp = claims.get("exp")
    if exp and exp < datetime.datetime.now().timestamp():
        log(f"ERROR: JWT 已过期 (exp={datetime.datetime.fromtimestamp(exp)})，需重新登录 WorkBuddy 后再次提取。")
        return 2
    uid = claims.get("sub")
    if not uid:
        log("ERROR: JWT 中缺少 sub(uid)，无法构造 X-User-Id。")
        return 2
    log(f"JWT OK | uid={uid} | nickname={claims.get('nickname')} | 账号={claims.get('preferred_username')}")

    # 1) 活动状态（用 v2，v1 状态接口已废弃返回 active=false）
    st_code, st = post("/v2/billing/meter/checkin-activity-status", jwt, uid)
    log(f"活动状态: HTTP {st_code} | code={st.get('code')} | msg={st.get('msg')}")
    data = (st.get("data") or {}) if isinstance(st, dict) else {}
    active = data.get("active")
    today_done = data.get("today_checked_in")
    log(f"  {RESET_NOTE}")
    log(
        f"  active={active} | today_checked_in={today_done} | streak_days={data.get('streak_days')}"
        f" | today_credit={data.get('today_credit')} | total_credits={data.get('total_credits')}"
        f" | 活动={data.get('activity_name')} | 周期={data.get('start_time')} ~ {data.get('end_time')}"
    )

    if active is False:
        log("当前签到活动未开启 (active=false)，跳过。")
        return 0
    if today_done is True:
        log("【验证】今日签到态已生效，刷新机制正常（次日北京时间 00:00 后可再次领取）。无需重复领取。")
        return 0

    # 2) 领取：v2 优先，v1 兜底
    for path in ("/v2/billing/meter/daily-checkin", "/billing/meter/daily-checkin"):
        c_code, c = post(path, jwt, uid)
        log(f"领取 {path}: HTTP {c_code} | {json.dumps(c, ensure_ascii=False)[:300]}")
        if isinstance(c, dict):
            code = c.get("code")
            if code == 0:
                log("领取成功！")
                return 0
            msg = c.get("msg", "")
            if "已签到" in msg or "今天" in msg:
                log("服务端提示今日已签到，无需重复。")
                return 0
        # 否则继续尝试下一个端点
    log("领取接口均未返回成功，请人工检查。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
