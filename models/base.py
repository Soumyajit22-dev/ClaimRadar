from dataclasses import dataclass, field
import os
from typing import Optional, Tuple
from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from configs.config import get_settings

# Individual getter functions
def _get_openai_model() -> Tuple[OpenAIModel, Optional[ModelSettings]]:
    """Returns OpenAI model and its settings."""
    load_dotenv()
    settings = get_settings()
    openai_model = OpenAIModel(
        model_name="gpt-4.1-mini",
        provider=OpenAIProvider(
            api_key=settings.api_keys.openai_api_key.get_secret_value(),
        )
    )
    openai_model_settings = ModelSettings(
    max_tokens=8192,
    parallel_tool_calls=True
)

    return openai_model, openai_model_settings


def get_model(provider: str = "openai"):
    """Get model and settings based on provider."""
    match provider:
        case "openai":
            return _get_openai_model()
        case _:
            raise ValueError(f"Invalid provider: {provider}")