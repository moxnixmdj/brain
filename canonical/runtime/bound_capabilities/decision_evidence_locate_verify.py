#!/usr/bin/env python3
"""Independently verify a located typed decision problem against external tools.

`structured.decision_evidence.locate.stdlib` walks the filesystem with
`pathlib.Path.glob`, parses with `json`, hashes with `hashlib`, and canonicalises with
`json.dumps`. Nothing in the registry checked any of that, so the bound adapter had no
independence evidence for it and refused to run it -- which blocked every goal whose
chain began with it, including `EXT_DECISION_VERIFY`.

This follows the pattern the repository already uses for exactly this problem:
`archive_verify_gnu_tar.py` does not re-run the archiver, it asks the external GNU tar
binary for the member list and compares; `source_candidates_verify_git_index.py` asks
`git ls-files` and `sha256sum`. Independence is a different implementation, not a
different opinion. Every load-bearing claim is therefore re-established by a mechanism
the producer does not use:

  * the candidate set comes from `git grep -l` -- git's own content search over the
    index, not a filesystem glob;
  * every digest comes from the external `sha256sum` binary, not from `hashlib`;
  * canonical form and document equality come from the external `jq` binary, not from
    Python's `json` serialiser;
  * the reported counts are extracted with `jq`, not by `len()` on a parsed dict;
  * decidability is re-established by re-running the consumer's own validator on bytes
    re-opened from disk, so the claim is checked against the authority that will
    actually consume it rather than trusted from the producer's report.

The selection rule is reproduced, not assumed: the located source must be the first
candidate, in sorted order, that the consumer's validator decides.

Any disagreement raises or reports `verified: false`. Nothing here scores, selects or
repairs; it only reports whether independent mechanisms agree on the same bytes.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1"


def _safe(root, raw, require_file=False):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if require_file and not p.is_file():
        raise RuntimeError("INPUT_FILE_MISSING:" + str(raw))
    return p


def _run(cmd, root):
    proc = subprocess.run(
        cmd, cwd=str(root), text=True, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(
            "INDEPENDENT_TOOL_FAILED:" + cmd[0] + ":" + (proc.stderr or "").strip()[:200])
    return proc.stdout


def _sha256sum(path, root):
    """Digest from coreutils, not from hashlib."""
    out = _run(["sha256sum", str(path)], root)
    digest = out.split()[0] if out.split() else ""
    if len(digest) != 64:
        raise RuntimeError("SHA256SUM_OUTPUT_INVALID:" + out[:80])
    return digest


def _jq_canonical(path, root):
    """Sorted-key canonical form from the jq binary, not from Python's json."""
    return _run(["jq", "-S", "--indent", "2", ".", str(path)], root)


def _jq_length(path, key, root):
    out = _run(["jq", "-r", "(.%s // []) | length" % key, str(path)], root).strip()
    try:
        return int(out)
    except ValueError:
        raise RuntimeError("JQ_LENGTH_INVALID:" + key + ":" + out[:60])


def _git_schema_candidates(root, search_root):
    """Files declaring the schema, found by git's own content search."""
    prefix = "" if str(search_root) in ("", ".") else str(search_root).rstrip("/") + "/"
    out = _run(
        ["git", "grep", "-l", "-F", SCHEMA, "--", (prefix + "*.json") or "*.json"],
        root,
    )
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def _synthesis_module(root):
    """The consumer's own validator -- the authority that will consume this problem."""
    path = (
        pathlib.Path(root).resolve()
        / "canonical/runtime/bound_capabilities/evidence_decision_synthesis.py"
    )
    spec = importlib.util.spec_from_file_location("evidence_decision_synthesis_indep", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("DECISION_SYNTHESIS_ADAPTER_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _decides(synthesis, problem):
    try:
        result = synthesis.synthesize(problem)
    except Exception:
        return False
    return isinstance(result, dict) and result.get("status") == "DECIDED"


def run(args, root):
    args = dict(args or {})
    root_path = pathlib.Path(root).resolve()
    result_doc = json.loads(
        _safe(root, args.get("result_path"), require_file=True).read_text(encoding="utf-8"))
    search_root = str(args.get("search_root") or ".")

    source_rel = str(result_doc.get("source_path") or "")
    output_rel = str(result_doc.get("output_path") or "")
    if not source_rel or not output_rel:
        raise RuntimeError("RESULT_PATHS_MISSING")
    source = _safe(root, source_rel, require_file=True)
    output = _safe(root, output_rel, require_file=True)

    mismatches = []

    # 1. Digests, from coreutils.
    actual_source = _sha256sum(source, root_path)
    actual_output = _sha256sum(output, root_path)
    if actual_source != str(result_doc.get("source_sha256") or ""):
        mismatches.append("SOURCE_SHA256_MISMATCH")
    if actual_output != str(result_doc.get("output_sha256") or ""):
        mismatches.append("OUTPUT_SHA256_MISMATCH")

    # 2. The located file really declares the schema, per git's own search.
    candidates = _git_schema_candidates(root_path, search_root)
    if source_rel not in candidates:
        mismatches.append("SOURCE_NOT_IN_GIT_SCHEMA_CANDIDATES")

    # 3. The output is the same document as the source, per jq -- so the locator
    #    copied a real problem rather than emitting something of its own.
    if _jq_canonical(source, root_path) != _jq_canonical(output, root_path):
        mismatches.append("OUTPUT_NOT_CANONICALLY_EQUAL_TO_SOURCE")

    # 4. The reported counts, extracted by jq rather than by len() on a parsed dict.
    for key, field in (
        ("alternatives", "alternative_count"),
        ("constraints", "constraint_count"),
        ("evidence", "evidence_count"),
    ):
        independent = _jq_length(source, key, root_path)
        if independent != int(result_doc.get(field) or -1):
            mismatches.append("COUNT_MISMATCH:" + field)

    # 5. Decidability, and that the selection rule was followed: the located source
    #    must be the first candidate in sorted order that the consumer decides.
    synthesis = _synthesis_module(root_path)
    first_deciding = None
    for rel in candidates:
        path = _safe(root, rel)
        if not path.is_file():
            continue
        try:
            problem = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if not isinstance(problem, dict) or problem.get("schema") != SCHEMA:
            continue
        if _decides(synthesis, problem):
            first_deciding = rel
            break
    if first_deciding is None:
        mismatches.append("NO_DECIDABLE_CANDIDATE_FOUND_INDEPENDENTLY")
    elif first_deciding != source_rel:
        mismatches.append("SELECTION_NOT_FIRST_DECIDABLE:" + str(first_deciding))

    return {
        "adapter": "decision_evidence_locate_verify",
        "verified": not mismatches,
        "mismatches": mismatches,
        "source_path": source_rel,
        "output_path": output_rel,
        "source_sha256": actual_source,
        "output_sha256": actual_output,
        "independent_enumeration_source": "git grep -l (git content search)",
        "independent_digest_source": "sha256sum (coreutils)",
        "independent_canonicalisation_source": "jq -S (jq binary)",
        "independent_count_source": "jq (jq binary)",
        "git_schema_candidate_count": len(candidates),
        "first_decidable_candidate": first_deciding,
        "decidability_authority": "evidence_decision_synthesis.synthesize re-run on re-opened bytes",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "output_verified": not mismatches,
    }
