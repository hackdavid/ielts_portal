"""OpenAI Agents SDK wrapper. Falls back to deterministic mocks without a key."""

import json
import time
from dataclasses import dataclass

from django.conf import settings
from pydantic import BaseModel

# Rough $/1M tokens for budget tracking (input, output); unknown models use default.
PRICES = {
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-4.1-mini": (0.4, 1.6),
    "gpt-4o": (2.5, 10.0),
    "gpt-4.1": (2.0, 8.0),
    "default": (1.0, 4.0),
}


@dataclass
class Result:
    output: BaseModel
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    raw: str = ""

    @property
    def cost(self):
        pin, pout = PRICES.get(self.model, PRICES["default"])
        return (self.tokens_in * pin + self.tokens_out * pout) / 1_000_000


def enabled():
    return bool(settings.CONTENT_LLM_API_KEY)


def _model(name):
    from agents import OpenAIChatCompletionsModel, set_tracing_disabled
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.CONTENT_LLM_API_KEY,
        base_url=settings.CONTENT_LLM_BASE_URL or None,
    )
    if settings.CONTENT_LLM_BASE_URL:
        set_tracing_disabled(True)
    return OpenAIChatCompletionsModel(model=name, openai_client=client)


def run(name, instructions, payload, output_type, model=None):
    """Run one agent turn with typed output. `payload` is JSON-serialisable."""
    from agents import Agent, AgentOutputSchema, ModelSettings, Runner

    model = model or settings.CONTENT_LLM_MODEL
    agent = Agent(
        name=name,
        instructions=instructions,
        model=_model(model),
        model_settings=ModelSettings(temperature=0.7 if name == "writer" else 0.2),
        output_type=AgentOutputSchema(output_type, strict_json_schema=False),
    )
    started = time.monotonic()
    message = payload if isinstance(payload, str) else json.dumps(payload, indent=1)
    result = Runner.run_sync(agent, message, max_turns=2)
    usage = result.context_wrapper.usage
    return Result(
        output=result.final_output,
        provider="openai-agents",
        model=model,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        latency_ms=int((time.monotonic() - started) * 1000),
    )
