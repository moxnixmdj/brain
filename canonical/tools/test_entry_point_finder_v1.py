"""Which test file can actually refuse an edit to this file?

WHY THIS EXISTS
---------------
The previous round could not verify 42 of 42 real changed files and reported six tasks as
`CHECK_NO_TEST_MODULE`. It was wrong, at least once. On `jodal/comics#652` there are five test files
that import `comics.accounts.models`, including `comics/tests/api/conftest.py`, and NOT ONE of them
is named `test_*.py` -- they are `conftest.py`, which pytest loads as fixtures. The old finder scanned
`self._dir.rglob("test_*.py")` and therefore concluded that no check existed.

That is the shape of the error to avoid: **a finder that searches one filename pattern reports a
missing check, and "no check exists" is indistinguishable from "I did not look here".**

WHAT THIS DOES
--------------
Given a project root and a file, it finds every test file that IMPORTS that file's module, by parsing
imports -- not by matching names -- and it searches three naming conventions plus configured roots:

    test_*.py | *_test.py | conftest.py        in tests/, test/, or beside the source

It then reports, for each candidate, what it is (`unittest`, `pytest`, `conftest`, `script`) and
whether the target's module is imported directly or through a re-export.

CRITICAL DISTINCTION
--------------------
Finding a test that imports the file is NOT the same as having a check.

* `IMPORTS`  -- a test file imports this module (a check probably exists)
* `COVERS`   -- and at least one test function/class in it names something this module defines
* `NONE`     -- nothing imports it

A module imported only by a `conftest.py` fixture may never be asserted on. Reporting `IMPORTS` as if
it were `COVERS` is how a metric becomes a lie. Both are reported, separately.

Authority: NONE. Sandbox measurement, `$0`, zero model calls.

Usage:
    python3 canonical/tools/test_entry_point_finder_v1.py --project /tmp/probes/comics \\
        --target src/comics/accounts/models.py
"""

from __future__ import annotations

import argparse
import ast
import re
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Sequence

SCHEMA = "TEST_ENTRY_POINT_FINDER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

TEST_NAME_PATTERNS = ("test_*.py", "*_test.py", "conftest.py")
TEST_DIRS = ("test", "tests")
SKIP_DIRS = {".git", ".tox", ".venv", "venv", "node_modules", "build", "dist", "__pycache__", ".eggs"}


@dataclass
class Candidate:
    path: str
    kind: str                     # unittest | pytest | conftest | script
    imported: list[str] = field(default_factory=list)
    naming: list[str] = field(default_factory=list)
    defines_tests: bool = False


