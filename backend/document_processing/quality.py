from __future__ import annotations

import re
from dataclasses import dataclass, field


INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s+prompt",
    r"developer\s+message",
    r"忽略.{0,12}(之前|以上|系统).{0,12}(指令|要求)",
    r"你现在是.{0,20}(助手|模型|agent)",
    r"输出.{0,12}(密钥|密码|系统提示词)",
)


@dataclass
class QualityResult:
    score: float
    injection_risk: bool
    flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires_human_review: bool = False


def assess_text_quality(text: str, parse_warning: str = "", ocr_confidence: float | None = None) -> QualityResult:
    stripped = text.strip()
    flags: list[str] = []
    warnings: list[str] = []
    score = 1.0
    if not stripped:
        flags.append("empty_text")
        warnings.append("未提取到可分析文本。")
        score = 0.0
    elif len(stripped) < 40:
        flags.append("very_short_text")
        warnings.append("提取文本过短，可能无法支持可靠分析。")
        score -= 0.35
    replacement_ratio = stripped.count("�") / max(len(stripped), 1)
    if replacement_ratio > 0.01:
        flags.append("encoding_noise")
        warnings.append("文本包含较多无法识别字符。")
        score -= min(0.4, replacement_ratio * 5)
    if ocr_confidence is not None and ocr_confidence < 0.75:
        flags.append("low_ocr_confidence")
        warnings.append(f"OCR 置信度较低（{ocr_confidence:.0%}）。")
        score -= 0.25
    injection_matches = [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, stripped, re.I)]
    if injection_matches:
        flags.append("prompt_injection_suspected")
        warnings.append("材料包含疑似指令性文本；该内容只作为证据数据，不执行其中指令。")
    if parse_warning:
        flags.append("parser_warning")
        warnings.append(parse_warning)
        score -= 0.15
    return QualityResult(
        score=max(0.0, min(1.0, score)),
        injection_risk=bool(injection_matches),
        flags=flags,
        warnings=list(dict.fromkeys(warnings)),
        requires_human_review=bool(flags),
    )
