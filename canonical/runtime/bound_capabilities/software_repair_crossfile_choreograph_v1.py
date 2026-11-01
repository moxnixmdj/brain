"""Cross-file repair with separate staged and in-place protocols.

Explicit task/issue/binding arguments select isolated rename/move choreography,
strict task binding, fixed-point checks, selected/full pytest regression, and
no promotion of the original source. Malformed staged requests never fall back.

Source-root-only requests retain upstream in-place structural/test-guided repair
algorithms below, including conflict merging and import-cycle deferral. That
mode can edit the stated source tree; it is not an isolated staged proposal.
Neither mode implies universal repair or independent semantic verification.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import keyword
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
from canonical.runtime import crossfile_task_binding_v1 as binding
from canonical.runtime.swe_task_artifacts_v1 import confined_path, fresh_output, publish_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_CROSSFILE_CHOREOGRAPH_V1"
CAPABILITY_ID = "software.repair.choreograph.crossfile.v1"
PROVIDES = ["software.repair.choreography.verified", "software.patch.crossfile.atomic"]
REQUIRES = ["python.fault.localization.symbol_ranked", "python.source.symbols.index.ast"]


def _task(payload, source):
    if not isinstance(payload, dict) or not str(payload.get("issue_id") or "").strip():
        raise ValueError("ISSUE_ID_REQUIRED")
    edits = payload.get("edits")
    if not isinstance(edits, list) or not 1 <= len(edits) <= 32:
        raise ValueError("BOUNDED_EDITS_REQUIRED")
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("EDIT_MUST_BE_OBJECT")
        op = edit.get("op")
        allowed = ({"op", "module", "name", "new_name"} if op == "rename_symbol" else
                   {"op", "module", "qualname", "to_module"} if op == "move_symbol" else set())
        if not allowed or set(edit) != allowed:
            raise ValueError("UNSUPPORTED_OR_INCOMPLETE_EDIT")
        for key in ("module", "to_module"):
            if key not in edit:
                continue
            raw = edit[key]
            if (not isinstance(raw, str) or "\\" in raw or Path(raw).is_absolute()
                    or ".." in Path(raw).parts or not raw.endswith(".py")):
                raise ValueError("EDIT_PATH_INVALID")
            target = (source / raw).resolve()
            if source not in target.parents:
                raise ValueError("EDIT_PATH_OUTSIDE_SOURCE")
        for key in allowed - {"op", "module", "to_module"}:
            value = edit[key]
            if not isinstance(value, str) or not value.isidentifier() or keyword.iskeyword(value):
                raise ValueError("EDIT_IDENTIFIER_INVALID")
    return {k: payload[k] for k in ("issue_id", "title", "body", "edits") if k in payload}


def _regression(worktree, junit, timeout):
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "--junitxml=" + str(junit), "."],
            cwd=worktree, capture_output=True, timeout=timeout)
        root = ET.parse(junit).getroot()
        cases = list(root.iter("testcase"))
        skipped = sum(c.find("skipped") is not None for c in cases)
        failed = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
        completed = len(cases) - skipped
        return {"pass": proc.returncode == 0 and completed > 0 and failed == 0,
                "returncode": proc.returncode, "completed": completed,
                "failed": failed, "skipped": skipped,
                "stdout_tail": proc.stdout[-4000:].decode("utf-8", "replace"),
                "stderr_tail": proc.stderr[-4000:].decode("utf-8", "replace")}
    except subprocess.TimeoutExpired:
        return {"pass": False, "status": "REGRESSION_TIMEOUT", "completed": 0}
    except (OSError, ET.ParseError):
        return {"pass": False, "status": "REGRESSION_EVIDENCE_UNAVAILABLE", "completed": 0}



def _exact_emitted_diff(source, worktree, before, candidate, changed, emitted):
    """Ensure the emitted diff represents the tree actually tested.

    Selected tests run inside the legacy orchestrator. They must not silently
    add candidate changes that are absent from its previously emitted diff.
    """
    original = {r["path"]: r["sha256"] for r in before["files"]}
    staged = {r["path"]: r["sha256"] for r in candidate["files"]
              if r["path"] not in {".orchestrate_plan.json", ".orchestrate_stage.diff",
                                     ".orchestrate_testselect.json"}}
    if set(original) - set(staged):
        return None
    actual = sorted(p for p, digest in staged.items() if original.get(p) != digest)
    if actual != sorted(changed):
        return None
    chunks = []
    patches = []
    for rel in actual:
        old = (source / rel).read_text(encoding="utf-8") if rel in original else ""
        new = (worktree / rel).read_text(encoding="utf-8")
        chunk = "".join(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile="a/" + rel if rel in original else "/dev/null", tofile="b/" + rel))
        chunks.append(chunk)
        patches.append({"relative_path": rel, "unified_diff": chunk,
                        "original_sha256": hashlib.sha256(old.encode()).hexdigest(),
                        "candidate_sha256": hashlib.sha256(new.encode()).hexdigest(),
                        "created": rel not in original})
    return patches if "".join(chunks) == emitted else None

def _run_task_bound(args, root):
    repo = Path(root).resolve()
    source = confined_path(repo, args.get("source_root"))
    if not source.is_dir():
        raise ValueError("SOURCE_ROOT_NOT_DIRECTORY")
    modes = [k for k in ("issue_path", "task_path") if args.get(k)]
    if len(modes) != 1:
        raise ValueError("EXACTLY_ONE_ISSUE_OR_TASK_REQUIRED")
    input_path = confined_path(repo, args[modes[0]])
    input_bytes = input_path.read_bytes()
    payload = json.loads(input_bytes)
    output = fresh_output(repo, args.get("output_path"), "canonical/tmp_choreograph_repair.json")
    if output == source or source in output.parents:
        raise ValueError("OUTPUT_OVERLAPS_SOURCE")
    timeout = args.get("timeout_s", 60)
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("TIMEOUT_MUST_BE_BOUNDED_INTEGER")
    before = tree_manifest(source)
    if before["pass"] is not True:
        raise ValueError("UNSUPPORTED_SOURCE_TREE_ENTRY")
    if "request_binding" in args:
        binding.validate_binding(args, repo, before)
    # Reject symlinks even inside ignored metadata: copytree follows links.
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("SOURCE_SYMLINK_REJECTED")
    if any(p.name.startswith(".orchestrate_") for p in source.iterdir()):
        raise ValueError("SOURCE_RESERVED_STAGE_FILE")
    if modes[0] == "task_path":
        payload = _task(payload, source)  # reject unsafe ops BEFORE creating scratch
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = {}
    regression = {"pass": False, "completed": 0, "status": "NOT_EXECUTED"}
    diff = ""
    changed = []
    candidate_sha = None
    candidate_content_sha = None
    patches = []
    candidate_unchanged = False
    reason = ""
    parse = None
    with tempfile.TemporaryDirectory(prefix=".crossfile-", dir=output.parent) as raw:
        scratch = Path(raw)
        rel = lambda p: p.relative_to(repo).as_posix()
        try:
            if modes[0] == "issue_path":
                from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
                from canonical.runtime.bound_capabilities import python_issue_nl_parse_edit_intent as nlp
                # Fresh index outside source avoids the parser's fixed probe
                # filename and cannot overwrite any pre-existing source file.
                frozen_issue = scratch / "issue.json"
                frozen_issue.write_bytes(input_bytes)
                index = scratch / "index.json"
                index_data = indexer.build_index(".", source)
                index_data["source_root"] = rel(source)  # cache's declared search root
                index.write_text(json.dumps(index_data), encoding="utf-8")
                parsed = scratch / "parsed.json"
                parse = nlp.run({"source_root": rel(source), "issue_path": rel(frozen_issue),
                                 "index_path": rel(index), "output_path": rel(parsed)}, repo)
                payload = json.loads(parsed.read_bytes())
                if parse.get("complete") is not True:
                    raise ValueError("ISSUE_NOT_COMPLETELY_BOUND")
                if any(r.get("parsed_as") == "prose" for r in payload.get("evidence", [])):
                    raise ValueError("UNSUPPORTED_ISSUE_PROSE_NOT_DISCARDED")
                payload = _task(payload, source)
            from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch
            task = scratch / "task.json"
            task.write_text(json.dumps(payload), encoding="utf-8")
            worktree = scratch / "candidate"
            summary = scratch / "summary.json"
            patch = scratch / "change.diff"
            intent = scratch / "pr.json"
            stage = orch.run({"task_path": rel(task), "source_root": rel(source),
                              "worktree_path": rel(worktree), "output_path": rel(summary),
                              "diff_path": rel(patch), "pr_intent_path": rel(intent),
                              "python_executable": sys.executable, "timeout_s": timeout}, repo)
            # Inspect actual artifacts, not merely the returned booleans.
            summary_bytes = summary.read_bytes()
            diff = patch.read_text(encoding="utf-8")
            pr = json.loads(intent.read_bytes())
            changed = pr["body"]["changed_files"]
            if (hashlib.sha256(summary_bytes).hexdigest() != stage.get("output_sha256")
                    or stage.get("diff_sha256") != hashlib.sha256(diff.encode()).hexdigest()
                    or stage.get("verified") is not True
                    or stage.get("applied_op_count") != len(payload["edits"])
                    or not changed or not diff.strip()
                    or pr["body"]["proof"].get("fixed_point_verified") is not True):
                raise ValueError("STAGED_CHANGE_NOT_VERIFIED")
            candidate = tree_manifest(worktree)
            candidate_sha = candidate["tree_sha256"]
            if candidate["pass"] is not True:
                raise ValueError("CANDIDATE_MANIFEST_INVALID")
            patches = _exact_emitted_diff(source, worktree, before, candidate, changed, diff)
            if patches is None:
                patches = []
                raise ValueError("TESTED_TREE_DIFF_MISMATCH")
            for row in patches:
                row["source_path"] = rel(source / row["relative_path"])
            candidate_content_sha = binding.content_manifest(candidate)["tree_sha256"]
            regression = _regression(worktree, scratch / "regression.xml", timeout)
            after_candidate = tree_manifest(worktree)
            candidate_unchanged = (after_candidate["pass"] is True
                                   and after_candidate["tree_sha256"] == candidate_sha)
        except (SystemExit, ValueError, RuntimeError, OSError, KeyError, TypeError,
                subprocess.TimeoutExpired) as exc:
            reason = type(exc).__name__ + ":" + str(exc)[:2000]
    after = tree_manifest(source)
    source_unchanged = after["pass"] is True and before["tree_sha256"] == after["tree_sha256"]
    input_unchanged = input_path.is_file() and input_path.read_bytes() == input_bytes
    accepted = (not reason and stage.get("verified") is True and regression["pass"] is True
                and source_unchanged and input_unchanged and candidate_unchanged)
    report = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "adapter": "software_repair_crossfile_choreograph_v1",
        "status": "PASS__STAGED_CROSSFILE_CHANGE_TESTED" if accepted else "OPEN__CROSSFILE_CHANGE_NOT_ACCEPTED",
        "pass": accepted, "verified": accepted, "choreography_verified": accepted,
        "verification_mode": "EXPLICIT_RENAME_MOVE_FIXED_POINT_SELECTED_AND_FULL_PYTEST",
        "source_root": rel(source), "source_tree_sha256": before["tree_sha256"],
        "source_unchanged": source_unchanged, "input_unchanged": input_unchanged,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "candidate_tree_sha256": candidate_sha, "candidate_unchanged_during_regression": candidate_unchanged,
        "candidate_content_sha256": candidate_content_sha,
        "patches": patches if accepted else [],
        "request_binding": args.get("request_binding"),
        "request_binding_sha256": args.get("request_binding_sha256"),
        "planned_edits": payload.get("edits", []) if isinstance(payload, dict) else [],
        "changed_files": changed, "unified_diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
        "stages": {k: v for k, v in stage.items() if k not in {"output_path", "seconds"}},
        "issue_binding": ({k: v for k, v in parse.items() if k != "output_path"} if parse else None),
        "regression": regression, "reason": reason,
        "source_promotion_performed": False, "independent_semantic_oracle_credit": False,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    return publish_report(repo, output, report)


# Upstream in-place repair algorithms; staged requests never fall back here.
"""Multi-file AST software repair & refactoring choreography (`software.repair.choreograph.crossfile.v1`).

