"""The propagation loop, driven only by error text plus a static definition lookup.

Two hop rules, both mechanical. No search, no guessing, no model:

  IMPORT hop      ImportError names a symbol and its old module
                  -> rewrite the importers to the symbol's new home.
  DEPENDENCY hop  NameError inside the newly-created module names a symbol that did not
                  travel with the moved code
                  -> import it into that module, after any __future__ imports.

Each hop is determined by the error message. The loop stops when the run reports no
naming failure, and then reports the suite honestly -- including "no tests ran", which is
never a pass.

    python the_zip_propagates_v1.py --tree /tmp/h7 --new-module httpx/_relocated.py
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import subprocess
import sys

PY = sys.executable

IMPORT_FAIL = re.compile(r"cannot import name '([\w_]+)' from '([\w_.]+)'")
NAME_FRAME = re.compile(r"^([\w/]+\.py):\d+: in <module>$", re.M)
NAME_FAIL = re.compile(r"NameError: name '([\w_]+)' is not defined")
SUMMARY = re.compile(r"(\d+) failed, (\d+) passed|(\d+) passed")


def run(tree: pathlib.Path, seconds: int) -> str:
    done = subprocess.run([PY, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
                           "--tb=line", f"--timeout={seconds}"],
                          cwd=tree, capture_output=True, text=True, errors="replace")
    return (done.stdout or "") + (done.stderr or "")


def home_of(tree: pathlib.Path, name: str) -> pathlib.Path | None:
    for py in tree.rglob("*.py"):
        if any(part in py.parts for part in (".git", "build", ".tox")):
            continue
        try:
            tree_ast = ast.parse(py.read_text(errors="replace"))
        except SyntaxError:
            continue
        for node in tree_ast.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
                return py
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return py
    return None


def import_path(tree: pathlib.Path, path: pathlib.Path) -> str:
    """Package-relative import string, e.g. httpx/_relocated.py -> '_relocated'."""
    parts = list(path.relative_to(tree).with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and (tree / parts[0] / "__init__.py").exists() and len(parts) > 1:
        parts = parts[1:]
    return ".".join(parts)


def insert_import(path: pathlib.Path, line: str) -> None:
    lines = path.read_text(errors="replace").splitlines(keepends=True)
    index = 0
    for position, text in enumerate(lines):
        stripped = text.strip()
        if (stripped.startswith("from __future__") or stripped.startswith("#")
                or stripped.startswith('"""') or stripped.startswith("'''")
                or not stripped or stripped.endswith('"""')):
            index = position + 1
        else:
            break
    lines.insert(index, line + "\n")
    path.write_text("".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=pathlib.Path, required=True)
    parser.add_argument("--hops", type=int, default=8)
    parser.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args(argv)
    tree = args.tree

    for hop in range(1, args.hops + 1):
        log = run(tree, args.seconds)
        found = SUMMARY.findall(log)
        print(f"hop {hop}: {found[-1] if found else 'no tests ran'}")

        broken = IMPORT_FAIL.search(log)
        if broken:
            name, origin = broken.group(1), broken.group(2)
            home = home_of(tree, name)
            if home is None:
                print(f"  IMPORT hop: {name!r} is defined nowhere -> cannot repair")
                return 1
            module = import_path(tree, home)
            old = origin.split(".", 1)[1] if "." in origin else origin
            touched = 0
            pattern = re.compile(rf"from \.{re.escape(old)} import \(([^)]*)\)", re.S)
            single = re.compile(rf"from \.{re.escape(old)} import ([^(\n]*\b{name}\b[^\n]*)")
            for path in tree.rglob("*.py"):
                if any(part in path.parts for part in (".git", "build")):
                    continue
                original = path.read_text(errors="replace")
                updated = pattern.sub(
                    lambda m: (f"from .{module} import ({m.group(1)})"
                               if re.search(rf"\b{name}\b", m.group(1)) else m.group(0)),
                    original)
                updated = single.sub(lambda m: f"from .{module} import {m.group(1)}",
                                     updated)
                if updated != original:
                    path.write_text(updated)
                    touched += 1
            print(f"  IMPORT hop: {name} -> .{module}  ({touched} file(s))")
            continue

        undefined = NAME_FAIL.search(log)
        if undefined:
            name = undefined.group(1)
            home = home_of(tree, name)
            if home is None:
                print(f"  DEPENDENCY hop: {name!r} defined nowhere -> cannot repair")
                return 1
            # Destination = the file containing the dangling reference. Take the
            # innermost traceback frame before the NameError, and never the module that
            # already defines the symbol (that produces a self-import loop -- observed).
            frames = re.findall(r"^([\w/]+\.py):(\d+): ", log, re.M)
            target = None
            for path_text, _line in reversed(frames):
                candidate = tree / path_text
                if candidate.exists() and candidate.resolve() != home.resolve():
                    target = candidate
                    break
            if target is None:
                print(f"  DEPENDENCY hop: {name!r} has no reference site outside its own "
                      f"module -> nothing to repair")
                return 2
            module = import_path(tree, home)
            insert_import(target, f"from .{module} import {name}")
            print(f"  DEPENDENCY hop: {name} imported into "
                  f"{target.relative_to(tree)} from .{module}")
            continue

        # A run that collected nothing prints no summary line. Treating that as
        # convergence is the same lie this repo has caught six times; it must be an
        # explicit failure here.
        if not found:
            print("  NO SUMMARY LINE -- tests did not run. Not convergence.")
            return 3
        failed_lines = [line for line in log.splitlines() if line.startswith("FAILED")]
        print(f"  converged: {found[-1]}; FAILED lines: {len(failed_lines)}")
        for line in failed_lines[:5]:
            print("   ", line[:110])
        return 0

    print("  hop budget exhausted")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
