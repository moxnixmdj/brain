"""Fail-closed immutable terminal receipt transport verifier.

A terminal receipt is transport-eligible only when the immutable receipt itself
contains the binding blob identity and that identity equals the Git blob hash of
the current binding file. Direct summaries without a per-route binding blob are
reported as IDENTITY_ONLY when a separately frozen historical hash matches; they
never receive transported-proof status from that summary alone.

This verifier grants no acceptance, capability, family, execution, or promotion
credit. It proves only that replay is unnecessary for already-observed evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TERMINAL_RECEIPT_TRANSPORT_MANIFEST_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_TERMINAL_RECEIPT_TRANSPORT_VERDICT_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "transport_eligible_count": 0,
        "identity_only_count": 0,
        "blocked_count": 0,
        "rows": [],
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def git_blob_sha_bytes(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def _parent_rows(wave: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {}
    raw = (
        wave.get("reduction_input", {})
        .get("wave", {})
        .get("parent_portfolio_receipts", {})
    )
    if not isinstance(raw, Mapping):
        return result
    for portfolio, rows in raw.items():
        if isinstance(portfolio, str) and isinstance(rows, list):
            result[portfolio] = [r for r in rows if isinstance(r, Mapping)]
    return result


def evaluate(
    manifest: Mapping[str, Any],
    wave: Mapping[str, Any],
    current_blob_shas: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []
    if manifest.get("schema") != SCHEMA:
        return _fail("MANIFEST_SCHEMA_INVALID")

    if wave.get("status") != "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        errors.append("WAVE_STATUS_NOT_IMMUTABLE_PASS")
    public_runner = wave.get("public_runner")
    if not isinstance(public_runner, Mapping) or public_runner.get("conclusion") != "success":
        errors.append("WAVE_PUBLIC_RUNNER_NOT_SUCCESS")
    guards = wave.get("result_guards")
    if not isinstance(guards, Mapping):
        errors.append("WAVE_RESULT_GUARDS_MISSING")
        guards = {}
    if guards.get("no_case_replacement") is not True:
        errors.append("CASE_REPLACEMENT_NOT_PROVEN_ABSENT")
    if guards.get("no_tuning_replay") is not True:
        errors.append("TUNING_REPLAY_NOT_PROVEN_ABSENT")
    if guards.get("result_to_runtime_feedback_during_wave") is not False:
        errors.append("RESULT_TO_RUNTIME_FEEDBACK_NOT_PROVEN_ABSENT")

    rows = manifest.get("bindings")
    if not isinstance(rows, list) or not rows:
        return _fail("BINDINGS_NOT_LIST")

    parent = _parent_rows(wave)
    direct = wave.get("direct_terminal_population", {}).get("routes", {})
    if not isinstance(direct, Mapping):
        direct = {}

    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"BINDING_ROW_INVALID:{i}")
            continue
        rid = row.get("id")
        behavior = row.get("behavior_id")
        path = row.get("current_binding_path")
        anchor = row.get("receipt_anchor")
        if not all(isinstance(x, str) and x for x in (rid, behavior, path, anchor)):
            errors.append(f"BINDING_ROW_FIELDS_INVALID:{i}")
            continue

        current_sha = current_blob_shas.get(path)
        row_errors: list[str] = []
        anchored = False
        identity = False
        evidence: list[str] = []

        if anchor == "PARENT_RECEIPT_BINDING_BLOB":
            portfolios = row.get("required_portfolios")
            if not isinstance(portfolios, list) or not portfolios or any(
                not isinstance(x, str) or not x for x in portfolios
            ):
                row_errors.append("REQUIRED_PORTFOLIOS_INVALID")
            else:
                anchored = True
                observed_binding_shas: set[str] = set()
                for portfolio in portfolios:
                    matches = [
                        r for r in parent.get(portfolio, [])
                        if r.get("behavior_id") == behavior
                    ]
                    if len(matches) != 1:
                        anchored = False
                        row_errors.append(f"PARENT_RECEIPT_COUNT_INVALID:{portfolio}")
                        continue
                    receipt = matches[0]
                    evidence.append(str(receipt.get("case_id")))
                    binding_blob = receipt.get("binding_blob")
                    if isinstance(binding_blob, str):
                        observed_binding_shas.add(binding_blob)
                    else:
                        anchored = False
                        row_errors.append(f"PARENT_BINDING_BLOB_MISSING:{portfolio}")
                    for key, expected in (
                        ("direct_instrumentation_pass", True),
                        ("parent_terminal_acceptance_pass", True),
                        ("case_replaced", False),
                        ("tuning_replay", False),
                        ("result_to_runtime_feedback", False),
                    ):
                        if receipt.get(key) is not expected:
                            anchored = False
                            row_errors.append(f"PARENT_RECEIPT_GUARD_INVALID:{portfolio}:{key}")
                if len(observed_binding_shas) != 1:
                    anchored = False
                    row_errors.append("PARENT_BINDING_BLOBS_DISAGREE")
                elif isinstance(current_sha, str):
                    receipt_sha = next(iter(observed_binding_shas))
                    identity = current_sha == receipt_sha
                    if not identity:
                        row_errors.append("CURRENT_BINDING_DIFFERS_FROM_RECEIPT_BINDING")
        elif anchor == "DIRECT_SUMMARY_ONLY":
            summary = direct.get(behavior)
            expected_historical_sha = row.get("expected_historical_blob_sha")
            identity = (
                isinstance(current_sha, str)
                and isinstance(expected_historical_sha, str)
                and current_sha == expected_historical_sha
            )
            if not identity:
                row_errors.append("CURRENT_BINDING_DIFFERS_FROM_FROZEN_HISTORICAL_ASSERTION")
            if not isinstance(summary, Mapping):
                row_errors.append("DIRECT_SUMMARY_MISSING")
            else:
                cases = summary.get("cases")
                passes = summary.get("passes")
                minimum_cases = row.get("minimum_cases")
                if not (
                    isinstance(cases, int)
                    and isinstance(passes, int)
                    and isinstance(minimum_cases, int)
                    and cases >= minimum_cases
                    and passes == cases
                ):
                    row_errors.append("DIRECT_SUMMARY_NOT_ALL_PASS_OR_TOO_SMALL")
                else:
                    evidence.append(f"DIRECT::{behavior}::{passes}/{cases}")
            anchored = False
        else:
            row_errors.append("RECEIPT_ANCHOR_MODE_INVALID")

        if row_errors:
            state = "BLOCKED"
        elif identity and anchored:
            state = "TRANSPORT_ELIGIBLE"
        elif identity:
            state = "IDENTITY_ONLY"
        else:
            state = "BLOCKED"

        out_rows.append(
            {
                "id": rid,
                "behavior_id": behavior,
                "binding_path": path,
                "current_blob_sha": current_sha,
                "binding_identity": identity,
                "receipt_binding_anchored": anchored,
                "state": state,
                "evidence": evidence,
                "errors": sorted(set(row_errors)),
                "acceptance_credit_authority": False,
            }
        )

    counts = {
        "transport_eligible_count": sum(r["state"] == "TRANSPORT_ELIGIBLE" for r in out_rows),
        "identity_only_count": sum(r["state"] == "IDENTITY_ONLY" for r in out_rows),
        "blocked_count": sum(r["state"] == "BLOCKED" for r in out_rows),
    }
    expected = manifest.get("expected_live_counts")
    if isinstance(expected, Mapping):
        for key, actual in counts.items():
            if expected.get(key) != actual:
                errors.append(f"LIVE_COUNT_MISMATCH:{key}:{actual}!={expected.get(key)}")

    errors = sorted(set(errors))
    return {
        "schema": VERDICT_SCHEMA,
        "status": "PASS__IMMUTABLE_RECEIPT_TRANSPORT_CLASSIFIED" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        **counts,
        "rows": out_rows,
        "rule": (
            "TRANSPORT_REQUIRES_CURRENT_GIT_BLOB_EQUALS_IMMUTABLE_RECEIPT_BINDING_BLOB__"
            "DIRECT_SUMMARY_WITHOUT_BINDING_BLOB_IS_IDENTITY_ONLY__"
            "NO_ACCEPTANCE_CREDIT_FROM_TRANSPORT_ALONE"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate_live(manifest_path: Path, wave_path: Path, repo_root: Path = ROOT) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    wave = json.loads(wave_path.read_text(encoding="utf-8"))
    bindings = manifest.get("bindings")
    if not isinstance(bindings, list):
        return _fail("BINDINGS_NOT_LIST")
    current: dict[str, str] = {}
    try:
        for row in bindings:
            if not isinstance(row, Mapping):
                continue
            path = row.get("current_binding_path")
            if isinstance(path, str) and path:
                current[path] = git_blob_sha_bytes((repo_root / path).read_bytes())
    except OSError as exc:
        return _fail("CURRENT_BINDING_READ_FAILED:" + str(exc))
    return evaluate(manifest, wave, current)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument(
        "--wave",
        type=Path,
        default=ROOT / "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json",
    )
    args = ap.parse_args()
    out = evaluate_live(args.manifest, args.wave)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
