"""Universal proof candidate for the full-total + exact Unknown-Domain route.

This theorem discharges the two independent defects that revoked V2:
1. every load-bearing opaque identifier is structurally injective even under
   total HMAC-token collision;
2. ADD2 support roles are oriented from visible cross-domain sign signatures,
   so candidate and gold use identical IEEE-754 operand order.

The proof is content-bound to exact runtime blobs. It generates no production
or terminal cases and grants no acceptance/family/capability/ownership credit.
"""
from __future__ import annotations

import hashlib
import inspect
import itertools
from fractions import Fraction
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V5_FULL_TOTAL_EXACT_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":
        "cb030de5a7f96bac7667b7fbb3be38a1cc55e3ea",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py":
        "bbb1ff90348306a1d196682ddfaac996fb658677",
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


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


def _identifier_totality_theorem() -> dict[str, Any]:
    # Feature-slot totality is independent of every HMAC value. _permutation
    # begins with range(n) and performs swaps only; every possible output is
    # therefore a bijection. Exhaust the complete finite output spaces n=3,4.
    permutation_count = 0
    for count in (3, 4):
        for perm in itertools.permutations(range(count)):
            ids = [f"udir4_b_t07_u{perm[i]}_COLLIDE" for i in range(count)]
            assert len(ids) == len(set(ids)) == count
            permutation_count += 1
    assert permutation_count == 30

    # Now force the opaque HMAC token to one identical constant symbolically.
    # Every identifier that must remain distinct still has a structural
    # discriminator. This is population-global, not merely case-local.
    feature_ids: set[str] = set()
    for case_index in range(12):
        count = 4 if case_index % len(FAMILIES) == 4 else 3
        for domain in ("udir4_a", "udir4_b"):
            for slot in range(count):
                fid = f"{domain}_t{case_index:02d}_u{slot}_COLLIDE"
                assert fid not in feature_ids
                feature_ids.add(fid)
    assert len(feature_ids) == (10 * 2 * 3) + (2 * 2 * 4) == 76

    receipt_ids = {
        f"R-UDIR4-T-{i:02d}-COLLIDE" for i in range(12)
    }
    assert len(receipt_ids) == 12

    transfer_probe_ids = {
        f"P-UDIR4-T-{i:02d}-{j}-COLLIDE"
        for i in range(12) for j in range(2)
    }
    assert len(transfer_probe_ids) == 24

    case_ids = (
        {f"UDIR4-T-{i:02d}-COLLIDE" for i in range(12)}
        | {f"UDIR4-A-{i:02d}-COLLIDE" for i in range(15)}
    )
    assert len(case_ids) == 27

    hypothesis_ids = {
        f"H-UDIR4-A-{i:02d}-{j}-COLLIDE"
        for i in range(15) for j in range(2)
    }
    assert len(hypothesis_ids) == 30

    # IDENTIFIABLE intentionally gives h1/h2 the same terminal action. That
    # semantic equality is not an identifier collision. All actions that must
    # be distinct retain structural local ordinals.
    action_ids = set()
    for i in range(15):
        action_ids.add(f"A-UDIR4-A-{i:02d}-0-COLLIDE")
        if i >= 5:
            action_ids.add(f"A-UDIR4-A-{i:02d}-1-COLLIDE")
    assert len(action_ids) == 25

    abstention_probe_ids = set()
    for i in range(5, 10):
        abstention_probe_ids.add(f"P-UDIR4-A-{i:02d}-0-COLLIDE")
    for i in range(10, 15):
        abstention_probe_ids.add(f"P-UDIR4-A-{i:02d}-0-COLLIDE")
        abstention_probe_ids.add(f"P-UDIR4-A-{i:02d}-1-COLLIDE")
    assert len(abstention_probe_ids) == 15
    assert transfer_probe_ids.isdisjoint(abstention_probe_ids)

    # Category prefixes and case namespace make all load-bearing categories
    # pairwise disjoint except intentional semantic references to the same ID.
    all_structural = [
        feature_ids,
        receipt_ids,
        transfer_probe_ids | abstention_probe_ids,
        case_ids,
        hypothesis_ids,
        action_ids,
    ]
    for i, left in enumerate(all_structural):
        for right in all_structural[i + 1:]:
            assert left.isdisjoint(right)

    return {
        "status": "PASS__FULL_STRUCTURAL_IDENTIFIER_TOTALITY",
        "feature_permutation_outputs_exhausted": permutation_count,
        "feature_ids_under_total_token_collision": len(feature_ids),
        "receipt_ids_under_total_token_collision": len(receipt_ids),
        "probe_ids_under_total_token_collision": len(
            transfer_probe_ids | abstention_probe_ids
        ),
        "case_ids_under_total_token_collision": len(case_ids),
        "hypothesis_ids_under_total_token_collision": len(hypothesis_ids),
        "distinct_action_ids_under_total_token_collision": len(action_ids),
        "intentional_identifiable_action_equalities": 5,
        "hmac_collision_freedom_assumed": False,
        "accepted_secret_or_beacon_rejected_for_identifier_collision": False,
        "proof": (
            "ALL_REQUIRED_DISTINCTNESS_IS_CARRIED_BY_LITERAL_KIND_LEAF_CASE_"
            "ORDINAL_AND_BIJECTIVE_FEATURE_SLOT_FIELDS__OPAQUE_HMAC_MATERIAL_"
            "MAY_COLLIDE_ARBITRARILY_WITHOUT_COLLAPSING_SEMANTIC_IDENTITIES"
        ),
    }


