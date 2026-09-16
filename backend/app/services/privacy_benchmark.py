"""轻量文本隐私代理的合成基准测试。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import RelationshipEvent
from app.services.privacy_audit import log_privacy_event
from app.services.privacy_text_proxy import count_sensitive_matches, proxy_message_payload

SYNTHETIC_BENCHMARK_CASES = (
    {
        "case_id": "conflict_phone",
        "title": "带手机号的冲突求助",
        "text": "昨晚又吵架了，你能帮我整理一下怎么跟 13800138000 说今晚先别升级情绪吗？",
        "keywords": ["吵架", "今晚", "情绪"],
    },
    {
        "case_id": "email_reflection",
        "title": "带邮箱的复盘记录",
        "text": "把这段复盘整理成一段更温和的话发给 partner@example.com，重点保留异地、误会和想和好。",
        "keywords": ["复盘", "异地", "误会", "和好"],
    },
    {
        "case_id": "uuid_token_support",
        "title": "带会话标识的支持请求",
        "text": "会话 123e4567-e89b-12d3-a456-426614174000 里提到的令牌 eyJhbGciOiJIUzI1NiJ9.payload.signature 不要外发，只帮我保留安抚和边界建议。",
        "keywords": ["不要外发", "安抚", "边界建议"],
    },
)


def runtime_profile_label() -> str:
    return str(settings.PRIVACY_SERVER_PROFILE or "2c2g_text_proxy")


def text_pipeline_label() -> str:
    return "local_text_proxy" if settings.PRIVACY_TEXT_PROXY_ENABLED else "redact_only"


def audio_pipeline_label() -> str:
    return str(settings.PRIVACY_AUDIO_PIPELINE_MODE or "cloud_transcription")


def run_privacy_text_benchmark_locally() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    raw_sensitive_hits = 0
    proxied_sensitive_hits = 0
    replacement_total = 0
    utility_total = 0.0

    for case in SYNTHETIC_BENCHMARK_CASES:
        text = str(case["text"])
        proxied_bundle = proxy_message_payload([{"role": "user", "content": text}])
        proxied_text = str(proxied_bundle.messages[0]["content"])
        case_raw_hits = count_sensitive_matches(text)
        case_proxied_hits = count_sensitive_matches(proxied_text)
        keywords = list(case.get("keywords") or [])
        kept_keywords = sum(1 for keyword in keywords if keyword in proxied_text)
        utility_pct = round(
            (kept_keywords / max(len(keywords), 1)) * 100,
            1,
        )

        raw_sensitive_hits += case_raw_hits
        proxied_sensitive_hits += case_proxied_hits
        replacement_total += proxied_bundle.replacement_count
        utility_total += utility_pct

        cases.append(
            {
                "case_id": case["case_id"],
                "title": case["title"],
                "original_text": text,
                "proxied_text": proxied_text,
                "raw_sensitive_hits": case_raw_hits,
                "proxied_sensitive_hits": case_proxied_hits,
                "utility_pct": utility_pct,
                "replacement_count": proxied_bundle.replacement_count,
                "entity_counts": proxied_bundle.entity_counts,
            }
        )

    leak_reduction_pct = round(
        (1 - (proxied_sensitive_hits / raw_sensitive_hits)) * 100,
        1,
    ) if raw_sensitive_hits else 100.0
    avg_utility_pct = round(utility_total / max(len(cases), 1), 1)
    summary = {
        "cases_total": len(cases),
        "raw_sensitive_hits": raw_sensitive_hits,
        "proxied_sensitive_hits": proxied_sensitive_hits,
        "leak_reduction_pct": leak_reduction_pct,
        "avg_utility_pct": avg_utility_pct,
        "replacement_total": replacement_total,
        "runtime_profile": runtime_profile_label(),
        "text_pipeline": text_pipeline_label(),
        "audio_pipeline": audio_pipeline_label(),
    }
    return {"summary": summary, "cases": cases}


async def run_privacy_text_benchmark(
    db: AsyncSession,
    *,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    payload = run_privacy_text_benchmark_locally()
    event = await log_privacy_event(
        db,
        event_type="privacy.benchmark.ran",
        user_id=actor_user_id,
        entity_type="privacy_benchmark",
        payload=payload,
        summary=(
            "文本隐私代理基准测试完成，"
            f"泄露下降 {payload['summary']['leak_reduction_pct']}%，"
            f"语义保留 {payload['summary']['avg_utility_pct']}%。"
        ),
        source="admin",
    )
    if event:
        payload["run_id"] = event.id
        payload["occurred_at"] = event.occurred_at
    else:
        payload["run_id"] = None
        payload["occurred_at"] = datetime.utcnow()
    return payload


def serialize_privacy_benchmark_run(event: RelationshipEvent) -> dict[str, Any]:
    payload = dict(event.payload or {})
    summary = dict(payload.get("summary") or {})
    cases = list(payload.get("cases") or [])
    return {
        "run_id": event.id,
        "occurred_at": event.occurred_at,
        "summary": summary,
        "cases": cases,
    }


async def list_privacy_benchmark_runs(
    db: AsyncSession,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    stmt = (
        select(RelationshipEvent)
        .where(RelationshipEvent.event_type == "privacy.benchmark.ran")
        .order_by(desc(RelationshipEvent.occurred_at))
        .limit(max(limit, 1))
    )
    result = await db.execute(stmt)
    return [
        serialize_privacy_benchmark_run(item) for item in result.scalars().all()
    ]


async def get_latest_privacy_benchmark_run(
    db: AsyncSession,
) -> dict[str, Any] | None:
    runs = await list_privacy_benchmark_runs(db, limit=1)
    return runs[0] if runs else None
