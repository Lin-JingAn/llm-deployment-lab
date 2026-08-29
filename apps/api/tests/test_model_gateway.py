import unittest

from app.core.model_registry import ModelConfig
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.model_gateway import (
    build_upstream_payload,
    extract_usage,
    resolve_max_output_tokens,
)


def model_config(
    *,
    provider: str = "Local vLLM",
    supports_reasoning: bool = False,
) -> ModelConfig:
    return ModelConfig(
        public_id="test-model",
        upstream_model="test-upstream",
        display_name="Test Model",
        provider=provider,
        enabled=True,
        supports_streaming=True,
        supports_reasoning=supports_reasoning,
        supports_tools=False,
        supports_vision=False,
        default_temperature=0.7,
        default_max_output_tokens=128,
        max_output_tokens=256,
    )


def chat_request(**updates):
    payload = {
        "model": "test-model",
        "messages": [
            ChatMessage(
                role="user",
                content="Explain model routing.",
            )
        ],
    }
    payload.update(updates)

    return ChatRequest(**payload)


class ModelGatewayTest(unittest.TestCase):
    def test_output_tokens_are_capped_by_model_limit(self):
        request = chat_request(max_output_tokens=1024)

        self.assertEqual(
            resolve_max_output_tokens(request, model_config()),
            256,
        )

    def test_local_model_uses_standard_openai_payload(self):
        payload = build_upstream_payload(
            request=chat_request(temperature=0.2),
            model_config=model_config(),
            stream=True,
        )

        self.assertEqual(payload["model"], "test-upstream")
        self.assertEqual(payload["temperature"], 0.2)
        self.assertTrue(payload["stream"])
        self.assertEqual(
            payload["stream_options"],
            {"include_usage": True},
        )

    def test_usage_accepts_openai_compatible_token_fields(self):
        usage = extract_usage(
            {
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 7,
                    "total_tokens": 18,
                }
            }
        )

        self.assertEqual(usage.input_tokens, 11)
        self.assertEqual(usage.output_tokens, 7)
        self.assertEqual(usage.total_tokens, 18)


if __name__ == "__main__":
    unittest.main()
