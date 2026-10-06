from canonical.runtime.terminal_progress_delta_gate_v1 import (
    INPUT_SCHEMA,
    STATE_SCHEMA,
    compile_result,
    sha256_json,
)

A40 = "a" * 40

def state(truth, interfaces, prereqs, depth, nodes):
    raw = {
        "schema": STATE_SCHEMA,
        "open_truth_obligations": list(truth),
        "active_causal_interfaces": list(interfaces),
        "open_prerequisites": list(prereqs),
        "max_open_causal_depth": depth,
        "open_proof_node_count": nodes,
    }
    raw["state_sha256"] = sha256_json(raw)
    return raw

def receipt(path="canonical/verification/X.json"):
    return {"path": path, "git_blob_sha": A40}

def test_direct_truth_closure_is_progress():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": state(["P1", "P2"], ["I1", "I2"], ["A", "B"], 3, 7),
        "after": state(["P2"], ["I1", "I2"], ["A", "B"], 3, 7),
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [receipt()],
    }
    out = compile_result(doc)
    assert out["status"] == "ADMIT_TERMINAL_CONTRACTING_PROGRESS"
    assert out["counts_as_progress"] is True
    assert out["closed_truth_obligations"] == ["P1"]

def test_shared_interface_contraction_is_progress_even_without_terminal_credit():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": state(["P1", "P2"], ["I1", "I2", "I3"], ["A", "B"], 4, 9),
        "after": state(["P1", "P2"], ["I1", "I2"], ["A", "B"], 4, 9),
        "target_truth_obligations": ["P1", "P2"],
        "evidence_receipts": [receipt()],
    }
    out = compile_result(doc)
    assert out["status"] == "ADMIT_TERMINAL_CONTRACTING_PROGRESS"
    assert out["before_potential"] == [2, 3, 4, 2, 9]
    assert out["after_potential"] == [2, 2, 4, 2, 9]

def test_prerequisite_chain_growth_without_contraction_is_rejected():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": state(["P1"], ["I1"], ["A"], 2, 4),
        "after": state(["P1"], ["I1"], ["A", "B"], 2, 5),
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [receipt()],
    }
    out = compile_result(doc)
    assert out["status"] == "REJECT_NONCONTRACTING_PROGRESS"
    assert out["counts_as_progress"] is False

def test_compiler_repackaging_with_identical_potential_is_rejected():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": state(["P1"], ["I1"], ["A"], 2, 4),
        "after": state(["P1"], ["I1"], ["RENAMED_A"], 2, 4),
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [receipt()],
    }
    out = compile_result(doc)
    assert out["status"] == "REJECT_NONCONTRACTING_PROGRESS"

def test_truth_repair_may_reopen_work_but_never_counts_as_progress():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "TRUTH_REPAIR",
        "before": state(["P1"], ["I1"], ["A"], 2, 4),
        "after": state(["P1", "P2"], ["I1", "I2"], ["A", "B"], 3, 6),
        "target_truth_obligations": ["P1"],
        "countermodel_receipts": [receipt("canonical/verification/COUNTERMODEL.json")],
    }
    out = compile_result(doc)
    assert out["status"] == "ADMIT_TRUTH_REPAIR_NOT_PROGRESS"
    assert out["admitted"] is True
    assert out["counts_as_progress"] is False
    assert out["recompute_required"] is True
    assert out["introduced_truth_obligations"] == ["P2"]

def test_progress_cannot_introduce_new_truth_obligation():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": state(["P1"], ["I1", "I2"], ["A"], 2, 4),
        "after": state(["P1", "P2"], ["I1"], [], 1, 1),
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [receipt()],
    }
    out = compile_result(doc)
    assert out["status"] == "REJECT_NONCONTRACTING_PROGRESS"

def test_missing_content_addressed_evidence_fails_closed():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": state(["P1"], ["I1", "I2"], ["A"], 2, 4),
        "after": state(["P1"], ["I1"], ["A"], 2, 4),
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [],
    }
    out = compile_result(doc)
    assert out["status"] == "FAIL_CLOSED"

def test_target_must_bind_current_open_truth():
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": state(["P1"], ["I1", "I2"], ["A"], 2, 4),
        "after": state(["P1"], ["I1"], ["A"], 2, 4),
        "target_truth_obligations": ["NOT_OPEN"],
        "evidence_receipts": [receipt()],
    }
    out = compile_result(doc)
    assert out["status"] == "FAIL_CLOSED"
