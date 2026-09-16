"""Shared invite-code rules."""

import secrets

INVITE_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
INVITE_CODE_LENGTH = 10
INVITE_CODE_PATTERN = rf"^[{INVITE_CODE_ALPHABET}]{{{INVITE_CODE_LENGTH}}}$"


def normalize_invite_code(value: str) -> str:
    return value.strip().upper()


def generate_invite_code() -> str:
    return "".join(
        secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH)
    )
