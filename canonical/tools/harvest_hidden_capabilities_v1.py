#!/usr/bin/env python3
"""Census of executable capability surfaces that no registry row can currently reach.

Why this exists
---------------
The receipt lane's ``discover()`` walks the *registries*: every candidate it can
produce a receipt for must already own a row in the bound or extended registry.
A module that was written, tested and measured but never declared is therefore
invisible to it -- not rejected, unseen.  The compile step has the same blind
spot: ``source_index`` lists such a module as "addressable, not executable", so
the unified model can name it and cannot call it.

This tool is the missing enumeration.  It reads the tree, not the registries, and
classifies every Python module by *invocation shape* -- the property that decides
whether the runtime could execute it at all:

``contract``  a top-level ``run(args, root) -> dict`` (or the lane's other
              entrypoint spellings with the same two parameters).  Callable
              in-process by ``run_adapter_locally``.
``cli``       a top-level ``main``/``__main__`` guard.  Callable through the
              repository's own ``bound_capabilities/cli_command.py`` adapter.
``library``   importable, no invocation shape a generic adapter could drive.
``test``      a test module (excluded from capability counts).

Every candidate that is not already declared is emitted with a deterministic id,
a content hash, the triggers the router could match on, and the evidence signals
the module carries (receipts, schemas, hashes).  Nothing is promoted here: a
census is a claim about what exists, and promotion needs execution evidence.

Determinism
-----------
Sorted traversal, no timestamps, no environment values.  Two runs over one tree
produce byte-identical JSON.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_HIDDEN_CAPABILITY_CENSUS_V1"
ROOT = Path(__file__).resolve().parents[2]

SKIP_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "site-packages",
    "tmp", "instances",
})
SKIP_PATH_PREFIXES = (
    "canonical/astra_runtime/tmp/",
    "canonical/tests/",
    "tests/",
    "generated_tests/",
    "canonical/capabilities/internalized/software_engineering/mini_swe_agent_02",
)
TEST_NAME_RE = re.compile(r"(^test_|_test\.py$|^test\.py$|_probe\d*\.py$|^conftest\.py$)")

ENTRYPOINTS = ("run", "execute", "invoke", "apply")
ARGS_NAMES = frozenset({"args", "arguments", "request", "payload", "params", "inputs"})

EVIDENCE_SIGNALS = {
    "receipt": "receipt",
    "schema": "schema",
    "sha256": "sha256",
    "json_stdout": "json.dumps",
    "refusal": "refus",
    "verification": "verif",
    "evidence": "evidence",
    "measured": "measur",
}

STOP_TOKENS = frozenset("""
a an and are as at be by can could do does for from has have how i if in into is it
its of on or our that the their them then there these this to using was we what when
where which who why will with without you your v1 v2 v3 v4 v5 v6 v7 v8 v9 v10 v11 v12
v13 v14 v15 v16 v17 v18 v19 v20 v21 v22 v23 v24 v25 v26 v27 v28 v29 v30 v31 v32 v33
the_and a_the
""".split())


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def first_doc_line(tree: ast.AST) -> str:
    doc = ast.get_docstring(tree) or ""
    for line in doc.splitlines():
        line = line.strip()
        if line:
            return line[:240]
    return ""


def top_level_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def shape_of(tree: ast.Module, source: str) -> tuple[str, str | None]:
    """(kind, entrypoint).  Contract wins over CLI: it is the cheaper invocation."""
    for fn in top_level_functions(tree):
        if fn.name not in ENTRYPOINTS:
            continue
        params = [a.arg for a in fn.args.posonlyargs + fn.args.args]
        if len(params) == 2 and params[0] in ARGS_NAMES:
            return "contract", fn.name
    if any(fn.name == "main" for fn in top_level_functions(tree)):
        return "cli", "main"
    if "__main__" in source:
        return "cli", "main"
    return "library", None


def signals_of(source: str) -> list[str]:
    low = source.lower()
    return sorted(name for name, needle in EVIDENCE_SIGNALS.items() if needle in low)


def imports_of(tree: ast.Module) -> list[str]:
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                mods.add(node.module.split(".")[0])
    return sorted(mods)


def triggers_for(rel: str, doc: str) -> list[str]:
    stem = Path(rel).stem
    tokens: list[str] = []
    for raw in re.split(r"[^a-z0-9]+", (stem + " " + doc).lower()):
        if len(raw) < 3 or raw in STOP_TOKENS or raw.isdigit():
            continue
        if raw not in tokens:
            tokens.append(raw)
    return tokens[:16]


CAP_ID_RE = re.compile(r"^([a-z][a-z0-9_]*(?:\.[a-z0-9_]+){1,7}(?:\.v\d+)?)\s*[\u2014:-]")
INPUT_LINE_RE = re.compile(r"^\s{2,}([a-z][a-z0-9_]*)\s{2,}")
RESULT_FIELDS_RE = re.compile(r"^\s*result_fields:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def declared_contract(tree: ast.AST) -> dict[str, Any]:
    """What the module says about itself: its capability name, inputs, result fields.

    These modules were written as capability adapters -- most open with
    ``python.something.v1 -- <what it does>`` and list their kwargs and result
    fields -- but no registry row was ever derived from that text.  Reading it is
    derivation, not invention: every field here is quoted from the module.
    """
    doc = ast.get_docstring(tree) or ""
    cap_id = None
    for line in doc.splitlines():
        m = CAP_ID_RE.match(line.strip())
        if m:
            cap_id = m.group(1)
            break
    inputs: list[str] = []
    in_block = False
    for line in doc.splitlines():
        low = line.strip().lower()
        if low.startswith("inputs"):
            in_block = True
            continue
        if in_block and (low.startswith("result_fields") or not line.strip()):
            in_block = False
            continue
        if in_block:
            m = INPUT_LINE_RE.match(line)
            if m:
                inputs.append(m.group(1))
    rf = RESULT_FIELDS_RE.search(doc)
    result_fields = [t.strip() for t in (rf.group(1).split(",") if rf else []) if t.strip()]
    return {"capability_id": cap_id, "inputs": inputs[:24], "result_fields": result_fields[:32]}


def capability_id(rel: str) -> str:
    dotted = rel[:-3].replace("/", ".")
    return dotted + ".hidden.v1"


def walk_python(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if any(rel.startswith(p) for p in SKIP_PATH_PREFIXES):
                continue
            yield path


def declared_ids(root: Path) -> dict[str, str]:
    """Every id any authority already knows, with where it was found."""
    declared: dict[str, str] = {}
    for rel, key in (
        ("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json", "capabilities"),
        ("canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json", "capabilities"),
        ("canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json", "capabilities"),
        ("canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json", "entries"),
    ):
        path = root / rel
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for cid in (doc.get(key) or {}):
            declared.setdefault(str(cid), rel)
    model = root / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
    if model.is_file():
        try:
            doc = json.loads(model.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = {}
        for row in doc.get("capabilities") or []:
            if isinstance(row, dict) and row.get("id"):
                declared.setdefault(str(row["id"]), "unified_model")
    return declared


def declared_source_paths(root: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    for rel, key in (
        ("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json", "capabilities"),
        ("canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json", "capabilities"),
    ):
        path = root / rel
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for cid, entry in (doc.get(key) or {}).items():
            if not isinstance(entry, dict):
                continue
            src = entry.get("source") or {}
            p = src.get("path") or src.get("adapter_path")
            if isinstance(p, str):
                paths.setdefault(p, str(cid))
    return paths


def census(root: Path) -> dict[str, Any]:
    declared = declared_ids(root)
    declared_paths = declared_source_paths(root)

    rows: list[dict[str, Any]] = []
    counts = {"files": 0, "unparseable": 0, "tests": 0,
              "contract": 0, "cli": 0, "library": 0,
              "declared": 0, "declared_by_capability_id": 0,
              "self_described": 0, "hidden_executable": 0}
    by_domain: dict[str, dict[str, int]] = {}

    for path in walk_python(root):
        rel = path.relative_to(root).as_posix()
        counts["files"] += 1
        if TEST_NAME_RE.search(Path(rel).name):
            counts["tests"] += 1
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError):
            counts["unparseable"] += 1
            continue
        kind, entrypoint = shape_of(tree, source)
        counts[kind] += 1
        if kind == "library":
            continue
        cid = capability_id(rel)
        contract = declared_contract(tree)
        # A module may be declared by capability id while its file path was never
        # recorded.  Counting that as hidden would be wrong: the capability is in
        # the registry, only the binding is implicit (`adapter_module` -> stem).
        named = contract["capability_id"]
        if cid in declared or rel in declared_paths:
            counts["declared"] += 1
            continue
        if named and (named in declared or named.rsplit(".v", 1)[0] in declared):
            counts["declared_by_capability_id"] += 1
            continue
        doc = first_doc_line(tree)
        domain = rel.split("/")[0] if "/" in rel else "(root)"
        if rel.startswith("canonical/"):
            parts = rel.split("/")
            domain = "canonical/" + (parts[1] if len(parts) > 1 else "")
        bucket = by_domain.setdefault(domain, {"contract": 0, "cli": 0})
        bucket[kind] += 1
        counts["hidden_executable"] += 1
        if contract["capability_id"]:
            counts["self_described"] += 1
        rows.append({
            "id": cid,
            "path": rel,
            "kind": kind,
            "entrypoint": entrypoint,
            "doc": doc,
            "declared_capability_id": contract["capability_id"],
            "declared_inputs": contract["inputs"],
            "declared_result_fields": contract["result_fields"],
            "triggers": triggers_for(rel, doc),
            "signals": signals_of(source),
            "imports": imports_of(tree)[:24],
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        })

    rows.sort(key=lambda r: (not r["declared_capability_id"], -len(r["signals"]), r["path"]))
    return {
        "schema": SCHEMA,
        "root": ".",
        "counts": counts,
        "by_domain": {k: v for k, v in sorted(by_domain.items())},
        "declared_ids_seen": len(declared),
        "hidden": rows,
        "digest": hashlib.sha256(canonical_json(rows).encode("utf-8")).hexdigest(),
    }


def harvested_rows(root: Path) -> list[dict[str, Any]]:
    """Rows for the compiled model: no argparse, cheap prefilter, always fresh.

    The compiler must not read a stale census artifact -- a capability claim that
    outlives its file is exactly the failure mode the artifact's digest exists to
    prevent -- so this re-derives classification from the tree on every compile.
    A regex prefilter keeps the cost to the files that can plausibly carry an
    invocation shape, which is where all of them are.
    """
    declared = declared_ids(root)
    declared_paths = declared_source_paths(root)
    out: list[dict[str, Any]] = []
    shape_hint = re.compile(r"^\s*(?:async\s+)?def\s+(?:run|execute)\s*\(", re.MULTILINE)
    for path in walk_python(root):
        rel = path.relative_to(root).as_posix()
        if TEST_NAME_RE.search(path.name):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "__main__" not in source and not shape_hint.search(source) and "def main(" not in source:
            continue
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            continue
        kind, entrypoint = shape_of(tree, source)
        if kind == "library":
            continue
        cid = capability_id(rel)
        if cid in declared or rel in declared_paths:
            continue
        contract = declared_contract(tree)
        named = contract["capability_id"]
        if named and (named in declared or named.rsplit(".v", 1)[0] in declared):
            continue
        out.append({
            "id": cid,
            "path": rel,
            "kind": kind,
            "entrypoint": entrypoint,
            "doc": first_doc_line(tree),
            "declared_capability_id": named,
            "declared_inputs": contract["inputs"],
            "declared_result_fields": contract["result_fields"],
            "triggers": triggers_for(rel, contract["capability_id"] or ""),
            "sha256": sha256_file(path),
        })
    out.sort(key=lambda r: r["path"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="canonical/capabilities/hidden/HIDDEN_CAPABILITY_CENSUS_V1.json")
    ap.add_argument("--print-summary", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    result = census(root)
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.print_summary or True:
        c = result["counts"]
        print(json.dumps({
            "files": c["files"], "tests": c["tests"], "unparseable": c["unparseable"],
            "contract": c["contract"], "cli": c["cli"], "library": c["library"],
            "already_declared": c["declared"], "hidden_executable": c["hidden_executable"],
            "digest": result["digest"], "out": str(out.relative_to(root)),
        }, indent=1))
        top = result["hidden"][:12]
        print("\ntop candidates by evidence signal:")
        for r in top:
            print(f"  {r['kind']:<8} {r['path']}  [{','.join(r['signals'][:4])}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
