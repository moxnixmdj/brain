"""The acts a tool was never going to provide, done with what is already installed.

Four acts the inventory ranked as missing, each of which turned out to need no new dependency:

  changelog      `git log` is the record; grouping it by conventional-commit type is arithmetic.
  license_scan   the licenses of the distributions a project imports are in their own metadata,
                 readable with `importlib.metadata` -- no scanner required.
  coverage       `coverage.py` is installed; the act is "run the tests under it and report".
  duplication    no installed tool finds clones, so the measurement is an AST window hash: the
                 same normalised statement sequence in two places IS the finding, and it carries
                 both locations, which a percentage cannot.

Every verb is deterministic, reads only what the sentence points at, writes the artifact the door
promised, and refuses when it cannot perform the act.  A verb that cannot run says so with a named
reason -- an empty finding list is never how "I did not check" is reported.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_S = 300
# A clone is a run of statements, not a pair of similar lines.  Six is short enough to catch a
# copy-pasted helper and long enough that two `if` blocks in different modules are not a finding.
CLONE_WINDOW = 6
# The distributions whose metadata is read are the ones the project actually imports: a license
# report about everything installed in the environment answers a question nobody asked.
_STDLIB = set(sys.stdlib_module_names)


class QualityError(RuntimeError):
    """A refusal the caller can act on: the request did not meet the verb's contract."""


def _fail(reason: str) -> None:
    raise QualityError(reason)


# --------------------------------------------------------------------------- paths and artifacts


def _inside(root: Path, path: str) -> Path | None:
    """The entry a stated path names, however the front layer stated it."""
    stated = Path(path)
    if stated.is_absolute() and stated.exists():
        return stated
    if not stated.is_absolute():
        absolute_like = Path("/") / stated
        if absolute_like.exists():
            return absolute_like
        if (root / stated).exists():
            return root / stated
    parts = stated.parts[1:] if stated.is_absolute() else stated.parts
    for start in range(1, len(parts)):
        candidate = Path(*parts[start:])
        if (root / candidate).exists():
            return root / candidate
    return None


def _destination(root: Path, output_path: str) -> Path:
    destination = Path(output_path)
    if destination.is_absolute():
        return destination
    absolute_like = Path("/") / output_path
    joined = root / destination
    if not joined.parent.exists() and absolute_like.parent.exists():
        return absolute_like
    return joined


def _canonical(payload: dict) -> str:
    body = dict(payload)
    body["artifact_sha256"] = ""
    return json.dumps(body, indent=1, sort_keys=True) + "\n"


def verify_artifact(output_path: Path) -> str:
    """Re-derive a written artifact's digest from its own bytes. Raises on mismatch."""
    loaded = json.loads(Path(output_path).read_text(encoding="utf-8"))
    recorded = str(loaded.get("artifact_sha256") or "")
    derived = hashlib.sha256(_canonical(loaded).encode("utf-8")).hexdigest()
    if not recorded or recorded != derived:
        _fail("ARTIFACT_DIGEST_MISMATCH:" + str(recorded)[:16])
    return derived


