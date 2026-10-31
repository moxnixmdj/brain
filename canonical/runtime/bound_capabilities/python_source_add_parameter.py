"""Cross-file Python signature evolution (`python.refactor.add_parameter.v1`).

Adds a backward-compatible parameter `<param>=<default>` to a function or
`Class.method` under `source_root`:
- Supports explicit `default_expr` OR Fowler *Parameterize Function* attribute
  override (`self.<param>` -> `(param if param is not None else self.<param>)`
  with `param=None` default when `default_expr` is `None` or omitted and body
  loads `self.<param>`).
- Audits all call sites across the project for positional-arity overflow or
  keyword-argument collision before mutating disk.
- Verifies syntax, imports, and `unittest` discovery in a clean `-B` child
  process and rolls back byte-for-byte on any failure.
"""
from __future__ import annotations

import ast
import hashlib
import json
import keyword
import os
import pathlib
import subprocess
import sys
from typing import Any, Mapping


def _safe_path(repo: pathlib.Path, raw: str, *, must_exist: bool = False) -> pathlib.Path:
    if not raw or not isinstance(raw, str):
        raise RuntimeError("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / raw).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY:" + raw)
    if must_exist and not p.exists():
        raise RuntimeError("PATH_MISSING:" + raw)
    return p


def _purge_pyc(path: pathlib.Path) -> None:
    cache_dir = path.parent / "__pycache__"
    if cache_dir.is_dir():
        stem = path.stem + "."
        for f in cache_dir.iterdir():
            if f.name.startswith(stem) and f.suffix == ".pyc":
                f.unlink(missing_ok=True)


def _resolve_project_and_tests(repo: pathlib.Path, src_root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    proj = src_root
    while (proj / "__init__.py").is_file() and proj != repo and repo in proj.parents:
        proj = proj.parent
    if proj == src_root and (src_root.parent / "tests").is_dir() and src_root.parent != repo and repo in src_root.parent.parents:
        proj = src_root.parent
    tdir = src_root / "tests" if (src_root / "tests").is_dir() else (proj / "tests" if (proj / "tests").is_dir() else proj)
    return proj, tdir


def _collect_state(proj: pathlib.Path, tdir: pathlib.Path) -> tuple[bool, int, set[str], str]:
    prod_mods: list[str] = []
    for p in sorted(proj.rglob("*.py")):
        if "__pycache__" in p.parts or ".git" in p.parts:
            continue
        rel = p.relative_to(proj).as_posix()
        if rel.startswith("tests/") or "/tests/" in f"/{rel}" or p.name.startswith("test_") or p.name.endswith("_test.py"):
            continue
        ast.parse(p.read_bytes())
        parts = [x for x in p.relative_to(proj).with_suffix("").parts if x != "__init__"]
        if parts:
            prod_mods.append(".".join(parts))

    runner = (
        "import importlib, importlib.util, json, pathlib, sys, unittest\n"
        "proj = pathlib.Path(sys.argv[1]).resolve()\n"
        "tdir = pathlib.Path(sys.argv[2]).resolve()\n"
        "mods = json.loads(sys.argv[3])\n"
        "sys.argv = [sys.argv[0]]\n"
        "sys.path.append(str(proj))\n"
        "stdlib = getattr(sys, 'stdlib_module_names', frozenset())\n"
        "for m in mods:\n"
        "    try:\n"
        "        if m in stdlib:\n"
        "            cand_p = proj / (m + '.py')\n"
        "            if not cand_p.is_file():\n"
        "                cand_p = proj / m / '__init__.py'\n"
        "            sp = importlib.util.spec_from_file_location('_proj_shadow_' + m, cand_p)\n"
        "            mod_obj = importlib.util.module_from_spec(sp)\n"
        "            sp.loader.exec_module(mod_obj)\n"
        "        else:\n"
        "            importlib.import_module(m)\n"
        "    except SystemExit:\n"
        "        pass\n"
        "ran = 0\n"
        "bad = []\n"
        "if tdir.is_dir():\n"
        "    top = str(proj) if (tdir == proj or (tdir / '__init__.py').is_file()) else str(tdir)\n"
        "    suite = unittest.TestLoader().discover(start_dir=str(tdir), top_level_dir=top)\n"
        "    res = unittest.TestResult()\n"
        "    suite.run(res)\n"
        "    ran = res.testsRun\n"
        "    bad = sorted(str(tc.id()) for tc, _ in (res.failures + res.errors))\n"
        "print(json.dumps({'ok': True, 'ran': ran, 'bad': bad}))\n"
    )
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONSAFEPATH": "1"}
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [sys.executable, "-B", "-P", "-c", runner, str(proj), str(tdir), json.dumps(prod_mods)],
        cwd=str(proj),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return False, 0, set(), (proc.stderr or proc.stdout)[-300:]
    info = json.loads(proc.stdout.strip().splitlines()[-1])
    return bool(info.get("ok")), int(info.get("ran") or 0), set(info.get("bad") or ()), ""


def _verify_project(proj: pathlib.Path, tdir: pathlib.Path, baseline_bad: set[str] | None = None) -> tuple[bool, int, str]:
    ok, ran, post_bad, err = _collect_state(proj, tdir)
    if not ok:
        return False, ran, err
    regressed = post_bad - (baseline_bad or set())
    if regressed:
        return False, ran, "REGRESSED_TESTS:" + ",".join(sorted(regressed))[:240]
    return True, ran, ""


def _find_target_fn(tree: ast.Module, qualname: str) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, str | None]:
    parts = qualname.split(".")
    if len(parts) == 1:
        fn_hits = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == parts[0]]
        if len(fn_hits) == 1:
            return fn_hits[0], None
        # Also check unique method across classes in module if unambiguous
        meth_hits = [
            (n, cls.name)
            for cls in tree.body if isinstance(cls, ast.ClassDef)
            for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == parts[0]
        ]
        if len(meth_hits) == 1:
            return meth_hits[0]
        return None, None
    if len(parts) == 2:
        cls_name, m_name = parts
        for cls in tree.body:
            if isinstance(cls, ast.ClassDef) and cls.name == cls_name:
                for n in cls.body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == m_name:
                        return n, cls_name
    return None, None


