"""关系树游戏化接口"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.core.database import get_db
from app.core.time import current_local_date
from app.models import (
    Checkin,
    Pair,
    RelationshipTask,
    RelationshipTree,
    TaskStatus,
    TreeLevel,
    User,
    TREE_LEVEL_THRESHOLDS,
    calc_tree_level,
)

router = APIRouter(prefix="/tree", tags=["关系树"])

LEVEL_EMOJI = {
    TreeLevel.SEED: "🌰",
    TreeLevel.SPROUT: "🌱",
    TreeLevel.SAPLING: "🌿",
    TreeLevel.TREE: "🌳",
    TreeLevel.BIG_TREE: "🏔️",
    TreeLevel.FOREST: "🌲",
}

LEVEL_NAME = {
    TreeLevel.SEED: "种子",
    TreeLevel.SPROUT: "萌芽",
    TreeLevel.SAPLING: "幼苗",
    TreeLevel.TREE: "小树",
    TreeLevel.BIG_TREE: "大树",
    TreeLevel.FOREST: "森林",
}

ENERGY_RULES = {
    "my_record": {
        "label": "记录",
        "points": 10,
        "locked_hint": "去记录后出现",
    },
    "partner_record": {
        "label": "同步",
        "points": 8,
        "locked_hint": "等对方同步",
    },
    "small_repair": {
        "label": "小行动",
        "points": 12,
        "locked_hint": "完成小行动后出现",
    },
}


class TreeCollectRequest(BaseModel):
    node_key: str


def _parse_pair_uuid(pair_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(pair_id, uuid.UUID):
        return pair_id
    try:
        return uuid.UUID(str(pair_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="无效的配对ID格式") from exc


async def _get_or_create_tree(
    pair_id: uuid.UUID | str,
    db: AsyncSession,
) -> RelationshipTree:
    pair_uuid = _parse_pair_uuid(pair_id)
    result = await db.execute(
        select(RelationshipTree).where(RelationshipTree.pair_id == pair_uuid)
    )
    tree = result.scalar_one_or_none()
    if not tree:
        tree = RelationshipTree(pair_id=pair_uuid)
        db.add(tree)
        await db.flush()
    return tree


def _next_threshold(growth_points: int) -> int | None:
    for threshold, _level in TREE_LEVEL_THRESHOLDS:
        if threshold > growth_points:
            return threshold
    return None


def _progress_percent(growth_points: int, next_threshold: int | None) -> int:
    if not next_threshold:
        return 100
    return min(100, int(growth_points / (next_threshold or 1200) * 100))


def _reset_energy_state_if_needed(
    tree: RelationshipTree,
    today_iso: str,
) -> set[str]:
    state = tree.energy_state if isinstance(tree.energy_state, dict) else {}
    if state.get("date") != today_iso:
        tree.energy_state = {"date": today_iso, "collected": []}
        return set()
    collected = state.get("collected")
    if not isinstance(collected, list):
        tree.energy_state = {"date": today_iso, "collected": []}
        return set()
    return {str(item) for item in collected}


async def _load_today_activity(
    db: AsyncSession,
    *,
    pair: Pair,
    user: User,
) -> dict[str, bool]:
    today = current_local_date()
    result = await db.execute(
        select(Checkin).where(
            Checkin.pair_id == pair.id,
            Checkin.checkin_date == today,
        )
    )
    checkins = result.scalars().all()

    partner_id = pair.user_b_id if str(pair.user_a_id) == str(user.id) else pair.user_a_id
    my_record = any(str(checkin.user_id) == str(user.id) for checkin in checkins)
    partner_record = bool(partner_id) and any(
        str(checkin.user_id) == str(partner_id) for checkin in checkins
    )
    task_completed_from_checkin = any(bool(checkin.task_completed) for checkin in checkins)

    task_result = await db.execute(
        select(RelationshipTask.id).where(
            RelationshipTask.pair_id == pair.id,
            RelationshipTask.due_date == today,
            RelationshipTask.status == TaskStatus.COMPLETED,
        )
    )
    task_completed = task_result.first() is not None

    return {
        "my_record": my_record,
        "partner_record": partner_record,
        "small_repair": task_completed_from_checkin or task_completed,
    }


def _build_energy_nodes(
    available_map: dict[str, bool],
    collected: set[str],
) -> list[dict]:
    nodes = []
    for key, rule in ENERGY_RULES.items():
        is_collected = key in collected
        is_available = bool(available_map.get(key)) and not is_collected
        if is_collected:
            state = "collected"
            hint = "已收"
        elif is_available:
            state = "available"
            hint = "点击收取成长值"
        else:
            state = "locked"
            hint = rule["locked_hint"]
        nodes.append(
            {
                "key": key,
                "label": rule["label"],
                "points": rule["points"],
                "state": state,
                "collected": is_collected,
                "available": is_available,
                "hint": hint,
            }
        )
    return nodes


async def _serialize_tree_status(
    db: AsyncSession,
    *,
    pair: Pair,
    user: User,
    tree: RelationshipTree,
    points_added: int | None = None,
    level_up: bool | None = None,
) -> dict:
    today = current_local_date()
    today_iso = str(today)
    collected = _reset_energy_state_if_needed(tree, today_iso)
    energy_nodes = _build_energy_nodes(
        await _load_today_activity(db, pair=pair, user=user),
        collected,
    )
    next_threshold = _next_threshold(tree.growth_points)
    payload = {
        "growth_points": tree.growth_points,
        "level": tree.level.value,
        "level_name": LEVEL_NAME.get(tree.level, "种子"),
        "level_emoji": LEVEL_EMOJI.get(tree.level, "🌰"),
        "next_level_at": next_threshold,
        "progress_percent": _progress_percent(tree.growth_points, next_threshold),
        "milestones": tree.milestones or [],
        "last_watered": str(tree.last_watered) if tree.last_watered else None,
        "can_water": any(node["available"] for node in energy_nodes),
        "energy_nodes": energy_nodes,
    }
    if points_added is not None:
        payload["points_added"] = points_added
    if level_up is not None:
        payload["level_up"] = level_up
    return payload


def _apply_growth(tree: RelationshipTree, points: int) -> bool:
    old_level = tree.level
    tree.growth_points += points
    tree.level = calc_tree_level(tree.growth_points)
    level_up = tree.level != old_level
    if level_up:
        today = current_local_date()
        milestones = tree.milestones or []
        milestones.append(
            {"type": "level_up", "level": tree.level.value, "date": str(today)}
        )
        tree.milestones = milestones
    return level_up


def _demo_status(*, collected: set[str] | None = None) -> dict:
    collected = collected or set()
    available_map = {"my_record": True, "partner_record": True, "small_repair": True}
    nodes = _build_energy_nodes(available_map, collected)
    return {
        "growth_points": 368 + sum(ENERGY_RULES[key]["points"] for key in collected),
        "level": "tree",
        "level_name": "小树",
        "level_emoji": "🌳",
        "next_level_at": 700,
        "progress_percent": 52,
        "milestones": [],
        "last_watered": None,
        "can_water": any(node["available"] for node in nodes),
        "energy_nodes": nodes,
    }


@router.get("/status", response_model=dict)
async def get_tree_status(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取关系树当前状态"""
    if pair_id in ("solo", "demo-pair"):
        return _demo_status()

    pair_uuid = _parse_pair_uuid(pair_id)
    pair = await validate_pair_access(pair_uuid, user, db, require_active=True)
    tree = await _get_or_create_tree(pair_uuid, db)
    return await _serialize_tree_status(db, pair=pair, user=user, tree=tree)


