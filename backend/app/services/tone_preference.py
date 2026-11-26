"""说话方式偏好：只调语气与直接程度，不改人格锚点，也不把用户状态当偏好。

用户每点一次“像我想要的”或“不太像”，这里记一条信号；同一方向攒够三条、
且距离上次调整满七天，才会挪一格。挪动都留历史，用户可以一键回到默认。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

AXIS_VALUES = (-1, 0, 1)
WINDOW_DAYS = 30
MIN_SIGNALS = 3
COOLDOWN_DAYS = 7

AXIS_GUIDE = {
    "directness": {
        -1: "更软一些：先接住感受，再给看法，不主动指出问题。",
        0: "该说的时候直说，不绕弯也不硬顶。",
        1: "直接一点：先说结论和能做的动作，少铺垫，不用“其实/确实”这类缓冲词。",
    },
    "warmth": {
        -1: "平一点：不加语气词，不用“～”，就正常说话，别在句尾补“啊/哦”显得客气。",
        0: "正常的热度：语气词能不加就不加，一句最多一个，别每句都带。",
        1: "暖一点：把话放轻，先接住再给话；真要加语气词就挑一个（呀、啦、嘛、诶），只放在轻松的地方，对方难受时不加。",
    },
}

# 用户原话里能看出方向的说法
_DIRECTNESS_UP = ("太客套", "客套", "太官方", "官方", "套话", "别绕", "直接说", "说重点", "别铺垫", "少来这套")
_DIRECTNESS_DOWN = ("太冲", "太凶", "别这么冲", "太硬", "语气重")
_WARMTH_DOWN = ("太啰嗦", "太长", "别分析了", "别讲道理", "大道理", "说教", "别安慰")
_WARMTH_UP = ("太冷", "冷淡", "敷衍", "没人味", "生硬")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def default_profile() -> dict[str, Any]:
    return {
        "directness": 0,
        "warmth": 0,
        "updated_at": None,
        "last_change_at": None,
        "history": [],
        "signals": [],
    }


def _normalize_axis(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number in AXIS_VALUES else 0


def read_profile(raw: Any) -> dict[str, Any]:
    profile = default_profile()
    if not isinstance(raw, dict):
        return profile
    profile["directness"] = _normalize_axis(raw.get("directness"))
    profile["warmth"] = _normalize_axis(raw.get("warmth"))
    profile["updated_at"] = raw.get("updated_at")
    profile["last_change_at"] = raw.get("last_change_at")
    history = raw.get("history")
    if isinstance(history, list):
        profile["history"] = [item for item in history if isinstance(item, dict)][-20:]
    signals = raw.get("signals")
    if isinstance(signals, list):
        profile["signals"] = [item for item in signals if isinstance(item, dict)][-60:]
    return profile


def classify_note(note: str | None) -> dict[str, int]:
    """把用户的一句话变成方向：加号表示“往这边走”。"""
    text = str(note or "")
    delta = {"directness": 0, "warmth": 0}
    if any(word in text for word in _DIRECTNESS_UP):
        delta["directness"] += 1
    if any(word in text for word in _DIRECTNESS_DOWN):
        delta["directness"] -= 1
    if any(word in text for word in _WARMTH_DOWN):
        delta["warmth"] -= 1
    if any(word in text for word in _WARMTH_UP):
        delta["warmth"] += 1
    return delta


def record_signal(
    raw_profile: Any,
    *,
    verdict: str,
    note: str | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """返回 (新的偏好, 本次处理结果)。verdict 只认 like / dislike。"""
    profile = read_profile(raw_profile)
    moment = now or _now()
    stamp = moment.isoformat()
    verdict = "like" if str(verdict).lower() == "like" else "dislike"

    # 气头上的话不算偏好：带脏话或纯情绪的直接记成当轮信号，不参与累计。
    text = str(note or "")
    angry = any(word in text for word in ("他妈", "妈的", "操", "滚", "烦死"))
    delta = classify_note(text)
    if angry and not (delta["directness"] or delta["warmth"]):
        return profile, {"changed": False, "reason": "这句话更像当轮情绪，先只影响这一次的回复。"}

    profile["signals"].append({"verdict": verdict, "note": text[:60], "delta": delta, "at": stamp})
    cutoff = moment - timedelta(days=WINDOW_DAYS)
    fresh = []
    for item in profile["signals"]:
        try:
            moment_of_item = datetime.fromisoformat(str(item.get("at")))
        except (TypeError, ValueError):
            continue
        if moment_of_item >= cutoff:
            fresh.append(item)
    profile["signals"] = fresh[-60:]
    if not any(delta.values()):
        return profile, {"changed": False, "reason": "已记录评价；没有说明语气方向，不调整档位。"}

    last_change = None
    if profile.get("last_change_at"):
        try:
            last_change = datetime.fromisoformat(str(profile["last_change_at"]))
        except (TypeError, ValueError):
            last_change = None

    changed: list[str] = []
    for axis, step in delta.items():
        if not step:
            continue
        same_direction = [
            item for item in profile["signals"]
            if int((item.get("delta") or {}).get(axis) or 0) * step > 0
        ]
        if len(same_direction) < MIN_SIGNALS:
            continue
        if last_change is not None and moment - last_change < timedelta(days=COOLDOWN_DAYS):
            continue
        current = _normalize_axis(profile.get(axis))
        target = max(-1, min(1, current + (1 if step > 0 else -1)))
        if target == current:
            continue
        profile[axis] = target
        changed.append(axis)

    if changed:
        profile["last_change_at"] = stamp
        profile["history"].append({"at": stamp, "changed": changed,
                                   "directness": profile["directness"], "warmth": profile["warmth"]})
        profile["history"] = profile["history"][-20:]
        profile["updated_at"] = stamp
        return profile, {"changed": True, "changed_axes": changed,
                         "directness": profile["directness"], "warmth": profile["warmth"],
                         "reason": "同一方向攒够三条，语气挪了一格。"}
    return profile, {"changed": False, "reason": "这条记下了，还不到调档的条件。"}


def guide_text(raw_profile: Any) -> str:
    profile = read_profile(raw_profile)
    lines = []
    directness = AXIS_GUIDE["directness"][_normalize_axis(profile["directness"])]
    warmth = AXIS_GUIDE["warmth"][_normalize_axis(profile["warmth"])]
    lines.append("- 直接程度：" + directness)
    lines.append("- 温度：" + warmth)
    return "\n".join(lines)


def reset_profile(raw_profile: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """回到默认，清空调整依据；历史仍保留，重新开始冷却。"""
    profile = read_profile(raw_profile)
    stamp = (now or _now()).isoformat()
    profile.update(directness=0, warmth=0, signals=[], updated_at=stamp, last_change_at=stamp)
    profile['history'] = profile['history'][-19:] + [
        {'at': stamp, 'changed': ['reset'], 'directness': 0, 'warmth': 0}
    ]
    return profile


def is_default(raw_profile: Any) -> bool:
    profile = read_profile(raw_profile)
    return profile["directness"] == 0 and profile["warmth"] == 0
