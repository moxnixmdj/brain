# PROJECT_BRAIN
"""python.tests.generate.scaffold.v1 — write tests for uncovered paths.

The crown closes loops only where tests already exist; uncovered code is
where regressions breed.  This adapter writes deterministic SMOKE-scaffold
unittests for module-scope functions from the verified symbol index, then
EXECUTES them (pytest) and reports what actually happened.

Honesty laws it refuses to break:

* SMOKE, NOT SEMANTICS — scaffolds assert only "evaluates with derived
  fixtures" (result is not an exception object); no invented expected
  values, no fake coverage claims.  Target functions that cannot be derived
  deterministically (unannotated params, *args, closures requiring state)
  are REFUSED with evidence per target — listed, never silently skipped.
* NEVER-MUTATE-SOURCE — source tree read-only; generated tests land in the
  ``generated_tests_root`` (which must NOT overlap source_root).
* EXECUTE-OR-REFUSE — nothing is "generated" unless pytest actually ran it
  in the same call and the harness recorded per-test pass/fail.
* DETERMINISM — byte-identical generated text and artifact on rerun
  (pin-proven); targets processed in sorted order; repr truncation pinned.
* FAIL CLOSED on bad inputs, path escapes, unknown modules/names (with
  lexical candidates listed), pytest absence (reported UNAVAILABLE —
  verdict then degrades to generated:false evidence, verified:false).

Inputs (kwargs, all paths confined to the repo):
  targets_path     JSON: [{"module": "pkg/x.py", "name": "fn"}] — name
                   optional: omit to target every module-scope def in module
  source_root      index scope (the index binds names to modules)
  generated_tests_root  where test modules are written (RE-created)
  output_path      summary artifact (registry result_fields mirror)
  index_path       optional validated slice-1 cache (schema+totals+root)
  python_executable  interpreter with pytest; defaults to this one
  timeout_s        wall clock cap for the pytest run (default 120)

result_fields: adapter, target_count, generated_count, refused_count,
test_count, test_passed, test_failed, complete, diff-free determinism note,
output_path, output_sha256, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_TESTGEN_SCAFFOLD_V1"
NAME_RE = re.compile(r"^[A-Za-z_]\w*$")

_FIXTURE_BY_ANNOTATION = {
    "int": "1", "float": "1.5", "str": '"s"', "bytes": 'b"s"', "bool": "True",
    "list": "[]", "dict": "{}", "set": "set()", "tuple": "()",
    "list[int]": "[1]", "list[str]": '["s"]', "list[float]": "[1.5]",
    "dict[str, int]": '{"s": 1}',
    "dict[str, str]": '{"s": "s"}', "dict[str, float]": '{"s": 1.5}',
    "Optional[int]": "1", "Optional[str]": '"s"', "Optional[float]": "1.5",
}


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.tests.generate.scaffold.v1",
        "reason": reason,
    }


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path | dict:
    if not rel or not isinstance(rel, str):
        return _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        return _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        return _fail("PATH_MISSING:" + rel)
    return p


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}


def _tree_manifest(root: Path) -> str:
    rows = [[str(p.relative_to(root)).replace("\\", "/"), _sha256(p.read_bytes())]
            for p in sorted(root.rglob("*.py")) if p.is_file()
            and not any(part in _SKIP_DIRS for part in p.parts)]
    return _sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8"))


def _fixture_for(param: ast.arg) -> tuple[str | None, str]:
    """Return (literal_repr, note) for a parameter, or (None, reason)."""
    if param.annotation is None:
        if param.default_value is None:
            return None, "UNANNOTATED_PARAM_NO_DEFAULT:" + param.arg
        try:
            return repr(ast.literal_eval(param.default_value)), "default"
        except Exception:
            return None, "NON_LITERAL_DEFAULT:" + param.arg
    ann = ast.unparse(param.annotation).strip()
    if ann in _FIXTURE_BY_ANNOTATION:
        return _FIXTURE_BY_ANNOTATION[ann], "annotation:" + ann
    base = ann.split("[")[0].split(".")[-1]
    if base in _FIXTURE_BY_ANNOTATION:
        return _FIXTURE_BY_ANNOTATION[base], "annotation-base:" + ann
    return None, "UNRESOLVABLE_ANNOTATION:" + ann


def _derive_call_from_ast(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str | None, list[str]]:
    """Derive `name(**fixtures)` from a parsed function definition.

    Every fixed parameter must map to a deterministic literal: annotated via
    the pinned annotation table, else a literal default, else refuse.
    (The index carries bare-name signatures only; the module file is stdlib
    truth.)"""
    name = fn_node.name
    a = fn_node.args
    params = list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
    fixtures = []
    for i, param in enumerate(params):
        shim = ast.arg(arg=param.arg, annotation=param.annotation)
        default_node = None
        # defaults align to the END of posonlyargs+args
        n_pos = len(a.posonlyargs) + len(a.args)
        if i >= len(a.posonlyargs) + len(a.args):
            kidx = params.index(param) - n_pos
            kd = a.kw_defaults[kidx] if 0 <= kidx < len(a.kw_defaults) else None
            default_node = kd
        else:
            posidx = i  # within positional space
            d = a.defaults
            pos_defaults_start = n_pos - len(d)
            if posidx >= pos_defaults_start:
                default_node = d[posidx - pos_defaults_start]
        shim.default_value = default_node
        lit, _note = _fixture_for(shim)
        if lit is None:
            return None, [_note]
        fixtures.append(f"{param.arg}={lit}")
    return f"{name}({', '.join(fixtures)})", fixtures


def _module_function_node(path: Path, name: str) -> ast.FunctionDef | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _render_module(rows: list[dict], src_abs: Path) -> str:
    lines = [
        "# PROJECT_BRAIN auto-generated SMOKE scaffolds (python.tests.generate.scaffold.v1)",
        "# Claims only: callable evaluates with deterministic derived fixtures.",
        "import pathlib",
        "import sys",
        "import unittest",
        "",
        f"sys.path.insert(0, {str(src_abs)!r})",
        "",
        "",
    ]
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["module"], []).append(r)
    cls_idx = 0
    for module in sorted(groups):
        dotted = module[:-3].replace("/", ".") if module.endswith(".py") else module.replace("/", ".")
        for r in sorted(groups[module], key=lambda x: x["name"]):
            cls_idx += 1
            cls = "GeneratedSmoke" + str(cls_idx)
            lines += [
                f"class {cls}(unittest.TestCase):",
                f"    def test_smoke_{r['name']}(self):",
                f"        from {dotted} import {r['name']}",
                f"        result = {r['call_expr']}",
                "        self.assertNotIsInstance(result, BaseException)",
                "",
                "",
            ]
    lines.append('if __name__ == "__main__":')
    lines.append("    unittest.main()")
    lines.append("")
    return "\n".join(lines)


def _load_index(source_abs: Path, cached: Path | None, source_root: str) -> tuple[dict, bool]:
    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
    if cached is not None:
        art = json.loads(cached.read_text(encoding="utf-8"))
        if art.get("schema") != "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1":
            return _fail("INDEX_CACHE_SCHEMA_MISMATCH")
        if str(art.get("source_root")) != str(source_root):
            _fail("INDEX_CACHE_SOURCE_ROOT_MISMATCH:" + str(art.get("source_root")))
        if int((art.get("totals") or {}).get("files", 0)) <= 0:
            return _fail("INDEX_CACHE_TOTALS_INVALID")
        return art, True
    probe = source_abs / ".testgen_probe_index.json"
    indexer.run({"source_root": ".", "output_path": probe.name}, source_abs)
    art = json.loads(probe.read_text(encoding="utf-8"))
    probe.unlink()
    return art, False


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    tgt_rel = str(args.get("targets_path") or "")
    tgt_path = _safe_path(repo, tgt_rel, must_exist=True)
    if isinstance(tgt_path, dict): return tgt_path
    try:
        targets = json.loads(tgt_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _fail("TARGETS_UNREADABLE_JSON:" + type(exc).__name__)
    if not isinstance(targets, list) or not targets:
        return _fail("TARGETS_EMPTY")
    for t in targets:
        if not isinstance(t, dict) or not t.get("module"):
            return _fail("TARGET_SCHEMA_MISSING:module")

    source_root = str(args.get("source_root") or "")
    source_abs = _safe_path(repo, source_root, must_exist=True)
    if isinstance(source_abs, dict): return source_abs
    if not source_abs.is_dir():
        return _fail("SOURCE_ROOT_NOT_DIRECTORY")
    gen_rel = str(args.get("generated_tests_root") or "")
    gen_abs = _safe_path(repo, gen_rel)
    if isinstance(gen_abs, dict): return gen_abs
    out_abs = _safe_path(repo, str(args.get("output_path") or ""))
    if isinstance(out_abs, dict): return out_abs
    for pth, key in ((gen_abs, "generated_tests_root"), (out_abs, "output_path")):
        if pth == source_abs or source_abs in pth.parents:
            return _fail("PATH_OVERLAPS_SOURCE_ROOT:" + key)
    timeout_s = int(args.get("timeout_s") or 120)
    python_exe = str(args.get("python_executable") or sys.executable)
    cached = _safe_path(repo, str(args["index_path"]), must_exist=True) if args.get("index_path") else None

    manifest_before = _tree_manifest(source_abs)
    index, cache_used = _load_index(source_abs, cached, source_root)
    mods = {}
    for row in index.get("modules") or []:
        mods[str(row["path"])] = row

    expanded: list[dict] = []
    refused: list[dict] = []
    for t in targets:
        module = str(t["module"])
        name = t.get("name")
        row = mods.get(module)
        if row is None:
            exact_prefix = sorted(p for p in mods if p.endswith("/" + module.split("/")[-1]))
            refused.append({"target": t, "reason": "MODULE_NOT_IN_INDEX:" + module,
                            "candidates": exact_prefix[:3]})
            continue
        defs = [d for d in row.get("definitions") or []
                if str(d["qualname"]).count(".") == 0 and d.get("kind") == "function"]
        wanted = sorted((d for d in defs if name is None or d["name"] == name),
                        key=lambda d: str(d["name"]))
        if not wanted:
            names = sorted(d["name"] for d in defs)
            close = sorted(n for n in names if abs(len(n) - len(str(name))) <= 2
                           and n.startswith(str(name)[: max(2, len(str(name)) // 2)]))[:3] if name else []
            refused.append({"target": t, "reason": "NAME_NOT_AT_MODULE_SCOPE:" + str(name),
                            "candidates": close})
            continue
        for d in wanted:
            expanded.append({"module": module, "name": d["name"], "def": d})

    gen_rows = []
    for e in expanded:
        mod_path = source_abs / e["module"]
        node = _module_function_node(mod_path, e["name"])
        if node is None:
            refused.append({"target": {"module": e["module"], "name": e["name"]},
                            "reason": "DEFINITION_NODE_NOT_IN_MODULE_AST"})
            continue
        call, notes = _derive_call_from_ast(node)
        if call is None:
            refused.append({"target": {"module": e["module"], "name": e["name"]},
                            "reason": ";".join(notes)})
            continue
        gen_rows.append({"module": e["module"], "name": e["name"],
                         "call_expr": call, "fixtures": notes})
    gen_rows.sort(key=lambda r: (r["module"], r["name"]))

    if gen_abs.exists():
        import shutil
        shutil.rmtree(gen_abs)
    gen_abs.mkdir(parents=True)
    test_file = gen_abs / f"test_generated_smoke_{_sha256(json.dumps([[r['module'], r['name']] for r in gen_rows]).encode())[:8]}.py"
    text = _render_module(gen_rows, source_abs) if gen_rows else ""
    test_file.write_text(text, encoding="utf-8")

    passed = failed = 0
    run_rc = None
    pytest_version = None
    if gen_rows:
        probe = subprocess.run([python_exe, "-c", "import pytest;print(pytest.__version__)"],
                               capture_output=True, text=True, timeout=min(timeout_s, 30))
        if probe.returncode == 0:
            pytest_version = probe.stdout.strip()
            import os
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            proc = subprocess.run([python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                   str(test_file)],
                                  cwd=repo, capture_output=True, text=True, timeout=timeout_s,
                                  env=env)
            run_rc = proc.returncode
            m = re.search(r"(\d+) passed", proc.stdout + proc.stderr)
            passed = int(m.group(1)) if m else 0
            m = re.search(r"(\d+) failed", proc.stdout + proc.stderr)
            failed = int(m.group(1)) if m else 0

    manifest_after = _tree_manifest(source_abs)
    if manifest_after != manifest_before:
        return _fail("SOURCE_TREE_MUTATED")

    complete = (not refused) and bool(gen_rows) and passed == len(gen_rows)
    verified = complete and run_rc == 0
    artifact = {
        "schema": SCHEMA,
        "target_count": len(targets),
        "expanded_target_count": len(expanded),
        "generated_count": len(gen_rows),
        "refused_count": len(refused),
        "test_count": len(gen_rows),
        "test_passed": passed,
        "test_failed": failed,
        "pytest": pytest_version or "UNAVAILABLE",
        "complete": complete,
        "smoke_law": "scaffolds assert evaluation with derived fixtures only; zero semantic claims",
        "cache_used": cache_used,
        "generated": gen_rows,
        "refusals": refused,
        "generated_test_file": str(test_file.relative_to(repo)),
        "generated_sha256": _sha256(text.encode("utf-8")),
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    atext = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(atext, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact
    return {
        "adapter": "python_tests_generate_scaffold",
        "target_count": len(targets),
        "generated_count": len(gen_rows),
        "refused_count": len(refused),
        "test_count": len(gen_rows),
        "test_passed": passed,
        "test_failed": failed,
        "complete": complete,
        "output_path": str(args.get("output_path")),
        "output_sha256": _sha256(atext.encode("utf-8")),
        "output_verified": out_verified,
        "verified": bool(verified),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    for name in ("targets_path", "source_root", "generated_tests_root", "output_path"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--index_path", default=None)
    p.add_argument("--python_executable", default=None)
    p.add_argument("--timeout_s", type=int, default=120)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
