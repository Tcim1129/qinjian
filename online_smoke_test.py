from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from typing import Any
from urllib import error, parse, request


BASE_URL = os.getenv("QJ_BASE_URL", "http://127.0.0.1:8080/api/v1")


def http_json(
    method: str,
    path: str,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> Any:
    url = f"{BASE_URL}{path}"
    if query:
        url = f"{url}?{parse.urlencode(query)}"

    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc


def poll_daily_report(
    token: str, pair_id: str, timeout_seconds: int = 120
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    latest = None
    while time.time() < deadline:
        latest = http_json(
            "GET",
            "/reports/latest",
            token=token,
            query={"pair_id": pair_id, "report_type": "daily"},
        )
        if latest and latest.get("status") in {"completed", "failed"}:
            return latest
        time.sleep(3)
    raise RuntimeError(f"日报轮询超时，最后状态: {latest}")


def main() -> int:
    suffix = datetime.now().strftime("%m%d%H%M%S")
    password = "QjTest#2026"
    email_a = f"smoke_a_{suffix}@example.com"
    email_b = f"smoke_b_{suffix}@example.com"

    print("[1/8] 注册用户 A")
    register_a = http_json(
        "POST",
        "/auth/register",
        payload={
            "email": email_a,
            "nickname": f"测试A{suffix[-4:]}",
            "password": password,
        },
    )

    print("[2/8] 注册用户 B")
    register_b = http_json(
        "POST",
        "/auth/register",
        payload={
            "email": email_b,
            "nickname": f"测试B{suffix[-4:]}",
            "password": password,
        },
    )

    print("[3/8] 验证登录链路")
    login_a = http_json(
        "POST", "/auth/login", payload={"email": email_a, "password": password}
    )
    login_b = http_json(
        "POST", "/auth/login", payload={"email": email_b, "password": password}
    )
    token_a = login_a["access_token"]
    token_b = login_b["access_token"]

    print("[4/8] 创建配对并邀请加入")
    pair_created = http_json(
        "POST", "/pairs/create", token=token_a, payload={"type": "couple"}
    )
    invite_code = pair_created["invite_code"]
    pair_joined = http_json(
        "POST", "/pairs/join", token=token_b, payload={"invite_code": invite_code}
    )
    pair_id = pair_joined["id"]

    pairs_a = http_json("GET", "/pairs/me", token=token_a)
    pairs_b = http_json("GET", "/pairs/me", token=token_b)
    if not pairs_a or not pairs_b:
        raise RuntimeError("配对创建后未能在双方列表中查询到记录")

    print("[5/8] 双方提交打卡")
    checkin_payload_a = {
        "pair_id": pair_id,
        "content": "今天一起讨论了比赛展示逻辑，沟通顺畅，也约好了晚上复盘。",
        "mood_tags": ["安心", "被支持"],
        "mood_score": 4,
        "interaction_freq": 8,
        "interaction_initiative": "equal",
        "deep_conversation": True,
        "task_completed": True,
    }
    checkin_payload_b = {
        "pair_id": pair_id,
        "content": "今天一起整理了演示内容，感觉对方很愿意倾听，也让我更有信心。",
        "mood_tags": ["轻松", "信任"],
        "mood_score": 4,
        "interaction_freq": 8,
        "interaction_initiative": "equal",
        "deep_conversation": True,
        "task_completed": True,
    }
    http_json("POST", "/checkins/", token=token_a, payload=checkin_payload_a)
    http_json("POST", "/checkins/", token=token_b, payload=checkin_payload_b)

    today_status = http_json(
        "GET", "/checkins/today", token=token_a, query={"pair_id": pair_id}
    )
    if not today_status.get("both_done"):
        raise RuntimeError(f"双方打卡后状态异常: {today_status}")

    print("[6/8] 触发日报生成")
    generated = http_json(
        "POST", "/reports/generate-daily", token=token_a, query={"pair_id": pair_id}
    )
    report_id = generated["id"]

    print("[7/8] 轮询日报结果")
    latest_report = poll_daily_report(token_a, pair_id)
    if latest_report.get("status") != "completed":
        raise RuntimeError(f"日报生成失败: {latest_report}")

    print("[8/8] 验证报告与趋势查询")
    history = http_json(
        "GET",
        "/reports/history",
        token=token_a,
        query={"pair_id": pair_id, "report_type": "daily", "limit": 3},
    )
    trend = http_json(
        "GET", "/reports/trend", token=token_a, query={"pair_id": pair_id, "days": 14}
    )
    streak = http_json(
        "GET", "/checkins/streak", token=token_a, query={"pair_id": pair_id}
    )

    summary = {
        "emails": {"user_a": email_a, "user_b": email_b},
        "pair_id": pair_id,
        "invite_code": invite_code,
        "report_id": report_id,
        "daily_report_status": latest_report.get("status"),
        "daily_report_health_score": latest_report.get("health_score"),
        "daily_report_insight": (latest_report.get("content") or {}).get("insight"),
        "history_count": len(history),
        "trend_points": len(trend.get("trend", [])),
        "trend_direction": trend.get("direction"),
        "streak": streak.get("streak"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"线上冒烟测试失败: {exc}", file=sys.stderr)
        raise
