from __future__ import annotations

import copy
import math

from canonical.runtime.verified_improvement_loop_v2 import (
    PHASES,
    compression_receipt_digest,
    neighbor_receipt_digest,
    phase_receipt_digest,
    route_manifest_digest,
    verify_loop,
)


def h(ch):
    return (ch * 64)[:64]


def episode():
    episode_id = "episode-1"
    subject = h("a")
    receipts = {}
    previous_output = subject
    previous_receipt = None
    phase_outputs = {}
    for i, phase in enumerate(PHASES):
        row = {
            "episode_id": episode_id,
            "phase": phase,
            "subject_sha256": subject,
            "input_sha256": previous_output,
            "output_sha256": h("bcdef0123"[i]),
            "evidence_sha256": h("456789abc"[i]),
            "pass": True,
            "previous_phase_receipt_sha256": previous_receipt,
        }
        if phase == "verify":
            row.update(
                {
                    "independently_verified": True,
                    "verifier_id": "independent-verifier",
                    "verification_subject_sha256": row["input_sha256"],
                    "verifier_receipt_sha256": h("d"),
                }
            )
        row["receipt_sha256"] = phase_receipt_digest(row)
        receipts[phase] = row
        previous_output = row["output_sha256"]
        previous_receipt = row["receipt_sha256"]
        phase_outputs[phase] = row["output_sha256"]

    compression = {
        "quality_preserved": True,
        "resource_metric_id": "raw_bytes",
        "resource_before": 10,
        "resource_after": 5,
        "behavior_sha256": h("e"),
        "scope_relation_sha256": h("f"),
        "compressed_artifact_sha256": phase_outputs["compress"],
    }
    compression["receipt_sha256"] = compression_receipt_digest(compression)

    route = {
        "route_id": "route-1",
        "episode_id": episode_id,
        "subject_sha256": subject,
        "behavior_sha256": compression["behavior_sha256"],
        "scope_relation_sha256": compression["scope_relation_sha256"],
        "behavior_preservation_verified": True,
        "learn_phase_output_sha256": phase_outputs["learn"],
        "generalize_phase_output_sha256": phase_outputs["generalize"],
        "compress_phase_output_sha256": phase_outputs["compress"],
        "compression_receipt_sha256": compression["receipt_sha256"],
    }
    route["route_manifest_sha256"] = route_manifest_digest(route)

    # The reuse phase is defined to output the final route manifest.
    receipts["reuse"]["output_sha256"] = route["route_manifest_sha256"]
    receipts["reuse"]["receipt_sha256"] = phase_receipt_digest(receipts["reuse"])

    def neighbor(subject_ch, result_ch, verifier):
        row = {
            "route_id": route["route_id"],
            "route_manifest_sha256": route["route_manifest_sha256"],
            "neighbor_subject_sha256": h(subject_ch),
            "behavior_sha256": route["behavior_sha256"],
            "scope_relation_sha256": route["scope_relation_sha256"],
            "pass": True,
            "independently_verified": True,
            "verifier_id": verifier,
            "result_sha256": h(result_ch),
        }
        row["receipt_sha256"] = neighbor_receipt_digest(row)
        return row

    return {
        "episode_id": episode_id,
        "subject_sha256": subject,
        "phase_receipts": receipts,
        "learned_route": route,
        "neighbor_replays": [
            neighbor("1", "2", "neighbor-verifier-a"),
            neighbor("3", "4", "neighbor-verifier-b"),
        ],
        "compression": compression,
    }


def assert_reason(e, reason):
    out = verify_loop(e)
    assert out["pass"] is False, out
    assert out["reason"] == reason, out


def test_complete_subject_bound_loop_is_candidate_not_authority():
    out = verify_loop(episode())
    assert out["pass"] is True, out
    assert out["promotion_candidate"] is True
    assert out["promotion_authority"] is False
    assert out["execution_authority"] is False
    assert out["fresh_reality_authority"] is False


def test_phase_splice_from_other_episode_fails():
    e = episode()
    e["phase_receipts"]["compose"]["episode_id"] = "other"
    e["phase_receipts"]["compose"]["receipt_sha256"] = phase_receipt_digest(
        e["phase_receipts"]["compose"]
    )
    assert_reason(e, "PHASE_EPISODE_BINDING_MISMATCH")


