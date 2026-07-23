from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted_types: tuple[str, ...]
    replacements: int


PATTERNS = (
    ("mainland_id", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "[身份证号已脱敏]"),
    ("mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[手机号已脱敏]"),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[邮箱已脱敏]"),
    ("bank_card", re.compile(r"(?<!\d)\d{16,19}(?!\d)"), "[银行卡号已脱敏]"),
)


def redact_text(text: str) -> RedactionResult:
    value = text
    types: list[str] = []
    count = 0
    for name, pattern, replacement in PATTERNS:
        value, replaced = pattern.subn(replacement, value)
        if replaced:
            types.append(name); count += replaced
    return RedactionResult(value, tuple(types), count)

