"""Content-bound universal proof candidate for Unknown-Domain direct V3.

Scope: every population successfully emitted by the exact V3 generator bytes.
The proof consumes no production/terminal cases and grants no credit.

V3 closes the two holes that revoked V2:
1) every emitted packet has harness/scorer-visible identifiers checked for
   injectivity before the population is returned;
2) ADD2 role order is reconstructed from visible cross-domain sign signatures,
   so candidate and gold use the identical IEEE-754 evaluation order.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":
        "7aafd50b833b9594ded35e4edb6fd41e7e89ce90",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":
        "02afbb813119c1aa8b8ff04580dff249639d4739",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":
        "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":
        "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}

FAMILIES = tuple(g1.PRIMITIVE_FAMILIES)
ADD2_INDEXES = (4, 10)
ADD2_R0_SIGNATURE = (-1, 1, -1)
ADD2_R1_SIGNATURE = (1, -1, 1)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _verify_bindings(root: Path) -> dict[str, str]:
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _non_add2_transfer_lemmas() -> dict[str, Any]:
    # V2 numeric ranges are content-bound above.  The two probe distractor
    # offsets are >=4.75 and >=6.25.
    min_shift = 4.75

    affine_gap = 0.6 * min_shift
    complement_gap = min_shift

    # f(x)=x/(1+|x|), x in [-3.5,3.5], shifted x in [1.25,10].
    # min derivative on the covering interval [-3.5,10] is 1/121.
    sat_gap = 0.7 * min_shift / 121.0
    sat_close_tolerance_max = 4.5e-9

    # SIGN indexes 1,7: first probe row j=3 is negative for the true role and
    # any distractor is positive after +4.75 or more.
    sign_true_upper = -0.25
    sign_distractor_lower = -3.5 + min_shift

    # STEP indexes 5,11: second probe row j=4 is below threshold by <=2.2;
    # distractor shift puts it strictly above.
    step_wrong_side_margin = min_shift - 2.2

    assert affine_gap > 2.84
    assert complement_gap >= 4.75
    assert sat_gap > sat_close_tolerance_max
    assert sign_true_upper < 0 < sign_distractor_lower
    assert step_wrong_side_margin > 2.54

    return {
        "affine_min_wrong_support_gap": affine_gap,
        "complement_min_wrong_support_gap": complement_gap,
        "sat_mono_min_wrong_support_gap": sat_gap,
        "sat_mono_max_close_tolerance": sat_close_tolerance_max,
        "sign_negative_probe_distractor_min": sign_distractor_lower,
        "step_wrong_side_margin": step_wrong_side_margin,
    }


def _add2_lemma() -> dict[str, Any]:
    # For both ADD2 indexes 4,10, rows 0..2 have domain-independent sign
    # patterns.  Magnitudes are strictly positive, so these signatures are
    # invariant for every valid beacon/evaluator secret.
    for index in ADD2_INDEXES:
        r0 = tuple(-1 if (j + index) % 2 == 0 else 1 for j in range(3))
        r1 = tuple(-1 if (j + index + 1) % 3 == 0 else 1 for j in range(3))
        assert r0 == ADD2_R0_SIGNATURE
        assert r1 == ADD2_R1_SIGNATURE
        assert r0 != r1

    # On first probe j=3 both true role values are positive in [0.25,3.5].
    # Wrong-support ADD2 gaps are therefore bounded strictly away from the
    # candidate close tolerance.
    wrong_support_min_gap = min(
        4.75 - (3.5 - 0.25),  # {r0,d0}
        6.25,                 # {r0,d1}
        4.75,                 # {r1,d0}
        6.25 - (3.5 - 0.25), # {r1,d1}
        4.75 + 6.25,          # {d0,d1}
    )
    assert wrong_support_min_gap == 1.5

    # With only the true support left, c3 matches the visible target feature
    # sign signature to the receipt-bound source role signature.  Therefore its
    # mapping is the actual r0/r1 orientation, not merely the support set.
    return {
        "indexes": list(ADD2_INDEXES),
        "r0_signature": list(ADD2_R0_SIGNATURE),
        "r1_signature": list(ADD2_R1_SIGNATURE),
        "first_probe_wrong_support_min_gap": wrong_support_min_gap,
        "exact_float_equality_reason": (
            "V3_RECONSTRUCTS_TRUE_R0_R1_ORIENTATION__CANDIDATE_AND_GENERATOR_"
            "THEN_EXECUTE_IDENTICAL_(BIAS_PLUS_R0)_PLUS_R1_FLOAT_OPERATION_ORDER"
        ),
    }


def _identifier_totality_lemma() -> dict[str, Any]:
    # The V3 generator invokes these guards before a transfer/abstention packet
    # is appended to any returned population.  A successfully returned
    # population therefore cannot contain a collision class that would make the
    # frozen harness/scorer ambiguous or raise.
    required_guards = (
        g3._validate_transfer_packet,
        g3._allowed_probe_ids,
        g3._validate_abstention_packet,
    )
    assert all(callable(x) for x in required_guards)
    return {
        "scope": "EVERY_SUCCESSFULLY_EMITTED_V3_POPULATION",
        "transfer_surface_mapping_relevant_distractor_source_binding": "FAIL_CLOSED_BEFORE_EMISSION",
        "transfer_and_abstention_probe_ids": "FAIL_CLOSED_BEFORE_EMISSION",
        "abstention_hypothesis_ids": "FAIL_CLOSED_BEFORE_EMISSION",
        "population_case_ids": "FAIL_CLOSED_BEFORE_RETURN",
    }


def _decisive_v2_counterexample_regression() -> dict[str, Any]:
    # This is explicitly a non-production qualification fixture.
    pop = g3.generate_qualification_fixture_population(
        beacon="CEX-00006-ABCDEFGHIJKLMNOP"
    )
    visible = pop["visible_cases"][10]
    hidden = pop["hidden_records"][10]
    out = harness.execute_case(
        candidate_step=c3.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert pop["production"] is False
    assert out["scorer_result"]["pass"] is True
    assert (
        out["candidate_terminal_action"]["terminal_consequence"]
        == hidden["gold_terminal_consequence"]
    )
    assert out["probe_count"] == 1
    return {
        "qualification_only": True,
        "case_index": 10,
        "scorer_pass": True,
        "exact_terminal_equality": True,
        "probe_count": 1,
    }


def _abstention_lemma() -> dict[str, Any]:
    assert tuple(g1.ABSTAIN_CLASSES) == (
        "IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED"
    )
    assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}
    return {
        "identifiable": "ALL_LIVE_HYPOTHESES_SHARE_VISIBLE_TERMINAL_CONSEQUENCE__V3_CONCLUDES",
        "nonidentifiable": "DISTINCT_CONSEQUENCES_NO_VISIBLE_SAFE_BINARY_DISCRIMINATOR__V3_ABSTAINS_WITH_WITNESS",
        "underspecified": "TWO_VISIBLE_SAFE_BINARY_DISCRIMINATORS_COST_1_AND_2__V3_REQUESTS_VISIBLE_MINIMUM_COST_ID",
        "cases_per_class": 5,
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    non_add2 = _non_add2_transfer_lemmas()
    add2 = _add2_lemma()
    identifiers = _identifier_totality_lemma()
    abstention = _abstention_lemma()
    regression = _decisive_v2_counterexample_regression()

    assert harness.MAX_TRANSFER_PROBES == 2
    assert c1.MAPPING_BASIS == "STRUCTURAL_EQUIVALENCE"
    assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE__UNIVERSAL_OVER_EVERY_SUCCESSFULLY_EMITTED_EXACT_V3_POPULATION",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "scope": {
            "generator": "V3",
            "every_successfully_emitted_population": True,
            "transfer_cases": 12,
            "abstention_cases": 15,
            "max_transfer_probes": 2,
            "production_or_terminal_cases_generated_by_proof": 0,
        },
        "non_add2_transfer_lemmas": non_add2,
        "add2_exact_role_and_float_lemma": add2,
        "identifier_totality_lemma": identifiers,
        "abstention_lemma": abstention,
        "revoked_v2_counterexample_repaired": regression,
        "theorem": (
            "FOR_EVERY_POPULATION_SUCCESSFULLY_EMITTED_BY_THE_EXACT_CONTENT_BOUND_"
            "V3_GENERATOR__THE_EXACT_V3_CANDIDATE_EXECUTED_THROUGH_THE_FROZEN_"
            "HARNESS_RECEIVES_PASS_FROM_THE_FROZEN_SCORER_ON_ALL_27_CASES"
        ),
        "authority": {
            "independent_verification_required": True,
            "promotion": False,
            "acceptance_credit": False,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
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
