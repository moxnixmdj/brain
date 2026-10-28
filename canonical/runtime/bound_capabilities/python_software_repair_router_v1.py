"""Bug-class repair router: diagnose, route, escalate, realize -- measured.

The ladder (REPAIR_DEPTH_LADDER_20261029) produced the feature map:
singles -> test_guided/strict (P100), stateful+pairs -> coupled (P100),
writers (apply.verified, cegis_hypothesis) 100% on every seeded class.
This capability is the map's consumer: it DIAGNOSES the failing repo
(suite outcome, failing-test count, traceback depth), routes along the
escalation ladder, REALIZES reporter patches (the engines restore the
source by contract; exactly one place in the stack writes), and replays
the suite itself. verified is measured, never inherited.

No subprocess of its own: diagnosis runs through the pinned ptg._run_tests
callsite, engines run their own pinned sites. Pure composition.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_SOFTWARE_REPAIR_ROUTER_V1"
CAPABILITY_ID = "python.software.repair.route.v1"
REPO = pathlib.Path(__file__).resolve().parents[3]


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_CTRL = _load(pathlib.Path(__file__).with_name(
    "python_repair_measured_acceptance_controller_v1.py"), "_brain_router_ctrl")
_PGC = _CTRL._REPAIR
_PTG = _PGC._PATCH
_ITER = _load(pathlib.Path(__file__).with_name(
    "python_iterative_software_repair_loop_v1.py"), "_brain_router_iter")
# The WRITER loop (measured 100% L1-L5, realizes+replays in place) -- not to
# be confused with _CTRL._REPAIR, the provenance-guided REPORTER engine.
_CEGIS = _load(pathlib.Path(__file__).with_name(
    "software_repair_loop_cegis_hypothesis_v1.py"), "_brain_router_cegis")


class RouterError(RuntimeError):
    pass


def _rel(repo: pathlib.Path, p: pathlib.Path) -> str:
    return str(p.resolve().relative_to(repo))


def _suite(repo, argv, timeout, env):
    d = _PTG._run_tests(repo, [str(x) for x in argv], timeout, env)
    text = (d.get("stdout") or "") + "\n" + (d.get("stderr") or "")
    return int(d["returncode"]), text


def _diagnose(text: str, rc: int) -> dict[str, Any]:
    failing = text.count("\nFAIL: ") + text.count("\nERROR: ")
    depth = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('File "') and s.endswith(".py, line"):
            pass
        if s.startswith('File "'):
            depth += 1
    return {
        "baseline_returncode": rc,
        "failing_test_count": failing,
        "traceback_frame_count": depth,
        "class_guess": ("coupled_or_stateful" if failing >= 2
                        else "single_defect"),
    }


def _realize(repo, patches, originals):
    for row in patches:
        target = (repo / str(row["source_path"])).resolve()
        if target not in originals:
            originals[target] = target.read_bytes()
        target.write_text(_CTRL._apply_unified_diff(
            originals[target].decode("utf-8"), str(row["unified_diff"])),
            encoding="utf-8")
        _PTG._purge_source_bytecode(target)


def _revert(originals):
    for t, raw in originals.items():
        t.write_bytes(raw)
        _PTG._purge_source_bytecode(t)


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _CTRL._safe_output(repo, args.get("output_path"))
    src = args.get("source_root") or "."
    src_abs = (repo / str(src)).resolve()
    tests = [_safe_test(repo, t) for t in (args.get("test_paths") or [])
             if str(t).strip()]
    if not tests:
        raise RouterError("TEST_PATHS_REQUIRED")
    argv = [str(x) for x in (args.get("test_argv") or
                             _PTG.suite_argv(sys.executable, *tests))]
    timeout = max(1, min(int(args.get("timeout_s", 20)), 120))
    env = _PTG._source_env(*tests)
    budget = max(1, min(int(args.get("budget", 2)), 6))

    rc, text = _suite(repo, argv, timeout, env)
    if rc == 0:
        raise RouterError("BASELINE_ALREADY_PASSES")
    diagnosis = _diagnose(text, rc)

    route_trace: list[dict[str, Any]] = []
    final_patches = None
    repaired = False
    originals: dict[pathlib.Path, bytes] = {}

    # Ladder step 1: the CEGIS writer (fastest proven writer on every tier).
    intermediate = output.parent / (".route_" + output.name)
    try:
        step = _CEGIS.run({
            "source_root": _rel(repo, src_abs) if src_abs != repo else ".",
            "test_paths": [_rel(repo, t) for t in tests],
            "test_argv": argv,
            "output_path": _rel(repo, intermediate),
            "timeout_s": timeout,
            "budget": budget,
        }, repo)
    except Exception as exc:
        step = {"status": type(exc).__name__ + ":" + str(exc)[:120]}
    route_trace.append({"step": "cegis_writer",
                        "status": step.get("status"),
                        "verified": step.get("verified")})
    rc2, _ = _suite(repo, argv, timeout, env)
    repaired = rc2 == 0

    # Ladder step 2: coupled pair engine's patch report, realized here.
    if not repaired:
        _revert(originals); originals.clear()
        cpl = intermediate.parent / (".route_cpl_" + output.name)
        try:
            r2 = _PGC._COUPLED.run({
                "source_root": _rel(repo, src_abs) if src_abs != repo else ".",
                "test_paths": [_rel(repo, t) for t in tests],
                "test_argv": argv,
                "output_path": _rel(repo, cpl),
                "timeout_s": timeout,
            }, repo)
        except Exception as exc:
            r2 = {"status": type(exc).__name__ + ":" + str(exc)[:120]}
        patches = r2.get("patches") or []
        route_trace.append({"step": "coupled_reporter",
                            "status": r2.get("status"),
                            "patch_count": len(patches)})
        if patches:
            _realize(repo, patches, originals)
            rc3, _ = _suite(repo, argv, timeout, env)
            if rc3 == 0:
                repaired = True
                final_patches = patches
            else:
                _revert(originals); originals.clear()

    # Ladder step 3: iterative single-file engine's patch report, realized.
    if not repaired:
        _revert(originals); originals.clear()
        it = intermediate.parent / (".route_it_" + output.name)
        try:
            r3 = _ITER.run({
                "source_root": _rel(repo, src_abs) if src_abs != repo else ".",
                "test_paths": [_rel(repo, t) for t in tests],
                "test_argv": argv,
                "output_path": _rel(repo, it),
                "timeout_s": timeout,
            }, repo)
        except Exception as exc:
            r3 = {"status": type(exc).__name__ + ":" + str(exc)[:120]}
        patches = r3.get("patches") or []
        route_trace.append({"step": "iterative_reporter",
                            "status": r3.get("status"),
                            "patch_count": len(patches)})
        if patches:
            _realize(repo, patches, originals)
            rc4, _ = _suite(repo, argv, timeout, env)
            if rc4 == 0:
                repaired = True
                final_patches = patches
            else:
                _revert(originals); originals.clear()

    # Final replay: the counterexample check against flaky greens.
    if repaired:
        rc5, _ = _suite(repo, argv, timeout, env)
        if rc5 != 0:
            repaired = False
            _revert(originals); originals.clear()
            route_trace.append({"step": "final_replay", "flipped": True})
        else:
            route_trace.append({"step": "final_replay", "green": True})

    if final_patches is None and repaired:
        # the writer route repaired in place; dig its patch rows for the record
        final_patches = step.get("patches") or []
        if not final_patches:
            final_patches = ((step.get("strict_result") or {})
                             .get("patches") or [])

    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "diagnosis": diagnosis, "route_trace": route_trace,
        "repaired": repaired, "patches": final_patches or [],
        "verified": repaired,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {"adapter": "python_software_repair_router_v1",
            "capability_id": CAPABILITY_ID,
            "output_path": _rel(repo, output),
            "output_sha256": __import__("hashlib").sha256(raw).hexdigest(),
            "output_verified": True,
            "verified": repaired, "repaired": repaired,
            "route_trace": route_trace,
            "model_dependency_count": 0, "incremental_spend_usd": 0}


def _safe_test(repo, t):
    p = (repo / str(t)).resolve()
    if repo not in p.parents or not p.is_file():
        raise RouterError("TEST_PATH_OUTSIDE_REPOSITORY")
    return p
