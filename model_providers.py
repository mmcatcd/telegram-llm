from enum import Enum
from dataclasses import dataclass
from telegram.ext import ContextTypes
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel


class ModelProvider(str, Enum):
    ANTHROPIC = "ANTHROPIC"
    OPENAI = "OPENAI"

MODEL_PROVIDERS = [ModelProvider.ANTHROPIC, ModelProvider.OPENAI]
DEFAULT_MODEL_PROVIDER = ModelProvider.ANTHROPIC
DEFAULT_MODEL_ID = "claude-3-7-sonnet-latest"

@dataclass
class LLMModel:
    model_provider: ModelProvider
    model_id: str

    @property
    def model_string(self):
        return f"{self.model_provider.lower()}:{self.model_id}"
    
    @property
    def pydantic_model(self) -> OpenAIModel | AnthropicModel | None:
        if self.model_provider == ModelProvider.ANTHROPIC:
            return AnthropicModel(self.model_id)
        elif self.model_provider == ModelProvider.OPENAI:
            return OpenAIModel(self.model_id)


def get_current_user_model(context: ContextTypes.DEFAULT_TYPE) -> LLMModel:
    model_provider = context.user_data.get("model_provider")
    model_id = context.user_data.get("model_id")

    if not model_provider or not model_id:
        return LLMModel(
            model_provider=DEFAULT_MODEL_PROVIDER,
            model_id=DEFAULT_MODEL_ID,
        )
    
    return LLMModel(
        model_provider=ModelProvider(model_provider),
        model_id=model_id,
    )


def update_user_model(context: ContextTypes.DEFAULT_TYPE, llm_model: LLMModel) -> None:
    context.user_data["model_provider"] = llm_model.model_provider
    context.user_data["model_id"] = llm_model.model_id
