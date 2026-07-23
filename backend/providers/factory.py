from core.config import settings
from .base import ModelProvider
from .mock import MockProvider
from .openai_compatible import OpenAICompatibleProvider


def get_provider() -> ModelProvider:
    if settings.model_provider == "openai-compatible":
        return OpenAICompatibleProvider()
    return MockProvider()

