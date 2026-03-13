from __future__ import annotations

import json
import os
import sys
import time
import base64
from datetime import datetime
from uuid import uuid4
from urllib import error, parse, request

import paramiko


BASE_URL = os.getenv("QJ_BASE_URL", "http://127.0.0.1:8080/api/v1")
REMOTE_HOST = os.getenv("QJ_REMOTE_HOST", "")
REMOTE_USER = os.getenv("QJ_REMOTE_USER", "root")
REMOTE_PASSWORD = os.getenv("QJ_REMOTE_PASSWORD", "")
REMOTE_ROOT = os.getenv("QJ_REMOTE_ROOT", "/opt/qinjian")


def http_json(
    method: str,
    path: str,
    token: str | None = None,
    payload: dict | None = None,
    query: dict | None = None,
    timeout: int = 180,
):
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
        with request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc


def poll_latest_report(
    token: str, pair_id: str, report_type: str, timeout_seconds: int = 420
):
    deadline = time.time() + timeout_seconds
    latest = None
    while time.time() < deadline:
        latest = http_json(
            "GET",
            "/reports/latest",
            token=token,
            query={"pair_id": pair_id, "report_type": report_type},
            timeout=180,
        )
        if latest and latest.get("status") in {"completed", "failed"}:
            return latest
        time.sleep(3)
    raise RuntimeError(f"轮询 {report_type} 报告超时，最后结果: {latest}")


def run_remote_sql(sql: str) -> None:
    if not REMOTE_HOST or not REMOTE_PASSWORD:
        raise RuntimeError(
            "缺少远端 SSH 配置，请设置 QJ_REMOTE_HOST 和 QJ_REMOTE_PASSWORD"
        )

    encoded_sql = base64.b64encode(sql.encode("utf-8")).decode("ascii")
    command = (
        f"cd {REMOTE_ROOT} && "
        f"printf '%s' '{encoded_sql}' | base64 -d | "
        f"docker compose exec -T db sh -lc 'cat >/tmp/qj_periodic_test.sql && psql -U qinjian -d qinjian -f /tmp/qj_periodic_test.sql; status=$?; rm -f /tmp/qj_periodic_test.sql; exit $status'"
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASSWORD, timeout=30
    )
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=600)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="ignore")
        error_text = stderr.read().decode("utf-8", errors="ignore")
        if exit_code != 0:
            raise RuntimeError(error_text or output or "远端 SQL 执行失败")
    finally:
        client.close()


def set_latest_daily_dates(pair_id: str, target_date: str) -> None:
    run_remote_sql(
        "UPDATE checkins SET checkin_date = DATE '{target_date}' "
        "WHERE pair_id = '{pair_id}' AND id IN ("
        "SELECT id FROM checkins WHERE pair_id = '{pair_id}' ORDER BY created_at DESC LIMIT 2"
        ");"
        "UPDATE reports SET report_date = DATE '{target_date}' "
        "WHERE id = (SELECT id FROM reports WHERE pair_id = '{pair_id}' AND type = 'DAILY' ORDER BY created_at DESC LIMIT 1);".format(
            pair_id=pair_id, target_date=target_date
        )
    )


def set_latest_weekly_date(pair_id: str, target_date: str) -> None:
    run_remote_sql(
        "UPDATE reports SET report_date = DATE '{target_date}' "
        "WHERE id = (SELECT id FROM reports WHERE pair_id = '{pair_id}' AND type = 'WEEKLY' ORDER BY created_at DESC LIMIT 1);".format(
            pair_id=pair_id, target_date=target_date
        )
    )


def seed_daily_reports(
    pair_id: str, start_index: int, day_specs: list[tuple[str, int, str]]
) -> None:
    values = []
    for offset, (target_date, health_score, insight) in enumerate(
        day_specs, start=start_index
    ):
        report_id = str(uuid4())
        payload = json.dumps(
            {
                "health_score": health_score,
                "insight": insight,
                "suggestion": "建议继续保持固定的情绪同步和低防御沟通。",
                "highlights": ["回应及时", "表达直接"],
                "concerns": ["暂无明显风险"],
            },
            ensure_ascii=False,
        )
        values.append(
            "('{report_id}', '{pair_id}', NULL, 'DAILY', 'COMPLETED', $json${payload}$json$, {health_score}, DATE '{target_date}', NOW())".format(
                report_id=report_id,
                pair_id=pair_id,
                payload=payload,
                health_score=health_score,
                target_date=target_date,
            )
        )

    sql = (
        "INSERT INTO reports (id, pair_id, user_id, type, status, content, health_score, report_date, created_at) VALUES "
        + ",".join(values)
        + ";"
    )
    run_remote_sql(sql)


