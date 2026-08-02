from dataclasses import dataclass
from typing import Literal

from app.core.config import settings


ProviderName = Literal[
    "Alibaba Cloud Bailian",
    "DeepSeek",
    "OpenAI",
    "Anthropic",
]


@dataclass(frozen=True)
class ModelConfig:
    """
    一个模型在统一平台中的完整基础配置。

    public_id:
        网页、用户和平台 API 使用的统一模型编号。

    upstream_model:
        LiteLLM 中实际配置的模型名称。

    display_name:
        网页中展示给用户的模型名称。

    provider:
        上游模型供应商。

    enabled:
        是否允许平台用户调用。

    supports_streaming:
        是否支持流式输出。

    supports_reasoning:
        是否支持深度思考或推理模式。

    supports_tools:
        是否支持工具调用。

    supports_vision:
        是否支持图片输入。

    default_temperature:
        普通聊天模式默认温度。

    default_max_output_tokens:
        默认最大输出 Token 数。

    max_output_tokens:
        平台允许用户设置的最大输出 Token 数。
    """

    public_id: str
    upstream_model: str
    display_name: str
    provider: ProviderName

    enabled: bool

    supports_streaming: bool
    supports_reasoning: bool
    supports_tools: bool
    supports_vision: bool

    default_temperature: float
    default_max_output_tokens: int
    max_output_tokens: int


MODEL_REGISTRY: dict[str, ModelConfig] = {
    "qwen-plus": ModelConfig(
        public_id="qwen-plus",
        upstream_model="qwen3.7-plus",
        display_name="Qwen Plus",
        provider="Alibaba Cloud Bailian",
        enabled=True,
        supports_streaming=True,
        supports_reasoning=True,
        supports_tools=False,
        supports_vision=False,
        default_temperature=0.7,
        default_max_output_tokens=1024,
        max_output_tokens=8192,
    ),

    "deepseek-v4-flash": ModelConfig(
        public_id="deepseek-v4-flash",
        upstream_model="deepseek-v4-flash",
        display_name="DeepSeek V4 Flash",
        provider="DeepSeek",
        enabled=True,
        supports_streaming=True,
        supports_reasoning=True,
        supports_tools=False,
        supports_vision=False,
        default_temperature=0.7,
        default_max_output_tokens=1024,
        max_output_tokens=8192,
    ),
}


def get_model_config(model_id: str) -> ModelConfig:
    """
    根据平台统一模型编号读取模型配置。

    这里只负责查找，不负责生成 HTTP 错误。
    HTTP 状态码由 API 路由层处理。
    """

    model_config = MODEL_REGISTRY.get(model_id)

    if model_config is None:
        raise KeyError(
            f"Model '{model_id}' is not registered."
        )

    if not model_config.enabled:
        raise PermissionError(
            f"Model '{model_id}' is disabled."
        )

    return model_config


def get_enabled_models() -> list[ModelConfig]:
    """
    返回所有已启用模型。
    """

    return [
        model_config
        for model_config in MODEL_REGISTRY.values()
        if model_config.enabled
    ]


def validate_default_model() -> None:
    """
    启动时检查默认模型配置是否合法。
    """

    if settings.default_model_id not in MODEL_REGISTRY:
        raise RuntimeError(
            "DEFAULT_MODEL_ID "
            f"'{settings.default_model_id}' "
            "does not exist in MODEL_REGISTRY."
        )

    default_model = MODEL_REGISTRY[
        settings.default_model_id
    ]

    if not default_model.enabled:
        raise RuntimeError(
            "DEFAULT_MODEL_ID "
            f"'{settings.default_model_id}' "
            "is currently disabled."
        )


validate_default_model()