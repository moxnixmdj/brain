#!/usr/bin/env python3
"""Finite adversarial false-negative benchmark for Tool Discovery retrieval.

This benchmark exercises the real residual-witness query compiler against a
frozen synthetic universe deliberately hostile to metadata-centric retrieval:
non-English-only text, empty/misleading metadata, code-only identifiers,
test-only clues, manifest-only clues, issues, commits, and exact benchmark
signatures.

It proves recall only for this declared finite fixture universe. Unsupported
open-world boundaries are carried separately as UNKNOWN and never counted as
closed or nonexistent.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import residual_witness_retrieval_compiler_v1 as compiler

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_RETRIEVAL_FALSE_NEGATIVE_BENCHMARK_V1"

SUPPORTED_FIXTURES = [
    {"id":"ZH_METADATA_ONLY","surface":"REPOSITORY_METADATA","payload":"这是一个用于工具发现和工具选择的项目。","trap":"NON_ENGLISH_METADATA_ONLY"},
    {"id":"AR_CODE_COMMENT_ONLY","surface":"CODE_CONTENT","payload":"# اكتشاف الأدوات واختيار الأدوات","trap":"NON_ENGLISH_CODE_ONLY"},
    {"id":"RU_DOC_ONLY","surface":"DOCUMENTATION","payload":"обнаружение инструментов и маршрутизация инструментов","trap":"NON_ENGLISH_DOC_ONLY"},
    {"id":"JA_DOC_ONLY","surface":"DOCUMENTATION","payload":"ツール探索 と ツール選択","trap":"NON_ENGLISH_DOC_ONLY"},
    {"id":"KO_ISSUE_ONLY","surface":"ISSUES_PRS","payload":"도구 탐색 및 도구 라우팅 관련 문제","trap":"NON_ENGLISH_ISSUE_ONLY"},
    {"id":"ES_WEB_ONLY","surface":"OPEN_WEB","payload":"descubrimiento de herramientas y selección de herramientas","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"FR_WEB_ONLY","surface":"OPEN_WEB","payload":"découverte d'outils et sélection d'outils","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"DE_WEB_ONLY","surface":"OPEN_WEB","payload":"Werkzeugentdeckung und Werkzeugauswahl","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"PT_WEB_ONLY","surface":"OPEN_WEB","payload":"descoberta de ferramentas e seleção de ferramentas","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"HI_WEB_ONLY","surface":"OPEN_WEB","payload":"उपकरण खोज और उपकरण चयन","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"TR_WEB_ONLY","surface":"OPEN_WEB","payload":"araç keşfi ve araç seçimi","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"ID_WEB_ONLY","surface":"OPEN_WEB","payload":"penemuan alat dan pemilihan alat","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"VI_WEB_ONLY","surface":"OPEN_WEB","payload":"khám phá công cụ và lựa chọn công cụ","trap":"NON_ENGLISH_WEB_ONLY"},
    {"id":"DESCRIPTIONLESS_CODE_IDENTIFIER","surface":"CODE_CONTENT","payload":"def valid_route_top1(routes): return routes[0]","trap":"NO_DESCRIPTION_ZERO_POPULARITY_CODE_ONLY"},
    {"id":"SYMBOL_ONLY_AUTHORITY","surface":"SYMBOLS","payload":"tool_authority_identity","trap":"SYMBOL_ONLY"},
    {"id":"TEST_ONLY_HARNESS","surface":"TESTS_EXAMPLES","payload":"assert same harness common tool authority","trap":"TEST_ONLY"},
    {"id":"MANIFEST_ONLY_TOOLATHLON","surface":"MANIFESTS","payload":"dependencies = [\"toolathlon\"]","trap":"MANIFEST_ONLY"},
    {"id":"COMMIT_ONLY_324","surface":"COMMITS_RELEASES_BRANCHES_TAGS","payload":"record Toolathlon 324 trials comparator evidence","trap":"COMMIT_MESSAGE_ONLY"},
    {"id":"CODE_ONLY_SCORE","surface":"CODE_CONTENT","payload":"EXPECTED = \"77.8 Pass@1\"","trap":"CODE_ONLY_NUMERIC_SIGNATURE"},
    {"id":"SCHOLARLY_TRAJECTORY_TERM","surface":"SCHOLARLY","payload":"Toolathlon reference trajectories for external validation","trap":"PAPER_TEXT_ONLY"},
    {"id":"PACKAGE_PROTOCOL_NAME","surface":"PACKAGE_REGISTRY","payload":"Toolathlon-Verified","trap":"PACKAGE_NAME_ONLY"},
    {"id":"DOC_TASK_TRIAL_SIGNATURE","surface":"DOCUMENTATION","payload":"evaluation uses 108 tasks 3 trials","trap":"DOC_NUMERIC_SIGNATURE"},
    {"id":"MISLEADING_REPO_NAME","surface":"CODE_CONTENT","payload":"project=banana_clock; protocol=Toolathlon-Verified; route_selection=True","trap":"MISLEADING_METADATA"},
    {"id":"EMPTY_README_API_ONLY","surface":"CODE_CONTENT","payload":"reference_trajectory = load_jsonl(path)","trap":"EMPTY_README_API_ONLY"}
]

UNSUPPORTED_BOUNDARIES = [
    {"id":"NONDEFAULT_BRANCH_ONLY","reason":"GLOBAL_GITHUB_CODE_SEARCH_DOES_NOT_PROVE_ALL_NONDEFAULT_REFS_SEARCHED"},
    {"id":"PRIVATE_REPOSITORY_ONLY","reason":"PRIVATE_OR_INACCESSIBLE_SOURCE_NOT_ENUMERABLE"},
    {"id":"DELETED_REF_ONLY","reason":"DELETED_HISTORY_NOT_GUARANTEED_OBSERVABLE"},
    {"id":"UNINDEXED_DISCUSSION_ONLY","reason":"UNINDEXED_OPEN_WEB_CONTENT_NOT_GUARANTEED_OBSERVABLE"},
    {"id":"BINARY_OR_LFS_ONLY","reason":"BINARY_LFS_CONTENT_NOT_GUARANTEED_SEARCHABLE_AS_TEXT"}
]


def _canon(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).casefold()


def _query_hits_payload(query: str, payload: str) -> bool:
    q = _canon(query).strip()
    p = _canon(payload)
    if not q:
        return False
    if q in p:
        return True
    # Search engines commonly tokenize multiword queries rather than requiring
    # an exact phrase. Require all substantial tokens to occur for this finite
    # synthetic approximation; single-token identifiers remain exact.
    tokens = [x for x in compiler.unicode_tokens(q) if len(x) >= 2]
    return bool(tokens) and all(_canon(x) in p for x in tokens)


def evaluate(retrieval_input: Mapping[str, Any]) -> dict[str, Any]:
    program = compiler.compile_residual(retrieval_input)
    rows = program["query_lattice"]
    found: list[dict[str, Any]] = []
    missed: list[dict[str, Any]] = []

    for fixture in SUPPORTED_FIXTURES:
        matches = [
            {
                "query_id": row["query_id"],
                "query": row["text"],
                "basis": row["basis"],
                "language_hint": row.get("language_hint"),
            }
            for row in rows
            if _query_hits_payload(row["text"], fixture["payload"])
        ]
        result = {
            "fixture_id": fixture["id"],
            "surface": fixture["surface"],
            "trap": fixture["trap"],
            "match_count": len(matches),
            "first_match": matches[0] if matches else None,
        }
        (found if matches else missed).append(result)

    total = len(SUPPORTED_FIXTURES)
    recall = len(found) / total if total else 1.0
    boundary_states = [
        {
            "fixture_id": row["id"],
            "state": "UNKNOWN_OUTSIDE_PROVED_FINITE_FIXTURE_SCOPE",
            "reason": row["reason"],
            "nonexistence_claim_authorized": False,
        }
        for row in UNSUPPORTED_BOUNDARIES
    ]
    passed = recall == 1.0 and not missed and all(
        x["nonexistence_claim_authorized"] is False for x in boundary_states
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FINITE_SUPPORTED_FIXTURE_RECALL_1_0__OPEN_WORLD_BOUNDARIES_UNKNOWN"
            if passed else
            "FAIL__FINITE_SUPPORTED_FIXTURE_FALSE_NEGATIVE_PRESENT"
        ),
        "pass": passed,
        "residual_id": program["residual_id"],
        "retrieval_program_sha256": program["retrieval_program_sha256"],
        "query_count": len(rows),
        "language_hints": sorted({str(x.get("language_hint")) for x in rows}),
        "explicit_language_variant_keys": sorted(str(x) for x in (retrieval_input.get("language_variants") or {}).keys()),
        "supported_fixture_count": total,
        "supported_fixture_found_count": len(found),
        "supported_fixture_missed_count": len(missed),
        "finite_supported_fixture_recall": recall,
        "found_fixtures": found,
        "missed_fixtures": missed,
        "unsupported_boundaries": boundary_states,
        "unsupported_boundary_count": len(boundary_states),
        "hard_nonclaims": [
            "FINITE_FIXTURE_RECALL_1_0_IS_NOT_OPEN_WORLD_RECALL_1_0",
            "UNSUPPORTED_BOUNDARIES_REMAIN_UNKNOWN",
            "NO_PRIVATE_DELETED_UNINDEXED_OR_BINARY_SOURCE_NONEXISTENCE_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_EXECUTION_OR_PROMOTION_CREDIT",
        ],
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    source = json.loads(
        (root / "canonical/governance/TOOL_DISCOVERY_MULTILINGUAL_RETRIEVAL_INPUT_V1.json").read_text(encoding="utf-8")
    )
    out = evaluate(source)
    print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
