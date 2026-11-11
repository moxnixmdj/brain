from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
ENVELOPE = ROOT / "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"
EVIDENCE = ROOT / "canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json"
RUNTIME = ROOT / "canonical/runtime/independent_acceptance_model.py"
CERT = ROOT / "canonical/governance/RECOVERY_EXISTING_CONTRACT_FACTORIZATION_AND_CONSERVATIVE_EXTENSION_20261005_V1.json"

OLD_COMMIT = "267f2e37f0d6951cfd6e56328ddc3178d162abff"
OLD_BLOB = "c420b8be1f79a0b06afa98f461f443f53d7fc77a"
CURRENT_BLOB = "710298c5d7154b5a3c2a4a1700420c40cb2fa55a"

PINNED = {
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json": "981c8ac9b66ee7fccf5b531525849e29df9be483",
    "canonical/capabilities/opus55/OPUS55_SCOPED_FAIL_CLOSED_SELF_VERIFICATION_RECOVERY_V1.json": "4f5348949c1c2d8784a056c637f05c865ff389b6",
    "canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json": "800ea1db458ff585431c2efb5dd7b503647b3d28",
    "canonical/runtime/independent_acceptance_model.py": CURRENT_BLOB,
}


def blob_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def blob_path(rel: str) -> str:
    return blob_bytes((ROOT / rel).read_bytes())


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def historical_runtime() -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{OLD_COMMIT}:canonical/runtime/independent_acceptance_model.py"],
        cwd=ROOT,
    )


def assignment_dict(tree: ast.Module, name: str) -> ast.Dict:
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            assert isinstance(node.value, ast.Dict)
            return node.value
    raise AssertionError(name)


def literal_dict(node: ast.Dict) -> dict:
    return ast.literal_eval(node)


def tree_without_named_assignments(tree: ast.Module, names: set[str]) -> str:
    body = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in names:
            continue
        body.append(node)
    return ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)


def test_recovery_gap_is_existing_contract_mapping_not_unnamed_behavior():
    for rel, expected in PINNED.items():
        assert blob_path(rel) == expected, (rel, blob_path(rel), expected)

    registry = load(REGISTRY)
    envelope = load(ENVELOPE)
    cert = load(CERT)

    recovery = next(x for x in envelope["families"] if x["id"] == "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
    assert "Check work creatively" in recovery["useful_behavior"]
    assert "falsify conclusions" in recovery["useful_behavior"]

    contracts = {x["behavior_id"]: x for x in registry["active_contracted_residuals"]}
    pre = contracts["SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"]
    assert "independently of the builder" in pre["required_output_or_action"]
    assert "counterexamples" in pre["required_output_or_action"]

    mapping = registry["family_to_residual_contracts"]["SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"]
    assert mapping == ["TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"]
    assert "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001" not in mapping

    fact = cert["current_registry_fact"]
    assert fact["pre_failure_contract_currently_mapped_to_recovery_family"] is False
    assert cert["accounting"]["acceptance_credit_delta"] == 0
    assert cert["fresh_reality_authority"] is False


def test_current_runtime_is_conservative_extension_on_historically_receipted_domain():
    old = historical_runtime()
    current = RUNTIME.read_bytes()
    assert blob_bytes(old) == OLD_BLOB
    assert blob_bytes(current) == CURRENT_BLOB
    assert old != current

    old_tree = ast.parse(old.decode("utf-8"))
    cur_tree = ast.parse(current.decode("utf-8"))

    names = {"OBLIGATIONS", "COUNTEREXAMPLE_TEMPLATES"}
    assert tree_without_named_assignments(old_tree, names) == tree_without_named_assignments(cur_tree, names)

    old_ob = literal_dict(assignment_dict(old_tree, "OBLIGATIONS"))
    cur_ob = literal_dict(assignment_dict(cur_tree, "OBLIGATIONS"))
    old_tpl = literal_dict(assignment_dict(old_tree, "COUNTEREXAMPLE_TEMPLATES"))
    cur_tpl = literal_dict(assignment_dict(cur_tree, "COUNTEREXAMPLE_TEMPLATES"))

    assert set(old_ob) < set(cur_ob)
    assert set(old_tpl) < set(cur_tpl)
    assert all(cur_ob[k] == v for k, v in old_ob.items())
    assert all(cur_tpl[k] == v for k, v in old_tpl.items())

    evidence = load(EVIDENCE)
    assert evidence["candidate_blob"] == OLD_BLOB
    assert evidence["runner"]["source_blob"] == OLD_BLOB
    assert evidence["runner"]["source_exact_match"] is True
    assert evidence["heldout_selection"]["valid_case"] == "bun-sourcemap-leak"
    assert evidence["integration_rule"] == (
        "MAY_BE_USED_AS_A_NECESSARY_FAIL_CLOSED_TERMINAL_GATE_ONLY__MUST_NOT_BE_TREATED_AS_SUFFICIENT_TERMINAL_AUTHORITY"
    )

    cert = load(CERT)
    extension = cert["current_runtime_conservative_extension_candidate"]
    assert extension["historical_blob"] == OLD_BLOB
    assert extension["current_blob"] == CURRENT_BLOB
    assert extension["historical_and_current_blobs_equal"] is False
    assert cert["hard_nonclaims"]


if __name__ == "__main__":
    test_recovery_gap_is_existing_contract_mapping_not_unnamed_behavior()
    test_current_runtime_is_conservative_extension_on_historically_receipted_domain()
    print("RECOVERY_EXISTING_CONTRACT_FACTORIZATION_PASS")
