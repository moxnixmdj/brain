"""Quantifier guard for the frozen Unknown-Domain V2 universal-proof route.

The frozen production launcher samples evaluator_secret with secrets.token_bytes(32).
Opaque identifiers are 14 hexadecimal HMAC-SHA256 characters = 56 bits.

The behavioral theorem is deterministic conditional on the critical identifiers
being collision-free. The frozen generator/harness do not reject every such
within-case collision, so an unconditional "for every valid secret" theorem is
too strong. This module records the exact critical pair count and the standard
PRF-model union bound; it grants no acceptance credit.
"""
from fractions import Fraction

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_V2_TOKEN_COLLISION_BOUND_V1"
TOKEN_BITS=56
TRANSFER_CASES=12
ADD2_TRANSFER_CASES=2
UNDERSPECIFIED_CASES=5

CRITICAL_PAIR_COUNTS={
    # hidden scorer requires distractor_feature_ids to be unique
    "target_distractor_pair_per_transfer_case": TRANSFER_CASES,
    # ADD2 hidden scorer requires the two relevant support feature ids unique
    "target_role_pair_per_add2_case": ADD2_TRANSFER_CASES,
    # harness rejects duplicate allowed probe ids before executing a case
    "transfer_probe_id_pair_per_transfer_case": TRANSFER_CASES,
    "underspecified_probe_id_pair_per_case": UNDERSPECIFIED_CASES,
}
CRITICAL_PAIR_COUNT=sum(CRITICAL_PAIR_COUNTS.values())


def bound():
    failure=Fraction(CRITICAL_PAIR_COUNT, 1 << TOKEN_BITS)
    return {
        "schema":SCHEMA,
        "status":"PASS__UNCONDITIONAL_UNIVERSAL_QUANTIFIER_NOT_JUSTIFIED__PRF_BOUND_COMPUTED",
        "token_bits":TOKEN_BITS,
        "critical_pair_counts":dict(CRITICAL_PAIR_COUNTS),
        "critical_pair_count":CRITICAL_PAIR_COUNT,
        "prf_union_bound_numerator":failure.numerator,
        "prf_union_bound_denominator":failure.denominator,
        "prf_union_bound_float":float(failure),
        "conditional_deterministic_theorem":"VALID_ONLY_IF_ALL_CRITICAL_IDENTIFIER_PAIRS_ARE_DISTINCT",
        "unconditional_for_every_secret_theorem_authorized":False,
        "acceptance_credit":False,
    }


if __name__=="__main__":
    import json
    print(json.dumps(bound(),indent=2,sort_keys=True))