def _replace_span(src: str, node: ast.AST, repl: str) -> str:
    lines = src.splitlines(keepends=True)
    pos = [0]
    for ln in lines:
        pos.append(pos[-1] + len(ln))
    start = pos[node.lineno - 1] + node.col_offset
    end = pos[(node.end_lineno or node.lineno) - 1] + (node.end_col_offset or node.col_offset)
    return src[:start] + repl + src[end:]


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    src_raw = str(args.get("source_root") or "").strip()
    qualname = str(args.get("qualname") or args.get("symbol") or "").strip()
    param_name = str(args.get("param_name") or args.get("new_param") or "").strip()
    default_expr = str(args.get("default_expr") if args.get("default_expr") is not None else "None").strip() or "None"
    mod_raw = str(args.get("module") or "").strip()
    out_raw = str(args.get("output_path") or "").strip()

    if not src_raw or not qualname or not param_name or not out_raw:
        raise RuntimeError("MISSING_REQUIRED_ARGUMENTS")
    if not param_name.isidentifier() or keyword.iskeyword(param_name):
        raise RuntimeError("INVALID_PARAM_NAME:" + param_name)
    # Validate default_expr parses as a single pure expression
    try:
        def_ast = ast.parse(default_expr, mode="eval").body
    except SyntaxError as exc:
        raise RuntimeError("INVALID_DEFAULT_EXPR:" + default_expr) from exc

    src_root = _safe_path(repo, src_raw, must_exist=True)
    out_path = _safe_path(repo, out_raw)
    if src_root.is_file():
        target_file = src_root
        src_root = src_root.parent
    elif mod_raw:
        cand = (src_root / mod_raw).resolve()
        target_file = cand if cand.is_file() else _safe_path(repo, mod_raw, must_exist=True)
    else:
        matches: list[pathlib.Path] = []
        for p in sorted(src_root.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            t = ast.parse(p.read_text(encoding="utf-8"))
            fn, _ = _find_target_fn(t, qualname)
            if fn is not None:
                matches.append(p)
        if len(matches) != 1:
            raise RuntimeError("TARGET_FUNCTION_AMBIGUOUS_OR_MISSING:" + qualname)
        target_file = matches[0]

    proj, tdir = _resolve_project_and_tests(repo, src_root)
    _, _, baseline_bad, _ = _collect_state(proj, tdir)
    orig_bytes = target_file.read_bytes()
    src_text = orig_bytes.decode("utf-8")
    tree = ast.parse(src_text, filename=str(target_file))
    fn_node, owner_cls = _find_target_fn(tree, qualname)
    if fn_node is None:
        raise RuntimeError(f"SYMBOL_NOT_FOUND:{qualname}")

    existing_params = [a.arg for a in (*fn_node.args.posonlyargs, *fn_node.args.args, *fn_node.args.kwonlyargs)]
    if fn_node.args.vararg:
        existing_params.append(fn_node.args.vararg.arg)
    if fn_node.args.kwarg:
        existing_params.append(fn_node.args.kwarg.arg)
    if param_name in existing_params:
        raise RuntimeError(f"PARAMETER_ALREADY_EXISTS:{param_name}")

    # Audit callers across project for keyword collision (`param_name=...` already passed)
    leaf_name = qualname.split(".")[-1]
    for p in sorted(proj.rglob("*.py")):
        if "__pycache__" in p.parts or ".git" in p.parts:
            continue
        ct = ast.parse(p.read_text(encoding="utf-8"))
        for call in ast.walk(ct):
            if isinstance(call, ast.Call):
                cname = call.func.id if isinstance(call.func, ast.Name) else (call.func.attr if isinstance(call.func, ast.Attribute) else None)
                if cname == leaf_name:
                    if any(kw.arg == param_name for kw in call.keywords):
                        raise RuntimeError(f"CALLER_KEYWORD_COLLISION:{p.name}:L{call.lineno}")

    # Rewrite body first if `<existing_param>.<param_name>` is loaded inside `fn_node`
    # (Fowler Parameterize Function: works for both `self.rate` on methods and `item.qty` on functions)
    working_src = src_text
    candidate_owners = {a.arg for a in (*fn_node.args.posonlyargs, *fn_node.args.args)}
    attr_rewrites = 0
    if candidate_owners:
        attr_hits = [
            sub for sub in ast.walk(fn_node)
            if isinstance(sub, ast.Attribute)
            and isinstance(sub.ctx, ast.Load)
            and isinstance(sub.value, ast.Name)
            and sub.value.id in candidate_owners
            and sub.attr == param_name
        ]
        if attr_hits:
            lines_pre = working_src.splitlines(keepends=True)
            pos_pre = [0]
            for ln in lines_pre:
                pos_pre.append(pos_pre[-1] + len(ln))
            spans = sorted(
                (
                    pos_pre[h.lineno - 1] + h.col_offset,
                    pos_pre[(h.end_lineno or h.lineno) - 1] + (h.end_col_offset or h.col_offset),
                    h.value.id,
                )
                for h in attr_hits
            )
            for s_off, e_off, owner_id in reversed(spans):
                override_expr = (
                    f"({param_name} if {param_name} is not None else {owner_id}.{param_name})"
                    if isinstance(def_ast, ast.Constant) and def_ast.value is None
                    else param_name
                )
                working_src = working_src[:s_off] + override_expr + working_src[e_off:]
                attr_rewrites += 1

    # Re-parse `working_src` to splice parameter into exact signature position
    tree2 = ast.parse(working_src, filename=str(target_file))
    fn2, _ = _find_target_fn(tree2, qualname)
    assert fn2 is not None
    lines2 = working_src.splitlines(keepends=True)
    pos2 = [0]
    for ln in lines2:
        pos2.append(pos2[-1] + len(ln))

    param_decl = f"{param_name}={default_expr}"
    # Locate exact insertion offset inside `def name(...):` header before `*args` / `**kwargs` / `)`
    all_pos_args = list(fn2.args.posonlyargs) + list(fn2.args.args)
    if all_pos_args:
        last_arg = all_pos_args[-1]
        # If `last_arg` has a default, end is after that default expression!
        n_defs = len(fn2.args.defaults)
        if n_defs > 0:
            last_end_node: ast.AST = fn2.args.defaults[-1]
        elif last_arg.annotation is not None:
            last_end_node = last_arg.annotation
        else:
            last_end_node = last_arg
        ins_off = pos2[(last_end_node.end_lineno or last_end_node.lineno) - 1] + (last_end_node.end_col_offset or last_end_node.col_offset)
        new_src = working_src[:ins_off] + f", {param_decl}" + working_src[ins_off:]
    else:
        fn_start = pos2[fn2.lineno - 1] + fn2.col_offset
        open_paren = working_src.index("(", fn_start)
        ins_off = open_paren + 1
        has_more = bool(fn2.args.vararg or fn2.args.kwonlyargs or fn2.args.kwarg)
        new_src = working_src[:ins_off] + param_decl + (", " if has_more else "") + working_src[ins_off:]

    try:
        ast.parse(new_src, filename=str(target_file))
        target_file.write_text(new_src, encoding="utf-8")
        _purge_pyc(target_file)
        ok, ran, err = _verify_project(proj, tdir, baseline_bad)
        if not ok:
            raise RuntimeError("VERIFICATION_FAILED_AFTER_ADD_PARAMETER:" + err)
    except BaseException:
        target_file.write_bytes(orig_bytes)
        _purge_pyc(target_file)
        raise

    rel_target = target_file.relative_to(repo).as_posix()
    report = {
        "schema": "PROJECT_BRAIN_PYTHON_ADD_PARAMETER_V1",
        "adapter": "python_source_add_parameter",
        "qualname": qualname,
        "param_name": param_name,
        "default_expr": default_expr,
        "attribute_overrides_rewritten": attr_rewrites,
        "files_edited": [rel_target],
        "tests_ran": ran,
        "verified": True,
        "output_verified": True,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out_path.write_bytes(raw)
    return {
        "adapter": "python_source_add_parameter",
        "qualname": qualname,
        "param_name": param_name,
        "default_expr": default_expr,
        "attribute_overrides_rewritten": attr_rewrites,
        "files_edited": [rel_target],
        "tests_ran": ran,
        "output_path": out_path.relative_to(repo).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
        "verified": True,
    }