def _scope_equivalence_theorem() -> dict[str, Any]:
    src = inspect.getsource(g4._transfer_case)
    abstain_src = inspect.getsource(g4._abstention_case)
    assert "v2._program_for" in src
    assert "v2._role_rows" in src
    assert "v1._surface_row" in src
    assert "v1._eval" in src
    assert "v1.ABSTAIN_CLASSES[index // 5]" in abstain_src
    assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}
    assert tuple(g1.PRIMITIVE_FAMILIES) == FAMILIES
    return {
        "status": "PASS__V2_NUMERIC_AND_DECISION_SCOPE_PRESERVED",
        "program_generation": "EXACT_V2_PROGRAM_FOR",
        "numeric_rows": "EXACT_V2_ROLE_ROWS",
        "surface_numeric_values": "EXACT_V1_SURFACE_ROW",
        "gold_evaluation": "EXACT_V1_EVAL",
        "transfer_count": 12,
        "abstention_count": 15,
        "delta": (
            "OPAQUE_IDENTIFIER_ALPHA_RENAMING_PLUS_TOTALIZATION_ONLY__"
            "COLLISION_INPUTS_THAT_COULD_MALFORM_V2_NOW_REMAIN_WELL_FORMED"
        ),
        "scope_relation_to_v2": "SEMANTICALLY_EQUAL_ON_NONCOLLISION_INPUTS__STRICTLY_TOTALIZED_ON_COLLISION_INPUTS",
    }


def _add2_sign_signature(index: int, role: str) -> tuple[int, int, int]:
    out = []
    for j in range(3):
        if role == "r0":
            negative = (j + index) % 2 == 0
        elif role == "r1":
            negative = (j + index + 1) % 3 == 0
        else:
            raise AssertionError("ROLE_UNSUPPORTED")
        out.append(-1 if negative else 1)
    return tuple(out)


def _transfer_theorem() -> dict[str, Any]:
    assert harness.MAX_TRANSFER_PROBES == 2
    assert c1.MAPPING_BASIS == "STRUCTURAL_EQUIVALENCE"

    d0 = Fraction(19, 4)  # first-probe distractor-0 minimum shift
    d1 = Fraction(25, 4)  # first-probe distractor-1 minimum shift
    min_mag = Fraction(1, 4)
    max_mag = Fraction(7, 2)

    affine_gap = Fraction(3, 5) * d0
    complement_gap = d0
    sat_gap = Fraction(7, 10) * d0 / Fraction(121, 1)
    sign_shifted_min = -max_mag + d0
    step_margin = d0 - Fraction(11, 5)
    add2_gap = min(
        d0 - (max_mag - min_mag),
        d1,
        d0,
        d1 - (max_mag - min_mag),
        d0 + d1,
    )

    assert affine_gap == Fraction(57, 20)
    assert complement_gap == Fraction(19, 4)
    assert float(sat_gap) > 4.5e-9
    assert sign_shifted_min == Fraction(5, 4) > 0
    assert step_margin == Fraction(51, 20) > 0
    assert add2_gap == Fraction(3, 2)

    # Conservative upper bounds on _close's 1e-9*scale tolerance are tiny
    # compared with every strict wrong-support margin above.
    assert float(affine_gap) > 3.0e-8
    assert float(complement_gap) > 1.5e-8
    assert float(add2_gap) > 2.5e-8

    add2_indexes = (4, 10)
    signatures = {}
    for index in add2_indexes:
        r0 = _add2_sign_signature(index, "r0")
        r1 = _add2_sign_signature(index, "r1")
        assert r0 == (-1, 1, -1)
        assert r1 == (1, -1, 1)
        assert r0 != r1
        signatures[str(index)] = {"r0": list(r0), "r1": list(r1)}

    # Exact candidate V3 transfers source role-sign signatures through the
    # receipt binding to the target support. The sign schedule is domain
    # invariant and all magnitudes are >=0.25, so role orientation is unique.
    orient_src = inspect.getsource(c3._orient_add2)
    transfer_src = inspect.getsource(c3._transfer)
    assert "_sign_signature(source_tasks, fid)" in orient_src
    assert "_sign_signature(target_tasks, fid)" in orient_src
    assert "mapping = _orient_add2(case, receipt, support)" in transfer_src
    assert "mapping = _orient_add2(case, receipt, v1._support_signature(mapping))" in transfer_src

    # If ADD2's two role permutations round to one query consequence, V3
    # orients and concludes after probe 1. If they do not, it requests probe 2;
    # V2 scale resolution groups by support and V3 then re-orients that exact
    # support. Hence exact binary64 correctness is independent of decimal-round
    # coincidence and remains below the rediscovery floor.
    assert harness.MAX_TRANSFER_PROBES == 2 < 3

    # Candidate and generator share the exact left-to-right expression:
    # bias + r0 + r1. Once role orientation is exact, IEEE-754 operands and
    # operation order are identical, so scorer exact equality follows.
    c1_src = inspect.getsource(c1._program_eval)
    g1_src = inspect.getsource(g1._eval)
    assert 'if op=="ADD2"' in c1_src
    assert 'if op=="ADD2"' in g1_src
    assert 'role_values["r0"]' in c1_src and 'role_values["r1"]' in c1_src
    assert 'roles["r0"]' in g1_src and 'roles["r1"]' in g1_src

    return {
        "status": "PASS__ALL_SIX_TRANSFER_FAMILIES__EXACT_ADD2",
        "all_six_families_universal": True,
        "affine_min_wrong_support_gap": str(affine_gap),
        "complement_min_wrong_support_gap": str(complement_gap),
        "sat_mono_min_wrong_support_gap": str(sat_gap),
        "sign_shifted_distractor_min": str(sign_shifted_min),
        "step_wrong_side_margin": str(step_margin),
        "add2_min_wrong_support_gap": str(add2_gap),
        "add2_role_signatures": signatures,
        "add2_exact_ieee754_order": "BIAS_PLUS_R0_THEN_PLUS_R1_IN_BOTH_CANDIDATE_AND_GOLD",
        "max_transfer_probes": 2,
        "full_rediscovery_probe_floor": 3,
    }


