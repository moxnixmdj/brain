from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime import r2_finance_oewn_synonym_unless_direct_adequacy_v1 as direct
from canonical.runtime import finance_oewn_synonym_unless_branch_v1 as producer
from canonical.runtime import finance_oewn_synonym_unless_verify_v1 as verifier

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "governance" / "H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json"


def _ctx(field: str, value):
    typ = "BOOL" if isinstance(value, bool) else "DECIMAL_STRING"
    c = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {field: {"type": typ, "value": value}},
    }
    return c, typed_context_sha256(c)


def _case(
    *,
    cue="upshot",
    field="result",
    context="The policy concerns a consequence effect outcome from a previous event.",
    value=True,
    literal="true",
):
    c, h = _ctx(field, value)
    return {
        "schema": "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_CASE_V1",
        "source_id": "oewn-finance-case",
        "source_text": f"{context} Apply Rule A unless {cue} is {literal}.",
        "target_field": field,
        "typed_context": c,
        "typed_context_sha256": h,
        "knowledge_path": "canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json",
    }


def _goal():
    return (
        "Using the OEWN-bound typed finance UNLESS case at "
        "canonical/tmp/oewn_case.json, select and independently verify the "
        "applicable branch and save it to canonical/tmp/oewn_out.json."
    )


def _write(root: Path, case):
    p = root / "canonical/tmp/oewn_case.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(case), encoding="utf-8")
    kp = root / "canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json"
    kp.parent.mkdir(parents=True, exist_ok=True)
    kp.write_bytes(PINNED.read_bytes())
    return p


def test_inferred_synonym_consensus_upshot_to_result_passes(tmp_path: Path):
    _write(tmp_path, _case())
    out = direct.run({"task_id": "o1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["lexical_binding_mode"] == "SENSE_CONSENSUS_SYNONYM"
    assert out["target_field"] == "result"
    assert out["selected_branch"] == "EXCEPTION_BRANCH"
    assert out["acceptance_receipt"]["producer_independent"] is True


def test_context_word_sense_comment_to_input_passes(tmp_path: Path):
    case = _case(
        cue="comment",
        field="input",
        context="A personal opinion belief that adds information from users is relevant.",
    )
    _write(tmp_path, case)
    out = direct.run({"task_id": "o2", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["lexical_binding_mode"] == "CONTEXT_UNIQUE_TOP_SENSE_SYNONYM"
    assert out["selected_synsets"] == ["06777755-n"]


def test_context_selecting_non_target_sense_fails_closed(tmp_path: Path):
    case = _case(
        cue="comment",
        field="input",
        context="A written explanation criticism illustration added to a book is relevant.",
    )
    _write(tmp_path, case)
    out = direct.preflight({"task_id": "o3", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"
    assert "SELECTED_SENSE_NOT_TARGET_FIELD_SYNONYM" in out["reason"]


def test_ambiguous_polysemy_without_context_fails_closed(tmp_path: Path):
    case = _case(cue="comment", field="input", context="Context unavailable.")
    _write(tmp_path, case)
    out = direct.preflight({"task_id": "o4", "goal": _goal()}, repo_root=tmp_path)
    assert out["status"] == "FAIL_CLOSED"
    assert "LEXICAL_SENSE_AMBIGUOUS" in out["reason"]


def test_target_field_must_be_member_of_selected_synset(tmp_path: Path):
    case = _case(field="not_a_member")
    case["typed_context"], case["typed_context_sha256"] = _ctx("not_a_member", True)
    _write(tmp_path, case)
    out = direct.preflight({"task_id": "o5", "goal": _goal()}, repo_root=tmp_path)
    assert out["status"] == "FAIL_CLOSED"
    assert "TARGET_FIELD_NOT_SYNONYM" in out["reason"]


def test_incomplete_query_fails_closed(tmp_path: Path):
    case = _case()
    _write(tmp_path, case)
    kp = tmp_path / case["knowledge_path"]
    knowledge = json.loads(kp.read_text(encoding="utf-8"))
    knowledge["queries"]["upshot"]["noun_query_complete"] = False
    kp.write_text(json.dumps(knowledge), encoding="utf-8")
    out = direct.preflight({"task_id": "o6", "goal": _goal()}, repo_root=tmp_path)
    assert out["status"] == "FAIL_CLOSED"
    assert "KNOWLEDGE_BLOB_MISMATCH" in out["reason"]


def test_query_completeness_tamper_fails_closed(tmp_path: Path):
    case = _case()
    _write(tmp_path, case)
    kp = tmp_path / case["knowledge_path"]
    knowledge = json.loads(kp.read_text(encoding="utf-8"))
    knowledge["queries"]["upshot"]["records"][0]["members"] = ["not-upshot", "result"]
    kp.write_text(json.dumps(knowledge), encoding="utf-8")
    out = direct.preflight({"task_id": "o7", "goal": _goal()}, repo_root=tmp_path)
    assert out["status"] == "FAIL_CLOSED"
    assert "KNOWLEDGE_BLOB_MISMATCH" in out["reason"]


def test_preflight_is_side_effect_free(tmp_path: Path):
    _write(tmp_path, _case())
    out = direct.preflight({"task_id": "o8", "goal": _goal()}, repo_root=tmp_path)
    assert out["status"] == "DIRECT_ADEQUACY_ROUTE_MATCHED", out
    assert not (tmp_path / "canonical/tmp/oewn_out.json").exists()


def test_verifier_rejects_tampered_selected_branch(tmp_path: Path):
    case = _case()
    _write(tmp_path, case)
    res = producer.compute(case, repo_root=tmp_path)
    res["selected_branch"] = "ORDINARY_BRANCH"
    checked = verifier.verify(case, res, repo_root=tmp_path)
    assert checked["verified"] is False
    assert "MISMATCH:selected_branch" in checked["errors"]


def test_nonmatching_goal_claims_no_scope(tmp_path: Path):
    out = direct.preflight(
        {"task_id": "o10", "goal": "Analyze this finance policy."},
        repo_root=tmp_path,
    )
    assert out["matched"] is False
    assert out["pass"] is False