@router.post("/collect", response_model=dict)
async def collect_tree_energy(
    pair_id: str,
    req: TreeCollectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """收取关系树能量节点。"""
    node_key = str(req.node_key or "").strip()
    if node_key not in ENERGY_RULES:
        raise HTTPException(status_code=400, detail="这个能量节点不存在")

    if pair_id in ("solo", "demo-pair"):
        payload = _demo_status(collected={node_key})
        payload["points_added"] = ENERGY_RULES[node_key]["points"]
        payload["level_up"] = False
        return payload

    pair_uuid = _parse_pair_uuid(pair_id)
    pair = await validate_pair_access(pair_uuid, user, db, require_active=True)
    tree = await _get_or_create_tree(pair_uuid, db)
    today_iso = str(current_local_date())
    collected = _reset_energy_state_if_needed(tree, today_iso)
    nodes = {
        node["key"]: node
        for node in _build_energy_nodes(
            await _load_today_activity(db, pair=pair, user=user),
            collected,
        )
    }
    node = nodes[node_key]
    if node["collected"]:
        raise HTTPException(status_code=400, detail="这个节点今天已经收过了")
    if not node["available"]:
        raise HTTPException(status_code=400, detail=node["hint"])

    collected.add(node_key)
    tree.energy_state = {"date": today_iso, "collected": sorted(collected)}
    tree.last_watered = current_local_date()
    points_added = ENERGY_RULES[node_key]["points"]
    level_up = _apply_growth(tree, points_added)
    await db.flush()
    return await _serialize_tree_status(
        db,
        pair=pair,
        user=user,
        tree=tree,
        points_added=points_added,
        level_up=level_up,
    )


@router.post("/water", response_model=dict)
async def water_tree(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """兼容旧浇水接口。"""
    if pair_id in ("solo", "demo-pair"):
        payload = _demo_status(collected={"my_record"})
        payload["points_added"] = 5
        payload["level_up"] = False
        return payload

    pair_uuid = _parse_pair_uuid(pair_id)
    pair = await validate_pair_access(pair_uuid, user, db, require_active=True)
    tree = await _get_or_create_tree(pair_uuid, db)

    today = current_local_date()
    if tree.last_watered == today:
        raise HTTPException(status_code=400, detail="今天已经浇过水了，明天再来吧 💧")

    tree.last_watered = today
    level_up = _apply_growth(tree, 5)
    await db.flush()
    return await _serialize_tree_status(
        db,
        pair=pair,
        user=user,
        tree=tree,
        points_added=5,
        level_up=level_up,
    )


async def grow_tree_on_checkin(
    pair_id: uuid.UUID | str,
    both_done: bool,
    streak: int,
):
    """打卡后只确保关系树存在；成长值由可领取节点增加。"""
    _ = both_done, streak
    from app.core.database import async_session

    async with async_session() as db:
        await _get_or_create_tree(pair_id, db)
        await db.commit()
