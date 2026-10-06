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

def receipt(before, after, targets, effect, path="canonical/verification/X.json"):
    return {
        "path": path,
        "git_blob_sha": A40,
        "before_state_sha256": before["state_sha256"],
        "after_state_sha256": after["state_sha256"],
        "target_truth_obligations_sha256": sha256_json(sorted(targets)),
        "effect_kind": effect,
    }

def test_direct_truth_closure_is_progress():
    before = state(["P1", "P2"], ["I1", "I2"], ["A", "B"], 3, 7)
    after = state(["P2"], ["I1", "I2"], ["A", "B"], 3, 7)
    targets = ["P1"]
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": targets,
        "evidence_receipts": [receipt(before, after, targets, "TRUTH_CLOSURE")],
    }
    out = compile_result(doc)
    assert out["status"] == "ADMIT_TERMINAL_CONTRACTING_PROGRESS"
    assert out["counts_as_progress"] is True
    assert out["closed_truth_obligations"] == ["P1"]

def test_shared_interface_contraction_is_progress_even_without_terminal_credit():
    before = state(["P1", "P2"], ["I1", "I2", "I3"], ["A", "B"], 4, 9)
    after = state(["P1", "P2"], ["I1", "I2"], ["A", "B"], 4, 9)
    targets = ["P1", "P2"]
    doc = {
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": targets,
        "evidence_receipts": [receipt(before, after, targets, "INTERFACE_CONTRACTION")],
    }
    out = compile_result(doc)
    assert out["status"] == "ADMIT_TERMINAL_CONTRACTING_PROGRESS"
    assert out["before_potential"] == [2, 3, 4, 2, 9]
    assert out["after_potential"] == [2, 2, 4, 2, 9]

def test_prerequisite_contraction_is_progress():
    before = state(["P1"], ["I1"], ["A", "B", "C"], 2, 6)
    after = state(["P1"], ["I1"], ["A"], 2, 6)
    targets = ["P1"]
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": targets,
        "evidence_receipts": [receipt(before, after, targets, "PREREQUISITE_CONTRACTION")],
    })
    assert out["status"] == "ADMIT_TERMINAL_CONTRACTING_PROGRESS"

def test_prerequisite_chain_growth_without_contraction_is_rejected():
    before = state(["P1"], ["I1"], ["A"], 2, 4)
    after = state(["P1"], ["I1"], ["A", "B"], 2, 5)
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [],
    })
    assert out["status"] == "REJECT_NONCONTRACTING_PROGRESS"
    assert out["counts_as_progress"] is False

def test_compiler_repackaging_with_identical_potential_is_rejected():
    before = state(["P1"], ["I1"], ["A"], 2, 4)
    after = state(["P1"], ["I1"], ["RENAMED_A"], 2, 4)
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [],
    })
    assert out["status"] == "REJECT_NONCONTRACTING_PROGRESS"

def test_truth_repair_may_reopen_work_but_never_counts_as_progress():
    before = state(["P1"], ["I1"], ["A"], 2, 4)
    after = state(["P1", "P2"], ["I1", "I2"], ["A", "B"], 3, 6)
    targets = ["P1"]
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "TRUTH_REPAIR",
        "before": before,
        "after": after,
        "target_truth_obligations": targets,
        "countermodel_receipts": [
            receipt(before, after, targets, "TRUTH_REPAIR", "canonical/verification/COUNTERMODEL.json")
        ],
    })
    assert out["status"] == "ADMIT_TRUTH_REPAIR_NOT_PROGRESS"
    assert out["admitted"] is True
    assert out["counts_as_progress"] is False
    assert out["recompute_required"] is True
    assert out["introduced_truth_obligations"] == ["P2"]

def test_progress_cannot_introduce_new_truth_obligation():
    before = state(["P1"], ["I1", "I2"], ["A"], 2, 4)
    after = state(["P1", "P2"], ["I1"], [], 1, 1)
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [],
    })
    assert out["status"] == "REJECT_NONCONTRACTING_PROGRESS"

def test_missing_content_addressed_evidence_fails_closed():
    before = state(["P1"], ["I1", "I2"], ["A"], 2, 4)
    after = state(["P1"], ["I1"], ["A"], 1, 4)
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": ["P1"],
        "evidence_receipts": [],
    })
    assert out["status"] == "FAIL_CLOSED"

def test_unrelated_receipt_cannot_authorize_progress():
    before = state(["P1"], ["I1", "I2"], ["A"], 2, 4)
    after = state(["P1"], ["I1"], ["A"], 2, 4)
    after["active_causal_interfaces"] = ["I1"]
    after["state_sha256"] = sha256_json({
        "schema": STATE_SCHEMA,
        "open_truth_obligations": ["P1"],
        "active_causal_interfaces": ["I1"],
        "open_prerequisites": ["A"],
        "max_open_causal_depth": 2,
        "open_proof_node_count": 4,
    })
    targets = ["P1"]
    bad = receipt(before, after, targets, "INTERFACE_CONTRACTION")
    bad["before_state_sha256"] = "b" * 64
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": targets,
        "evidence_receipts": [bad],
    })
    assert out["status"] == "FAIL_CLOSED"
    assert "EVIDENCE_RECEIPTS_BEFORE_STATE_BINDING_MISMATCH" in out["errors"]

def test_wrong_effect_kind_fails_closed():
    before = state(["P1"], ["I1", "I2"], ["A"], 2, 4)
    after = state(["P1"], ["I1"], ["A"], 2, 4)
    targets = ["P1"]
    bad = receipt(before, after, targets, "TRUTH_CLOSURE")
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": targets,
        "evidence_receipts": [bad],
    })
    assert out["status"] == "FAIL_CLOSED"
    assert "EVIDENCE_RECEIPTS_EFFECT_KIND_MISMATCH" in out["errors"]

def test_target_must_bind_current_open_truth():
    before = state(["P1"], ["I1", "I2"], ["A"], 2, 4)
    after = state(["P1"], ["I1"], ["A"], 2, 4)
    out = compile_result({
        "schema": INPUT_SCHEMA,
        "kind": "PROGRESS",
        "before": before,
        "after": after,
        "target_truth_obligations": ["NOT_OPEN"],
        "evidence_receipts": [],
    })
    assert out["status"] == "FAIL_CLOSED"
