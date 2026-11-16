# Credits

## Where this started

This project began in August 2026 as a fork of
[EimanTahir027/Multi-Agent-Book-Writer](https://github.com/EimanTahir027/Multi-Agent-Book-Writer),
a neat demonstration of the idea: a small team of LLM "agents" — an architect, a
planner, a researcher, a writer and an editor — that hand a book down a chain, one
stage at a time, through a single shared Python dict. It was about 350 lines and
it made the point clearly enough to be worth building something on. Thanks to
Eiman Tahir for writing it and publishing it under the MIT licence.

## What is left of it

Honestly: less each month. The idea (one story passed along a fixed sequence of
specialised prompts), the module layout under `agents/`, and the shape of the
shared dict with its `get` / `set` / `reset` helpers are the parts that survived
the rewrite; the dict is now `shared/story.py`. Every module was rewritten from
the ground up — the pipeline went from 348 to roughly 25,000 lines across 72
modules — so treat this as a project with the same origin story rather than a
patched copy. The commit history says which is which: the eight upstream commits
are at its root, under Eiman's name, followed by everything since.

## What was added here

The parts that make it usable for a real book, rather than a demonstration:

- **Seed review** (`agents/seed_review.py`): scenes with quotes code verifies,
  arithmetic on whether the material fills the requested length, then a
  critique → answer → expand loop whose result is the run's master seed.
- **A deterministic layer under the model**: word counts, name grounding, quote
  verification, banned phrases, style/POV/tense lint, cast and county checks,
  and death/grounding checks on extracted story state. Nothing that arithmetic
  can settle is left to a prompt.
- **Story state and the reviewer**: per-chapter facts (who is where, who has met
  whom, deaths, injuries, secrets) with a continuity review that catches a dead
  character walking into chapter nine.
- **Resume that survives a crash** (`output/state/`, atomic writes, archive
  instead of delete), durable per-chapter files, and interim artifacts you can
  read while the book is being written.
- **Review-as-you-go**, where chapter N is edited before chapter N+1 is drafted.
- **EPUB export** (`make_epub.py`, no LLM), a **web GUI** (`web/`) with a browser
  question channel so the seed review works on a phone, and a Docker image.
- **Evaluation harnesses** (`tools/`): planted-error reviewer sets, extractor
  cases with known answers, fact-check verdict pairs, prose-style sweeps — so
  "this model is better" is a measurement rather than a feeling.
- **1,009 offline tests** that need no model, network or Docker.

## Licence

MIT, as it was before, and the copyright notice in [`LICENSE.txt`](LICENSE.txt)
still names Eiman Tahir: that notice must stay for the parts that are derived,
and removing it would be both wrong and unnecessary. The rest of the code is
Copyright (c) Stuart Harding.

If you are looking for the upstream project — the small, clear demonstration —
it is [github.com/EimanTahir027/Multi-Agent-Book-Writer](https://github.com/EimanTahir027/Multi-Agent-Book-Writer).
It is a good read, and the place to start if you want the idea without the
machinery.
