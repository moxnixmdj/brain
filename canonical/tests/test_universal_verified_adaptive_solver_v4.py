import json
from hashlib import sha256

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v4 import run
from canonical.runtime.executable_skill_program_v7 import program_digest


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


def bind(root, problem, cid):
    cap = next(x for x in problem["capabilities"] if x["id"] == cid)
    verifier_id, payload = active(cap)
    payload_sha = sha256(canon(payload).encode()).hexdigest()
    rd = {
        "schema": BINDING_SCHEMA,
        "capability_id": cid,
        "task_contract_sha256": task_contract_sha256(problem),
        "requires": sorted(cap["requires"]),
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[verifier_id],
        "provided_effects": sorted(cap["provides"]),
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = write_json(root, f"canonical/verification/{cid}-effect.json", rd)
    vd = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "capability_id": cid,
        "task_contract_sha256": rd["task_contract_sha256"],
        "requires": sorted(cap["requires"]),
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[verifier_id],
        "provided_effects": sorted(cap["provides"]),
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "independent-test",
    }
    vr = write_json(root, f"canonical/verification/{cid}-effect-verify.json", vd)
    cap["effect_semantics_binding"] = {"receipt": rr, "verification": vr}


def exact_cap(cid, cost, expected):
    provides = ["GOAL"]
    return {
        "id": cid,
        "requires": [],
        "provides": provides,
        "cost": cost,
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


def finite_dead_cap(cid, cost):
    provides = ["GOAL"]
    return {
        "id": cid,
        "requires": [],
        "provides": provides,
        "cost": cost,
        "result_fields": [],
        "action": {
            "type": "verified_policy",
            "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
            "verifier_payload": {
                "program": {
                    "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                    "fields": [
                        {"id": "x", "type": "integer", "dimension": "score", "source": "candidate"},
                    ],
                    "accept_when": {
                        "op": "ge",
                        "left": {"op": "ref", "id": "x"},
                        "right": {"op": "const", "type": "number", "dimension": "score", "value": 10},
                    },
                },
                "trusted_values": {},
            },
            "proposal_generator_id": "TYPED_ACCEPTANCE_FINITE_SEARCH_V1",
            "proposal_generator_payload": {
                "candidate_domains": {"x": [0, 1, 2]},
                "max_candidates": 10,
            },
            "effect_contract": {
                "effects": provides,
                "verifier_success_condition": SUCCESS_CONDITIONS["TYPED_ACCEPTANCE_PROGRAM_V1"],
            },
        },
    }


def problem(caps):
    return {
        "task_id": "demo",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": caps,
    }


def bind_all(root, p):
    for cap in p["capabilities"]:
        bind(root, p, cap["id"])


def test_authenticated_exact_route_solves_and_has_global_lineage(tmp_path):
    p = problem([exact_cap("solve", 1, {"answer": 42})])
    bind_all(tmp_path, p)
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is True, out
    assert out["state_target_verdict"]["pass"] is True
    assert out["trace"][0]["effect_semantics_authenticated"] is True


