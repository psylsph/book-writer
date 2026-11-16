#!/usr/bin/env python3
"""Compare ways of catching a character who acts on a secret nobody told them.

The reviewer misses this error type more than any other (about two runs in
three on a 27B model). agents/knowledge_check.py asks one narrow question per
recorded secret instead. This tool scores both on the same chapters
(tools/knowledge_cases.py: 20 versions of one chapter, 4 with the error) by one
measure: did it report a KNOWLEDGE issue?

  uv run python tools/knowledge_eval.py --runs 3 \\
      --target reviewer http://127.0.0.1:8080 my-model --mode reviewer=reviewer \\
      --target check    http://127.0.0.1:8080 my-model \\
      --target check-off http://127.0.0.1:8080 my-model --no-thinking check-off

Per-target options (repeatable, LABEL or LABEL=VALUE): --mode (check, the
default, or reviewer), --no-thinking, --reasoning-effort. For `check` they set
the `knowledge` agent (that is the agent the check runs as); for `reviewer`, the
`reviewer` agent. The config's own effort for that agent is ignored.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import knowledge_check, reviewer  # noqa: E402
from shared import llm_client  # noqa: E402
from shared.story import reset_story, set_story  # noqa: E402
from shared.story_state import merge_states  # noqa: E402
from tools.knowledge_cases import cases  # noqa: E402
from tools.reviewer_cases import (BIBLE, BRIEF, CHAPTERS, NUMBER,  # noqa: E402
                                  TITLE, chronology)

AGENT = {"check": "knowledge", "reviewer": "reviewer"}


def score(expected, reported):
    """'hit' / 'miss' for an error chapter, 'ok' / 'false_positive' otherwise."""
    if expected:
        return "hit" if reported else "miss"
    return "false_positive" if reported else "ok"


def summarize(runs, seconds, unreadable):
    errors = [r for r in runs if r["expected"]]
    clean = [r for r in runs if not r["expected"]]

    def rate(num, den):
        return num / den if den else 0.0

    return {
        "recall": rate(sum(r["outcome"] == "hit" for r in errors), len(errors)),
        "hits": sum(r["outcome"] == "hit" for r in errors),
        "errors": len(errors),
        "false_positive_rate": rate(
            sum(r["outcome"] == "false_positive" for r in clean), len(clean)),
        "false_positives": sum(r["outcome"] == "false_positive" for r in clean),
        "unreadable": unreadable,
        "sec_per_chapter": seconds / len(runs) if runs else 0.0,
        "problems": sorted({f"{r['id']}: {r['outcome'].upper()}" for r in runs
                            if r["outcome"] in ("miss", "false_positive")}),
    }


def configure(url, model, opts):
    cfg = llm_client.get_config()
    cfg["llm"].update(base_url=url, model=model, retries=0, endpoint_wait=0,
                      json_mode=opts.get("json_mode", False))
    cfg.setdefault("output", {})["interim"] = False
    agent = cfg.setdefault("agents", {}).setdefault(AGENT[opts["mode"]], {})
    for key in ("model", "reasoning_effort", "enable_thinking"):
        agent.pop(key, None)
    if opts.get("reasoning_effort"):
        agent["reasoning_effort"] = opts["reasoning_effort"]
    if opts.get("no_thinking"):
        agent["reasoning_effort"] = ""
        agent["enable_thinking"] = False
    reset_story()
    set_story("bible", BIBLE)
    set_story("chapters", CHAPTERS)
    set_story("research", {NUMBER: BRIEF})
    set_story("chronology", chronology())
    llm_client.reset_stats()


def report(mode, draft, unreadable):
    """True when the setup reported a knowledge issue on `draft`."""
    if mode == "reviewer":
        _, issues = reviewer.review_chapter(NUMBER, TITLE, draft)
    else:
        cumulative = merge_states(chronology(), upto=NUMBER)
        issues = knowledge_check.check_chapter(NUMBER, draft, cumulative,
                                               BIBLE, unreadable)
    return any(i["type"] == "knowledge" for i in issues)


def run_target(label, url, model, chapters, opts, runs=1, verbose=False):
    configure(url, model, opts)
    results, unreadable, started = [], [], time.time()
    for case_id, expected, draft in chapters:
        for _ in range(runs):
            try:
                outcome = score(expected, report(opts["mode"], draft, unreadable))
            except llm_client.EndpointUnavailable:
                raise
            except Exception:
                unreadable.append(case_id)
                continue
            results.append({"id": case_id, "expected": expected,
                            "outcome": outcome})
            if verbose:
                print(f"  [{label}] {case_id:16} {outcome}")
    return summarize(results, time.time() - started, len(unreadable))


COLUMNS = [("recall", "recall", "{:.2f}"), ("hits", "(hit)", "{}"),
           ("errors", "(of)", "{}"),
           ("false_positive_rate", "FALSE POS", "{:.2f}"),
           ("false_positives", "(count)", "{}"),
           ("unreadable", "unreadable", "{}"),
           ("sec_per_chapter", "s/chapter", "{:.1f}")]


def format_table(results):
    width = max(len(label) for label in list(results) + ["target"]) + 2
    head = "target".ljust(width) + "".join(h.rjust(12) for _, h, _ in COLUMNS)
    lines = [head, "-" * len(head)]
    for label, r in results.items():
        lines.append(label.ljust(width) + "".join(
            fmt.format(r[key]).rjust(12) for key, _, fmt in COLUMNS))
    lines += ["", "where it went wrong:"]
    for label, r in results.items():
        lines.append(f"  {label}")
        lines += [f"      {p}" for p in r["problems"]] or ["      nothing"]
    return "\n".join(lines)


def _label_values(items, cast=str):
    out = {}
    for item in items or []:
        label, _, value = item.partition("=")
        if not value:
            raise SystemExit(f"expected LABEL=VALUE, got '{item}'")
        out[label] = cast(value)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", nargs=3, action="append", required=True,
                        metavar=("LABEL", "URL", "MODEL"))
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--json-mode", action="store_true")
    parser.add_argument("--mode", action="append", default=[], metavar="LABEL=MODE",
                        help="check (default) or reviewer")
    parser.add_argument("--no-thinking", action="append", default=[], metavar="LABEL")
    parser.add_argument("--reasoning-effort", action="append", default=[],
                        metavar="LABEL=EFFORT")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--json", metavar="FILE")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    llm_client.load_config(args.config)
    modes = _label_values(args.mode)
    efforts = _label_values(args.reasoning_effort)
    known = {label for label, _, _ in args.target}
    for name, mapping in (("--mode", modes), ("--reasoning-effort", efforts)):
        for label in mapping:
            if label not in known:
                raise SystemExit(f"{name} names unknown target '{label}'")
    for mode in modes.values():
        if mode not in AGENT:
            raise SystemExit(f"--mode: choose from {', '.join(AGENT)}")

    results = {}
    for label, url, model in args.target:
        mode = modes.get(label, "check")
        print(f"== {label} ({mode}): {model} @ {url} ({len(cases())} chapters x "
              f"{args.runs})")
        opts = {"mode": mode, "no_thinking": label in args.no_thinking,
                "reasoning_effort": efforts.get(label),
                "json_mode": args.json_mode}
        try:
            results[label] = run_target(label, url, model, cases(), opts,
                                        args.runs, args.verbose)
        except Exception as e:
            print(f"   could not run: {e}")
    if not results:
        sys.exit("No target produced results.")
    print("\n" + format_table(results))
    print("\nrecall = chapters with the planted error where a knowledge issue "
          "was reported. FALSE POS = a chapter without it that got one.")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    main()
