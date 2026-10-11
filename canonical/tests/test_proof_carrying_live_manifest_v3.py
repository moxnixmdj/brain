from __future__ import annotations

import copy

from canonical.runtime.proof_carrying_live_manifest_v3 import (
    candidate_authority_digest,
    canary_receipt_digest,
    compile_manifest,
    replay_receipt_digest,
    route_subject_digest,
    runtime_ack_digest,
    validate_manifest,
    verification_receipt_digest,
    verify_activation_candidate,
)


def h(ch):
    return (ch * 64)[:64]


def route(rid="r1", cap="c1", pred="k=x", exe="exec:x"):
    row = {
        "capability_id": cap,
        "route_id": rid,
        "request_predicate": pred,
        "executor_binding": exe,
        "acceptance_contract": "accept:" + rid,
        "selector_proof_sha256": h("a"),
        "executor_sha256": h("b"),
        "acceptance_contract_sha256": h("c"),
        "dependency_hashes": [h("d")],
        "origin_class": "STATIC_VERIFIED",
        "improvement_receipt": None,
        "runtime_compatible": True,
        "revoked": False,
        "deployable": True,
        "priority": 1,
        "specificity": 1,
    }
    subject = route_subject_digest(row)
    verification = {
        "pass": True,
        "independently_verified": True,
        "verifier_id": "route-verifier",
        "subject_sha256": subject,
        "result_sha256": h("e"),
    }
    verification["sha256"] = verification_receipt_digest(verification)
    authority = {
        "valid": True,
        "manifest_candidate_authority": True,
        "authority_scope": "LIVE_MANIFEST_CANDIDACY",
        "issuer_id": "candidate-authority",
        "subject_sha256": subject,
    }
    authority["sha256"] = candidate_authority_digest(authority)
    row["verification_receipt"] = verification
    row["candidate_authority"] = authority
    return row


def compiled():
    return compile_manifest(
        [route("r1", "c1"), route("r2", "c2", "k=y", "exec:y")],
        verified_deployable_capability_ids=["c1", "c2"],
    )


def activation_inputs(manifest):
    canary = []
    replay = []
    by_id = {x["route_id"]: x for x in manifest["routes"]}
    for rid in manifest["route_ids"]:
        c = {
            "route_id": rid,
            "manifest_sha256": manifest["manifest_sha256"],
            "route_record_sha256": by_id[rid]["route_record_sha256"],
            "pass": True,
            "independently_verified": True,
            "verifier_id": "canary-verifier-" + rid,
            "result_sha256": h("1" if rid == "r1" else "2"),
        }
        c["receipt_sha256"] = canary_receipt_digest(c)
        canary.append(c)
        r = {
            "route_id": rid,
            "manifest_sha256": manifest["manifest_sha256"],
            "route_record_sha256": by_id[rid]["route_record_sha256"],
            "pass": True,
            "through_normal_front_door": True,
            "independently_verified": True,
            "verifier_id": "replay-verifier-" + rid,
            "result_sha256": h("3" if rid == "r1" else "4"),
        }
        r["receipt_sha256"] = replay_receipt_digest(r)
        replay.append(r)
    ack = {
        "loaded": True,
        "manifest_sha256": manifest["manifest_sha256"],
        "route_ids": list(manifest["route_ids"]),
        "runtime_instance_sha256": h("5"),
        "deployment_artifact_sha256": h("6"),
    }
    ack["receipt_sha256"] = runtime_ack_digest(ack)
    return canary, ack, replay


def test_compile_and_activation_candidate_never_grants_authority():
    manifest = compiled()
    assert manifest["pass"] is True, manifest
    canary, ack, replay = activation_inputs(manifest)
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is True, out
    assert out["activation_candidate"] is True
    assert out["requires_live_global_authority"] is True
    assert out["activation_authority"] is False
    assert out["promotion_authority"] is False


def test_manifest_self_digest_tamper_fails():
    manifest = compiled()
    manifest["routes"][0]["priority"] = 999
    ok, reason = validate_manifest(manifest)
    assert ok is False
    assert reason == "CANDIDATE_MANIFEST_SELF_DIGEST_MISMATCH"


def test_activation_recomputes_manifest_not_just_supplied_hash():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    manifest["routes"][0]["priority"] = 999
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is False
    assert out["reason"] == "CANDIDATE_MANIFEST_SELF_DIGEST_MISMATCH"


def test_verification_receipt_subject_mismatch_fails_compile():
    row = route()
    row["verification_receipt"]["subject_sha256"] = h("9")
    row["verification_receipt"]["sha256"] = verification_receipt_digest(
        row["verification_receipt"]
    )
    out = compile_manifest([row], verified_deployable_capability_ids=["c1"])
    assert out["pass"] is False
    assert out["detail"] == "VERIFICATION_RECEIPT_INVALID"


def test_verification_receipt_tamper_fails_self_digest():
    row = route()
    row["verification_receipt"]["result_sha256"] = h("9")
    out = compile_manifest([row], verified_deployable_capability_ids=["c1"])
    assert out["pass"] is False
    assert out["detail"] == "VERIFICATION_RECEIPT_SELF_DIGEST_MISMATCH"


def test_candidate_authority_subject_mismatch_fails():
    row = route()
    row["candidate_authority"]["subject_sha256"] = h("9")
    row["candidate_authority"]["sha256"] = candidate_authority_digest(
        row["candidate_authority"]
    )
    out = compile_manifest([row], verified_deployable_capability_ids=["c1"])
    assert out["pass"] is False
    assert out["detail"] == "CANDIDATE_AUTHORITY_INVALID"


