from hamutay.providers.anthropic import AnthropicAdapter
from hamutay.providers.openai import OpenAIAdapter


def adapters() -> dict[str, object]:
    return {
        "anthropic": AnthropicAdapter(),
        "openai": OpenAIAdapter(),
    }
