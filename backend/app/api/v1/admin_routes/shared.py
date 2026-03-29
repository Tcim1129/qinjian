"""Shared helpers for admin policy routes."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import InterventionPolicyLibrary, RelationshipEvent, User
from app.services.policy_registry import ensure_policy_library_seeded
from app.services.relationship_intelligence import record_relationship_event

POLICY_AUDIT_LABELS = {
    "admin.policy.created": "新建策略版本",
    "admin.policy.updated": "编辑策略内容",
    "admin.policy.toggled": "切换策略状态",
    "admin.policy.reordered": "调整发布时间顺序",
    "admin.policy.rolled_back": "回滚到历史版本",
}

POLICY_AUDIT_FIELD_LABELS = {
    "plan_type": "方案类型",
    "title": "策略名称",
    "summary": "策略摘要",
    "branch": "分支编码",
    "branch_label": "分支标签",
    "intensity": "强度编码",
    "intensity_label": "强度标签",
    "copy_mode": "文案风格编码",
    "copy_mode_label": "文案风格标签",
    "when_to_use": "适用时机",
    "success_marker": "成功信号",
    "guardrail": "护栏规则",
    "version": "版本号",
    "status": "状态",
    "sort_order": "发布顺序",
    "metadata_json": "附加元数据",
}

POLICY_SNAPSHOT_FIELDS = (
    "policy_id",
    "plan_type",
    "title",
    "summary",
    "branch",
    "branch_label",
    "intensity",
    "intensity_label",
    "copy_mode",
    "copy_mode_label",
    "when_to_use",
    "success_marker",
    "guardrail",
    "version",
    "status",
    "source",
    "sort_order",
    "metadata_json",
    "created_at",
    "updated_at",
)

POLICY_RESTORABLE_FIELDS = (
    "plan_type",
    "title",
    "summary",
    "branch",
    "branch_label",
    "intensity",
    "intensity_label",
    "copy_mode",
    "copy_mode_label",
    "when_to_use",
    "success_marker",
    "guardrail",
    "version",
    "status",
    "sort_order",
    "metadata_json",
)


def admin_email_set() -> set[str]:
    raw = (settings.ADMIN_EMAILS or "").replace(";", ",").replace("\n", ",")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    admin_emails = admin_email_set()
    normalized_email = (user.email or "").strip().lower()
    if normalized_email and normalized_email in admin_emails:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only admins can access this endpoint.",
    )


def serialize_policy_row(row: InterventionPolicyLibrary) -> dict[str, Any]:
    return {
        "id": row.id,
        "policy_id": row.policy_id,
        "plan_type": row.plan_type,
        "title": row.title,
        "summary": row.summary,
        "branch": row.branch,
        "branch_label": row.branch_label,
        "intensity": row.intensity,
        "intensity_label": row.intensity_label,
        "copy_mode": row.copy_mode,
        "copy_mode_label": row.copy_mode_label,
        "when_to_use": row.when_to_use,
        "success_marker": row.success_marker,
        "guardrail": row.guardrail,
        "version": row.version,
        "status": row.status,
        "source": row.source,
        "sort_order": row.sort_order,
        "metadata_json": dict(row.metadata_json or {}),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def jsonify(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): jsonify(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonify(item) for item in value]
    return value


def snapshot_policy_row(row: InterventionPolicyLibrary) -> dict[str, Any]:
    serialized = serialize_policy_row(row)
    return {field: jsonify(serialized.get(field)) for field in POLICY_SNAPSHOT_FIELDS}


def build_policy_change_summary(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not before or not after:
        return []

    changes: list[dict[str, Any]] = []
    for field, label in POLICY_AUDIT_FIELD_LABELS.items():
        before_value = before.get(field)
        after_value = after.get(field)
        if before_value == after_value:
            continue
        changes.append(
            {
                "field": field,
                "label": label,
                "before_value": before_value,
                "after_value": after_value,
            }
        )
    return changes


def summarize_policy_event(
    event_label: str,
    changes: list[dict[str, Any]],
) -> str:
    if not changes:
        return event_label

    labels = [str(change.get("label") or change.get("field") or "") for change in changes[:3]]
    labels = [item for item in labels if item]
    suffix = "等字段" if len(changes) > 3 else "字段"
    if not labels:
        return event_label
    return f"{event_label}，涉及 {'、'.join(labels)}{suffix}。"


async def record_policy_audit_event(
    db: AsyncSession,
    *,
    row: InterventionPolicyLibrary,
    actor: User,
    event_type: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    note: str | None = None,
    meta: dict[str, Any] | None = None,
) -> RelationshipEvent:
    event_label = POLICY_AUDIT_LABELS.get(event_type, event_type)
    changed_fields = build_policy_change_summary(before, after)
    payload: dict[str, Any] = {
        "policy_id": row.policy_id,
        "policy_row_id": str(row.id),
        "plan_type": row.plan_type,
        "event_label": event_label,
        "summary": summarize_policy_event(event_label, changed_fields),
        "actor": {
            "user_id": str(actor.id),
            "email": actor.email,
        },
        "before": before,
        "after": after,
        "changed_fields": changed_fields,
    }
    if note:
        payload["note"] = note.strip()
    if meta:
        payload["meta"] = jsonify(meta)

    return await record_relationship_event(
        db,
        event_type=event_type,
        user_id=actor.id,
        entity_type="intervention_policy",
        entity_id=row.id,
        source="admin",
        payload=payload,
    )


def serialize_policy_audit_event(event: RelationshipEvent) -> dict[str, Any]:
    payload = dict(event.payload or {})
    actor = payload.get("actor") or None
    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "event_label": payload.get("event_label")
        or POLICY_AUDIT_LABELS.get(event.event_type, event.event_type),
        "summary": payload.get("summary"),
        "occurred_at": event.occurred_at,
        "note": payload.get("note"),
        "actor": actor,
        "before": payload.get("before"),
        "after": payload.get("after"),
        "changed_fields": payload.get("changed_fields") or [],
        "meta": payload.get("meta"),
        "can_restore": bool(payload.get("after")),
    }


def apply_policy_snapshot(
    row: InterventionPolicyLibrary,
    snapshot: dict[str, Any],
) -> None:
    for field in POLICY_RESTORABLE_FIELDS:
        if field not in snapshot:
            continue
        value = snapshot.get(field)
        if field == "sort_order":
            value = int(value or 0)
        elif field == "metadata_json":
            value = dict(value or {}) if value is not None else None
        setattr(row, field, value)


def clean_text(value: str | None, label: str, *, allow_blank: bool = False) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned and not allow_blank:
        raise HTTPException(status_code=400, detail=f"{label} cannot be empty.")
    return cleaned


def normalize_policy_id(value: str) -> str:
    normalized = clean_text(value, "policy_id")
    assert normalized is not None
    return normalized.lower()


def normalize_policy_payload(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    field_labels = {
        "plan_type": "plan_type",
        "title": "title",
        "summary": "summary",
        "branch": "branch",
        "branch_label": "branch_label",
        "intensity": "intensity",
        "intensity_label": "intensity_label",
        "copy_mode": "copy_mode",
        "copy_mode_label": "copy_mode_label",
        "when_to_use": "when_to_use",
        "success_marker": "success_marker",
        "guardrail": "guardrail",
        "version": "version",
    }
    required_fields = {
        "plan_type",
        "title",
        "summary",
        "branch",
        "branch_label",
        "intensity",
        "intensity_label",
        "when_to_use",
        "success_marker",
        "guardrail",
        "version",
    }

    normalized: dict[str, Any] = {}
    for field, label in field_labels.items():
        if field not in payload:
            continue
        allow_blank = partial and field in {"copy_mode", "copy_mode_label"}
        cleaned = clean_text(payload.get(field), label, allow_blank=allow_blank)
        if cleaned == "" and field in {"copy_mode", "copy_mode_label"}:
            cleaned = None
        if field in required_fields and cleaned is None:
            raise HTTPException(status_code=400, detail=f"{label} cannot be empty.")
        normalized[field] = cleaned

    if "status" in payload and payload.get("status") not in {"active", "inactive"}:
        raise HTTPException(
            status_code=400,
            detail="status must be either active or inactive.",
        )

    if "status" in payload:
        normalized["status"] = payload.get("status")

    if "metadata_json" in payload:
        metadata_json = payload.get("metadata_json")
        normalized["metadata_json"] = (
            dict(metadata_json or {}) if metadata_json is not None else None
        )

    if not normalized.get("copy_mode"):
        normalized["copy_mode"] = None
        normalized["copy_mode_label"] = None

    return normalized


async def ensure_policy_library_ready(db: AsyncSession) -> None:
    try:
        await ensure_policy_library_seeded(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Policy library is not ready. Run alembic upgrade head first.",
        ) from exc


async def get_policy_row_or_404(
    db: AsyncSession,
    policy_id: str,
) -> InterventionPolicyLibrary:
    result = await db.execute(
        select(InterventionPolicyLibrary).where(
            InterventionPolicyLibrary.policy_id == policy_id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return row

