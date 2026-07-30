from __future__ import annotations

import json

import httpx

import providers.openai_compatible as provider_module
from providers.openai_compatible import OpenAICompatibleProvider


class _Settings:
    model_api_key = "synthetic-test-key"
    model_name = "synthetic-test-model"
    model_base_url = "https://example.invalid/v1"
    model_temperature = 0.1
    model_timeout_seconds = 1
    model_max_retries = 2


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://example.invalid/v1/chat/completions")


def _success() -> httpx.Response:
    return httpx.Response(
        200,
        request=_request(),
        json={"choices": [{"message": {"content": json.dumps({"facts": []})}}]},
    )


def test_provider_retries_timeout_then_returns_structured_result(monkeypatch):
    calls = 0

    def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("synthetic timeout", request=_request())
        return _success()

    monkeypatch.setattr(provider_module, "settings", _Settings())
    monkeypatch.setattr(provider_module.httpx, "post", fake_post)
    monkeypatch.setattr(provider_module.time, "sleep", lambda _: None)
    result = OpenAICompatibleProvider().generate_structured(
        system_prompt="test",
        user_content="{}",
        json_schema={"type": "object"},
    )
    assert calls == 2
    assert result.data == {"facts": []}
    assert "第 2 次尝试" in result.warnings[0]


def test_provider_does_not_retry_non_retryable_client_error(monkeypatch):
    calls = 0

    def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        return httpx.Response(400, request=_request(), json={"error": "bad request"})

    monkeypatch.setattr(provider_module, "settings", _Settings())
    monkeypatch.setattr(provider_module.httpx, "post", fake_post)
    monkeypatch.setattr(provider_module.time, "sleep", lambda _: None)
    try:
        OpenAICompatibleProvider().generate_structured(
            system_prompt="test",
            user_content="{}",
            json_schema={"type": "object"},
        )
    except RuntimeError as exc:
        assert "HTTP 400" in str(exc)
    else:
        raise AssertionError("HTTP 400 应立即失败")
    assert calls == 1


def test_provider_rejects_non_json_object(monkeypatch):
    response = httpx.Response(
        200,
        request=_request(),
        json={"choices": [{"message": {"content": "[]"}}]},
    )
    monkeypatch.setattr(provider_module, "settings", _Settings())
    monkeypatch.setattr(provider_module.httpx, "post", lambda *args, **kwargs: response)
    try:
        OpenAICompatibleProvider().generate_structured(
            system_prompt="test",
            user_content="{}",
            json_schema={"type": "object"},
        )
    except RuntimeError as exc:
        assert "JSON 对象" in str(exc)
    else:
        raise AssertionError("数组响应必须被拒绝")
