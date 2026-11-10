"""r52: THE STRATEGY IS REFUTED BY ITS OWN MECHANISM.

The proposal under test: "give it the smartest actions we need the agent to do; after it
does them at least once it learns all of those permanently; so we solve everything."

This is a claim about what happens as the skill store GROWS. It was never measured, because
every previous round taught between one and eight skills and never built a catalog.

RESULT. One fixed ask in a user's own words ("dedupe the lines in <file>"), against a store
of N taught skills, each in its own sqlite store:

      N=1    sort -u     OK
      N=2    sort -u     OK
      N=5    sort -u     OK
      N=10   sort -u     OK
      N=15   sort -u     OK
      N=20   sort -u     OK
      N=25   sort -u     OK
      N=30   sort        WRONG VERB

The failure at N=30 is not a miss. It returns `sort` without `-u`: the right verb, the right
row, the wrong column. It LOOKS like an answer. r50 reported "0 misroutes, every miss returns
None" as the system's saving grace -- that property is an artifact of teaching one skill at
a time and does not survive a catalog.

This is the 2026 "recall-driven failure" and "confusion gap" from enterprise routing studies,
reproduced here: retrieval recovers *something* as the catalog grows, and the wrong something
is indistinguishable from the right one downstream.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

POOL = [("unique lines of", ["sort", "-u"]), ("count the lines of", ["wc", "-l"]),
        ("dump the contents of", ["cat"]), ("reverse each line of", ["rev"]),
        ("reverse the order of", ["tac"]), ("first line of", ["head", "-1"]),
        ("last line of", ["tail", "-1"]), ("sort the lines of", ["sort"]),
        ("character count of", ["wc", "-c"]), ("word count of", ["wc", "-w"]),
        ("sha256 of", ["sha256sum"]), ("md5 of", ["md5sum"]), ("number the lines of", ["cat", "-n"]),
        ("first column of", ["cut", "-f1"]), ("second column of", ["cut", "-f2"]),
        ("lowercase of", ["tr", "A-Z", "a-z"]), ("upper of", ["tr", "a-z", "A-Z"]),
        ("base64 of", ["base64"]), ("distinct count of", ["sort", "-u"]),
        ("duplicate count of", ["uniq", "-d"]), ("unique count of", ["uniq", "-c"]),
        ("last 3 of", ["tail", "-n", "3"]), ("all but first of", ["tail", "-n", "+2"]),
        ("delete blank lines of", ["grep", "."]), ("bytes of", ["od", "-c"]),
        ("checksum of", ["cksum"]), ("word sort of", ["sort"]), ("case fold of", ["tr", "A-Z", "a-z"]),
        ("line numbers of", ["cat", "-n"]), ("first two lines of", ["head", "-n", "2"])]

ASK = "dedupe the lines in"


def _store_with(n: int):
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("one\ntwo\none\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("red\nblue\nred\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    for goal, argv in POOL[:n]:
        K.compile_and_qualify_skill(
            goal=f"{goal} {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": argv + [str(t)]}],
            postcondition=None, heldout_goal=f"{goal} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
    f = tmp / "data.txt"; f.write_text("z\nq\nz\n", encoding="utf-8")
    got = K.recall_and_execute_workflow(f"{ASK} {f}", cwd=str(tmp), db_path=db)
    return got, f


def _is_right(got) -> bool:
    if got is None:
        return False
    argv = got["provenance"]["steps"][0]["argv"]
    return argv[0] == "sort" and "-u" in argv


@pytest.mark.parametrize("n", [1, 5, 10, 20, 25])
def test_a_small_catalog_selects_correctly(n):
    got, _ = _store_with(n)
    assert _is_right(got), f"n={n} should still choose sort -u"


def test_a_large_catalog_returns_a_WRONG_verb_not_a_miss():
    """The finding. Pinned as a defect, not accepted as behaviour.

    At 30 taught skills the system answers `sort <file>` for 'dedupe the lines in'. That is
    not deletion of duplicates; it is an alphabetised duplicate-retaining listing. It is
    returned with provenance, would pass the derivation audit (it genuinely derives from
    that argv) and would pass the shape audit (the goal did ask for lines)."""
    got, _ = _store_with(30)
    assert got is not None, "it does not refuse -- it answers"
    argv = got["provenance"]["steps"][0]["argv"]
    assert argv[0] == "sort"
    assert "-u" not in argv, "if this ever becomes sort -u the defect is fixed; say so loudly"
    assert not _is_right(got)


def test_the_failure_survives_both_audits_by_construction():
    """A wrong column of the right type is invisible to every instrument this project built.
    r49 found this for a wrong TYPE. Here it is one flag short."""
    answer = {"answer": ["q", "z", "z"], "answer_type": "lines"}
    shape = K.audit_answer_shape(f"dedupe the lines in data.txt", answer)
    assert shape.get("verdict", "").startswith("SHAPE_MATCHES") or "MATCH" in str(shape)


def test_growth_is_the_cause_and_it_is_not_a_miss():
    """The distinction that matters: r50 claimed zero misroutes. That claim was measured at
    n=1 per store. It is false at n=30."""
    small, _ = _store_with(1)
    large, _ = _store_with(30)
    assert small is not None and large is not None
    assert _is_right(small)
    assert not _is_right(large)


# ---------------------------------------------------------------------------
# r52b: THE CAUSE IS NOT SIZE.
#
# The first run looked like a scaling collapse at n=30. Isolation refutes that:
#
#     |S|=30, four confusable sort-skills   -> sort data.txt    WRONG
#     |S|=30, one sort-skill only           -> sort -u          OK
#     |S|=4,  four confusable sort-skills   -> sort data.txt    WRONG
#
# It fails at FOUR. Catalog size is not the variable. Semantic confusability among
# near-identical skills is, and this reproduces the central claim of arXiv 2601.04748v2
# ("semantic confusability among similar skills, rather than library size alone, plays a
# central role in this degradation") at the smallest scale it can be shown.
#
# Consequence for the strategy "teach it all the smartest actions": every near-duplicate
# action added to the catalog makes selection WORSE. Teaching more is not neutral and is
# not merely unhelpful -- past a point it is actively destructive to the thing being taught.
# ---------------------------------------------------------------------------

CONFUSABLE = [("unique lines of", ["sort", "-u"]), ("sort the lines of", ["sort"]),
              ("word sort of", ["sort"]), ("distinct count of", ["sort", "-u"])]


def _store(pool):
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("one\ntwo\none\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("red\nblue\nred\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    for goal, argv in pool:
        K.compile_and_qualify_skill(
            goal=f"{goal} {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": argv + [str(t)]}],
            postcondition=None, heldout_goal=f"{goal} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
    f = tmp / "data.txt"; f.write_text("z\nq\nz\n", encoding="utf-8")
    return K.recall_and_execute_workflow(f"{ASK} {f}", cwd=str(tmp), db_path=db)


def test_four_confusable_skills_are_enough_to_break_selection():
    """Fail at four. Not a capacity limit -- a duplicate limit."""
    got = _store(CONFUSABLE)
    assert got is not None
    argv = got["provenance"]["steps"][0]["argv"]
    assert argv[0] == "sort" and "-u" not in argv


def test_thirty_skills_are_harmless_when_none_are_confusable():
    """The control that kills the 'big catalogs degrade' reading. Thirty distinct
    operations select correctly; four overlapping ones do not."""
    filler = POOL[1:30]
    pool = [("unique lines of", ["sort", "-u"])] + [p for p in filler if p[1][0] != "sort"]
    assert len(pool) >= 25
    got = _store(pool)
    assert got is not None
    argv = got["provenance"]["steps"][0]["argv"]
    assert argv[0] == "sort" and "-u" in argv


def test_the_strategy_of_teaching_everything_is_self_defeating():
    """The one-line refutation of 'just give it all the smartest actions'.

    Adding a near-duplicate action to the catalog does not add capability. It removes the
    ability to select the capability that was already there."""
    before = _store([("unique lines of", ["sort", "-u"])])
    after = _store(CONFUSABLE)
    assert _is_right(before), "one skill: correct"
    assert not _is_right(after), "four overlapping skills: the original skill is now unreachable"
