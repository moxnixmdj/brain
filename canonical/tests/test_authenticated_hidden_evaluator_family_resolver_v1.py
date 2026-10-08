import json
import tempfile
from pathlib import Path

from canonical.runtime.authenticated_hidden_evaluator_family_resolver_v1 import (
    CONTRACT_SCHEMA,
    CONTRACT_VERIFY_SCHEMA,
    DIST_SCHEMA,
    DIST_VERIFY_SCHEMA,
    FAMILY,
    SUPPORT_SCHEMA,
    SUPPORT_VERIFY_SCHEMA,
    evaluate,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id


def _write(root: Path, path: str, obj: dict) -> dict:
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()
    p.write_bytes(data)
    return {"path": path, "git_blob_sha": git_blob_id(data, object_format="sha1")}


def _pair(root: Path, stem: str, receipt: dict, verification: dict, verify_schema: str) -> dict:
    rr = _write(root, f"r/{stem}.json", receipt)
    verification = {
        **verification,
        "schema": verify_schema,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "pass": True,
        "independent_verified": True,
    }
    rv = _write(root, f"v/{stem}.json", verification)
    return {"receipt": rr, "verification": rv}


def _contract(root: Path, *, actual_in_family=True) -> dict:
    outcomes = ["BAD", "OK", "TOP"]
    closure = [
        {"better": "BAD", "worse": "BAD"},
        {"better": "OK", "worse": "BAD"},
        {"better": "OK", "worse": "OK"},
        {"better": "TOP", "worse": "BAD"},
        {"better": "TOP", "worse": "OK"},
        {"better": "TOP", "worse": "TOP"},
    ]
    receipt = {
        "schema": CONTRACT_SCHEMA,
        "pass": True,
        "comparison_id": "C1",
        "evaluator_id": "E1",
        "evaluator_family": FAMILY,
        "outcome_ids": outcomes,
        "dominance_edges": [
            {"better": "TOP", "worse": "OK"},
            {"better": "OK", "worse": "BAD"},
        ],
        "outcome_basis_scope_complete": True,
        "load_bearing_material_dimensions_complete": True,
        "material_order_sound": True,
        "actual_target_evaluator_in_family": actual_in_family,
        "actual_target_evaluator_bounded": True,
        "actual_target_evaluator_monotone_nondecreasing_on_material_order": True,
    }
    verification = {
        "comparison_id": "C1",
        "evaluator_id": "E1",
        "evaluator_family": FAMILY,
        "outcome_ids": outcomes,
        "dominance_transitive_closure": closure,
        "outcome_basis_scope_complete": True,
        "load_bearing_material_dimensions_complete": True,
        "material_order_sound": True,
        "actual_target_evaluator_in_family": actual_in_family,
        "actual_target_evaluator_bounded": True,
        "actual_target_evaluator_monotone_nondecreasing_on_material_order": True,
    }
    return _pair(root, "contract", receipt, verification, CONTRACT_VERIFY_SCHEMA)


def _support(root: Path, support_ids) -> dict:
    receipt = {
        "schema": SUPPORT_SCHEMA,
        "pass": True,
        "comparison_id": "C1",
        "role": "BRAIN",
        "support_scope_complete": True,
        "deployed_exact": True,
        "support_ids": list(support_ids),
    }
    verification = {
        "comparison_id": "C1",
        "role": "BRAIN",
        "support_scope_complete": True,
        "deployed_exact": True,
        "support_ids": list(support_ids),
    }
    return _pair(root, "support", receipt, verification, SUPPORT_VERIFY_SCHEMA)


def _dist(root: Path, role: str, rows) -> dict:
    receipt = {
        "schema": DIST_SCHEMA,
        "pass": True,
        "comparison_id": "C1",
        "role": role,
        "distribution_scope_complete": True,
        "distribution": rows,
    }
    verification = {
        "comparison_id": "C1",
        "role": role,
        "distribution_scope_complete": True,
        "distribution": rows,
    }
    return _pair(root, "dist_" + role.lower(), receipt, verification, DIST_VERIFY_SCHEMA)


def test_target_free_top_support_passes_without_target_distribution():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate({
            "mode": "TARGET_FREE_TOP_SUPPORT",
            "evaluator_contract_binding": _contract(root),
            "brain_support_binding": _support(root, ["TOP"]),
        }, repo_root=root)
        assert out["pass"] is True
        assert out["universal_monotone_utility_noninferiority"] is True
        assert out["target_distribution_required"] is False
        assert out["terminal_authority"] is False


def test_target_free_non_top_support_returns_exact_missing_pair():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate({
            "mode": "TARGET_FREE_TOP_SUPPORT",
            "evaluator_contract_binding": _contract(root),
            "brain_support_binding": _support(root, ["OK"]),
        }, repo_root=root)
        assert out["pass"] is False
        assert out["status"].startswith("UNRESOLVED__")
        assert out["missing_cross_support_dominance_relations"] == [
            {"brain_outcome_id": "OK", "target_outcome_id": "TOP"}
        ]


def test_authenticated_coupling_passes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate({
            "mode": "MATCHED_DISTRIBUTION_COUPLING",
            "evaluator_contract_binding": _contract(root),
            "target_distribution_binding": _dist(root, "TARGET", [{"id": "OK", "probability": "1"}]),
            "brain_distribution_binding": _dist(root, "BRAIN", [{"id": "TOP", "probability": "1"}]),
        }, repo_root=root)
        assert out["pass"] is True
        assert out["max_coupled_mass"] == "1"
        assert out["universal_monotone_utility_noninferiority"] is True


def test_failed_coupling_returns_policy_changing_relation_witness():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate({
            "mode": "MATCHED_DISTRIBUTION_COUPLING",
            "evaluator_contract_binding": _contract(root),
            "target_distribution_binding": _dist(root, "TARGET", [{"id": "TOP", "probability": "1"}]),
            "brain_distribution_binding": _dist(root, "BRAIN", [{"id": "OK", "probability": "1"}]),
        }, repo_root=root)
        assert out["pass"] is False
        assert out["unmatched_target_mass"] == [
            {"target_outcome_id": "TOP", "unmatched_mass": "1"}
        ]
        assert out["decision_relevant_missing_relation_candidates"][0] == {
            "missing_relation": {"better": "OK", "worse": "TOP"},
            "coupled_mass_gain": "1",
            "post_relation_max_coupled_mass": "1",
            "single_relation_sufficient": True,
        }


def test_actual_evaluator_family_cannot_be_self_assumed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate({
            "mode": "TARGET_FREE_TOP_SUPPORT",
            "evaluator_contract_binding": _contract(root, actual_in_family=False),
            "brain_support_binding": _support(root, ["TOP"]),
        }, repo_root=root)
        assert out["pass"] is False
        assert "CONTRACT_PREMISE_NOT_PROVED:actual_target_evaluator_in_family" in out["reason"]


def test_incomplete_brain_support_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        contract = _contract(root)
        support = _support(root, ["TOP"])
        doc_path = root / support["receipt"]["path"]
        doc = json.loads(doc_path.read_text())
        doc["support_scope_complete"] = False
        data = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()
        doc_path.write_bytes(data)
        support["receipt"]["git_blob_sha"] = git_blob_id(data, object_format="sha1")
        out = evaluate({
            "mode": "TARGET_FREE_TOP_SUPPORT",
            "evaluator_contract_binding": contract,
            "brain_support_binding": support,
        }, repo_root=root)
        assert out["pass"] is False


def test_receipt_byte_drift_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        contract = _contract(root)
        p = root / contract["receipt"]["path"]
        p.write_text(p.read_text() + " ")
        out = evaluate({
            "mode": "TARGET_FREE_TOP_SUPPORT",
            "evaluator_contract_binding": contract,
            "brain_support_binding": _support(root, ["TOP"]),
        }, repo_root=root)
        assert out["pass"] is False
        assert "RECEIPT_GIT_BLOB_MISMATCH" in out["reason"]


def test_order_cycle_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        outcomes = ["A", "B"]
        receipt = {
            "schema": CONTRACT_SCHEMA,
            "pass": True,
            "comparison_id": "C1",
            "evaluator_id": "E1",
            "evaluator_family": FAMILY,
            "outcome_ids": outcomes,
            "dominance_edges": [
                {"better": "A", "worse": "B"},
                {"better": "B", "worse": "A"},
            ],
            "outcome_basis_scope_complete": True,
            "load_bearing_material_dimensions_complete": True,
            "material_order_sound": True,
            "actual_target_evaluator_in_family": True,
            "actual_target_evaluator_bounded": True,
            "actual_target_evaluator_monotone_nondecreasing_on_material_order": True,
        }
        verification = {
            "comparison_id": "C1",
            "evaluator_id": "E1",
            "evaluator_family": FAMILY,
            "outcome_ids": outcomes,
            "dominance_transitive_closure": [],
            "outcome_basis_scope_complete": True,
            "load_bearing_material_dimensions_complete": True,
            "material_order_sound": True,
            "actual_target_evaluator_in_family": True,
            "actual_target_evaluator_bounded": True,
            "actual_target_evaluator_monotone_nondecreasing_on_material_order": True,
        }
        contract = _pair(root, "cycle", receipt, verification, CONTRACT_VERIFY_SCHEMA)
        out = evaluate({
            "mode": "TARGET_FREE_TOP_SUPPORT",
            "evaluator_contract_binding": contract,
            "brain_support_binding": _support(root, ["A"]),
        }, repo_root=root)
        assert out["pass"] is False
        assert "MATERIAL_ORDER_NOT_ANTISYMMETRIC" in out["reason"]


def test_unknown_outcome_distribution_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate({
            "mode": "MATCHED_DISTRIBUTION_COUPLING",
            "evaluator_contract_binding": _contract(root),
            "target_distribution_binding": _dist(root, "TARGET", [{"id": "ALIEN", "probability": "1"}]),
            "brain_distribution_binding": _dist(root, "BRAIN", [{"id": "TOP", "probability": "1"}]),
        }, repo_root=root)
        assert out["pass"] is False
        assert "DISTRIBUTION_OUTCOME_OUTSIDE_BASIS:TARGET:ALIEN" in out["reason"]


def test_zero_terminal_and_u_authority_on_success():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate({
            "mode": "TARGET_FREE_TOP_SUPPORT",
            "evaluator_contract_binding": _contract(root),
            "brain_support_binding": _support(root, ["TOP"]),
        }, repo_root=root)
        assert out["pass"] is True
        assert out["db_admission_authority"] is False
        assert out["u_empty_authorized"] is False
        assert out["terminal_authority"] is False
        assert out["terminal_credit_delta"] == 0
