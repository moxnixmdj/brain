"""A lesson that was kept must stay usable, however many other lessons the store holds.

History (sandbox measurement, 2026-11-11). The owner asked why the machine cannot be given many
coding experiences, once each, and then have them for good. The store was given them: the last 600
single-file commits of a public project (psf/requests), taught one at a time through
`VerifiedSkillStore.crystallize_code_fix` with the maintainers' own resulting file as the answer,
each replayed straight afterwards. 191 were kept as lessons. Replay was 128 of 128 for the first
128 lessons and 0 of 63 for every lesson after them.

The cause was one clause. `_load_rules` read

    ORDER BY verified_hits DESC, created_ts DESC LIMIT 128

so recall only ever saw 128 lessons per language, chosen before any of them was matched against
the source in hand:

* once 128 lessons had each been reused, a new lesson (never reused yet) ranked below all of them
  and was never read. It could therefore never be reused, so it could never rise. It was stored,
  reported `crystallized: True`, and dead.
* with no reuse at all the cut fell on the other end: the oldest lessons dropped out of sight as
  newer ones arrived.

Nothing reported either case. "Learned permanently" was true for 128 lessons and false after.

These tests pin the behaviour, not the clause: a lesson the store kept is offered to recall and
can be applied, wherever it ranks and however many others exist. They use more than twice as many
lessons as the old cut, so nudging the number up instead of removing it fails as well.

What this file does not claim. It says nothing about whether a lesson helps on a problem it was
not taught on. The same measurement found that it did not: of the 549 real code changes in that
history, none could be produced from the earlier lessons before it was shown. This file only says
that a kept lesson is not silently lost. (The script that made the measurement is in the pull
request that added this file.)
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

# More than twice the old cut of 128.
MANY = 300

# The lesson under test: a boundary that should have been inclusive.
LATE_BEFORE = (
    "def count_under(prices, limit):\n"
    "    count = 0\n"
    "    for p in prices:\n"
    "        if p < limit:\n"
    "            count += 1\n"
    "    return count\n"
)
LATE_AFTER = LATE_BEFORE.replace("if p < limit:", "if p <= limit:")

# The same mistake somewhere else: other names, other layout around it.
ELSEWHERE_BEFORE = (
    "def tally_small(weights, cap):\n"
    "    seen = 0\n"
    "    for w in weights:\n"
    "        if w < cap:\n"
    "            seen += 1\n"
    "    return seen\n"
)
ELSEWHERE_AFTER = ELSEWHERE_BEFORE.replace("if w < cap:", "if w <= cap:")

# A third, unrelated lesson; teaching it is only a change to the store.
_DRAIN_BEFORE = "def drain(n):\n    while n > 0:\n        n -= 1\n    return n\n"
_DRAIN_AFTER = _DRAIN_BEFORE.replace("while n > 0:", "while n >= 0:")


def _store(tmp_path: pathlib.Path) -> cry.VerifiedSkillStore:
    # seed=False: the count of lessons is the subject, so the store must start empty.
    return cry.VerifiedSkillStore(db_path=tmp_path / "skills.sqlite", seed=False)


def _other_lesson(k: int) -> tuple[str, str]:
    """Lesson number k of a family that has nothing to do with the lesson under test.

    Each one replaces an increment by a different constant, so each is a different rule; none of
    them matches a comparison, so none of them can stand in for the boundary lesson.
    """
    return ("def step(x):\n    return x + 1\n", f"def step(x):\n    return x + {1000 + k}\n")


def _teach(store: cry.VerifiedSkillStore, before: str, after: str) -> str:
    taught = store.crystallize_code_fix(before_snippet=before, after_snippet=after, language="python")
    assert taught.get("crystallized") is True, taught
    return str(taught["skill_id"])


def _reuse_other_lesson(store: cry.VerifiedSkillStore, k: int) -> None:
    """Apply lesson k once, on a renamed copy of its own shape, so that it counts as reused."""
    want = f"def advance(y):\n    return y + {1000 + k}\n"
    hit = store.recall_and_apply_verified(
        source_text="def advance(y):\n    return y + 1\n",
        language="python",
        verifier=lambda candidate: candidate == want,
    )
    assert hit is not None and hit["patched_source"] == want


def _apply_boundary_lesson(store: cry.VerifiedSkillStore) -> dict | None:
    return store.recall_and_apply_verified(
        source_text=ELSEWHERE_BEFORE,
        language="python",
        verifier=lambda candidate: candidate == ELSEWHERE_AFTER,
    )


def _rows_kept(store: cry.VerifiedSkillStore) -> int:
    conn = sqlite3.connect(store.db_path)
    try:
        return int(conn.execute(
            "SELECT count(*) FROM crystallized_skills WHERE domain='swe_code_repair' AND language='python'"
        ).fetchone()[0])
    finally:
        conn.close()


def test_a_lesson_taught_after_many_reused_lessons_can_still_be_applied(tmp_path):
    """The lock-out. Everything before it has been reused; the new lesson has not, yet."""
    store = _store(tmp_path)
    for k in range(MANY):
        _teach(store, *_other_lesson(k))
        _reuse_other_lesson(store, k)

    late_id = _teach(store, LATE_BEFORE, LATE_AFTER)

    hit = _apply_boundary_lesson(store)
    assert hit is not None, "a lesson the store kept was never offered to recall"
    assert hit["skill_id"] == late_id
    assert hit["patched_source"] == ELSEWHERE_AFTER


def test_the_first_lesson_can_still_be_applied_after_many_newer_ones(tmp_path):
    """The other end. Nothing has been reused; the oldest lesson must not fall out of sight."""
    store = _store(tmp_path)
    first_id = _teach(store, LATE_BEFORE, LATE_AFTER)
    for k in range(MANY):
        _teach(store, *_other_lesson(k))

    hit = _apply_boundary_lesson(store)
    assert hit is not None, "the oldest lesson was pushed out by newer ones"
    assert hit["skill_id"] == first_id
    assert hit["patched_source"] == ELSEWHERE_AFTER


def test_recall_is_offered_every_lesson_the_store_kept(tmp_path):
    store = _store(tmp_path)
    kept = {_teach(store, *_other_lesson(k)) for k in range(MANY)}
    kept.add(_teach(store, LATE_BEFORE, LATE_AFTER))

    offered = [str(rule["skill_id"]) for rule in store.lookup_rules("python")]

    assert len(kept) == MANY + 1, "the lessons taught here are meant to be distinct"
    assert _rows_kept(store) == MANY + 1
    assert len(offered) == len(set(offered)), "a lesson was offered twice"
    assert set(offered) == kept


def test_a_lesson_that_has_worked_before_is_still_tried_first(tmp_path):
    """Reading every lesson must not change which one is preferred when several apply.

    Two lessons rewrite the same shape differently. A verifier that accepts nothing sees every
    proposal in the order recall makes them; the lesson that has been reused more often comes
    first. (Recall reads the lessons again when the store changes, so each half teaches one
    unrelated lesson before it looks.)
    """
    store = _store(tmp_path)
    _teach(store, *_other_lesson(7))
    _teach(store, *_other_lesson(9))
    _reuse_other_lesson(store, 7)
    _teach(store, LATE_BEFORE, LATE_AFTER)

    asked: list[str] = []

    def refuse_and_remember(candidate: str) -> bool:
        asked.append(candidate)
        return False

    def proposals() -> list[str]:
        asked.clear()
        hit = store.recall_and_apply_verified(
            source_text="def advance(y):\n    return y + 1\n",
            language="python",
            verifier=refuse_and_remember,
        )
        assert hit is None
        return list(asked)

    assert proposals() == ["def advance(y):\n    return y + 1007\n", "def advance(y):\n    return y + 1009\n"]

    # The preference follows the evidence, not the order of teaching: make the other one the
    # better established lesson and it moves to the front.
    _reuse_other_lesson(store, 9)
    _reuse_other_lesson(store, 9)
    _teach(store, _DRAIN_BEFORE, _DRAIN_AFTER)

    assert proposals() == ["def advance(y):\n    return y + 1009\n", "def advance(y):\n    return y + 1007\n"]
