from __future__ import annotations

import json

import httpx

from core.config import settings
from .base import ModelProvider, StructuredModelResponse


class OpenAICompatibleProvider(ModelProvider):
    name = "openai-compatible"

    def generate_structured(self, *, system_prompt, user_content, json_schema):
        if not settings.model_api_key or not settings.model_name:
            raise RuntimeError("外部模型未配置：请设置 MODEL_API_KEY 和 MODEL_NAME。")
        response = httpx.post(
            f"{settings.model_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.model_api_key}"},
            json={
                "model": settings.model_name,
                "temperature": settings.model_temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "case_node_output", "schema": json_schema, "strict": True},
                },
            },
            timeout=settings.model_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = json.loads(payload["choices"][0]["message"]["content"])
        return StructuredModelResponse(data=data, model_name=settings.model_name)