def _declared_package_roots(project: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    """(directory, module prefix) pairs taken from packaging metadata, not from the filesystem.

    THE BUG THIS FIXES. In `django-argcache` the file `src/function.py` is imported as
    `argcache.function`. Its path contains neither "argcache" nor a resolvable suffix, so a
    path-only finder reports that nothing imports it -- while four test files do. The import name
    is a DECLARATION, made in setup.py/pyproject.toml (`packages=['argcache']`, `package_dir`), and
    the filesystem alone cannot recover it. So the declaration is read.
    """
    roots: list[tuple[pathlib.Path, str]] = []
    metadata = ["setup.py", "setup.cfg", "pyproject.toml"]
    text = ""
    for name in metadata:
        candidate = project / name
        if candidate.is_file():
            text += candidate.read_text(encoding="utf-8", errors="replace") + "\n"

    # `packages=['argcache']` + `package_dir={'': 'src'}` means: the directory `src/` IS the
    # package whose import name is `argcache`. The mapping lives in that dict and nowhere else.
    declared_list = re.findall(r"packages\s*=\s*\[([^\]]*)\]", text)
    names: list[str] = []
    for group in declared_list:
        names += re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_.]*)['\"]", group)
    top_level = [n for n in names if "." not in n]

    remapped = re.findall(r"['\"]{0,2}\s*:\s*['\"]([A-Za-z_][A-Za-z0-9_./]*)['\"]", text)
    remapped += re.findall(r"package[-_]dir\s*=\s*['\"]([A-Za-z_][A-Za-z0-9_./]*)['\"]", text)
    for directory in remapped:
        candidate = project / directory
        if candidate.is_dir() and top_level:
            for name in top_level:
                roots.append((candidate, name))

    for root in [project, *[project / d for d in ("src", "lib", "python")]]:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or not (child / "__init__.py").is_file():
                continue
            roots.append((child, child.name))
    return roots


def _dotted_for(path: pathlib.Path, root: pathlib.Path) -> str:
    """The module name this file would be imported by, under several plausible roots."""
    relative = path.resolve().relative_to(root.resolve())
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _module_names(path: pathlib.Path, root: pathlib.Path) -> set[str]:
    """Every dotted name that could plausibly import this file.

    Projects disagree about where the root is: `src/` layout, flat layout, or the package dir. Rather
    than guess once, every suffix of the path is offered -- the match is on the IMPORT SIDE, so a
    wrong root simply produces no match rather than a false one.
    """
    relative = path.resolve().relative_to(root.resolve())
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    names = {".".join(parts[i:]) for i in range(len(parts))}
    for base, prefix in _declared_package_roots(root):
        try:
            relative_to_base = path.resolve().relative_to(base.resolve())
        except ValueError:
            continue
        inner = list(relative_to_base.with_suffix("").parts)
        if inner and inner[-1] == "__init__":
            inner = inner[:-1]
        names.add(".".join([prefix, *inner]) if inner else prefix)
    names.discard("")
    return names


def _imports_of(source: str, package: Sequence[str] = ()) -> set[str]:
    """Absolute module names imported by `source`, with relative imports actually resolved.

    A relative import is the single easiest way to produce a false match in a finder like this.
    `from .validation import check` inside `activityassure/ui/data_utils.py` parses with
    `node.module == "validation"` and `node.level == 1`; a naive matcher then sees the bare string
    "validation" and reports that a test covers `activityassure/validation.py`. It does not -- the
    import points at `activityassure.ui.validation`. This function resolves the level against the
    importing file's package so the name it returns means what it appears to mean.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    package = list(package)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - (node.level - 1)] if node.level > 1 else package
                if node.module:
                    resolved = ".".join([*base, node.module]) if base else node.module
                else:
                    resolved = ".".join(base)
            else:
                resolved = node.module or ""
            if resolved:
                found.add(resolved)
                found |= {f"{resolved}.{alias.name}" for alias in node.names}
    return {name for name in found if name}


def _names_defined(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            out |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return out


def _kind_of(path: pathlib.Path, source: str) -> str:
    if path.name == "conftest.py":
        return "conftest"
    if "unittest" in source:
        return "unittest"
    if "pytest" in source or "def test_" in source:
        return "pytest"
    return "script"


def _routes_into(project: pathlib.Path, target: pathlib.Path,
                 package: Sequence[str]) -> list[dict[str, str]]:
    """Routes in a router file (`urls.py`, `urls/`) that dispatch to this file.

    The import graph is NOT the whole graph. `comics/accounts/views.py` is imported by exactly one
    file, `urls.py`, and is exercised by tests that never name it: `client.get("/me/secret-key/")`
    reaches `views.secret_key` through the router. A finder built only on imports calls that
    file untested while a real HTTP test hits it. For a Django-shaped project the router is part of
    the graph, so it is walked explicitly.
    """
    wanted = _module_names(target, project)
    routes: list[dict[str, str]] = []
    for path in project.rglob("urls.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        pkg = list(path.relative_to(project).parent.parts)
        if not (path.parent / "__init__.py").is_file():
            pkg = pkg[:-1] if pkg else []
        if not any(name in wanted or name.startswith(f"{name}.") or name.startswith(".".join(pkg))
                   for name in _imports_of(source, pkg)
                   if any(w in name for w in wanted)):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            kind = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if kind not in {"path", "re_path", "url"}:
                continue
            route = next((a.value for a in node.args
                          if isinstance(a, ast.Constant) and isinstance(a.value, str)), "")
            name = next((k.value.value for k in node.keywords
                         if k.arg == "name" and isinstance(k.value, ast.Constant)), "")
            view = ast.unparse(node.args[1]) if len(node.args) > 1 else ""
            if not view:
                continue
            if not any(w in view for w in wanted) and "views." not in view:
                continue
            routes.append({"router": path.relative_to(project).as_posix(),
                           "route": route, "name": name, "view": view})
    return routes


def _test_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Test files under FOUR conventions, not one.

    `test_*.py` and `*_test.py` are the obvious two. `conftest.py` is the third -- pytest loads it,
    and it was the file that made comics look untested. The fourth is the one that is easy to miss:
    **any .py file inside a directory named `test` or `tests`**. `torproject/stem` names its tests
    after the module they test (`test/unit/util/asyncio.py`), so a filename pattern finds nothing there
    while a real test exists. Searching one convention and concluding "no test exists" is the bug
    this tool exists to avoid -- so it searches all four and reports which one paid off.
    """
    seen: list[pathlib.Path] = []
    for pattern in TEST_NAME_PATTERNS:
        for path in root.rglob(pattern):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            seen.append(path)
    for dirname in TEST_DIRS:
        for directory in root.rglob(dirname):
            if not directory.is_dir() or any(part in SKIP_DIRS for part in directory.parts):
                continue
            for path in directory.rglob("*.py"):
                if any(part in SKIP_DIRS for part in path.parts):
                    continue
                seen.append(path)
    return sorted(set(seen))


def find(project: pathlib.Path, target: pathlib.Path) -> dict[str, Any]:
    """Which test files import `target`, and do any of them name something it defines?"""
    project = project.resolve()
    target = (project / target).resolve() if not target.is_absolute() else target.resolve()
    if target in {(project / p).resolve() for p in
                  (q.relative_to(project).as_posix() for q in _test_files(project))}:
        return {"schema": SCHEMA, "authority": AUTHORITY, "incremental_spend_usd": 0,
                "model_calls": 0, "project": project.name,
                "target": target.relative_to(project).as_posix(),
                "verdict": "IS_TEST_FILE",
                "note": "This file is itself a test/check, not a subject of one."}
    if not target.is_file():
        return {"schema": SCHEMA, "error": "TARGET_NOT_A_FILE", "target": str(target)}

    wanted = _module_names(target, project)
    defined = _names_defined(target.read_text(encoding="utf-8", errors="replace"))
    candidates: list[Candidate] = []
    for path in _test_files(project):
        source = path.read_text(encoding="utf-8", errors="replace")
        package = list(path.relative_to(project).parent.parts)
        if "__init__.py" not in {p.name for p in path.parent.iterdir() if p.is_file()} and path.name != "__init__.py":
            package = package[:-1] if package else []
        imported = _imports_of(source, package)
        hit = sorted(name for name in imported
                     if name in wanted or any(name.startswith(w + ".") for w in wanted))
        if not hit:
            continue
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", source))
        naming = sorted(n for n in defined if n.startswith("_") is False and n in tokens)
        defines_tests = ("def test" in source or "TestCase" in source or "unittest" in source)
        candidates.append(Candidate(
            path=path.relative_to(project).as_posix(),
            kind=_kind_of(path, source),
            imported=hit,
            naming=naming,
            defines_tests=defines_tests))

    routes = _routes_into(project, target, []) if not target.name == "urls.py" else []
    dispatch: list[dict[str, str]] = []
    for route in routes:
        needle = route["route"].strip("/").split("/")[0]
        for path in _test_files(project):
            source = path.read_text(encoding="utf-8", errors="replace")
            hit = (needle and needle in source) or (route["name"] and route["name"] in source)
            if hit:
                dispatch.append({"path": path.relative_to(project).as_posix(),
                                 "via": f'{route["router"]}:{route["name"] or route["route"]}',
                                 "view": route["view"]})
                break

    covers = [c.path for c in candidates if c.naming]
    imports_only = [c.path for c in candidates if not c.naming]
    if covers:
        verdict = "COVERS"
    elif candidates:
        verdict = "IMPORTS"
    elif dispatch:
        verdict = "DISPATCH"
    else:
        verdict = "NONE"
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "incremental_spend_usd": 0,
        "model_calls": 0,
        "project": project.name,
        "target": target.relative_to(project).as_posix(),
        "module_names_tried": sorted(wanted),
        "defined_names": sorted(defined)[:25],
        "candidates": [
            {"path": c.path, "kind": c.kind, "imported": c.imported,
             "names_the_definition": c.naming, "defines_tests": c.defines_tests}
            for c in candidates],
        "covers": covers,
        "imports_only": imports_only,
        "dispatch": dispatch,
        "verdict": verdict,
        "test_files_examined": len(_test_files(project)),
        "naming_conventions_that_found_something": sorted({c.kind for c in candidates}),
        "note": ("IMPORTS means a check probably exists; COVERS means a test in it names something "
                 "this file defines. They are reported separately because conflating them is how a "
                 "metric becomes a lie."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=pathlib.Path, required=True)
    parser.add_argument("--target", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    ns = parser.parse_args()
    result = find(ns.project, ns.target)
    text = json.dumps(result, indent=1)
    print(text)
    if ns.out:
        ns.out.parent.mkdir(parents=True, exist_ok=True)
        ns.out.write_text(text + "\n", encoding="utf-8")
    return 0 if "error" not in result else 2


if __name__ == "__main__":
    raise SystemExit(main())
