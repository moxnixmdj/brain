"""Mine existing Brain evidence for exact reusable proof atoms.

This is a zero-credit discovery tool. It never creates semantic implication edges.
It answers two narrower questions:
1) Do any of the nine independently normalized witness source files literally contain
   the frozen target source literals?
2) Do other existing repository evidence files contain those literals, suggesting a
   receipt worth explicit scope review before any new reality is acquired?

Exact lexical occurrence is a candidate pointer only. Semantic implication, metric
compatibility, scope relation, contamination cleanliness, acceptance credit, and
family credit remain separate fail-closed obligations.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
WITNESSES = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"

TEXT_SUFFIXES = {".json", ".md", ".py", ".yml", ".yaml", ".txt"}
MAX_FILE_BYTES = 5_000_000
MAX_MATCHES_PER_LITERAL = 20
SEARCH_ROOTS = ("canonical/verification", "canonical/capabilities", "canonical/governance")
SELF_OUTPUT_PREFIXES = ("EXISTING_RECEIPT_SEMANTIC_CANDIDATE_MINING_",)
_IDENTIFIER_NEIGHBOR = r"A-Za-z0-9_:.\-"

PIPELINE_BASENAMES = {
    "OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json",
    "OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json",
    "OPUS55_MATCHED_TARGET_NORMALIZATION_ACTIVATION_V1.json",
    "OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json",
    "OPUS55_PROTOCOL_IMPLICATION_GATE_REFINEMENT_V1.json",
    "OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json",
    "CURRENT_TERMINAL_AUTHORITY_V1.json",
    "OPUS55_ZERO_REALITY_PROOF_COMPRESSION_CUT_V1.json",
    "OPUS55_ZERO_REALITY_PROOF_COMPRESSION_CUT_V2.json",
}

DEFINITION_BASENAMES = {
    "OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
    "OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
}

CONTAMINATION_TERMS = (
    "contamination",
    "preexposure",
    "pre-exposure",
    "result blind",
    "result-blind",
    "heldout",
    "held-out",
    "cleanroom",
    "clean-room",
)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def classify(path: Path) -> str:
    p = rel(path)
    if path.name in DEFINITION_BASENAMES:
        return "TARGET_DEFINITION"
    if path.name in PIPELINE_BASENAMES:
        return "DERIVED_PROOF_PIPELINE"
    if p.startswith("canonical/verification/"):
        return "VERIFICATION_RECEIPT"
    if p.startswith("canonical/capabilities/"):
        return "CAPABILITY_EVIDENCE"
    if p.startswith("canonical/runtime/"):
        return "RUNTIME_PROOF_OR_IMPLEMENTATION"
    if p.startswith("canonical/governance/"):
        return "GOVERNANCE_EVIDENCE_OR_BINDING"
    if p.startswith("canonical/tests/"):
        return "TEST"
    if p.startswith(".github/workflows/"):
        return "WORKFLOW"
    return "OTHER"


def line_hits(text: str, literal: str) -> list[int]:
    pattern = re.compile(
        rf"(?<![{_IDENTIFIER_NEIGHBOR}]){re.escape(literal)}(?![{_IDENTIFIER_NEIGHBOR}])"
    )
    return [
        i for i, line in enumerate(text.splitlines(), start=1)
        if pattern.search(line) is not None
    ]


def excluded_from_global_reuse(path: Path) -> bool:
    return (
        path.name in PIPELINE_BASENAMES
        or path.name in DEFINITION_BASENAMES
        or any(path.name.startswith(prefix) for prefix in SELF_OUTPUT_PREFIXES)
    )


def all_searchable_files() -> list[Path]:
    out: list[Path] = []
    for rel_root in SEARCH_ROOTS:
        base = ROOT / rel_root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if (
                p.is_file()
                and p.suffix.lower() in TEXT_SUFFIXES
                and not excluded_from_global_reuse(p)
            ):
                out.append(p)
    return sorted(out, key=lambda x: rel(x))


def witness_source_paths(witness: dict[str, Any]) -> list[Path]:
    raw: list[str] = []
    source = witness.get("source_path")
    if isinstance(source, str) and source:
        raw.append(source)
    for row in witness.get("supporting_sources", []):
        if isinstance(row, dict):
            p = row.get("path")
            if isinstance(p, str) and p:
                raw.append(p)
    seen: set[str] = set()
    out: list[Path] = []
    root_resolved = ROOT.resolve()
    for p in raw:
        if p in seen:
            continue
        seen.add(p)
        try:
            candidate = (ROOT / p).resolve()
            candidate.relative_to(root_resolved)
        except (OSError, ValueError):
            continue
        out.append(candidate)
    return out


def source_literals(target_row: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for atom_row in target_row.get("atom_sources", []):
        atom = atom_row.get("atom")
        for source in atom_row.get("sources", []):
            literal = source.get("literal") if isinstance(source, dict) else None
            if isinstance(atom, str) and isinstance(literal, str) and literal:
                out.append({"kind": "atom", "key": atom, "literal": literal})
    for metric_row in target_row.get("metric_requirement_sources", []):
        metric = metric_row.get("metric")
        for source in metric_row.get("sources", []):
            literal = source.get("literal") if isinstance(source, dict) else None
            if isinstance(metric, str) and isinstance(literal, str) and literal:
                out.append({"kind": "metric", "key": metric, "literal": literal})
    return out


def main() -> int:
    target_doc = json.loads(TARGET.read_text(encoding="utf-8"))
    witness_doc = json.loads(WITNESSES.read_text(encoding="utf-8"))

    files = all_searchable_files()
    cache: dict[Path, str | None] = {}

    def text_of(path: Path) -> str | None:
        if path not in cache:
            cache[path] = read_text(path)
        return cache[path]

    catalog_matches: list[dict[str, Any]] = []
    global_matches: list[dict[str, Any]] = []
    contamination_pointers: list[dict[str, Any]] = []
    truncated_literal_search_count = 0
    global_actual_reuse_candidate_count = 0

    witnesses = [w for w in witness_doc.get("witnesses", []) if isinstance(w, dict)]
    targets = [t for t in target_doc.get("targets", []) if isinstance(t, dict)]

    # Candidate lexical edges inside the exact nine normalized witness sources.
    for witness in witnesses:
        wid = witness.get("witness_id")
        for path in witness_source_paths(witness):
            txt = text_of(path)
            if txt is None:
                continue

            low = txt.lower()
            terms = sorted({term for term in CONTAMINATION_TERMS if term in low})
            if terms:
                contamination_pointers.append({
                    "witness_id": wid,
                    "path": rel(path),
                    "git_blob_sha": git_blob_sha(path),
                    "terms_found": terms,
                    "rule": "POINTER_ONLY__DOES_NOT_ESTABLISH_CONTAMINATION_CLEAN",
                })

            for target in targets:
                pid = target.get("predicate_id")
                for item in source_literals(target):
                    hits = line_hits(txt, item["literal"])
                    if hits:
                        catalog_matches.append({
                            "witness_id": wid,
                            "target_predicate_id": pid,
                            "target_item_kind": item["kind"],
                            "target_item_key": item["key"],
                            "exact_source_literal": item["literal"],
                            "path": rel(path),
                            "git_blob_sha": git_blob_sha(path),
                            "line_numbers": hits[:MAX_MATCHES_PER_LITERAL],
                            "line_hit_count": len(hits),
                            "source_class": classify(path),
                            "candidate_only": True,
                        })

    # Global reuse mining. Exclude the normalization/gate pipeline itself so the
    # search cannot "prove" a target by finding a document that merely restates it.
    for target in targets:
        pid = target.get("predicate_id")
        for item in source_literals(target):
            actual_per_literal = 0
            stored_per_literal = 0
            for path in files:
                txt = text_of(path)
                if txt is None or item["literal"] not in txt:
                    continue
                cls = classify(path)
                hits = line_hits(txt, item["literal"])
                if not hits:
                    continue
                actual_per_literal += 1
                global_actual_reuse_candidate_count += 1
                if stored_per_literal < MAX_MATCHES_PER_LITERAL:
                    global_matches.append({
                        "target_predicate_id": pid,
                        "target_item_kind": item["kind"],
                        "target_item_key": item["key"],
                        "exact_source_literal": item["literal"],
                        "path": rel(path),
                        "git_blob_sha": git_blob_sha(path),
                        "line_numbers": hits[:MAX_MATCHES_PER_LITERAL],
                        "line_hit_count": len(hits),
                        "source_class": cls,
                        "candidate_only": True,
                    })
                    stored_per_literal += 1
            if actual_per_literal > stored_per_literal:
                truncated_literal_search_count += 1

    targets_with_catalog = sorted({x["target_predicate_id"] for x in catalog_matches})
    targets_with_global = sorted({x["target_predicate_id"] for x in global_matches})

    corpus_manifest = [
        {
            "path": rel(path),
            "git_blob_sha": git_blob_sha(path),
            "source_class": classify(path),
            "size_bytes": path.stat().st_size,
        }
        for path in files
    ]

    out = {
        "schema": "PROJECT_BRAIN_EXISTING_RECEIPT_SEMANTIC_CANDIDATE_MINER_V2",
        "status": "PASS__DISCOVERY_ONLY__CONTENT_ADDRESSED_SELF_REFLECTION_SAFE__ZERO_CREDIT",
        "search_roots": list(SEARCH_ROOTS),
        "scanned_file_count": len(corpus_manifest),
        "scanned_corpus_manifest_sha256": canonical_sha256(corpus_manifest),
        "scanned_files": corpus_manifest,
        "target_input_git_blob_sha": git_blob_sha(TARGET),
        "witness_input_git_blob_sha": git_blob_sha(WITNESSES),
        "target_count": len(targets),
        "witness_count": len(witnesses),
        "exact_catalog_edge_candidate_count": len(catalog_matches),
        "targets_with_catalog_edge_candidates": targets_with_catalog,
        "global_actual_reuse_candidate_count": global_actual_reuse_candidate_count,
        "global_stored_reuse_candidate_count": len(global_matches),
        "truncated_literal_search_count": truncated_literal_search_count,
        "targets_with_global_exact_reuse_candidates": targets_with_global,
        "contamination_pointer_count": len(contamination_pointers),
        "catalog_edge_candidates": catalog_matches,
        "global_reuse_candidates": global_matches,
        "contamination_pointers": contamination_pointers,
        "hard_rules": [
            "LEXICAL_TOKEN_OCCURRENCE_IS_NOT_SEMANTIC_IMPLICATION",
            "GLOBAL_REUSE_SEARCHES_ONLY_DECLARED_EVIDENCE_ROOTS",
            "RUNTIME_TEST_WORKFLOW_AND_PRIOR_DISCOVERY_OUTPUTS_CANNOT_BECOME_GLOBAL_REUSE_EVIDENCE",
            "EVERY_STORED_CANDIDATE_IS_GIT_BLOB_CONTENT_ADDRESSED",
            "COMPLETE_SEARCHABLE_CORPUS_MANIFEST_IS_SHA256_ADDRESSED",
            "MATCH_TRUNCATION_IS_EXPLICIT",
            "NO_TARGET_ATOM_CREDIT_FROM_STRING_MATCH",
            "NO_SCOPE_RELATION_FROM_NAME_OR_PROSE_ANALOGY",
            "NO_CONTAMINATION_CLEAN_FLAG_FROM_KEYWORD_OCCURRENCE",
            "NO_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT",
            "USE_RESULTS_ONLY_TO_PRIORITIZE_EXPLICIT_CONTENT_ADDRESSED_SCOPE_REVIEW",
        ],
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
