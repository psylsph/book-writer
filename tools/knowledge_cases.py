"""Chapters for tools/knowledge_eval.py: who acts on a secret they were never told.

The world is tools/reviewer_cases.py: in chapter 2 Marcus tells ELIZABETH
ALONE that a letter names her heir to the chapel. Chapter 5 (Friday) has Tom
and Dr Cole in it, and neither was told. Every case is chapter 5 with one
change. The reviewer's 14 cases are reused (only "knowledge" is an error there)
and these add three more errors and three tempting clean chapters, because one
error case per run is too thin a sample to compare two checks on.
"""

from tools.reviewer_cases import CASES as REVIEWER_CASES
from tools.reviewer_cases import CLOSE, FUNERAL, OPEN, chapter

TOM_TOLD = FUNERAL.replace(
    "Tom suggested the chapel, because Marcus had loved it. Elizabeth said "
    "the chapel was hers now, and she would not have the harbourmaster "
    "buried anywhere else.",
    "Tom suggested the chapel, because Marcus had loved it. Elizabeth hesitated, "
    "then told him what she had told no one: Marcus had given her a letter, "
    "and it named her heir to the chapel. \"Then it is yours to bury him in,\" "
    "Tom said slowly.")

# (id, is_error, draft): an error means a character acts on the secret untold
NEW_CASES = [
    # Elizabeth's own "the chapel was hers now" is removed: said aloud before
    # Anna, it would TELL her, and the case would not be an error.
    ("k-anna-land", True, chapter(OPEN, FUNERAL.replace(
        "Elizabeth said the chapel was hers now, and she would not have the "
        "harbourmaster buried anywhere else. Anna wrote it in her notebook:",
        "Elizabeth said she would not have the harbourmaster buried anywhere "
        "else. \"Since the land round the chapel is yours, Miss Hale, I will "
        "have the deeds drawn up in your name,\" Anna said, and wrote it in "
        "her notebook:"))),
    ("k-tom-quip", True, chapter(OPEN + " \"Heir to a drowned chapel,\" Tom "
                                        "muttered at the knot. \"Funny sort of luck.\"",
                                FUNERAL)),
    ("k-tom-will", True, chapter(OPEN, FUNERAL.replace(
        "Elizabeth said the chapel was hers now, and",
        "Elizabeth said nothing, and Tom added that a woman who had come into "
        "the chapel by her mother's letter could bury whom she liked there, and"))),
    ("told-in-scene", False, chapter(OPEN, TOM_TOLD)),
    ("asks-only", False, chapter(OPEN, FUNERAL.replace(
        "Elizabeth said the chapel was hers now, and",
        "Tom asked what Marcus had wanted with her at the chapel, and "
        "Elizabeth said it was a private matter, and"))),
    ("anna-no-secret", False, chapter(OPEN, FUNERAL.replace(
        "Tom suggested the chapel, because Marcus had loved it. Elizabeth said "
        "the chapel was hers now, and she would not have the harbourmaster "
        "buried anywhere else.",
        "Anna said the chapel was the natural place, being the nearest "
        "consecrated ground. Elizabeth agreed, and Tom nodded."), CLOSE)),
]


def cases():
    """[(id, is_knowledge_error, draft)]: the reviewer's cases, then the new."""
    base = [(cid, planted == "knowledge", draft)
            for cid, planted, draft in REVIEWER_CASES]
    return base + NEW_CASES
