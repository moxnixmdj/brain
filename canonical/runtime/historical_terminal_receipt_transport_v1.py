"""Fail-closed transport of immutable terminal evidence to unchanged current bindings.

This reducer grants zero acceptance, capability, family, execution, or promotion
credit. It answers one narrower question: may an immutable terminal receipt be
treated as evidence under the current binding without replay when the historical
execution-snapshot blob and current binding blob are byte-identical?
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "canonical/governance/HISTORICAL_TERMINAL_RECEIPT_TRANSPORT_V1.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _current_blob_sha(rel: str) -> str:
    return _git("hash-object", rel)


def _historical_blob_sha(commit: str, rel: str) -> str:
    return _git("rev-parse", f"{commit}:{rel}")


def _nested(value: Mapping[str, Any], path: list[str]) -> Any:
    cur: Any = value
    for key in path:
        if not isinstance(cur, Mapping) or key not in cur:
            return None
        cur = cur[key]
    return cur


def evaluate(
    config: Mapping[str, Any],
    wave: Mapping[str, Any],
    binding_verification: Mapping[str, Any],
    bindings: Mapping[str, Mapping[str, Any]],
    current_blob_shas: Mapping[str, str],
    historical_blob_shas: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_snapshot = config.get("execution_snapshot_commit")

    if wave.get("execution_snapshot_commit") != expected_snapshot:
        errors.append("EXECUTION_SNAPSHOT_MISMATCH")
    required_wave_status = (config.get("terminal_wave") or {}).get("required_status")
    if wave.get("status") != required_wave_status:
        errors.append("TERMINAL_WAVE_STATUS_MISMATCH")

    guards = wave.get("result_guards")
    if not isinstance(guards, Mapping):
        errors.append("TERMINAL_WAVE_GUARDS_MISSING")
        guards = {}
    if guards.get("no_case_replacement") is not True:
        errors.append("CASE_REPLACEMENT_NOT_FAIL_CLOSED")
    if guards.get("no_tuning_replay") is not True:
        errors.append("TUNING_REPLAY_NOT_FAIL_CLOSED")
    if guards.get("result_to_runtime_feedback_during_wave") is not False:
        errors.append("RESULT_TO_RUNTIME_FEEDBACK_PRESENT")
    if guards.get("direct_route_duplicate_execution_count") != 0:
        errors.append("DIRECT_ROUTE_DUPLICATE_EXECUTION_PRESENT")

    required_verification_status = (config.get("current_binding_verification") or {}).get("required_status")
    if binding_verification.get("status") != required_verification_status:
        errors.append("CURRENT_BINDING_VERIFICATION_STATUS_MISMATCH")

    verified_jobs = binding_verification.get("verified_jobs")
    verified_by_behavior: dict[str, Mapping[str, Any]] = {}
    if isinstance(verified_jobs, list):
        for row in verified_jobs:
            if isinstance(row, Mapping) and isinstance(row.get("behavior_id"), str):
                verified_by_behavior[row["behavior_id"]] = row
    else:
        errors.append("CURRENT_BINDING_VERIFIED_JOBS_MISSING")

    direct_routes = ((wave.get("direct_terminal_population") or {}).get("routes") or {})
    parent_receipts = (((wave.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts") or {})

    route_results: list[dict[str, Any]] = []
    routes = config.get("routes")
    if not isinstance(routes, list) or not routes:
        errors.append("TRANSPORT_ROUTES_MISSING")
        routes = []

    for route in routes:
        if not isinstance(route, Mapping):
            errors.append("INVALID_TRANSPORT_ROUTE")
            continue

        rid = str(route.get("id"))
        behavior = route.get("behavior_id")
        binding_path = route.get("binding_path")
        expected_blob = route.get("expected_binding_blob_sha")
        route_errors: list[str] = []

        if not all(isinstance(x, str) and x for x in (behavior, binding_path, expected_blob)):
            route_errors.append("ROUTE_IDENTITY_INVALID")
        else:
            binding = bindings.get(binding_path)
            if not isinstance(binding, Mapping):
                route_errors.append("CURRENT_BINDING_DOCUMENT_MISSING")
                binding = {}
            if binding.get("behavior_id") != behavior:
                route_errors.append("CURRENT_BINDING_BEHAVIOR_MISMATCH")

            if current_blob_shas.get(binding_path) != expected_blob:
                route_errors.append("CURRENT_BINDING_BLOB_MISMATCH")
            if historical_blob_shas.get(binding_path) != expected_blob:
                route_errors.append("HISTORICAL_BINDING_BLOB_MISMATCH")
            if current_blob_shas.get(binding_path) != historical_blob_shas.get(binding_path):
                route_errors.append("HISTORICAL_CURRENT_BINDING_NOT_IDENTICAL")

            verified = verified_by_behavior.get(str(behavior))
            if not isinstance(verified, Mapping):
                route_errors.append("INDEPENDENT_CURRENT_BINDING_VERIFICATION_MISSING")
            else:
                if verified.get("binding_path") != binding_path:
                    route_errors.append("VERIFIED_BINDING_PATH_MISMATCH")
                if verified.get("binding_blob_sha") != expected_blob:
                    route_errors.append("VERIFIED_BINDING_BLOB_MISMATCH")
                if verified.get("conclusion") != "success":
                    route_errors.append("VERIFIED_BINDING_JOB_NOT_SUCCESS")

            mode = route.get("evidence_mode")
            if mode == "DIRECT_TERMINAL_ROUTE":
                evidence = direct_routes.get(behavior) if isinstance(direct_routes, Mapping) else None
                if not isinstance(evidence, Mapping):
                    route_errors.append("DIRECT_TERMINAL_ROUTE_RECEIPT_MISSING")
                else:
                    if evidence.get("cases") != route.get("expected_cases"):
                        route_errors.append("DIRECT_TERMINAL_CASE_COUNT_MISMATCH")
                    if evidence.get("passes") != route.get("expected_passes"):
                        route_errors.append("DIRECT_TERMINAL_PASS_COUNT_MISMATCH")
                    if evidence.get("passes") != evidence.get("cases"):
                        route_errors.append("DIRECT_TERMINAL_ROUTE_NOT_ALL_PASS")
            elif mode == "PARENT_PORTFOLIO_RECEIPTS":
                expected_portfolios = route.get("expected_portfolios")
                if not isinstance(expected_portfolios, list) or not expected_portfolios:
                    route_errors.append("EXPECTED_PARENT_PORTFOLIOS_MISSING")
                else:
                    for portfolio in expected_portfolios:
                        rows = parent_receipts.get(portfolio) if isinstance(parent_receipts, Mapping) else None
                        matches = [
                            row for row in rows or []
                            if isinstance(row, Mapping) and row.get("behavior_id") == behavior
                        ]
                        if len(matches) != 1:
                            route_errors.append(f"PARENT_RECEIPT_COUNT_INVALID:{portfolio}")
                            continue
                        row = matches[0]
                        if row.get("binding_blob") != expected_blob:
                            route_errors.append(f"PARENT_BINDING_BLOB_MISMATCH:{portfolio}")
                        if row.get("direct_instrumentation_pass") is not True:
                            route_errors.append(f"PARENT_DIRECT_INSTRUMENTATION_FAIL:{portfolio}")
                        if row.get("parent_terminal_acceptance_pass") is not True:
                            route_errors.append(f"PARENT_TERMINAL_ACCEPTANCE_FAIL:{portfolio}")
                        if row.get("case_replaced") is not False:
                            route_errors.append(f"PARENT_CASE_REPLACED:{portfolio}")
                        if row.get("tuning_replay") is not False:
                            route_errors.append(f"PARENT_TUNING_REPLAY:{portfolio}")
                        if row.get("result_to_runtime_feedback") is not False:
                            route_errors.append(f"PARENT_RESULT_FEEDBACK:{portfolio}")
            else:
                route_errors.append("UNKNOWN_EVIDENCE_MODE")

            caveat_path = route.get("scope_caveat_field")
            caveat_token = route.get("scope_caveat_must_contain")
            if isinstance(caveat_path, list) and caveat_path:
                caveat = _nested(binding, [str(x) for x in caveat_path])
                if not isinstance(caveat, str) or (
                    isinstance(caveat_token, str) and caveat_token not in caveat
                ):
                    route_errors.append("REQUIRED_SCOPE_CAVEAT_MISSING")

        errors.extend(f"{rid}:{e}" for e in route_errors)
        transported = not route_errors
        route_results.append(
            {
                "id": rid,
                "behavior_id": behavior,
                "binding_path": binding_path,
                "binding_blob_sha": expected_blob,
                "transported_terminal_evidence": transported,
                "historical_current_binding_identical": transported,
                "acceptance_predicate": route.get("target_predicate"),
                "acceptance_predicate_closed": False,
                "full_scope_noninferiority_proved": False,
                "remaining_acceptance_obligation": route.get("remaining_acceptance_obligation"),
                "fresh_terminal_replay_required": False if transported else None,
                "errors": route_errors,
            }
        )

    pass_transport = not errors and bool(route_results) and all(
        row["transported_terminal_evidence"] for row in route_results
    )
    return {
        "schema": "PROJECT_BRAIN_HISTORICAL_TERMINAL_RECEIPT_TRANSPORT_VERDICT_V1",
        "status": (
            "PASS__IMMUTABLE_TERMINAL_EVIDENCE_TRANSPORTED__FULL_SCOPE_ACCEPTANCE_STILL_OPEN__ZERO_CREDIT"
            if pass_transport
            else "FAIL_CLOSED"
        ),
        "pass": pass_transport,
        "errors": sorted(set(errors)),
        "transported_route_count": sum(r["transported_terminal_evidence"] for r in route_results),
        "route_count": len(route_results),
        "routes": route_results,
        "acceptance_predicates_closed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "terminal_replay_executed": False,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "execution_authority": False,
        "rule": (
            "EXACT_BINDING_IDENTITY_MAY_TRANSPORT_IMMUTABLE_TERMINAL_EVIDENCE_WITHOUT_REPLAY__"
            "TRANSPORT_DOES_NOT_PROVE_MATCHED_NONINFERIORITY_OR_SCOPE_COMPLETENESS"
        ),
    }


def evaluate_live() -> dict[str, Any]:
    config = _load(CONFIG_PATH)
    wave_spec = config["terminal_wave"]
    verify_spec = config["current_binding_verification"]
    wave = _load(ROOT / wave_spec["path"])
    binding_verification = _load(ROOT / verify_spec["path"])

    bindings: dict[str, Mapping[str, Any]] = {}
    current: dict[str, str] = {}
    historical: dict[str, str] = {}
    snapshot = str(config["execution_snapshot_commit"])
    for route in config["routes"]:
        rel = str(route["binding_path"])
        bindings[rel] = _load(ROOT / rel)
        current[rel] = _current_blob_sha(rel)
        historical[rel] = _historical_blob_sha(snapshot, rel)

    return evaluate(config, wave, binding_verification, bindings, current, historical)


def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
