from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.runtime import universal_verified_adaptive_solver_v5 as v5
from canonical.runtime import universal_verified_adaptive_solver_v6 as v6

ROOT = Path(__file__).resolve().parents[2]


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(root, rel, doc):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    path.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def problem():
    effect = "TARGET_EFFECT_X"
    return {
        "task_id": "effect-semantics-counterexample",
        "initial_facts": [],
        "target_effects": [effect],
        "capabilities": [{
            "id": "candidate",
            "requires": [],
            "provides": [effect],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "EXACT_JSON_V1",
                "verifier_payload": {"expected": {"answer": 42}},
                "effect_contract": {
                    "effects": [effect],
                    "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
                },
            },
        }],
    }


def author_local_binding(root, p):
    cap = p["capabilities"][0]
    verifier_id = cap["action"]["verifier_id"]
    payload = cap["action"]["verifier_payload"]
    payload_sha = sha256(canon(payload).encode()).hexdigest()
    contract_sha = task_contract_sha256(p)

    receipt = write_json(root, "canonical/verification/local-binding.json", {
        "schema": BINDING_SCHEMA,
        "capability_id": cap["id"],
        "task_contract_sha256": contract_sha,
        "requires": [],
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[verifier_id],
        "provided_effects": cap["provides"],
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    })
    verification = write_json(root, "canonical/verification/local-binding-verify.json", {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": receipt["git_blob_sha"],
        "capability_id": cap["id"],
        "task_contract_sha256": contract_sha,
        "requires": [],
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[verifier_id],
        "provided_effects": cap["provides"],
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "locally-declared-verifier",
    })
    cap["effect_semantics_binding"] = {"receipt": receipt, "verification": verification}
    return verification


def install_exact_root(root):
    src = ROOT / v6.TRUST_ROOT_REL
    dst = root / v6.TRUST_ROOT_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def test_current_v5_accepts_locally_declared_independence_on_fresh_run(tmp_path):
    p = problem()
    author_local_binding(tmp_path, p)
    out = v5.run(
        p,
        proposal_packets={"candidate": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is True, out
    assert "TARGET_EFFECT_X" in out["verified_facts"]


def test_v6_rejects_same_untrusted_verification_blob(tmp_path):
    install_exact_root(tmp_path)
    p = problem()
    verification = author_local_binding(tmp_path, p)
    out = v6.run(
        p,
        proposal_packets={"candidate": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert "UNTRUSTED_EFFECT_SEMANTICS_VERIFICATION_BLOB" in out["reason"]
    assert verification["git_blob_sha"] in out["reason"]


def test_v6_rejects_modified_root_that_adds_local_blob(tmp_path):
    install_exact_root(tmp_path)
    p = problem()
    verification = author_local_binding(tmp_path, p)
    path = tmp_path / v6.TRUST_ROOT_REL
    doc = json.loads(path.read_text())
    doc["trusted_effect_semantics_verification_blobs"] = [verification["git_blob_sha"]]
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")

    out = v6.run(
        p,
        proposal_packets={"candidate": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert "EFFECT_SEMANTICS_TRUST_ROOT_BLOB_MISMATCH" in out["reason"]


def test_v6_rejects_missing_trust_root(tmp_path):
    p = problem()
    author_local_binding(tmp_path, p)
    out = v6.run(
        p,
        proposal_packets={"candidate": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert "EFFECT_SEMANTICS_TRUST_ROOT_UNREADABLE" in out["reason"]
