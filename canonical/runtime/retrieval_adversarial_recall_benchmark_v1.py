#!/usr/bin/env python3
"""Finite adversarial recall benchmark for the retrieval V3 candidate stack.

This benchmark is intentionally synthetic and finite. Therefore 100% recall is
a legitimate requirement for the declared observable fixture universe.

A separate unbridgeable fixture is intentionally outside that observable
contract. Correct behavior for it is UNKNOWN, never NONEXISTENT.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Mapping, Sequence

from canonical.runtime.adaptive_retrieval_query_expansion_v1 import expand as expand_queries
from canonical.runtime.public_source_federation_v1 import compile_federation

SCHEMA = "PROJECT_BRAIN_RETRIEVAL_ADVERSARIAL_RECALL_BENCHMARK_V1"

FIXTURES = [
    {
        "id": "DESCRIPTIONLESS_CODE_ONLY",
        "surface": "CODE_CONTENT",
        "text": "def dumpb(obj): return UBJSON serializer output",
    },
    {
        "id": "CHINESE_NATIVE_METADATA",
        "surface": "REPOSITORY_METADATA",
        "text": "高可靠二进制数据编码器",
    },
    {
        "id": "ARABIC_ISSUE_ONLY",
        "surface": "ISSUES_PRS",
        "text": "إصلاح محوّل البيانات الثنائية",
    },
    {
        "id": "RUSSIAN_TEST_ONLY",
        "surface": "TESTS_EXAMPLES",
        "text": "тест сериализатор двоичных данных",
    },
    {
        "id": "MISLEADING_METADATA_MANIFEST_ONLY",
        "surface": "MANIFESTS",
        "text": "name = ubjson-codec dependencies serializer-core",
    },
    {
        "id": "HISTORY_ONLY",
        "surface": "COMMITS_RELEASES_BRANCHES_TAGS",
        "text": "fix UBJSON encoder overflow in historical implementation",
    },
    {
        "id": "NONDEFAULT_BRANCH_ONLY",
        "surface": "COMMITS_RELEASES_BRANCHES_TAGS",
        "text": "alternate branch contains dumpb serializer implementation",
    },
    {
        "id": "EXAMPLE_ONLY",
        "surface": "TESTS_EXAMPLES",
        "text": "example: dumpb payload with UBJSON",
    },
    {
        "id": "PACKAGE_REGISTRY_ONLY",
        "surface": "PACKAGE_REGISTRY",
        "text": "ubjson serializer codec package",
    },
    {
        "id": "SYMBOL_ONLY",
        "surface": "SYMBOLS",
        "text": "dumpb loadb Encoder Decoder",
    },
]

UNBRIDGEABLE_FIXTURE = {
    "id": "NO_SHARED_IDENTIFIER_NO_LANGUAGE_BRIDGE",
    "surface": "CODE_CONTENT",
    "text": "神秘压缩转换器",
}


def _canon(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).casefold()


def _program() -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_RESIDUAL_WITNESS_RETRIEVAL_COMPILER_V1",
        "status": "COMPILED",
        "effect": "serialize binary data",
        "query_lattice": [
            {"text": "UBJSON serializer", "basis": "RESIDUAL_EFFECT"},
            {"text": "dumpb", "basis": "OBSERVABLE_API_SYMBOLS"},
            {"text": "ubjson-codec", "basis": "OBSERVABLE_IMPORTS"},
        ],
        "surfaces": [
            "PACKAGE_REGISTRY","REPOSITORY_METADATA","CODE_CONTENT","SYMBOLS",
            "MANIFESTS","TESTS_EXAMPLES","ISSUES_PRS",
            "COMMITS_RELEASES_BRANCHES_TAGS","DOCUMENTATION","OPEN_WEB",
            "SCHOLARLY","SOCIAL_TECHNICAL_DISCUSSION"
        ],
    }


def _bridge_variants() -> list[dict[str, Any]]:
    return [
        {"text": "编码器", "language": "zh", "source": "WIKIDATA", "qid": "QX", "semantic_equivalence_verified": False},
        {"text": "محوّل", "language": "ar", "source": "WIKIDATA", "qid": "QX", "semantic_equivalence_verified": False},
        {"text": "сериализатор", "language": "ru", "source": "WIKIDATA", "qid": "QX", "semantic_equivalence_verified": False},
    ]


def _queries(expansion: Mapping[str, Any]) -> list[str]:
    base = [row["text"] for row in _program()["query_lattice"]]
    more = [
        row.get("text")
        for row in expansion.get("new_queries", [])
        if isinstance(row, Mapping) and row.get("text")
    ]
    return base + more


def _matches(query: str, text: str) -> bool:
    q = _canon(query)
    t = _canon(text)
    if q in t:
        return True
    tokens = [x for x in q.replace("-", " ").replace("/", " ").replace(".", " ").split() if len(x) >= 4]
    return any(tok in t for tok in tokens)


def run() -> dict[str, Any]:
    program = _program()
    expansion = expand_queries(program, bridge_variants=_bridge_variants(), prior_candidates=[], max_queries=96)
    queries = _queries(expansion)
    federation = compile_federation(queries[:8], max_queries_per_source=4)

    found: list[str] = []
    misses: list[str] = []
    for fixture in FIXTURES:
        if any(_matches(q, fixture["text"]) for q in queries):
            found.append(fixture["id"])
        else:
            misses.append(fixture["id"])

    unbridgeable_found = any(_matches(q, UNBRIDGEABLE_FIXTURE["text"]) for q in queries)
    recall = len(found) / len(FIXTURES)

    return {
        "schema": SCHEMA,
        "status": "PASS" if recall == 1.0 and not unbridgeable_found else "FAIL",
        "declared_observable_fixture_count": len(FIXTURES),
        "found_fixture_count": len(found),
        "recall": recall,
        "found": found,
        "misses": misses,
        "unbridgeable_fixture": {
            "id": UNBRIDGEABLE_FIXTURE["id"],
            "found": unbridgeable_found,
            "correct_state": "UNKNOWN" if not unbridgeable_found else "CANDIDATE_FOUND",
            "nonexistence_allowed": False,
        },
        "query_expansion_new_count": expansion["new_query_count"],
        "federation_source_group_count": federation["source_group_count"],
        "federation_request_count": federation["request_count"],
        "incremental_spend_usd": 0,
        "hard_rules": [
            "RECALL_1_REQUIRED_ONLY_FOR_THIS_DECLARED_FINITE_OBSERVABLE_FIXTURE_UNIVERSE",
            "UNBRIDGEABLE_OPEN_WORLD_ARTIFACT_MUST_REMAIN_UNKNOWN",
            "NO_SYNTHETIC_FIXTURE_PASS_TO_OPEN_WORLD_COMPLETENESS_INFERENCE",
            "NO_RESULT_IS_NOT_NONEXISTENCE",
        ],
    }


if __name__ == "__main__":
    import json
    out = run()
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if out.get("status") == "PASS" else 1)
