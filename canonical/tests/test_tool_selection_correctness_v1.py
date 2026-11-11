"""r50: TOOL SELECTION CORRECTNESS -- the 2026 metric this project had never computed.

Prefix Executability (arXiv 2610.40444) defines it as "given the state and goal, did the
agent choose the correct tool", scored deterministically with no LLM judge. It is separable
from argument validity and from execution, and it is where an agent can be right for the
wrong reason.

MEASURED, in two parts.

1. IN THE TEACHING WORDS: 5/5. Worthless as evidence -- the goal string IS the index key,
   so of course it returns what was taught. Recorded so the difference is visible.

2. IN NEW WORDS (a user who never saw the teaching sentence): 0/8 BEFORE, 4/8 AFTER.

      dedupe the lines in            -> sort        OK
      sha256 of                      -> sha256sum   OK
      show me the content of         -> cat         OK
      backwards                      -> tac         OK
      give me the distinct lines of  -> None        MISS
      how many lines are in          -> None        MISS
      tally the rows of              -> None        MISS
      flip each line of              -> None        MISS

   ZERO MISROUTES: every miss returned None. Recall never picked a WRONG verb. Selection
   here fails by absence, not by error -- which is the whole reason it was invisible.

WHY THE FOUR MISSES ARE NOT FIXED
---------------------------------
The fixes available are more cue phrases, which is the same "widen until the held-out set
passes" move rejected in r47. 4/8 with four named misses is a measurement; 8/8 after
tuning is a copy of the test set. The root cause is structural and is stated below.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K


def test_selection_in_the_teaching_words_is_perfect_and_means_nothing():
    """The circular version. Kept as a control so nobody reports it as a result."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    h = tmp / "held.txt"; h.write_text("one\ntwo\none\n", encoding="utf-8")
    f = tmp / "data.txt"; f.write_text("zebra\napple\nzebra\n", encoding="utf-8")
    pairs = [("unique lines of", ["sort", "-u"]), ("count the lines of", ["wc", "-l"]),
             ("sha256 of", ["sha256sum"]), ("dump the contents of", ["cat"]),
             ("reverse each line of", ["rev"])]
    for goal, argv in pairs:
        r = K.compile_and_qualify_skill(
            goal=f"{goal} {h}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": argv + [str(h)]}],
            postcondition=None, heldout_goal=f"{goal} {f}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        assert r.get("pass"), r.get("status")
    correct = 0
    for goal, argv in pairs:
        hit = K.recall_and_execute_workflow(f"{goal} {f}", cwd=str(tmp), db_path=db)
        if hit and hit["provenance"]["steps"][0]["argv"][0] == argv[0]:
            correct += 1
    assert correct == 5, "in-teaching-words selection was 5/5"


@pytest.fixture(scope="module")
def selection_score():
    cases = [("unique lines of", ["sort", "-u"], "give me the distinct lines of"),
             ("unique lines of", ["sort", "-u"], "dedupe the lines in"),
             ("count the lines of", ["wc", "-l"], "how many lines are in"),
             ("count the lines of", ["wc", "-l"], "tally the rows of"),
             ("sha256 of", ["sha256sum"], "sha256 of"),
             ("dump the contents of", ["cat"], "show me the content of"),
             ("reverse each line of", ["rev"], "flip each line of"),
             ("reverse the order of", ["tac"], "backwards")]
    hits = seconds = misses = 0
    for taught, argv, ask in cases:
        tmp = pathlib.Path(tempfile.mkdtemp())
        db = str(tmp / "s.sqlite")
        s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
        h = tmp / "held.txt"; h.write_text("one\ntwo\none\n", encoding="utf-8")
        f = tmp / "data.txt"; f.write_text("zebra\napple\nzebra\n", encoding="utf-8")
        K.compile_and_qualify_skill(
            goal=f"{taught} {h}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": argv + [str(h)]}],
            postcondition=None, heldout_goal=f"{taught} {f}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        got = K.recall_and_execute_workflow(f"{ask} {f}", cwd=str(tmp), db_path=db)
        if got is None:
            misses += 1
            continue
        verb = got["provenance"]["steps"][0]["argv"][0]
        if verb == argv[0]:
            hits += 1
        else:
            seconds += 1
    return {"hits": hits, "misroutes": seconds, "misses": misses}


def test_selection_in_new_words_is_four_of_eight(selection_score):
    """Pinned. If this rises through better cues, raise it deliberately -- do not let it
    drift by widening a vocabulary until the test turns green."""
    assert selection_score["hits"] == 4, selection_score


def test_every_miss_is_an_absence_not_a_wrong_verb(selection_score):
    """The saving grace, and the reason the defect was invisible: a miss returns None."""
    assert selection_score["misroutes"] == 0, selection_score
    assert selection_score["misses"] == 4, selection_score


def test_the_verb_inference_is_a_vocabulary_not_comprehension():
    assert K.infer_verb_from_goal("dedupe the lines in f") == "sort"
    assert K.infer_verb_from_goal("how many lines are in f") == "wc"
    # and it simply has no answer for phrasing outside the table
    assert K.infer_verb_from_goal("reticulate the splines of f") is None


def test_the_structural_cause_is_recorded():
    """Recall is still gated by sentence-shaped checks. A verb-selected candidate has to
    clear a regex written for a DIFFERENT sentence, which is why four remain unreachable.
    This test documents the cause rather than asserting a fix."""
    src = pathlib.Path(K.__file__).read_text(encoding="utf-8")
    assert "_selected_by" in src
    assert "_bind_by_verb_selection" in src
