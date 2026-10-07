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
from canonical.runtime.universal_solver_resume_authenticator_v1 import (
    authenticate,
    make_resume_state,
)


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
        "independent_verifier_id": "resume-test-verifier",
    }
    vr = write_json(root, "canonical/verification/" + cap["id"] + "-verify.json", vd)
    cap["effect_semantics_binding"] = {"receipt": rr, "verification": vr}


def exact_cap(cid, requires, provides, expected):
    return {
        "id": cid,
        "requires": requires,
        "provides": provides,
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": expected},
            "effect_contract": {
                "effects": provides,
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def effect_cap():
    provides = ["FILE_WRITTEN"]
    return {
        "id": "write",
        "requires": [],
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
                "sandbox_rel": "mission",
            },
            "effect_contract": {
                "effects": provides,
                "verifier_success_condition": SUCCESS_CONDITIONS["TYPED_ACCEPTANCE_PROGRAM_V1"],
            },
        },
    }


def partial_problem(root):
    w = effect_cap()
    f = exact_cap("finish", ["FILE_WRITTEN"], ["GOAL"], {"answer": 42})
    p = {
        "task_id": "resume-demo",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [w, f],
    }
    bind(root, p, w)
    bind(root, p, f)
    return p


def produce_partial(root):
    p = partial_problem(root)
    er = root / "effects"
    er.mkdir()
    out = run_v4(
        p,
        proposal_packets={
            "write": [{"candidate_values": {"name": "Alice", "passed": True}}],
        },
        repo_root=root,
        effect_root=str(er),
    )
    assert out["status"] == "AUTHENTICATED_RESUME_REQUIRED_AFTER_PARTIAL_EFFECTFUL_PROGRESS", out
    return p, er, out, make_resume_state(p, out)


def test_partial_effectful_state_authenticates_against_current_world(tmp_path):
    p, er, _, state = produce_partial(tmp_path)
    out = authenticate(p, state, repo_root=tmp_path, effect_root=er)
    assert out["pass"] is True, out
    assert out["verified_facts"] == ["FILE_WRITTEN"]
    assert len(out["reverified_effects"]) == 1


def test_changed_effect_bytes_invalidate_resume(tmp_path):
    p, er, _, state = produce_partial(tmp_path)
    target = er / "mission" / "receipts" / "result.json"
    target.write_text('{"tampered":true}')
    out = authenticate(p, state, repo_root=tmp_path, effect_root=er)
    assert out["pass"] is False
    assert any("CURRENT_EFFECT_WORLD_STATE_MISMATCH" in x for x in out["errors"])


def test_tampered_historical_proposal_invalidates_resume(tmp_path):
    p, er, _, state = produce_partial(tmp_path)
    state["trace"][0]["accepted_proposal"]["candidate_values"]["passed"] = False
    out = authenticate(p, state, repo_root=tmp_path, effect_root=er)
    assert out["pass"] is False


def test_changed_problem_invalidates_resume(tmp_path):
    p, er, _, state = produce_partial(tmp_path)
    changed = json.loads(json.dumps(p))
    changed["task_id"] = "different"
    out = authenticate(changed, state, repo_root=tmp_path, effect_root=er)
    assert out["pass"] is False
    assert "RESUME_PROBLEM_SHA256_MISMATCH" in out["errors"][0]


def test_pure_solved_trace_can_be_reauthenticated_without_effect_root(tmp_path):
    cap = exact_cap("solve", [], ["GOAL"], {"answer": 42})
    p = {
        "task_id": "pure",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [cap],
    }
    bind(tmp_path, p, cap)
    solved = run_v4(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert solved["pass"] is True
    state = make_resume_state(p, solved)
    out = authenticate(p, state, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["target_verdict"]["pass"] is True
