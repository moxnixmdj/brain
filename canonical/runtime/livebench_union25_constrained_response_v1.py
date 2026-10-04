#!/usr/bin/env python3
"""Isolated exact witness for registry25 constrained_response.

The pinned registry conflict graph makes detectable_format:constrained_response
incompatible with every other registered checker.  Therefore its entire
registry25 structural domain is the singleton identity set containing only
itself.  The pinned checker succeeds iff the stripped response contains at least
one member of the three fixed response options.

This module chooses one exact option and deliberately grants zero acceptance
credit until independent verification binds the pinned registry and checker
source.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime import livebench_union25_interaction_cut_v1 as cut

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_CONSTRAINED_RESPONSE_V1"
INSTRUCTION_ID = "detectable_format:constrained_response"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

PINNED_OPTIONS = (
    "My answer is yes.",
    "My answer is no.",
    "My answer is maybe.",
)
WITNESS = PINNED_OPTIONS[0]


def verify() -> dict[str, Any]:
    structural = cut.verify()
    if structural["constrained_response"]["structural_set_count"] != 1:
        raise AssertionError("CONSTRAINED_RESPONSE_NOT_ISOLATED")
    if structural["constrained_response"]["only_reachable_set"] != [INSTRUCTION_ID]:
        raise AssertionError("CONSTRAINED_RESPONSE_SINGLETON_ID_DRIFT")
    if WITNESS.strip() not in PINNED_OPTIONS:
        raise AssertionError("WITNESS_NOT_PINNED_OPTION")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CONSTRAINED_RESPONSE_STRUCTURAL_DOMAIN_IS_SINGLETON__"
            "EXACT_PINNED_OPTION_WITNESS_SELECTED__INDEPENDENT_CHECKER_REPLAY_REQUIRED"
        ),
        "instruction_id": INSTRUCTION_ID,
        "structural_domain": [[INSTRUCTION_ID]],
        "pinned_options": list(PINNED_OPTIONS),
        "witness": WITNESS,
        "pinned_source": {
            "livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "registry_blob": PINNED_REGISTRY_BLOB,
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
        },
        "pointwise_claim_if_independently_verified": {
            "maximum_possible_pass_count": 1,
            "witness_pass_count": 1,
            "pointwise_optimal": True,
        },
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "NO_ACCEPTANCE_CREDIT_BEFORE_INDEPENDENT_PINNED_CHECKER_REPLAY",
            "THIS_CLOSES_ONE_REGISTRY25_FAMILY_NOT_THE_FULL_UNION25_DOMAIN",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
