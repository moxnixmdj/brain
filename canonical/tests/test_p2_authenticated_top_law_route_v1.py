import json
from unittest.mock import patch

from canonical.runtime import p2_top_law_policy_adequacy_authenticator_v1 as auth

from canonical.runtime.p2_explicit_contract_membership_v1 import P2
from canonical.runtime.p2_top_law_policy_adequacy_authenticator_v1 import (
    authenticate_repository,
    MEMBERSHIP_ATOM_ID,
)
from canonical.runtime.p2_authenticated_top_law_route_v1 import execute


def source(extra=None):
    task = {
        "audience": "executive",
        "required_topics": ["T1"],
        "evidence": [{"fact_id": "F1"}],
        "edit_candidates": [{
            "id": "E1",
            "analysis_kind": "quantify",
            "topic": "T1",
            "claims": ["F1"],
            "intended_audience": "executive",
            "cost": 1,
        }],
        "edit_budget": 1,
    }
    if extra:
        task.update(extra)
    return json.dumps({"contract": P2, "task": task}, separators=(",", ":"))


def test_existing_independent_top_law_authenticates_policy():
    out = authenticate_repository()
    assert out["pass"] is True, out
    assert out["adequacy_proved"] is True
    assert out["policy_condition"] == {"op": "ATOM", "id": MEMBERSHIP_ATOM_ID}


def test_membership_recognizer_bytes_are_content_bound():
    out = authenticate_repository()
    assert out["pass"] is True, out
    assert out["membership_recognizer_git_blob_sha"] == auth.MEMBERSHIP_BLOB
    with patch.object(auth, "MEMBERSHIP_BLOB", "0" * 40):
        drift = auth.authenticate_repository()
    assert drift["pass"] is False
    assert any("BOUND_BLOB_DRIFT:" + auth.MEMBERSHIP_PATH in x for x in drift["errors"])


def test_lossless_member_executes_authenticated_top_law_policy():
    out = execute(source(), source_id="task")
    assert out["pass"] is True, out
    assert out["status"] == "PASS__AUTHENTICATED_P2_TOP_LAW_POLICY_SELECTED"
    assert out["policy_result"]["selected_edits"] == ["E1"]


def test_extra_semantic_dimension_blocks_route_before_policy():
    out = execute(source({"producer_roster": ["A", "B"]}), source_id="task")
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__P2_MEMBERSHIP_NOT_PROVED"


def test_policy_route_does_not_claim_terminal_authority():
    out = execute(source(), source_id="task")
    assert out["terminal_authority"] is False
    assert "GLOBAL_BENCHMARK_SCOPE_REMAIN_SEPARATE" in out["boundary"]
