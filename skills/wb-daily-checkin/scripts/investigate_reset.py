#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 签到刷新时间调研脚本 — 输出完整签到状态 JSON 和时区信息。
用于确认每日刷新机制。仅用标准库。
"""

import os, re, json, base64, ssl, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

# --- 自动检测日志目录 ---
_APPDATA = os.environ.get("APPDATA", "")
if _APPDATA:
    base = os.path.join(_APPDATA, "WorkBuddy", "logs")
else:
    base = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")),
                        "AppData", "Roaming", "WorkBuddy", "logs")

jwt_re = re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')
best = []
for root, _, fs in os.walk(base):
    for f in fs:
        if not f.endswith('.log'):
            continue
        fp = os.path.join(root, f)
        try:
            data = open(fp, 'r', encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        for m in jwt_re.finditer(data):
            best.append((os.path.getmtime(fp), m.group(0)))
if not best:
    print("ERROR: 未找到 JWT，请先登录 WorkBuddy。")
    raise SystemExit(2)
best.sort(reverse=True)
jwt = best[0][1]
payload = json.loads(base64.urlsafe_b64decode(
    jwt.split('.')[1] + '=' * (-len(jwt.split('.')[1]) % 4)))
uid = payload['sub']


def post(path, body=b'{}'):
    url = f"https://copilot.tencent.com{path}"
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header("Authorization", f"Bearer {jwt}")
    req.add_header("X-User-Id", str(uid))
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Domain", "copilot.tencent.com")
    try:
        r = urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context())
        return r.status, r.read().decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'ignore')
    except Exception as e:
        return "ERR", repr(e)


print("=== 本机/UTC 时间 ===")
print("local now:", datetime.now().astimezone().isoformat())
print("UTC now  :", datetime.now(timezone.utc).isoformat())
print("Beijing   :", (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat())
print()

print("=== v2 checkin-activity-status (完整) ===")
st, body = post("/v2/billing/meter/checkin-activity-status")
print("HTTP", st)
try:
    print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
except Exception:
    print(body[:1500])
print()

print("=== v1 checkin-status (完整, 作对照) ===")
st2, body2 = post("/billing/meter/checkin-status")
print("HTTP", st2)
try:
    print(json.dumps(json.loads(body2), ensure_ascii=False, indent=2))
except Exception:
    print(body2[:1500])
print()

# 看返回里是否有 reset / next / 刷新 / 下次 等字段
for b in (body, body2):
    for kw in ['reset', 'next', '刷新', '下次', 'expire', 'deadline', 'reset_at', 'reset_time', 'next_time']:
        if kw in b.lower():
            print(f"[命中关键字] {kw} 出现在返回中")
