"""危机预警接口：关系危机分级预警 + 差异化干预方案 + CrisisAlert CRUD"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, validate_pair_access
from app.models import (
    User,
    Pair,
    PairStatus,
    Report,
    ReportType,
    CrisisAlert,
    CrisisAlertStatus,
    CrisisLevel,
    RelationshipProfileSnapshot,
    InterventionPlan,
)
from app.schemas import (
    CrisisStatusResponse,
    CrisisHistoryResponse,
    CrisisAlertResponse,
    CrisisAcknowledgeRequest,
    CrisisResolveRequest,
    CrisisEscalateRequest,
    InterventionSchema,
    RepairProtocolResponse,
)
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_snapshot,
)
from app.services.repair_protocol import build_repair_protocol

router = APIRouter(prefix="/crisis", tags=["危机预警"])


# ── 危机状态 ──


@router.get("/status/{pair_id}", response_model=CrisisStatusResponse)
async def get_crisis_status(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前危机等级 — 优先从 CrisisAlert 表读取，回退到 Report.content"""
    await validate_pair_access(pair_id, user, db, require_active=True)

    # 优先查 CrisisAlert 表（active 状态）
    result = await db.execute(
        select(CrisisAlert)
        .where(
            CrisisAlert.pair_id == pair_id,
            CrisisAlert.status.in_(
                [CrisisAlertStatus.ACTIVE.value, CrisisAlertStatus.ACKNOWLEDGED.value]
            ),
        )
        .order_by(desc(CrisisAlert.created_at))
        .limit(1)
    )
    alert = result.scalar_one_or_none()

    if alert:
        return CrisisStatusResponse(
            crisis_level=alert.level.value,
            alert_id=alert.id,
            alert_status=alert.status.value,
            intervention=InterventionSchema(
                type=alert.intervention_type or "none",
                title=alert.intervention_title,
                description=alert.intervention_desc,
                action_items=alert.action_items,
            )
            if alert.intervention_type
            else None,
            health_score=alert.health_score,
            source_report_id=str(alert.report_id) if alert.report_id else None,
            previous_level=alert.previous_level.value if alert.previous_level else None,
        )

    # 回退：从最近报告的 content 中提取（兼容旧数据）
    result = await db.execute(
        select(Report)
        .where(Report.pair_id == pair_id, Report.content.isnot(None))
        .order_by(desc(Report.created_at))
        .limit(1)
    )
    report = result.scalar_one_or_none()

    if not report or not report.content:
        return CrisisStatusResponse(
            crisis_level="none",
            message="暂无足够数据生成预警",
        )

    content = report.content
    intervention_data = content.get("intervention")
    return CrisisStatusResponse(
        crisis_level=content.get("crisis_level", "none"),
        intervention=InterventionSchema(**intervention_data)
        if intervention_data and isinstance(intervention_data, dict)
        else None,
        health_score=content.get("health_score") or content.get("overall_health_score"),
        source_report_id=str(report.id),
        source_report_type=report.type.value,
        report_date=str(report.report_date),
    )


# ── 危机历史 ──


