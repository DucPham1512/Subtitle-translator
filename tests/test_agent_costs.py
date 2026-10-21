"""Spending per agent, and the script-review step in the run panel."""

from __future__ import annotations

import io

from subagent.kernel.models import CostRecord
from subagent.kernel.progress import Progress
from subagent.kernel.util import read_jsonl
from subagent.llm import build_messages
from subagent.pipeline import Pipeline, collect_metrics, episode_status
from tests.conftest import make_llm, register_episode, seed_memory
from tests.test_llm import Answer
from tests.test_pipeline import _handlers, calls, stubs  # noqa: F401 - pytest fixtures


def test_each_call_records_its_agent(project):
    config, paths = project
    cost = paths.work / "ep001" / "cost.jsonl"
    llm, _ = make_llm(config, paths, {"utility": lambda m: {"value": 1}}, cost_path=cost)
    llm.call("utility", build_messages("S", "", "a"), Answer, task="script_review")
    llm.call("utility", build_messages("S", "", "b"), Answer)
    llm.call("utility", build_messages("S", "", "a"), Answer, task="script_review")      # disk-cache hit
    assert [r.task for r in read_jsonl(cost, CostRecord)] == ["script_review", "utility", "script_review"]
    m = collect_metrics(paths.work / "ep001", "ep001", config.llm.prices)
    assert m["cost_by_task"]["script_review"]["calls"] == 2
    assert m["cost_by_task"]["script_review"]["disk_cache_hits"] == 1
    assert m["cost_by_task"]["script_review"]["cost"] > 0


def test_pipeline_reports_script_reviewer_spending(project, stubs):  # noqa: F811
    config, paths = project
    seed_memory(config, paths)
    register_episode(paths, 1)
    llm, _ = make_llm(config, paths, _handlers(), cost_path=paths.episode_dir("ep001") / "cost.jsonl")
    pipe = Pipeline(config, paths, progress=Progress("json", stream=io.StringIO()), llm=llm)
    pipe.run("ep001", mode="human")
    ep = pipe.registry.get("ep001")
    agents = episode_status(paths, ep, config.llm.prices)["cost_by_agent"]
    assert {"ocr_fix", "pinyin", "translate", "evaluate", "script_review"} <= set(agents)
    report = (paths.episode_dir("ep001") / "report.md").read_text(encoding="utf-8")
    assert "### Cost by agent" in report and "| Script reviewer |" in report
