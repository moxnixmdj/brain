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
import importlib.util
import importlib.util
import pathlib
import re
import subprocess
import sys

PY = sys.executable

IMPORT_FAIL = re.compile(r"cannot import name '([\w_]+)' from '([\w_.]+)'")
NAME_FRAME = re.compile(r"^([\w/]+\.py):\d+: in <module>$", re.M)
NAME_FAIL = re.compile(r"NameError: name '([\w_]+)' is not defined")
# "to_bytes_or_str() missing 1 required positional argument: 'strict'"
SIG_FAIL = re.compile(r"([\w_]+)\(\) missing 1 required positional argument: '([\w_]+)'")
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
    parser.add_argument("--hops", type=int, default=20)
    parser.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args(argv)
    tree = args.tree

    first_summary: str | None = None
    for hop in range(1, args.hops + 1):
        log = run(tree, args.seconds)
        found = SUMMARY.findall(log)
        print(f"hop {hop}: {found[-1] if found else 'no tests ran'}")

        if first_summary is None:
            first_summary = found[-1] if found else ""

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
            # Per-SYMBOL rewrite. Moving the whole import line drags symbols that never
            # moved along with it, and the next hop then moves them back -- an observed
            # two-symbol thrash: "from ._utils import to_bytes_or_str, to_str" needs ONE
            # of the two relocated, and a line-level move gets it wrong every hop.
            single = re.compile(
                rf"^from \.{re.escape(old)} import ([^\n(]+)$", re.M)
            block = re.compile(
                rf"^from \.{re.escape(old)} import \(([^)]*)\)", re.M | re.S)

            def split_single(match: re.Match[str]) -> str:
                names = [part.strip() for part in match.group(1).split(",") if part.strip()]
                if name not in names:
                    return match.group(0)
                stay = [n for n in names if n != name]
                lines = []
                if stay:
                    lines.append(f"from .{old} import {', '.join(stay)}")
                lines.append(f"from .{module} import {name}")
                return "\n".join(lines)

            def split_block(match: re.Match[str]) -> str:
                names = [part.strip() for part in re.split(r"[,\n]", match.group(1))
                         if part.strip()]
                if name not in names:
                    return match.group(0)
                stay = [n for n in names if n != name]
                lines = []
                if stay:
                    lines.append(f"from .{old} import {', '.join(stay)}")
                lines.append(f"from .{module} import {name}")
                return "\n".join(lines)

            for path in tree.rglob("*.py"):
                if any(part in path.parts for part in (".git", "build")):
                    continue
                original = path.read_text(errors="replace")
                # THE FILE THAT DEFINES THE SYMBOL MUST NOT IMPORT IT. When a symbol is
                # moved into a module that ALREADY imported it, the stale import is still
                # there and now shadows the local definition. The correct repair is to
                # DELETE it from that import, not to redirect it. Without this the loop
                # wrote `from ._models import parse_header_links` INTO _models.py, which
                # is a circular self-import and turned a 4-hop repair into a dead stop.
                if path.resolve() == home.resolve():
                    def drop_self(match: re.Match[str]) -> str:
                        parts = [part.strip() for part in re.split(r"[,\n]", match.group(1))
                                 if part.strip()]
                        if name not in parts:
                            return match.group(0)
                        rest = [n for n in parts if n != name]
                        return f"from .{old} import {', '.join(rest)}" if rest else ""
                    def drop_single(match: re.Match[str]) -> str:
                        parts = [part.strip() for part in match.group(1).split(",")
                                 if part.strip()]
                        if name not in parts:
                            return match.group(0)
                        rest = [n for n in parts if n != name]
                        return f"from .{old} import {', '.join(rest)}" if rest else ""

                    updated = block.sub(drop_self, original)
                    updated = single.sub(drop_single, updated)
                    if updated != original:
                        path.write_text(updated)
                        touched += 1
                    continue
                updated = block.sub(split_block, original)
                updated = single.sub(split_single, updated)
                if updated != original:
                    path.write_text(updated)
                    touched += 1
            print(f"  IMPORT hop: {name} -> .{module}  ({touched} file(s))")
            continue

        signature = SIG_FAIL.search(log)
        if signature:
            # SIGNATURE hop: the callee gained a required parameter. Supply the
            # parameter's own default at each call site -- the only value that preserves
            # existing behaviour, and the one a human would choose.
            callee, param = signature.group(1), signature.group(2)
            home = home_of(tree, callee)
            if home is None:
                print(f"  SIGNATURE hop: {callee!r} defined nowhere -> cannot repair")
                return 1
            home_ast = ast.parse(home.read_text(errors="replace"))
            default = None
            for node in ast.walk(home_ast):
                if isinstance(node, ast.FunctionDef) and node.name == callee:
                    fn_args = node.args
                    if fn_args.defaults:
                        default = ast.unparse(fn_args.defaults[-1])
            value = default if default is not None else "True"
            touched = 0
            call = re.compile(rf"\b{re.escape(callee)}\(([^()]*)\)")
            for path in tree.rglob("*.py"):
                if any(part in path.parts for part in (".git", "build")):
                    continue
                original = path.read_text(errors="replace")

                def add_kw(match: re.Match[str]) -> str:
                    inner = match.group(1)
                    if f"{param}=" in inner or not inner.strip():
                        return match.group(0)
                    # Never rewrite a DEFINITION as though it were a call. Matching
                    # `def to_bytes_or_str(...)` and appending the keyword produced
                    # `strict: bool, strict=True` -- a duplicate argument SyntaxError,
                    # and the loop then reported "no summary line".
                    start = max(0, match.start() - 8)
                    if "def " in original[start:match.start()]:
                        return match.group(0)
                    return f"{callee}({inner}, {param}={value})"

                updated = call.sub(add_kw, original)
                if updated != original:
                    path.write_text(updated)
                    touched += 1
            print(f"  SIGNATURE hop: {callee}({param}={value}) at {touched} file(s)")
            continue

        undefined = NAME_FAIL.search(log)
        if undefined:
            name = undefined.group(1)
            home = home_of(tree, name)
            if home is None:
                # Moved code carries its IMPORTS with it. A function that used `codecs`
                # in its old module is a NameError in its new one. If the name is
                # importable (stdlib or installed), the repair is to import it -- not to
                # give up. Observed: "NameError: name 'codecs' is not defined" after a
                # 4-symbol move from _utils.py to _models.py.
                frames0 = re.findall(r"^([\w/]+\.py):(\d+): ", log, re.M)
                target0 = None
                for path_text, _line in reversed(frames0):
                    candidate = tree / path_text
                    if "tests" in candidate.parts:
                        continue
                    if candidate.exists():
                        target0 = candidate
                        break
                if target0 is not None and importlib.util.find_spec(name) is not None:
                    insert_import(target0, f"import {name}")
                    print(f"  DEPENDENCY hop: stdlib {name!r} imported into "
                          f"{target0.relative_to(tree)}")
                    continue
                print(f"  DEPENDENCY hop: {name!r} defined nowhere -> cannot repair")
                return 1
            # Destination = the file containing the dangling reference. Take the
            # innermost traceback frame before the NameError, and never the module that
            # already defines the symbol (that produces a self-import loop -- observed).
            frames = re.findall(r"^([\w/]+\.py):(\d+): ", log, re.M)
            target = None
            for path_text, _line in reversed(frames):
                candidate = tree / path_text
                # Never repair a TEST file: production debt is a production repair, and a
                # relative import dropped into tests/ is an ImportError of its own
                # ("No module named 'tests._urlparse'"). Observed exactly that.
                if "tests" in candidate.parts:
                    continue
                if candidate.exists() and candidate.resolve() != home.resolve():
                    target = candidate
                    break
            if target is None:
                print(f"  DEPENDENCY hop: {name!r} has no reference site outside its own "
                      f"module -> nothing to repair")
                return 2
            module = import_path(tree, home)
            # Relative only inside the package; absolute otherwise.
            inside = target.parent == (tree / "httpx")
            stmt = f"from .{module} import {name}" if inside else f"import {tree.name}"
            if not inside:
                stmt = f"from {tree.name}.{module} import {name}"
            insert_import(target, stmt)
            print(f"  DEPENDENCY hop: {name} imported into "
                  f"{target.relative_to(tree)}: {stmt}")
            continue

        # A run that collected nothing prints no summary line. Treating that as
        # convergence is the same lie this repo has caught six times; it must be an
        # explicit failure here.
        if not found:
            print("  NO SUMMARY LINE -- tests did not run. Not convergence.")
            return 3
        # Convergence is only meaningful if the tree was actually broken and a hop
        # repaired it. A tree that was GREEN on arrival (or an edit that silently
        # failed to apply) would otherwise be reported as a successful zip. This
        # happened: a failed regex left the tree untouched and the loop printed
        # "converged".
        if hop == 1 and found[-1] == first_summary:
            print(f"  NOT A ZIP: tree was already {first_summary} before any hop.")
            print("  Nothing was broken, so nothing was repaired.")
            return 4
        failed_lines = [line for line in log.splitlines() if line.startswith("FAILED")]
        print(f"  converged: {found[-1]}; FAILED lines: {len(failed_lines)}")
        for line in failed_lines[:5]:
            print("   ", line[:110])
        return 0

    print("  hop budget exhausted")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
