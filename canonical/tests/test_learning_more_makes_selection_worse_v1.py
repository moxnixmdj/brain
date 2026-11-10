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


@pytest.mark.parametrize("n", [1, 2, 5, 10, 20, 25, 30])
def test_never_a_wrong_verb_at_any_catalog_size(n):
    """r57 replaces r52's headline. Across every catalog size the invariant is the same:
    either the right operation comes back, or nothing does. Never `sort` without `-u`.

    At n>=5 the ask genuinely ties (`count the lines of` also scores on the word "lines"),
    so a correct answer there is only possible when the target is the sole scoring
    operation. Where it is not, the system must refuse. r52 recorded `sort <file>` at n=30
    as the defect; this asserts that shape can no longer occur."""
    got, _ = _store_with(n)
    if got is not None:
        argv = got["provenance"]["steps"][0]["argv"]
        assert argv[0] == "sort" and "-u" in argv, f"n={n} returned a wrong verb: {argv}"


def test_the_positive_control_and_the_hardest_admission():
    """n=1 answers. n=2 does NOT: `count the lines of` scores on the same word ("lines") as
    `unique lines of`, so the ask is a genuine tie with only two skills in the store.

    That is the most useful single fact in this round. A user who has taught exactly two
    operations, one of which counts lines and one of which dedupes lines, and who then says
    "dedupe the lines in", cannot be served by ranking. The system's honest options are to
    ask, or to be wrong. r50 counted the n=2 case as a pass and moved on."""
    assert _is_right(_store_with(1)[0]), "one skill: unambiguous, must answer"
    assert _store_with(2)[0] is None, "two line-operations: genuine tie, must refuse"


def test_a_large_catalog_no_longer_returns_a_WRONG_verb():
    """r52 pinned the opposite of this: at 30 taught skills the system answered `sort <file>`
    for 'dedupe the lines in' -- deleted nothing, alphabetised everything, and passed both
    audits. r57's tie gate now refuses instead.

    The refusal is raised to a question by `answer_or_ask`, which names the operations."""
    got, f = _store_with(30)
    assert got is None, "a wrong verb must not come back as an answer"
    tmp = f.parent
    door = K.answer_or_ask(f"dedupe the lines in {f}", cwd=str(tmp), db_path=str(tmp / "s.sqlite"))
    assert door["verdict"] == "ASK"
    assert len(door.get("options") or []) >= 1


def test_the_failure_survives_both_audits_by_construction():
    """A wrong column of the right type is invisible to every instrument this project built.
    r49 found this for a wrong TYPE. Here it is one flag short."""
    answer = {"answer": ["q", "z", "z"], "answer_type": "lines"}
    shape = K.audit_answer_shape(f"dedupe the lines in data.txt", answer)
    assert shape.get("verdict", "").startswith("SHAPE_MATCHES") or "MATCH" in str(shape)


def test_growth_used_to_produce_a_wrong_verb_and_now_produces_a_refusal():
    """r50 claimed zero misroutes. Measured at one skill per store, that was true; at n=30 it
    was false. r57 makes the n=30 case refuse, so the claim holds again -- for a different
    reason and at the cost of an answer."""
    small, _ = _store_with(1)
    large, _ = _store_with(30)
    assert _is_right(small)
    assert large is None or _is_right(large)
    assert not (large is not None and not _is_right(large))


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


def test_four_confusable_skills_are_enough_to_REFUSE_selection():
    """r52: four confusable skills produced `sort` without `-u` -- a wrong answer with a clean
    receipt. r57: same catalog, the tie is detected and nothing is returned.

    The four skills are only TWO operations (sort, sort -u); two are filed twice. That
    duplication is what inflated the tie and is the argument for canonicalisation."""
    got = _store(CONFUSABLE)
    assert got is None, "the tie must not be answered by picking the first that runs"


def test_thirty_skills_are_harmless_when_none_are_confusable():
    """The control that kills the 'big catalogs degrade' reading: the variable is duplicate
    OPERATIONS, not catalog size. With ONE sort in the catalog and no operation whose
    skeleton also scores on the ask, the answer is right at full size.

    The filler is chosen to share no word with the ask, because any operation sharing "lines"
    would tie under r57 and be refused -- correctly."""
    filler = [p for p in POOL[1:30] if p[1][0] != "sort" and "lines" not in p[0]
              and "line" not in p[0] and "row" not in p[0]]
    pool = [("unique lines of", ["sort", "-u"])] + filler
    assert len(pool) >= 19
    got = _store(pool)
    assert _is_right(got), "distinct operations at scale must still select"


