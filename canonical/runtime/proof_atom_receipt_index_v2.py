"""Content-addressed candidate receipt index for canonical proof atoms.

This is discovery only. Exact proposition occurrence identifies a file worth explicit
semantic review; it is never acceptance evidence by itself.
"""
from __future__ import annotations

import hashlib
import json
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
ACTIVE_BASIS_AUTHORITY = "canonical/governance/CANONICAL_PROOF_ATOM_BASIS_V2_ACTIVE_AUTHORITY_V1.json"

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


def _load_json_bytes(root: Path, rel: str) -> tuple[dict[str, Any], bytes]:
    data = (root / rel).read_bytes()
    return json.loads(data.decode("utf-8")), data


def validate_active_basis_binding(*, root: Path = ROOT) -> dict[str, Any]:
    """Fail closed unless the scanner consumes the exact independently verified V2 basis world."""
    errors: list[str] = []
    try:
        authority, authority_bytes = _load_json_bytes(root, ACTIVE_BASIS_AUTHORITY)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "status": "FAIL_CLOSED",
            "errors": [f"ACTIVE_BASIS_AUTHORITY_UNREADABLE:{type(exc).__name__}"],
        }

    if not str(authority.get("status", "")).startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("ACTIVE_BASIS_AUTHORITY_STATUS_NOT_INDEPENDENT_PASS")

    verified = authority.get("verified_candidate")
    if not isinstance(verified, Mapping):
        return {"status": "FAIL_CLOSED", "errors": ["ACTIVE_BASIS_VERIFIED_CANDIDATE_MISSING"]}

    bindings = (
        ("frontier_path", "frontier_git_blob_sha"),
        ("refinement_overlay_path", "refinement_overlay_git_blob_sha"),
        ("runtime_path", "runtime_git_blob_sha"),
        ("tests_path", "tests_git_blob_sha"),
        ("governance_path", "governance_git_blob_sha"),
    )
    exact_blobs: dict[str, str] = {}
    for path_key, sha_key in bindings:
        rel = verified.get(path_key)
        expected = verified.get(sha_key)
        if not isinstance(rel, str) or not rel or not isinstance(expected, str) or len(expected) != 40:
            errors.append(f"ACTIVE_BASIS_PIN_INVALID:{path_key}:{sha_key}")
            continue
        try:
            actual = _blob_sha((root / rel).read_bytes())
        except OSError:
            errors.append(f"ACTIVE_BASIS_PIN_UNREADABLE:{rel}")
            continue
        exact_blobs[rel] = actual
        if actual != expected:
            errors.append(f"ACTIVE_BASIS_BLOB_MISMATCH:{rel}:{expected}:{actual}")

    verification_path = verified.get("verification_path")
    receipt: Mapping[str, Any] = {}
    if not isinstance(verification_path, str) or not verification_path:
        errors.append("ACTIVE_BASIS_VERIFICATION_PATH_MISSING")
    else:
        try:
            receipt_obj, _ = _load_json_bytes(root, verification_path)
            receipt = receipt_obj
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"ACTIVE_BASIS_VERIFICATION_UNREADABLE:{type(exc).__name__}")

    if receipt:
        if not str(receipt.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
            errors.append("ACTIVE_BASIS_VERIFICATION_STATUS_NOT_PASS")
        receipt_blobs = receipt.get("exact_brain_blobs")
        if not isinstance(receipt_blobs, Mapping):
            errors.append("ACTIVE_BASIS_VERIFICATION_EXACT_BLOBS_MISSING")
        else:
            for rel, actual in exact_blobs.items():
                if receipt_blobs.get(rel) != actual:
                    errors.append(f"ACTIVE_BASIS_RECEIPT_PIN_MISMATCH:{rel}")

    if errors:
        return {
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "authority_path": ACTIVE_BASIS_AUTHORITY,
            "authority_git_blob_sha": _blob_sha(authority_bytes),
            "exact_blobs": dict(sorted(exact_blobs.items())),
        }
    return {
        "status": "PASS__EXACT_ACTIVE_INDEPENDENTLY_VERIFIED_V2_BASIS_BOUND",
        "errors": [],
        "authority_path": ACTIVE_BASIS_AUTHORITY,
        "authority_git_blob_sha": _blob_sha(authority_bytes),
        "verification_path": verification_path,
        "exact_blobs": dict(sorted(exact_blobs.items())),
    }


def build_active_index(*, root: Path = ROOT) -> dict[str, Any]:
    binding = validate_active_basis_binding(root=root)
    if not str(binding.get("status", "")).startswith("PASS"):
        out = _fail("ACTIVE_BASIS_BINDING_NOT_PASS", *binding.get("errors", []))
        out["basis_binding"] = binding
        return out

    authority, _ = _load_json_bytes(root, ACTIVE_BASIS_AUTHORITY)
    verified = authority["verified_candidate"]
    global_frontier, _ = _load_json_bytes(root, verified["frontier_path"])
    refinement_overlay, _ = _load_json_bytes(root, verified["refinement_overlay_path"])
    out = build_index(global_frontier, refinement_overlay, root=root)
    out["basis_binding"] = binding
    return out


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
            "candidate_match_count": len(matches),
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
        "scanned_file_count": len(file_cache),
        "candidate_match_count": total_matches,
        "atoms_with_candidate_matches": atoms_with_matches,
        "atoms_without_candidate_matches": len(zero),
        "atom_ids_with_candidate_matches": nonzero,
        "atom_ids_without_candidate_matches": zero,
        "candidate_matches_by_source_class": dict(sorted(source_class_counts.items())),
        "atoms": atom_rows,
        "rule": (
            "EXACT_LITERAL_OCCURRENCE_IS_CANDIDATE_POINTER_ONLY__"
            "CONTENT_ADDRESS_EACH_MATCH__EXCLUDE_FRONTIER_AND_SCHEDULER_RESTATEMENTS__"
            "NO_SEMANTIC_SCOPE_METRIC_ACCEPTANCE_OR_FAMILY_CREDIT_FROM_INDEX"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = build_active_index()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
