"""关系树游戏化接口"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.time import current_local_date
from app.api.deps import get_current_user, validate_pair_access
from app.models import (
    User,
    Pair,
    PairStatus,
    RelationshipTree,
    TreeLevel,
    calc_tree_level,
    TREE_LEVEL_THRESHOLDS,
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


async def _get_or_create_tree(pair_id, db: AsyncSession) -> RelationshipTree:
    """获取或创建关系树"""
    result = await db.execute(
        select(RelationshipTree).where(RelationshipTree.pair_id == pair_id)
    )
    tree = result.scalar_one_or_none()
    if not tree:
        tree = RelationshipTree(pair_id=pair_id)
        db.add(tree)
        await db.flush()
    return tree


@router.get("/status", response_model=dict)
async def get_tree_status(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取关系树当前状态"""
    if pair_id in ("solo", "demo-pair"):
        return {
            "growth_points": 368,
            "level": "tree",
            "level_name": "小树",
            "level_emoji": "🌳",
            "next_level_at": 700,
            "progress_percent": 52,
            "milestones": [],
            "last_watered": None,
            "can_water": True,
        }

    import uuid
    try:
        uuid.UUID(pair_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的配对ID格式")

    await validate_pair_access(pair_id, user, db, require_active=True)

    tree = await _get_or_create_tree(pair_id, db)

    # 计算到下一级需要的成长值
    next_threshold = None
    for threshold, lvl in TREE_LEVEL_THRESHOLDS:
        if threshold > tree.growth_points:
            next_threshold = threshold
            break

    return {
        "growth_points": tree.growth_points,
        "level": tree.level.value,
        "level_name": LEVEL_NAME.get(tree.level, "种子"),
        "level_emoji": LEVEL_EMOJI.get(tree.level, "🌰"),
        "next_level_at": next_threshold,
        "progress_percent": min(
            100, int(tree.growth_points / (next_threshold or 1200) * 100)
        )
        if next_threshold
        else 100,
        "milestones": tree.milestones or [],
        "last_watered": str(tree.last_watered) if tree.last_watered else None,
        "can_water": tree.last_watered != current_local_date(),
    }


@router.post("/water", response_model=dict)
async def water_tree(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动浇水（每日限一次，+5 成长值）"""
    if pair_id in ("solo", "demo-pair"):
        return {
            "growth_points": 373,
            "level": "tree",
            "level_name": "小树",
            "level_emoji": "🌳",
            "points_added": 5,
            "level_up": False,
        }

    import uuid
    try:
        uuid.UUID(pair_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的配对ID格式")

    await validate_pair_access(pair_id, user, db, require_active=True)

    tree = await _get_or_create_tree(pair_id, db)

    today = current_local_date()
    if tree.last_watered == today:
        raise HTTPException(status_code=400, detail="今天已经浇过水了，明天再来吧 💧")

    tree.growth_points += 5
    tree.last_watered = today

    old_level = tree.level
    tree.level = calc_tree_level(tree.growth_points)

    level_up = tree.level != old_level
    if level_up:
        milestones = tree.milestones or []
        milestones.append(
            {"type": "level_up", "level": tree.level.value, "date": str(today)}
        )
        tree.milestones = milestones

    await db.flush()

    return {
        "growth_points": tree.growth_points,
        "level": tree.level.value,
        "level_name": LEVEL_NAME.get(tree.level, "种子"),
        "level_emoji": LEVEL_EMOJI.get(tree.level, "🌰"),
        "points_added": 5,
        "level_up": level_up,
    }


async def grow_tree_on_checkin(pair_id: str, both_done: bool, streak: int):
    """打卡后触发关系树成长（从 checkins.py 调用）"""
    from app.core.database import async_session

    async with async_session() as db:
        tree = await _get_or_create_tree(pair_id, db)

        points = 10  # 单方打卡 +10
        if both_done:
            points += 15  # 双方都打卡额外 +15
        if streak >= 7:
            points += 10  # 连续7天额外 +10

        tree.growth_points += points
        old_level = tree.level
        tree.level = calc_tree_level(tree.growth_points)

        if tree.level != old_level:
            milestones = tree.milestones or []
            milestones.append(
                {
                    "type": "level_up",
                    "level": tree.level.value,
                    "date": str(current_local_date()),
                }
            )
            tree.milestones = milestones

        await db.commit()
