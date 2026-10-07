import json
from hashlib import sha256

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v4 import run as run_v4
from canonical.runtime.universal_verified_adaptive_solver_v5 import run as run_v5
from canonical.runtime.universal_solver_resume_authenticator_v1 import make_resume_state


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def active(cap):
    a = cap["action"]
    if a.get("type") == "verified_effect_tool":
        return a["pre_verifier_id"], a["pre_verifier_payload"]
    return a["verifier_id"], a["verifier_payload"]


def bind(root, problem, cap):
    vid, payload = active(cap)
    payload_sha = sha256(canon(payload).encode()).hexdigest()
    rd = {
        "schema": BINDING_SCHEMA,
        "capability_id": cap["id"],
        "task_contract_sha256": task_contract_sha256(problem),
        "requires": sorted(cap["requires"]),
        "verifier_id": vid,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[vid],
        "provided_effects": sorted(cap["provides"]),
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = write_json(root, "canonical/verification/" + cap["id"] + ".json", rd)
    vd = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "capability_id": cap["id"],
        "task_contract_sha256": rd["task_contract_sha256"],
        "requires": sorted(cap["requires"]),
        "verifier_id": vid,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[vid],
        "provided_effects": sorted(cap["provides"]),
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "v5-test",
    }
    vr = write_json(root, "canonical/verification/" + cap["id"] + "-verify.json", vd)
    cap["effect_semantics_binding"] = {"receipt": rr, "verification": vr}


def effect_cap(cid="write", requires=None, provides=None, sandbox="mission"):
    requires = list(requires or [])
    provides = list(provides or ["FILE_WRITTEN"])
    return {
        "id": cid,
        "requires": requires,
        "provides": provides,
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_effect_tool",
            "pre_verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
            "pre_verifier_payload": {
                "program": {
                    "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                    "fields": [
                        {"id": "name", "type": "enum", "dimension": "dimensionless", "source": "candidate"},
                        {"id": "passed", "type": "boolean", "dimension": "dimensionless", "source": "candidate"},
                    ],
                    "accept_when": {
                        "op": "and",
                        "args": [
                            {
                                "op": "eq",
                                "left": {"op": "ref", "id": "name"},
                                "right": {"op": "const", "type": "enum", "dimension": "dimensionless", "value": "Alice"},
                            },
                            {"op": "ref", "id": "passed"},
                        ],
                    },
                },
                "trusted_values": {},
            },
            "executor_id": "H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
            "executor_payload": {
                "tool_id": "JSON_RECEIPT_WRITER_V1",
                "sandbox_rel": sandbox,
            },
            "effect_contract": {
                "effects": provides,
                "verifier_success_condition": SUCCESS_CONDITIONS["TYPED_ACCEPTANCE_PROGRAM_V1"],
            },
        },
    }


def exact_cap():
    return {
        "id": "finish",
        "requires": ["FILE_WRITTEN"],
        "provides": ["GOAL"],
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": {"answer": 42}},
            "effect_contract": {
                "effects": ["GOAL"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def problem(root):
    w = effect_cap()
    f = exact_cap()
    p = {
        "task_id": "resume-v5",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [w, f],
    }
    bind(root, p, w)
    bind(root, p, f)
    return p


def partial(root):
    p = problem(root)
    er = root / "effects"
    er.mkdir()
    out = run_v4(
        p,
        proposal_packets={"write": [{"candidate_values": {"name": "Alice", "passed": True}}]},
        repo_root=root,
        effect_root=str(er),
    )
    assert out["status"] == "AUTHENTICATED_RESUME_REQUIRED_AFTER_PARTIAL_EFFECTFUL_PROGRESS", out
    return p, er, out, make_resume_state(p, out)


def test_resume_finishes_without_replaying_prior_effect(tmp_path):
    p, er, partial_out, state = partial(tmp_path)
    target = er / "mission" / "receipts" / "result.json"
    before = target.read_bytes()
    before_hash = sha256(before).hexdigest()

    out = run_v5(
        p,
        resume_state=state,
        proposal_packets={"finish": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
        effect_root=er,
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"
    assert [x["capability_id"] for x in out["trace"]] == ["write", "finish"]
    assert sha256(target.read_bytes()).hexdigest() == before_hash
    assert len(out["trace"]) == len(partial_out["trace"]) + 1


def test_resume_rejects_mutated_effect_world_before_continuing(tmp_path):
    p, er, _, state = partial(tmp_path)
    target = er / "mission" / "receipts" / "result.json"
    target.write_text('{"changed":true}')
    out = run_v5(
        p,
        resume_state=state,
        proposal_packets={"finish": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
        effect_root=er,
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__RESUME_AUTHENTICATION_FAILED"


def test_resume_without_new_proposal_preserves_state_and_requests_new_authenticated_resume(tmp_path):
    p, er, _, state = partial(tmp_path)
    out = run_v5(
        p,
        resume_state=state,
        proposal_packets={},
        repo_root=tmp_path,
        effect_root=er,
    )
    assert out["pass"] is False
    assert out["status"] == "AUTHENTICATED_RESUME_REQUIRED_AFTER_PARTIAL_EFFECTFUL_PROGRESS"
    assert out["verified_facts"] == ["FILE_WRITTEN"]
    assert out["next_required_input"]["capability_id"] == "finish"


def test_fresh_v5_delegates_to_v4_and_stops_safely_after_effect(tmp_path):
    p = problem(tmp_path)
    er = tmp_path / "effects-fresh"
    er.mkdir()
    out = run_v5(
        p,
        proposal_packets={"write": [{"candidate_values": {"name": "Alice", "passed": True}}]},
        repo_root=tmp_path,
        effect_root=er,
    )
    assert out["status"] == "AUTHENTICATED_RESUME_REQUIRED_AFTER_PARTIAL_EFFECTFUL_PROGRESS"
    assert out["state_capsule_head_hash"]
