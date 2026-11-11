"""r48: the receipt becomes evidence.

r47 built provenance -- argv, exit, stdout sha256. Its own closing note said a receipt is
not an audit, citing arXiv 2610.09581: a reader can retrieve every literal source correctly
and still emit unsupported attribution, 22 of 26 undetectable from the answer. That paper's
fix is a DETERMINISTIC same-packet comparator. This is that comparator.

`audit_answer_by_rederivation(result)` ignores the skill entirely: it takes the recorded
argv, runs it, applies the same answer contract to ITS OWN stdout, and compares.

MEASURED
  * 23 of 23 track answers: ANSWER_MATCHES_ITS_SOURCE, 0 mismatches, 0 unauditable.
  * a fabricated answer      -> ANSWER_NOT_DERIVABLE_FROM_ITS_SOURCE
  * a wrong-source argv      -> ANSWER_NOT_DERIVABLE_FROM_ITS_SOURCE
  * no workspace to replay in-> NOT_AUDITABLE__WORKSPACE_UNKNOWN (refuses, does not guess)
  * no provenance at all     -> NOT_AUDITABLE__NO_STEPS

THE BUG THIS FOUND IN ITSELF, WHICH IS THE POINT
------------------------------------------------
The first auditor replayed the recorded argv from its own cwd. But the recorded argv is the
TRANSLATED form (`beta.txt`), which only resolves inside the staged workspace -- so 20 of 23
answers appeared "not derivable" when nothing was wrong. An auditor that cannot resolve its
own inputs must fail loudly, not produce a verdict. It now requires the workspace and says
NOT_AUDITABLE when it is missing.
"""
from __future__ import annotations

import copy
import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

FIXTURE = "zebra\napple\nzebra\n"          # 2 unique
HELD = "one\ntwo\none\n"


@pytest.fixture()
def recalled():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "a.sqlite")
    a = tmp / "alpha.txt"; a.write_text(FIXTURE, encoding="utf-8")
    h = tmp / "held.txt"; h.write_text(HELD, encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    r = K.compile_and_qualify_skill(
        goal=f"unique lines of {a}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(a)]}],
        postcondition=None, heldout_goal=f"unique lines of {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    assert r.get("pass"), r.get("status")
    hit = K.recall_and_execute_workflow(f"unique lines of {a}", cwd=str(tmp), db_path=db)
    assert hit is not None
    return hit, tmp


def test_an_honest_answer_matches_its_own_source(recalled):
    hit, _ = recalled
    audit = K.audit_answer_by_rederivation(hit)
    assert audit["auditable"] is True
    assert audit["verdict"] == "ANSWER_MATCHES_ITS_SOURCE"
    assert audit["answer_stated"] == audit["answer_rederived"] == ["apple", "zebra"]


def test_a_fabricated_answer_is_caught(recalled):
    hit, _ = recalled
    doctored = copy.deepcopy(hit)
    doctored["answer"] = ["totally", "invented"]
    audit = K.audit_answer_by_rederivation(doctored)
    assert audit["verdict"] == "ANSWER_NOT_DERIVABLE_FROM_ITS_SOURCE"


def test_a_wrong_source_is_caught(recalled):
    hit, tmp = recalled
    other = tmp / "held.txt"
    doctored = copy.deepcopy(hit)
    doctored["provenance"]["steps"][0]["argv"] = ["sort", "-u", str(other)]
    audit = K.audit_answer_by_rederivation(doctored)
    assert audit["verdict"] == "ANSWER_NOT_DERIVABLE_FROM_ITS_SOURCE"


def test_an_auditor_that_cannot_resolve_its_inputs_refuses_to_judge(recalled):
    hit, _ = recalled
    doctored = copy.deepcopy(hit)
    doctored["provenance"]["workspace"] = None
    audit = K.audit_answer_by_rederivation(doctored)
    assert audit["auditable"] is False
    assert audit["verdict"] == "NOT_AUDITABLE__WORKSPACE_UNKNOWN"


def test_no_provenance_means_no_verdict(recalled):
    hit, _ = recalled
    doctored = copy.deepcopy(hit)
    doctored["provenance"]["steps"] = []
    audit = K.audit_answer_by_rederivation(doctored)
    assert audit["verdict"] == "NOT_AUDITABLE__NO_STEPS"


def test_a_multi_step_answer_is_not_audited_by_replaying_a_subset(recalled):
    hit, _ = recalled
    doctored = copy.deepcopy(hit)
    doctored["provenance"]["steps"] = [hit["provenance"]["steps"][0],
                                       hit["provenance"]["steps"][0]]
    audit = K.audit_answer_by_rederivation(doctored)
    assert audit["verdict"] == "NOT_AUDITABLE__MULTI_STEP"


def test_the_auditor_uses_no_model(recalled):
    hit, _ = recalled
    audit = K.audit_answer_by_rederivation(hit)
    assert "no model" in audit["method"].lower()
