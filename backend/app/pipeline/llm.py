import time
from typing import Protocol

from openai import OpenAI
from openai.types.responses import ResponseUsage
from pydantic import BaseModel, SecretStr

from app.pipeline.common import PaidCall

# USD per 1M tokens: input, cached input, cache write, output (standard processing).
PRICES: dict[str, tuple[float, float, float, float]] = {
    "gpt-6-sol": (2.00, 0.20, 2.50, 10.00),
    "gpt-6-luna": (0.10, 0.01, 0.125, 0.50),
    "gpt-6-astra": (10.00, 1.00, 12.50, 50.00),
}


class LlmError(Exception):
    """The model returned no output that matches the schema."""


class Llm(Protocol):
    def parse[T: BaseModel](
        self, *, model: str, instructions: str, prompt: str, schema: type[T], effort: str
    ) -> tuple[T, PaidCall]: ...


class OpenAILlm:
    """The OpenAI Responses API with Structured Outputs (a Pydantic schema)."""

    def __init__(self, api_key: SecretStr) -> None:
        self._client = OpenAI(api_key=api_key.get_secret_value(), max_retries=2)

    def parse[T: BaseModel](
        self, *, model: str, instructions: str, prompt: str, schema: type[T], effort: str
    ) -> tuple[T, PaidCall]:
        if model not in PRICES:
            raise ValueError(f"No price for {model}: add it to PRICES before using it")
        start = time.perf_counter()
        response = self._client.responses.parse(
            model=model,
            instructions=instructions,
            input=prompt,
            text_format=schema,
            reasoning={"effort": effort},
        )
        latency_ms = round((time.perf_counter() - start) * 1000)
        if response.output_parsed is None:
            raise LlmError(f"{model} returned no parsed output (status: {response.status})")
        usage = response.usage
        call = PaidCall(
            provider="openai",
            model=model,
            cost_usd=openai_cost(model, usage),
            latency_ms=latency_ms,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        return response.output_parsed, call


# Cached and cache-written tokens are part of input_tokens (Step 3 spike: 1,707 of 1,710).
def openai_cost(model: str, usage: ResponseUsage) -> float:
    price_in, price_cached, price_write, price_out = PRICES[model]
    cached = usage.input_tokens_details.cached_tokens
    written = usage.input_tokens_details.cache_write_tokens
    return (
        (usage.input_tokens - cached - written) * price_in
        + cached * price_cached
        + written * price_write
        + usage.output_tokens * price_out
    ) / 1_000_000
