"""agents/knowledge_check.py and tools/knowledge_eval.py (offline)."""

import json as jsonlib

import pytest

from agents import knowledge_check as kc
from shared.story_state import merge_states
from tools import knowledge_eval as ke
from tools.knowledge_cases import cases
from tools.reviewer_cases import BIBLE, NUMBER, chronology

CUM = merge_states(chronology(), upto=NUMBER)
SECRET = CUM["secrets"][0]
DRAFTS = {cid: draft for cid, _, draft in cases()}
QUIP = DRAFTS["k-tom-quip"]
QUOTE = '"Heir to a drowned chapel," Tom muttered at the knot.'


def test_the_cases_are_well_formed():
    all_cases = cases()
    assert len(all_cases) == 20 and len({c[0] for c in all_cases}) == 20
    assert {c[0] for c in all_cases if c[1]} == {
        "knowledge", "k-anna-land", "k-tom-quip", "k-tom-will"}
    assert QUOTE in QUIP


def test_outsiders_are_the_living_named_characters_not_told():
    # Elizabeth knows; Marcus is dead; Tom and Dr Cole are named and untold
    assert kc.outsiders(SECRET, QUIP, BIBLE, CUM["dead"]) == [
        "Tom Baker", "Anna Cole"]
    # a character the chapter never names is not asked about
    only_tom = "Tom coiled the rope. Elizabeth watched the tide."
    assert kc.outsiders(SECRET, only_tom, BIBLE, CUM["dead"]) == ["Tom Baker"]
    assert kc.outsiders(SECRET, "The marsh was still.", BIBLE, {}) == []


def test_a_title_surname_or_nickname_counts_as_naming_the_character():
    assert kc.named_in("Dr Cole came down the jetty.", "Anna Cole")
    assert kc.named_in("\"Morning, Liz,\" he said.", "Elizabeth Hale",
                       {"Elizabeth Hale": ["Liz"]})
    assert not kc.named_in("The sun rose over Marcusville.", "Marcus Reed")


def _reply(monkeypatch, **fields):
    monkeypatch.setattr(kc, "generate_with_wait",
                        lambda *a, **k: jsonlib.dumps(fields))


def check(draft=QUIP):
    return kc.check_secret(SECRET, ["Tom Baker", "Anna Cole"],
                           CUM["secrets"], NUMBER, draft)


def test_a_yes_with_a_real_quote_is_a_finding(monkeypatch):
    _reply(monkeypatch, answer=True, who="Tom", quote=QUOTE)
    assert check() == {"who": "Tom Baker", "quote": QUOTE}


@pytest.mark.parametrize("fields", [
    dict(answer=True, who="Tom", quote="Tom said something that is not there."),
    dict(answer=True, who="Marcus Reed", quote=QUOTE),     # not asked about
    dict(answer=True, who="Tom", quote="Tom"),              # too short to count
    dict(answer=False, who="", quote=""),
])
def test_invented_or_misdirected_evidence_is_not_a_finding(monkeypatch, fields):
    _reply(monkeypatch, **fields)
    assert check() is False


def test_unreadable_replies_are_none_not_a_pass(monkeypatch):
    monkeypatch.setattr(kc, "generate_with_wait", lambda *a, **k: "no json")
    assert check() is None
    _reply(monkeypatch, answer="yes", who="Tom", quote=QUOTE)   # not a bool
    assert check() is None


def test_abort_run_propagates(monkeypatch):
    def boom(*a, **k):
        raise kc.AbortRun("server down")
    monkeypatch.setattr(kc, "generate_with_wait", boom)
    with pytest.raises(kc.AbortRun):
        check()


def test_check_chapter_asks_once_per_secret_and_skips_empty_chapters(monkeypatch):
    calls = []

    def fake(prompt, **kw):
        calls.append(prompt)
        return jsonlib.dumps({"answer": True, "who": "Tom", "quote": QUOTE})

    monkeypatch.setattr(kc, "generate_with_wait", fake)
    issues = kc.check_chapter(NUMBER, QUIP, CUM, BIBLE)
    assert len(calls) == 1 and "NOT TOLD: Tom Baker, Anna Cole" in calls[0]
    assert issues[0]["type"] == "knowledge" and QUOTE in issues[0]["description"]
    calls.clear()
    assert kc.check_chapter(NUMBER, "The marsh was still.", CUM, BIBLE) == []
    assert calls == []


def test_check_chapter_counts_unreadable(monkeypatch):
    monkeypatch.setattr(kc, "generate_with_wait", lambda *a, **k: "garbage")
    lost = []
    assert kc.check_chapter(NUMBER, QUIP, CUM, BIBLE, lost) == []
    assert lost == [SECRET]


def test_score_and_summary():
    assert [ke.score(e, r) for e, r in ((True, True), (True, False),
                                        (False, True), (False, False))] == [
        "hit", "miss", "false_positive", "ok"]
    runs = [{"id": "a", "expected": True, "outcome": "hit"},
            {"id": "b", "expected": True, "outcome": "miss"},
            {"id": "c", "expected": False, "outcome": "false_positive"},
            {"id": "d", "expected": False, "outcome": "ok"}]
    s = ke.summarize(runs, 8.0, 1)
    assert (s["recall"], s["false_positive_rate"], s["unreadable"]) == (0.5, 0.5, 1)
    assert s["problems"] == ["b: MISS", "c: FALSE_POSITIVE"]
    assert s["sec_per_chapter"] == 2.0


def test_the_eval_runs_end_to_end_against_a_stub(tmp_path, monkeypatch):
    def post(url, json=None, **kwargs):
        prompt = json["messages"][-1]["content"]
        says_yes = "Heir to a drowned chapel" in prompt
        data = {"answer": says_yes, "who": "Tom" if says_yes else "",
                "quote": QUOTE if says_yes else ""}
        from tests.fake_llm import FakeResponse
        return FakeResponse(data={
            "choices": [{"message": {"content": jsonlib.dumps(data)},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

    monkeypatch.setattr(ke.llm_client.requests, "post", post)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f'output:\n  directory: "{tmp_path / "out"}"\n')
    r = ke.main(["--config", str(cfg), "--target", "stub", "http://h:1", "m"])
    assert r["stub"]["hits"] == 1 and r["stub"]["errors"] == 4
    assert r["stub"]["false_positives"] == 0 and r["stub"]["unreadable"] == 0
    with pytest.raises(SystemExit):
        ke.main(["--config", str(cfg), "--target", "a", "http://h:1", "m",
                 "--mode", "a=bogus"])