def _write(output_path: Path, payload: dict) -> dict:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload["artifact_path"] = str(output_path)
    payload["artifact_sha256"] = ""
    payload["artifact_sha256"] = hashlib.sha256(
        _canonical(payload).encode("utf-8")
    ).hexdigest()
    output_path.write_text(
        json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    verify_artifact(output_path)
    return payload


def _base(capability_id: str, act: str, target: Path) -> dict[str, Any]:
    return {
        "adapter": "quality_v1",
        "capability_id": capability_id,
        "act": act,
        "target": str(target),
        "gate": "PASS",
        "model_dependency_count": 0,
    }


def _git(repo: Path, argv: list[str], timeout_s: int) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", *argv], cwd=str(repo), capture_output=True, text=True, timeout=timeout_s
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        _fail(
            "GIT_FAILED:"
            + " ".join(argv[:2])
            + ":"
            + (detail[-1] if detail else "")[:200]
        )
    return proc


# --------------------------------------------------------------------------- changelog

_COMMIT_TYPES = {
    "feat": "Features",
    "feature": "Features",
    "fix": "Fixes",
    "bugfix": "Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Documentation",
    "test": "Tests",
    "tests": "Tests",
    "build": "Build",
    "ci": "Continuous integration",
    "chore": "Chores",
    "style": "Style",
    "revert": "Reverts",
}
_CONVENTIONAL = re.compile(
    r"^\s*(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]*)\))?!?:\s*(?P<subject>.+)$"
)


def _changelog(args, target: Path, cap: str) -> dict:
    """A changelog that is READ from history, not invented.

    The capability writes what the repository's own commits say, grouped by their conventional
    type, and keeps the ones that do not follow the convention in an `Other` section rather than
    dropping them -- a changelog that silently omits half the history is a wrong report.
    """
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    limit = int(args.get("limit") or 400)
    revision = str(args.get("ref") or "").strip()
    if not (target / ".git").exists():
        _fail("NOT_A_REPOSITORY:" + str(target))
    argv = [
        "log",
        "--no-merges",
        "--pretty=format:%H%x1f%an%x1f%aI%x1f%s",
        "-n",
        str(limit),
    ]
    if revision:
        argv.append(revision)
    proc = _git(target, argv, timeout_s)
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 4:
            continue
        sha, author, when, subject = parts
        match = _CONVENTIONAL.match(subject)
        if match:
            kind = match.group("type").lower()
            section = _COMMIT_TYPES.get(kind, "Other")
            entry = match.group("subject").strip()
            scope = (match.group("scope") or "").strip()
        else:
            section, entry, scope = "Other", subject.strip(), ""
        commits.append(
            {
                "sha": sha,
                "short_sha": sha[:7],
                "author": author,
                "date": when,
                "subject": subject,
                "section": section,
                "entry": entry,
                "scope": scope,
            }
        )
    sections: dict[str, list[dict]] = {}
    for commit in commits:
        sections.setdefault(commit["section"], []).append(commit)
    lines = ["# Changelog", ""]
    for name in sorted(sections):
        lines.append("## " + name)
        for commit in sections[name]:
            scope = "**%s**: " % commit["scope"] if commit["scope"] else ""
            lines.append("- %s%s (%s)" % (scope, commit["entry"], commit["short_sha"]))
        lines.append("")
    return {
        **_base(cap, "changelog", target),
        "revision": revision or "HEAD",
        "commit_count": len(commits),
        "sections": {k: len(v) for k, v in sections.items()},
        "commits": commits,
        "changelog_markdown": "\n".join(lines).rstrip() + "\n",
        "empty": not commits,
    }


# --------------------------------------------------------------------------- licenses


def _imported_distributions(files: list[Path]) -> dict[str, set[str]]:
    """Top-level module -> the files that import it.  Read from the AST, not from grep."""
    wanted: dict[str, set[str]] = {}
    for path in files:
        try:
            tree = ast.parse(
                path.read_bytes().decode("utf-8", "replace"), filename=str(path)
            )
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name and name not in _STDLIB:
                    wanted.setdefault(name, set()).add(str(path))
    return wanted


def _license_scan(args, target: Path, cap: str) -> dict:
    """Licenses of the distributions this project actually imports.

    `importlib.metadata` already carries every installed distribution's declared license, so the
    act needs no scanner and no network.  What it must not do is report "no license" for a
    distribution that simply does not declare one in metadata: that is `NO_DECLARED_LICENSE`, a
    distinct fact from a permissive license, and the two are counted separately.
    """
    from importlib import metadata as md

    files = (
        [target]
        if target.is_file()
        else sorted(
            p
            for p in target.rglob("*.py")
            if ".venv" not in p.parts and "/.git/" not in str(p)
        )
    )
    if not files:
        _fail("NO_PYTHON_SOURCE_FOUND:" + str(target))
    imported = _imported_distributions(files)
    # A module name is not a distribution name (`yaml` lives in `PyYAML`), so the mapping is read
    # from the distributions' own top_level files rather than guessed from the import.
    by_module: dict[str, str] = {}
    for dist in md.distributions():
        name = dist.metadata["Name"] if dist.metadata else None
        if not name:
            continue
        top = dist.read_text("top_level.txt") or ""
        for module in [line.strip() for line in top.splitlines() if line.strip()]:
            by_module.setdefault(module, name)
        by_module.setdefault(re.sub(r"[-_.]+", "_", name).lower(), name)
    rows = []
    for module in sorted(imported):
        dist_name = by_module.get(module)
        if not dist_name:
            rows.append(
                {
                    "module": module,
                    "distribution": "",
                    "version": "",
                    "license": "",
                    "status": "NOT_INSTALLED_OR_UNKNOWN_DISTRIBUTION",
                    "imported_by": sorted(imported[module])[:5],
                }
            )
            continue
        try:
            info = md.metadata(dist_name)
            license_text = (
                info.get("License-Expression") or info.get("License") or ""
            ).strip()
            classifiers = [
                c
                for c in (info.get_all("Classifier") or [])
                if c.startswith("License ::")
            ]
            if not license_text and classifiers:
                license_text = classifiers[-1].split("::")[-1].strip()
            if not license_text:
                # `License ::` may be absent while the file is present; the file is the claim.
                license_text = ""
            status = "DECLARED" if license_text else "NO_DECLARED_LICENSE"
            rows.append(
                {
                    "module": module,
                    "distribution": dist_name,
                    "version": md.version(dist_name),
                    "license": license_text,
                    "status": status,
                    "imported_by": sorted(imported[module])[:5],
                }
            )
        except Exception as exc:  # noqa: BLE001 - unreadable metadata is a finding, not a crash
            rows.append(
                {
                    "module": module,
                    "distribution": dist_name,
                    "version": "",
                    "license": "",
                    "status": "METADATA_UNREADABLE:" + type(exc).__name__,
                    "imported_by": sorted(imported[module])[:5],
                }
            )
    declared = [r for r in rows if r["status"] == "DECLARED"]
    counts: dict[str, int] = {}
    for row in declared:
        counts[row["license"]] = counts.get(row["license"], 0) + 1
    return {
        **_base(cap, "license_scan", target),
        "dependency_count": len(rows),
        "declared_count": len(declared),
        "no_declared_license_count": len(
            [r for r in rows if r["status"] == "NO_DECLARED_LICENSE"]
        ),
        "unknown_distribution_count": len(
            [r for r in rows if r["status"] == "NOT_INSTALLED_OR_UNKNOWN_DISTRIBUTION"]
        ),
        "licenses": rows,
        "license_counts": counts,
        "clean": all(r["status"] == "DECLARED" for r in rows) if rows else True,
    }


# --------------------------------------------------------------------------- coverage


def _coverage(args, target: Path, cap: str) -> dict:
    """Run the stated tests under `coverage.py` and report what they actually executed.

    Coverage is not a number about the source; it is a fact about a RUN.  The verb therefore runs
    the suite (that is the act), refuses when there is no suite to run, and reports both the total
    and the per-file detail, because "80%" over a tree that was half unimportable is a lie the
    total cannot show.
    """
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    # Run IN the project the tests belong to.  Measured: pytest started from the repository root
    # on an absolute target could not import the package it was asked to test ("1 error in 0.18s",
    # reported as TESTS_COULD_NOT_RUN with a reason that named nothing), because a package's own
    # root is what makes `import pkg.calc` resolve.
    root = target if target.is_dir() else target.parent
    with tempfile.TemporaryDirectory() as tmp:
        data_file = str(Path(tmp) / ".coverage")
        env = dict(os.environ)
        env["COVERAGE_FILE"] = data_file
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--branch",
                "--source",
                str(target),
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                str(target),
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        if "No module named coverage" in (run.stderr or ""):
            _fail("TOOL_NOT_INSTALLED:coverage")
        if run.returncode not in (0, 1, 5):
            # Name the failure, not the summary line.  "1 error in 0.18s" tells a caller nothing;
            # the error line above it is the diagnosis.
            detail = (
                ((run.stdout or "") + "\n" + (run.stderr or "")).strip().splitlines()
            )
            interesting = [
                line
                for line in detail
                if line.strip()
                and ("Error" in line or "error" in line or "E   " in line)
            ]
            _fail(
                "TESTS_COULD_NOT_RUN:"
                + (" | ".join((interesting or detail)[-3:]))[:300]
            )
        if run.returncode == 5:
            _fail("NO_TESTS_FOUND:" + str(target))
        report_path = Path(tmp) / "coverage.json"
        rep = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "json",
                "--quiet",
                "-o",
                str(report_path),
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        if not report_path.is_file():
            _fail("TOOL_FAILED:coverage:" + ((rep.stderr or "").strip()[:200]))
        report = json.loads(report_path.read_text(encoding="utf-8"))
    files = []
    for name, body in (report.get("files") or {}).items():
        summary = body.get("summary") or {}
        files.append(
            {
                "path": name,
                "percent_covered": round(
                    float(summary.get("percent_covered") or 0.0), 2
                ),
                "num_statements": int(summary.get("num_statements") or 0),
                "missing_lines": len(body.get("missing_lines") or []),
            }
        )
    files.sort(key=lambda f: f["percent_covered"])
    totals = report.get("totals") or {}
    return {
        **_base(cap, "coverage", target),
        "tests_passed": run.returncode == 0,
        "test_exit": run.returncode,
        "percent_covered": round(float(totals.get("percent_covered") or 0.0), 2),
        "num_statements": int(totals.get("num_statements") or 0),
        "missing_lines": int(totals.get("missing_lines") or 0),
        "file_count": len(files),
        "files": files,
        "least_covered": files[:10],
        "test_output_tail": (run.stdout or "").strip().splitlines()[-5:],
    }


# --------------------------------------------------------------------------- duplication


def _normalise(node: ast.AST) -> str:
    """The shape of a statement with its names and literals erased.

    Two blocks that differ only in the identifiers they use are the same copied code; that is the
    whole reason a clone detector normalises, and it is why the finding survives a rename that a
    line-based tool would report as two separate fragments.
    """
    if isinstance(node, ast.Name):
        return "NAME"
    if isinstance(node, ast.Attribute):
        return _normalise(node.value) + ".ATTR"
    if isinstance(node, ast.Constant):
        return "CONST"
    if isinstance(node, ast.arg):
        return "ARG"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return type(node).__name__
    parts = [_normalise(child) for child in ast.iter_child_nodes(node)]
    return type(node).__name__ + "(" + ",".join(parts) + ")"


def _statement_window(body: list[ast.stmt]) -> list[list[str]]:
    joined = [_normalise(stmt) for stmt in body]
    size = min(CLONE_WINDOW, len(joined))
    if size < 2:
        return []
    return [joined[i : i + size] for i in range(len(joined) - size + 1)]


def _duplication(args, target: Path, cap: str) -> dict:
    """Clone detection as an AST fact: the same normalised statement run in two functions."""
    files = (
        [target]
        if target.is_file()
        else sorted(
            p
            for p in target.rglob("*.py")
            if ".venv" not in p.parts and "/.git/" not in str(p)
        )
    )
    if not files:
        _fail("NO_PYTHON_SOURCE_FOUND:" + str(target))
    seen: dict[str, list[dict]] = {}
    parsed = 0
    for path in files:
        try:
            tree = ast.parse(
                path.read_bytes().decode("utf-8", "replace"), filename=str(path)
            )
        except (OSError, SyntaxError):
            continue
        parsed += 1
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list) or not body or not isinstance(node, ast.stmt):
                continue
            for window in _statement_window(body):
                key = hashlib.sha256(("\n".join(window)).encode()).hexdigest()[:16]
                seen.setdefault(key, []).append(
                    {
                        "path": str(path),
                        "line": int(getattr(node, "lineno", 0) or 0),
                        "statements": len(window),
                        "kind": type(node).__name__,
                    }
                )
    groups = []
    for key, places in seen.items():
        # Two windows starting at the SAME statement of the same node are one block seen twice,
        # not a clone: only distinct places count.
        distinct = {(p["path"], p["line"]) for p in places}
        if len(distinct) > 1:
            groups.append(
                {
                    "fingerprint": key,
                    "statement_count": places[0]["statements"],
                    "occurrences": len(distinct),
                    "places": sorted(places, key=lambda p: (p["path"], p["line"]))[:20],
                }
            )
    groups.sort(key=lambda c: (-c["statement_count"], -c["occurrences"]))
    # A run of N identical statements matches at every offset it starts at, so the raw groups
    # OVERLAP: one copied 20-statement block reported as fifteen clones.  The report is of the
    # blocks, so a group whose every place falls inside a block already reported is dropped.  The
    # measured cost of not doing this: 5331 "clone groups" over one package, which is a number
    # nobody can act on.
    covered: dict[str, list[tuple[int, int]]] = {}
    clones = []
    for group in groups:
        inside = True
        for place in group["places"]:
            span = (place["line"], place["line"] + group["statement_count"])
            if not any(
                start <= span[0] and span[1] <= end
                for start, end in covered.get(place["path"], [])
            ):
                inside = False
                break
        if inside:
            continue
        clones.append(group)
        for place in group["places"]:
            covered.setdefault(place["path"], []).append(
                (place["line"], place["line"] + group["statement_count"])
            )
    duplicated_statements = sum(
        c["statement_count"] * (c["occurrences"] - 1) for c in clones
    )
    return {
        **_base(cap, "duplication", target),
        "window": CLONE_WINDOW,
        "files_parsed": parsed,
        "clone_group_count": len(clones),
        "clones": clones[:200],
        "duplicated_statement_estimate": duplicated_statements,
        "clean": not clones,
    }


