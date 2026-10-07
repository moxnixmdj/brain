"""Fail-closed verifier for the Vision non-chart direct benchmark binding."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "canonical/governance/VISION_NONCHART_QWEN3VL4B_DIRECT_BENCHMARK_BINDING_20261005_V1.json"
EXPECTED_SOURCES = {
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":
        "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/VISION_NONCHART_FOUR_LEAF_PARTITION_20261005_V1.json":
        "a95f412b365c8927547477232e8516c81e16abaf",
    "canonical/governance/CHARTOGRAPHY_QWEN3_VL4B_EXACT_ARTIFACT_MANIFEST_20261005_V1.json":
        "fc60bd458243e9ce721ca29fb986f067c0b70417",
    "canonical/verification/CHARTOGRAPHY_QWEN3_VL4B_PUBLIC_SOURCE_VERIFICATION_20261005_V1.json":
        "22dc5bddb1b5144c601d65431494c0eab556b874",
}
EXPECTED_LEAVES = {
    "dense documents",
    "screenshots",
    "diagrams",
    "complex real-world imagery",
}
EXPECTED_BENCHMARKS = {
    "dense documents": {"DocVQA_test", "MMLongBenchDoc"},
    "screenshots": {"ScreenSpot Pro"},
    "diagrams": {"AI2D_w.M."},
    "complex real-world imagery": {"RealWorldQA"},
}


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    for path, expected in EXPECTED_SOURCES.items():
        if _blob(path) != expected:
            errors.append("SOURCE_BLOB_DRIFT:" + path)

    c = _load(CANDIDATE)
    if c.get("target_predicate") != "VISION_DENSE_NONCHART_SCOPE":
        errors.append("TARGET_PREDICATE_DRIFT")

    authority = c.get("authority")
    if not isinstance(authority, Mapping):
        errors.append("AUTHORITY_NOT_MAPPING")
        authority = {}

    subject = authority.get("exact_subject_manifest")
    if not isinstance(subject, Mapping):
        errors.append("SUBJECT_NOT_MAPPING")
    else:
        if subject.get("model") != "Qwen/Qwen3-VL-4B-Instruct":
            errors.append("SUBJECT_MODEL_DRIFT")
        if subject.get("revision") != "ebb281ec70b05090aa6165b016eac8ec08e71b17":
            errors.append("SUBJECT_REVISION_DRIFT")

    rows = c.get("direct_leaf_witnesses")
    if not isinstance(rows, list):
        errors.append("WITNESSES_NOT_LIST")
        rows = []

    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("WITNESS_NOT_MAPPING")
            continue
        leaf = row.get("leaf")
        if not isinstance(leaf, str):
            errors.append("LEAF_NOT_STRING")
            continue
        if leaf in seen:
            errors.append("DUPLICATE_LEAF:" + leaf)
        seen.add(leaf)
        benches = row.get("benchmark_witnesses")
        if not isinstance(benches, list):
            errors.append("BENCHMARKS_NOT_LIST:" + leaf)
            continue
        names = {
            x.get("benchmark")
            for x in benches
            if isinstance(x, Mapping) and isinstance(x.get("benchmark"), str)
        }
        if names != EXPECTED_BENCHMARKS.get(leaf, set()):
            errors.append("BENCHMARK_SET_DRIFT:" + leaf)
        for witness in benches:
            if not isinstance(witness, Mapping):
                errors.append("BENCHMARK_WITNESS_NOT_MAPPING:" + leaf)
                continue
            if witness.get("subject") != "Qwen3-VL-4B-Instruct":
                errors.append("BENCHMARK_SUBJECT_DRIFT:" + leaf)
            score = witness.get("score")
            if not isinstance(score, (int, float)):
                errors.append("BENCHMARK_SCORE_NOT_NUMERIC:" + leaf)

    if seen != EXPECTED_LEAVES:
        errors.append("LEAF_SET_DRIFT")

    public = c.get("primary_public_evidence")
    if not isinstance(public, Mapping):
        errors.append("PUBLIC_EVIDENCE_NOT_MAPPING")
    else:
        report = public.get("qwen3_vl_technical_report")
        if not isinstance(report, Mapping):
            errors.append("REPORT_NOT_MAPPING")
        else:
            if report.get("arxiv_id") != "2511.21631":
                errors.append("REPORT_ID_DRIFT")
            if report.get("table") != "Table 4: Performance of small-sized Qwen3-VL models and GPT-5-nano on visual benchmarks":
                errors.append("REPORT_TABLE_DRIFT")
            if report.get("subject_column") != "Qwen3-VL 4B / instruct":
                errors.append("REPORT_COLUMN_DRIFT")

    reduction = c.get("reduction")
    if not isinstance(reduction, Mapping):
        errors.append("REDUCTION_NOT_MAPPING")
        reduction = {}
    after = reduction.get("after")
    if not isinstance(after, Mapping):
        errors.append("AFTER_NOT_MAPPING")
        after = {}
    else:
        if after.get("exact_subject_direct_leaf_benchmark_witness_count") != 4:
            errors.append("DIRECT_WITNESS_COUNT_DRIFT")
        if after.get("semantically_unwitnessed_leaf_count") != 0:
            errors.append("UNWITNESSED_COUNT_DRIFT")
        if after.get("matched_opus55_comparator_bound") is not False:
            errors.append("COMPARATOR_OVERCLAIM")
        if after.get("brain_internalization_or_ownership_bound") is not False:
            errors.append("OWNERSHIP_OVERCLAIM")
        if after.get("acceptance_closed") is not False:
            errors.append("ACCEPTANCE_OVERCLAIM")

    accounting = c.get("accounting")
    if not isinstance(accounting, Mapping):
        errors.append("ACCOUNTING_NOT_MAPPING")
        accounting = {}
    for key in (
        "incremental_spend_usd",
        "new_reality_units_consumed",
        "terminal_cases_consumed",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key) != 0:
            errors.append("NONZERO_ACCOUNTING:" + key)

    for key in (
        "scheduling_authority",
        "execution_authority",
        "promotion_authority",
        "fresh_reality_authority",
    ):
        if c.get(key) is not False:
            errors.append("AUTHORITY_OVERCLAIM:" + key)

    ok = not errors
    return {
        "schema": "PROJECT_BRAIN_VISION_NONCHART_QWEN3VL4B_DIRECT_BENCHMARK_BINDING_VERIFIER_V1",
        "pass": ok,
        "status": (
            "PASS__FOUR_OF_FOUR_DIRECT_LEAF_WITNESSES_BOUND__MATCHED_COMPARATOR_AND_OWNERSHIP_REMAIN_OPEN__ZERO_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "direct_leaf_witness_count": 4 if ok else None,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0,
        "fresh_reality_authority": False,
        "rule": (
            "DIRECT_PUBLIC_BENCHMARK_COVERAGE_MAY_DELETE_SEMANTIC_ROUTE_SEARCH_ONLY;"
            "_IT_MUST_NOT_BE_PROMOTED_TO_MATCHED_OPUS_NONINFERIORITY_OR_BRAIN_OWNERSHIP"
        ),
    }


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
