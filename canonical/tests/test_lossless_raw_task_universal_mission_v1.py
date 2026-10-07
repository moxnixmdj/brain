import json

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v6 import run as run_v6
from canonical.runtime.universal_solver_value_state_v1 import (
    initialize as initialize_value_state,
    append_verified_transition as append_value_transition,
    resolve_effect_results,
)
from canonical.runtime.resolved_capability_semantics_authenticator_v1 import (
    expected_binding,
    BINDING_SCHEMA,
    VERIFY_SCHEMA,
    CLAIM,
)
from canonical.runtime.lossless_raw_task_universal_mission_v1 import (
    compile_mission,
    FINAL_CAPABILITY_ID,
)
from canonical.runtime.lossless_raw_task_acceptance_gate_v1 import (
    RECEIPT_SCHEMA as ACCEPT_SCHEMA,
    VERIFY_SCHEMA as ACCEPT_VERIFY_SCHEMA,
)


CANDIDATE_SHA = "a" * 64


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def semantics_pair(root, name, expected):
    rd = {"schema": BINDING_SCHEMA, **expected, "pass": True, "claim": CLAIM}
    rr = write_json(root, "canonical/verification/" + name + ".json", rd)
    vd = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        **expected,
        "pass": True,
        "independent_verified": True,
        "effect_semantics_verified": True,
        "result_field_semantics_verified": True,
        "trusted_substitution_semantics_verified": True,
        "independent_verifier_id": "raw-task-test-verifier",
    }
    vr = write_json(root, "canonical/verification/" + name + "-verify.json", vd)
    return {"receipt": rr, "verification": vr}


