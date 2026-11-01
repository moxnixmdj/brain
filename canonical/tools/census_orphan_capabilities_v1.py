"""Census which capabilities in this repo exist but are never called.

The recurring finding of this work is not a missing mechanism. It is a built, tested mechanism
with **no caller**: `finite_capability_diagnosis.select_probe` narrows a version space exactly,
has seven passing tests, and until this session nothing in the tree invoked it.

Searching for such things by name repeatedly failed. Searching by *effect* found them. This
tool searches by effect mechanically: it builds a name-level call graph over the tree and
classifies every module-level function and class by who references it.

CLASSES
    LIVE        referenced by at least one non-test module other than the one defining it
    TEST_ONLY   referenced only from tests -- specified, never used in production
    ORPHAN      referenced nowhere at all

Matching is by bare identifier, so it is an approximation: two unrelated functions sharing a
name can make a dead one look live. The direction of that error is safe (it under-reports
orphans), and names defined in many modules are excluded from the ORPHAN class for that reason.

Usage:
    python3 canonical/tools/census_orphan_capabilities_v1.py [--root canonical] [--limit 40]
    python3 canonical/tools/census_orphan_capabilities_v1.py --json out.json
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_ORPHAN_CAPABILITY_CENSUS_V1"

def _is_test(path: Path) -> bool:
    """A test is a file named `test_*`, or anything inside a `tests` directory.

    Deliberately not a substring search over the whole path: a temporary directory called
    `test_something0` (which is what pytest hands out) would otherwise mark every file under
    it as a test and silently empty the census.
    """
    if path.name.startswith("test_"):
        return True
    return "tests" in path.parts


def _definitions(tree: ast.AST) -> dict[str, str]:
    """Module-level functions and classes: name -> kind."""
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = "function"
        elif isinstance(node, ast.ClassDef):
            out[node.name] = "class"
    return out


def _references(tree: ast.AST) -> set[str]:
    """Every identifier this module mentions: loads, attributes and imported names."""
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                out.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # __all__ and similar name lists
            for token in node.value.replace("\n", " ").split():
                if token.isidentifier():
                    out.add(token)
    return out


def census(root: Path) -> dict:
    files = [p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts]
    definitions: dict[str, list[dict]] = defaultdict(list)
    references: dict[str, set[str]] = {}
    errors: list[str] = []

    for path in files:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except SyntaxError as exc:
            errors.append(f"{path}: {exc}")
            continue
        references[str(path)] = _references(tree)
        for name, kind in _definitions(tree).items():
            definitions[name].append({"file": str(path), "kind": kind, "is_test": _is_test(path)})

    # A name defined in many places is too ambiguous to classify by bare identifier.
    ambiguous = {name for name, sites in definitions.items() if len(sites) > 3}

    rows: list[dict] = []
    for name, sites in definitions.items():
        for site in sites:
            if site["is_test"]:
                continue
            if name in ambiguous:
                continue
            live = test_only = False
            for other_file, names in references.items():
                if other_file == site["file"]:
                    continue
                if name not in names:
                    continue
                if _is_test(Path(other_file)):
                    test_only = True
                else:
                    live = True
            status = "LIVE" if live else ("TEST_ONLY" if test_only else "ORPHAN")
            rows.append({"name": name, "file": site["file"], "kind": site["kind"], "status": status})

    # Public names only: a leading underscore is an implementation detail by convention.
    rows = [r for r in rows if not r["name"].startswith("_")]

    counts = defaultdict(int)
    for row in rows:
        counts[row["status"]] += 1

    return {
        "schema": SCHEMA,
        "root": str(root),
        "files_scanned": len(files),
        "parse_errors": errors,
        "counts": dict(sorted(counts.items())),
        "ambiguous_names_skipped": len(ambiguous),
        "rows": rows,
    }


def module_census(root: Path) -> dict:
    """Module-level reachability, which is the sharper question.

    A function called by another function in its own file is not dead code, but if no module
    outside its tests imports the file, the capability is unreachable from production. Static
    imports are not the whole story -- this tree also dispatches by name -- so modules whose
    stem appears as a string literal anywhere in non-test code are excluded from "unreachable".
    That is an upper bound on unreachability, deliberately conservative in the safe direction.
    """
    files = [p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts]
    imported: dict[str, set[str]] = defaultdict(set)
    literals: list[str] = []

    for path in files:
        if _is_test(path):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported[node.module].add(str(path))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported[alias.name].add(str(path))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.append(node.value)

    blob = "\n".join(literals)

    # Import statements name modules absolutely (`canonical.runtime.x`) while a scan rooted at
    # `canonical` names them relatively (`runtime.x`). Compare on suffixes so a module counts as
    # imported wherever the scan starts.
    imported_suffixes: set[str] = set()
    for key in imported:
        bits = key.split(".")
        for size in range(1, min(len(bits), 4) + 1):
            imported_suffixes.add(".".join(bits[-size:]))

    def module_name(path: Path) -> str:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        parts = list(rel.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _top(path: Path) -> str:
        try:
            rel = path.relative_to(root)
        except ValueError:
            return ""
        return rel.parts[0] if len(rel.parts) > 1 else ""

    targets = [
        p for p in files if not _is_test(p) and _top(p) in {"runtime", "swe_kernel"}
    ]
    no_importer = [p for p in targets if module_name(p) not in imported_suffixes]
    unreachable = [p for p in no_importer if p.stem not in blob]

    test_names = {q.name for q in (root / "tests").glob("test_*.py")}

    def has_test(path: Path) -> bool:
        return any(name.startswith("test_" + path.stem) or path.stem in name for name in test_names)

    with_test = [p for p in unreachable if has_test(p)]
    return {
        "modules_scanned": len(targets),
        "no_static_importer": len(no_importer),
        "not_named_as_string": len(unreachable),
        "with_matching_test": len(with_test),
        "without_any_test": len(unreachable) - len(with_test),
        "modules": [str(p) for p in unreachable],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="canonical")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--json", default=None)
    parser.add_argument("--status", default="ORPHAN", choices=["ORPHAN", "TEST_ONLY", "LIVE", "ALL"])
    parser.add_argument("--modules", action="store_true",
                        help="report module-level reachability instead of names")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print("census: root not found: " + str(root), file=sys.stderr)
        return 2

    if args.modules:
        module_report = module_census(root)
        if args.json:
            Path(args.json).write_text(
                json.dumps({"schema": SCHEMA + "_MODULES", **module_report}, indent=2) + "\n",
                encoding="utf-8",
            )
        print(f"census: schema={SCHEMA}_MODULES root={root}")
        print(f"census: modules scanned            = {module_report['modules_scanned']}")
        print(f"census: no non-test static importer= {module_report['no_static_importer']}")
        print(f"census: not named as a string      = {module_report['not_named_as_string']}")
        print(f"census:   ...with a matching test  = {module_report['with_matching_test']}")
        print(f"census:   ...with no test at all   = {module_report['without_any_test']}")
        return 0

    report = census(root)

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"census: schema={SCHEMA}")
    print(f"census: files={report['files_scanned']} parse_errors={len(report['parse_errors'])}")
    print(
        "census: LIVE={LIVE} TEST_ONLY={TEST_ONLY} ORPHAN={ORPHAN} "
        "(ambiguous names skipped: {n})".format(
            n=report["ambiguous_names_skipped"],
            **{k: report["counts"].get(k, 0) for k in ("LIVE", "TEST_ONLY", "ORPHAN")},
        )
    )

    rows = report["rows"]
    if args.status != "ALL":
        rows = [r for r in rows if r["status"] == args.status]
    rows = sorted(rows, key=lambda r: (r["file"], r["name"]))[: args.limit]

    if rows:
        print()
        print(f"{'file':58} {'kind':9} name")
        for row in rows:
            print(f"{row['file']:58} {row['kind']:9} {row['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
