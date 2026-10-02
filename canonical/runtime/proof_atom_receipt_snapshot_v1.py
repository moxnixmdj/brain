"""Sealed repository snapshot for the V2 proof-atom receipt index.

V2 discovers candidate evidence. This wrapper makes both positive matches and
negative-search claims replayable by binding the exact Git commit/tree and the
complete candidate-file universe. It grants no acceptance or capability credit.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.proof_atom_receipt_index_v2 import (
    ROOT,
    SEARCH_ROOTS,
    _blob_sha,
    _candidate_files,
    _manifest_sha256,
    _source_class,
    build_index,
)

SCHEMA = "PROJECT_BRAIN_PROOF_ATOM_RECEIPT_SNAPSHOT_V1"


def _git(root: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout.strip()


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def seal_candidate_universe(root: Path, files: Sequence[Path]) -> dict[str, Any]:
    """Bind every scanned candidate file to HEAD and hash the ordered manifest."""
    manifest: list[dict[str, Any]] = []
    for path in sorted(files, key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        computed = _blob_sha(data)
        head_blob = _git(root, "rev-parse", f"HEAD:{rel}")
        if computed != head_blob:
            raise RuntimeError(
                f"WORKTREE_OR_INDEX_DRIFT:{rel}:computed={computed}:head={head_blob}"
            )
        manifest.append(
            {
                "path": rel,
                "git_blob_sha": computed,
                "size_bytes": len(data),
                "source_class": _source_class(rel),
            }
        )

    root_trees: dict[str, str] = {}
    for rel_root in SEARCH_ROOTS:
        root_trees[rel_root] = _git(root, "rev-parse", f"HEAD:{rel_root}")

    return {
        "repository_commit_sha": _git(root, "rev-parse", "HEAD"),
        "repository_tree_sha": _git(root, "rev-parse", "HEAD^{tree}"),
        "search_root_tree_shas": root_trees,
        "scanned_file_count": len(manifest),
        "scanned_files": manifest,
        "scanned_manifest_sha256": _canonical_digest(manifest),
    }


def _index_compatible_manifest_sha256(seal: Mapping[str, Any]) -> str:
    rows = [
        (
            str(row["path"]),
            str(row["source_class"]),
            str(row["git_blob_sha"]),
            "",
        )
        for row in seal.get("scanned_files", [])
    ]
    return _manifest_sha256(rows)


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def build_snapshot(
    global_frontier: Mapping[str, Any],
    refinement_overlay: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    try:
        if _git(root, "status", "--porcelain"):
            return _fail("WORKTREE_NOT_CLEAN")

        index = build_index(global_frontier, refinement_overlay, root=root)
        if not str(index.get("status", "")).startswith("PASS"):
            return _fail("V2_INDEX_NOT_PASS")

        files = _candidate_files(root)
        seal = seal_candidate_universe(root, files)
        if int(index.get("scanned_file_count", -1)) != int(seal["scanned_file_count"]):
            return _fail("SCANNED_FILE_COUNT_MISMATCH")

        sealed_index_manifest_sha256 = _index_compatible_manifest_sha256(seal)
        if index.get("scanned_corpus_manifest_sha256") != sealed_index_manifest_sha256:
            return _fail("SCANNED_CORPUS_MANIFEST_MISMATCH")

        manifest_map = {
            row["path"]: row["git_blob_sha"] for row in seal["scanned_files"]
        }
        for atom in index.get("atoms", []):
            for match in atom.get("candidate_matches", []):
                path = match.get("path")
                if manifest_map.get(path) != match.get("git_blob_sha"):
                    return _fail("CANDIDATE_MATCH_OUTSIDE_SEALED_UNIVERSE")

        input_paths = [
            "canonical/runtime/proof_atom_receipt_index_v2.py",
            "canonical/runtime/canonical_proof_atom_basis_v2.py",
            "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
            "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json",
        ]
        inputs = {p: _git(root, "rev-parse", f"HEAD:{p}") for p in input_paths}

        return {
            "schema": SCHEMA,
            "status": "PASS__SEALED_REPLAYABLE_V2_RECEIPT_SNAPSHOT__ZERO_CREDIT",
            "errors": [],
            "proof_input_git_blob_shas": inputs,
            "repository_snapshot": seal,
            "sealed_index_compatible_manifest_sha256": sealed_index_manifest_sha256,
            "index": index,
            "index_sha256": _canonical_digest(index),
            "rule": (
                "POSITIVE_AND_NEGATIVE_DISCOVERY_CLAIMS_BOUND_TO_ONE_EXACT_GIT_SNAPSHOT__"
                "EVERY_SCANNED_FILE_CONTENT_ADDRESSED__"
                "INDEX_SCANNED_CORPUS_DIGEST_MUST_EQUAL_SEALED_UNIVERSE_DIGEST__"
                "ZERO_MATCH_MEANS_ZERO_LITERAL_MATCHES_ONLY_WITHIN_THE_SEALED_CANDIDATE_UNIVERSE__"
                "NO_SEMANTIC_SCOPE_METRIC_ACCEPTANCE_CAPABILITY_OR_FAMILY_CREDIT"
            ),
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }
    except Exception as exc:
        return _fail(f"SNAPSHOT_EXCEPTION:{type(exc).__name__}:{exc}")


def main() -> int:
    global_frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(
            encoding="utf-8"
        )
    )
    refinement_overlay = json.loads(
        (ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(
            encoding="utf-8"
        )
    )
    out = build_snapshot(global_frontier, refinement_overlay)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
