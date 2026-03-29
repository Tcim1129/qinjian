"""Product preference helpers for client-side AI and privacy modes."""

from __future__ import annotations

from typing import Literal


PrivacyMode = Literal["cloud", "local_first"]
PreferredEntry = Literal["daily", "emergency", "reflection"]

DEFAULT_PRODUCT_PREFS: dict[str, object] = {
    "ai_assist_enabled": True,
    "privacy_mode": "cloud",
    "preferred_entry": "daily",
}

VALID_PRIVACY_MODES = {"cloud", "local_first"}
VALID_PREFERRED_ENTRIES = {"daily", "emergency", "reflection"}


def normalize_product_prefs(raw: dict | None) -> dict[str, object]:
    payload = dict(DEFAULT_PRODUCT_PREFS)
    if not isinstance(raw, dict):
        return payload

    if isinstance(raw.get("ai_assist_enabled"), bool):
        payload["ai_assist_enabled"] = raw["ai_assist_enabled"]

    privacy_mode = str(raw.get("privacy_mode") or "").strip()
    if privacy_mode in VALID_PRIVACY_MODES:
        payload["privacy_mode"] = privacy_mode

    preferred_entry = str(raw.get("preferred_entry") or "").strip()
    if preferred_entry in VALID_PREFERRED_ENTRIES:
        payload["preferred_entry"] = preferred_entry

    return payload