def test_active_capability_set_drift_fails():
    out = compile_manifest(
        [route()],
        verified_deployable_capability_ids=["c1", "c2"],
    )
    assert out["pass"] is False
    assert out["reason"] == "VERIFIED_DEPLOYABLE_ACTIVE_SET_DRIFT"


def test_exact_predicate_executor_conflict_fails():
    out = compile_manifest(
        [route("r1", "c1"), route("r2", "c2", "k=x", "exec:other")],
        verified_deployable_capability_ids=["c1", "c2"],
    )
    assert out["pass"] is False
    assert out["reason"] == "AMBIGUOUS_EXACT_PREDICATE_EXECUTOR_CONFLICT"


def test_canary_set_must_be_exact():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary[:1],
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is False
    assert out["reason"] == "CANARY_SET_NOT_EXACT"


def test_canary_receipt_tamper_fails():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    canary[0]["result_sha256"] = h("9")
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is False
    assert out["reason"] == "CANARY_RECEIPT_SELF_DIGEST_MISMATCH"


def test_runtime_ack_route_set_mismatch_fails():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    ack["route_ids"] = ["r1"]
    ack["receipt_sha256"] = runtime_ack_digest(ack)
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is False
    assert out["reason"] == "RUNTIME_ACK_INVALID"


def test_runtime_ack_tamper_fails_self_digest():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    ack["runtime_instance_sha256"] = h("9")
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is False
    assert out["reason"] == "RUNTIME_ACK_SELF_DIGEST_MISMATCH"


def test_replay_must_use_normal_front_door():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    replay[0]["through_normal_front_door"] = False
    replay[0]["receipt_sha256"] = replay_receipt_digest(replay[0])
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is False
    assert out["reason"] == "REPRESENTATIVE_REPLAY_BINDING_INVALID"


def test_replay_route_record_binding_mismatch_fails():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    replay[0]["route_record_sha256"] = h("9")
    replay[0]["receipt_sha256"] = replay_receipt_digest(replay[0])
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256=h("f"),
    )
    assert out["pass"] is False
    assert out["reason"] == "REPRESENTATIVE_REPLAY_BINDING_INVALID"


def test_invalid_last_known_good_fails_closed():
    manifest = compiled()
    canary, ack, replay = activation_inputs(manifest)
    out = verify_activation_candidate(
        manifest,
        canary_receipts=canary,
        runtime_ack=ack,
        replay_receipts=replay,
        previous_live_manifest_sha256="bad",
    )
    assert out["pass"] is False
    assert out["rollback_required"] is True
    assert out["last_known_good_manifest_sha256"] is None


def _canon_sha(value):
    import hashlib
    import json
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def improvement_receipt(rid="rlearn"):
    phase_receipts = {
        name: h(str((i % 9) + 1))
        for i, name in enumerate(
            (
                "understand",
                "plan",
                "compose",
                "act",
                "verify",
                "learn",
                "generalize",
                "compress",
                "reuse",
            )
        )
    }
    phase_outputs = {
        name: h("abcdefghi"[i])
        for i, name in enumerate(phase_receipts)
    }
    core = {
        "episode_id": "learned-episode",
        "subject_sha256": h("7"),
        "route_id": rid,
        "route_manifest_sha256": h("8"),
        "phase_receipt_sha256": phase_receipts,
        "phase_output_sha256": phase_outputs,
        "neighbor_receipt_sha256": [h("1"), h("2")],
        "compression_receipt_sha256": h("3"),
    }
    return {
        "schema": "PROJECT_BRAIN_VERIFIED_IMPROVEMENT_LOOP_V2",
        "pass": True,
        "promotion_candidate": True,
        "promotion_authority": False,
        **core,
        "improvement_receipt_sha256": _canon_sha(core),
    }


def learned_route():
    row = route("rlearn", "clearn", "k=learn", "exec:learn")
    row["origin_class"] = "LEARNED_V2"
    row["improvement_receipt"] = improvement_receipt("rlearn")
    return row


def test_learned_v2_route_requires_exact_self_bound_improvement_receipt():
    out = compile_manifest(
        [learned_route()],
        verified_deployable_capability_ids=["clearn"],
    )
    assert out["pass"] is True, out
    assert out["routes"][0]["origin_class"] == "LEARNED_V2"
    assert out["routes"][0]["improvement_receipt_sha256"] == (
        learned_route()["improvement_receipt"]["improvement_receipt_sha256"]
    )


def test_learned_v2_improvement_receipt_tamper_fails():
    row = learned_route()
    row["improvement_receipt"]["subject_sha256"] = h("9")
    out = compile_manifest(
        [row],
        verified_deployable_capability_ids=["clearn"],
    )
    assert out["pass"] is False
    assert out["detail"] == "IMPROVEMENT_RECEIPT_SELF_DIGEST_MISMATCH"


def test_learned_v2_route_id_mismatch_fails():
    row = learned_route()
    row["improvement_receipt"] = improvement_receipt("other-route")
    out = compile_manifest(
        [row],
        verified_deployable_capability_ids=["clearn"],
    )
    assert out["pass"] is False
    assert out["detail"] == "IMPROVEMENT_ROUTE_ID_MISMATCH"
