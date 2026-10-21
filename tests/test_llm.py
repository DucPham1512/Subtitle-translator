from __future__ import annotations

import pytest
from pydantic import BaseModel

from subagent.kernel.errors import BudgetExceeded, ConfigError, LLMCallError, LLMOutputError
from subagent.kernel.models import CostRecord
from subagent.kernel.util import read_jsonl
from subagent.llm.client import build_messages
from subagent.settings.config import Band, update_config_values
from tests.conftest import make_llm


class Answer(BaseModel):
    value: int


def test_band_pixels_are_even_and_inside_frame():
    x, y, w, h = Band(top=0.8, bottom=0.97, left=0.05, right=0.95).pixels(1921, 1081)
    assert all(v % 2 == 0 for v in (x, y, w, h))
    assert x + w <= 1921 and y + h <= 1081


def test_config_update_validates(project):
    config, paths = project
    cfg = update_config_values(paths.root, {"video.sample_fps": 5})
    assert cfg.video.sample_fps == 5
    with pytest.raises(ConfigError):
        update_config_values(paths.root, {"review.mode": "sometimes"})


def test_messages_keep_static_then_memory_then_variable():
    msgs = build_messages("STATIC", "MEMORY", "VARIABLE")
    assert msgs[0]["content"].index("STATIC") < msgs[0]["content"].index("MEMORY")
    assert msgs[1] == {"role": "user", "content": "VARIABLE"}


