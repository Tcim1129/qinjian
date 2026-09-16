"""Question-bank helpers for the weekly relationship assessment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Pair, PairType, RelationshipEvent


DIMENSION_LABELS = {
    "connection": "连接与表达",
    "trust": "信任与安全",
    "repair": "修复能力",
    "shared_future": "共同愿景",
    "vitality": "关系活力",
}

LIKERT_OPTIONS = [
    {"id": "opt_0", "label": "很不符合", "score": 0},
    {"id": "opt_25", "label": "不太符合", "score": 25},
    {"id": "opt_50", "label": "一半一半", "score": 50},
    {"id": "opt_75", "label": "比较符合", "score": 75},
    {"id": "opt_100", "label": "很符合", "score": 100},
]

ASSESSMENT_PROFILE_COPY = {
    "couple": {
        "title": "关系体检",
        "subtitle": "这次围绕这段关系，用固定 10 题看现在最值得照顾的地方。",
    },
    "friend": {
        "title": "友情体检",
        "subtitle": "这次围绕这段友情，用固定 10 题看现在最值得照顾的地方。",
    },
    "spouse": {
        "title": "婚姻体检",
        "subtitle": "这次围绕这段婚姻，用固定 10 题看现在最值得照顾的地方。",
    },
    "long_distance": {
        "title": "异地关系体检",
        "subtitle": "这次围绕这段异地关系，用固定 10 题看现在最值得照顾的地方。",
    },
    "solo": {
        "title": "自我诊断",
        "subtitle": "这次先只看你自己，用固定 10 题整理最近在关系里最容易卡住的地方。",
    },
}

ASSESSMENT_PROMPT_VARIANTS = {
    "solo": {
        "anchor-connection-1": "过去一周里，我还能把真正介意的事说出来，不需要一直憋着。",
        "anchor-connection-2": "最近一次重要沟通里，我大致能说清自己到底在介意什么。",
        "anchor-trust-1": "最近大多数时候，我不太需要靠猜测或反复确认，来证明自己在关系里还有位置。",
        "anchor-repair-1": "有摩擦时，我最近至少能先停下来，不把局面越顶越高。",
        "anchor-shared-future-1": "最近我对自己想保留什么样的关系状态，仍然有一点基本认识。",
        "anchor-vitality-1": "最近在关系里，除了压力，我还能感到一点轻松或舒服。",
        "rot-connection-1": "当我表达不舒服时，我最近更愿意把真正介意的点说出来，而不是一下子顶回去或憋住。",
        "rot-connection-2": "最近谈重要话题时，我更能把问题说具体，而不是一直绕在情绪里。",
        "rot-connection-3": "最近我更少用“你总是”或“你从不”这种一下把人推远的话。",
        "rot-connection-4": "最近一次沟通里，我至少有一句话，是把自己真正想说的点说清楚了。",
        "rot-connection-5": "最近即使意见不同，我也还能把自己真正想表达的点说清楚。",
        "rot-connection-6": "最近我更容易把需求说出来，而不是等别人自己猜。",
        "rot-trust-1": "最近我不太需要靠试探、冷一下或反复确认，来判断别人还在不在乎我。",
        "rot-trust-2": "最近我更能看清，什么样的回应对我是稳定的，什么样的回应会让我不安。",
        "rot-trust-3": "最近即使联系没那么及时，我也不太会立刻觉得自己被丢下。",
        "rot-trust-4": "最近我能把脆弱的一面露出来，而不太会马上把自己重新藏起来。",
        "rot-trust-5": "最近在边界上，我更能注意到哪些答应和反悔，会让我慢慢失去安全感。",
        "rot-trust-6": "最近在关系里，我还能感到一点基本稳定感，而不是总提着一口气。",
        "rot-repair-1": "最近有摩擦时，我更能先停 10 分钟，而不是一直追着把话说死。",
        "rot-repair-2": "最近一次不愉快后，我更愿意先伸手把关系拉回来，而不是只等对方动作。",
        "rot-repair-3": "最近吵完或别扭后，我还能回到“到底卡在哪”这个问题上。",
        "rot-repair-4": "最近当情绪上来时，我更少翻旧账或一下子扩大到所有问题。",
        "rot-repair-5": "最近一次误会后，我还有耐心把它补清楚，而不是直接撤走。",
        "rot-repair-6": "最近即使没完全解决，我也更能先把伤害止住。",
        "rot-shared-future-1": "最近我对“这段关系值不值得继续投入”这件事，想法比以前更清楚一点。",
        "rot-shared-future-2": "最近我对自己能接受的相处频率、联系节奏或见面安排，有更清楚的预期。",
        "rot-shared-future-3": "最近讨论现实问题时，我更能分清自己想一起解决什么，不想再耗在哪里。",
        "rot-shared-future-4": "最近我还能想一想，接下来一个月什么样的关系状态会让我更舒服。",
        "rot-shared-future-5": "最近我对一段关系里最想保住的东西，说得越来越清楚。",
        "rot-shared-future-6": "最近想到接下来的关系安排时，我不只是拖着，也还有一点自己的期待。",
        "rot-vitality-1": "最近和别人相处完，我被耗空的感觉比以前少了一点。",
        "rot-vitality-2": "最近在关系里，我偶尔还能自然笑出来，而不只是处理问题。",
        "rot-vitality-3": "最近在关系里，不只是任务和矛盾，我还是能感到一点陪伴感。",
        "rot-vitality-4": "最近我还能留下一些不带压力的小互动，让自己觉得关系还活着。",
        "rot-vitality-5": "最近想到重要的人时，我不只是紧绷，也会有一点想靠近的感觉。",
        "rot-vitality-6": "最近关系里虽然有压力，但没有一直压到我喘不过气。",
    },
    "friend": {
        "anchor-connection-1": "过去一周里，这段友情里真正介意的事，我们还能说出来，不需要一直憋着。",
        "anchor-connection-2": "最近一次认真聊天里，我们大致能听懂对方到底在介意什么。",
        "anchor-trust-1": "最近我大多数时候都不用靠猜，能知道自己在这段友情里的位置。",
        "anchor-repair-1": "有别扭时，我们最近至少有一方能先停下来，不把气氛越顶越僵。",
        "anchor-shared-future-1": "最近我们对这段友情接下来怎么相处，仍然有基本共识。",
        "anchor-vitality-1": "最近和这个朋友相处时，除了压力，我还能感到一点轻松或舒服。",
    },
    "spouse": {
        "anchor-connection-1": "过去一周里，这段婚姻里真正介意的事，我们还能说出来，不需要一直憋着。",
        "anchor-connection-2": "最近一次重要沟通里，我们大致能听懂对方到底在介意什么，而不是只剩情绪。",
        "anchor-trust-1": "最近我大多数时候都不用靠猜，能知道自己在这段婚姻里的位置。",
        "anchor-repair-1": "有摩擦时，我们最近至少有一方能先停下来，不把家里的气氛越顶越高。",
        "anchor-shared-future-1": "最近我们对这段婚姻接下来怎么走，仍然有基本共识。",
        "anchor-vitality-1": "最近和对方待在一起时，除了现实压力，我还能感到一点轻松或舒服。",
    },
    "long_distance": {
        "anchor-connection-1": "过去一周里，隔着距离时真正介意的事，我们还能说出来，不需要一直憋着。",
        "anchor-connection-2": "最近一次重要联系里，我们大致能听懂对方到底在介意什么。",
        "anchor-trust-1": "最近我大多数时候都不用靠猜，能知道自己在这段异地关系里的位置。",
        "anchor-repair-1": "有摩擦时，我们最近至少有一方能先停下来，不把隔着距离的误会越顶越高。",
        "anchor-shared-future-1": "最近我们对这段异地关系接下来怎么走，仍然有基本共识。",
        "anchor-vitality-1": "最近隔着距离联系时，除了压力，我还能感到一点轻松或被陪到。",
    },
}

ASSESSMENT_ITEM_BANK = [
    {
        "item_id": "anchor-connection-1",
        "track": "core",
        "dimension": "connection",
        "prompt": "过去一周里，我们还能把真正介意的事说出来，不需要一直憋着。",
        "rotation_group": "anchor",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "anchor-connection-2",
        "track": "core",
        "dimension": "connection",
        "prompt": "最近一次重要沟通里，我们大致能听懂对方到底在介意什么。",
        "rotation_group": "anchor",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "anchor-trust-1",
        "track": "core",
        "dimension": "trust",
        "prompt": "最近我大多数时候都不用靠猜，能知道自己在这段关系里的位置。",
        "rotation_group": "anchor",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "anchor-repair-1",
        "track": "core",
        "dimension": "repair",
        "prompt": "有摩擦时，我们最近至少有一方能先停下来，不把局面越顶越高。",
        "rotation_group": "anchor",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "anchor-shared-future-1",
        "track": "core",
        "dimension": "shared_future",
        "prompt": "最近我们对这段关系接下来怎么走，仍然有基本共识。",
        "rotation_group": "anchor",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "anchor-vitality-1",
        "track": "core",
        "dimension": "vitality",
        "prompt": "最近和对方待在一起时，除了压力，我还能感到一点轻松或舒服。",
        "rotation_group": "anchor",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-connection-1",
        "track": "rotation",
        "dimension": "connection",
        "prompt": "当我表达不舒服时，对方最近更愿意先听完，而不是立刻反驳。",
        "rotation_group": "connection-a",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-connection-2",
        "track": "rotation",
        "dimension": "connection",
        "prompt": "最近谈重要话题时，我们能把问题说具体，而不是绕在情绪里。",
        "rotation_group": "connection-b",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-connection-3",
        "track": "rotation",
        "dimension": "connection",
        "prompt": "最近我们更少用“你总是”或“你从不”这种一下把人推远的话。",
        "rotation_group": "connection-c",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-connection-4",
        "track": "rotation",
        "dimension": "connection",
        "prompt": "最近一次沟通里，我们至少有一句话让彼此感觉被听见。",
        "rotation_group": "connection-d",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-connection-5",
        "track": "rotation",
        "dimension": "connection",
        "prompt": "最近即使意见不同，我们也还能把各自真正想表达的点说清楚。",
        "rotation_group": "connection-e",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-connection-6",
        "track": "rotation",
        "dimension": "connection",
        "prompt": "最近我们更容易把需求说出来，而不是等对方自己猜。",
        "rotation_group": "connection-f",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-trust-1",
        "track": "rotation",
        "dimension": "trust",
        "prompt": "最近我不太需要靠试探、冷一下或反复确认，来判断对方在不在乎我。",
        "rotation_group": "trust-a",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-trust-2",
        "track": "rotation",
        "dimension": "trust",
        "prompt": "对方最近的回应方式，大多数时候和他说的承诺是对得上的。",
        "rotation_group": "trust-b",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-trust-3",
        "track": "rotation",
        "dimension": "trust",
        "prompt": "最近即使联系没那么及时，我也不太会立刻觉得自己被丢下。",
        "rotation_group": "trust-c",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-trust-4",
        "track": "rotation",
        "dimension": "trust",
        "prompt": "最近我能把脆弱的一面露出来，而不太担心会被敷衍或利用。",
        "rotation_group": "trust-d",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-trust-5",
        "track": "rotation",
        "dimension": "trust",
        "prompt": "最近在边界上，我们更少出现答应了又反悔、或者说了不算的情况。",
        "rotation_group": "trust-e",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-trust-6",
        "track": "rotation",
        "dimension": "trust",
        "prompt": "最近这段关系里，我能感到基本的稳定感，而不是总提着一口气。",
        "rotation_group": "trust-f",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-repair-1",
        "track": "rotation",
        "dimension": "repair",
        "prompt": "最近有摩擦时，我们更能先停 10 分钟，而不是一直追着把话说死。",
        "rotation_group": "repair-a",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-repair-2",
        "track": "rotation",
        "dimension": "repair",
        "prompt": "最近一次不愉快后，我们有人愿意先伸手把关系拉回来。",
        "rotation_group": "repair-b",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-repair-3",
        "track": "rotation",
        "dimension": "repair",
        "prompt": "最近吵完或别扭后，我们还能回到“到底卡在哪”这个问题上。",
        "rotation_group": "repair-c",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-repair-4",
        "track": "rotation",
        "dimension": "repair",
        "prompt": "最近当情绪上来时，我们更少翻旧账或一下子扩大到所有问题。",
        "rotation_group": "repair-d",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-repair-5",
        "track": "rotation",
        "dimension": "repair",
        "prompt": "最近一次误会后，我们还有耐心把它补清楚，而不是各自撤走。",
        "rotation_group": "repair-e",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-repair-6",
        "track": "rotation",
        "dimension": "repair",
        "prompt": "最近即使没完全解决，我们也更能先把伤害止住。",
        "rotation_group": "repair-f",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-shared-future-1",
        "track": "rotation",
        "dimension": "shared_future",
        "prompt": "最近我们对“这段关系要不要继续投入”这件事，想法大致是一致的。",
        "rotation_group": "future-a",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-shared-future-2",
        "track": "rotation",
        "dimension": "shared_future",
        "prompt": "最近我们对相处频率、联系节奏或见面安排，有更清楚的预期。",
        "rotation_group": "future-b",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-shared-future-3",
        "track": "rotation",
        "dimension": "shared_future",
        "prompt": "最近讨论现实问题时，我们更像在一起想办法，而不是各顾各的。",
        "rotation_group": "future-c",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-shared-future-4",
        "track": "rotation",
        "dimension": "shared_future",
        "prompt": "最近我们还能一起商量接下来一个月要怎么相处得更舒服。",
        "rotation_group": "future-d",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-shared-future-5",
        "track": "rotation",
        "dimension": "shared_future",
        "prompt": "最近我们对这段关系最想保住的东西，说得越来越清楚。",
        "rotation_group": "future-e",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-shared-future-6",
        "track": "rotation",
        "dimension": "shared_future",
        "prompt": "最近我们还能对接下来的安排有一点共同期待，而不是只剩拖着。",
        "rotation_group": "future-f",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-vitality-1",
        "track": "rotation",
        "dimension": "vitality",
        "prompt": "最近和对方相处完，我被耗空的感觉比以前少了一点。",
        "rotation_group": "vitality-a",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-vitality-2",
        "track": "rotation",
        "dimension": "vitality",
        "prompt": "最近我们偶尔还能自然笑出来，而不只是处理问题。",
        "rotation_group": "vitality-b",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-vitality-3",
        "track": "rotation",
        "dimension": "vitality",
        "prompt": "最近这段关系里，不只是任务和矛盾，还是有一点陪伴感。",
        "rotation_group": "vitality-c",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-vitality-4",
        "track": "rotation",
        "dimension": "vitality",
        "prompt": "最近我们还有一些不带压力的小互动，让人觉得关系还活着。",
        "rotation_group": "vitality-d",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-vitality-5",
        "track": "rotation",
        "dimension": "vitality",
        "prompt": "最近想到对方时，我不只是紧绷，也会有一点想靠近的感觉。",
        "rotation_group": "vitality-e",
        "active": True,
        "version": "v1",
    },
    {
        "item_id": "rot-vitality-6",
        "track": "rotation",
        "dimension": "vitality",
        "prompt": "最近这段关系虽然有压力，但没有一直压到我喘不过气。",
        "rotation_group": "vitality-f",
        "active": True,
        "version": "v1",
    },
]

ITEMS_BY_ID = {item["item_id"]: item for item in ASSESSMENT_ITEM_BANK}
CORE_ITEMS = [item for item in ASSESSMENT_ITEM_BANK if item["track"] == "core"]
ROTATION_ITEMS = [item for item in ASSESSMENT_ITEM_BANK if item["track"] == "rotation"]


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _assessment_profile_for_pair(pair: Pair | None) -> str:
    if not pair:
        return "solo"
    if pair.is_long_distance and pair.type in {PairType.COUPLE, PairType.SPOUSE}:
        return "long_distance"
    if pair.type in {PairType.FRIEND, PairType.BESTFRIEND}:
        return "friend"
    if pair.type in {PairType.SPOUSE, PairType.PARENT}:
        return "spouse"
    return "couple"


def _prompt_for_profile(item: dict, profile: str) -> str:
    variants = ASSESSMENT_PROMPT_VARIANTS.get(profile) or {}
    return variants.get(item["item_id"], item["prompt"])


def _serialize_item(item: dict, *, profile: str) -> dict:
    return {
        **item,
        "prompt": _prompt_for_profile(item, profile),
        "dimension_label": DIMENSION_LABELS.get(item["dimension"], item["dimension"]),
        "options": [dict(option) for option in LIKERT_OPTIONS],
    }


async def _get_recent_assessment_events(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    limit: int = 6,
) -> list[RelationshipEvent]:
    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.event_type == "assessment.weekly_submitted",
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.user_id == user_id,
        )
        .order_by(desc(RelationshipEvent.occurred_at), desc(RelationshipEvent.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


def _used_item_ids(events: list[RelationshipEvent]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for event in events:
        payload = event.payload or {}
        for answer in payload.get("answers") or []:
            item_id = str(answer.get("item_id") or "").strip()
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            ordered.append(item_id)
    return ordered


def _low_dimensions_from_latest(events: list[RelationshipEvent]) -> list[str]:
    if not events:
        return []
    latest_payload = events[0].payload or {}
    dimension_scores = latest_payload.get("dimension_scores") or []
    ranked = sorted(
        [
            (
                str(item.get("id") or "").strip(),
                item.get("score"),
            )
            for item in dimension_scores
            if item.get("id")
        ],
        key=lambda entry: (
            999 if entry[1] is None else int(entry[1]),
            entry[0],
        ),
    )
    return [dimension for dimension, _ in ranked if dimension]


def _stable_dimension_order(
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> list[str]:
    dimensions = list(DIMENSION_LABELS.keys())
    stable_key = str(pair_id or user_id or "").strip()
    if not stable_key:
        return dimensions
    offset = sum(ord(ch) for ch in stable_key if ch.isalnum()) % len(dimensions)
    return dimensions[offset:] + dimensions[:offset]


def _rotation_candidates(
    low_dimensions: list[str],
    used_item_ids: list[str],
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> list[dict]:
    ordered_dimensions = list(
        dict.fromkeys(
            [dim for dim in low_dimensions if dim in DIMENSION_LABELS]
            + _stable_dimension_order(pair_id=pair_id, user_id=user_id)
        )
    )
    candidates: list[dict] = []
    seen_item_ids: set[str] = set()
    recently_used = set(used_item_ids[:12])

    for dimension in ordered_dimensions:
        for item in ROTATION_ITEMS:
            if item["dimension"] != dimension or not item["active"]:
                continue
            if item["item_id"] in seen_item_ids:
                continue
            if item["item_id"] in recently_used:
                continue
            candidates.append(item)
            seen_item_ids.add(item["item_id"])

    if len(candidates) >= 4:
        return candidates

    for item in ROTATION_ITEMS:
        if not item["active"] or item["item_id"] in seen_item_ids:
            continue
        candidates.append(item)
        seen_item_ids.add(item["item_id"])

    return candidates


async def build_weekly_assessment_pack(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
) -> dict:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    pair = await db.get(Pair, normalized_pair_id) if normalized_pair_id else None
    profile = _assessment_profile_for_pair(pair)
    profile_copy = ASSESSMENT_PROFILE_COPY.get(profile, ASSESSMENT_PROFILE_COPY["couple"])
    recent_events = await _get_recent_assessment_events(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        limit=6,
    )
    used_item_ids = _used_item_ids(recent_events)
    low_dimensions = _low_dimensions_from_latest(recent_events)
    rotation_items = _rotation_candidates(
        low_dimensions,
        used_item_ids,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )[:4]
    items = CORE_ITEMS + rotation_items

    if len(items) < 10:
        fallback_ids = {item["item_id"] for item in items}
        for item in ROTATION_ITEMS:
            if item["item_id"] in fallback_ids or not item["active"]:
                continue
            items.append(item)
            fallback_ids.add(item["item_id"])
            if len(items) >= 10:
                break

    latest_payload = recent_events[0].payload if recent_events else {}
    latest_score = latest_payload.get("total_score") if isinstance(latest_payload, dict) else None
    change_summary = (
        str(latest_payload.get("change_summary") or "").strip()
        if isinstance(latest_payload, dict)
        else ""
    )

    return {
        "title": profile_copy["title"],
        "subtitle": profile_copy["subtitle"],
        "latest_score": latest_score if latest_score is not None else None,
        "change_summary": change_summary or "这次先做 10 题正式体检，后面再看趋势变化。",
        "items": [_serialize_item(item, profile=profile) for item in items[:10]],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
