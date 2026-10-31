"""Cross-file Python symbol relocation (`python.refactor.move_symbol.v1`).

Relocates a top-level function or class (plus any unshared intra-module private
helper dependencies) from `source_module` to `target_module` under `source_root`,
rewrites all sibling caller imports (`from <src> import <sym>`, `<src>.<sym>`)
and `__all__` exports, purges stale `.pyc`, verifies every production module +
`unittest` discovery in a clean `-B` child process, and rolls back byte-for-byte
on any failure.
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


def _modname_rel(src_root: pathlib.Path, mod_path: pathlib.Path) -> str:
    rel = mod_path.relative_to(src_root).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    return ".".join(parts)


def _resolve_project_and_tests(repo: pathlib.Path, src_root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    proj = src_root
    while (proj / "__init__.py").is_file() and proj != repo and repo in proj.parents:
        proj = proj.parent
    if proj == src_root and (src_root.parent / "tests").is_dir() and src_root.parent != repo and repo in src_root.parent.parents:
        proj = src_root.parent
    tdir = src_root / "tests" if (src_root / "tests").is_dir() else (proj / "tests" if (proj / "tests").is_dir() else proj)
    return proj, tdir


def _verify_project(proj: pathlib.Path, tdir: pathlib.Path) -> tuple[bool, int, str]:
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
        "import importlib, json, pathlib, sys, unittest\n"
        "proj = pathlib.Path(sys.argv[1]).resolve()\n"
        "tdir = pathlib.Path(sys.argv[2]).resolve()\n"
        "mods = json.loads(sys.argv[3])\n"
        "sys.path.insert(0, str(proj))\n"
        "for m in mods:\n"
        "    importlib.import_module(m)\n"
        "ran = 0\n"
        "if tdir.is_dir():\n"
        "    top = str(proj) if (tdir == proj or (tdir / '__init__.py').is_file()) else str(tdir)\n"
        "    suite = unittest.TestLoader().discover(start_dir=str(tdir), top_level_dir=top)\n"
        "    res = unittest.TestResult()\n"
        "    suite.run(res)\n"
        "    ran = res.testsRun\n"
        "    if res.failures or res.errors:\n"
        "        print(json.dumps({'ok': False, 'ran': ran, 'err': str((res.failures + res.errors)[0][1])[-240:]}))\n"
        "        raise SystemExit(1)\n"
        "print(json.dumps({'ok': True, 'ran': ran}))\n"
    )
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env["PYTHONPATH"] = str(proj) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(
        [sys.executable, "-B", "-c", runner, str(proj), str(tdir), json.dumps(prod_mods)],
        cwd=str(proj),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return False, 0, (proc.stderr or proc.stdout)[-300:]
    info = json.loads(proc.stdout.strip().splitlines()[-1])
    return bool(info.get("ok")), int(info.get("ran") or 0), ""


def _resolve_module_arg(src_root: pathlib.Path, repo: pathlib.Path, raw: str, *, must_exist: bool) -> pathlib.Path:
    sr_rel = src_root.relative_to(repo).as_posix().rstrip("/")
    if raw.startswith(sr_rel + "/"):
        cand2 = _safe_path(repo, raw, must_exist=must_exist)
        if cand2 != src_root and src_root not in cand2.parents:
            raise RuntimeError("MODULE_OUTSIDE_SOURCE_ROOT:" + raw)
        return cand2
    cand = (src_root / raw).resolve()
    if cand != repo and repo in cand.parents and (cand.exists() or not must_exist):
        if (cand == src_root or src_root in cand.parents) and raw.endswith(".py"):
            return cand
    cand2 = _safe_path(repo, raw, must_exist=must_exist)
    if cand2 != src_root and src_root not in cand2.parents:
        raise RuntimeError("MODULE_OUTSIDE_SOURCE_ROOT:" + raw)
    return cand2


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    src_raw = str(args.get("source_root") or "").strip()
    sym = str(args.get("symbol") or args.get("qualname") or "").strip()
    src_mod_raw = str(args.get("source_module") or args.get("module") or "").strip()
    dst_mod_raw = str(args.get("target_module") or args.get("to_module") or "").strip()
    out_raw = str(args.get("output_path") or "").strip()

    if not src_raw or not sym or not dst_mod_raw or not out_raw:
        raise RuntimeError("MISSING_REQUIRED_ARGUMENTS")
    if not sym.isidentifier() or keyword.iskeyword(sym):
        raise RuntimeError("INVALID_SYMBOL_IDENTIFIER:" + sym)

    src_root = _safe_path(repo, src_raw, must_exist=True)
    if not src_root.is_dir():
        raise RuntimeError("SOURCE_ROOT_NOT_DIRECTORY")
    out_path = _safe_path(repo, out_raw)
    proj, tdir = _resolve_project_and_tests(repo, src_root)

    if not dst_mod_raw.endswith(".py"):
        dst_mod_raw = dst_mod_raw.replace(".", "/") + ".py"
    dst_file = _resolve_module_arg(src_root, repo, dst_mod_raw, must_exist=False)

    # Locate source_module automatically under src_root if omitted
    if src_mod_raw:
        if not src_mod_raw.endswith(".py"):
            src_mod_raw = src_mod_raw.replace(".", "/") + ".py"
        src_file = _resolve_module_arg(src_root, repo, src_mod_raw, must_exist=True)
    else:
        hits: list[pathlib.Path] = []
        for p in sorted(src_root.rglob("*.py")):
            if "__pycache__" in p.parts or p == dst_file:
                continue
            t = ast.parse(p.read_text(encoding="utf-8"))
            if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == sym for n in t.body):
                hits.append(p)
        if len(hits) != 1:
            raise RuntimeError("SOURCE_SYMBOL_AMBIGUOUS_OR_MISSING:" + sym)
        src_file = hits[0]

    if src_file == dst_file:
        raise RuntimeError("SOURCE_AND_TARGET_IDENTICAL")

    all_py = sorted(p for p in proj.rglob("*.py") if "__pycache__" not in p.parts and ".git" not in p.parts)
    snap: dict[pathlib.Path, bytes | None] = {p: p.read_bytes() for p in all_py}
    if dst_file not in snap:
        snap[dst_file] = dst_file.read_bytes() if dst_file.exists() else None

    src_text = src_file.read_text(encoding="utf-8")
    src_tree = ast.parse(src_text, filename=str(src_file))
    top_defs = {
        n.name: n
        for n in src_tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    if sym not in top_defs:
        raise RuntimeError(f"SYMBOL_NOT_FOUND:{sym}")

    # Check destination collision
    dst_existing_text = dst_file.read_text(encoding="utf-8") if dst_file.exists() else ""
    dst_tree = ast.parse(dst_existing_text, filename=str(dst_file)) if dst_existing_text.strip() else ast.Module(body=[], type_ignores=[])
    dst_defs = {
        n.name for n in dst_tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    if sym in dst_defs:
        raise RuntimeError(f"TARGET_SYMBOL_COLLISION:{sym}")

    # Transitive closure of intra-module private helpers needed ONLY by `sym`
    move_names: list[str] = [sym]
    remaining_defs = set(top_defs) - {sym}
    changed_closure = True
    while changed_closure:
        changed_closure = False
        used_by_moved: set[str] = set()
        for nm in move_names:
            for sub in ast.walk(top_defs[nm]):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    used_by_moved.add(sub.id)
        used_by_staying: set[str] = set()
        for st in src_tree.body:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and st.name in move_names:
                continue
            for sub in ast.walk(st):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    used_by_staying.add(sub.id)
        for cand_dep in sorted(used_by_moved & remaining_defs):
            if cand_dep.startswith("_") and cand_dep not in used_by_staying and cand_dep not in dst_defs:
                move_names.append(cand_dep)
                remaining_defs.remove(cand_dep)
                changed_closure = True

    move_nodes = sorted((top_defs[nm] for nm in move_names), key=lambda n: n.lineno)
    moved_load_names = {
        sub.id
        for nd in move_nodes
        for sub in ast.walk(nd)
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load)
    }

    # Collect imports from src_tree needed by moved definitions
    src_lines = src_text.splitlines(keepends=True)
    needed_import_lines: list[str] = []
    for st in src_tree.body:
        if isinstance(st, ast.Import):
            if any((a.asname or a.name.split(".")[0]) in moved_load_names for a in st.names):
                s = st.lineno - 1
                e = st.end_lineno or st.lineno
                needed_import_lines.append("".join(src_lines[s:e]))
        elif isinstance(st, ast.ImportFrom):
            if any((a.asname or a.name) in moved_load_names for a in st.names):
                s = st.lineno - 1
                e = st.end_lineno or st.lineno
                needed_import_lines.append("".join(src_lines[s:e]))

    # Also check if moved code calls staying symbols in src_file -> import them in dst_file!
    src_dotted = _modname_rel(proj, src_file)
    dst_dotted = _modname_rel(proj, dst_file)
    staying_needed = sorted(moved_load_names & remaining_defs)
    if staying_needed:
        needed_import_lines.append(f"from {src_dotted} import {', '.join(staying_needed)}\n")

    # Check if staying code in src_file still calls `sym` -> add `from dst import sym` ONLY if needed inside src_file functions (avoiding re-exporting blindly if moved away, or importing locally if used)
    staying_uses_sym = False
    for st in src_tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and st.name in move_names:
            continue
        if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in st.targets):
            continue
        for sub in ast.walk(st):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id == sym:
                staying_uses_sym = True

    moved_chunks: list[str] = []
    remove_spans: list[tuple[int, int]] = []
    for nd in move_nodes:
        s_line = (nd.decorator_list[0].lineno if nd.decorator_list else nd.lineno) - 1
        e_line = nd.end_lineno or nd.lineno
        chunk = "".join(src_lines[s_line:e_line])
        if not chunk.endswith("\n"):
            chunk += "\n"
        moved_chunks.append(chunk)
        remove_spans.append((s_line, e_line))

    # Remove moved definitions (and update `__all__` if present) in `src_file`
    new_src_lines = list(src_lines)
    for st in src_tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) and st.targets[0].id == "__all__" and isinstance(st.value, (ast.List, ast.Tuple)):
            kept_elts = [
                el.value for el in st.value.elts
                if isinstance(el, ast.Constant) and isinstance(el.value, str) and el.value not in move_names
            ]
            s_l = st.lineno - 1
            e_l = st.end_lineno or st.lineno
            remove_spans.append((s_l, e_l))
            # Replaced below
            new_src_lines[s_l:e_l] = [f"__all__ = {kept_elts!r}\n"]
            remove_spans.pop()

    for s_l, e_l in sorted(remove_spans, key=lambda x: x[0], reverse=True):
        del new_src_lines[s_l:e_l]
    if staying_uses_sym:
        # Insert import after __future__ / module docstring
        ins_at = 0
        while ins_at < len(new_src_lines) and (new_src_lines[ins_at].startswith("#") or "from __future__" in new_src_lines[ins_at] or not new_src_lines[ins_at].strip()):
            ins_at += 1
        new_src_lines.insert(ins_at, f"from {dst_dotted} import {sym}\n")
    if not "".join(new_src_lines).strip():
        new_src_lines = ["# Module relocated symbols\n"]

    # Build new `dst_file` text (first removing any stale import of `sym` from `src_file`)
    src_short = src_file.stem
    dst_short = dst_file.stem
    src_rel_mod = _modname_rel(src_root, src_file)
    dst_rel_mod = _modname_rel(src_root, dst_file)
    existing_dst_lines = dst_existing_text.splitlines(keepends=True)
    if existing_dst_lines:
        dst_repls: list[tuple[int, int, list[str]]] = []
        for st in dst_tree.body:
            if isinstance(st, ast.ImportFrom):
                mname = st.module or ""
                matches_src = (
                    mname in {src_dotted, src_rel_mod}
                    or (st.level >= 1 and (mname == src_short or mname.endswith("." + src_short)))
                    or (mname == src_short and src_file.parent == dst_file.parent)
                )
                if matches_src and any(a.name in set(move_names) for a in st.names):
                    other_a = [a for a in st.names if a.name not in set(move_names)]
                    s_i = st.lineno - 1
                    e_i = st.end_lineno or st.lineno
                    if other_a:
                        kept_s = ", ".join(f"{a.name} as {a.asname}" if a.asname else a.name for a in other_a)
                        dots = "." * (st.level or 0)
                        dst_repls.append((s_i, e_i, [f"from {dots}{mname} import {kept_s}\n"]))
                    else:
                        dst_repls.append((s_i, e_i, []))
        for s_i, e_i, r_lines in reversed(dst_repls):
            existing_dst_lines[s_i:e_i] = r_lines
        dst_existing_text = "".join(existing_dst_lines)
        dst_tree = ast.parse(dst_existing_text, filename=str(dst_file)) if dst_existing_text.strip() else ast.Module(body=[], type_ignores=[])
    dst_header_imps = [imp for imp in needed_import_lines if imp.strip() not in dst_existing_text]
    if existing_dst_lines:
        ins_at = 0
        if dst_tree.body and isinstance(dst_tree.body[0], ast.Expr) and isinstance(dst_tree.body[0].value, ast.Constant) and isinstance(dst_tree.body[0].value.value, str):
            ins_at = dst_tree.body[0].end_lineno or 1
        while ins_at < len(existing_dst_lines) and "from __future__" in existing_dst_lines[ins_at]:
            ins_at += 1
        new_dst_text = (
            "".join(existing_dst_lines[:ins_at])
            + "".join(dst_header_imps)
            + "".join(existing_dst_lines[ins_at:])
            + ("\n" if not dst_existing_text.endswith("\n") else "")
            + "\n"
            + "\n".join(c.rstrip("\n") for c in moved_chunks)
            + "\n"
        )
    else:
        new_dst_text = "".join(dst_header_imps) + ("\n" if dst_header_imps else "") + "\n\n".join(c.rstrip("\n") for c in moved_chunks) + "\n"

    # Rewrite imports across all sibling/test `.py` files in `proj`
    planned_writes: dict[pathlib.Path, str] = {
        src_file: "".join(new_src_lines),
        dst_file: new_dst_text,
    }

    for p in all_py:
        if p in (src_file, dst_file):
            continue
        txt = p.read_text(encoding="utf-8")
        ptree = ast.parse(txt, filename=str(p))
        plines = txt.splitlines(keepends=True)
        line_repls: list[tuple[int, int, str]] = []
        mod_alias_hits: set[str] = set()

        for st in ptree.body:
            if isinstance(st, ast.ImportFrom):
                mname = st.module or ""
                matches_src = (
                    mname in {src_dotted, src_rel_mod}
                    or (st.level >= 1 and (mname == src_short or mname.endswith("." + src_short)))
                    or (mname == src_short and src_file.parent == p.parent)
                )
                if matches_src and any(a.name == sym for a in st.names):
                    other_aliases = [a for a in st.names if a.name != sym]
                    sym_alias = next(a for a in st.names if a.name == sym)
                    if st.level >= 1:
                        dots = "." * st.level
                        new_mod_ref = f"{dots}{dst_rel_mod}" if "." in dst_rel_mod else f"{dots}{dst_short}"
                    elif mname == src_short:
                        new_mod_ref = dst_short
                    elif mname == src_rel_mod:
                        new_mod_ref = dst_rel_mod
                    else:
                        new_mod_ref = dst_dotted
                    sym_str = f"{sym} as {sym_alias.asname}" if sym_alias.asname else sym
                    new_imp = f"from {new_mod_ref} import {sym_str}\n"
                    if other_aliases:
                        kept_str = ", ".join(f"{a.name} as {a.asname}" if a.asname else a.name for a in other_aliases)
                        dots = "." * (st.level or 0)
                        orig_ref = f"{dots}{mname}"
                        repl = f"from {orig_ref} import {kept_str}\n{new_imp}"
                    else:
                        repl = new_imp
                    line_repls.append((st.lineno - 1, st.end_lineno or st.lineno, repl))
                elif st.level >= 1 and mname == "" and any(a.name == src_short for a in st.names):
                    for a in st.names:
                        if a.name == src_short:
                            mod_alias_hits.add(a.asname or a.name)
            elif isinstance(st, ast.Import):
                for a in st.names:
                    if a.name in {src_dotted, src_rel_mod, src_short}:
                        mod_alias_hits.add(a.asname or a.name.split(".")[-1])

        new_txt = txt
        if line_repls:
            work_lines = list(plines)
            for s_i, e_i, r_txt in sorted(line_repls, key=lambda x: x[0], reverse=True):
                work_lines[s_i:e_i] = [r_txt]
            new_txt = "".join(work_lines)

        if mod_alias_hits:
            for alias_nm in sorted(mod_alias_hits):
                if f"{alias_nm}.{sym}" in new_txt:
                    new_txt = f"from {dst_dotted} import {sym} as _moved_{sym}\n" + new_txt.replace(f"{alias_nm}.{sym}", f"_moved_{sym}")

        if new_txt != txt:
            planned_writes[p] = new_txt

    try:
        for p, content in planned_writes.items():
            ast.parse(content, filename=str(p))
        for p, content in planned_writes.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            _purge_pyc(p)
        ok, ran, err = _verify_project(proj, tdir)
        if not ok:
            raise RuntimeError("VERIFICATION_FAILED_AFTER_MOVE:" + err)
    except BaseException:
        for p, orig in snap.items():
            if orig is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(orig)
            _purge_pyc(p)
        raise

    edited_rels = sorted(p.relative_to(repo).as_posix() for p in planned_writes)
    report = {
        "schema": "PROJECT_BRAIN_PYTHON_MOVE_SYMBOL_V1",
        "adapter": "python_source_move_symbol",
        "symbol": sym,
        "moved_symbols": move_names,
        "source_module": src_file.relative_to(repo).as_posix(),
        "target_module": dst_file.relative_to(repo).as_posix(),
        "files_edited": edited_rels,
        "tests_ran": ran,
        "verified": True,
        "output_verified": True,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out_path.write_bytes(raw)
    return {
        "adapter": "python_source_move_symbol",
        "symbol": sym,
        "moved_symbols": move_names,
        "source_module": report["source_module"],
        "target_module": report["target_module"],
        "files_edited": edited_rels,
        "tests_ran": ran,
        "output_path": out_path.relative_to(repo).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
        "verified": True,
    }
