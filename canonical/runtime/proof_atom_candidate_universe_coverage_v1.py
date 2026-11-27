"""Coverage audit for the V2 proof-atom candidate universe.

The receipt index is intentionally lexical and policy-bounded. This guard makes
that boundary explicit so a sealed zero-match cannot be misread as "no evidence
exists anywhere in the search roots".

No acceptance, capability, family, execution, or promotion credit is granted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime.proof_atom_receipt_index_v2 import (
    EXCLUDED_BASENAME_PREFIXES,
    EXCLUDED_BASENAMES,
    EXCLUDED_REL_PATHS,
    MAX_FILE_BYTES,
    SEARCH_ROOTS,
    TEXT_SUFFIXES,
    _candidate_files,
)

SCHEMA = "PROJECT_BRAIN_PROOF_ATOM_CANDIDATE_UNIVERSE_COVERAGE_V1"
ROOT = Path(__file__).resolve().parents[2]


def _digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _explicitly_excluded(rel: str, name: str) -> bool:
    return (
        rel in EXCLUDED_REL_PATHS
        or name in EXCLUDED_BASENAMES
        or any(name.startswith(prefix) for prefix in EXCLUDED_BASENAME_PREFIXES)
    )


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "rows": [],
        "candidate_selection_parity": False,
        "negative_literal_exhaustive_within_configured_candidate_set": False,
        "negative_literal_exhaustive_over_supported_text_in_search_roots": False,
        "negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def audit_coverage(*, root: Path = ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    policy_candidate_paths: list[str] = []
    scan_gap_paths: list[str] = []
    oversized_supported_text_paths: list[str] = []
    unsupported_suffix_paths: list[str] = []
    explicit_exclusion_paths: list[str] = []

    for rel_root in SEARCH_ROOTS:
        base = root / rel_root
        if not base.exists():
            errors.append(f"MISSING_SEARCH_ROOT:{rel_root}")
            continue

        try:
            paths = sorted(
                base.rglob("*"),
                key=lambda p: p.relative_to(root).as_posix(),
            )
        except OSError as exc:
            errors.append(f"ENUMERATION_ERROR:{rel_root}:{type(exc).__name__}")
            continue

        for path in paths:
            try:
                if not path.is_file():
                    continue
            except OSError as exc:
                rel = path.relative_to(root).as_posix()
                errors.append(f"FILE_TYPE_ERROR:{rel}:{type(exc).__name__}")
                scan_gap_paths.append(rel)
                rows.append({"path": rel, "disposition": "FILE_TYPE_ERROR"})
                continue

            rel = path.relative_to(root).as_posix()
            name = path.name
            suffix = path.suffix.lower()

            if _explicitly_excluded(rel, name):
                explicit_exclusion_paths.append(rel)
                rows.append(
                    {
                        "path": rel,
                        "disposition": "EXPLICIT_PROVENANCE_RESTATEMENT_EXCLUSION",
                    }
                )
                continue

            if suffix not in TEXT_SUFFIXES:
                unsupported_suffix_paths.append(rel)
                rows.append(
                    {
                        "path": rel,
                        "disposition": "UNSUPPORTED_SUFFIX_POLICY_EXCLUSION",
                        "suffix": suffix,
                    }
                )
                continue

            try:
                size = path.stat().st_size
            except OSError as exc:
                errors.append(f"STAT_ERROR:{rel}:{type(exc).__name__}")
                scan_gap_paths.append(rel)
                rows.append({"path": rel, "disposition": "STAT_ERROR"})
                continue

            if size > MAX_FILE_BYTES:
                oversized_supported_text_paths.append(rel)
                rows.append(
                    {
                        "path": rel,
                        "disposition": "OVERSIZE_SUPPORTED_TEXT_POLICY_EXCLUSION",
                        "size_bytes": size,
                        "max_file_bytes": MAX_FILE_BYTES,
                    }
                )
                continue

            policy_candidate_paths.append(rel)
            try:
                data = path.read_bytes()
            except OSError as exc:
                errors.append(f"READ_ERROR:{rel}:{type(exc).__name__}")
                scan_gap_paths.append(rel)
                rows.append(
                    {
                        "path": rel,
                        "disposition": "READ_ERROR",
                        "size_bytes": size,
                    }
                )
                continue

            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                errors.append(f"NON_UTF8_SUPPORTED_TEXT:{rel}")
                scan_gap_paths.append(rel)
                rows.append(
                    {
                        "path": rel,
                        "disposition": "NON_UTF8_SUPPORTED_TEXT",
                        "size_bytes": size,
                    }
                )
                continue

            rows.append(
                {
                    "path": rel,
                    "disposition": "SCANNABLE_CONFIGURED_CANDIDATE",
                    "size_bytes": size,
                }
            )

    actual_candidate_paths = [
        p.relative_to(root).as_posix() for p in _candidate_files(root)
    ]
    candidate_selection_parity = policy_candidate_paths == actual_candidate_paths
    if not candidate_selection_parity:
        errors.append("CANDIDATE_SELECTION_PARITY_MISMATCH")

    configured_complete = candidate_selection_parity and not scan_gap_paths
    supported_text_complete = configured_complete and not oversized_supported_text_paths
    all_nonexcluded_complete = supported_text_complete and not unsupported_suffix_paths

    status = (
        "PASS__CANDIDATE_UNIVERSE_BOUNDARY_EXPLICIT__ZERO_CREDIT"
        if configured_complete
        else "FAIL_CLOSED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "search_roots": list(SEARCH_ROOTS),
        "text_suffixes": sorted(TEXT_SUFFIXES),
        "max_file_bytes": MAX_FILE_BYTES,
        "candidate_selection_parity": candidate_selection_parity,
        "configured_candidate_count": len(policy_candidate_paths),
        "scannable_configured_candidate_count": sum(
            row["disposition"] == "SCANNABLE_CONFIGURED_CANDIDATE" for row in rows
        ),
        "scan_gap_count": len(scan_gap_paths),
        "scan_gap_paths": sorted(scan_gap_paths),
        "oversized_supported_text_count": len(oversized_supported_text_paths),
        "oversized_supported_text_paths": sorted(oversized_supported_text_paths),
        "unsupported_suffix_count": len(unsupported_suffix_paths),
        "unsupported_suffix_paths": sorted(unsupported_suffix_paths),
        "explicit_provenance_exclusion_count": len(explicit_exclusion_paths),
        "explicit_provenance_exclusion_paths": sorted(explicit_exclusion_paths),
        "negative_literal_exhaustive_within_configured_candidate_set": configured_complete,
        "negative_literal_exhaustive_over_supported_text_in_search_roots": supported_text_complete,
        "negative_literal_exhaustive_over_all_nonexcluded_files_in_search_roots": all_nonexcluded_complete,
        "rows_manifest_sha256": _digest(rows),
        "rows": rows,
        "rule": (
            "POSITIVE_LITERAL_MATCHES_REMAIN_CANDIDATE_POINTERS_ONLY__"
            "ZERO_MATCH_SCOPE_MUST_BE_STATED_EXPLICITLY__"
            "OVERSIZE_SUPPORTED_TEXT_CANNOT_BE_SILENTLY_TREATED_AS_NEGATIVE_EVIDENCE__"
            "UNSUPPORTED_SUFFIXES_CANNOT_BE_SILENTLY_TREATED_AS_NEGATIVE_EVIDENCE__"
            "CONFIGURED_CANDIDATE_SELECTION_MUST_MATCH_INDEXER_EXACTLY__"
            "NO_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = audit_coverage()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
