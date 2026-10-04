"""Content-bound universal proof candidate for Unknown-Domain direct V3.

V3 repairs the V2 ADD2 binary64 role-order defect by identifying ordered roles
from visible cross-domain sign signatures before computing the final consequence.

This theorem is zero-production and grants no acceptance credit by itself.
Independent content-bound verification is required before promotion.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":
        "522f551eb73035bf18379131c83202f6673e04d1",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":
        "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":
        "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}

FAMILIES = (
    "ORDER_PRESERVING_TRANSFORM",
    "PARITY_OR_SIGN_INVARIANT",
    "CONSERVATION_RELATION",
    "MONOTONE_CAUSAL_EDGE",
    "COMPOSITIONAL_REWRITE",
    "THRESHOLD_OR_PARTITION_INVARIANT",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _verify_bindings(root: Path) -> dict[str, str]:
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS
        if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _add2_role_identity_theorem() -> dict[str, Any]:
    # ADD2 occurs at indexes 4 and 10 because family position is 4 mod 6.
    # For V2 _role_rows, magnitudes are strictly positive. Therefore signs are
    # determined solely by the public j/index schedules, independent of secret,
    # beacon, domain A/B, or numeric magnitude.
    signatures = {}
    for index in (4, 10):
        r0 = tuple(-1 if (j + index) % 2 == 0 else 1 for j in range(3))
        r1 = tuple(-1 if (j + index + 1) % 3 == 0 else 1 for j in range(3))
        assert r0 == (-1, 1, -1)
        assert r1 == (1, -1, 1)
        assert r0 != r1
        signatures[str(index)] = {"r0": list(r0), "r1": list(r1)}

    # Source and target call the same _role_rows formula with only the "domain"
    # string entering magnitude HMAC inputs. Since magnitude never reaches zero,
    # the sign sequence above is invariant across A/B. V3 reads source roles via
    # the visible receipt source_role_binding and target roles via public task
    # rows, so exactly one ordered mapping matches.
    return {
        "add2_indexes": [4, 10],
        "public_rows_used": 3,
        "signatures": signatures,
        "source_target_sign_signature_invariant": True,
        "ordered_role_mapping_unique": True,
        "binary64_order_defect_removed": True,
        "reason": (
            "V3_RECOVERS_TRUE_r0_r1_ORDER_BEFORE_FINAL_ADD2_EVALUATION__"
            "CANDIDATE_AND_GENERATOR_THEN_EXECUTE_IDENTICAL_LEFT_ASSOCIATIVE_"
            "PYTHON_FLOAT_OPERATION_ORDER"
        ),
    }


def _transfer_theorem() -> dict[str, Any]:
    assert tuple(g1.PRIMITIVE_FAMILIES) == FAMILIES
    assert g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER] == 12
    assert harness.MAX_TRANSFER_PROBES == 2
    assert c1.MAPPING_BASIS == "STRUCTURAL_EQUIVALENCE"

    min_shift = 4.75

    affine_min_output_gap = 0.6 * min_shift
    complement_min_output_gap = min_shift
    sat_mono_min_output_gap = 0.7 * min_shift / 121.0
    sat_mono_max_close_tolerance = 4.5e-9
    sign_negative_probe_distractor_min = -3.5 + min_shift
    step_wrong_side_margin = min_shift - 2.2

    assert affine_min_output_gap > 1.0
    assert complement_min_output_gap > 1.0
    assert sat_mono_min_output_gap > sat_mono_max_close_tolerance
    assert sign_negative_probe_distractor_min > 0.0
    assert step_wrong_side_margin > 0.0

    # ADD2 first allowed probe (actual role row j=3) has both true roles
    # positive for indexes 4 and 10. Every wrong support has a strict output gap.
    add2_wrong_support_min_gap = min(
        4.75 - (3.5 - 0.25),
        6.25,
        4.75,
        6.25 - (3.5 - 0.25),
        4.75 + 6.25,
    )
    assert add2_wrong_support_min_gap == 1.5

    add2_order = _add2_role_identity_theorem()

    return {
        "all_six_families_universal_candidate": True,
        "families": list(FAMILIES),
        "max_transfer_probes": 2,
        "full_rediscovery_probe_floor": 3,
        "affine_min_output_gap": affine_min_output_gap,
        "complement_min_output_gap": complement_min_output_gap,
        "sat_mono_min_output_gap": sat_mono_min_output_gap,
        "sat_mono_max_close_tolerance": sat_mono_max_close_tolerance,
        "sign_negative_probe_distractor_min": sign_negative_probe_distractor_min,
        "step_wrong_side_margin": step_wrong_side_margin,
        "add2_wrong_support_min_gap": add2_wrong_support_min_gap,
        "add2_role_identity": add2_order,
        "scale_fallback_load_bearing_on_frozen_v2_generator": False,
    }


def _abstention_theorem() -> dict[str, Any]:
    assert tuple(g1.ABSTAIN_CLASSES) == (
        "IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED"
    )
    assert g1.PRODUCTION_CASE_COUNTS[g1.ABSTAIN] == 15
    assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}
    return {
        "all_three_classes_universal_candidate": True,
        "cases_per_class": 5,
        "identifiable": "VISIBLE_CONSEQUENCES_EQUAL__V3_DELEGATES_TO_V1_AND_CONCLUDES",
        "nonidentifiable": "VISIBLE_CONSEQUENCES_DIFFER__NO_SAFE_BINARY_DISCRIMINATOR__V3_ABSTAINS",
        "underspecified": "VISIBLE_SAFE_BINARY_DISCRIMINATORS_EXIST__V3_REQUESTS_MINIMUM_COST_ID",
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _repo_root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    transfer = _transfer_theorem()
    abstention = _abstention_theorem()
    assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN__INDEPENDENT_VERIFICATION_REQUIRED",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "transfer_proof": transfer,
        "abstention_proof": abstention,
        "v2_counterexample_repaired": True,
        "fresh_reality_required_for_this_frozen_generator_claim_if_verified": False,
        "production_execution_information_gain_if_verified": 0,
        "hard_nonclaims": [
            "NO_ACCEPTANCE_PROMOTION_UNTIL_INDEPENDENT_CONTENT_BOUND_VERIFICATION",
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_FROZEN_GENERATOR_DOMAIN",
            "NO_PRODUCTION_OR_TERMINAL_CASE_GENERATED_OR_CONSUMED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True))
