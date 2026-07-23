from __future__ import annotations

from .base import ModelProvider, StructuredModelResponse


class MockProvider(ModelProvider):
    """Deterministic provider used by the portfolio demo and test suite."""

    name = "mock"

    def generate_structured(self, *, system_prompt, user_content, json_schema):
        return StructuredModelResponse(
            data={"status": "mocked", "items": []},
            warnings=["当前使用确定性演示 Provider，未调用外部模型。"],
            model_name="deterministic-demo",
        )

