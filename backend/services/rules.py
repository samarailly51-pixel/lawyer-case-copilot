from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


RULE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,119}$")
ALLOWED_SEVERITIES = {"low", "medium", "high"}
ALLOWED_OUTPUT_TYPES = {"missing_material", "risk", "checklist"}


@dataclass
class RuleValidation:
    valid: bool
    version: str
    rule_count: int
    enabled_rule_count: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)


def validate_rule_file(path: Path) -> RuleValidation:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return RuleValidation(False, "", 0, 0, errors=[f"{path.name}: 无法读取规则文件：{exc}"])

    rules = payload.get("rules")
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(rules, list):
        errors.append(f"{path.name}: rules 必须是数组。")
        rules = []
    seen: set[str] = set()
    enabled_count = 0
    for index, rule in enumerate(rules, 1):
        prefix = f"{path.name} 第 {index} 条"
        if not isinstance(rule, dict):
            errors.append(f"{prefix}: 规则必须是对象。")
            continue
        rule_id = str(rule.get("id", ""))
        if not RULE_ID_PATTERN.fullmatch(rule_id):
            errors.append(f"{prefix}: id 必须是稳定的小写英文标识。")
        elif rule_id in seen:
            errors.append(f"{prefix}: id {rule_id} 重复。")
        seen.add(rule_id)
        if not str(rule.get("description", "")).strip():
            errors.append(f"{prefix}: description 不能为空。")
        if rule.get("severity", "medium") not in ALLOWED_SEVERITIES:
            errors.append(f"{prefix}: severity 仅允许 low/medium/high。")
        if rule.get("output_type", "risk") not in ALLOWED_OUTPUT_TYPES:
            errors.append(f"{prefix}: output_type 不受支持。")
        if rule.get("severity") == "high" and rule.get("requires_human_review") is not True:
            errors.append(f"{prefix}: high 风险规则必须 requires_human_review=true。")
        if rule.get("enabled", True):
            enabled_count += 1
            source = rule.get("source") or {}
            if path.name == "personal_experience_rules.yaml":
                if not isinstance(source, dict) or source.get("title") in {None, "", "待律师补充"}:
                    errors.append(f"{prefix}: 启用个人经验规则前必须填写可核验的 source.title。")
                if rule.get("owner") in {None, "", "待填写"}:
                    errors.append(f"{prefix}: 启用个人经验规则前必须填写 owner。")
                if rule.get("jurisdiction") in {None, "", "待填写"}:
                    errors.append(f"{prefix}: 启用个人经验规则前必须填写 jurisdiction。")
                if not rule.get("reviewed_at"):
                    errors.append(f"{prefix}: 启用个人经验规则前必须填写 reviewed_at。")
    if not rules:
        warnings.append(f"{path.name}: 当前没有启用的实际规则。")
    version = str(payload.get("version", ""))
    if not version:
        errors.append(f"{path.name}: 缺少版本号。")
    return RuleValidation(
        valid=not errors,
        version=version,
        rule_count=len(rules),
        enabled_rule_count=enabled_count,
        errors=errors,
        warnings=warnings,
        payload=payload,
    )


def load_enabled_rules(path: Path, output_type: str | None = None) -> list[dict[str, Any]]:
    validation = validate_rule_file(path)
    if not validation.valid:
        raise RuntimeError("；".join(validation.errors))
    return [
        rule for rule in validation.payload.get("rules", [])
        if rule.get("enabled", True) and (output_type is None or rule.get("output_type") == output_type)
    ]
