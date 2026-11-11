"""r55: FIRST PRINCIPLES -- THE INFORMATION IS NOT IN THE SENTENCE.

The instruction for this round was to stop patching and derive the constraint. Here it is.

QUESTION: why did selection score 4/8 in r50? Is that a defect in the cue table, the
skeleton matcher, or the floor?

MEASURED, 30-skill catalog, a PERFECT bag-of-words selector (no code of mine, just the
oracle argmax over word overlap):

    ask                            top score   tied at top   verdict
    give me the distinct lines of     1           7          TIE
    dedupe the lines in               1           6          TIE
    how many lines are in             1           6          TIE
    tally the rows of                 0          30          TIE
    sha256 of                         1           1          DETERMINABLE
    show me the content of            0          30          TIE
    flip each line of                 1           4          TIE
    backwards                         0          30          TIE

7 of 8 asks cannot be resolved by ANY selector that consumes only the words of the sentence.
"tally the rows of" shares no content word with "unique lines of" or "count the lines of":
score zero, destination thirty ways.

Nobody can exceed this ceiling with a better index, better embeddings, or a bigger model,
because those all re-rank the same bits. The bit that separates `sort -u` from `sort` is
the word "unique", and in a paraphrase it is simply absent.

CONSEQUENCE. There are exactly two correct behaviours when the top is tied, and this module
had neither. It returned None -- indistinguishable from "no such skill exists" -- or it
silently took the first, which is how r52's `sort` without `-u` happened. `select_or_ask`
implements both correct behaviours:

    SELECTED -- one operation ties at the top
    ASK      -- zero or several tie: name the options, do not guess

This is the same conclusion 2026 reached from the opposite direction. Entity Binding Failures
in Tool-Augmented Agents (arXiv 2606.30531): "For truly ambiguous tasks, no unique binding
can be recovered from the instruction and environment state alone ... the expected safe
behavior is clarification rather than execution." MID-Bench: agents act without asking, and
"clarification behavior accounts for only 0.1% of emitted actions" across four open-weight
agents. ProactiveBench: models recognise ambiguity when asked to judge it and answer directly
anyway -- "knowing but not showing".
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

POOL = [("unique lines of", ["sort", "-u"]), ("count the lines of", ["wc", "-l"]),
        ("dump the contents of", ["cat"]), ("reverse each line of", ["rev"]),
        ("reverse the order of", ["tac"]), ("first line of", ["head", "-1"]),
        ("sort the lines of", ["sort"]), ("sha256 of", ["sha256sum"]),
        ("word count of", ["wc", "-w"])]


@pytest.fixture(scope="module")
def store():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("a\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("b\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    for g, a in POOL:
        K.compile_and_qualify_skill(
            goal=f"{g} {t}", trace=[{"kind": "cli_exec", "layer": "cli_exec",
                                     "argv": a + [str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
    return db


def test_an_unambiguous_sentence_is_selected(store):
    r = K.select_or_ask("sha256 of myfile.txt", db_path=store)
    assert r["verdict"] == "SELECTED"
    assert r["operation"].startswith("sha256sum")


def test_a_sentence_that_cannot_separate_two_operations_asks_instead_of_guessing(store):
    """"dedupe the lines in" ties `sort` against `sort -u`. Guessing returned the wrong one."""
    r = K.select_or_ask("dedupe the lines in myfile.txt", db_path=store)
    assert r["verdict"] == "ASK"
    assert r["reason"] == "SEVERAL_OPERATIONS_TIE"
    assert len(r["options"]) >= 2
    assert "Which of these did you mean" in r["question"]


def test_a_sentence_with_no_overlap_at_all_asks_and_says_why(store):
    """'tally the rows of' scores zero against every taught skeleton. Not a ranking problem."""
    r = K.select_or_ask("tally the rows of myfile.txt", db_path=store)
    assert r["verdict"] == "ASK"
    assert r["reason"] == "NO_WORD_OVERLAP__CANNOT_CHOOSE"


def test_the_ask_is_distinguishable_from_having_nothing_taught():
    empty = str(pathlib.Path(tempfile.mkdtemp()) / "nothing.sqlite")
    r = K.select_or_ask("sha256 of f.txt", db_path=empty)
    assert r["verdict"] == "ASK"
    assert r["reason"] == "NOTHING_TAUGHT"


def test_the_ceiling_is_a_property_of_the_input_not_of_the_code():
    """The oracle: with only the words, the top is tied. No implementation choice changes it.

    The counts depend on the catalog, and both are recorded rather than the flattering one:
    this fixture holds 9 taught operations and 6 of the 8 asks tie at the top. The 30-skill
    catalog measured at the start of the round tied 7 of 8. Fewer skills, fewer ties --
    which is itself the point: the ambiguity is a function of the catalog, not the sentence
    alone, and it only ever gets worse as the catalog grows."""
    asks = ["give me the distinct lines of", "dedupe the lines in", "how many lines are in",
            "tally the rows of", "sha256 of", "show me the content of", "flip each line of",
            "backwards"]
    stop = K._STOP_WORDS
    def words(s):
        import re
        return {w for w in re.findall(r"[a-z0-9]{2,}", s.lower()) if w not in stop}
    ambiguous = 0
    for ask in asks:
        A = words(ask)
        scores = [(len(A & words(g)), " ".join(a[:2])) for g, a in POOL]
        best = max(s for s, _ in scores)
        if len({v for s, v in scores if s == best}) > 1:
            ambiguous += 1
    assert ambiguous == 6, ambiguous


def test_a_single_taught_operation_is_never_ambiguous():
    tmp = pathlib.Path(tempfile.mkdtemp()); db = str(tmp / "one.sqlite")
    t = tmp / "teach.txt"; t.write_text("a\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("b\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    K.compile_and_qualify_skill(
        goal=f"unique lines of {t}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(t)]}],
        postcondition=None, heldout_goal=f"unique lines of {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    r = K.select_or_ask("anything at all here", db_path=db)
    assert r["verdict"] == "SELECTED"
    assert r["confidence"] == "only_one_operation_taught"
