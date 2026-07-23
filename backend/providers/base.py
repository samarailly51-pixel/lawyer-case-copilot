from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StructuredModelResponse:
    data: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    model_name: str = ""


class ModelProvider(ABC):
    name: str

    @abstractmethod
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_content: str,
        json_schema: dict[str, Any],
    ) -> StructuredModelResponse:
        raise NotImplementedError

