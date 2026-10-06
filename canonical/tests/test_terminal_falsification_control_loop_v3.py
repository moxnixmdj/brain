from hashlib import sha256

from canonical.runtime.terminal_falsification_control_loop_v3 import (
    LEMMA,
    NEW,
    OLD,
    compile_control_loop_v3,
)

SHA = "0" * 40


def fp(inputs):
    rows = sorted(f"{x['path']}:{x['git_blob_sha']}" for x in inputs)
    return sha256("\n".join(rows).encode()).hexdigest()


def state():
    inputs = [{"path": "canonical/governance/BASE.json", "git_blob_sha": SHA}]
    return {
        "authoritative_inputs": inputs,
        "frontier_fingerprint": fp(inputs),
        "known_open_truth_obligations": 32,
        "claims": [
            {
                "id": "C_TARGET_UNIVERSE_COMPLETENESS_OR_SCOPE_SUPERSET_V2",
                "lane": "UNIVERSE_AUTHORITY",
                "status": "PROVED",
                "cost_units": 1,
                "target_truth_obligations": ["TARGET_UNIVERSE_SCOPE_SUPERSET"],
                "proof_receipts": [
                    {
                        "path": "canonical/verification/SCOPE.json",
                        "git_blob_sha": "1" * 40,
                    }
                ],
            },
            {
                "id": OLD,
                "lane": "UNIVERSE_AUTHORITY",
                "status": "ACTIVE",
                "cost_units": 1,
                "target_truth_obligations": ["LITERAL_ALL_USEFUL_OPUS55_FINALITY"],
            },
            {
                "id": "STABLE_SIDE_LANE",
                "lane": "EFFECT_CLOSURE",
                "status": "ACTIVE",
                "cost_units": 2,
                "target_truth_obligations": ["SIDE"],
                "stable_under_universe_expansion": True,
                "expansion_stability_receipt": {
                    "path": "canonical/verification/STABLE.json",
                    "git_blob_sha": "2" * 40,
                },
            },
        ],
    }


def overlay():
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_UTILITY_QUOTIENT_CONTROL_REPAIR_V1",
        "source_control": {
            "path": "canonical/governance/TERMINAL_FALSIFICATION_CONTROL_LOOP_V2.json",
            "git_blob_sha": "da8803584bc1e2bea672bcd1833e526ec489ac81",
        },
        "truth_repair": {
            "path": "canonical/governance/TERMINAL_FIRST_PRINCIPLES_THEORY_TOURNAMENT_20261006_V1.json",
            "git_blob_sha": "7102f0d0fef813c209a54246bcf7e221d060572f",
        },
        "independent_verification": {
            "path": "canonical/verification/TERMINAL_THEOREM_MINIMALITY_FALSIFIER_INDEPENDENT_VERIFICATION_20261006_V1.json",
            "git_blob_sha": "38486f2002c0d025fac73c36c43f86cdd2fee24d",
        },
        "falsified_claim": {
            "id": OLD,
            "replacement_status": "FALSIFIED",
            "falsification_receipt": {
                "path": "canonical/verification/TERMINAL_THEOREM_MINIMALITY_FALSIFIER_INDEPENDENT_VERIFICATION_20261006_V1.json",
                "git_blob_sha": "38486f2002c0d025fac73c36c43f86cdd2fee24d",
            },
        },
        "successor_claim": {
            "id": NEW,
            "lane": "UNIVERSE_AUTHORITY",
            "status": "ACTIVE",
            "successor_of": OLD,
            "cost_units": 1,
            "target_truth_obligations": ["LITERAL_ALL_USEFUL_OPUS55_FINALITY"],
            "target_truth_obligation_count": 1,
            "required_lemmas": [
                "UTILITY_AND_EQUAL_OR_BETTER_ORDERING_WELL_FORMED",
                "TARGET_UTILITY_QUOTIENT_COMPLETENESS",
                "TARGET_CLASS_WEAK_DOMINANCE",
                "CONDITION_AND_COMPOSITION_CLOSURE",
                "RESOURCE_SAFETY_AND_AUTHORITY_NONREGRESSION",
                "DONOR_INDEPENDENT_BRAIN_OWNERSHIP",
            ],
            "first_unresolved_lemma": LEMMA,
        },
    }


def test_verified_truth_repair_replaces_old_first_claim():
    out = compile_control_loop_v3(state(), overlay())
    assert out["status"].startswith("PASS__")
    assert out["first_universe_claim"] == NEW
    assert out["first_unresolved_lemma"] == LEMMA
    assert out["ordered_claim_ids"][0] == NEW
    assert OLD in out["dead_claim_ids"]
    assert OLD not in out["unrepaired_dead_claim_ids"]
    assert out["terminal_ready"] is False
    assert out["proof_credit_delta"] == 0


def test_wrong_truth_repair_blob_fails_closed():
    x = overlay()
    x["truth_repair"]["git_blob_sha"] = "f" * 40
    try:
        compile_control_loop_v3(state(), x)
    except ValueError as exc:
        assert "truth_repair_BINDING_MISMATCH" in str(exc)
    else:
        raise AssertionError("stale theorem repair accepted")


def test_wrong_lemma_order_fails_closed():
    x = overlay()
    x["successor_claim"]["required_lemmas"] = list(
        reversed(x["successor_claim"]["required_lemmas"])
    )
    try:
        compile_control_loop_v3(state(), x)
    except ValueError as exc:
        assert "LEMMA_SET_OR_ORDER_MISMATCH" in str(exc)
    else:
        raise AssertionError("wrong lemma order accepted")


def test_old_claim_must_be_exact_active_v2_claim():
    s = state()
    next(c for c in s["claims"] if c["id"] == OLD)["status"] = "PROVED"
    try:
        compile_control_loop_v3(s, overlay())
    except ValueError as exc:
        assert "OLD_CLAIM_NOT_ACTIVE" in str(exc)
    else:
        raise AssertionError("drifted predecessor accepted")


def test_duplicate_successor_fails_closed():
    s = state()
    s["claims"].append(dict(overlay()["successor_claim"]))
    try:
        compile_control_loop_v3(s, overlay())
    except ValueError as exc:
        assert "SUCCESSOR_ALREADY_PRESENT" in str(exc)
    else:
        raise AssertionError("duplicate successor accepted")


def test_stable_parallel_lane_remains_after_rerank():
    out = compile_control_loop_v3(state(), overlay())
    assert "STABLE_SIDE_LANE" in out["ordered_claim_ids"]
    assert out["ordered_claim_ids"].index(NEW) < out["ordered_claim_ids"].index(
        "STABLE_SIDE_LANE"
    )
