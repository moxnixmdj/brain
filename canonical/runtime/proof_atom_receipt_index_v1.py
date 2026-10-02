"""Exact-literal content-addressed receipt index for canonical proof atoms.

This module discovers existing zero-reality receipt candidates for the active
canonical proof-atom basis. It deliberately separates discovery from proof:

* An exact literal occurrence is only a mention candidate.
* A candidate becomes an explicit verified-binding candidate only when an
  independent public-runner verification receipt explicitly lists the exact
  proposition under an allowlisted proof-assertion field.
* Even an explicit verified-binding candidate grants zero acceptance,
  capability, family, execution, or promotion credit until existing admission
  and fixed-point machinery accepts it.

Scheduling/frontier/source files are excluded so an obligation cannot prove
itself merely by being declared.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from canonical.runtime.canonical_proof_atom_basis_v1 import compile_basis

SCHEMA = "PROJECT_BRAIN_PROOF_ATOM_RECEIPT_INDEX_V1"
ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SCAN_PREFIXES = (
    "canonical/verification",
    "canonical/governance",
    "canonical/reasoning",
    "canonical/capabilities/opus55",
)

DEFAULT_EXCLUDED_PATHS = frozenset({
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json",
    "canonical/governance/CANONICAL_PROOF_ATOM_BASIS_ACTIVATION_V1.json",
    "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json",
    "canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json",
    "canonical/governance/TERMINAL_INFORMATION_DOMINANCE_V5_PROJECTION.json",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_ACTIVATION_V1.json",
})

EXPLICIT_PROOF_FIELDS = frozenset({
    "proved_propositions",
    "verified_propositions",
    "discharged_propositions",
    "propositions_proved",
    "proved_atoms",
    "verified_atoms",
})


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "leaf_atom_count": 0,
        "atom_rows": [],
        "atoms_with_candidates": 0,
        "atoms_with_explicit_verified_binding_candidates": 0,
        "atoms_without_candidates": 0,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def _contains_explicit_proof_assertion(node: Any, proposition: str) -> bool:
    if isinstance(node, Mapping):
        for key, value in node.items():
            if (
                key in EXPLICIT_PROOF_FIELDS
                and isinstance(value, list)
                and proposition in value
            ):
                return True
            if _contains_explicit_proof_assertion(value, proposition):
                return True
    elif isinstance(node, list):
        return any(_contains_explicit_proof_assertion(x, proposition) for x in node)
    return False


def _candidate_metadata(rel: str, data: bytes, proposition: str) -> tuple[dict[str, Any], str | None]:
    try:
        doc = json.loads(data.decode("utf-8"))
    except Exception as exc:
        return {
            "path": rel,
            "git_blob_sha": git_blob_sha(data),
            "classification": "INVALID_JSON_EXACT_LITERAL_CANDIDATE",
        }, f"INVALID_JSON_CANDIDATE:{rel}:{type(exc).__name__}"

    schema = doc.get("schema") if isinstance(doc, Mapping) else None
    status = doc.get("status") if isinstance(doc, Mapping) else None
    is_independent_verification = (
        rel.startswith("canonical/verification/")
        and isinstance(status, str)
        and status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    )
    explicit = (
        is_independent_verification
        and _contains_explicit_proof_assertion(doc, proposition)
    )
    return {
        "path": rel,
        "git_blob_sha": git_blob_sha(data),
        "schema": schema,
        "status": status,
        "classification": (
            "EXPLICIT_INDEPENDENT_VERIFIED_BINDING_CANDIDATE"
            if explicit
            else "EXACT_LITERAL_MENTION_CANDIDATE_ONLY"
        ),
        "explicit_proof_assertion": explicit,
    }, None


def _json_files(root: Path, prefixes: Iterable[str]) -> list[Path]:
    files: set[Path] = set()
    for prefix in prefixes:
        base = root / prefix
        if base.is_dir():
            files.update(p for p in base.rglob("*.json") if p.is_file())
    return sorted(files)


def index_receipts(
    root: Path,
    basis: Mapping[str, Any],
    *,
    scan_prefixes: Iterable[str] = DEFAULT_SCAN_PREFIXES,
    excluded_paths: frozenset[str] = DEFAULT_EXCLUDED_PATHS,
) -> dict[str, Any]:
    if not isinstance(basis, Mapping) or not str(basis.get("status", "")).startswith("PASS"):
        return _fail("BASIS_NOT_ACTIVE_COMPILED_PASS")
    atoms = basis.get("atoms")
    if not isinstance(atoms, list) or not atoms:
        return _fail("BASIS_ATOMS_INVALID")

    atom_rows: list[dict[str, Any]] = []
    for atom in atoms:
        if not isinstance(atom, Mapping):
            return _fail("BASIS_ATOM_NOT_OBJECT")
        if not isinstance(atom.get("atom_id"), str) or not isinstance(atom.get("proposition"), str):
            return _fail("BASIS_ATOM_ID_OR_PROPOSITION_INVALID")
        atom_rows.append({
            "atom_id": atom["atom_id"],
            "proposition": atom["proposition"],
            "layers": list(atom.get("layers", [])),
            "certificate_ids": list(atom.get("certificate_ids", [])),
            "associated_target_predicates": list(atom.get("associated_target_predicates", [])),
            "candidate_receipts": [],
        })

    proposition_to_row = {x["proposition"]: x for x in atom_rows}
    errors: list[str] = []
    scanned_file_count = 0
    excluded_file_count = 0

    for path in _json_files(root, scan_prefixes):
        rel = path.relative_to(root).as_posix()
        if rel in excluded_paths or rel.startswith("canonical/verification/PROOF_ATOM_RECEIPT_INDEX_"):
            excluded_file_count += 1
            continue
        data = path.read_bytes()
        scanned_file_count += 1
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue

        for proposition, row in proposition_to_row.items():
            if proposition not in text:
                continue
            candidate, error = _candidate_metadata(rel, data, proposition)
            row["candidate_receipts"].append(candidate)
            if error:
                errors.append(error)

    for row in atom_rows:
        row["candidate_receipts"].sort(
            key=lambda x: (
                x["classification"] != "EXPLICIT_INDEPENDENT_VERIFIED_BINDING_CANDIDATE",
                x["path"],
            )
        )
        row["candidate_receipt_count"] = len(row["candidate_receipts"])
        row["explicit_verified_binding_candidate_count"] = sum(
            x["classification"] == "EXPLICIT_INDEPENDENT_VERIFIED_BINDING_CANDIDATE"
            for x in row["candidate_receipts"]
        )
        row["index_state"] = (
            "EXPLICIT_VERIFIED_BINDING_CANDIDATE_PRESENT"
            if row["explicit_verified_binding_candidate_count"]
            else "MENTION_CANDIDATES_ONLY"
            if row["candidate_receipt_count"]
            else "NO_EXACT_LITERAL_CANDIDATE_FOUND"
        )

    atoms_with_candidates = sum(x["candidate_receipt_count"] > 0 for x in atom_rows)
    atoms_with_explicit = sum(
        x["explicit_verified_binding_candidate_count"] > 0 for x in atom_rows
    )
    atoms_without = len(atom_rows) - atoms_with_candidates

    if errors:
        return {
            **_fail(*errors),
            "leaf_atom_count": len(atom_rows),
            "atom_rows": atom_rows,
            "scanned_file_count": scanned_file_count,
            "excluded_file_count": excluded_file_count,
            "atoms_with_candidates": atoms_with_candidates,
            "atoms_with_explicit_verified_binding_candidates": atoms_with_explicit,
            "atoms_without_candidates": atoms_without,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_LITERAL_CONTENT_ADDRESSED_RECEIPT_INDEX_COMPILED__ZERO_CREDIT",
        "errors": [],
        "basis_leaf_atom_count": len(atom_rows),
        "leaf_atom_count": len(atom_rows),
        "scanned_file_count": scanned_file_count,
        "excluded_file_count": excluded_file_count,
        "atoms_with_candidates": atoms_with_candidates,
        "atoms_with_explicit_verified_binding_candidates": atoms_with_explicit,
        "atoms_without_candidates": atoms_without,
        "atom_rows": atom_rows,
        "rules": [
            "EXACT_UTF8_PROPOSITION_LITERAL_MATCH_ONLY",
            "SCHEDULER_FRONTIER_SOURCE_FILES_EXCLUDED_FROM_RECEIPT_DISCOVERY",
            "MENTION_IS_NOT_PROOF",
            "EXPLICIT_BINDING_CANDIDATE_REQUIRES_INDEPENDENT_PUBLIC_RUNNER_PASS_AND_ALLOWLISTED_EXACT_PROOF_ASSERTION",
            "INDEX_OUTPUT_ALONE_GRANTS_ZERO_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT",
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
    matched_subfrontier = json.loads(
        (ROOT / "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json").read_text(encoding="utf-8")
    )
    basis = compile_basis(global_frontier, matched_subfrontier)
    out = index_receipts(ROOT, basis)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