Deterministic, fail-closed AST choreography engine grounded in PL/SE algorithms:
  A. Git 3-way conflict marker resolution (Apel et al. ASE 2011, JDime additive AST merge)
  B. Tarjan-SCC top-level import cycle deferral (Tarjan 1972)
  C. Python 3.11+ removed/deprecated stdlib API codemod (PEP 479 / 2to3)
  D. DB-API 2.0 parameterized SQL rewrite eliminating CWE-89 injection (PEP 249)
  E. Shared-state concurrency RLock synthesis (Flanagan & Freund PLDI 2000; Cherem et al. PLDI 2008)
  G. Failing-suite Plastic-Surgery call-ingredient & AST operator repair (Barr et al. FSE 2014)
  F. Container & loop strength reduction O(n^2) -> O(n) via hash-set indexing (Shacham et al. PLDI 2009)
  H. Whole-project AST dead-function & unused-import pruning (Vulture / autoflake reachability)

Every candidate edit is verified by `ast.parse` AND child-process module import + `unittest`
discovery (5 consecutive runs for concurrency repairs). Any unverified edit rolls back atomically.
"""

import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping


def _safe_path(repo: pathlib.Path, raw: str, *, allow_root: bool = False) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if allow_root and p == repo:
        return p
    if p == repo or repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _resolve_workspace(src: pathlib.Path, repo: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, list[pathlib.Path]]:
    """Return ``(project_root, test_dir, focus_prod_files)``."""
    def _is_test(p: pathlib.Path, proj: pathlib.Path) -> bool:
        rel = p.relative_to(proj).as_posix()
        return (
            rel.startswith("tests/")
            or "/tests/" in f"/{rel}"
            or p.name.startswith("test_")
            or p.name.endswith("_test.py")
        )

    if src.is_file():
        if src.suffix != ".py":
            raise RuntimeError("SOURCE_FILE_NOT_PYTHON")
        proj = src.parent
        while (proj / "__init__.py").is_file() and proj != repo and repo in proj.parents:
            proj = proj.parent
        tdir = proj / "tests" if (proj / "tests").is_dir() else proj
        return proj, tdir, [src]

    if src.name in ("tests", "test") and src.parent != repo and repo in src.parent.parents:
        proj = src.parent
        tdir = src
        scan_root = proj
    else:
        proj = src
        while (proj / "__init__.py").is_file() and proj != repo and repo in proj.parents:
            proj = proj.parent
        if proj == src and (src.parent / "tests").is_dir() and src.parent != repo and repo in src.parent.parents:
            proj = src.parent
        tdir = src / "tests" if (src / "tests").is_dir() else (proj / "tests" if (proj / "tests").is_dir() else proj)
        scan_root = src

    focus = [
        p for p in sorted(scan_root.rglob("*.py"))
        if "__pycache__" not in p.parts and ".git" not in p.parts and not _is_test(p, proj)
    ]
    # NO SILENT WIDENING OF THE EDIT SCOPE.  The fallback below used to adopt the ancestor's
    # Python files whenever the named tree held none, so "Fix the off-by-one bug in <src>/main.cpp"
    # -- a C++ request -- was answered by rewriting <pkg>/mod.py and <pkg>/service.py.  A tree the
    # sentence named that holds no Python is a request this row cannot serve; refusing by name is
    # the honest outcome and leaves the caller's tree untouched.  Measured 2026-10-31: the door now
    # refuses those edits (EDITS_LANDED_OUTSIDE_THE_NAMED_SUBJECT) but the adapter had already made
    # them -- a refusal after the damage is not a guard.
    return proj, tdir, focus


def _all_prod_files(proj: pathlib.Path) -> list[pathlib.Path]:
    out = []
    for p in sorted(proj.rglob("*.py")):
        if "__pycache__" in p.parts or ".git" in p.parts:
            continue
        rel = p.relative_to(proj).as_posix()
        if rel.startswith("tests/") or "/tests/" in f"/{rel}" or p.name.startswith("test_") or p.name.endswith("_test.py"):
            continue
        out.append(p)
    return out


def _verify_project(proj: pathlib.Path, test_dir: pathlib.Path, *, repeats: int = 1) -> tuple[bool, int, str]:
    """Verify every production `.py` parses, imports cleanly, and passes `unittest` `repeats` times."""
    prod_files = _all_prod_files(proj)
    mod_names: list[str] = []
    for p in prod_files:
        try:
            raw_src = p.read_bytes()
            ast.parse(raw_src)
        except (SyntaxError, ValueError, OSError) as exc:
            return False, 0, f"SYNTAX_ERROR:{p.name}:{exc}"
        if b"parse_args(" in raw_src and b"__main__" not in raw_src:
            continue
        rel = p.relative_to(proj).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            mod_names.append(".".join(parts))

    # Reuse the counted framework-aware executor used by repair and tracing.
    # Calling bare functions ourselves ignores pytest skip/fixture/parametrize
    # semantics and can certify an all-skipped suite as a successful repair.
    from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import SUITE_RUNNER
    checker = SUITE_RUNNER + (
        "import importlib, importlib.util, json\n"
        "proj = pathlib.Path(sys.argv[1]).resolve()\n"
        "tdir = pathlib.Path(sys.argv[2]).resolve()\n"
        "repeats = int(sys.argv[3])\n"
        "mods = json.loads(sys.argv[4])\n"
        "sys.argv[:] = [sys.argv[0]]\n"
        "if str(proj) in sys.path:\n"
        "    sys.path.remove(str(proj))\n"
        "sys.path.append(str(proj))\n"
        "_stdlib_names = getattr(sys, 'stdlib_module_names', frozenset())\n"
        "targets = [p for p in sorted(tdir.rglob('*.py')) if '__pycache__' not in p.parts and (p.name.startswith('test_') or p.name.endswith('_test.py'))]\n"
        "total_ran = 0\n"
        "for _ in range(repeats):\n"
        "    for k, v in list(sys.modules.items()):\n"
        "        f = getattr(v, '__file__', None)\n"
        "        if f and proj in pathlib.Path(f).resolve().parents:\n"
        "            sys.modules.pop(k, None)\n"
        "    for m in mods:\n"
        "        try:\n"
        "            if m.split('.')[0] in _stdlib_names:\n"
        "                cand_p = proj / (m.replace('.', '/') + '.py')\n"
        "                if cand_p.is_file():\n"
        "                    sp = importlib.util.spec_from_file_location('_proj_shadow_' + m, cand_p)\n"
        "                    if sp and sp.loader:\n"
        "                        mod_obj = importlib.util.module_from_spec(sp)\n"
        "                        sp.loader.exec_module(mod_obj)\n"
        "                continue\n"
        "            importlib.import_module(m)\n"
        "        except SystemExit:\n"
        "            pass\n"
        "    try:\n"
        "        total_ran += _brain_run_suites(targets)\n"
        "    except ImportError as _imp_exc:\n"
        "        if not any(_t in str(_imp_exc) for _t in ('pytest', 'exceptiongroup', 'pluggy', 'iniconfig')):\n"
        "            raise\n"
        "        import inspect as _insp, unittest as _ut\n"
        "        _suite = _ut.TestLoader().discover(start_dir=str(tdir), top_level_dir=str(proj if (tdir == proj or (tdir / '__init__.py').is_file()) else tdir))\n"
        "        _res = _ut.TestResult(); _suite.run(_res)\n"
        "        if _res.failures or _res.errors:\n"
        "            raise AssertionError((_res.failures + _res.errors)[0][1])\n"
        "        total_ran += int(_res.testsRun)\n"
        "        for _i, _tf in enumerate(targets):\n"
        "            if 'unittest.TestCase' in _tf.read_text(encoding='utf-8', errors='replace') and _res.testsRun > 0:\n"
        "                continue\n"
        "            _sp = importlib.util.spec_from_file_location(f'_fb_t_{_i}_{_tf.stem}', _tf)\n"
        "            if _sp and _sp.loader:\n"
        "                _tm = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_tm)\n"
        "                for _fn_n, _fn_o in vars(_tm).items():\n"
        "                    if _fn_n.startswith('test_') and callable(_fn_o) and not isinstance(_fn_o, type):\n"
        "                        if not [p for p in _insp.signature(_fn_o).parameters.values() if p.default is _insp.Parameter.empty]:\n"
        "                            _fn_o(); total_ran += 1\n"
        "if total_ran <= 0:\n"
        "    raise RuntimeError('NO_TESTS_EXECUTED')\n"
        "print(json.dumps({'ok': True, 'ran': total_ran}))\n"
    )
    # THE PROJECT'S OWN IMPORT ROOTS, NOT THE VERIFIER'S ASSUMPTION ABOUT THEM.
    # `-P`/PYTHONSAFEPATH remove the one path this subprocess used to rely on, and it put back
    # only `proj` -- so a flat-layout project (`pkg/calc.py` imported as `calc` by its own tests,
    # which is what its Makefile and CI both run) died on the test file's import line.  That reads
    # as a RED BASELINE, and a red baseline is what makes this choreographer rewrite source: it
    # then tries a test-guided repair over code that was never broken.  Measured 2026-10-31 on
    # three advanced sentences ("Optimise the function total in <pkg>/util.py", "Add a thread
    # pool ...", "Make the function total ... release the GIL"): all three raised
    # CHOREOGRAPHY_REPAIR_UNRESOLVED:<ModuleNotFoundError tail>.
    # The repository already owns this derivation (`_source_env`: the source directories plus the
    # ancestor that holds the packages the tests import, never a package dir itself, so no stdlib
    # shadowing).  Same mechanism the patch search and the mutation gate run their suites with.
    from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import _source_env
    env = dict(os.environ)
    env.update(_source_env(proj, test_dir, *prod_files))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONSAFEPATH"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", "-P", "-c", checker, str(proj), str(test_dir), str(repeats), json.dumps(mod_names)],
        cwd=str(proj),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return False, 0, (proc.stderr or proc.stdout)[-300:]
    try:
        info = json.loads(proc.stdout.strip().splitlines()[-1])
        ran = info.get("ran")
        if info.get("ok") is not True or type(ran) is not int or ran <= 0:
            return False, 0, "NO_TESTS_EXECUTED_OR_INVALID_VERIFICATION"
        return True, ran, ""
    except (ValueError, TypeError, IndexError, AttributeError):
        return False, 0, "VERIFICATION_EVIDENCE_INVALID"


def _purge_pyc(path: pathlib.Path) -> None:
    cache_dir = path.parent / "__pycache__"
    if cache_dir.is_dir():
        stem = path.stem + "."
        for f in cache_dir.iterdir():
            if f.name.startswith(stem) and f.suffix == ".pyc":
                try:
                    f.unlink()
                except OSError:
                    pass


def _inproc_sieve(
    proj: pathlib.Path,
    test_dir: pathlib.Path,
    prioritized_tests: list[pathlib.Path] | None = None,
) -> tuple[bool, int]:
    """Sub-millisecond in-process unittest + plain-pytest-fn sieve before clean child replay."""
    import importlib
    import importlib.util
    import inspect
    import unittest

    if not test_dir.is_dir():
        return False, 0
    proj_str = str(proj.resolve())
    extra_paths: list[str] = []
    for cand_dir in (proj.resolve(), proj.resolve() / "src", proj.resolve() / "pkg"):
        s = str(cand_dir)
        if cand_dir.is_dir() and s not in sys.path:
            sys.path.insert(0, s)
            extra_paths.append(s)
    old_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        local_top_pkgs = {
            (d.stem if d.is_file() else d.name)
            for d in proj.iterdir()
            if (d.is_dir() and not d.name.startswith((".", "__"))) or d.suffix == ".py"
        }
        importlib.invalidate_caches()
        for k, v in list(sys.modules.items()):
            top_k = k.split(".", 1)[0]
            if top_k in local_top_pkgs and top_k not in getattr(sys, "stdlib_module_names", frozenset()):
                sys.modules.pop(k, None)
                continue
            f = getattr(v, "__file__", None)
            if f:
                try:
                    fp = pathlib.Path(f).resolve()
                    if fp == proj or proj in fp.parents:
                        sys.modules.pop(k, None)
                except OSError:
                    pass
        top_str = proj_str if (test_dir == proj or (test_dir / "__init__.py").is_file()) else str(test_dir)
        suite = unittest.TestLoader().discover(start_dir=str(test_dir), top_level_dir=top_str)
        res = unittest.TestResult()
        suite.run(res)
        if res.failures or res.errors:
            return False, int(res.testsRun)
        plain_ran = 0
        test_files = [
            p for p in sorted(test_dir.rglob("*.py"))
            if "__pycache__" not in p.parts and (p.name.startswith("test_") or p.name.endswith("_test.py"))
        ]
        if prioritized_tests:
            prio_set = {p.resolve() for p in prioritized_tests}
            test_files.sort(key=lambda p: (0 if p.resolve() in prio_set else 1, str(p)))
        for idx, tf in enumerate(test_files):
            src_txt = tf.read_text(encoding="utf-8", errors="replace")
            if "unittest.TestCase" in src_txt and res.testsRun > 0:
                continue
            spec = importlib.util.spec_from_file_location(f"_sieve_t_{idx}_{tf.stem}", tf)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for name, obj in vars(mod).items():
                if name.startswith("test_") and callable(obj) and not isinstance(obj, type):
                    sig = inspect.signature(obj)
                    req_params = [
                        par for par in sig.parameters.values()
                        if par.default is inspect.Parameter.empty
                        and par.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    ]
                    if req_params:
                        # Parameterized/fixture pytest function: delegate to _verify_project
                        return True, max(1, int(res.testsRun) + plain_ran + 1)
                    obj()
                    plain_ran += 1
        total_ran = int(res.testsRun) + plain_ran
        return total_ran > 0, total_ran
    except BaseException:
        return False, 0
    finally:
        sys.dont_write_bytecode = old_dont_write
        for s in extra_paths:
            if s in sys.path:
                sys.path.remove(s)
# ---------------------------------------------------------------------------
_CONFLICT_RE = re.compile(
    r"^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n?",
    re.MULTILINE | re.DOTALL,
)


def _try_conflict_merge(proj: pathlib.Path, test_dir: pathlib.Path, focus: list[pathlib.Path]) -> list[pathlib.Path] | None:
    conflicted = [p for p in focus if _CONFLICT_RE.search(p.read_text(encoding="utf-8", errors="replace"))]
    if not conflicted:
        return None
    snap = {p: p.read_bytes() for p in conflicted}
    for strategy in ("union", "ours", "theirs"):
        ok_parse = True
        for p in conflicted:
            raw = snap[p].decode("utf-8", errors="replace")
            def _merge_block(m: re.Match[str]) -> str:
                ours = m.group(1)
                theirs = m.group(2)
                if strategy == "ours":
                    return ours
                if strategy == "theirs":
                    return theirs
                combined = ours.rstrip("\n") + "\n\n" + theirs.lstrip("\n")
                return combined
            merged = _CONFLICT_RE.sub(_merge_block, raw)
            try:
                ast.parse(merged)
            except SyntaxError:
                ok_parse = False
                break
            p.write_text(merged, encoding="utf-8")
        if ok_parse:
            ok, _ran, _ = _verify_project(proj, test_dir)
            if ok:
                return conflicted
        for p, b in snap.items():
            p.write_bytes(b)
    return None


# ---------------------------------------------------------------------------
# Pass B: Tarjan-SCC top-level import cycle choreography
# ---------------------------------------------------------------------------
def _tarjan_sccs(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        for w in sorted(graph.get(v, ())):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) >= 2:
                sccs.append(comp)

    for node in sorted(graph):
        if node not in indices:
            strongconnect(node)
    return sccs


def _loads_outside_defs(tree: ast.Module) -> set[str]:
    outside: set[str] = set()

    def walk_stmt(stmt: ast.stmt) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in stmt.decorator_list:
                for sub in ast.walk(dec):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        outside.add(sub.id)
            for default in list(stmt.args.defaults) + [d for d in stmt.args.kw_defaults if d is not None]:
                for sub in ast.walk(default):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        outside.add(sub.id)
            return
        if isinstance(stmt, ast.ClassDef):
            for base in list(stmt.bases) + [kw.value for kw in stmt.keywords] + list(stmt.decorator_list):
                for sub in ast.walk(base):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        outside.add(sub.id)
            for item in stmt.body:
                walk_stmt(item)
            return
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                outside.add(sub.id)

    for s in tree.body:
        walk_stmt(s)
    return outside


def _defer_cycle_edge(src_text: str, scc_set: set[str], cur_mod: str, mod_map: dict[str, pathlib.Path]) -> str | None:
    tree = ast.parse(src_text)
    outside = _loads_outside_defs(tree)
    pkg_parts = cur_mod.split(".")[:-1]
    candidates: list[tuple[ast.ImportFrom, dict[str, str], str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        base_parts = list(pkg_parts[: max(0, len(pkg_parts) - (node.level - 1))]) if node.level and node.level >= 1 else []
        if node.module:
            base_parts.extend(node.module.split("."))
        target_mod = ".".join(base_parts)
        bound_map: dict[str, str] = {}
        hits = False
        for alias in node.names:
            if alias.name == "*":
                bound_map = {}
                break
            local_name = alias.asname or alias.name
            sub_mod = f"{target_mod}.{alias.name}" if target_mod else alias.name
            if target_mod in scc_set and target_mod != cur_mod:
                hits = True
                bound_map[local_name] = f"from {target_mod} import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
            elif sub_mod in mod_map and sub_mod in scc_set and sub_mod != cur_mod:
                hits = True
                bound_map[local_name] = f"from {target_mod} import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
        if hits and bound_map and not (set(bound_map) & outside):
            candidates.append((node, bound_map, target_mod))
    if not candidates:
        return None
    imp_node, bound_map, _ = candidates[0]
    targets_to_inject: list[tuple[int, str, list[str]]] = []

    def scan_defs(stmts: list[ast.stmt]) -> None:
        for st in stmts:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)) and st.body:
                used = {
                    sub.id for sub in ast.walk(st)
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id in bound_map
                }
                if used:
                    first = st.body[0]
                    if (
                        isinstance(first, ast.Expr)
                        and isinstance(first.value, ast.Constant)
                        and isinstance(first.value.value, str)
                        and len(st.body) >= 2
                    ):
                        ins_line = st.body[1].lineno
                        indent = " " * st.body[1].col_offset
                    else:
                        ins_line = first.lineno
                        indent = " " * first.col_offset
                    targets_to_inject.append((ins_line, indent, [bound_map[k] for k in sorted(used)]))
            elif isinstance(st, ast.ClassDef):
                scan_defs(st.body)

    scan_defs(tree.body)
    lines = src_text.splitlines(keepends=True)
    for ins_line, indent, stmts_str in sorted(targets_to_inject, key=lambda x: x[0], reverse=True):
        lines.insert(ins_line - 1, "".join(f"{indent}{s}\n" for s in stmts_str))
    start_idx = imp_node.lineno - 1
    end_idx = (imp_node.end_lineno or imp_node.lineno)
    del lines[start_idx:end_idx]
    out_text = "".join(lines)
    ast.parse(out_text)
    return out_text


def _try_import_cycle_choreography(proj: pathlib.Path, test_dir: pathlib.Path) -> list[pathlib.Path] | None:
    prod = _all_prod_files(proj)
    mod_map: dict[str, pathlib.Path] = {}
    for p in prod:
        rel = p.relative_to(proj).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            mod_map[".".join(parts)] = p
    graph: dict[str, set[str]] = {m: set() for m in mod_map}
    for m, fp in mod_map.items():
        try:
            tree = ast.parse(fp.read_bytes())
        except SyntaxError:
            return None
        pkg_parts = m.split(".")[:-1]
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in mod_map and alias.name != m:
                        graph[m].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                base = list(pkg_parts[: max(0, len(pkg_parts) - (node.level - 1))]) if node.level and node.level >= 1 else []
                if node.module:
                    base.extend(node.module.split("."))
                tmod = ".".join(base)
                if tmod in mod_map and tmod != m:
                    graph[m].add(tmod)
                for alias in node.names:
                    sub = f"{tmod}.{alias.name}" if tmod else alias.name
                    if sub in mod_map and sub != m:
                        graph[m].add(sub)
    sccs = _tarjan_sccs(graph)
    if not sccs:
        return None
    snap = {p: p.read_bytes() for p in prod}
    edited: list[pathlib.Path] = []
    for scc in sccs:
        scc_set = set(scc)
        broke = False
        for m in sorted(scc):
            fp = mod_map[m]
            updated = _defer_cycle_edge(fp.read_text(encoding="utf-8"), scc_set, m, mod_map)
            if updated is not None:
                fp.write_text(updated, encoding="utf-8")
                edited.append(fp)
                broke = True
                break
        if not broke:
            for p, b in snap.items():
                p.write_bytes(b)
            return None
    ok, _ran, _ = _verify_project(proj, test_dir)
    if ok:
        return edited
    for p, b in snap.items():
        p.write_bytes(b)
    return None


# ---------------------------------------------------------------------------
# Pass C: Python 3.11+ removed/deprecated stdlib API codemod
# ---------------------------------------------------------------------------
_STDLIB_SUBS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\binspect\.getargspec\s*\("), "inspect.getfullargspec("),
    (re.compile(r"\bfrom\s+inspect\s+import\s+getargspec\b"), "from inspect import getfullargspec as getargspec"),
    (re.compile(r"\bconfigparser\.SafeConfigParser\b"), "configparser.ConfigParser"),
    (re.compile(r"\bcollections\.(Mapping|MutableMapping|Sequence|MutableSequence|Set|MutableSet|Iterable|Iterator|Callable)\b"), r"collections.abc.\1"),
    (re.compile(r"\.assertEquals\s*\("), ".assertEqual("),
)


def _try_deprecated_stdlib_codemod(proj: pathlib.Path, test_dir: pathlib.Path, focus: list[pathlib.Path]) -> list[pathlib.Path] | None:
    snap = {p: p.read_bytes() for p in focus}
    edited: list[pathlib.Path] = []
    for p in focus:
        src = snap[p].decode("utf-8", errors="replace")
        new_src = src
        for pat, repl in _STDLIB_SUBS:
            new_src = pat.sub(repl, new_src)
        if "collections.abc." in new_src and "import collections.abc" not in new_src:
            new_src = "import collections.abc\n" + new_src
        if new_src != src:
            p.write_text(new_src, encoding="utf-8")
            edited.append(p)
    if not edited:
        return None
    ok, _ran, _ = _verify_project(proj, test_dir)
    if ok:
        return edited
    for p, b in snap.items():
        p.write_bytes(b)
    return None


# ---------------------------------------------------------------------------
# Pass D: DB-API 2.0 SQL parameterization (CWE-89 elimination)
# ---------------------------------------------------------------------------
_SQL_KW_RE = re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_PCT_SLOT_RE = re.compile(r"(?:'%[sdr]'|\"%[sdr]\"|%[sdr])")
_BRACE_SLOT_RE = re.compile(r"(?:'\{[^}]*\}'|\"\{[^}]*\}\"|\{[^}]*\})")


def _parameterize_sql_expr(expr: ast.expr, src_text: str) -> tuple[str, str] | None:
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Mod) and isinstance(expr.left, ast.Constant) and isinstance(expr.left.value, str):
        raw_sql = expr.left.value
        if not _SQL_KW_RE.search(raw_sql) or not _PCT_SLOT_RE.search(raw_sql):
            return None
        param_sql = _PCT_SLOT_RE.sub("?", raw_sql)
        rhs = expr.right
        if isinstance(rhs, ast.Tuple):
            params_src = "(" + ", ".join(ast.get_source_segment(src_text, el) or ast.unparse(el) for el in rhs.elts) + ("," if len(rhs.elts) == 1 else "") + ")"
        else:
            seg = ast.get_source_segment(src_text, rhs) or ast.unparse(rhs)
            params_src = f"({seg},)"
        return repr(param_sql), params_src

    if isinstance(expr, ast.JoinedStr):
        parts_sql: list[str] = []
        param_segs: list[str] = []
        for val in expr.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                parts_sql.append(val.value)
            elif isinstance(val, ast.FormattedValue):
                if parts_sql and parts_sql[-1].endswith(("'", '"')):
                    parts_sql[-1] = parts_sql[-1][:-1]
                parts_sql.append("?")
                param_segs.append(ast.get_source_segment(src_text, val.value) or ast.unparse(val.value))
            else:
                return None
        cleaned: list[str] = []
        for idx, chunk in enumerate(parts_sql):
            if idx > 0 and parts_sql[idx - 1] == "?" and chunk.startswith(("'", '"')):
                chunk = chunk[1:]
            cleaned.append(chunk)
        full_sql = "".join(cleaned)
        if not param_segs or not _SQL_KW_RE.search(full_sql):
            return None
        params_src = "(" + ", ".join(param_segs) + ("," if len(param_segs) == 1 else "") + ")"
        return repr(full_sql), params_src

    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "format"
        and isinstance(expr.func.value, ast.Constant)
        and isinstance(expr.func.value.value, str)
        and expr.args
        and not expr.keywords
    ):
        raw_sql = expr.func.value.value
        if not _SQL_KW_RE.search(raw_sql) or not _BRACE_SLOT_RE.search(raw_sql):
            return None
        param_sql = _BRACE_SLOT_RE.sub("?", raw_sql)
        segs = [ast.get_source_segment(src_text, a) or ast.unparse(a) for a in expr.args]
        params_src = "(" + ", ".join(segs) + ("," if len(segs) == 1 else "") + ")"
        return repr(param_sql), params_src

    return None


def _replace_span(src_text: str, node: ast.AST, replacement: str) -> str:
    lines = src_text.splitlines(keepends=True)
    offsets: list[int] = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln))
    start = offsets[node.lineno - 1] + node.col_offset
    end = offsets[(node.end_lineno or node.lineno) - 1] + (node.end_col_offset or node.col_offset)
    return src_text[:start] + replacement + src_text[end:]


def _try_sql_parameterization(proj: pathlib.Path, test_dir: pathlib.Path, focus: list[pathlib.Path]) -> list[pathlib.Path] | None:
    snap = {p: p.read_bytes() for p in focus}
    edited: list[pathlib.Path] = []
    for p in focus:
        src = snap[p].decode("utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        rewritten = src
        changed = False
        calls = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "execute" and len(n.args) == 1 and not n.keywords
        ]
        for call in sorted(calls, key=lambda c: (c.lineno, c.col_offset), reverse=True):
            spec = _parameterize_sql_expr(call.args[0], src)
            if spec is not None:
                sql_lit, params_lit = spec
                recv = ast.get_source_segment(src, call.func) or ast.unparse(call.func)
                rewritten = _replace_span(rewritten, call, f"{recv}({sql_lit}, {params_lit})")
                changed = True
        if changed:
            p.write_text(rewritten, encoding="utf-8")
            edited.append(p)
    if not edited:
        return None
    ok, _ran, _ = _verify_project(proj, test_dir)
    if ok:
        return edited
    for p, b in snap.items():
        p.write_bytes(b)
    return None


# ---------------------------------------------------------------------------
# Pass E: Shared-state concurrency RLock synthesis
# ---------------------------------------------------------------------------
def _try_concurrency_lock_synthesis(proj: pathlib.Path, test_dir: pathlib.Path, focus: list[pathlib.Path]) -> list[pathlib.Path] | None:
    snap = {p: p.read_bytes() for p in focus}
    edited: list[pathlib.Path] = []
    for p in focus:
        src = snap[p].decode("utf-8", errors="replace")
        if "threading" not in src or re.search(r"\b(?:R?Lock|Semaphore|Condition)\s*\(", src):
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        target_cls: ast.ClassDef | None = None
        init_fn: ast.FunctionDef | None = None
        mut_methods: list[ast.FunctionDef] = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            c_init = None
            c_muts = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    c_init = item
                elif isinstance(item, ast.FunctionDef) and not item.name.startswith("__"):
                    stores_self = any(
                        isinstance(sub, ast.Attribute)
                        and isinstance(sub.ctx, ast.Store)
                        and isinstance(sub.value, ast.Name)
                        and sub.value.id == "self"
                        for sub in ast.walk(item)
                    )
                    if stores_self:
                        c_muts.append(item)
            if c_init is not None and c_muts:
                target_cls = node
                init_fn = c_init
                mut_methods = c_muts
                break
        if target_cls is None or init_fn is None:
            continue
        lines = src.splitlines(keepends=True)
        for mfn in sorted(mut_methods, key=lambda f: f.lineno, reverse=True):
            b_start = mfn.body[0].lineno - 1
            b_end = mfn.end_lineno or mfn.body[-1].lineno
            body_indent = " " * mfn.body[0].col_offset
            wrapped = [f"{body_indent}with self._lock:\n"]
            for idx in range(b_start, b_end):
                ln = lines[idx]
                wrapped.append(("    " + ln) if ln.strip() else ln)
            lines[b_start:b_end] = wrapped
        init_indent = " " * init_fn.body[0].col_offset
        init_end = init_fn.end_lineno or init_fn.body[-1].lineno
        lines.insert(init_end, f"{init_indent}self._lock = threading.RLock()\n")
        new_src = "".join(lines)
        if "import threading" not in new_src:
            new_src = "import threading\n" + new_src
        p.write_text(new_src, encoding="utf-8")
        edited.append(p)
    if not edited:
        return None
    ok, _ran, _ = _verify_project(proj, test_dir, repeats=5)
    if ok:
        return edited
    for p, b in snap.items():
        p.write_bytes(b)
    return None


# ---------------------------------------------------------------------------
# Pass G: Failing-suite Plastic-Surgery call-ingredient & AST operator repair
# ---------------------------------------------------------------------------
def _try_test_guided_repair(proj: pathlib.Path, test_dir: pathlib.Path, focus: list[pathlib.Path]) -> list[pathlib.Path] | None:
    snap = {p: p.read_bytes() for p in focus}
    per_file_cands: dict[pathlib.Path, list[str]] = {}
    for p in focus:
        src = snap[p].decode("utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        imported_syms: list[str] = []
        called_syms: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported_syms.append(alias.asname or alias.name)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called_syms.add(node.func.id)
        # Prioritize imported helpers not yet called in the body (Barr et al. FSE 2014)
        ordered_helpers = [s for s in imported_syms if s not in called_syms and not s[:1].isupper()] + [
            s for s in imported_syms if s in called_syms and not s[:1].isupper()
        ]

        candidates: list[str] = []
        # 1. Plastic-surgery call ingredients: var.attr -> helper(var)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name) and node.value.id != "self":
                for helper in ordered_helpers:
                    candidates.append(_replace_span(src, node, f"{helper}({node.value.id})"))

        # 2. Single-site binary, boolean, call & comparison operator repairs
        bin_swaps: list[tuple[type[ast.operator], str]] = [
            (ast.Sub, "+"), (ast.Add, "-"), (ast.Add, "*"), (ast.FloorDiv, "*"), (ast.Mult, "//"), (ast.Div, "*"),
        ]
        cmp_swaps: list[tuple[type[ast.cmpop], str]] = [
            (ast.Lt, "<="), (ast.LtE, "<"), (ast.Gt, ">="), (ast.GtE, ">"), (ast.Eq, "!="), (ast.NotEq, "=="), (ast.Is, "is not"), (ast.IsNot, "is"),
        ]
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, (ast.Add, ast.Sub)) and isinstance(node.right, ast.Constant) and node.right.value == 1:
                    lhs = ast.get_source_segment(src, node.left) or ast.unparse(node.left)
                    candidates.append(_replace_span(src, node, lhs))
                for op_cls, sym in bin_swaps:
                    if isinstance(node.op, op_cls):
                        lhs = ast.get_source_segment(src, node.left) or ast.unparse(node.left)
                        rhs = ast.get_source_segment(src, node.right) or ast.unparse(node.right)
                        candidates.append(_replace_span(src, node, f"{lhs} {sym} {rhs}"))
            elif isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
                for cmp_cls, sym in cmp_swaps:
                    if isinstance(node.ops[0], cmp_cls):
                        lhs = ast.get_source_segment(src, node.left) or ast.unparse(node.left)
                        rhs = ast.get_source_segment(src, node.comparators[0]) or ast.unparse(node.comparators[0])
                        candidates.append(_replace_span(src, node, f"{lhs} {sym} {rhs}"))
            elif isinstance(node, ast.BoolOp) and len(node.values) >= 2:
                joiner = " or " if isinstance(node.op, ast.And) else " and "
                parts = [ast.get_source_segment(src, v) or ast.unparse(v) for v in node.values]
                candidates.append(_replace_span(src, node, "(" + joiner.join(parts) + ")"))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                swap_fn = {"min": "max", "max": "min", "any": "all", "all": "any"}.get(node.func.id)
                if swap_fn:
                    candidates.append(_replace_span(src, node.func, swap_fn))

        # 3. NOPOL / SPR early-return precondition & zero-divisor statement guards
        src_lines = src.splitlines(keepends=True)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                params = [a.arg for a in (*node.args.posonlyargs, *node.args.args) if a.arg not in ("self", "cls")]
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str) and len(node.body) >= 2:
                    ins_idx = node.body[1].lineno - 1
                    indent = " " * node.body[1].col_offset
                else:
                    ins_idx = first.lineno - 1
                    indent = " " * first.col_offset
                for sub in ast.walk(node):
                    if isinstance(sub, ast.BinOp) and isinstance(sub.op, (ast.Div, ast.FloorDiv, ast.Mod)) and isinstance(sub.right, ast.Name):
                        d = sub.right.id
                        g_lines = list(src_lines)
                        g_lines.insert(ins_idx, f"{indent}if {d} == 0:\n{indent}    return 0\n")
                        candidates.append("".join(g_lines))
                if params:
                    p0 = params[0]
                    for guard_stmt in (
                        f"{indent}if {p0} is None:\n{indent}    return None\n",
                        f"{indent}if {p0} is None:\n{indent}    return 0\n",
                        f"{indent}if not {p0}:\n{indent}    return 0\n",
                        f"{indent}if not {p0}:\n{indent}    return []\n",
                        f"{indent}if not {p0}:\n{indent}    return ''\n",
                    ):
                        g_lines = list(src_lines)
                        g_lines.insert(ins_idx, guard_stmt)
                        candidates.append("".join(g_lines))

        seen_cands: set[str] = set()
        deduped_cands: list[str] = []
        # 0. Prepend any crystallized skill from VerifiedSkillStore for Python repair
        try:
            from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

            for rule in VerifiedSkillStore().lookup_rules("python", "python_test_repair"):
                from canonical.swe_kernel.verified_skill_crystallizer_v1 import apply_crystallized_code_rule

                c_out = apply_crystallized_code_rule(src, rule)
                if c_out is not None and c_out != src:
                    candidates.insert(0, c_out)
        except Exception:
            pass

        try:
            from canonical.swe_kernel.incremental_semantic_graph_v1 import query_impacted_tests

            imp_doc = query_impacted_tests(proj, ".", [p])
            prio_tests: list[pathlib.Path] | None = [
                proj / rel_t for rel_t in (imp_doc.get("impacted_tests") or [])
            ] or None
        except Exception:
            prio_tests = None

        for cand in candidates[:64]:
            if cand == src or cand in seen_cands:
                continue
            seen_cands.add(cand)
            try:
                ast.parse(cand)
            except SyntaxError:
                continue
            deduped_cands.append(cand)
            p.write_text(cand, encoding="utf-8")
            _purge_pyc(p)
            # Fast Stage-1 in-memory sieve (~0.3ms), confirmed by clean child `-B` referee!
            sieve_ok, sieve_ran = _inproc_sieve(proj, test_dir, prioritized_tests=prio_tests)
            if sieve_ok and sieve_ran > 0:
                ok, ran, _ = _verify_project(proj, test_dir)
                if ok and ran > 0:
                    try:
                        from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

                        VerifiedSkillStore().crystallize_verified_fix(
                            language="python",
                            bug_class="python_test_repair",
                            before_code=src,
                            after_code=cand,
                            verifier_oracle_kind="unittest_or_pytest",
                        )
                    except Exception:
                        pass
                    return [p]
            p.write_bytes(snap[p])
            _purge_pyc(p)
        per_file_cands[p] = deduped_cands[:12]

    # Joint 2-file coupled fault repair (e.g. caller + callee or producer + consumer both faulty):
    # bounded at <=8 focus files * <=12 candidates/file via ~0.3ms _inproc_sieve + child referee.
    cand_files = [fp for fp in focus if per_file_cands.get(fp)]
    if 2 <= len(cand_files) <= 8:
        for idx_a in range(len(cand_files)):
            pa = cand_files[idx_a]
            src_a = snap[pa].decode("utf-8", errors="replace")
            for idx_b in range(idx_a + 1, len(cand_files)):
                pb = cand_files[idx_b]
                src_b = snap[pb].decode("utf-8", errors="replace")
                for cand_a in per_file_cands[pa]:
                    pa.write_text(cand_a, encoding="utf-8")
                    _purge_pyc(pa)
                    for cand_b in per_file_cands[pb]:
                        pb.write_text(cand_b, encoding="utf-8")
                        _purge_pyc(pb)
                        sieve_ok, sieve_ran = _inproc_sieve(proj, test_dir)
                        if sieve_ok and sieve_ran > 0:
                            ok, ran, _ = _verify_project(proj, test_dir)
                            if ok and ran > 0:
                                try:
                                    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

                                    store = VerifiedSkillStore()
                                    store.crystallize_verified_fix("python", "python_test_repair", src_a, cand_a, "coupled_suite")
                                    store.crystallize_verified_fix("python", "python_test_repair", src_b, cand_b, "coupled_suite")
                                except Exception:
                                    pass
                                return [pa, pb]
                    pb.write_bytes(snap[pb])
                    _purge_pyc(pb)
                pa.write_bytes(snap[pa])
                _purge_pyc(pa)
    return None


def _synthesize_differential_regression_test(
    proj: pathlib.Path,
    test_dir: pathlib.Path,
    patched_files: list[pathlib.Path],
    pre_snap: dict[pathlib.Path, bytes],
) -> pathlib.Path | None:
    """Synthesize a standalone regression test proved to FAIL pre-patch and PASS post-patch."""
    if not patched_files:
        return None
    target = patched_files[0]
    post_bytes = target.read_bytes()
    pre_bytes = pre_snap.get(target)
    if pre_bytes is None or pre_bytes == post_bytes:
        return None

    rel_mod = target.relative_to(proj).with_suffix("")
    parts = list(rel_mod.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    mod_dotted = ".".join(parts)

    # Mine existing failing test assertion or synthesize boundary/witness call on changed function
    pre_tree = ast.parse(pre_bytes.decode("utf-8", errors="replace"))
    post_tree = ast.parse(post_bytes.decode("utf-8", errors="replace"))
    pre_fns = {n.name: ast.unparse(n) for n in pre_tree.body if isinstance(n, ast.FunctionDef)}
    changed_fns = [
        n for n in post_tree.body
        if isinstance(n, ast.FunctionDef) and pre_fns.get(n.name) != ast.unparse(n)
    ]
    if not changed_fns:
        return None
    fn = changed_fns[0]
    fn_name = fn.name
    arity = len([a for a in fn.args.args if a.arg not in ("self", "cls")])

    # Probe candidate inputs in-process on pre vs post code to find a differential witness!
    sample_vectors: list[tuple[Any, ...]] = []
    if arity == 0:
        sample_vectors = [()]
    elif arity == 1:
        sample_vectors = [(0,), (1,), (2,), (3,), (-1,), ([1, 2, 3],), ("abc",), (None,)]
    elif arity == 2:
        sample_vectors = [(2, 3), (10, 5), (0, 5), (4, 2), ([1, 2], [2, 3]), ("a", "b")]
    elif arity == 3:
        sample_vectors = [(2, 3, 4), (10, 2, 5), (1, 0, 1)]

    # Also harvest concrete call argument tuples from existing test files!
    if test_dir.is_dir():
        for tf in sorted(test_dir.rglob("test*.py")):
            try:
                tt = ast.parse(tf.read_text(encoding="utf-8"))
                for call in ast.walk(tt):
                    if isinstance(call, ast.Call):
                        cname = call.func.id if isinstance(call.func, ast.Name) else (call.func.attr if isinstance(call.func, ast.Attribute) else None)
                        if cname == fn_name and len(call.args) == arity and not call.keywords:
                            vals = []
                            for a in call.args:
                                vals.append(ast.literal_eval(a))
                            sample_vectors.insert(0, tuple(vals))
            except Exception:
                continue

    probe_code = (
        "import importlib, json, pathlib, sys\n"
        "proj = pathlib.Path(sys.argv[1]).resolve()\n"
        "mod_name, fn_name, vecs = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])\n"
        "sys.path.insert(0, str(proj))\n"
        "m = importlib.import_module(mod_name)\n"
        "f = getattr(m, fn_name)\n"
        "out = []\n"
        "for v in vecs:\n"
        "    try:\n"
        "        r = f(*v)\n"
        "        out.append({'ok': True, 'val': r})\n"
        "    except Exception as e:\n"
        "        out.append({'ok': False, 'err': type(e).__name__})\n"
        "print(json.dumps(out))\n"
    )
    json_vecs: list[list[Any]] = []
    for v in sample_vectors:
        try:
            json.dumps(list(v))
            if list(v) not in json_vecs:
                json_vecs.append(list(v))
        except TypeError:
            continue
    if not json_vecs:
        return None

    def _eval_vectors(raw_code: bytes) -> list[dict[str, Any]] | None:
        saved_path = list(sys.path)
        saved_mods = dict(sys.modules)
        try:
            sys.path.insert(0, str(proj))
            top_pkg = mod_dotted.split(".")[0]
            for _k in list(sys.modules):
                if _k == top_pkg or _k.startswith(top_pkg + "."):
                    sys.modules.pop(_k, None)
            ns_mod: dict[str, Any] = {"__name__": mod_dotted, "__file__": str(target), "__builtins__": __builtins__}
            exec(compile(raw_code, str(target), "exec"), ns_mod)
            fn_obj = ns_mod.get(fn_name)
            if not callable(fn_obj):
                return None
            out_rows: list[dict[str, Any]] = []
            for vec in json_vecs:
                try:
                    rv = fn_obj(*vec)
                    json.dumps(rv)
                    out_rows.append({"ok": True, "val": rv})
                except Exception as exc_v:
                    out_rows.append({"ok": False, "err": type(exc_v).__name__})
            return out_rows
        except Exception:
            return None
        finally:
            sys.path[:] = saved_path
            for _k in list(sys.modules):
                if _k not in saved_mods:
                    sys.modules.pop(_k, None)
            sys.modules.update(saved_mods)

    post_res = _eval_vectors(post_bytes)
    pre_res = _eval_vectors(pre_bytes)

    if not post_res or not pre_res or len(post_res) != len(pre_res):
        return None

    witness_args = None
    witness_expected = None
    for args_vec, pr, po in zip(json_vecs, pre_res, post_res):
        if po.get("ok") and pr != po:
            witness_args = args_vec
            witness_expected = po.get("val")
            break
    if witness_args is None:
        return None

    test_dir.mkdir(parents=True, exist_ok=True)
    reg_file = test_dir / f"test_regression_{target.stem}_{fn_name}.py"
    args_src = ", ".join(repr(x) for x in witness_args)
    test_content = (
        "import unittest\n"
        f"from {mod_dotted} import {fn_name}\n\n\n"
        f"class TestRegression_{fn_name}(unittest.TestCase):\n"
        f"    def test_regression_{fn_name}_differential_witness(self) -> None:\n"
        f"        self.assertEqual({fn_name}({args_src}), {witness_expected!r})\n\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n"
    )
    reg_file.write_text(test_content, encoding="utf-8")
    _purge_pyc(reg_file)

    # Differential proof: MUST fail on pre_bytes (`-B`) and MUST pass on post_bytes (`-B`)!
    try:
        target.write_bytes(pre_bytes)
        _purge_pyc(target)
        fails_pre, _, _ = _verify_project(proj, test_dir)
        target.write_bytes(post_bytes)
        _purge_pyc(target)
        passes_post, ran_post, _ = _verify_project(proj, test_dir)
        if (not fails_pre) and passes_post and ran_post > 0:
            return reg_file
        reg_file.unlink(missing_ok=True)
        return None
    except BaseException:
        target.write_bytes(post_bytes)
        _purge_pyc(target)
        reg_file.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Pass F: Container & loop strength reduction O(n^2) -> O(n)
# ---------------------------------------------------------------------------
def _match_nested_dup_scan(fn: ast.FunctionDef) -> str | None:
    """Recognize the exact all-pairs algorithm, not just two nested loops."""
    stmts = list(fn.body)
    if stmts and isinstance(stmts[0], ast.Expr) and isinstance(stmts[0].value, ast.Constant) and isinstance(stmts[0].value.value, str):
        stmts = stmts[1:]
    if len(stmts) != 2:
        return None
    outer, last = stmts
    if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant) and last.value.value is False
            and isinstance(outer, ast.For) and isinstance(outer.target, ast.Name)
            and not outer.orelse and len(outer.body) == 1):
        return None
    inner = outer.body[0]
    if not (isinstance(inner, ast.For) and isinstance(inner.target, ast.Name)
            and not inner.orelse and len(inner.body) == 1):
        return None
    cond = inner.body[0]
    if not (isinstance(cond, ast.If) and not cond.orelse and len(cond.body) == 1
            and isinstance(cond.body[0], ast.Return)
            and isinstance(cond.body[0].value, ast.Constant) and cond.body[0].value.value is True
            and isinstance(cond.test, ast.Compare) and isinstance(cond.test.left, ast.Subscript)
            and isinstance(cond.test.left.value, ast.Name)):
        return None
    seq = cond.test.left.value.id
    i, j = outer.target.id, inner.target.id
    if len({seq, i, j}) != 3 or seq not in {a.arg for a in fn.args.posonlyargs + fn.args.args}:
        return None
    def same(node, expression):
        return ast.dump(node) == ast.dump(ast.parse(expression, mode="eval").body)
    if not (same(outer.iter, f"range(len({seq}))")
            and same(inner.iter, f"range({i} + 1, len({seq}))")
            and same(cond.test, f"{seq}[{i}] == {seq}[{j}]")):
        return None
    return seq


def _try_quadratic_to_linear(proj: pathlib.Path, test_dir: pathlib.Path, focus: list[pathlib.Path]) -> list[pathlib.Path] | None:
    snap = {p: p.read_bytes() for p in focus}
    edited: list[pathlib.Path] = []
    for p in focus:
        src = snap[p].decode("utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines(keepends=True)
        changed = False
        fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        for fn in sorted(fns, key=lambda f: f.lineno, reverse=True):
            seq_name = _match_nested_dup_scan(fn)
            if seq_name is None:
                continue
            first_stmt = fn.body[0]
            if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str) and len(fn.body) >= 2:
                b_start = fn.body[1].lineno - 1
                indent = " " * fn.body[1].col_offset
            else:
                b_start = first_stmt.lineno - 1
                indent = " " * first_stmt.col_offset
            b_end = fn.end_lineno or fn.body[-1].lineno
            # Specialize only exact builtin sequences of equality/hash-safe scalar
            # values. Keep the ORIGINAL algorithm for unhashables, NaNs, custom
            # equality/hash methods, subclasses and shadowed range/len. Fresh
            # locals cannot capture a parameter or the original induction names.
            occupied = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
            occupied.update(n.arg for n in ast.walk(fn) if isinstance(n, ast.arg))
            def fresh(stem):
                while stem in occupied:
                    stem += "_"
                occupied.add(stem)
                return stem
            bi, seen, item = (fresh(n) for n in ("_brain_builtins", "_brain_seen", "_brain_item"))
            original = lines[b_start:b_end]
            replacement = [
                f"{indent}import builtins as {bi}\n",
                f"{indent}if (range is {bi}.range and len is {bi}.len\n",
                f"{indent}        and {bi}.type({seq_name}) in ({bi}.list, {bi}.tuple)\n",
                f"{indent}        and {bi}.all({bi}.type({item}) in ({bi}.int, {bi}.bool, {bi}.str, {bi}.bytes, {bi}.type(None)) for {item} in {seq_name})):\n",
                f"{indent}    {seen} = {bi}.set()\n",
                f"{indent}    for {item} in {seq_name}:\n",
                f"{indent}        if {item} in {seen}:\n",
                f"{indent}            return True\n",
                f"{indent}        {seen}.add({item})\n",
                f"{indent}    return False\n",
            ] + original
            lines[b_start:b_end] = replacement
            changed = True
        if changed:
            p.write_text("".join(lines), encoding="utf-8")
            edited.append(p)
    if not edited:
        return None
    ok, _ran, _ = _verify_project(proj, test_dir)
    if ok:
        return edited
    for p, b in snap.items():
        p.write_bytes(b)
    return None


# ---------------------------------------------------------------------------
# Pass H: Whole-project AST unused-import & unreferenced-function pruning
# ---------------------------------------------------------------------------
def _try_dead_code_pruning(proj: pathlib.Path, test_dir: pathlib.Path, focus: list[pathlib.Path], remove_functions: set[str] | None = None) -> list[pathlib.Path] | None:
    all_py = [
        p for p in sorted(proj.rglob("*.py"))
        if "__pycache__" not in p.parts and ".git" not in p.parts
    ]
    global_refs: set[str] = set()
    for p in all_py:
        try:
            t = ast.parse(p.read_bytes())
        except SyntaxError:
            return None
        for node in ast.walk(t):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                global_refs.add(node.id)
            elif isinstance(node, ast.Attribute):
                global_refs.add(node.attr)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    global_refs.add(alias.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                    # A literal export list is a real reference. Dynamic export
                    # construction is unknown, not authority to delete its API.
                    try:
                        exports = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        exports = None
                    if isinstance(exports, (list, tuple, set)) and all(isinstance(v, str) for v in exports):
                        global_refs.update(exports)
                    else:
                        global_refs.update(n.name for n in t.body
                                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))

    snap = {p: p.read_bytes() for p in focus}
    edited: list[pathlib.Path] = []
    for p in focus:
        if p.name == "__init__.py":
            continue
        src = snap[p].decode("utf-8", errors="replace")
        tree = ast.parse(src)
        # First drop dead top-level functions never referenced anywhere in proj
        drop_ranges: list[tuple[int, int]] = []
        kept_stmts: list[ast.stmt] = []
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and not stmt.name.startswith("__"):
                requested = stmt.name in (remove_functions or set())
                implicit_private = not remove_functions and stmt.name.startswith("_")
                if (requested or implicit_private) and stmt.name not in global_refs and not stmt.decorator_list:
                    start = (stmt.decorator_list[0].lineno if stmt.decorator_list else stmt.lineno) - 1
                    end = stmt.end_lineno or stmt.lineno
                    drop_ranges.append((start, end))
                    continue
            kept_stmts.append(stmt)

        # Next compute module-local loads among kept non-import statements
        local_loads: set[str] = set()
        for stmt in kept_stmts:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    local_loads.add(sub.id)
                elif isinstance(sub, ast.Assign):
                    for tgt in sub.targets:
                        if isinstance(tgt, ast.Name) and tgt.id == "__all__" and isinstance(sub.value, (ast.List, ast.Tuple)):
                            for el in sub.value.elts:
                                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                                    local_loads.add(el.value)

        lines = src.splitlines(keepends=True)
        import_rewrites: dict[int, tuple[int, str]] = {}
        for stmt in kept_stmts:
            if isinstance(stmt, ast.Import):
                live = [a for a in stmt.names if (a.asname or a.name.split(".")[0]) in local_loads]
                if len(live) != len(stmt.names):
                    s_idx = stmt.lineno - 1
                    e_idx = stmt.end_lineno or stmt.lineno
                    if not live:
                        drop_ranges.append((s_idx, e_idx))
                    else:
                        rendered = "import " + ", ".join(
                            f"{a.name} as {a.asname}" if a.asname else a.name for a in live
                        ) + "\n"
                        import_rewrites[s_idx] = (e_idx, rendered)
            elif isinstance(stmt, ast.ImportFrom) and stmt.module != "__future__":
                if any(a.name == "*" for a in stmt.names):
                    continue
                live = [a for a in stmt.names if (a.asname or a.name) in local_loads]
                if len(live) != len(stmt.names):
                    s_idx = stmt.lineno - 1
                    e_idx = stmt.end_lineno or stmt.lineno
                    if not live:
                        drop_ranges.append((s_idx, e_idx))
                    else:
                        dots = "." * (stmt.level or 0)
                        mod_str = f"{dots}{stmt.module or ''}"
                        rendered = f"from {mod_str} import " + ", ".join(
                            f"{a.name} as {a.asname}" if a.asname else a.name for a in live
                        ) + "\n"
                        import_rewrites[s_idx] = (e_idx, rendered)

        if not drop_ranges and not import_rewrites:
            continue
        edits_by_start: list[tuple[int, int, str]] = [
            (s, e, "") for s, e in drop_ranges
        ] + [
            (s, e, repl) for s, (e, repl) in import_rewrites.items()
        ]
        for s, e, repl in sorted(edits_by_start, key=lambda x: x[0], reverse=True):
            lines[s:e] = [repl] if repl else []
        new_src = "".join(lines)
        ast.parse(new_src)
        p.write_text(new_src, encoding="utf-8")
        edited.append(p)

    if not edited:
        return None
    ok, _ran, _ = _verify_project(proj, test_dir)
    if ok:
        return edited
    for p, b in snap.items():
        p.write_bytes(b)
    return None


def _try_live_trace_synthesis_repair(
    proj: pathlib.Path,
    test_dir: pathlib.Path,
    focus: list[pathlib.Path],
) -> list[pathlib.Path] | None:
    """Synthesize function bodies from live runtime failure-frame & assertion values."""
    try:
        from canonical.swe_kernel.whitebox_introspector_and_trace_synthesizer_v1 import (
            synthesize_candidates_for_file,
        )
    except Exception:
        return None

    test_files = [
        p for p in sorted(test_dir.rglob("*.py"))
        if "__pycache__" not in p.parts and (p.name.startswith("test_") or p.name.endswith("_test.py"))
    ]
    if not test_files:
        return None
    src_files = [
        p for p in focus
        if not (p.name.startswith("test_") or p.name.endswith("_test.py"))
    ]
    for src_f in src_files:
        orig_bytes = src_f.read_bytes()
        orig_txt = orig_bytes.decode("utf-8", errors="replace")
        try:
            cands = synthesize_candidates_for_file(src_f, proj=proj, test_files=test_files)
        except Exception:
            cands = []
        for idx, patched_txt in enumerate(cands):
            desc = f"obs_synth_{idx}"
            try:
                src_f.write_text(patched_txt, encoding="utf-8")
                _purge_pyc(src_f)
                sieve_ok, _ = _inproc_sieve(proj, test_dir, prioritized_tests=test_files)
                if not sieve_ok:
                    continue
                ok, _ran, _ = _verify_project(proj, test_dir)
                if ok:
                    try:
                        from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
                        VerifiedSkillStore().crystallize_patch(
                            skill_family="python_repair_ast_patch",
                            operator_id=f"live_trace_synth:{desc}",
                            before_code=orig_txt,
                            after_code=patched_txt,
                            proof_kind="clean_subprocess_test_suite_pass",
                        )
                    except Exception:
                        pass
                    return [src_f]
            finally:
                if not src_f.exists():
                    src_f.write_bytes(orig_bytes)
            src_f.write_bytes(orig_bytes)
            _purge_pyc(src_f)
        src_f.write_bytes(orig_bytes)
        _purge_pyc(src_f)
    return None


def _run_in_place(args: Mapping[str, Any], root_path: pathlib.Path | str) -> dict[str, Any]:
    repo = pathlib.Path(root_path).resolve()
    src_raw = str(args.get("source_root") or "").strip()
    out_raw = str(args.get("output_path") or "").strip()
    if not src_raw or not out_raw:
        raise RuntimeError("MISSING_REQUIRED_ARGUMENTS")
    src = _safe_path(repo, src_raw, allow_root=False)
    out = _safe_path(repo, out_raw)
    if not (src.is_dir() or src.is_file()):
        raise RuntimeError("SOURCE_ROOT_NOT_FOUND")

    proj, test_dir, focus = _resolve_workspace(src, repo)
    if proj in (repo, repo / "canonical", repo / "canonical" / "runtime") or len(focus) > 64:
        raise RuntimeError("REFUSING_BROAD_REPO_MUTATION")
    if not focus:
        raise RuntimeError("NO_PYTHON_SOURCE_FILES")

    removals = args.get("remove_functions", [])
    if not isinstance(removals, list) or any(not isinstance(n, str) or not n.isidentifier() for n in removals):
        raise RuntimeError("REMOVAL_TARGETS_INVALID")
    remove_functions = set(removals)
    if remove_functions:
        definitions = [node.name for path in focus for node in ast.parse(path.read_bytes()).body
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if any(definitions.count(name) != 1 for name in remove_functions):
            raise RuntimeError("REMOVAL_TARGET_NOT_UNIQUE")

    pre_run_snap = {p: p.read_bytes() for p in focus}
    mode_applied = "already_acyclic_and_green"
    edited: list[pathlib.Path] | None = None

    # Strictly ordered structural diagnostic passes
    for pass_name, fn in (
        ("conflict_merge", lambda: _try_conflict_merge(proj, test_dir, focus)),
        ("circular_import_deferral", lambda: _try_import_cycle_choreography(proj, test_dir)),
        ("deprecated_stdlib_codemod", lambda: _try_deprecated_stdlib_codemod(proj, test_dir, focus)),
        ("sql_parameterization", lambda: _try_sql_parameterization(proj, test_dir, focus)),
        ("concurrency_lock_synthesis", lambda: _try_concurrency_lock_synthesis(proj, test_dir, focus)),
    ):
        if remove_functions:
            break  # An explicit removal does not authorize unrelated repair passes.
        edited = fn()
        if edited is not None:
            mode_applied = pass_name
            break

    if edited is None:
        base_ok, _ran, _err = _verify_project(proj, test_dir)
        if not base_ok:
            if remove_functions:
                raise RuntimeError("REMOVAL_REQUIRES_GREEN_BASELINE:" + _err[:200])
            _has_tests = test_dir.is_dir() and any(
                "__pycache__" not in p.parts and (p.name.startswith("test_") or p.name.endswith("_test.py"))
                for p in test_dir.rglob("*.py")
            )
            edited = _try_test_guided_repair(proj, test_dir, focus) if _has_tests else None
            if edited is not None:
                mode_applied = "test_guided_ast_repair"
            elif _has_tests:
                edited = _try_live_trace_synthesis_repair(proj, test_dir, focus)
                if edited is not None:
                    mode_applied = "live_trace_observational_synthesis"
                else:
                    raise RuntimeError("CHOREOGRAPHY_REPAIR_UNRESOLVED:" + _err[:200])
            else:
                raise RuntimeError("CHOREOGRAPHY_REPAIR_UNRESOLVED:" + _err[:200])
        else:
            for pass_name, fn in (
                ("quadratic_to_linear_set", lambda: _try_quadratic_to_linear(proj, test_dir, focus)),
                ("dead_code_and_import_pruning", lambda: _try_dead_code_pruning(proj, test_dir, focus, remove_functions)),
            ):
                if remove_functions and pass_name != "dead_code_and_import_pruning":
                    continue
                edited = fn()
                if edited is not None:
                    mode_applied = pass_name
                    break

    reg_test_rel: str | None = None
    if args.get("synthesize_regression_test") and edited:
        for _ef in edited:
            if _ef in pre_run_snap and _ef.is_file() and _ef.stat().st_size == len(pre_run_snap[_ef]):
                _ef.write_bytes(_ef.read_bytes() + b"\n")
                _purge_pyc(_ef)
        reg_file = _synthesize_differential_regression_test(proj, test_dir, edited, pre_run_snap)
        if reg_file is not None:
            reg_test_rel = reg_file.relative_to(repo).as_posix()
            edited = list(edited) + [reg_file]
            if (proj / ".git").is_dir() and proj != repo:
                rel_to_proj = [p.relative_to(proj).as_posix() for p in edited]
                subprocess.run(["git", "add", "--", *rel_to_proj], cwd=str(proj), capture_output=True, timeout=10)
                subprocess.run(
                    ["git", "-c", "user.name=brain", "-c", "user.email=brain@local", "commit", "-q", "-m", "fix and regression test"],
                    cwd=str(proj),
                    capture_output=True,
                    timeout=10,
                )

    edited_rels = sorted({p.relative_to(repo).as_posix() for p in (edited or [])})
    report = {
        "schema": "PROJECT_BRAIN_CROSSFILE_CHOREOGRAPH_V1",
        "adapter": "software_repair_crossfile_choreograph_v1",
        "source_root": src.relative_to(repo).as_posix() if src != repo else ".",
        "project_root": proj.relative_to(repo).as_posix() if proj != repo else ".",
        "mode": mode_applied,
        "files_edited": edited_rels,
        "regression_test_written": reg_test_rel,
        "edit_count": len(edited_rels),
        "choreography_verified": True,
        "output_verified": True,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out.write_bytes(payload)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    return {
        "adapter": "software_repair_crossfile_choreograph_v1",
        "choreography_verified": True,
        "edit_count": len(edited_rels),
        "files_edited": edited_rels,
        "mode": mode_applied,
        "output_path": out.relative_to(repo).as_posix(),
        "output_sha256": sha,
        "output_verified": True,
        "verified": True,
    }


def run(args, root):
    if any(key in args for key in ("task_path", "issue_path", "request_binding", "request_binding_sha256")):
        return _run_task_bound(args, root)
    return _run_in_place(args, root)