def test_schema_call_is_cached_and_costed(project):
    config, paths = project
    cost = paths.work / "ep001" / "cost.jsonl"
    llm, clients = make_llm(config, paths, {"utility": lambda m: {"value": 7}}, cost_path=cost)
    msgs = build_messages("S", "M", "V")
    assert llm.call("utility", msgs, Answer).value == 7
    assert llm.call("utility", msgs, Answer).value == 7
    assert len(clients["utility"].calls) == 1           # second call served from disk cache
    records = read_jsonl(cost, CostRecord)
    assert [r.cached_response for r in records] == [False, True]
    # 400 uncached input, 600 cached, 200 output at the configured prices
    assert records[0].cost == pytest.approx((400 * 0.27 + 600 * 0.07 + 200 * 1.1) / 1e6)
    assert clients["utility"].calls[0]["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in clients["utility"].calls[0]["messages"][0]["content"]


def test_no_cache_flag_calls_again(project):
    config, paths = project
    llm, clients = make_llm(config, paths, {"utility": lambda m: {"value": 1}})
    llm.use_cache = False
    msgs = build_messages("S", "", "V")
    llm.call("utility", msgs, Answer)
    llm.call("utility", msgs, Answer)
    assert len(clients["utility"].calls) == 2


def test_validation_retry_then_error(project):
    config, paths = project
    replies = iter(['{"value": "x"}', '{"value": 3}'])
    llm, clients = make_llm(config, paths, {"utility": lambda m: next(replies)})
    assert llm.call("utility", build_messages("S", "", "retry"), Answer).value == 3
    repair = clients["utility"].calls[1]["messages"]
    assert repair[-1]["role"] == "user" and "failed validation" in repair[-1]["content"]

    llm2, _ = make_llm(config, paths, {"utility": lambda m: '{"nope": 1}'})
    with pytest.raises(LLMOutputError):
        llm2.call("utility", build_messages("S", "", "always bad"), Answer)


def test_fenced_json_is_accepted(project):
    config, paths = project
    llm, _ = make_llm(config, paths, {"utility": lambda m: '```json\n{"value": 5}\n```'})
    assert llm.call("utility", build_messages("S", "", "fenced"), Answer).value == 5


def test_budget_stops_before_next_call(project):
    config, paths = project
    llm, clients = make_llm(config, paths, {"utility": lambda m: {"value": 1}}, budget=0.0)
    llm.call("utility", build_messages("S", "", "a"), Answer)     # total 0 → allowed, then over budget
    with pytest.raises(BudgetExceeded):
        llm.call("utility", build_messages("S", "", "b"), Answer)
    assert len(clients["utility"].calls) == 1


def test_network_errors_are_retried(project):
    import openai

    config, paths = project
    attempts = {"n": 0}

    def flaky(messages):
        attempts["n"] += 1
        if attempts["n"] < 3:
            # the transport library differs across SDK versions; only the exception type matters here
            return openai.APIConnectionError.__new__(openai.APIConnectionError)
        return {"value": 2}

    llm, _ = make_llm(config, paths, {"utility": flaky})
    assert llm.call("utility", build_messages("S", "", "flaky"), Answer).value == 2
    assert attempts["n"] == 3


def test_missing_api_key_is_reported_without_the_key(project, monkeypatch):
    from subagent.llm.client import LLMClient

    config, paths = project
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    with pytest.raises(LLMCallError) as err:
        LLMClient(config, paths).call("utility", build_messages("S", "", "x"))
    assert "DEEPSEEK_API_KEY" in str(err.value)


def test_unpriced_calls_are_marked_and_repriced_later(project):
    from types import SimpleNamespace

    from subagent.llm.client import LLMClient, missing_prices, record_cost
    from subagent.pipeline import collect_metrics
    from subagent.settings.config import PriceConfig

    config, paths = project
    config.llm.prices = {}
    assert missing_prices(config) == sorted({p.model for p in config.llm.providers.values()})
    work = paths.work / "ep001"
    cost = work / "cost.jsonl"
    llm, _ = make_llm(config, paths, {"utility": lambda m: {"value": 1}}, cost_path=cost)
    llm.call("utility", build_messages("S", "", "unpriced"), Answer)
    rec = read_jsonl(cost, CostRecord)[0]
    assert rec.priced is False and rec.cost == 0.0
    assert record_cost(rec, {}) is None                                   # unknown, not $0
    m = collect_metrics(work, "ep001", {})
    assert m["unpriced_models"] == ["deepseek-chat"] and m["cost_total"] == 0.0

    prices = {"deepseek-chat": PriceConfig(input=0.27, input_cached=0.07, output=1.1)}
    expected = (400 * 0.27 + 600 * 0.07 + 200 * 1.1) / 1e6
    assert record_cost(rec, prices) == pytest.approx(expected)            # priced from its tokens
    m = collect_metrics(work, "ep001", prices)
    assert m["unpriced_models"] == [] and m["cost_total"] == pytest.approx(expected)
    config.llm.prices = prices
    assert LLMClient(config, paths, cost_path=cost).total_cost == pytest.approx(expected)   # budget catches up

    legacy = rec.model_copy(update={"priced": None})                     # written before the field existed
    assert record_cost(legacy, prices) == pytest.approx(expected)
    assert record_cost(legacy.model_copy(update={"cost": 0.5}), {}) == 0.5

    from subagent.llm.client import _usage_numbers
    thinking = SimpleNamespace(prompt_tokens=100, completion_tokens=10, total_tokens=410)
    assert _usage_numbers(thinking) == (100, 0, 310)                      # hidden thinking tokens billed


def test_report_and_status_flag_missing_prices(project):
    from subagent.pipeline import episode_status
    from tests.conftest import register_episode

    config, paths = project
    ep = register_episode(paths, 1)
    config.llm.prices = {}
    llm, _ = make_llm(config, paths, {"utility": lambda m: {"value": 1}},
                      cost_path=paths.episode_dir(ep.id) / "cost.jsonl")
    llm.call("utility", build_messages("S", "", "status"), Answer)
    st = episode_status(paths, ep, config.llm.prices)
    assert not st["cost_complete"] and st["unpriced_models"] == ["deepseek-chat"]


def test_retry_waits_as_long_as_the_provider_asks():
    from types import SimpleNamespace

    from subagent.llm.client import _server_delay

    gemini = Exception("Error code: 429 - Quota exceeded ...\nPlease retry in 37.322318889s.")
    assert _server_delay(gemini) == pytest.approx(37.322318889)
    assert _server_delay(Exception("{'retryDelay': '12s'}")) == 12
    header = Exception("429")
    header.response = SimpleNamespace(headers={"retry-after": "5"})  # type: ignore[attr-defined]
    assert _server_delay(header) == 5
    assert _server_delay(Exception("connection reset")) is None


def test_daily_quota_is_not_retried():
    from subagent.llm.client import _daily_quota

    exc = Exception("429 ... 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier' ... retry in 45s")
    exc.status_code = 429  # type: ignore[attr-defined]
    assert _daily_quota(exc)
    per_minute = Exception("429 ... 'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier'")
    per_minute.status_code = 429  # type: ignore[attr-defined]
    assert not _daily_quota(per_minute)
