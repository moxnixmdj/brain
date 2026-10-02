"""Content-addressed candidate receipt index for canonical proof atoms.

This is discovery only. Exact proposition occurrence identifies a file worth explicit
semantic review; it is never acceptance evidence by itself.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.canonical_proof_atom_basis_v2 import compile_basis

SCHEMA = "PROJECT_BRAIN_PROOF_ATOM_RECEIPT_INDEX_V2"
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
}
EXCLUDED_REL_PATHS = {
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V1.json",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json",
}
EXCLUDED_BASENAME_PREFIXES = (
    "PROOF_ATOM_RECEIPT_INDEX_",
    "PROOF_ATOM_RECEIPT_SNAPSHOT_",
    "DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_",
)


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "canonical_atom_count": 0,
        "candidate_match_count": 0,
        "atoms": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


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
            if rel in EXCLUDED_REL_PATHS or p.name in EXCLUDED_BASENAMES:
                continue
            if any(p.name.startswith(prefix) for prefix in EXCLUDED_BASENAME_PREFIXES):
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
    """Return literal-token line hits, rejecting superstring identifier matches."""
    pattern = re.compile(
        rf"(?<![{_IDENTIFIER_NEIGHBOR}]){re.escape(literal)}(?![{_IDENTIFIER_NEIGHBOR}])"
    )
    return [
        i
        for i, line in enumerate(text.splitlines(), start=1)
        if pattern.search(line) is not None
    ]


def _manifest_sha256(rows: list[tuple[str, str, str, str]]) -> str:
    h = hashlib.sha256()
    for rel, source_class, blob_sha, _text in rows:
        h.update(rel.encode("utf-8"))
        h.update(b"\\0")
        h.update(source_class.encode("utf-8"))
        h.update(b"\\0")
        h.update(blob_sha.encode("ascii"))
        h.update(b"\\n")
    return h.hexdigest()


def _atom_manifest_sha256(atoms: list[Mapping[str, Any]]) -> str:
    normalized = [
        {
            "atom_id": x.get("atom_id"),
            "proposition": x.get("proposition"),
            "associated_target_predicates": x.get("associated_target_predicates", []),
        }
        for x in atoms
    ]
    payload = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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

    files = _candidate_files(root)
    file_cache: list[tuple[str, str, str, str]] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        file_cache.append((rel, _source_class(rel), _blob_sha(data), text))

    atom_rows = []
    total_matches = 0
    source_class_counts: dict[str, int] = {}
    atoms_with_matches = 0

    for atom in atoms:
        proposition = atom.get("proposition")
        atom_id = atom.get("atom_id")
        if not isinstance(proposition, str) or not proposition or not isinstance(atom_id, str):
            return _fail("CANONICAL_ATOM_INVALID")

        matches = []
        actual_match_count = 0
        for rel, source_class, blob_sha, text in file_cache:
            if proposition not in text:
                continue
            hits = _line_hits(text, proposition)
            if not hits:
                continue
            actual_match_count += 1
            source_class_counts[source_class] = source_class_counts.get(source_class, 0) + 1
            if len(matches) < MAX_MATCHES_PER_ATOM:
                matches.append({
                    "path": rel,
                    "git_blob_sha": blob_sha,
                    "source_class": source_class,
                    "line_numbers": hits[:16],
                    "candidate_only": True,
                })

        if actual_match_count:
            atoms_with_matches += 1
        total_matches += actual_match_count
        atom_rows.append({
            "atom_id": atom_id,
            "proposition": proposition,
            "associated_target_predicates": atom.get("associated_target_predicates", []),
            "candidate_match_count": actual_match_count,
            "stored_candidate_match_count": len(matches),
            "candidate_match_truncated": actual_match_count > len(matches),
            "candidate_matches": matches,
            "candidate_only": True,
        })

    zero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] == 0)
    nonzero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] > 0)

    return {
        "schema": SCHEMA,
        "status": "PASS__CONTENT_ADDRESSED_CANDIDATE_RECEIPT_INDEX_COMPUTED__ZERO_CREDIT",
        "errors": [],
        "canonical_atom_count": len(atom_rows),
        "canonical_atom_manifest_sha256": _atom_manifest_sha256(atoms),
        "scanned_file_count": len(file_cache),
        "scanned_corpus_manifest_sha256": _manifest_sha256(file_cache),
        "candidate_match_count": total_matches,
        "atoms_with_truncated_candidate_lists": sum(
            1 for row in atom_rows if row["candidate_match_truncated"]
        ),
        "atoms_with_candidate_matches": atoms_with_matches,
        "atoms_without_candidate_matches": len(zero),
        "atom_ids_with_candidate_matches": nonzero,
        "atom_ids_without_candidate_matches": zero,
        "candidate_matches_by_source_class": dict(sorted(source_class_counts.items())),
        "atoms": atom_rows,
        "rule": (
            "EXACT_LITERAL_TOKEN_OCCURRENCE_IS_CANDIDATE_POINTER_ONLY__"
            "REJECT_IDENTIFIER_SUPERSTRING_FALSE_POSITIVES__"
            "CONTENT_ADDRESS_EACH_MATCH__CONTENT_ADDRESS_FULL_SCANNED_CORPUS_MANIFEST__"
            "REPORT_MATCH_TRUNCATION_EXPLICITLY__"
            "EXCLUDE_FRONTIER_AND_SCHEDULER_RESTATEMENTS__"
            "EXCLUDE_RECEIPT_PIPELINE_SELF_VERIFICATION_AND_DECLARED_CORPUS_RESTATEMENTS__"
            "NO_SEMANTIC_SCOPE_METRIC_ACCEPTANCE_OR_FAMILY_CREDIT_FROM_INDEX"
        ),
        "new_reality_units_consumed": 0,
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
