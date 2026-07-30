from __future__ import annotations

import json
import time

import httpx

from core.config import settings
from .base import ModelProvider, StructuredModelResponse


class OpenAICompatibleProvider(ModelProvider):
    name = "openai-compatible"

    def generate_structured(self, *, system_prompt, user_content, json_schema):
        if not settings.model_api_key or not settings.model_name:
            raise RuntimeError("外部模型未配置：请设置 MODEL_API_KEY 和 MODEL_NAME。")
        attempts = settings.model_max_retries + 1
        response = None
        for attempt in range(1, attempts + 1):
            try:
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
                break
            except httpx.TimeoutException:
                if attempt >= attempts:
                    raise RuntimeError(f"外部模型请求超时，已尝试 {attempt} 次。") from None
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                retryable = status == 429 or status >= 500
                if not retryable or attempt >= attempts:
                    raise RuntimeError(f"外部模型请求失败（HTTP {status}，尝试 {attempt} 次）。") from None
            time.sleep(min(2.0, 0.25 * (2 ** (attempt - 1))))
        if response is None:
            raise RuntimeError("外部模型请求没有返回响应。")
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("外部模型响应不符合结构化输出协议。") from exc
        if not isinstance(data, dict):
            raise RuntimeError("外部模型结构化输出必须是 JSON 对象。")
        used_attempts = attempt
        warnings = [f"外部模型在第 {used_attempts} 次尝试后成功。"] if used_attempts > 1 else []
        return StructuredModelResponse(
            data=data,
            warnings=warnings,
            model_name=settings.model_name,
        )