# The acquisitions worth reporting: a call that TAKES an operating-system resource and
# whose release is a separate, forgettable step.  Each entry is (module, name, release
# method).  A resource acquired through `with` needs no release and is never reported.
_RESOURCE_ACQUISITIONS = {
    ("builtins", "open"): "close",
    ("io", "open"): "close",
    ("io", "open_code"): "close",
    ("socket", "socket"): "close",
    ("socket", "create_connection"): "close",
    ("sqlite3", "connect"): "close",
    ("subprocess", "Popen"): "terminate",
    ("os", "popen"): "close",
    ("tempfile", "NamedTemporaryFile"): "close",
    ("tempfile", "TemporaryFile"): "close",
    ("tarfile", "open"): "close",
    ("zipfile", "ZipFile"): "close",
    ("urllib.request", "urlopen"): "close",
    ("mmap", "mmap"): "close",
}


def _acquisition_kind(node: ast.AST):
    """(kind, release) when this Call acquires a resource, else None.

    `open(...)` is a bare name in the builtins; `sqlite3.connect(...)` is an attribute
    whose receiver names the module.  A call through some other receiver is NOT assumed
    to be one of these: guessing here would report a leak in every wrapper that has a
    `close()` method of its own.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name):
        key = ("builtins", func.id)
        if key in _RESOURCE_ACQUISITIONS:
            return func.id + "()", _RESOURCE_ACQUISITIONS[key]
        return None
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        key = (func.value.id, func.attr)
        if key in _RESOURCE_ACQUISITIONS:
            return func.value.id + "." + func.attr + "()", _RESOURCE_ACQUISITIONS[key]
    return None


def _scope_bodies(tree):
    """(name, node, body) for the module and every function, WITHOUT nested scopes.

    A resource acquired inside `inner()` and closed in `outer()` is not closed; the
    scopes are reported separately, which is the truth a reader can act on.
    """
    yield "<module>", tree, tree.body

    def walk(parent_name, nodes):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = parent_name + "." + node.name if parent_name != "<module>" else node.name
                yield qual, node, node.body
                yield from walk(qual, node.body)

    yield from walk("<module>", tree.body)


def _scope_nodes(body):
    """Every node of ONE scope, never descending into a nested def, class or lambda."""
    stack = list(body)
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _resource_leak(args, target: Path, cap: str) -> dict:
    """Unreleased OS resources: every acquisition whose release is provable-missing.

    The law is deliberately conservative in one direction and strict in the other:
    a `with` or a matching `.close()`/`.terminate()` anywhere in the same scope counts
    as released (this is a static reading, not a path-sensitive one), and RETURNING the
    handle is ownership transfer, not a leak.  Anything else is reported with the line,
    the variable and the release call that is missing -- a finding a reader can check.
    """
    files = (
        [target]
        if target.is_file()
        else sorted(
            p
            for p in target.rglob("*.py")
            if ".venv" not in p.parts and "/.git/" not in str(p)
        )
    )
    if not files:
        _fail("NO_PYTHON_SOURCE_FOUND:" + str(target))
    findings = []
    scanned = 0
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        scanned += 1
        rel = path.name if target.is_file() else str(path.relative_to(target))
        for scope_name, _node, body in _scope_bodies(tree):
            # handles bound in this scope, and what release calls exist on those names
            nodes = list(_scope_nodes(body))
            released = set()
            for sub in nodes:
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                        and isinstance(sub.func.value, ast.Name):
                    if sub.func.attr in {"close", "terminate", "kill", "release", "__exit__"}:
                        released.add(sub.func.value.id)
            # OWNERSHIP TRANSFER IS `return handle`, NOT `return handle.read()`.
            # Measured on the first build: reading the whole returned expression made every
            # `return handle.read()` count as handing the handle over, so the most common
            # leak in Python -- open, read, never close -- was the one shape it missed.
            transferred = set()
            for sub in nodes:
                if not isinstance(sub, ast.Return) or sub.value is None:
                    continue
                returned = sub.value.elts if isinstance(sub.value, (ast.Tuple, ast.List)) \
                    else [sub.value]
                for inner in returned:
                    if isinstance(inner, ast.Name):
                        transferred.add(inner.id)
            in_with = set()
            for sub in nodes:
                if isinstance(sub, (ast.With, ast.AsyncWith)):
                    for item in sub.items:
                        for inner in ast.walk(item.context_expr):
                            if isinstance(inner, ast.Name):
                                in_with.add(inner.id)
            for sub in nodes:
                target_names = []
                value = None
                if isinstance(sub, ast.Assign) and len(sub.targets) == 1 \
                        and isinstance(sub.targets[0], ast.Name):
                    target_names = [sub.targets[0].id]
                    value = sub.value
                elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                    target_names = [sub.target.id]
                    value = sub.value
                elif isinstance(sub, ast.Expr):
                    value = sub.value
                kind = _acquisition_kind(value) if value is not None else None
                if not kind:
                    continue
                kind_name, release = kind
                if not target_names:
                    findings.append({
                        "file": rel, "line": sub.lineno, "scope": scope_name,
                        "kind": kind_name, "variable": None,
                        "reason": "resource acquired and neither bound nor released",
                    })
                    continue
                name = target_names[0]
                if name in released or name in transferred or name in in_with:
                    continue
                findings.append({
                    "file": rel, "line": sub.lineno, "scope": scope_name,
                    "kind": kind_name, "variable": name,
                    "reason": "no " + release + "() on this variable in the same scope",
                })
    payload = _base(cap, "resource_leak", target)
    payload.update({
        "files_scanned": scanned,
        "leaks_found": len(findings),
        "leaks": findings,
        "detection_scope": "same-scope static reading: a with-statement, a close/terminate "
                           "call on the bound name, or returning the handle clears a "
                           "finding; path-sensitivity is not claimed",
        "complete": True,
    })
    return payload


_HANDLERS = {
    "changelog": _changelog,
    "license_scan": _license_scan,
    "coverage": _coverage,
    "duplication": _duplication,
    "resource_leak": _resource_leak,
}


def run(args: dict, root: Path) -> dict:
    """The one entrypoint every one of these capabilities uses."""
    args = dict(args or {})
    root = Path(root)
    verb = str(args.get("act_verb") or "").strip()
    capability_id = str(args.get("capability_id") or "")
    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        _fail("OUTPUT_PATH_NOT_STATED")
    destination = _destination(root, output_path)
    try:
        if verb not in _HANDLERS:
            _fail("ACT_NOT_SUPPORTED:" + (verb or "<none>"))
        stated = str(args.get("source_root") or args.get("path") or "").strip()
        if not stated:
            _fail("PATH_NOT_STATED")
        target = _inside(root, stated)
        if target is None:
            _fail("PATH_NOT_IN_THE_REPOSITORY:" + stated)
        payload = _HANDLERS[verb](args, target, capability_id)
    except QualityError as exc:
        _write(
            destination,
            {
                "adapter": "quality_v1",
                "capability_id": capability_id,
                "act": verb,
                "gate": "FAIL",
                "reason": str(exc),
            },
        )
        raise
    return _write(destination, payload)
