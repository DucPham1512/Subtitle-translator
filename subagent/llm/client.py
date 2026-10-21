"""The only place that talks to LLM APIs (5.1).

Prompt layout rule: every prompt is [static system prompt] + [memory prefix] + [variable content].
`build_messages` enforces it: the static prompt and the memory prefix share the system message (in that
order, byte-identical across calls of one episode), the variable content goes in the user message.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from subagent.kernel import (
    BudgetExceeded,
    CostRecord,
    LLMCallError,
    LLMOutputError,
    append_jsonl,
    atomic_write_json,
    now_iso,
    read_jsonl,
    sha256_json,
)
from subagent.settings import Config, Paths

log = logging.getLogger(__name__)

Role = Literal["translator", "evaluator", "utility"]
Message = dict[str, str]


SERIES_NOTES = "## Series notes"


def load_prompt(paths: Paths, name: str) -> str:
    """The general prompt (prompts/<name>.md), followed by the active series' notes for it when it has some
    (data/series/<slug>/prompts/<name>.md): quirks of one show, such as how its font draws a character."""
    path = paths.prompts / f"{name}.md"
    if not path.is_file():
        raise LLMCallError(f"Prompt file missing: {path}", code="prompt_missing")
    text = path.read_text(encoding="utf-8")
    notes = paths.series_prompts / f"{name}.md"
    if paths.series and notes.is_file() and notes.read_text(encoding="utf-8").strip():
        text = text.rstrip() + f"\n\n{SERIES_NOTES}\n\n" + notes.read_text(encoding="utf-8").strip() + "\n"
    return text


def build_messages(static_prompt: str, memory_prefix: str, variable: str) -> list[Message]:
    system = static_prompt.rstrip() + "\n"
    if memory_prefix:
        system += "\n" + memory_prefix.rstrip() + "\n"
    return [{"role": "system", "content": system}, {"role": "user", "content": variable}]


def schema_instruction(schema: type[BaseModel]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, sort_keys=True)
    return (
        "\n\n## Output format\n"
        "Reply with a single JSON object, and nothing else, that validates against this JSON Schema:\n"
        f"```json\n{schema_json}\n```\n"
    )


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


def _strip_fence(text: str) -> str:
    m = _FENCE.match(text)
    return m.group(1) if m else text


def _usage_numbers(usage: Any) -> tuple[int, int, int]:
    if usage is None:
        return 0, 0, 0
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total = int(getattr(usage, "total_tokens", 0) or 0)
    # "Thinking" tokens are billed as output; some OpenAI-compatible providers leave them out of
    # completion_tokens but count them in total_tokens.
    completion = max(completion, total - prompt)
    hit = getattr(usage, "prompt_cache_hit_tokens", None)   # DeepSeek
    if hit is None:
        details = getattr(usage, "prompt_tokens_details", None)
        hit = getattr(details, "cached_tokens", None) if details is not None else None
    return prompt, int(hit or 0), completion


def compute_cost(price: Any, prompt: int, hit: int, completion: int) -> float:
    return ((prompt - hit) * price.input + hit * price.input_cached + completion * price.output) / 1e6


def record_cost(record: CostRecord, prices: dict) -> float | None:
    """Cost of a recorded call; recomputed from its tokens when it was made without a price.

    None: still no price for its model (cost unknown).
    """
    if record.cached_response:
        return 0.0
    if record.priced or (record.priced is None and record.cost > 0):
        return record.cost
    price = prices.get(record.model)
    if price is None:
        return None
    return compute_cost(price, record.prompt_tokens, record.cache_hit_tokens, record.completion_tokens)


def missing_prices(config: Config) -> list[str]:
    """Models used by a configured role that have no entry in llm.prices."""
    models = {p.model for p in config.llm.providers.values()}
    return sorted(m for m in models if m not in config.llm.prices)


_WARNED_UNPRICED: set[str] = set()


class LLMClient:
    def __init__(
        self,
        config: Config,
        paths: Paths,
        *,
        cost_path: Path | None = None,
        budget: float | None = None,
        use_cache: bool = True,
        clients: dict[str, Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        on_cost: Callable[[float], None] | None = None,
    ):
        self.config = config
        self.paths = paths
        self.cost_path = cost_path
        self.budget = config.budget.max_cost_per_episode if budget is None else budget
        self.use_cache = use_cache
        self._clients: dict[str, Any] = dict(clients or {})
        self._sleep = sleep
        self._on_cost = on_cost
        records = read_jsonl(cost_path, CostRecord) if cost_path else []
        self.total_cost = sum(record_cost(r, config.llm.prices) or 0.0 for r in records)

    # -- clients -----------------------------------------------------------------------------------

    def _client(self, role: Role) -> Any:
        if role not in self._clients:
            provider = self.config.llm.providers.get(role)
            if provider is None:
                raise LLMCallError(f"No LLM provider configured for role '{role}'", code="provider_missing")
            api_key = os.environ.get(provider.api_key_env)
            if not api_key:
                raise LLMCallError(
                    f"API key missing: set {provider.api_key_env} in .env or the environment",
                    code="api_key_missing",
                )
            from openai import OpenAI

            self._clients[role] = OpenAI(
                base_url=provider.base_url, api_key=api_key, timeout=self.config.llm.timeout_s, max_retries=0
            )
        return self._clients[role]

    def model_for(self, role: Role) -> str:
        return self.config.llm.providers[role].model

    # -- cache --------------------------------------------------------------------------------------

    def _cache_path(self, key: str) -> Path:
        return self.paths.llm_cache / key[:2] / f"{key}.json"

    def _cache_get(self, key: str) -> str | None:
        if not self.use_cache:
            return None
        path = self._cache_path(key)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))["content"]
        except (OSError, ValueError, KeyError):
            return None

    def _cache_put(self, key: str, content: str) -> None:
        if self.use_cache:
            atomic_write_json(self._cache_path(key), {"content": content})

    # -- cost ---------------------------------------------------------------------------------------

    def _record(self, role: Role, model: str, usage: Any, cached_response: bool = False, task: str = "") -> None:
        prompt, hit, completion = _usage_numbers(usage)
        price = self.config.llm.prices.get(model)
        cost = 0.0
        if price is not None:
            cost = compute_cost(price, prompt, hit, completion)
        elif not cached_response and model not in _WARNED_UNPRICED:
            _WARNED_UNPRICED.add(model)
            log.warning("No price configured for model %s: its cost is unknown and does not count toward the "
                        "budget until you add it under llm.prices", model)
        self.total_cost += cost
        record = CostRecord(
            ts=now_iso(), role=role, model=model, prompt_tokens=prompt, cache_hit_tokens=hit,
            completion_tokens=completion, cost=cost, cached_response=cached_response,
            priced=price is not None or cached_response, task=task or role,
        )
        if self.cost_path:
            append_jsonl(self.cost_path, record)
        if self._on_cost:
            self._on_cost(self.total_cost)

    def _check_budget(self) -> None:
        if self.budget is not None and self.total_cost > self.budget:
            raise BudgetExceeded(
                f"LLM budget exceeded: spent ${self.total_cost:.4f} of ${self.budget:.2f} for this episode"
            )

    # -- calls --------------------------------------------------------------------------------------

    def _complete(self, role: Role, messages: list[Message], json_mode: bool, task: str = "") -> tuple[str, Any]:
        client = self._client(role)
        model = self.model_for(role)
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": self.config.llm.temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        attempt = 0
        while True:
            self._check_budget()
            try:
                resp = client.chat.completions.create(**kwargs)
            except Exception as exc:  # noqa: BLE001 - classified below
                if _daily_quota(exc):              # waiting minutes cannot help; say so at once
                    raise LLMCallError(f"LLM call failed ({role}, {model}): the provider's daily request quota "
                                       "is used up; try again after it resets or use another model") from exc
                if not _retryable(exc) or attempt >= self.config.llm.max_retries:
                    raise LLMCallError(f"LLM call failed ({role}, {model}): {_describe(exc)}") from exc
                hint = _server_delay(exc)          # "retry in 37s": waiting less only burns the retries
                delay = min(self.config.llm.max_retry_wait_s, max(2.0**attempt, hint + 1 if hint else 0.0))
                log.warning("LLM %s call failed (%s); retrying in %.0fs", role, _describe(exc), delay)
                self._sleep(delay)
                attempt += 1
                continue
            choice = resp.choices[0]
            content = choice.message.content or ""
            self._record(role, model, getattr(resp, "usage", None), task=task)
            if getattr(choice, "finish_reason", None) == "length":
                content = content + "\n<<truncated: output hit the token limit>>"
            return content, resp

    def call(self, role: Role, messages: list[Message], schema: type[BaseModel] | None = None, *,
             task: str = "") -> BaseModel | str:
        """`task` names the agent making the call, for cost tracking per agent (defaults to the role)."""
        model = self.model_for(role)
        msgs = [dict(m) for m in messages]
        if schema is not None:
            msgs[0]["content"] = msgs[0]["content"] + schema_instruction(schema)
        key = sha256_json([model, msgs, schema.__name__ if schema else None])

        cached = self._cache_get(key)
        if cached is not None:
            try:
                result = schema.model_validate_json(_strip_fence(cached)) if schema else cached
                self._record(role, model, None, cached_response=True, task=task)
                return result
            except ValidationError:
                pass  # stale cache entry for a changed schema; call again

        content, _ = self._complete(role, msgs, json_mode=schema is not None, task=task)
        if schema is None:
            self._cache_put(key, content)
            return content

        try:
            result = schema.model_validate_json(_strip_fence(content))
        except ValidationError as first_error:
            repair = msgs + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": (
                    "Your reply failed validation:\n"
                    f"{_short_error(first_error)}\n"
                    "Reply again with the complete, corrected JSON object only."
                )},
            ]
            content, _ = self._complete(role, repair, json_mode=True, task=task)
            try:
                result = schema.model_validate_json(_strip_fence(content))
            except ValidationError as second_error:
                raise LLMOutputError(
                    f"{role} output failed validation twice ({schema.__name__}): {_short_error(second_error)}"
                ) from second_error
        self._cache_put(key, result.model_dump_json())
        return result

    def test_connection(self, role: Role) -> str:
        """Send one minimal request; returns the model's reply. Never cached, never budgeted.

        No tight token cap: "thinking" models spend tokens reasoning first and would return an empty reply.
        """
        client = self._client(role)
        resp = client.chat.completions.create(
            model=self.model_for(role), messages=[{"role": "user", "content": "Reply with: ok"}], max_tokens=512,
        )
        return (resp.choices[0].message.content or "").strip()


def _retryable(exc: Exception) -> bool:
    try:
        import openai
    except ImportError:  # pragma: no cover
        return False
    if isinstance(exc, openai.APIConnectionError | openai.APITimeoutError | openai.RateLimitError
                  | openai.InternalServerError):
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def _server_delay(exc: Exception) -> float | None:
    """The wait the provider asks for: a Retry-After header, or Gemini's "retry in 37.3s" / retryDelay."""
    response = getattr(exc, "response", None)
    header = getattr(response, "headers", {}).get("retry-after") if response is not None else None
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    m = re.search(r"retry in ([\d.]+)\s*s|retryDelay['\"]?:\s*['\"]([\d.]+)s", str(exc))
    return float(m.group(1) or m.group(2)) if m else None


def _daily_quota(exc: Exception) -> bool:
    """A per-day quota is exhausted (Gemini free tier: quotaId ...PerDay...); retrying the same day is useless."""
    return getattr(exc, "status_code", None) == 429 and "PerDay" in str(exc)


def _describe(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    return f"{name} {status}" if status else f"{name}: {exc}"


def _short_error(err: ValidationError, limit: int = 1500) -> str:
    text = str(err)
    return text if len(text) <= limit else text[:limit] + " ..."
