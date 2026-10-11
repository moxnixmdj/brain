import json

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA, BINDING_VERIFY_SCHEMA, task_contract_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v12 import run
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def save(root, rel, doc):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    path.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def make_problem():
    return {
        "task_id": "growth-demo",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [],
    }


def make_capability(root, problem):
    action = {
        "type": "verified_policy",
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload": {"expected": {"answer": 42}},
        "effect_contract": {
            "effects": ["GOAL"],
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        },
    }
    expected = {
        "capability_id": "new-route",
        "task_contract_sha256": task_contract_sha256(problem),
        "requires": [],
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload_sha256": v1._digest(action["verifier_payload"]),
        "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        "provided_effects": ["GOAL"],
    }
    rd = {
        "schema": BINDING_SCHEMA,
        **expected,
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = save(root, "canonical/verification/growth-effect.json", rd)
    vd = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        **expected,
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "growth-test-verifier",
    }
    vr = save(root, "canonical/verification/growth-effect-verify.json", vd)
    return {
        "id": "new-route",
        "requires": [],
        "provides": ["GOAL"],
        "cost": 1,
        "result_fields": [],
        "action": action,
        "effect_semantics_binding": {"receipt": rr, "verification": vr},
    }


def test_zero_graph_can_expand_and_solve(tmp_path):
    problem = make_problem()
    cap = make_capability(tmp_path, problem)

    def expander(request, index, current_problem):
        return {"source_id": "test-expander", "capabilities": [cap]}

    def proposer(request, index, prior):
        return {"candidate": {"answer": 42}}

    out = run(
        problem,
        repo_root=tmp_path,
        capability_expander=expander,
        max_capability_expansions=1,
        proposal_provider=proposer,
        proposal_provider_max_candidates=1,
    )
    assert out["pass"] is True, out
    assert out["verified_facts"] == ["GOAL"]
    assert out["expanded_capability_ids"] == ["new-route"]
    assert out["capability_expansion_attempts"][0]["status"] == "EXPANSION_ADMITTED"
    provenance = out["acquisition_donor_provenance"]
    assert provenance["used"] is True
    assert provenance["capability_expansion_source_ids"] == ["test-expander"]
    assert provenance["runtime_credit_authority"] is False
    assert provenance["transfer_gate_required_before_reuse"] is True



def test_unauthenticated_expansion_is_not_admitted(tmp_path):
    problem = make_problem()
    cap = make_capability(tmp_path, problem)
    cap.pop("effect_semantics_binding")

    def expander(request, index, current_problem):
        return {"capabilities": [cap]}

    out = run(
        problem,
        repo_root=tmp_path,
        capability_expander=expander,
        max_capability_expansions=1,
    )
    assert out["pass"] is False
    assert out["expanded_capability_ids"] == []
    attempt = out["capability_expansion_attempts"][0]
    assert attempt["status"] == "NO_AUTHENTICATED_CAPABILITY_ADMITTED"
    assert attempt["rejected"]


def test_value_dependent_dynamic_expansion_waits_for_bound_semantics(tmp_path):
    problem = make_problem()
    cap = make_capability(tmp_path, problem)
    cap["result_fields"] = ["answer"]

    def expander(request, index, current_problem):
        return {"capabilities": [cap]}

    out = run(
        problem,
        repo_root=tmp_path,
        capability_expander=expander,
        max_capability_expansions=1,
    )
    assert out["pass"] is False
    assert out["expanded_capability_ids"] == []
    reasons = [
        row["reason"]
        for row in out["capability_expansion_attempts"][0]["rejected"]
    ]
    assert any("EXPANDED_DYNAMIC_VALUE_SEMANTICS_NOT_ADMITTED_V1" in x for x in reasons)
