"""Product preference helpers for client-side AI and privacy modes."""

from __future__ import annotations

from typing import Literal

from app.services.task_planner import normalize_task_planner_defaults


PrivacyMode = Literal["cloud"]
PreferredEntry = Literal["daily", "emergency", "reflection"]

DEFAULT_PRODUCT_PREFS: dict[str, object] = {
    "ai_assist_enabled": True,
    "privacy_mode": "cloud",
    "preferred_entry": "daily",
    "preferred_language": "zh",
    "tone_preference": "gentle",
    "response_length": "medium",
    "relationship_space_theme": "classic",
    "spiritual_support_enabled": False,
    "living_region": "",
    "selected_pair_id": "",
    "custom_mood_presets": [],
    "hidden_default_moods": [],
    "avatar_presentation": {
        "focus_x": 50.0,
        "focus_y": 50.0,
        "scale": 1.0,
    },
    "task_planner_defaults": normalize_task_planner_defaults(None),
    "habit_profile": {
        "taboos": [],
        "comfort_preferences": [],
        "custom_notes": "",
    },
}

DEFAULT_SUGGESTED_TABOOS = (
    "反感长篇大论的说教",
    "疲惫时不喜被追问细节",
    "讨厌做家务时居高临下邀功",
    "反感空洞的加油打气",
    "抗拒被查岗或催促表态",
    "冷战时别硬逼马上说清楚",
)

DEFAULT_SUGGESTED_COMFORT_PREFERENCES = (
    "疲惫时先给一杯温水或安静陪伴",
    "有事直接给解决方案不用绕弯",
    "先接住感受再讨论对错",
    "看重实际行动胜过口头安慰",
)

DEFAULT_CHECKIN_MOODS = (
    "开心",
    "平静",
    "感动",
    "期待",
    "焦虑",
    "委屈",
    "生气",
    "疲惫",
)
DEFAULT_CHECKIN_MOOD_SET = frozenset(DEFAULT_CHECKIN_MOODS)

VALID_PRIVACY_MODES = {"cloud"}
VALID_PREFERRED_ENTRIES = {"daily", "emergency", "reflection"}
VALID_PREFERRED_LANGUAGES = {"zh", "en", "mixed"}
VALID_TONE_PREFERENCES = {"gentle", "direct", "warm", "concise"}
VALID_RESPONSE_LENGTHS = {"short", "medium", "long"}
VALID_RELATIONSHIP_SPACE_THEMES = {"classic", "stardust", "engine"}
MAX_LIVING_REGION_LENGTH = 40
MAX_SELECTED_PAIR_ID_LENGTH = 64
MAX_CUSTOM_MOOD_PRESETS = 12
MAX_CUSTOM_MOOD_LENGTH = 24


