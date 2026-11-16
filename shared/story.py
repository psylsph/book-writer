"""The run's story record: one dict every stage reads and writes.

`STORY` holds the seed, the bible, the outline, per-chapter briefs, drafts,
summaries, story facts and the edited chapters. Agents import it directly
(`from shared.story import STORY`) and mutate it in place, so nothing has to be
threaded through call signatures; `set_story()` is the key/value setter for the
places that prefer a function.

`reset_story()` empties and refills that same dict instead of rebinding the
name: a module that did `from shared.story import STORY` would otherwise keep
pointing at the dict of a previous run. Chapter-keyed entries use `int` keys;
`shared/resume.py` restores them after a JSON round-trip turns them into
strings.
"""

DEFAULTS = {
    "seed": "",        # raw seed prompt text (characters, world, outline, ...)
    "title": "",       # book title (set by the architect from the bible)
    "bible": {},       # structured story bible built by the architect agent
    "chapters": [],    # [{"number": int, "title": str, "summary": str}]
    "research": {},    # chapter number -> lore brief
    "drafts": {},      # chapter number -> draft text
    "summaries": {},   # chapter number -> rolling plot summary
    "chronology": {},  # chapter number -> structured story state
    "final": {},       # chapter number -> edited body (no heading)
    "unreviewed": set(),  # chapters finished without a readable review
    "unrefreshed": set(), # edited chapters whose story state still comes from
                          # the draft (review as you go; see main.py)
    "chapter_notes": {},  # chapter number -> {drafted_at, edited_at, note}
    "output_path": "", # where the final book was actually written
}

STORY = {}


def reset_story():
    """Empty and refill STORY in place, so every importer sees the new run."""
    STORY.clear()
    for key, value in DEFAULTS.items():
        STORY[key] = value.copy() if isinstance(value, (dict, list, set)) else value


def set_story(key, value):
    """Set one entry of the run's story record."""
    STORY[key] = value


def get_story(key=None):
    """One entry of the story record, or the whole dict when no key is given."""
    if key:
        return STORY.get(key)
    return STORY


reset_story()  # fresh copies: never hand out DEFAULTS' mutable values
