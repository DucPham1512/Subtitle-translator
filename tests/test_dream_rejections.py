"""Dreaming never re-proposes what the reviewer rejected."""

from __future__ import annotations

from subagent.kernel.models import ReviewedLine
from subagent.kernel.util import write_jsonl
from subagent.memory import dreaming
from tests.conftest import make_llm, register_episode, seed_memory


def _setup(project):
    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    write_jsonl(paths.episode_dir(ep.id) / "approved.jsonl", [
        ReviewedLine(event_id="ep001:0000", start_ms=0, end_ms=1, speaker="lin_yuan", listener="shi_zun",
                     zh="弟子想下山", pinyin="", vi="Đồ nhi muốn xuống núi.", approved=True)])
    return config, paths


def _response(since: str):
    return {
        "glossary": [{"zh": "下山", "vi": "xuống núi", "reason": "recurring", "evidence": ["ep001:0000"]}],
        "pronoun_pairs": [{"speaker_id": "lin_yuan", "listener_id": "shi_zun", "self_term": "con",
                           "address_term": "sư phụ", "since_episode": since, "reason": "usage changed"}],
        "style_rules": [{"rule": "Bỏ tên gọi ở đầu câu.", "example": "林, 走 → Đi"}],
    }


def test_rejected_proposals_are_not_proposed_again(project):
    config, paths = _setup(project)
    prompts = []

    def utility(messages):
        prompts.append(messages[1]["content"])
        return _response(since=f"ep00{len(prompts)}")      # incidental details differ between runs

    llm, _ = make_llm(config, paths, {"utility": utility})
    out = dreaming.dream(config, paths, llm)
    by_kind = {i.proposal.kind: i for i in out.items}
    assert set(by_kind) == {"glossary", "pronoun_pair", "style_rule"}
    dreaming.apply_dream(config, paths, {by_kind["glossary"].id})          # accept one, reject two

    remembered = dreaming.load_rejections(paths)
    assert len(remembered) == 2
    out2 = dreaming.dream(config, paths, llm)
    assert out2.items == [] and out2.inputs["previously_rejected"] == 2    # glossary now matches memory
    assert "pronouns lin_yuan → shi_zun: con / sư phụ" in prompts[-1]      # the model is told what was rejected
    assert "Bỏ tên gọi ở đầu câu." in prompts[-1]

    assert dreaming.forget_rejections(config, paths) == 2                 # changed your mind
    out3 = dreaming.dream(config, paths, llm)
    assert {i.proposal.kind for i in out3.items} == {"pronoun_pair", "style_rule"}


def test_auto_apply_does_not_count_as_rejection(project):
    config, paths = _setup(project)
    llm, _ = make_llm(config, paths, {"utility": lambda m: _response("ep001")})
    dreaming.dream(config, paths, llm)
    dreaming.apply_dream(config, paths, auto=True)        # skips locked ones by rule, nobody rejected them
    assert dreaming.load_rejections(paths) == []


def test_a_different_suggestion_for_the_same_term_still_comes_through(project):
    from subagent.kernel.models import MemoryProposal

    def gloss(vi: str) -> MemoryProposal:
        return MemoryProposal(kind="glossary", source="dreaming", payload={"zh": "下山", "vi": vi})

    assert dreaming.signature(gloss("xuống núi")) == dreaming.signature(gloss("Xuống Núi "))
    assert dreaming.signature(gloss("xuống núi")) != dreaming.signature(gloss("hạ sơn"))


def test_existing_rules_are_not_reproposed_and_terms_go_to_the_glossary(project):
    from subagent.kernel.models import MemoryProposal
    from subagent.memory.manager import MemoryManager

    config, paths = _setup(project)
    m = MemoryManager(paths, config)
    m.apply([MemoryProposal(kind="style_rule", source="human", payload={"rule": "Bỏ tên gọi ở đầu câu."})])
    response = {
        "glossary": [],
        "pronoun_pairs": [],
        "style_rules": [
            {"rule": "bỏ tên gọi ở đầu câu", "action": "add"},           # already there (case, final dot)
            {"rule": "Bỏ tên gọi ở đầu câu.", "action": "use"},           # just a usage bump: not a decision
            {"rule": "Không có quy tắc này.", "action": "remove"},       # nothing to remove
            {"rule": "Dịch 筑基 thành 'Trúc Cơ'.", "action": "add"},      # same as the glossary: nothing to do
            {"rule": "Dịch 筑基 thành 'Xây Nền'.", "action": "add"},      # a term: glossary proposal on a locked entry
            {"rule": "Dịch 下山 thành “xuống núi”", "action": "add"},      # new term
            {"rule": "Câu hỏi giữ dấu chấm hỏi.", "action": "add"},       # a real style rule
        ],
    }
    llm, _ = make_llm(config, paths, {"utility": lambda msgs: response})
    out = dreaming.dream(config, paths, llm)
    got = {(i.proposal.kind, i.key): i for i in out.items}
    assert set(got) == {("glossary", "筑基"), ("glossary", "下山"), ("style_rule", "Câu hỏi giữ dấu chấm hỏi.")}
    assert got[("glossary", "筑基")].proposal.payload == {"zh": "筑基", "vi": "Xây Nền"}
    assert got[("glossary", "筑基")].touches_locked and got[("glossary", "筑基")].preselected == "reject"
    assert got[("glossary", "下山")].proposal.payload["vi"] == "xuống núi"
