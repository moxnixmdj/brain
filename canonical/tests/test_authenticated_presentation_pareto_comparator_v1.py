import json

from canonical.runtime.authenticated_presentation_pareto_comparator_v1 import (
    compare,
    CONTRACT_SCHEMA,
    CONTRACT_VERIFY_SCHEMA,
    DIMENSION_SCHEMA,
    DIMENSION_VERIFY_SCHEMA,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id


A = "a" * 64
B = "b" * 64


def _write(root, name, doc):
    p = root / "canonical" / "verification" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    p.write_bytes(raw)
    return {
        "path": str(p.relative_to(root)).replace("\\", "/"),
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }


def _bundle(root, relations, *, complete=True):
    dims = list(relations)
    contract_doc = {
        "schema": CONTRACT_SCHEMA,
        "comparison_id": "cmp-1",
        "artifact_a_sha256": A,
        "artifact_b_sha256": B,
        "order_rule": "AT_LEAST_ONE_BETTER_AND_NO_WORSE",
        "dimension_set_complete": complete,
        "dimensions": dims,
    }
    contract = _write(root, "contract.json", contract_doc)
    cv = _write(root, "contract_verify.json", {
        "schema": CONTRACT_VERIFY_SCHEMA,
        "subject_git_blob_sha": contract["git_blob_sha"],
        "comparison_id": "cmp-1",
        "dimension_set_complete": complete,
        "pass": True,
        "verifier_id": "independent-contract-verifier",
    })

    bindings = {}
    for i, (dim, rel) in enumerate(relations.items()):
        receipt = _write(root, f"d{i}.json", {
            "schema": DIMENSION_SCHEMA,
            "comparison_id": "cmp-1",
            "dimension_id": dim,
            "artifact_a_sha256": A,
            "artifact_b_sha256": B,
            "relation": rel,
            "pass": True,
        })
        verify = _write(root, f"d{i}_verify.json", {
            "schema": DIMENSION_VERIFY_SCHEMA,
            "subject_git_blob_sha": receipt["git_blob_sha"],
            "comparison_id": "cmp-1",
            "dimension_id": dim,
            "relation": rel,
            "pass": True,
            "verifier_id": "independent-dimension-verifier",
        })
        bindings[dim] = {"receipt": receipt, "verification": verify}

    return {
        "contract_binding": {"receipt": contract, "verification": cv},
        "dimension_bindings": bindings,
    }


def test_a_pareto_dominates_when_one_better_and_none_worse(tmp_path):
    out = compare(_bundle(tmp_path, {"spacing": "A_BETTER", "hierarchy": "EQUAL"}), repo_root=tmp_path)
    assert out["pass"] is True
    assert out["pareto_relation"] == "A_PARETO_DOMINATES_B"


def test_b_pareto_dominates(tmp_path):
    out = compare(_bundle(tmp_path, {"spacing": "EQUAL", "hierarchy": "B_BETTER"}), repo_root=tmp_path)
    assert out["pass"] is True
    assert out["pareto_relation"] == "B_PARETO_DOMINATES_A"


def test_regression_makes_order_incomparable(tmp_path):
    out = compare(_bundle(tmp_path, {"spacing": "A_BETTER", "hierarchy": "B_BETTER"}), repo_root=tmp_path)
    assert out["pass"] is True
    assert out["pareto_relation"] == "INCOMPARABLE"


def test_all_equal_is_tie(tmp_path):
    out = compare(_bundle(tmp_path, {"spacing": "EQUAL", "hierarchy": "EQUAL"}), repo_root=tmp_path)
    assert out["pass"] is True
    assert out["pareto_relation"] == "TIE"


def test_missing_dimension_binding_fails_closed(tmp_path):
    bundle = _bundle(tmp_path, {"spacing": "A_BETTER", "hierarchy": "EQUAL"})
    del bundle["dimension_bindings"]["hierarchy"]
    out = compare(bundle, repo_root=tmp_path)
    assert out["pass"] is False
    assert "DIMENSION_BINDING_DOMAIN_MISMATCH" in out["errors"][0]


def test_unverified_complete_dimension_set_fails_closed(tmp_path):
    out = compare(_bundle(tmp_path, {"spacing": "A_BETTER"}, complete=False), repo_root=tmp_path)
    assert out["pass"] is False
    assert "DIMENSION_SET_NOT_DECLARED_COMPLETE" in out["errors"][0]


def test_dimension_receipt_blob_drift_fails_closed(tmp_path):
    bundle = _bundle(tmp_path, {"spacing": "A_BETTER"})
    bundle["dimension_bindings"]["spacing"]["receipt"]["git_blob_sha"] = "0" * 40
    out = compare(bundle, repo_root=tmp_path)
    assert out["pass"] is False
