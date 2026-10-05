#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_PATH = "canonical/governance/SEVEN_SCOPE_LEAF_ACTIVE_ROUTE_REUSE_FIXED_POINT_V1.json"
PARTITION_PATH = "canonical/governance/SIX_BENCHMARK_PROXY_FAMILY_SCOPE_PARTITION_V2.json"
BASIS_PATH = "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
REGISTRY_PATH = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

CORE_FIELDS = (
    "behavior_id",
    "inputs",
    "environment_state",
    "allowed_information",
    "required_output_or_action",
    "success_condition",
    "failure_condition",
    "terminal_consequence",
    "verification_route",
    "dependency_boundary",
    "scope",
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_text(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def git_blob(ref: str, path: str) -> str:
    return git_text("rev-parse", f"{ref}:{path}")


def git_json(ref: str, path: str) -> dict:
    return json.loads(git_text("show", f"{ref}:{path}"))


def contracts_by_id(registry: dict) -> dict[str, dict]:
    return {
        row["behavior_id"]: row
        for row in registry.get("active_contracted_residuals", [])
    }


def main() -> int:
    errors: list[str] = []
    candidate = load(CANDIDATE_PATH)
    partition = load(PARTITION_PATH)
    basis = load(BASIS_PATH)
    current_registry = load(REGISTRY_PATH)

    auth = candidate["authorities"]
    historical = auth["historical_behavioral_registry"]
    old_commit = historical["commit"]
    historical_registry = git_json(old_commit, REGISTRY_PATH)

    blob_checks = (
        ("PARTITION_BLOB", "HEAD", PARTITION_PATH, auth["six_family_scope_partition"]["git_blob_sha"]),
        ("BASIS_BLOB", "HEAD", BASIS_PATH, auth["active_terminal_proof_basis"]["git_blob_sha"]),
        ("CURRENT_REGISTRY_BLOB", "HEAD", REGISTRY_PATH, auth["current_behavioral_registry"]["git_blob_sha"]),
        ("HISTORICAL_REGISTRY_BLOB", old_commit, REGISTRY_PATH, historical["git_blob_sha"]),
    )
    for label, ref, path, expected in blob_checks:
        actual = git_blob(ref, path)
        if actual != expected:
            errors.append(f"{label}_MISMATCH:{actual}!={expected}")

    expected_ids = sorted(row["behavior_id"] for row in candidate["surviving_leaves"])
    partition_ids = sorted(
        row["leaf"] for row in partition["deduplicated_surviving_hypergraph"]
    )
    if partition_ids != expected_ids:
        errors.append("PARTITION_SURVIVING_LEAF_SET_MISMATCH")
    if len(expected_ids) != 7 or len(set(expected_ids)) != 7:
        errors.append("EXPECTED_LEAF_SET_NOT_EXACTLY_SEVEN_UNIQUE")

    old_map = contracts_by_id(historical_registry)
    current_map = contracts_by_id(current_registry)
    basis_map = {row["behavior_id"]: row for row in basis.get("contracts", [])}
    candidate_map = {row["behavior_id"]: row for row in candidate["surviving_leaves"]}

    route_rows = []
    for behavior_id in expected_ids:
        old_row = old_map.get(behavior_id)
        current_row = current_map.get(behavior_id)
        basis_row = basis_map.get(behavior_id)
        candidate_row = candidate_map.get(behavior_id)

        if old_row is None:
            errors.append(f"OLD_REGISTRY_MISSING:{behavior_id}")
            continue
        if current_row is None:
            errors.append(f"CURRENT_REGISTRY_MISSING:{behavior_id}")
            continue
        if basis_row is None:
            errors.append(f"ACTIVE_BASIS_MISSING:{behavior_id}")
            continue

        drift = [
            field
            for field in CORE_FIELDS
            if old_row.get(field) != current_row.get(field)
        ]
        if drift:
            errors.append(f"CORE_CONTRACT_DRIFT:{behavior_id}:{','.join(drift)}")

        if basis_row.get("proof_state") != "TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
            errors.append(f"ROUTE_NOT_FROZEN_ADMISSIBLE:{behavior_id}")
        if basis_row.get("blockers") != []:
            errors.append(f"ROUTE_BLOCKERS_NONEMPTY:{behavior_id}")
        if basis_row.get("prewave_admissible") is not True:
            errors.append(f"PREWAVE_NOT_ADMISSIBLE:{behavior_id}")
        if basis_row.get("terminal_results_observed") != 0:
            errors.append(f"TERMINAL_RESULTS_ALREADY_OBSERVED:{behavior_id}")
        if candidate_row.get("portfolio") != basis_row.get("portfolio"):
            errors.append(f"PORTFOLIO_BINDING_MISMATCH:{behavior_id}")
        if candidate_row.get("route") != basis_row.get("route"):
            errors.append(f"ROUTE_BINDING_MISMATCH:{behavior_id}")

        route_rows.append(
            {
                "behavior_id": behavior_id,
                "portfolio": basis_row.get("portfolio"),
                "route": basis_row.get("route"),
                "core_contract_identical": not drift,
                "frozen_admissible": basis_row.get("proof_state")
                == "TERMINAL_ROUTE_FROZEN_ADMISSIBLE",
                "blockers_empty": basis_row.get("blockers") == [],
                "prewave_admissible": basis_row.get("prewave_admissible") is True,
                "terminal_results_observed": basis_row.get("terminal_results_observed"),
            }
        )

    portfolios = set()
    for row in route_rows:
        for token in str(row["portfolio"]).split("_"):
            if token in {"T0", "T1", "T2", "T3"}:
                portfolios.add(token)
    if portfolios != {"T0", "T1", "T2", "T3"}:
        errors.append(f"PORTFOLIO_UNION_MISMATCH:{sorted(portfolios)}")

    claimed = candidate["verified_preconditions_to_be_machine_checked"]
    computed = {
        "surviving_leaf_count": len(route_rows),
        "all_current_contract_cores_identical_to_active_basis_registry_pin": all(
            row["core_contract_identical"] for row in route_rows
        )
        and len(route_rows) == 7,
        "all_active_routes_present": len(route_rows) == 7,
        "all_active_routes_frozen_admissible": all(
            row["frozen_admissible"] for row in route_rows
        )
        and len(route_rows) == 7,
        "all_active_route_blockers_empty": all(
            row["blockers_empty"] for row in route_rows
        )
        and len(route_rows) == 7,
        "all_active_routes_prewave_admissible": all(
            row["prewave_admissible"] for row in route_rows
        )
        and len(route_rows) == 7,
        "all_active_route_terminal_results_observed_zero": all(
            row["terminal_results_observed"] == 0 for row in route_rows
        )
        and len(route_rows) == 7,
    }
    if computed != claimed:
        errors.append(f"CANDIDATE_PRECONDITION_ACCOUNTING_MISMATCH:{computed!r}!={claimed!r}")

    result = {
        "schema": "PROJECT_BRAIN_SEVEN_SCOPE_LEAF_ACTIVE_ROUTE_REUSE_VERIFICATION_V1",
        "status": "PASS" if not errors else "FAIL",
        "historical_registry_commit": old_commit,
        "surviving_leaf_count": len(route_rows),
        "portfolio_union": sorted(portfolios),
        "new_scope_route_construction_required": False if not errors else None,
        "acceptance_credit_delta": 0,
        "terminal_cases_consumed": 0,
        "errors": errors,
        "routes": route_rows,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
