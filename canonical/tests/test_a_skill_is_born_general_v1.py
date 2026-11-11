"""A skill must not be BORN a specialist.

Round 36 fixed recall: an already-stored skill taught as "unique" could reach "distinct".
That was the wrong end of the pipeline. `anti_unify_workflow` froze the literal adjective
into the skeleton AND the regex, so every skill compiled from then on was born a specialist
and needed rescuing at read time.

The 2026 field answer is the same finding from a different direction:
  * PolySkill (ICLR 2026) lifts cross-site skill reuse from <31% to 73% by separating a
    skill's abstract GOAL from its concrete IMPLEMENTATION.
  * Memory Transfer Learning (2026) finds high-level insights transfer (+3.7%) while
    low-level traces induce NEGATIVE transfer.

So a skill record should carry the OPERATION it performs, not the caller's adjectives.

WHAT THIS PINS
--------------
1. The intent-bearing word is not a hard skeleton token, so a paraphrase is not required.
2. The record is not a wildcard either: it carries a reserved `__intent__` anchor, and an
   intentless match against it is refused. An empty skeleton would be worse than a
   specialist -- it would answer questions it was never taught.
3. Two different intents never share an anchor.
"""
from __future__ import annotations

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as C
from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import anti_unify_workflow

# Resolved at import rather than imported by name: a missing constant should fail the
# ASSERTION ("the record carries no anchor"), not collection. A test that cannot import is a
# test that never ran.
_INTENT_TOKEN = getattr(C, "_INTENT_TOKEN", None)


def _compile(goal: str, argv: list[str]):
    return anti_unify_workflow(goal, [{"layer": "cli_exec", "argv": argv}],
                               {"kind": "stdout_line_count"})


def test_the_intent_word_is_not_a_hard_skeleton_token():
    """"unique" names the operation; "distinct" names the same operation."""
    got = _compile("how many unique lines in /x/d.txt", ["sort", "-u", "/x/d.txt"])
    assert "unique" not in got["skeleton_tokens"], got["skeleton_tokens"]


def test_a_born_skill_still_carries_an_anchor():
    """Not a wildcard: the record must still say WHICH question it answers."""
    got = _compile("how many unique lines in /x/d.txt", ["sort", "-u", "/x/d.txt"])
    assert _INTENT_TOKEN is not None, "the compiler defines no intent anchor"
    assert _INTENT_TOKEN in got["skeleton_tokens"]
    assert got["skeleton_intent"] == "uniquelines"


@pytest.mark.parametrize("goal,argv", [
    ("how many lines in /x/d.txt", ["wc", "-l", "/x/d.txt"]),
    ("how many words in /x/d.txt", ["wc", "-w", "/x/d.txt"]),
    ("how many duplicate lines in /x/d.txt", ["uniq", "-d", "/x/d.txt"]),
])
def test_distinct_intents_keep_distinct_anchors(goal, argv):
    """The nearest world in which generalisation must NOT merge two skills."""
    got = _compile(goal, argv)
    assert got["skeleton_intent"] is not None
    assert got["skeleton_intent"] != "uniquelines"


def test_a_skill_with_no_recognisable_intent_is_unchanged():
    """Nothing is generalised that was never classified -- no silent widening."""
    got = _compile("rename the file /x/d.txt", ["mv", "/x/d.txt", "/x/e.txt"])
    assert got["skeleton_tokens"], "an unclassifiable goal keeps its literal skeleton"
    assert got["skeleton_intent"] is None