def test_complete_finite_failure_falsifies_route_then_fallback_solves(tmp_path):
    p = problem([
        finite_dead_cap("dead", 1),
        exact_cap("fallback", 2, {"answer": 42}),
    ])
    bind_all(tmp_path, p)
    out = run(
        p,
        proposal_packets={"fallback": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is True, out
    assert "dead" in out["falsified_capability_ids"]
    assert out["trace"][0]["capability_id"] == "fallback"


def test_bad_external_proposal_defers_route_not_falsifies_it(tmp_path):
    p = problem([
        exact_cap("proposal-route", 1, {"answer": 42}),
        exact_cap("fallback", 2, {"answer": 42}),
    ])
    bind_all(tmp_path, p)
    out = run(
        p,
        proposal_packets={
            "proposal-route": [{"candidate": {"answer": 41}}],
            "fallback": [{"candidate": {"answer": 42}}],
        },
        repo_root=tmp_path,
    )
    assert out["pass"] is True, out
    assert "proposal-route" in out["deferred_capability_ids"]
    assert "proposal-route" not in out["falsified_capability_ids"]


def test_missing_effect_semantics_binding_fails_closed(tmp_path):
    p = problem([exact_cap("solve", 1, {"answer": 42})])
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert "EFFECT_SEMANTICS_BINDING_REQUIRED" in out["reason"]


def test_verified_effect_tool_executes_and_readback_mints_bound_effect(tmp_path):
    provides = ["GOAL"]
    cap = {
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
    p = problem([cap])
    bind_all(tmp_path, p)
    effect_root = tmp_path / "effects"
    effect_root.mkdir()
    out = run(
        p,
        proposal_packets={"write": [{"candidate_values": {"name": "Alice", "passed": True}}]},
        repo_root=tmp_path,
        effect_root=str(effect_root),
    )
    assert out["pass"] is True, out
    assert out["trace"][0]["effect_outcome_sha256"]
    assert (effect_root / "mission" / "receipts" / "result.json").is_file()


def test_success_without_independent_episode_receipt_does_not_learn(tmp_path):
    p = problem([exact_cap("solve", 1, {"answer": 42})])
    bind_all(tmp_path, p)
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"
    assert out["skill_candidate"] is None
    assert out["current_episode_verified"] is False


def test_repeated_independently_verified_success_induces_candidate_only(tmp_path):
    p = problem([exact_cap("solve", 1, {"answer": 42})])
    bind_all(tmp_path, p)
    steps = [{"op": "solve", "inputs": [], "outputs": ["GOAL"]}]
    digest = program_digest(
        steps=steps,
        preconditions=[],
        postconditions=["GOAL"],
        invalidators=[],
    )
    prior = {
        "episode_id": "prior",
        "scope_id": "scope",
        "steps": steps,
        "preconditions": [],
        "postconditions": ["GOAL"],
        "invalidators": [],
        "verification_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "behavior_verified": True,
            "episode_id": "prior",
            "scope_id": "scope",
            "program_sha256": digest,
            "receipt_id": "prior-r",
        },
    }
    receipt = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "behavior_verified": True,
        "episode_id": "current",
        "scope_id": "scope",
        "program_sha256": digest,
        "receipt_id": "current-r",
    }
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
        episode_id="current",
        scope_id="scope",
        episode_verification_receipt=receipt,
        prior_verified_episodes=[prior],
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__SKILL_CANDIDATE_READY"
    assert out["current_episode_verified"] is True
    assert out["skill_candidate"]["status"] == "EXECUTABLE_SKILL_CANDIDATE_ONLY"
    assert out["skill_candidate_reuse_authorized"] is False


def test_effectful_partial_progress_requires_authenticated_resume_before_later_proposal(tmp_path):
    intermediate = ["INTERMEDIATE"]
    effect_cap = {
        "id": "write-first",
        "requires": [],
        "provides": intermediate,
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_effect_tool",
            "pre_verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
            "pre_verifier_payload": {
                "program": {
                    "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                    "fields": [
                        {"id": "ok", "type": "boolean", "dimension": "dimensionless", "source": "candidate"},
                    ],
                    "accept_when": {"op": "ref", "id": "ok"},
                },
                "trusted_values": {},
            },
            "executor_id": "H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
            "executor_payload": {
                "tool_id": "JSON_RECEIPT_WRITER_V1",
                "sandbox_rel": "partial",
            },
            "effect_contract": {
                "effects": intermediate,
                "verifier_success_condition": SUCCESS_CONDITIONS["TYPED_ACCEPTANCE_PROGRAM_V1"],
            },
        },
    }
    final_cap = {
        "id": "finish-reasoning",
        "requires": ["INTERMEDIATE"],
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
    p = problem([effect_cap, final_cap])
    bind_all(tmp_path, p)
    effect_root = tmp_path / "effects-resume"
    effect_root.mkdir()
    out = run(
        p,
        proposal_packets={
            "write-first": [{"candidate_values": {"ok": True}}],
        },
        repo_root=tmp_path,
        effect_root=str(effect_root),
    )
    assert out["pass"] is False
    assert out["status"] == "AUTHENTICATED_RESUME_REQUIRED_AFTER_PARTIAL_EFFECTFUL_PROGRESS"
    assert out["state_capsule_head_hash"]
    assert out["next_required_input"]["capability_id"] == "finish-reasoning"
