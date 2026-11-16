"""Knowledge check (experimental, not yet in the pipeline): does a character
act on a secret nobody told them?

The reviewer has to spot this inside one broad review of eight error types, and
on a 27B model it caught it in about one run in three. The facts it needs are
already recorded: the extractor saves `secret_revealed` events (who learned
what, in which chapter). So code does the bookkeeping and the model gets one
narrow question per (secret, chapter):

    SECRET: the letter names her heir to the chapel
    LEARNED IT: Elizabeth Hale        NOT TOLD: Tom Baker, Anna Cole
    Does any NOT-TOLD character speak or act as if they know it, without being
    told in this chapter? -> {"answer": true/false, "who": ..., "quote": ...}

A "yes" counts only when its quote is really in the chapter and `who` is one of
the characters asked about (deterministic code checks the model). Only
characters who are NAMED in the chapter are asked about, so a chapter that
leaves the outsiders out costs no call.

check_chapter() is what a pipeline stage would call; tools/knowledge_eval.py
measures it against the reviewer.
"""

import re

from shared import prompts
from shared.llm_client import AbortRun, generate_with_wait
from shared.llm_utils import extract_json
from shared.story_state import canonical_name, strip_title
from shared.web_search import quote_in_text


def _variants(name, aliases):
    """The ways a chapter may name a character: the full name, the first name
    and the surname ('Dr Cole'), and the bible's declared nicknames."""
    words = strip_title(name).split()
    found = {name, strip_title(name)}
    if len(words) > 1:
        found.update(w for w in (words[0], words[-1]) if len(w) > 2)
    found.update(aliases.get(name, []))
    return sorted(v for v in found if v)


def named_in(draft, name, aliases=None):
    """True when the chapter names the character (whole word, case-sensitive
    so a dead 'Rose' does not match 'the sun rose')."""
    return any(re.search(rf"\b{re.escape(v)}\b", draft)
               for v in _variants(name, aliases or {}))


def outsiders(secret, draft, bible, dead=()):
    """Characters named in `draft` who, by the record, were never told
    `secret` (and are alive: the dead cannot act in the chapter)."""
    canon = [c["name"] for c in bible.get("characters", []) if c.get("name")]
    aliases = {c["name"]: c.get("aliases") or []
               for c in bible.get("characters", []) if c.get("name")}
    knowers = {canonical_name(w, canon, aliases) for w in secret["who"]}
    return [name for name in canon
            if name not in knowers and name not in dead
            and named_in(draft, name, aliases)]


def _prompt(secret, asked, record, number, draft):
    others = "; ".join(f"Ch{s['chapter']}: {' & '.join(s['who'])} learned "
                       f"'{s['detail']}'" for s in record if s is not secret)
    return (
        f"A secret was revealed in an earlier chapter.\n\n"
        f"SECRET (Chapter {secret['chapter']}): {secret['detail']}\n"
        f"LEARNED IT: {', '.join(secret['who'])}\n"
        f"NOT TOLD: {', '.join(asked)}\n"
        + (f"Other revelations on record: {others}\n" if others else "")
        + f"\nCHAPTER {number}:\n{draft}\n\n"
        "In this chapter, does any NOT-TOLD character speak, think or act as "
        "if they already know the secret's content, WITHOUT being told it "
        "inside this chapter? Being present when someone ELSE tells or "
        "mentions it in the chapter is fine, and so is a NOT-TOLD character "
        "who only asks about it or guesses. Reply with JSON: "
        '{"answer": true or false, "who": "the character", "quote": "the '
        'exact sentence copied from the chapter"}. If the answer is false, '
        'use "" for who and quote.')


def check_secret(secret, asked, record, number, draft):
    """One question. Returns {"who", "quote"} when a NOT-TOLD character acts
    on the secret (quote verified against the chapter), False when not, None
    when the reply could not be read. EndpointUnavailable/AbortRun propagate."""
    try:
        raw = generate_with_wait(_prompt(secret, asked, record, number, draft),
                                 system=prompts.KNOWLEDGE, agent="verifier",
                                 json_mode=True)
        data = extract_json(raw, expect="object")
    except AbortRun:
        raise
    except Exception:
        return None
    answer = data.get("answer")
    if not isinstance(answer, bool):
        return None
    if not answer:
        return False
    who = str(data.get("who", "")).strip()
    quote = str(data.get("quote", ""))
    if not quote_in_text(quote, draft):
        return False                      # invented evidence is not a finding
    canon = list(asked)
    if canonical_name(who, canon) not in canon:
        return False                      # named someone we did not ask about
    return {"who": canonical_name(who, canon), "quote": quote.strip()}


def check_chapter(number, draft, cumulative, bible, unreadable=None):
    """Knowledge issues for chapter `number`, as reviewer-style
    {type, description, fix} dicts. `cumulative` is merge_states(...,
    upto=number). A secret whose question cannot be read is skipped (and
    appended to `unreadable` when a list is passed, so an evaluation can count
    it)."""
    issues = []
    record = cumulative.get("secrets") or []
    for secret in record:
        asked = outsiders(secret, draft, bible, cumulative.get("dead") or {})
        if not asked:
            continue
        found = check_secret(secret, asked, record, number, draft)
        if found is None and unreadable is not None:
            unreadable.append(secret)
        if found:
            issues.append({
                "type": "knowledge",
                "description": f"{found['who']} acts on a secret they were "
                               f"never told (Ch{secret['chapter']}: "
                               f"{secret['detail']}): \"{found['quote']}\"",
                "fix": f"Remove {found['who']}'s knowledge of it, or have "
                       "someone tell them in the chapter first."})
    return issues