def test_phase_subject_substitution_fails():
    e = episode()
    e["phase_receipts"]["plan"]["subject_sha256"] = h("9")
    e["phase_receipts"]["plan"]["receipt_sha256"] = phase_receipt_digest(
        e["phase_receipts"]["plan"]
    )
    assert_reason(e, "PHASE_SUBJECT_BINDING_MISMATCH")


def test_phase_receipt_tamper_fails_self_digest():
    e = episode()
    e["phase_receipts"]["act"]["evidence_sha256"] = h("9")
    assert_reason(e, "PHASE_RECEIPT_SELF_DIGEST_MISMATCH")


def test_phase_output_input_chain_break_fails():
    e = episode()
    e["phase_receipts"]["generalize"]["input_sha256"] = h("9")
    e["phase_receipts"]["generalize"]["receipt_sha256"] = phase_receipt_digest(
        e["phase_receipts"]["generalize"]
    )
    assert_reason(e, "PHASE_INPUT_OUTPUT_CHAIN_BROKEN")


def test_verify_must_be_independent():
    e = episode()
    e["phase_receipts"]["verify"]["independently_verified"] = False
    e["phase_receipts"]["verify"]["receipt_sha256"] = phase_receipt_digest(
        e["phase_receipts"]["verify"]
    )
    assert_reason(e, "VERIFY_NOT_INDEPENDENT")


def test_verify_subject_must_bind_act_output():
    e = episode()
    e["phase_receipts"]["verify"]["verification_subject_sha256"] = h("9")
    e["phase_receipts"]["verify"]["receipt_sha256"] = phase_receipt_digest(
        e["phase_receipts"]["verify"]
    )
    assert_reason(e, "VERIFY_SUBJECT_BINDING_MISMATCH")


def test_route_must_bind_generalize_output():
    e = episode()
    e["learned_route"]["generalize_phase_output_sha256"] = h("9")
    e["learned_route"]["route_manifest_sha256"] = route_manifest_digest(
        e["learned_route"]
    )
    assert_reason(e, "ROUTE_PHASE_OUTPUT_BINDING_MISMATCH")


def test_reuse_phase_must_output_exact_route_manifest():
    e = episode()
    e["phase_receipts"]["reuse"]["output_sha256"] = h("9")
    e["phase_receipts"]["reuse"]["receipt_sha256"] = phase_receipt_digest(
        e["phase_receipts"]["reuse"]
    )
    assert_reason(e, "REUSE_PHASE_ROUTE_MANIFEST_MISMATCH")


def test_neighbor_must_bind_exact_route_manifest():
    e = episode()
    e["neighbor_replays"][0]["route_manifest_sha256"] = h("9")
    e["neighbor_replays"][0]["receipt_sha256"] = neighbor_receipt_digest(
        e["neighbor_replays"][0]
    )
    assert_reason(e, "NEIGHBOR_ROUTE_MANIFEST_MISMATCH")


def test_neighbor_subjects_must_be_distinct():
    e = episode()
    e["neighbor_replays"][1]["neighbor_subject_sha256"] = e[
        "neighbor_replays"
    ][0]["neighbor_subject_sha256"]
    e["neighbor_replays"][1]["receipt_sha256"] = neighbor_receipt_digest(
        e["neighbor_replays"][1]
    )
    assert_reason(e, "NEIGHBOR_SUBJECT_DUPLICATE")


def test_neighbor_receipt_tamper_fails_self_digest():
    e = episode()
    e["neighbor_replays"][0]["result_sha256"] = h("9")
    assert_reason(e, "NEIGHBOR_RECEIPT_SELF_DIGEST_MISMATCH")


def test_compression_must_bind_compress_phase_output():
    e = episode()
    e["compression"]["compressed_artifact_sha256"] = h("9")
    e["compression"]["receipt_sha256"] = compression_receipt_digest(
        e["compression"]
    )
    assert_reason(e, "COMPRESSION_PHASE_OUTPUT_MISMATCH")


def test_compression_cannot_worsen_resource():
    e = episode()
    e["compression"]["resource_after"] = 11
    e["compression"]["receipt_sha256"] = compression_receipt_digest(
        e["compression"]
    )
    assert_reason(e, "COMPRESSION_RESOURCE_RELATION_INVALID")


def test_nonfinite_resource_is_rejected():
    e = episode()
    e["compression"]["resource_after"] = math.inf
    assert_reason(e, "COMPRESSION_RESOURCE_RELATION_INVALID")
