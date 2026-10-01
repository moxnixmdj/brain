"""Fail-closed terminal-goal closure reducer for Project Brain.

This module does not estimate progress. It answers exactly one question:
does the supplied terminal closure manifest prove every required predicate?

Unknown, null, malformed, duplicate, open, contaminated, donor-dependent,
or otherwise unresolved state always reduces to NOT ACHIEVED.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FAMILY_COUNT = 19
REQUIRED_COUNTERS = (
    "uncontracted_required_behaviors",
    "unproved_required_behaviors",
    "donor_dependent_required_behaviors",
    "unresolved_verifier_mutations",
    "unresolved_composition_failures",
    "contaminated_promotion_evidence",
    "resource_or_authority_violations",
)
REQUIRED_PREDICATES = (
    "exact_target_family_count_19",
    "every_required_behavior_contracted",
    "every_required_behavior_has_admissible_proof",
    "donor_dependent_required_behaviors_zero",
    "unexplained_required_behaviors_zero",
    "unresolved_verifier_mutations_zero",
    "unresolved_composition_failures_zero",
    "contaminated_evidence_used_for_promotion_zero",
    "resource_or_authority_violations_zero",
    "all_frozen_opus_acceptance_predicates_pass",
    "final_donor_deletion_cleanroom_pass",
    "proof_bundle_frozen",
)


def evaluate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    if manifest.get("expected_family_count") != REQUIRED_FAMILY_COUNT:
        failures.append("EXPECTED_FAMILY_COUNT_NOT_19")

    families = manifest.get("families")
    if not isinstance(families, list):
        families = []
        failures.append("FAMILIES_NOT_LIST")

    ids: list[str] = []
    for index, family in enumerate(families):
        if not isinstance(family, dict):
            failures.append(f"FAMILY_{index}_MALFORMED")
            continue
        fid = family.get("id")
        if not isinstance(fid, str) or not fid.strip():
            failures.append(f"FAMILY_{index}_ID_INVALID")
            continue
        ids.append(fid)
        if family.get("closure_state") != "PASS":
            failures.append(f"FAMILY_OPEN:{fid}")

    if len(families) != REQUIRED_FAMILY_COUNT:
        failures.append(f"ACTUAL_FAMILY_COUNT:{len(families)}")
    if len(ids) != len(set(ids)):
        failures.append("DUPLICATE_FAMILY_ID")
    if manifest.get("actual_family_count") != len(families):
        failures.append("DECLARED_ACTUAL_FAMILY_COUNT_MISMATCH")

    counters = manifest.get("counters")
    if not isinstance(counters, dict):
        counters = {}
        failures.append("COUNTERS_NOT_OBJECT")
    for name in REQUIRED_COUNTERS:
        value = counters.get(name)
        if type(value) is not int:
            failures.append(f"COUNTER_UNKNOWN_OR_NONINTEGER:{name}")
        elif value != 0:
            failures.append(f"COUNTER_NONZERO:{name}:{value}")

    predicates = manifest.get("terminal_predicates")
    if not isinstance(predicates, dict):
        predicates = {}
        failures.append("TERMINAL_PREDICATES_NOT_OBJECT")
    for name in REQUIRED_PREDICATES:
        if predicates.get(name) is not True:
            failures.append(f"PREDICATE_NOT_TRUE:{name}")

    # Cross-check counter-backed predicates. A handwritten true may not override
    # a missing/nonzero counter.
    counter_predicates = {
        "donor_dependent_required_behaviors": "donor_dependent_required_behaviors_zero",
        "unresolved_verifier_mutations": "unresolved_verifier_mutations_zero",
        "unresolved_composition_failures": "unresolved_composition_failures_zero",
        "contaminated_promotion_evidence": "contaminated_evidence_used_for_promotion_zero",
        "resource_or_authority_violations": "resource_or_authority_violations_zero",
    }
    for counter, predicate in counter_predicates.items():
        if counters.get(counter) != 0 and predicates.get(predicate) is True:
            failures.append(f"COUNTER_PREDICATE_CONTRADICTION:{counter}:{predicate}")

    unique_failures = sorted(set(failures))
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CLOSURE_VERDICT_V1",
        "achieved": not unique_failures,
        "failed_predicates": unique_failures,
        "family_count": len(families),
        "closed_family_count": sum(
            1 for family in families
            if isinstance(family, dict) and family.get("closure_state") == "PASS"
        ),
        "rule": "ACHIEVED_IFF_FAILED_PREDICATES_EMPTY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    verdict = evaluate_manifest(data)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["achieved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
