"""Mine current Brain evidence for the 16 post-Recovery matched-scope child facts.

Discovery only. This scanner never upgrades a lexical or structural candidate into a
semantic binding or scope relation. It exists to make the current 16-fact zero-reality
cut cheap to review without allowing scheduler/restatement documents to self-prove it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"

SCHEMA = "PROJECT_BRAIN_POST_RECOVERY_MATCHED_CHILD_RECEIPT_MINER_V1"
SEARCH_ROOTS = (
    "canonical/verification",
    "canonical/capabilities",
    "canonical/governance",
)
TEXT_SUFFIXES = {".json", ".md", ".py", ".yml", ".yaml", ".txt"}
MAX_FILE_BYTES = 5_000_000
MAX_CANDIDATES_PER_FACT = 64

EXCLUDED_REL_PATHS = {
    "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V1.json",
    "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json",
    "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_V1.json",
    "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json",
    "canonical/governance/MATCHED_SCOPE_BINDING_SUBHYPERGRAPH_V1.json",
    "canonical/governance/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_ACTIVATION_V1.json",
    "canonical/verification/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json",
}
EXCLUDED_PREFIXES = (
    "POST_RECOVERY_MATCHED_CHILD_RECEIPT_",
    "MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_",
)


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _source_class(rel: str) -> str:
    if rel.startswith("canonical/verification/"):
        return "VERIFICATION_RECEIPT"
    if rel.startswith("canonical/capabilities/"):
        return "CAPABILITY_EVIDENCE"
    if rel.startswith("canonical/governance/"):
        return "GOVERNANCE_EVIDENCE_OR_BINDING"
    return "OTHER"


def _candidate_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for rel_root in SEARCH_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = p.relative_to(root).as_posix()
            if rel in EXCLUDED_REL_PATHS:
                continue
            if any(p.name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            out.append(p)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


def _child_facts(doc: Mapping[str, Any]) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    seen: set[str] = set()
    for edge in doc.get("implications", []):
        if not isinstance(edge, Mapping):
            raise ValueError("IMPLICATION_NOT_OBJECT")
        then = edge.get("then")
        if not isinstance(then, list) or len(then) != 1 or not isinstance(then[0], str):
            raise ValueError("IMPLICATION_TARGET_INVALID")
        target = then[0]
        reqs = edge.get("if_all")
        if not isinstance(reqs, list) or len(reqs) != 2:
            raise ValueError(f"CHILD_REQUIREMENT_COUNT_NOT_2:{target}")
        for proposition in reqs:
            if not isinstance(proposition, str) or not proposition:
                raise ValueError(f"CHILD_REQUIREMENT_INVALID:{target}")
            if proposition in seen:
                raise ValueError(f"DUPLICATE_CHILD_FACT:{proposition}")
            seen.add(proposition)
            if proposition.endswith("::WITNESS_TARGET_SEMANTIC_BINDING_INDEPENDENT_PASS"):
                kind = "SEMANTIC_BINDING"
            elif proposition.endswith("::WITNESS_TARGET_EXACT_OR_SUPERSET_SCOPE_RELATION_INDEPENDENT_PASS"):
                kind = "SCOPE_RELATION"
            else:
                raise ValueError(f"UNKNOWN_CHILD_FACT_KIND:{proposition}")
            facts.append({"target_predicate_id": target, "proposition": proposition, "kind": kind})
    if len(facts) != 16:
        raise ValueError(f"EXPECTED_16_CHILD_FACTS_GOT_{len(facts)}")
    return facts


def _manifest_sha256(rows: list[tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for rel, sha in rows:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(sha.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _status_hint(text: str) -> str | None:
    try:
        doc = json.loads(text)
    except Exception:
        return None
    if not isinstance(doc, Mapping):
        return None
    value = doc.get("status")
    return str(value) if isinstance(value, str) else None


def _line_numbers(text: str, needle: str, limit: int = 16) -> list[int]:
    return [
        i for i, line in enumerate(text.splitlines(), start=1) if needle in line
    ][:limit]


def _candidate_score(kind: str, source_class: str, text_lower: str) -> int:
    score = 0
    if source_class == "VERIFICATION_RECEIPT":
        score += 8
    elif source_class == "CAPABILITY_EVIDENCE":
        score += 5
    elif source_class == "GOVERNANCE_EVIDENCE_OR_BINDING":
        score += 3

    if "independent" in text_lower:
        score += 2
    if "public_runner" in text_lower or "public runner" in text_lower:
        score += 2

    if kind == "SEMANTIC_BINDING":
        for term in ("semantic", "binding", "atom", "metric", "witness"):
            if term in text_lower:
                score += 1
    else:
        for term in ("scope", "exact", "superset", "relation", "coverage"):
            if term in text_lower:
                score += 1
    return score


def build_index(*, root: Path = ROOT) -> dict[str, Any]:
    input_path = root / "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"
    doc = json.loads(input_path.read_text(encoding="utf-8"))
    facts = _child_facts(doc)

    files = _candidate_files(root)
    cache: list[tuple[str, str, str, str, str | None]] = []
    manifest: list[tuple[str, str]] = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        try:
            data = p.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        sha = _blob_sha(data)
        manifest.append((rel, sha))
        cache.append((rel, _source_class(rel), sha, text, _status_hint(text)))

    rows: list[dict[str, Any]] = []
    exact_total = 0
    candidate_total = 0

    for fact in facts:
        target = fact["target_predicate_id"]
        proposition = fact["proposition"]
        kind = fact["kind"]
        exact_matches: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []

        for rel, source_class, sha, text, status in cache:
            if proposition in text:
                exact_matches.append({
                    "path": rel,
                    "git_blob_sha": sha,
                    "source_class": source_class,
                    "status_hint": status,
                    "line_numbers": _line_numbers(text, proposition),
                    "candidate_only": True,
                })

            if target not in text:
                continue
            low = text.lower()
            score = _candidate_score(kind, source_class, low)
            if score <= 0:
                continue
            candidates.append({
                "path": rel,
                "git_blob_sha": sha,
                "source_class": source_class,
                "status_hint": status,
                "target_line_numbers": _line_numbers(text, target),
                "priority_score": score,
                "candidate_only": True,
            })

        exact_matches.sort(key=lambda x: (x["source_class"] != "VERIFICATION_RECEIPT", x["path"]))
        candidates.sort(key=lambda x: (-x["priority_score"], x["source_class"] != "VERIFICATION_RECEIPT", x["path"]))
        exact_total += len(exact_matches)
        candidate_total += len(candidates)
        rows.append({
            **fact,
            "proved": False,
            "exact_fact_occurrence_count": len(exact_matches),
            "exact_fact_occurrences": exact_matches[:MAX_CANDIDATES_PER_FACT],
            "candidate_receipt_count": len(candidates),
            "candidate_receipts": candidates[:MAX_CANDIDATES_PER_FACT],
            "candidate_list_truncated": len(candidates) > MAX_CANDIDATES_PER_FACT,
            "review_rule": "CANDIDATE_POINTER_ONLY__EXPLICIT_SCOPE_AND_SEMANTIC_REVIEW_REQUIRED",
        })

    no_candidates = sorted(r["proposition"] for r in rows if r["candidate_receipt_count"] == 0)
    exact_occurrence_facts = sorted(r["proposition"] for r in rows if r["exact_fact_occurrence_count"] > 0)

    return {
        "schema": SCHEMA,
        "status": "PASS__POST_RECOVERY_16_CHILD_FACT_CANDIDATE_RECEIPT_INDEX_COMPUTED__ZERO_CREDIT",
        "input": {
            "path": "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json",
            "git_blob_sha": _blob_sha(input_path.read_bytes()),
        },
        "child_fact_count": len(rows),
        "scanned_file_count": len(cache),
        "scanned_corpus_manifest_sha256": _manifest_sha256(manifest),
        "exact_fact_occurrence_count": exact_total,
        "facts_with_exact_occurrences": exact_occurrence_facts,
        "candidate_receipt_count": candidate_total,
        "facts_without_candidate_receipts": no_candidates,
        "facts": rows,
        "hard_rules": [
            "EXACT_OCCURRENCE_IS_CANDIDATE_ONLY_NOT_PROOF",
            "TARGET_ID_COOCCURRENCE_IS_CANDIDATE_ONLY_NOT_PROOF",
            "SCHEDULER_FRONTIER_RESIDUAL_AND_SELF_INDEX_RESTATEMENTS_EXCLUDED",
            "NO_SEMANTIC_BINDING_FROM_NAMES_OR_PROSE_ANALOGY",
            "NO_SCOPE_RELATION_FROM_NAMES_OR_PROSE_ANALOGY",
            "NO_SIBLING_OR_FAMILY_INHERITANCE",
            "CONTENT_ADDRESS_EVERY_CANDIDATE_AND_THE_SCANNED_CORPUS",
            "NO_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT",
        ],
        "next": "SEMANTICALLY_REVIEW_HIGHEST_PRIORITY_ORIGINAL_RECEIPTS_PER_CHILD__PROMOTE_ONLY_EXACT_INDEPENDENT_BINDING_OR_SCOPE_RELATION__RUN_FIXED_POINT_AFTER_EACH_VERIFIED_CHILD",
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = build_index()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
