"""r48: cross-source conflation probe.

ProvenanceGuard (arXiv 2606.18037) names the failure: a claim can be supported SOMEWHERE
while being attributed to the WRONG source, and source-blind checks cannot see it. This is
the minimal probe for it.

Teach a skill bound to alpha.txt. Ask about beta.txt, which the skill has never seen and
whose correct answer differs. Three things must hold:
  1. the answer describes beta, not alpha;
  2. the recorded argv names beta;
  3. the recorded argv_asked names beta as it was asked (the absolute path).

MEASURED 2026-11-09: all three hold. The answer for beta was ['fig','kiwi','plum'] where
alpha's was ['apple','zebra'] -- so a conflation would have been visible.

THE PROBE'S OWN BUG, RECORDED
-----------------------------
The first version compared `str(argv[-1]) == str(asked_path)` and printed
"*** WRONG SOURCE ***" for a correct answer, because `argv` is the TRANSLATED workspace
form ('beta.txt') while `argv_asked` is the absolute path. Both name the same file. The
procedure below checks both fields properly. A probe that cries wolf is worse than none.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

ALPHA = "zebra\napple\nzebra\n"                    # 2 unique
HELD = "one\ntwo\none\n"                           # held-out, distinct from alpha
BETA = "kiwi\nplum\nkiwi\nfig\nplum\n"             # 3 unique, never seen


@pytest.fixture()
def trained():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "x.sqlite")
    a = tmp / "alpha.txt"; a.write_text(ALPHA, encoding="utf-8")
    h = tmp / "held.txt"; h.write_text(HELD, encoding="utf-8")
    b = tmp / "beta.txt"; b.write_text(BETA, encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    r = K.compile_and_qualify_skill(
        goal=f"unique lines of {a}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(a)]}],
        postcondition=None, heldout_goal=f"unique lines of {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    assert r.get("pass"), r.get("status")
    return tmp, db, a, b


def test_the_answer_describes_the_file_asked_about(trained):
    tmp, db, a, b = trained
    hit = K.recall_and_execute_workflow(f"unique lines of {b}", cwd=str(tmp), db_path=db)
    assert hit is not None
    assert hit["answer"] == ["fig", "kiwi", "plum"], "this is beta's content, not alpha's"
    assert hit["answer"] != ["apple", "zebra"], "no conflation with the trained source"


def test_the_recorded_argv_names_the_right_file(trained):
    tmp, db, a, b = trained
    hit = K.recall_and_execute_workflow(f"unique lines of {b}", cwd=str(tmp), db_path=db)
    step = hit["provenance"]["steps"][0]
    ran = [str(x) for x in step["argv"]]
    asked = [str(x) for x in step["argv_asked"]]
    # argv is the translated workspace form; argv_asked is what we asked about
    assert pathlib.Path(ran[-1]).name == b.name
    assert asked[-1] == str(b)


def test_the_two_fields_disagree_in_form_and_that_is_correct(trained):
    """A naive probe that compares argv[-1] to the asked path reports a false alarm."""
    tmp, db, a, b = trained
    hit = K.recall_and_execute_workflow(f"unique lines of {b}", cwd=str(tmp), db_path=db)
    step = hit["provenance"]["steps"][0]
    assert str(step["argv"][-1]) != str(step["argv_asked"][-1])
    assert pathlib.Path(step["argv"][-1]).name == pathlib.Path(step["argv_asked"][-1]).name


def test_the_answer_survives_its_own_audit(trained):
    tmp, db, a, b = trained
    hit = K.recall_and_execute_workflow(f"unique lines of {b}", cwd=str(tmp), db_path=db)
    audit = K.audit_answer_by_rederivation(hit)
    assert audit["auditable"] is True
    assert audit["verdict"] == "ANSWER_MATCHES_ITS_SOURCE"