def main() -> int:
    suffix = datetime.now().strftime("%m%d%H%M%S")
    password = "QjPeriod#2026"
    email_a = f"period_a_{suffix}@example.com"
    email_b = f"period_b_{suffix}@example.com"

    print("[1/7] 注册并登录测试账号")
    http_json(
        "POST",
        "/auth/register",
        payload={
            "email": email_a,
            "nickname": f"周期A{suffix[-4:]}",
            "password": password,
        },
    )
    http_json(
        "POST",
        "/auth/register",
        payload={
            "email": email_b,
            "nickname": f"周期B{suffix[-4:]}",
            "password": password,
        },
    )
    token_a = http_json(
        "POST", "/auth/login", payload={"email": email_a, "password": password}
    )["access_token"]
    token_b = http_json(
        "POST", "/auth/login", payload={"email": email_b, "password": password}
    )["access_token"]

    print("[2/7] 创建配对")
    pair = http_json("POST", "/pairs/create", token=token_a, payload={"type": "couple"})
    pair_id = pair["id"]
    http_json(
        "POST",
        "/pairs/join",
        token=token_b,
        payload={"invite_code": pair["invite_code"]},
    )

    print("[3/7] 注入第一组已完成日报，构造第一周数据")
    seed_daily_reports(
        pair_id,
        1,
        [
            ("2026-02-28", 78, "第一周整体稳定，沟通保持开放。"),
            ("2026-03-01", 80, "双方都愿意说出真实需求，互动质量不错。"),
            ("2026-03-02", 82, "共同目标让这段关系更有凝聚力。"),
        ],
    )

    print("[4/7] 生成第一份周报并回填到较早日期")
    http_json(
        "POST", "/reports/generate-weekly", token=token_a, query={"pair_id": pair_id}
    )
    weekly_one = poll_latest_report(token_a, pair_id, "weekly")
    if weekly_one.get("status") != "completed":
        raise RuntimeError(f"第一份周报生成失败: {weekly_one}")
    set_latest_weekly_date(pair_id, "2026-02-23")

    print("[5/7] 注入第二组已完成日报，构造第二周数据")
    seed_daily_reports(
        pair_id,
        4,
        [
            ("2026-03-04", 84, "这一周开始后，回应更及时了。"),
            ("2026-03-05", 86, "冲突表达更克制，修复效率提升。"),
            ("2026-03-06", 88, "本周的合作感和信任感都明显增强。"),
        ],
    )

    print("[6/7] 生成第二份周报")
    http_json(
        "POST", "/reports/generate-weekly", token=token_a, query={"pair_id": pair_id}
    )
    weekly_two = poll_latest_report(token_a, pair_id, "weekly")
    if weekly_two.get("status") != "completed":
        raise RuntimeError(f"第二份周报生成失败: {weekly_two}")

    print("[7/7] 生成月报")
    http_json(
        "POST", "/reports/generate-monthly", token=token_a, query={"pair_id": pair_id}
    )
    monthly = poll_latest_report(token_a, pair_id, "monthly")
    if monthly.get("status") != "completed":
        raise RuntimeError(f"月报生成失败: {monthly}")

    weekly_history = http_json(
        "GET",
        "/reports/history",
        token=token_a,
        query={"pair_id": pair_id, "report_type": "weekly", "limit": 5},
    )
    monthly_latest = http_json(
        "GET",
        "/reports/latest",
        token=token_a,
        query={"pair_id": pair_id, "report_type": "monthly"},
    )

    summary = {
        "emails": {"user_a": email_a, "user_b": email_b},
        "pair_id": pair_id,
        "weekly_reports": [
            {
                "report_date": weekly_history[0].get("report_date")
                if len(weekly_history) > 0
                else None,
                "status": weekly_history[0].get("status")
                if len(weekly_history) > 0
                else None,
                "health_score": weekly_history[0].get("health_score")
                if len(weekly_history) > 0
                else None,
            },
            {
                "report_date": weekly_history[1].get("report_date")
                if len(weekly_history) > 1
                else None,
                "status": weekly_history[1].get("status")
                if len(weekly_history) > 1
                else None,
                "health_score": weekly_history[1].get("health_score")
                if len(weekly_history) > 1
                else None,
            },
        ],
        "monthly_report": {
            "report_date": monthly_latest.get("report_date"),
            "status": monthly_latest.get("status"),
            "health_score": monthly_latest.get("health_score"),
            "summary": (monthly_latest.get("content") or {}).get("executive_summary"),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"周期报告测试失败: {exc}", file=sys.stderr)
        raise
