"""Fail-closed learned-state accounting gate for the sub-100MB research program.

This gate does not create capability or acceptance credit. It verifies that a
content-addressed audit has not hidden learned state or a remote learned
capability provider outside the declared budget.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SUB100MB_ACCEPTED5_ZERO_LEARNED_STATE_AUDIT_V1"


class LearnedStateAuditError(ValueError):
    pass


def _int_nonnegative(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LearnedStateAuditError(f"{name}_INVALID")
    return value


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        raise LearnedStateAuditError("AUDIT_NOT_MAPPING")
    if doc.get("schema") != SCHEMA:
        raise LearnedStateAuditError("SCHEMA_INVALID")

    budget = doc.get("budget")
    if not isinstance(budget, Mapping):
        raise LearnedStateAuditError("BUDGET_MISSING")
    max_bytes = _int_nonnegative(
        budget.get("persistent_learned_state_bytes_max"),
        "PERSISTENT_LEARNED_STATE_BYTES_MAX",
    )

    families = doc.get("families")
    if not isinstance(families, list) or not families:
        raise LearnedStateAuditError("FAMILIES_INVALID")

    seen: set[str] = set()
    total = 0
    rows = []
    for row in families:
        if not isinstance(row, Mapping):
            raise LearnedStateAuditError("FAMILY_ROW_INVALID")
        family = row.get("family")
        if not isinstance(family, str) or not family or family in seen:
            raise LearnedStateAuditError("FAMILY_ID_INVALID_OR_DUPLICATE")
        seen.add(family)

        if row.get("accepted_status") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
            raise LearnedStateAuditError(f"FAMILY_NOT_ACCEPTED:{family}")
        if row.get("dependency_inventory_complete_for_scoped_capability") is not True:
            raise LearnedStateAuditError(f"DEPENDENCY_INVENTORY_INCOMPLETE:{family}")
        if row.get("external_learned_capability_provider_required") is not False:
            raise LearnedStateAuditError(f"EXTERNAL_LEARNED_PROVIDER_REQUIRED:{family}")

        artifacts = row.get("operative_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise LearnedStateAuditError(f"OPERATIVE_ARTIFACTS_MISSING:{family}")
        for artifact in artifacts:
            if not isinstance(artifact, Mapping):
                raise LearnedStateAuditError(f"OPERATIVE_ARTIFACT_INVALID:{family}")
            path = artifact.get("path")
            sha = artifact.get("git_blob_sha")
            if not isinstance(path, str) or not path:
                raise LearnedStateAuditError(f"ARTIFACT_PATH_INVALID:{family}")
            if not isinstance(sha, str) or len(sha) != 40:
                raise LearnedStateAuditError(f"ARTIFACT_BLOB_SHA_INVALID:{family}")

        learned = _int_nonnegative(
            row.get("persistent_learned_state_bytes"),
            f"PERSISTENT_LEARNED_STATE_BYTES:{family}",
        )
        total += learned
        rows.append({"family": family, "persistent_learned_state_bytes": learned})

    result = doc.get("result")
    if not isinstance(result, Mapping):
        raise LearnedStateAuditError("RESULT_MISSING")
    if result.get("accepted_families_audited") != len(families):
        raise LearnedStateAuditError("RESULT_FAMILY_COUNT_MISMATCH")
    if result.get("persistent_learned_state_bytes_required_by_audited_accepted_routes") != total:
        raise LearnedStateAuditError("RESULT_LEARNED_BYTES_MISMATCH")

    within = total <= max_bytes
    if result.get("within_100mb_learned_state_budget") is not within:
        raise LearnedStateAuditError("RESULT_BUDGET_VERDICT_MISMATCH")

    zero_count = sum(1 for row in rows if row["persistent_learned_state_bytes"] == 0)
    if result.get("accepted_families_with_zero_persistent_learned_state") != zero_count:
        raise LearnedStateAuditError("RESULT_ZERO_FAMILY_COUNT_MISMATCH")

    return {
        "schema": "PROJECT_BRAIN_SUB100MB_LEARNED_STATE_GATE_RESULT_V1",
        "pass": within,
        "family_count": len(rows),
        "zero_learned_state_family_count": zero_count,
        "persistent_learned_state_bytes": total,
        "persistent_learned_state_bytes_max": max_bytes,
        "remaining_budget_bytes": max_bytes - total,
        "terminal_hypothesis_proved": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
    }


def evaluate_path(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return evaluate(doc)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()
    verdict = evaluate_path(args.audit)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
