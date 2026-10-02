"""Corpus-bound candidate receipt index for canonical proof atoms.

V4 binds the exact V2 proof-atom basis, every scanned evidence blob, the scan policy,
and the deterministic candidate-review queue. It is discovery/scheduling only and
never grants acceptance, capability, family, execution, or promotion credit.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.canonical_proof_atom_basis_v2 import compile_basis

SCHEMA = "PROJECT_BRAIN_PROOF_ATOM_RECEIPT_INDEX_V4"
ROOT = Path(__file__).resolve().parents[2]
SEARCH_ROOTS = (
    "canonical/verification",
    "canonical/capabilities",
    "canonical/governance",
)
TEXT_SUFFIXES = {".json", ".md", ".py", ".yml", ".yaml", ".txt"}
MAX_FILE_BYTES = 5_000_000
MAX_MATCHES_PER_ATOM = 64

EXCLUDED_BASENAMES = {
    "TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json",
    "OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json",
    "MATCHED_SCOPE_BINDING_SUBHYPERGRAPH_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_ACTIVATION_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_V2_ACTIVATION_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_V2_ACTIVE_AUTHORITY_V1.json",
    "PROOF_ATOM_REFINEMENT_OVERLAY_V1.json",
    "GLOBAL_CERTIFICATE_ABDUCTIVE_RESIDUAL_EXECUTION_V1.json",
    "GLOBAL_CERTIFICATE_ABDUCTIVE_RESIDUAL_ACTIVATION_V1.json",
    "MULTITARGET_CERTIFICATE_TARGET_REFINEMENT_ACTIVATION_V1.json",
    "CURRENT_TERMINAL_AUTHORITY_V1.json",
    "EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json",
    "PROOF_ATOM_RECEIPT_INDEX_V1.json",
    "PROOF_ATOM_RECEIPT_INDEX_V2.json",
    "PROOF_ATOM_RECEIPT_INDEX_V3.json",
}
EXCLUDED_REL_PATHS = {
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V1.json",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V3.json",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V4.json",
}
EXCLUDED_BASENAME_PREFIXES = (
    "TERMINAL_CERTIFICATE_FRONTIER_",
    "MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_",
    "GLOBAL_CERTIFICATE_ABDUCTIVE_RESIDUAL_",
    "MULTITARGET_CERTIFICATE_TARGET_REFINEMENT_",
    "PROOF_ATOM_REFINEMENT_OVERLAY_",
    "PROOF_ATOM_RECEIPT_INDEX_",
    "PROOF_ATOM_RECEIPT_SNAPSHOT_",
    "CANONICAL_PROOF_ATOM_BASIS_",
    "DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_",
)
SOURCE_RANK = {
    "VERIFICATION_RECEIPT": 0,
    "CAPABILITY_EVIDENCE": 1,
    "GOVERNANCE_EVIDENCE_OR_BINDING": 2,
    "OTHER": 3,
}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "canonical_atom_count": 0,
        "candidate_match_count": 0,
        "atoms": [],
        "review_queue": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _sha256_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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
            if rel in EXCLUDED_REL_PATHS or p.name in EXCLUDED_BASENAMES or p.name.startswith(EXCLUDED_BASENAME_PREFIXES):
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            out.append(p)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


_IDENTIFIER_NEIGHBOR = r"A-Za-z0-9_:.\\-"


def _line_hits(text: str, literal: str) -> list[int]:
    """Return exact literal-token line hits, rejecting identifier superstrings."""
    pattern = re.compile(
        rf"(?<![{_IDENTIFIER_NEIGHBOR}]){re.escape(literal)}(?![{_IDENTIFIER_NEIGHBOR}])"
    )
    return [
        i
        for i, line in enumerate(text.splitlines(), start=1)
        if pattern.search(line) is not None
    ]


def _scan_policy() -> dict[str, Any]:
    return {
        "search_roots": list(SEARCH_ROOTS),
        "text_suffixes": sorted(TEXT_SUFFIXES),
        "max_file_bytes": MAX_FILE_BYTES,
        "max_matches_per_atom": MAX_MATCHES_PER_ATOM,
        "excluded_basenames": sorted(EXCLUDED_BASENAMES),
        "excluded_rel_paths": sorted(EXCLUDED_REL_PATHS),
        "excluded_basename_prefixes": list(EXCLUDED_BASENAME_PREFIXES),
        "source_rank": dict(sorted(SOURCE_RANK.items())),
        "identifier_neighbor_regex_class": _IDENTIFIER_NEIGHBOR,
    }


def build_index(
    global_frontier: Mapping[str, Any],
    refinement_overlay: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    basis = compile_basis(global_frontier, refinement_overlay)
    if not str(basis.get("status", "")).startswith("PASS"):
        return _fail("CANONICAL_PROOF_ATOM_BASIS_NOT_PASS")

    atoms = basis.get("atoms")
    if not isinstance(atoms, list) or not atoms:
        return _fail("CANONICAL_ATOMS_MISSING")

    basis_manifest = [
        {
            "atom_id": atom.get("atom_id"),
            "proposition": atom.get("proposition"),
            "associated_target_predicates": atom.get("associated_target_predicates", []),
            "certificate_ids": atom.get("certificate_ids", []),
            "layers": atom.get("layers", []),
        }
        for atom in atoms
    ]
    if any(not isinstance(x["atom_id"], str) or not isinstance(x["proposition"], str) for x in basis_manifest):
        return _fail("CANONICAL_ATOM_INVALID")
    basis_manifest = sorted(basis_manifest, key=lambda x: x["atom_id"])
    basis_manifest_sha256 = _sha256_json(basis_manifest)

    files = _candidate_files(root)
    file_cache: list[dict[str, Any]] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        file_cache.append(
            {
                "path": rel,
                "source_class": _source_class(rel),
                "git_blob_sha": _blob_sha(data),
                "size_bytes": len(data),
                "text": text,
            }
        )

    corpus_manifest = [
        {
            "path": x["path"],
            "git_blob_sha": x["git_blob_sha"],
            "size_bytes": x["size_bytes"],
            "source_class": x["source_class"],
        }
        for x in file_cache
    ]
    scanned_corpus_manifest_sha256 = _sha256_json(corpus_manifest)
    scan_policy_sha256 = _sha256_json(_scan_policy())

    atom_rows: list[dict[str, Any]] = []
    total_matches = 0
    source_class_counts: dict[str, int] = {}
    atoms_with_matches = 0

    for atom in atoms:
        proposition = atom.get("proposition")
        atom_id = atom.get("atom_id")
        if not isinstance(proposition, str) or not proposition or not isinstance(atom_id, str):
            return _fail("CANONICAL_ATOM_INVALID")

        matches: list[dict[str, Any]] = []
        actual_match_count = 0
        for file_row in file_cache:
            text = file_row["text"]
            if proposition not in text:
                continue
            hits = _line_hits(text, proposition)
            if not hits:
                continue
            source_class = file_row["source_class"]
            actual_match_count += 1
            source_class_counts[source_class] = source_class_counts.get(source_class, 0) + 1
            if len(matches) < MAX_MATCHES_PER_ATOM:
                matches.append(
                    {
                        "path": file_row["path"],
                        "git_blob_sha": file_row["git_blob_sha"],
                        "source_class": source_class,
                        "line_numbers": hits[:16],
                        "explicit_atom_id_reference": atom_id in text,
                        "candidate_only": True,
                    }
                )

        matches.sort(
            key=lambda m: (
                SOURCE_RANK.get(m["source_class"], 99),
                0 if m["explicit_atom_id_reference"] else 1,
                m["path"],
                m["git_blob_sha"],
            )
        )
        if actual_match_count:
            atoms_with_matches += 1
        total_matches += actual_match_count
        atom_rows.append(
            {
                "atom_id": atom_id,
                "proposition": proposition,
                "associated_target_predicates": atom.get("associated_target_predicates", []),
                "associated_target_count": len(atom.get("associated_target_predicates", [])),
                "candidate_match_count": actual_match_count,
                "stored_candidate_match_count": len(matches),
                "candidate_match_truncated": actual_match_count > len(matches),
                "candidate_matches": matches,
                "candidate_only": True,
            }
        )

    zero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] == 0)
    nonzero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] > 0)

    queue_rows: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for row in atom_rows:
        if not row["candidate_matches"]:
            continue
        best = row["candidate_matches"][0]
        key = (
            SOURCE_RANK.get(best["source_class"], 99),
            0 if best["explicit_atom_id_reference"] else 1,
            -row["associated_target_count"],
            row["candidate_match_count"],
            row["atom_id"],
        )
        queue_rows.append(
            (
                key,
                {
                    "atom_id": row["atom_id"],
                    "proposition": row["proposition"],
                    "associated_target_predicates": row["associated_target_predicates"],
                    "associated_target_count": row["associated_target_count"],
                    "candidate_match_count": row["candidate_match_count"],
                    "best_candidate": best,
                    "scheduling_only": True,
                },
            )
        )
    review_queue = [row for _, row in sorted(queue_rows, key=lambda x: x[0])]

    result_fingerprint = {
        "basis_manifest_sha256": basis_manifest_sha256,
        "scanned_corpus_manifest_sha256": scanned_corpus_manifest_sha256,
        "scan_policy_sha256": scan_policy_sha256,
        "candidate_bindings": [
            {
                "atom_id": row["atom_id"],
                "candidate_match_count": row["candidate_match_count"],
                "matches": [
                    [m["path"], m["git_blob_sha"], m["explicit_atom_id_reference"]]
                    for m in row["candidate_matches"]
                ],
            }
            for row in atom_rows
        ],
    }

    return {
        "schema": SCHEMA,
        "status": "PASS__CORPUS_BOUND_CONTENT_ADDRESSED_CANDIDATE_INDEX__DETERMINISTIC_REVIEW_QUEUE__ZERO_CREDIT",
        "errors": [],
        "canonical_atom_count": len(atom_rows),
        "basis_manifest_sha256": basis_manifest_sha256,
        "scan_policy_sha256": scan_policy_sha256,
        "scanned_file_count": len(file_cache),
        "scanned_corpus_manifest_sha256": scanned_corpus_manifest_sha256,
        "candidate_match_count": total_matches,
        "atoms_with_truncated_candidate_lists": sum(
            1 for row in atom_rows if row["candidate_match_truncated"]
        ),
        "atoms_with_candidate_matches": atoms_with_matches,
        "atoms_without_candidate_matches": len(zero),
        "atom_ids_with_candidate_matches": nonzero,
        "atom_ids_without_candidate_matches": zero,
        "candidate_matches_by_source_class": dict(sorted(source_class_counts.items())),
        "review_queue_length": len(review_queue),
        "review_queue": review_queue,
        "atoms": atom_rows,
        "index_fingerprint_sha256": _sha256_json(result_fingerprint),
        "rules": [
            "EXACT_PROPOSITION_LITERAL_TOKEN_OCCURRENCE_IS_CANDIDATE_POINTER_ONLY",
            "IDENTIFIER_SUPERSTRING_FALSE_POSITIVES_ARE_REJECTED",
            "MATCH_CAP_NEVER_HIDES_ACTUAL_CANDIDATE_COUNT",
            "EVERY_CANDIDATE_MATCH_IS_BOUND_TO_GIT_BLOB_SHA",
            "ZERO_MATCH_STATE_IS_BOUND_TO_DIGEST_OF_EVERY_SCANNED_ELIGIBLE_EVIDENCE_BLOB",
            "ATOM_BASIS_IS_BOUND_TO_DETERMINISTIC_V2_ATOM_MANIFEST_DIGEST",
            "SCAN_POLICY_IS_CONTENT_DIGESTED",
            "REVIEW_QUEUE_IS_DETERMINISTIC_SCHEDULING_ONLY",
            "VERIFICATION_RECEIPTS_RANK_BEFORE_CAPABILITY_EVIDENCE_BEFORE_GOVERNANCE_BINDINGS",
            "EXPLICIT_PA1_REFERENCE_ONLY_STRENGTHENS_REVIEW_PRIORITY_AND_NEVER_GRANTS_PROOF",
            "NO_SEMANTIC_SCOPE_METRIC_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT_FROM_INDEX",
        ],
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    global_frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(encoding="utf-8")
    )
    refinement_overlay = json.loads(
        (ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(encoding="utf-8")
    )
    out = build_index(global_frontier, refinement_overlay)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
