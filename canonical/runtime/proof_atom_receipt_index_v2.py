"""V2 content-addressed candidate receipt index for the active proof-atom basis.

Discovery only. Candidate occurrence never grants acceptance, capability, family,
execution, or promotion credit. The full scanned corpus and basis are fingerprinted so
one repository scan can be frozen and independently replayed exactly.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
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
_SYMBOL_CHAR_CLASS = r"A-Za-z0-9_:.-"

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
}
EXCLUDED_REL_PATHS = {
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V1.json",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json",
}


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
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            out.append(p)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


def _occurrence_hits(text: str, literal: str) -> tuple[list[int], list[int]]:
    pattern = re.compile(
        rf"(?<![{_SYMBOL_CHAR_CLASS}]){re.escape(literal)}(?![{_SYMBOL_CHAR_CLASS}])"
    )
    exact: list[int] = []
    embedded: list[int] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if literal not in line:
            continue
        if pattern.search(line):
            exact.append(i)
        else:
            embedded.append(i)
    return exact, embedded


def _manifest_sha256(entries: list[tuple[str, str, str, str]]) -> str:
    h = hashlib.sha256()
    for rel, source_class, blob_sha, _text in entries:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(source_class.encode("utf-8"))
        h.update(b"\0")
        h.update(blob_sha.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _basis_manifest_sha256(atoms: list[Mapping[str, Any]]) -> str:
    h = hashlib.sha256()
    for atom in sorted(atoms, key=lambda x: str(x.get("atom_id", ""))):
        atom_id = atom.get("atom_id")
        proposition = atom.get("proposition")
        if not isinstance(atom_id, str) or not isinstance(proposition, str):
            continue
        h.update(atom_id.encode("utf-8"))
        h.update(b"\0")
        h.update(proposition.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _index_input_fingerprint(basis_digest: str, corpus_digest: str) -> str:
    payload = {
        "schema": SCHEMA,
        "basis_atom_manifest_sha256": basis_digest,
        "scanned_corpus_manifest_sha256": corpus_digest,
        "searched_roots": list(SEARCH_ROOTS),
        "excluded_basenames": sorted(EXCLUDED_BASENAMES),
        "max_file_bytes": MAX_FILE_BYTES,
        "max_matches_per_atom": MAX_MATCHES_PER_ATOM,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _priority_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, str]:
    matches = row.get("candidate_matches", [])
    exact = any(m.get("match_kind") == "EXACT_SYMBOL_LITERAL" for m in matches)
    classes = {m.get("source_class") for m in matches}
    return (
        0 if exact else 1,
        0 if "VERIFICATION_RECEIPT" in classes else 1,
        0 if "CAPABILITY_EVIDENCE" in classes else 1,
        int(row.get("candidate_match_count", 0)),
        str(row.get("atom_id", "")),
    )


def build_index(
    global_frontier: Mapping[str, Any],
    refinement_overlay: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    basis = compile_basis(global_frontier, refinement_overlay)
    if not str(basis.get("status", "")).startswith("PASS"):
        return _fail("CANONICAL_PROOF_ATOM_BASIS_V2_NOT_PASS")

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

    atom_rows: list[dict[str, Any]] = []
    total_matches = 0
    source_class_counts: dict[str, int] = {}
    match_kind_counts: dict[str, int] = {}
    atoms_with_matches = 0

    for atom in atoms:
        proposition = atom.get("proposition")
        atom_id = atom.get("atom_id")
        if not isinstance(proposition, str) or not proposition or not isinstance(atom_id, str):
            return _fail("CANONICAL_ATOM_INVALID")

        matches = []
        for rel, source_class, blob_sha, text in file_cache:
            if proposition not in text:
                continue
            exact_hits, embedded_hits = _occurrence_hits(text, proposition)
            if not exact_hits and not embedded_hits:
                continue
            kind = "EXACT_SYMBOL_LITERAL" if exact_hits else "EMBEDDED_LITERAL"
            hits = exact_hits if exact_hits else embedded_hits
            matches.append(
                {
                    "path": rel,
                    "git_blob_sha": blob_sha,
                    "source_class": source_class,
                    "match_kind": kind,
                    "line_numbers": hits[:16],
                    "candidate_only": True,
                }
            )
            source_class_counts[source_class] = source_class_counts.get(source_class, 0) + 1
            match_kind_counts[kind] = match_kind_counts.get(kind, 0) + 1
            if len(matches) >= MAX_MATCHES_PER_ATOM:
                break

        if matches:
            atoms_with_matches += 1
        total_matches += len(matches)
        atom_rows.append(
            {
                "atom_id": atom_id,
                "proposition": proposition,
                "layers": atom.get("layers", []),
                "certificate_ids": atom.get("certificate_ids", []),
                "associated_target_predicates": atom.get("associated_target_predicates", []),
                "candidate_match_count": len(matches),
                "candidate_matches": matches,
                "candidate_only": True,
            }
        )

    zero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] == 0)
    nonzero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] > 0)
    review_priority = [
        row["atom_id"]
        for row in sorted((x for x in atom_rows if x["candidate_match_count"] > 0), key=_priority_key)
    ]
    basis_digest = _basis_manifest_sha256(atoms)
    corpus_digest = _manifest_sha256(file_cache)

    return {
        "schema": SCHEMA,
        "status": "PASS__V2_CONTENT_ADDRESSED_CANDIDATE_RECEIPT_INDEX_COMPUTED__INPUTS_FINGERPRINTED__ZERO_CREDIT",
        "errors": [],
        "source_basis_schema": basis.get("schema"),
        "source_basis_status": basis.get("status"),
        "canonical_atom_count": len(atom_rows),
        "basis_atom_manifest_sha256": basis_digest,
        "searched_roots": list(SEARCH_ROOTS),
        "excluded_basenames": sorted(EXCLUDED_BASENAMES),
        "scanned_file_count": len(file_cache),
        "scanned_corpus_manifest_sha256": corpus_digest,
        "index_input_fingerprint_sha256": _index_input_fingerprint(basis_digest, corpus_digest),
        "candidate_match_count": total_matches,
        "atoms_with_candidate_matches": atoms_with_matches,
        "atoms_without_candidate_matches": len(zero),
        "atom_ids_with_candidate_matches": nonzero,
        "atom_ids_without_candidate_matches": zero,
        "candidate_review_priority": review_priority,
        "candidate_matches_by_source_class": dict(sorted(source_class_counts.items())),
        "candidate_matches_by_kind": dict(sorted(match_kind_counts.items())),
        "atoms": atom_rows,
        "rule": (
            "ACTIVE_V2_BASIS_ONLY__LITERAL_OCCURRENCE_IS_CANDIDATE_POINTER_ONLY__"
            "CLASSIFY_EXACT_SYMBOL_VS_EMBEDDED_OCCURRENCE__CONTENT_ADDRESS_EACH_MATCH__"
            "FINGERPRINT_ENTIRE_SCANNED_CORPUS_AND_BASIS__"
            "EXCLUDE_FRONTIER_BASIS_OVERLAY_AUTHORITY_AND_INDEX_RESTATEMENTS__"
            "NO_SEMANTIC_SCOPE_METRIC_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(
            encoding="utf-8"
        )
    )
    overlay = json.loads(
        (ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(
            encoding="utf-8"
        )
    )
    out = build_index(frontier, overlay)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