@router.get("/history/{pair_id}", response_model=CrisisHistoryResponse)
async def get_crisis_history(
    pair_id: str,
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取危机等级历史趋势 — 合并 CrisisAlert 记录 + Report.content"""
    await validate_pair_access(pair_id, user, db, require_active=True)

    history = []

    # 从 CrisisAlert 表获取历史记录
    result = await db.execute(
        select(CrisisAlert)
        .where(CrisisAlert.pair_id == pair_id)
        .order_by(desc(CrisisAlert.created_at))
        .limit(limit)
    )
    alerts = result.scalars().all()

    alert_dates = set()
    for a in alerts:
        date_str = str(a.created_at.date()) if a.created_at else ""
        alert_dates.add(date_str)
        history.append(
            {
                "date": date_str,
                "type": "alert",
                "crisis_level": a.level.value,
                "health_score": a.health_score,
                "intervention_type": a.intervention_type or "none",
                "alert_status": a.status.value,
            }
        )

    # 补充 Report.content 中的历史（排除已有 alert 的日期避免重复）
    remaining = limit - len(history)
    if remaining > 0:
        result = await db.execute(
            select(Report)
            .where(
                Report.pair_id == pair_id,
                Report.content.isnot(None),
                Report.type.in_([ReportType.DAILY, ReportType.WEEKLY]),
            )
            .order_by(desc(Report.created_at))
            .limit(remaining + len(alert_dates))  # 多取一些，因为会过滤
        )
        reports = result.scalars().all()
        for r in reports:
            date_str = str(r.report_date)
            if date_str in alert_dates:
                continue
            if r.content:
                history.append(
                    {
                        "date": date_str,
                        "type": r.type.value,
                        "crisis_level": r.content.get("crisis_level", "none"),
                        "health_score": r.content.get("health_score")
                        or r.content.get("overall_health_score"),
                        "intervention_type": (r.content.get("intervention") or {}).get(
                            "type", "none"
                        ),
                        "alert_status": None,
                    }
                )

    # 按日期降序排序
    history.sort(key=lambda x: x["date"], reverse=True)
    history = history[:limit]

    return CrisisHistoryResponse(pair_id=pair_id, history=history)


# ── 预警列表 ──


@router.get("/alerts/{pair_id}", response_model=list[CrisisAlertResponse])
async def get_crisis_alerts(
    pair_id: str,
    status: str | None = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取预警记录列表（可按状态筛选）"""
    await validate_pair_access(pair_id, user, db, require_active=True)

    query = select(CrisisAlert).where(CrisisAlert.pair_id == pair_id)
    if status:
        try:
            status_enum = CrisisAlertStatus(status)
            query = query.where(CrisisAlert.status == status_enum)
        except ValueError:
            pass
    query = query.order_by(desc(CrisisAlert.created_at)).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/protocol/{pair_id}", response_model=RepairProtocolResponse)
async def get_repair_protocol(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前关系状态下的冲突修复协议。"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    status_payload = await get_crisis_status(pair_id=pair_id, user=user, db=db)
    crisis_level = status_payload.crisis_level or "none"

    snapshot_result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            RelationshipProfileSnapshot.pair_id == pair.id,
            RelationshipProfileSnapshot.user_id.is_(None),
            RelationshipProfileSnapshot.window_days == 7,
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    snapshot = snapshot_result.scalar_one_or_none()
    if not snapshot:
        snapshot = await refresh_profile_snapshot(db, pair_id=pair.id, window_days=7)

    plan_result = await db.execute(
        select(InterventionPlan)
        .where(
            InterventionPlan.pair_id == pair.id,
            InterventionPlan.user_id.is_(None),
            InterventionPlan.status == "active",
        )
        .order_by(InterventionPlan.created_at.desc())
        .limit(1)
    )
    active_plan = plan_result.scalar_one_or_none()

    protocol = build_repair_protocol(
        pair=pair,
        crisis_level=crisis_level,
        active_plan=active_plan,
        snapshot=snapshot,
    )

    await record_relationship_event(
        db,
        event_type="repair_protocol.requested",
        pair_id=pair.id,
        user_id=user.id,
        entity_type="repair_protocol",
        payload={
            "level": crisis_level,
            "protocol_type": protocol.get("protocol_type"),
        },
    )

    return RepairProtocolResponse(**protocol)


# ── 预警操作 ──


@router.post("/alerts/{alert_id}/acknowledge", response_model=CrisisAlertResponse)
async def acknowledge_alert(
    alert_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户确认已查看预警"""
    alert = await db.get(CrisisAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")

    # 验证权限
    await validate_pair_access(str(alert.pair_id), user, db, require_active=True)

    if alert.status not in (CrisisAlertStatus.ACTIVE,):
        raise HTTPException(status_code=400, detail="该预警已处理")

    alert.status = CrisisAlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = user.id
    alert.acknowledged_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=CrisisAlertResponse)
async def resolve_alert(
    alert_id: str,
    req: CrisisResolveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户标记预警已解决"""
    alert = await db.get(CrisisAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")

    await validate_pair_access(str(alert.pair_id), user, db, require_active=True)

    if alert.status == CrisisAlertStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="该预警已解决")

    alert.status = CrisisAlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    alert.resolve_note = req.note
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/alerts/{alert_id}/escalate", response_model=CrisisAlertResponse)
async def escalate_alert(
    alert_id: str,
    req: CrisisEscalateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """升级至专业帮助"""
    alert = await db.get(CrisisAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")

    await validate_pair_access(str(alert.pair_id), user, db, require_active=True)

    alert.status = CrisisAlertStatus.ESCALATED
    alert.resolve_note = (
        f"升级原因: {req.reason}" if req.reason else "用户主动寻求专业帮助"
    )
    await db.commit()
    await db.refresh(alert)
    return alert


# ── 专业帮助资源 ──


@router.get("/resources")
async def get_crisis_resources(
    user: User = Depends(get_current_user),
):
    """获取危机干预专业资源列表"""
    return {
        "hotlines": [
            {"name": "全国心理援助热线", "number": "400-161-9995", "hours": "24小时"},
            {
                "name": "北京心理危机研究与干预中心",
                "number": "010-82951332",
                "hours": "24小时",
            },
            {"name": "生命热线", "number": "400-821-1215", "hours": "每天 8:00-22:00"},
            {"name": "希望24热线", "number": "400-161-9995", "hours": "24小时"},
        ],
        "online": [
            {
                "name": "壹心理",
                "url": "https://www.xinli001.com",
                "desc": "专业心理咨询平台",
            },
            {
                "name": "简单心理",
                "url": "https://www.jiandanxinli.com",
                "desc": "在线心理咨询",
            },
        ],
        "tips": [
            "如果你或伴侣正在经历严重的关系危机，请不要独自承受",
            "专业心理咨询师可以提供客观、安全的沟通空间",
            "寻求帮助不是软弱的表现，而是对关系负责的体现",
            "如果存在家庭暴力等紧急情况，请立即拨打 110",
        ],
    }