def candidate_cap():
    return {
        "id": "MAKE_CANDIDATE",
        "requires": [],
        "provides": ["CANDIDATE_READY"],
        "cost": 1,
        "result_fields": ["candidate_sha256"],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {
                "expected": {"candidate_sha256": CANDIDATE_SHA},
            },
            "effect_contract": {
                "effects": ["CANDIDATE_READY"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def compile_problem(root, task_text="Write a concise report. Include the word alpha."):
    out = compile_mission(
        task_text,
        source_id="user-task",
        candidate_capabilities=[candidate_cap()],
        candidate_effect="CANDIDATE_READY",
        candidate_sha256_field="candidate_sha256",
        repo_root=str(root),
        task_id="raw-demo",
    )
    assert out["pass"] is True, out
    return out


def producer_trace():
    cap = candidate_cap()
    proposal = {"candidate": {"candidate_sha256": CANDIDATE_SHA}}
    verdict = v1.BUILTIN_VERIFIERS["EXACT_JSON_V1"](
        cap["action"]["verifier_payload"], proposal
    )
    assert verdict["pass"] is True
    return {
        "capability_id": cap["id"],
        "cycle": 0,
        "verifier_id": "EXACT_JSON_V1",
        "action_contract_sha256": v1._digest(cap["action"]),
        "proposal_sha256": v1._digest(proposal),
        "proof_digest": verdict["proof_digest"],
        "verified_output": verdict["verified_output"],
        "effect_outcome": None,
        "effect_outcome_sha256": None,
    }


def acceptance_receipts(root, contract, *, omit_last=False, candidate_sha=CANDIDATE_SHA):
    pairs = []
    obligations = contract["acceptance_contract"]["obligations"]
    selected = obligations[:-1] if omit_last else obligations
    for i, row in enumerate(selected):
        rd = {
            "schema": ACCEPT_SCHEMA,
            "task_contract_sha256": contract["task_contract_sha256"],
            "task_sha256": contract["task_sha256"],
            "obligation_id": row["obligation_id"],
            "segment_sha256": row["segment_sha256"],
            "candidate_sha256": candidate_sha,
            "accepted": True,
            "verifier_class": "DETERMINISTIC",
            "verifier_id": "raw-obligation-test-" + str(i),
        }
        rr = write_json(
            root,
            "canonical/verification/raw-accept-" + str(i) + ".json",
            rd,
        )
        vd = {
            "schema": ACCEPT_VERIFY_SCHEMA,
            "subject_git_blob_sha": rr["git_blob_sha"],
            "task_contract_sha256": contract["task_contract_sha256"],
            "task_sha256": contract["task_sha256"],
            "obligation_id": row["obligation_id"],
            "segment_sha256": row["segment_sha256"],
            "candidate_sha256": candidate_sha,
            "verifier_class": rd["verifier_class"],
            "verifier_id": rd["verifier_id"],
            "accepted": True,
            "pass": True,
            "independent_verified": True,
            "acceptance_semantics_verified": True,
            "independent_verifier_id": "independent-accept-" + str(i),
        }
        vr = write_json(
            root,
            "canonical/verification/raw-accept-" + str(i) + "-verify.json",
            vd,
        )
        pairs.append({"receipt": rr, "verification": vr})
    return pairs


def resolved_semantics(root, compiled):
    p = compiled["problem"]
    state0 = initialize_value_state(p)
    producer = p["capabilities"][0]
    producer_expected = expected_binding(p, producer, producer["action"], state0)
    producer_pair = semantics_pair(root, "candidate-semantics", producer_expected)

    state1 = append_value_transition(
        state0,
        capability=producer,
        trace_row=producer_trace(),
    )
    final = next(x for x in p["capabilities"] if x["id"] == FINAL_CAPABILITY_ID)
    resolved_final = resolve_effect_results(
        state1,
        capability=final,
        template=final["action"],
    )
    final_expected = expected_binding(p, final, resolved_final, state1)
    final_pair = semantics_pair(root, "final-accept-semantics", final_expected)
    return {
        producer["id"]: [producer_pair],
        final["id"]: [final_pair],
    }


def test_every_raw_segment_acceptance_closes_final_task_target(tmp_path):
    compiled = compile_problem(tmp_path)
    contract = compiled["raw_task_contract"]
    out = run_v6(
        compiled["problem"],
        proposal_packets={
            "MAKE_CANDIDATE": [
                {"candidate": {"candidate_sha256": CANDIDATE_SHA}}
            ],
            FINAL_CAPABILITY_ID: [
                {
                    "obligation_receipts": acceptance_receipts(
                        tmp_path, contract
                    )
                }
            ],
        },
        repo_root=tmp_path,
        resolved_semantics_bindings=resolved_semantics(tmp_path, compiled),
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"
    assert out["verified_facts"] == ["CANDIDATE_READY", "RAW_TASK_ACCEPTED"]
    assert out["trace"][1]["resolved_action"]["verifier_payload"]["candidate_sha256"] == CANDIDATE_SHA
    assert out["verified_target_values"]["values"]["RAW_TASK_ACCEPTED"]["result"]["candidate_sha256"] == CANDIDATE_SHA


def test_missing_one_raw_obligation_never_mints_task_accepted(tmp_path):
    compiled = compile_problem(tmp_path)
    contract = compiled["raw_task_contract"]
    out = run_v6(
        compiled["problem"],
        proposal_packets={
            "MAKE_CANDIDATE": [
                {"candidate": {"candidate_sha256": CANDIDATE_SHA}}
            ],
            FINAL_CAPABILITY_ID: [
                {
                    "obligation_receipts": acceptance_receipts(
                        tmp_path, contract, omit_last=True
                    )
                }
            ],
        },
        repo_root=tmp_path,
        resolved_semantics_bindings=resolved_semantics(tmp_path, compiled),
    )
    assert out["pass"] is False
    assert "RAW_TASK_ACCEPTED" not in out["verified_facts"]


def test_acceptance_receipts_for_different_candidate_hash_cannot_close_task(tmp_path):
    compiled = compile_problem(tmp_path)
    contract = compiled["raw_task_contract"]
    out = run_v6(
        compiled["problem"],
        proposal_packets={
            "MAKE_CANDIDATE": [
                {"candidate": {"candidate_sha256": CANDIDATE_SHA}}
            ],
            FINAL_CAPABILITY_ID: [
                {
                    "obligation_receipts": acceptance_receipts(
                        tmp_path,
                        contract,
                        candidate_sha="b" * 64,
                    )
                }
            ],
        },
        repo_root=tmp_path,
        resolved_semantics_bindings=resolved_semantics(tmp_path, compiled),
    )
    assert out["pass"] is False
    assert "RAW_TASK_ACCEPTED" not in out["verified_facts"]


def test_routing_contract_has_zero_success_authority(tmp_path):
    compiled = compile_problem(tmp_path, "Do something difficult and ambiguous.")
    contract = compiled["raw_task_contract"]
    assert compiled["routing_success_authority"] is False
    assert contract["routing_contract"]["success_authority"] is False
    assert contract["acceptance_contract"]["raw_source_is_final_semantic_reference"] is True
    assert len(contract["acceptance_contract"]["required_obligation_ids"]) >= 1
