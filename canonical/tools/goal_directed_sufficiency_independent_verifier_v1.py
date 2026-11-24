#!/usr/bin/env python3
"""Different-code local recheck for the goal-directed sufficiency receipt.

This script intentionally does NOT import the gate or the formal runner. It uses
only the Python standard library, recomputes canonical digests, reconstructs
expected decision classes from the frozen case bundle, checks all negative
refusals, inspects the external store, and supplies its own run reference.

PASS means a separate local process with different code found no discrepancy.
It is NOT independent cloud attestation, benchmark verification, GUI/DOM
oracle verification, own-weights qualification, or §6 completion.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import itertools
import json
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PASS = "LOCAL_DIFFERENT_CODE_RECHECK_PASS__NOT_INDEPENDENT_ATTESTATION"
REFUSE = "LOCAL_DIFFERENT_CODE_RECHECK_REFUSED"
EXPECTED_STATUS = {
    "A1_READ_ONLY": "READ_ONLY__NO_STORE_WRITE",
    "A2_CONFLICT_ASK": "ASK__SETTLED_NAMED_GAP",
    "A3_SAVE_ABSTRACT": "SAVE__ABSTRACTION_ADMITTED",
    "N1_CALLER_AUTHORITY": "REFUSED__CALLER_AUTHORITY_DENIED",
    "N2_RAW_RECORDING": "REFUSED__RAW_EXPERIENCE_IS_NOT_A_RULE",
    "N3_SAME_STATE_HIDDEN_PRECONDITION": "REFUSED__OBSERVABLE_VOCABULARY_INSUFFICIENT",
    "N4_SEPARATION_IMPOSSIBLE": "REFUSED__OBSERVABLE_VOCABULARY_INSUFFICIENT",
    "N5_DYNAMIC_STALE_UPDATE": "REFUSED__DYNAMIC_UPDATE_REQUIRES_FRESH_OBSERVATION",
    "N6_OUTSIDE_HYPOTHESIS_SPACE": "REFUSED__EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE",
    "N7_OPEN_HYPOTHESIS_SPACE": "REFUSED__OPEN_HYPOTHESIS_SPACE",
    "N8_INSTRUMENT_BLIND": "REFUSED__INSTRUMENT_BLIND",
    "N9_UNADMITTED_FRESH_INSTANCES": "REFUSED__ADMISSION_NOT_REACHED_ON_FRESH_INSTANCES",
}
ADMITTED = frozenset({"A1_READ_ONLY", "A2_CONFLICT_ASK", "A3_SAVE_ABSTRACT"})
AUTHORITY_KEYS = frozenset({
    "force_learn", "store_now", "trust_retrieved", "independent_verified",
    "execution_authorized", "benchmark_score_claimed", "truth_achieved",
})
FORBIDDEN_TOKENS = (
    "path", "argv", "content", "trace", "answer", "reward", "outcome",
    "exact_action", "source_bytes", "raw", "gold",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forbidden_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            lowered = label.lower()
            if any(token in lowered for token in FORBIDDEN_TOKENS):
                found.append(label)
            found.extend(forbidden_fields(child, label))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(token in lowered for token in FORBIDDEN_TOKENS):
            found.append(prefix or "<string>")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for i, child in enumerate(value):
            found.extend(forbidden_fields(child, f"{prefix}[{i}]"))
    return sorted(set(found))


def facts(value: Any) -> frozenset[str]:
    if isinstance(value, Mapping):
        return frozenset(str(k) for k, v in value.items() if bool(v))
    return frozenset(str(x) for x in (value or ()))


def evidence_rows(case: Mapping[str, Any]) -> list[tuple[frozenset[str], bool]]:
    return [(facts(row.get("facts")), bool(row.get("outcome")))
            for row in (case.get("evidence") or []) if isinstance(row, Mapping)]


def insufficiency(rows: Sequence[tuple[frozenset[str], bool]]) -> bool:
    by_state: dict[frozenset[str], set[bool]] = {}
    for state, ok in rows:
        by_state.setdefault(state, set()).add(ok)
    if any(len(outcomes) > 1 for outcomes in by_state.values()):
        return True
    successes = [state for state, ok in rows if ok]
    failures = [state for state, ok in rows if not ok]
    if not successes or not failures:
        return False
    shared = set(successes[0])
    for state in successes[1:]:
        shared &= set(state)
    if len(shared) > 8:
        return False
    for failure in failures:
        if frozenset(shared) <= failure:
            return True
    return False


def informative_contrast(case: Mapping[str, Any]) -> bool:
    """Independent reconstruction of the small applicability version space."""
    rows = evidence_rows(case)
    successes = [state for state, ok in rows if ok]
    failures = [state for state, ok in rows if not ok]
    if not successes or not failures:
        return False
    shared = sorted(set(successes[0]).intersection(*(set(s) for s in successes[1:])))
    if len(shared) > 8:
        return False
    requirements: list[frozenset[str]] = []
    for n in range(len(shared) + 1):
        for combo in itertools.combinations(shared, n):
            need = frozenset(combo)
            if any(need <= failure for failure in failures):
                continue
            requirements.append(need)
    if len(requirements) < 2:
        return False
    states = [facts(row) for row in (case.get("candidate_states") or [])]
    states.extend(state for state, _ in rows)
    for state in states:
        admits = {need <= state for need in requirements}
        if len(admits) > 1:
            return True
    return False


def has_caller_authority(case: Mapping[str, Any]) -> bool:
    if any(bool(case.get(key)) for key in AUTHORITY_KEYS):
        return True
    nested = case.get("caller_flags")
    return isinstance(nested, Mapping) and any(bool(nested.get(key)) for key in AUTHORITY_KEYS)


def reading_suffices(case: Mapping[str, Any]) -> bool:
    instruction = str(case.get("instruction") or "")
    elements = (case.get("observation") or {}).get("elements") or []
    has_save = any(str((e or {}).get("label") or (e or {}).get("text") or "").lower() == "save"
                   for e in elements if isinstance(e, Mapping))
    return '"Save"' in instruction and "click" in instruction.lower() and has_save


def classify(case: Mapping[str, Any]) -> str:
    """Recompute the frozen expected class without importing the implementation."""
    if has_caller_authority(case):
        return "REFUSED__CALLER_AUTHORITY_DENIED"
    if reading_suffices(case):
        return "READ_ONLY__NO_STORE_WRITE"
    payload = case.get("candidate_store_payload")
    if payload is not None:
        if forbidden_fields(payload):
            return "REFUSED__RAW_EXPERIENCE_IS_NOT_A_RULE"
        if not bool(case.get("candidate_store_payload_admitted")):
            return "REFUSED__STORE_CANDIDATE_NOT_ADMITTED"
    rows = evidence_rows(case)
    if insufficiency(rows):
        return "REFUSED__OBSERVABLE_VOCABULARY_INSUFFICIENT"
    versions = [int(row.get("version", 0)) for row in (case.get("evidence") or [])
                if isinstance(row, Mapping)]
    if int(case.get("current_version") or 0) > max(versions or [0]):
        return "REFUSED__DYNAMIC_UPDATE_REQUIRES_FRESH_OBSERVATION"
    missing = facts(case.get("goal_facts")) - facts(case.get("scan_facts"))
    if missing:
        regime_rows = case.get("regime_rows") or []
        probes = case.get("probes") or []
        oracle = str(case.get("oracle_name") or "none")
        if not regime_rows or not probes or oracle == "none":
            return "REFUSED__NO_CLOSED_HYPOTHESIS_SPACE"
        if oracle == "outside_space":
            return "REFUSED__EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE"
        if len(regime_rows) > 24:
            return "REFUSED__OPEN_HYPOTHESIS_SPACE"
        signatures = {json.dumps(row.get("outcomes") or {}, sort_keys=True) for row in regime_rows}
        if len(signatures) <= 1:
            return "REFUSED__INSTRUMENT_BLIND"
        if oracle == "latest_email":
            return "ASK__SETTLED_NAMED_GAP"
        return "REFUSED__QUESTION_NOT_SETTLED"
    if not informative_contrast(case):
        return "REFUSED__NO_DECISIVE_CONTRAST"
    plan = [str(x) for x in (case.get("plan_sketch") or ())]
    fresh = case.get("fresh_instances") or []
    if not plan or not fresh:
        return "REFUSED__ADMISSION_NOT_REACHED_ON_FRESH_INSTANCES"
    all_reach = all([str(x) for x in ((row or {}).get("expected_plan") or ())] == plan
                    for row in fresh if isinstance(row, Mapping))
    if not all_reach:
        return "REFUSED__ADMISSION_NOT_REACHED_ON_FRESH_INSTANCES"
    return "SAVE__ABSTRACTION_ADMITTED"


def truth_ok(payload: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    truth = payload.get("truth") or {}
    expected = {
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "written_to_weights": False,
        "own_weights": False,
        "carrier_qualified": False,
        "execution_authorized": False,
        "patch_published": False,
        "independent_attestation": False,
        "independent_cloud_verifier": False,
        "gui_dom_oracle": False,
        "hardest_open_nov_2026_score": "NO_SCORE",
        "acceptance_credit_delta": 0,
        "section_6": "NOT_DONE",
        "truth_achieved": False,
        "completion_claim": False,
    }
    if any(truth.get(k) != v for k, v in expected.items()):
        return False
    if receipt.get("independent_attestation") is not False:
        return False
    if payload.get("frontier_score_claim") is not False:
        return False
    return payload.get("external_sources_build_time_only") is True


def check(receipt_path: Path, prereg_path: Path, store_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload = receipt.get("canonical_payload")
    if not isinstance(payload, Mapping):
        return {"status": REFUSE, "reason": "MISSING_CANONICAL_PAYLOAD"}
    prereg_hash = file_sha256(prereg_path)
    script_hash = file_sha256(Path(__file__).resolve())
    receipt_digest_ok = receipt.get("receipt_sha256") == digest(payload)
    prereg_digest_ok = payload.get("prereg_sha256") == prereg_hash
    script_digest_ok = payload.get("verifier_script_sha256") == script_hash

    cases = payload.get("case_bundle") or []
    decisions = payload.get("decisions") or []
    decision_ok = len(cases) == len(decisions) == len(EXPECTED_STATUS)
    recomputed: dict[str, str] = {}
    if decision_ok:
        for case, row in zip(cases, decisions):
            case_id = str((case or {}).get("case_id") or "?")
            expected = classify(case)
            recomputed[case_id] = expected
            if case_id not in EXPECTED_STATUS or expected != EXPECTED_STATUS[case_id]:
                decision_ok = False
            if (row or {}).get("case_id") != case_id or (row or {}).get("decision") != expected:
                decision_ok = False
            if case_id not in ADMITTED and not str((row or {}).get("decision") or "").startswith("REFUSED"):
                decision_ok = False
            if (row or {}).get("store_write") is not False:
                decision_ok = False

    counts = payload.get("counts") or {}
    negative_refusals = sum(1 for case in cases
                            if str((case or {}).get("case_id")) not in ADMITTED
                            and classify(case).startswith("REFUSED"))
    counts_ok = (
        counts.get("case_count") == len(EXPECTED_STATUS)
        and counts.get("admitted_arms") == 3
        and counts.get("negative_arms") == 9
        and counts.get("expected_decision_matches") == len(EXPECTED_STATUS)
        and counts.get("negative_refusals") == negative_refusals == 9
        and int(counts.get("question_probes") or 0) >= 1
        and counts.get("store_write_count") == 1
        and counts.get("verifier_processes") == 1
        and not (counts.get("forbidden_store_fields") or [])
        and counts.get("runtime_model_calls") == 0
        and counts.get("runtime_network_calls") == 0
        and counts.get("parameters_written") == 0
    )

    store_action = payload.get("store_action") or {}
    rule = store_action.get("rule") or {}
    store_meta = store_action.get("store") or {}
    store_bad = forbidden_fields(rule)
    store_file_ok = store_path.is_file()
    computed_store_digest = None
    store_rules_bad: list[str] = []
    if store_file_ok:
        store_data = json.loads(store_path.read_text(encoding="utf-8"))
        rules = store_data.get("rules") or []
        store_rules_bad = forbidden_fields(rules)
        recomputed_payload = {
            "schema": store_data.get("schema"),
            "authority": store_data.get("authority"),
            "rules": rules,
        }
        computed_store_digest = digest(recomputed_payload)
    store_digest_ok = (
        store_file_ok
        and computed_store_digest is not None
        and computed_store_digest == store_data.get("digest")
        and computed_store_digest == store_meta.get("digest")
        and store_meta.get("status") == "PASS__STORE_VERIFIED"
        and bool(store_meta.get("store_write"))
        and not store_bad
        and not store_rules_bad
        and store_action.get("decision") == "SAVE__ABSTRACTION_ADMITTED"
        and bool(store_action.get("store_write"))
    )

    edit = payload.get("store_editability") or {}
    editability_ok = (
        bool(edit.get("removal_refused"))
        and bool(edit.get("restore_verified"))
        and bool(edit.get("restart_digest_matches"))
        and (edit.get("missing") or {}).get("status") == "STORE_MISSING__REFUSE"
        and (edit.get("before") or {}).get("digest") == computed_store_digest
        and (edit.get("after") or {}).get("digest") == computed_store_digest
    )

    refs = payload.get("run_refs") or {}
    refs_ok = bool(refs.get("run_refs_distinct")) and len({
        refs.get("producer_run_ref"), refs.get("decision_run_ref"),
        refs.get("store_run_ref"), refs.get("restart_run_ref")
    }) == 4
    run_ref = secrets.token_hex(8)
    while run_ref in {refs.get("producer_run_ref"), refs.get("decision_run_ref"),
                      refs.get("store_run_ref"), refs.get("restart_run_ref")}:
        run_ref = secrets.token_hex(8)

    checks = {
        "receipt_digest_match": receipt_digest_ok,
        "prereg_digest_match": prereg_digest_ok,
        "script_digest_match": script_digest_ok,
        "decision_classes_match": decision_ok,
        "counts_match": counts_ok,
        "store_digest_match": store_digest_ok,
        "store_clean": not store_bad and not store_rules_bad,
        "store_editability_match": editability_ok,
        "run_refs_distinct": refs_ok,
        "truth_fields_false": truth_ok(payload, receipt),
    }
    status = PASS if all(checks.values()) else REFUSE
    return {
        "schema": "BRAIN_GOAL_DIRECTED_SUFFICIENCY_LOCAL_RECHECK_V1",
        "status": status,
        "authority": "NONE__DIFFERENT_CODE_LOCAL_PROCESS",
        "run_ref": run_ref,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "checks": checks,
        "checked_decisions": len(recomputed),
        "recomputed_decision_classes": recomputed,
        "prereg_sha256": prereg_hash,
        "verifier_script_sha256": script_hash,
        "receipt_sha256": receipt.get("receipt_sha256"),
        "recomputed_receipt_sha256": digest(payload),
        "store_digest": computed_store_digest,
        "store_forbidden_fields": sorted(set(store_bad + store_rules_bad)),
        "independent_attestation": False,
        "independent_cloud_verifier": False,
        "benchmark_score_verified": False,
        "gui_dom_oracle": False,
        "section_6": "NOT_DONE",
        "completion_claim": False,
        "wall_seconds": round(time.perf_counter() - started, 6),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--prereg", required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = check(Path(args.receipt), Path(args.prereg), Path(args.store))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
