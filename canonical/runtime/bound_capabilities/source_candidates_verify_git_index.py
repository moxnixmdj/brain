#!/usr/bin/env python3
"""Independently verify a source-candidate enumeration against the git index.

`source.candidates.enumerate.stdlib` walks the filesystem with `pathlib.Path.glob`
and hashes with `hashlib`. Nothing in the registry checked that walk, so the bound
adapter had no independence evidence for it and refused to run it -- which blocked
every goal whose chain began with it.

This follows the pattern the repository already uses for exactly this problem:
`archive_verify_gnu_tar.py` does not re-run the archiver, it asks the *external GNU
tar binary* for the member list and compares. Independence here is a different
implementation, not a different opinion:

  * the file set comes from `git ls-files`, i.e. the git index -- a different
    mechanism than a filesystem glob, maintained by a different program;
  * every digest comes from the external `sha256sum` binary, not from `hashlib`;
  * the pattern is matched with `fnmatch`, not `pathlib`'s glob translator.

Any disagreement raises. Nothing here scores, selects or repairs; it only reports
whether two independent mechanisms agree on the same bytes.
"""
from __future__ import annotations

import fnmatch
import json
import pathlib
import subprocess


def _safe(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _suffix_pattern(pattern: str) -> str:
    """The `fnmatch` form of a `**/`-prefixed glob, matched against search-root-relative paths."""
    return pattern[3:] if pattern.startswith("**/") else pattern


def _matches(rel_from_root: str, search_root: str, pattern: str) -> bool:
    prefix = "" if search_root in ("", ".") else search_root.rstrip("/") + "/"
    if not rel_from_root.startswith(prefix):
        return False
    return fnmatch.fnmatch(rel_from_root[len(prefix):], _suffix_pattern(pattern))


def _independent_digests(root, paths):
    """{path: sha256} from the external sha256sum binary, in batches."""
    out = {}
    batch = 200
    for start in range(0, len(paths), batch):
        chunk = paths[start:start + batch]
        proc = subprocess.run(["sha256sum", "--"] + chunk, cwd=str(root),
                              text=True, capture_output=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError("SHA256SUM_FAILED:" + (proc.stderr or "")[-1200:])
        for line in proc.stdout.splitlines():
            if len(line) < 67:
                continue
            # sha256 hex is always 64 chars, then a two-char mode separator, then the name.
            out[line[66:]] = line[:64]
    return out


def run(args, root):
    args = dict(args or {})
    root_path = pathlib.Path(root).resolve()
    enum_path = _safe(root, args.get("enumeration_path") or args.get("output_path"))
    if not enum_path.is_file():
        raise RuntimeError("ENUMERATION_INPUT_REQUIRED")

    payload = json.loads(enum_path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("ENUMERATION_CANDIDATES_MISSING")

    search_root = str(payload.get("search_root") or ".")
    pattern = str(payload.get("glob") or "**/*.py")

    listing = subprocess.run(["git", "ls-files", "--", search_root], cwd=str(root_path),
                             text=True, capture_output=True, timeout=120)
    if listing.returncode != 0:
        raise RuntimeError("GIT_LS_FILES_FAILED:" + (listing.stderr or "")[-1200:])
    tracked = sorted(x for x in listing.stdout.splitlines() if x.strip())
    matched = [rel for rel in tracked if _matches(rel, search_root, pattern)]
    # The producer stops at its own candidate_count, in sorted order; compare the same slice.
    expected = sorted(matched)[:len(candidates)]
    observed = sorted(str(c.get("title") or "") for c in candidates)
    if observed != expected:
        raise RuntimeError("CANDIDATE_SET_MISMATCH:" + json.dumps({
            "expected_count": len(expected), "observed_count": len(observed),
            "only_in_git_index": sorted(set(expected) - set(observed))[:10],
            "only_in_enumeration": sorted(set(observed) - set(expected))[:10],
        }, sort_keys=True)[:3000])

    claimed = {str(c.get("title") or ""): str(c.get("sha256") or "") for c in candidates}
    independent = _independent_digests(root_path, observed)
    mismatches = sorted(
        rel for rel in observed
        if claimed.get(rel) != independent.get(rel)
    )
    if mismatches:
        raise RuntimeError("CANDIDATE_DIGEST_MISMATCH:" + json.dumps({
            "count": len(mismatches), "sample": mismatches[:5],
        }, sort_keys=True)[:2000])

    size_mismatches = sorted(
        str(c.get("title")) for c in candidates
        if int(c.get("bytes") or -1) != (root_path / str(c.get("title"))).stat().st_size
    )
    if size_mismatches:
        raise RuntimeError("CANDIDATE_SIZE_MISMATCH:" + json.dumps(size_mismatches[:5])[:1000])

    return {
        "adapter": "source_candidates_verify_git_index",
        "status": "SOURCE_CANDIDATES_INDEPENDENTLY_VERIFIED",
        "verified": True,
        "candidate_count": len(observed),
        "enumeration_path": str(enum_path.resolve().relative_to(root_path)).replace("\\", "/"),
        "search_root": search_root,
        "glob": pattern,
        "independent_enumeration_source": "git ls-files (git index)",
        "independent_digest_source": "sha256sum (coreutils)",
        "independent_pattern_matcher": "fnmatch",
        "tracked_files_considered": len(tracked),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
