"""Refinement-aware, content-addressed candidate receipt index for canonical proof atoms.

Discovery only. Candidate occurrence never grants acceptance, capability, family,
execution, or promotion credit. V2 binds the verified proof-atom basis v2 and
fingerprints the entire scanned corpus so an index result is reproducible.
"""
from __future__ import annotations

import hashlib
import json
import os
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

# These are structural definitions / schedulers, not evidence that their own leaf
# propositions are true. Excluding them prevents circular candidate discovery.
EXCLUDED_BASENAMES = {
    "TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json",
    "OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json",
    "MATCHED_SCOPE_BINDING_SUBHYPERGRAPH_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_ACTIVATION_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_ACTIVATION_V2.json",
    "CANONICAL_PROOF_ATOM_BASIS_V2.json",
    "CANONICAL_PROOF_ATOM_BASIS_V2_ACTIVATION_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_V2_ACTIVE_AUTHORITY_V1.json",
    "PROOF_ATOM_REFINEMENT_OVERLAY_V1.json",
    "MULTITARGET_CERTIFICATE_TARGET_REFINEMENT_ACTIVATION_V1.json",
    "CURRENT_TERMINAL_AUTHORITY_V1.json",
    "EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json",
    "PROOF_ATOM_RECEIPT_INDEX_V1.json",
    "PROOF_ATOM_RECEIPT_INDEX_V2.json",
    "CANONICAL_PROOF_ATOM_BASIS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "CANONICAL_PROOF_ATOM_BASIS_V2_HARDENED_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "PROOF_ATOM_RECEIPT_INDEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "GLOBAL_ABDUCTIVE_AND_MULTITARGET_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
}
EXCLUDED_REL_PATHS = {
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V1.json",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json",
}


def _canonical_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


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
    return hashlib.sha1(f"blob {len(data)}\\0".encode() + data).hexdigest()


def _path_blob_sha(root: Path, rel: str) -> str | None:
    p = root / rel
    try:
        return _blob_sha(p.read_bytes())
    except OSError:
        return None


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


def _line_hits(text: str, literal: str) -> list[int]:
    return [i for i, line in enumerate(text.splitlines(), start=1) if literal in line]


def build_index(
    global_frontier: Mapping[str, Any],
    refinement_overlay: Mapping[str, Any],
    *,
    root: Path = ROOT,
    source_revision: str | None = None,
) -> dict[str, Any]:
    basis = compile_basis(global_frontier, refinement_overlay)
    if not str(basis.get("status", "")).startswith("PASS"):
        return _fail("CANONICAL_PROOF_ATOM_BASIS_V2_NOT_PASS")

    atoms = basis.get("atoms")
    if not isinstance(atoms, list) or not atoms:
        return _fail("CANONICAL_ATOMS_MISSING")
    if any(not str(x.get("atom_id", "")).startswith("PA1:") for x in atoms):
        return _fail("PA1_ATOM_ID_CONTINUITY_VIOLATION")

    files = _candidate_files(root)
    file_cache: list[tuple[str, str, str, str]] = []
    corpus_manifest: list[dict[str, str]] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        blob = _blob_sha(data)
        file_cache.append((rel, _source_class(rel), blob, text))
        corpus_manifest.append({"path": rel, "git_blob_sha": blob})

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
        for rel, source_class, blob_sha, text in file_cache:
            if proposition not in text:
                continue
            hits = _line_hits(text, proposition)
            if not hits:
                continue
            matches.append({
                "path": rel,
                "git_blob_sha": blob_sha,
                "source_class": source_class,
                "line_numbers": hits[:16],
                "candidate_only": True,
            })
            source_class_counts[source_class] = source_class_counts.get(source_class, 0) + 1
            if len(matches) >= MAX_MATCHES_PER_ATOM:
                break

        if matches:
            atoms_with_matches += 1
        total_matches += len(matches)
        atom_rows.append({
            "atom_id": atom_id,
            "proposition": proposition,
            "associated_target_predicates": atom.get("associated_target_predicates", []),
            "associated_target_count": atom.get("associated_target_count", 0),
            "candidate_match_count": len(matches),
            "candidate_matches": matches,
            "candidate_only": True,
        })

    zero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] == 0)
    nonzero = sorted(row["atom_id"] for row in atom_rows if row["candidate_match_count"] > 0)
    atom_manifest = [
        {"atom_id": row["atom_id"], "proposition": row["proposition"]}
        for row in sorted(atom_rows, key=lambda x: x["atom_id"])
    ]
    review_queue = [
        row["atom_id"]
        for row in sorted(
            (x for x in atom_rows if x["candidate_match_count"] > 0),
            key=lambda x: (-x["candidate_match_count"], -x["associated_target_count"], x["atom_id"]),
        )
    ]

    frontier_rel = "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
    overlay_rel = "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json"
    basis_runtime_rel = "canonical/runtime/canonical_proof_atom_basis_v2.py"
    index_runtime_rel = "canonical/runtime/proof_atom_receipt_index_v2.py"

    out = {
        "schema": SCHEMA,
        "status": "PASS__V2_BASIS_BOUND_CONTENT_ADDRESSED_CORPUS_INDEX__ZERO_CREDIT",
        "errors": [],
        "source_revision": source_revision,
        "basis_binding": {
            "schema": basis.get("schema"),
            "status": basis.get("status"),
            "refined_parent_count": basis.get("refined_parent_count"),
            "canonical_atom_count": len(atom_rows),
            "atom_manifest_sha256": _canonical_sha256(atom_manifest),
            "frontier_git_blob_sha": _path_blob_sha(root, frontier_rel),
            "refinement_overlay_git_blob_sha": _path_blob_sha(root, overlay_rel),
            "basis_runtime_git_blob_sha": _path_blob_sha(root, basis_runtime_rel),
            "index_runtime_git_blob_sha": _path_blob_sha(root, index_runtime_rel),
        },
        "canonical_atom_count": len(atom_rows),
        "scanned_file_count": len(file_cache),
        "scanned_corpus_manifest_sha256": _canonical_sha256(corpus_manifest),
        "candidate_match_count": total_matches,
        "atoms_with_candidate_matches": atoms_with_matches,
        "atoms_without_candidate_matches": len(zero),
        "atom_ids_with_candidate_matches": nonzero,
        "atom_ids_without_candidate_matches": zero,
        "candidate_matches_by_source_class": dict(sorted(source_class_counts.items())),
        "zero_reality_semantic_review_queue": review_queue,
        "atoms": atom_rows,
        "rule": (
            "EXACT_LITERAL_OCCURRENCE_IS_CANDIDATE_POINTER_ONLY__"
            "FULL_SCANNED_CORPUS_IS_MANIFEST_HASHED__"
            "V2_BASIS_AND_REFINEMENT_INPUTS_ARE_CONTENT_ADDRESSED__"
            "STRUCTURAL_DEFINITION_AND_COMPILER_VERIFICATION_SOURCES_ARE_EXCLUDED__"
            "NO_SEMANTIC_SCOPE_METRIC_ACCEPTANCE_OR_FAMILY_CREDIT_FROM_INDEX"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
    core = dict(out)
    core.pop("result_payload_sha256", None)
    out["result_payload_sha256"] = _canonical_sha256(core)
    return out


def main() -> int:
    frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(encoding="utf-8")
    )
    overlay = json.loads(
        (ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(encoding="utf-8")
    )
    out = build_index(
        frontier,
        overlay,
        source_revision=os.environ.get("BRAIN_SOURCE_COMMIT"),
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
