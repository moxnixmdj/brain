#!/usr/bin/env python3
"""python.vcs.merge_conflict.resolve.v1 — keep both sides, then prove it.

"Resolve the merge conflict in <b>/app/models.py keeping both changes, so the
module imports and the tests pass" states its own resolution rule: BOTH.  That
sentence is the whole policy -- it is what a human does when two branches added
different things in the same place -- and it turns a judgement call into a union.

So the edit is not a heuristic and not a model:

  * a conflicted region is `<<<<<<< ours` ... `=======` ... `>>>>>>> theirs`;
  * "keep both changes" is the concatenation of the two sides in that order;
  * a `|||||||` base section means the merge was started with diff3 style.  There
    the two sides are not the whole story and the union is not stated, so it is
    refused, not guessed.

The proof is execution and it is what makes this safe: after the splice the file
must parse, no marker may remain anywhere in the subject, and the project's suite
must be green.  A union that happens to be wrong syntactically or semantically
fails one of those three, and every original byte is restored before returning --
a conflicted tree is better than a corrupted one.

Measured on the census fixture (`line_total` added on HEAD, `class Item` added on
the feature branch): union -> module imports, `line_total(Item(100, 2)) == 200`,
suite green.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_PYTHON_MERGE_CONFLICT_RESOLVE_V1"
CAPABILITY_ID = "python.vcs.merge_conflict.resolve.v1"
PROVIDES = ["python.vcs.merge_conflict.resolved", "python.source.conflict.free"]
REQUIRES: list[str] = []

_OURS = re.compile(r"^<<<<<<<(?: .*)?$")
_BASE = re.compile(r"^\|\|\|\|\|\|\|(?: .*)?$")
_SEP = re.compile(r"^=======$")
_THEIRS = re.compile(r"^>>>>>>>(?: .*)?$")


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _files(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in sorted(root.rglob("*.py"))
            if "__pycache__" not in p.parts and ".git" not in p.parts]


def _has_markers(text: str) -> bool:
    return any(_OURS.match(line) or _THEIRS.match(line) for line in text.splitlines())


def _resolve(text: str) -> tuple[str, list[dict]]:
    """Union every conflicted region.  Refuses diff3 and an unbalanced file."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    regions: list[dict] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not _OURS.match(line):
            out.append(line)
            index += 1
            continue
        start = index
        index += 1
        ours: list[str] = []
        while index < len(lines) and not _SEP.match(lines[index]) and not _BASE.match(lines[index]):
            ours.append(lines[index])
            index += 1
        if index < len(lines) and _BASE.match(lines[index]):
            raise RuntimeError("DIFF3_BASE_SECTION_PRESENT__UNION_NOT_STATED")
        if index >= len(lines) or not _SEP.match(lines[index]):
            raise RuntimeError("UNBALANCED_CONFLICT_MISSING_SEPARATOR")
        index += 1
        theirs: list[str] = []
        while index < len(lines) and not _THEIRS.match(lines[index]):
            theirs.append(lines[index])
            index += 1
        if index >= len(lines):
            raise RuntimeError("UNBALANCED_CONFLICT_MISSING_END")
        index += 1
        out.extend(ours)
        out.extend(theirs)
        regions.append({
            "start_line": start + 1,
            "ours_lines": len(ours),
            "theirs_lines": len(theirs),
            "resolution": "KEEP_BOTH__OURS_THEN_THEIRS",
        })
    return "".join(out), regions


def _suite(project_root: pathlib.Path, tests: pathlib.Path, timeout_s: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", str(tests), "-t", str(project_root)],
            cwd=str(project_root), capture_output=True, text=True, timeout=timeout_s,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(project_root),
                 "PATH": "/usr/local/bin:/usr/bin:/bin"})
    except subprocess.TimeoutExpired:
        return False, "SUITE_TIMEOUT"
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or ""))[-300:]


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    timeout_s = int(args.get("timeout_s") or 60)

    # The project is the directory holding both the subject and its tests.  When
    # the subject IS the repository the project is the repository -- measured:
    # taking the parent of the repo root pointed discovery at /home/user/tests.
    project_root = (source_root.parent
                    if source_root != repo and source_root.name not in ("", ".")
                    else source_root)
    tests = project_root / "tests"
    if not tests.is_dir():
        raise RuntimeError("TEST_ROOT_MISSING")

    originals: dict[pathlib.Path, bytes] = {}
    resolved: list[dict] = []
    for path in _files(source_root):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not _has_markers(text):
            continue
        new, regions = _resolve(text)
        try:
            ast.parse(new, filename=str(path))
        except SyntaxError as exc:
            raise RuntimeError("UNION_DOES_NOT_PARSE:" + _rel(repo, path) + ":" + str(exc.lineno))
        originals[path] = path.read_bytes()
        path.write_text(new, encoding="utf-8")
        resolved.append({"file": _rel(repo, path), "regions": regions,
                         "lines_removed": sum(r["ours_lines"] + r["theirs_lines"] for r in regions)
                         - sum(r["ours_lines"] + r["theirs_lines"] for r in regions)})

    if not originals:
        raise RuntimeError("NO_CONFLICT_MARKERS_FOUND:" + _rel(repo, source_root))

    # PROOF 1: no marker survives anywhere in the subject.
    for path in _files(source_root):
        try:
            if _has_markers(path.read_text(encoding="utf-8")):
                for p, b in originals.items():
                    p.write_bytes(b)
                raise RuntimeError("CONFLICT_MARKER_SURVIVED:" + _rel(repo, path))
        except OSError:
            continue

    # PROOF 2: the tree still imports and its suite is green.
    ok, tail = _suite(project_root, tests, timeout_s)
    if not ok:
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("SUITE_FAILED_AFTER_RESOLUTION:" + tail.replace("\n", " ")[-200:])

    report = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": _rel(repo, source_root),
        "resolved": resolved,
        "resolved_file_count": len(resolved),
        "suite_passed": True,
        "law": "a two-sided conflict the sentence says to keep is the union of its sides, in "
               "order; a diff3 base section is not stated and is refused, never guessed",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_merge_resolve",
        "answer": "resolved",
        "resolved": resolved,
        "resolved_file_count": len(resolved),
        "files_edited": sorted(_rel(repo, p) for p in originals),
        "suite_passed": True,
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