def _clamp_avatar_axis(value: object, *, fallback: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return max(0.0, min(100.0, round(numeric, 2)))


def _clamp_avatar_scale(value: object, *, fallback: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return max(1.0, min(3.0, round(numeric, 2)))


def _normalize_avatar_presentation(raw: object) -> dict[str, float]:
    default = dict(DEFAULT_PRODUCT_PREFS["avatar_presentation"])  # type: ignore[arg-type]
    if not isinstance(raw, dict):
        return default

    return {
        "focus_x": _clamp_avatar_axis(
            raw.get("focus_x"),
            fallback=float(default["focus_x"]),
        ),
        "focus_y": _clamp_avatar_axis(
            raw.get("focus_y"),
            fallback=float(default["focus_y"]),
        ),
        "scale": _clamp_avatar_scale(
            raw.get("scale"),
            fallback=float(default["scale"]),
        ),
    }


def _normalize_custom_mood_presets(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        value = (
            str(item or "")
            .replace("\n", " ")
            .replace("\r", " ")
            .strip()
        )
        value = " ".join(value.split())
        value = value.rstrip("，、；;")
        if not value:
            continue
        value = value[:MAX_CUSTOM_MOOD_LENGTH]
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
        if len(normalized) >= MAX_CUSTOM_MOOD_PRESETS:
            break
    return normalized


def _normalize_hidden_default_moods(raw: object) -> list[str]:
    return [
        value
        for value in _normalize_custom_mood_presets(raw)
        if value in DEFAULT_CHECKIN_MOOD_SET
    ]


MAX_HABIT_TAGS = 16
MAX_HABIT_TAG_LENGTH = 32
MAX_HABIT_NOTES_LENGTH = 200


def _normalize_habit_tags(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        val = str(item or "").replace("\n", " ").replace("\r", " ").strip()
        val = " ".join(val.split())
        val = val.rstrip("，、；;")
        if not val:
            continue
        val = val[:MAX_HABIT_TAG_LENGTH]
        key = val.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(val)
        if len(normalized) >= MAX_HABIT_TAGS:
            break
    return normalized


def _normalize_habit_profile(raw: object) -> dict[str, object]:
    default = {
        "taboos": [],
        "comfort_preferences": [],
        "custom_notes": "",
    }
    if not isinstance(raw, dict):
        return default
    return {
        "taboos": _normalize_habit_tags(raw.get("taboos")),
        "comfort_preferences": _normalize_habit_tags(raw.get("comfort_preferences")),
        "custom_notes": str(raw.get("custom_notes") or "").strip()[:MAX_HABIT_NOTES_LENGTH],
    }


def normalize_product_prefs(raw: dict | None) -> dict[str, object]:
    payload = dict(DEFAULT_PRODUCT_PREFS)
    if not isinstance(raw, dict):
        return payload

    if isinstance(raw.get("ai_assist_enabled"), bool):
        payload["ai_assist_enabled"] = raw["ai_assist_enabled"]

    preferred_entry = str(raw.get("preferred_entry") or "").strip()
    if preferred_entry in VALID_PREFERRED_ENTRIES:
        payload["preferred_entry"] = preferred_entry

    preferred_language = str(raw.get("preferred_language") or "").strip()
    if preferred_language in VALID_PREFERRED_LANGUAGES:
        payload["preferred_language"] = preferred_language

    tone_preference = str(raw.get("tone_preference") or "").strip()
    if tone_preference in VALID_TONE_PREFERENCES:
        payload["tone_preference"] = tone_preference

    response_length = str(raw.get("response_length") or "").strip()
    if response_length in VALID_RESPONSE_LENGTHS:
        payload["response_length"] = response_length

    relationship_space_theme = str(raw.get("relationship_space_theme") or "").strip()
    if relationship_space_theme in VALID_RELATIONSHIP_SPACE_THEMES:
        payload["relationship_space_theme"] = relationship_space_theme

    if isinstance(raw.get("spiritual_support_enabled"), bool):
        payload["spiritual_support_enabled"] = raw["spiritual_support_enabled"]

    living_region = str(raw.get("living_region") or "").strip()
    if living_region:
        payload["living_region"] = living_region[:MAX_LIVING_REGION_LENGTH]

    selected_pair_id = str(raw.get("selected_pair_id") or "").strip()
    if selected_pair_id:
        payload["selected_pair_id"] = selected_pair_id[:MAX_SELECTED_PAIR_ID_LENGTH]

    payload["custom_mood_presets"] = _normalize_custom_mood_presets(
        raw.get("custom_mood_presets")
    )
    payload["hidden_default_moods"] = _normalize_hidden_default_moods(
        raw.get("hidden_default_moods")
    )
    payload["avatar_presentation"] = _normalize_avatar_presentation(
        raw.get("avatar_presentation")
    )
    payload["task_planner_defaults"] = normalize_task_planner_defaults(
        raw.get("task_planner_defaults")
    )
    payload["habit_profile"] = _normalize_habit_profile(
        raw.get("habit_profile")
    )

    return payload


def resolve_privacy_mode(raw: dict | None) -> PrivacyMode:
    _ = normalize_product_prefs(raw)
    return "cloud"