def test_the_strategy_of_teaching_everything_is_self_defeating_still():
    """The one-line refutation of 'just give it all the smartest actions'.

    Adding a near-duplicate action to the catalog does not add capability. It removes the
    ability to select the capability that was already there."""
    before = _store([("unique lines of", ["sort", "-u"])])
    after = _store(CONFUSABLE)
    assert _is_right(before), "one skill: correct"
    assert not _is_right(after), "four overlapping skills: the original skill is now unreachable"


# ---------------------------------------------------------------------------
# r57: THE TIE GATE, AND WHAT THE 4/8 ACTUALLY WAS.
#
# r52 concluded "four near-duplicate skills break selection". Correct, and incomplete.
# Four skills were only TWO operations: `sort` and `sort -u`, each filed twice. The
# duplication inflated a tie that was already there.
#
# The tie is between DIFFERENT operations, and it exists at n=5:
#
#     score=0  tac ?path0        reverse the order of
#     score=0  rev ?path0        reverse each line of
#     score=0  cat ?path0        dump the contents of
#     score=1  wc -l             count the lines of      <- ties with
#     score=1  sort -u           unique lines of         <- the target
#
# "dedupe the lines in" shares the word "lines" with BOTH `count the lines of` and
# `unique lines of`. The old loop then ran the candidates in list order and returned the
# first one that executed. It was right when the target happened to come first and wrong
# when it did not -- r52's `sort` without `-u`. The 4/8 contained answers won by ordering.
#
# The gate refuses a tie between distinct operations and lets a single operation filed
# several times through (deduplication, not suppression). The door then names the options.
# ---------------------------------------------------------------------------

def test_a_tie_between_different_operations_is_refused():
    got, f = _store_with(5)
    assert got is None
    door = K.answer_or_ask(f"dedupe the lines in {f}", cwd=str(f.parent), db_path=str(f.parent / "s.sqlite"))
    assert door["verdict"] == "ASK"
    assert door["reason"] == "SEVERAL_OPERATIONS_TIE"


def test_one_operation_filed_twice_is_not_a_tie():
    """Deduplication, not suppression: two skills that run the same program with the same
    first two arguments are one capability and must still be selectable."""
    tmp = pathlib.Path(tempfile.mkdtemp()); db = str(tmp / "one.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    for g in ("unique lines of", "distinct count of"):
        K.compile_and_qualify_skill(
            goal=f"{g} {t}", trace=[{"kind": "cli_exec", "layer": "cli_exec",
                                     "argv": ["sort", "-u", str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
    f = tmp / "data.txt"; f.write_text("z\nq\nz\n", encoding="utf-8")
    got = K.recall_and_execute_workflow(f"unique lines of {f}", cwd=str(tmp), db_path=db)
    assert got is not None and got["answer"] == ["q", "z"]


def test_eight_asks_produce_no_wrong_answer_and_no_lucky_one():
    """r50 reported 4/8 and called the misses recall failures. Some of the four that passed
    were won by candidate order rather than by evidence. Under the gate they are either
    answered on evidence or raised as a question -- never answered by luck."""
    cases = [("unique lines of", ["sort", "-u"], "give me the distinct lines of"),
             ("unique lines of", ["sort", "-u"], "dedupe the lines in"),
             ("count the lines of", ["wc", "-l"], "how many lines are in"),
             ("count the lines of", ["wc", "-l"], "tally the rows of"),
             ("sha256 of", ["sha256sum"], "sha256 of"),
             ("dump the contents of", ["cat"], "show me the content of"),
             ("reverse each line of", ["rev"], "flip each line of"),
             ("reverse the order of", ["tac"], "backwards")]
    answered = wrong = 0
    for taught, argv, ask in cases:
        tmp = pathlib.Path(tempfile.mkdtemp()); db = str(tmp / "s.sqlite")
        t = tmp / "teach.txt"; t.write_text("one\ntwo\none\n", encoding="utf-8")
        h = tmp / "hold.txt"; h.write_text("red\nblue\nred\n", encoding="utf-8")
        s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
        K.compile_and_qualify_skill(
            goal=f"{taught} {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": argv + [str(t)]}],
            postcondition=None, heldout_goal=f"{taught} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        f = tmp / "data.txt"; f.write_text("z\nq\nz\n", encoding="utf-8")
        door = K.answer_or_ask(f"{ask} {f}", cwd=str(tmp), db_path=db)
        if door["verdict"] == "ANSWERED":
            actual = door["result"]["provenance"]["steps"][0]["argv"]
            if actual[0] != argv[0] or (len(argv) > 1 and argv[1] not in actual):
                wrong += 1
            else:
                answered += 1
    assert wrong == 0, "a gate that still returns a wrong operation is not a gate"
    assert answered == 4, answered