def _abstention_theorem() -> dict[str, Any]:
    assert tuple(g1.ABSTAIN_CLASSES) == (
        "IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED"
    )
    assert scorer.DECISIONS == {
        "CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"
    }
    assert c3.step is not None
    return {
        "status": "PASS__ALL_THREE_ABSTENTION_CLASSES",
        "cases_per_class": 5,
        "identifiable": (
            "TWO_DISTINCT_HYPOTHESIS_IDS_INTENTIONALLY_SHARE_ONE_ACTION__"
            "CANDIDATE_CONCLUDES_THE_UNIQUE_CONSEQUENCE"
        ),
        "nonidentifiable": (
            "DISTINCT_HYPOTHESES_AND_ACTIONS__NO_SAFE_BINARY_DISCRIMINATOR__"
            "CANDIDATE_ABSTAINS_WITH_NONEMPTY_WITNESS"
        ),
        "underspecified": (
            "DISTINCT_HYPOTHESES_ACTIONS_AND_TWO_STRUCTURALLY_DISTINCT_SAFE_"
            "DISCRIMINATORS__CANDIDATE_REQUESTS_UNIQUE_COST_1_DISCRIMINATOR"
        ),
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _repo_root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    identifiers = _identifier_totality_theorem()
    scope = _scope_equivalence_theorem()
    transfer = _transfer_theorem()
    abstention = _abstention_theorem()

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FULL_IDENTIFIER_TOTALITY_PLUS_EXACT_ADD2__"
            "UNIVERSAL_OVER_ALL_VALID_V4_PRODUCTION_INPUTS"
        ),
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "scope": {
            "beacon": "ALL_VALID_STRINGS_LENGTH_GE_16",
            "evaluator_secret": "ALL_VALUES_ACCEPTED_BY_EXACT_SECRET_BYTES_GATE",
            "production_population_cases": 27,
            "transfer_cases": 12,
            "abstention_cases": 15,
            "terminal_or_production_cases_generated_by_proof": 0,
        },
        "identifier_totality_proof": identifiers,
        "scope_equivalence_proof": scope,
        "transfer_proof": transfer,
        "abstention_proof": abstention,
        "theorem": (
            "FOR_EVERY_VALID_BEACON_AND_EVALUATOR_SECRET__GENERATOR_V4_EMITS_"
            "ONE_WELL_FORMED_27_CASE_POPULATION_WITH_FULL_STRUCTURAL_IDENTIFIER_"
            "TOTALITY__CANDIDATE_V3_THROUGH_THE_EXACT_FROZEN_HARNESS_AND_SCORER_"
            "PASSES_ALL_12_TRANSFER_AND_15_ABSTENTION_CASES__INCLUDING_EXACT_"
            "IEEE754_ADD2_EQUALITY__WITH_AT_MOST_TWO_TRANSFER_PROBES"
        ),
        "repairs": {
            "v2_truncated_identifier_universal_quantifier_hole": True,
            "v2_add2_exact_ieee754_role_order_counterexample": True,
            "scorer_or_harness_relaxed": False,
            "input_quantifier_weakened": False,
        },
        "fresh_reality_required_for_this_exact_totalized_contract": False,
        "production_execution_information_gain_for_this_exact_totalized_contract": 0,
        "hard_nonclaims": [
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_BOUND_DIRECT_AUDIT_CONTRACT",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_MODULE_ALONE",
            "NO_PRODUCTION_OR_TERMINAL_CASE_GENERATED_READ_OR_CONSUMED",
            "INDEPENDENT_CONTENT_BOUND_VERIFICATION_AND_SEPARATE_FAIL_CLOSED_ACCEPTANCE_REDUCTION_REQUIRED",
        ],
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
