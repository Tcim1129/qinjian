"""低内存场景下的本地文本隐私代理。"""

from __future__ import annotations

import copy
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.services.privacy_sandbox import (
    CONFIDENTIAL_TOKEN_PATTERN,
    EMAIL_PATTERN,
    EXTRA_SENSITIVE_PATTERNS,
    JWT_PATTERN,
    LONG_NUMBER_PATTERN,
    PHONE_PATTERN,
    UUID_PATTERN,
    redact_message_payload,
)

PROXY_PATTERN_SPECS = (
    ("TOKEN", JWT_PATTERN),
    ("PHONE", PHONE_PATTERN),
    ("EMAIL", EMAIL_PATTERN),
    ("UUID", UUID_PATTERN),
    ("LONG", LONG_NUMBER_PATTERN),
    ("CONFIDENTIAL_TOKEN", CONFIDENTIAL_TOKEN_PATTERN),
    *(("CONFIDENTIAL_TERM", pattern) for pattern in EXTRA_SENSITIVE_PATTERNS),
)


@dataclass(slots=True)
class ProxyReplacement:
    entity_type: str
    placeholder: str
    value: str


@dataclass(slots=True)
class PrivacyTextProxyBundle:
    messages: list[dict[str, Any]]
    placeholder_map: dict[str, str] = field(default_factory=dict)
    replacements: list[ProxyReplacement] = field(default_factory=list)
    replacement_count: int = 0
    entity_counts: dict[str, int] = field(default_factory=dict)

    def metrics(self) -> dict[str, Any]:
        return {
            "replacement_count": int(self.replacement_count),
            "placeholder_count": len(self.placeholder_map),
            "entity_counts": dict(self.entity_counts),
        }


class _ProxyAccumulator:
    def __init__(self) -> None:
        self.placeholder_map: dict[str, str] = {}
        self._value_to_placeholder: dict[str, str] = {}
        self._counters: Counter[str] = Counter()
        self._entity_counts: Counter[str] = Counter()
        self._replacements: list[ProxyReplacement] = []
        self._replacement_count = 0

    def proxy_text(self, text: str) -> str:
        if not text:
            return text

        proxied = str(text)
        for entity_type, pattern in PROXY_PATTERN_SPECS:
            proxied = pattern.sub(
                lambda match, current_type=entity_type: self._replace_match(
                    current_type, match.group(0)
                ),
                proxied,
            )
        return proxied

    def _replace_match(self, entity_type: str, value: str) -> str:
        self._replacement_count += 1
        self._entity_counts[entity_type] += 1
        cached = self._value_to_placeholder.get(value)
        if cached:
            return cached

        self._counters[entity_type] += 1
        placeholder = f"[{entity_type}_{self._counters[entity_type]}]"
        self._value_to_placeholder[value] = placeholder
        self.placeholder_map[placeholder] = value
        self._replacements.append(
            ProxyReplacement(entity_type=entity_type, placeholder=placeholder, value=value)
        )
        return placeholder

    def build_bundle(self, messages: list[dict[str, Any]]) -> PrivacyTextProxyBundle:
        return PrivacyTextProxyBundle(
            messages=messages,
            placeholder_map=dict(self.placeholder_map),
            replacements=list(self._replacements),
            replacement_count=int(self._replacement_count),
            entity_counts=dict(self._entity_counts),
        )


def proxy_message_payload(
    messages: Sequence[Mapping[str, Any]],
) -> PrivacyTextProxyBundle:
    accumulator = _ProxyAccumulator()
    proxied_messages = [
        _proxy_mapping(dict(message), accumulator=accumulator) for message in messages
    ]
    # 占位替换后再跑一遍脱敏，作为第二道保护。
    sanitized_messages = redact_message_payload(proxied_messages, enabled=True)
    return accumulator.build_bundle(sanitized_messages)


def _proxy_mapping(
    data: Mapping[str, Any],
    *,
    accumulator: _ProxyAccumulator,
) -> dict[str, Any]:
    proxied: dict[str, Any] = {}
    for key, value in data.items():
        proxied[key] = _proxy_value(value, key=key, accumulator=accumulator)
    return proxied


def _proxy_value(
    value: Any,
    *,
    accumulator: _ProxyAccumulator,
    key: str | None = None,
) -> Any:
    if isinstance(value, str):
        if key == "url":
            return value
        return accumulator.proxy_text(value)

    if isinstance(value, Mapping):
        return {
            item_key: _proxy_value(
                item_value, key=item_key, accumulator=accumulator
            )
            for item_key, item_value in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [
            _proxy_value(item, accumulator=accumulator)
            for item in value
        ]

    return copy.deepcopy(value)


def rehydrate_content(value: Any, placeholder_map: Mapping[str, str] | None) -> Any:
    if not placeholder_map:
        return copy.deepcopy(value)

    if isinstance(value, str):
        restored = value
        for placeholder, raw in sorted(
            placeholder_map.items(), key=lambda item: len(item[0]), reverse=True
        ):
            restored = restored.replace(placeholder, raw)
        return restored

    if isinstance(value, Mapping):
        return {
            item_key: rehydrate_content(item_value, placeholder_map)
            for item_key, item_value in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [rehydrate_content(item, placeholder_map) for item in value]

    return copy.deepcopy(value)


def count_sensitive_matches(text: str) -> int:
    if not text:
        return 0
    total = 0
    for _, pattern in PROXY_PATTERN_SPECS:
        total += len(pattern.findall(str(text)))
    return total
