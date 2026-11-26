#!/usr/bin/env python3
"""Dark-matter adjudicator: turn "we already have it somewhere" into an executable verdict.

The repository has 6,114 modules that no other module imports, 1,996 of them >=140 lines. Every
plan that says "awaken the hidden organs" assumes those modules work. Nothing in the repo checks
that, and a module nobody imports is not a capability -- it is a claim.

This tool makes the claim checkable, in four fail-closed states:

  PROVEN            imported, and a callable zero-argument `self_check()` returned a dict whose
                    `verdict`/`pass`/`ok` field says it passed. This is the only state that
                    counts as evidence.
  IMPORTS_ONLY      imported cleanly but exposes no self-check. Reachable, unproven. Most dark
                    modules land here, and saying so is the point.
  MISSING_SUBSTRATE import failed on a third-party dependency (network, GPU, a package we do not
                    ship). Not broken -- unexercisable here.
  BROKEN            import raised anything else, the self-check raised, the self-check said no,
                    or the probe timed out. Quarantine list.

Isolation is not decoration: each module is imported in its own subprocess with a timeout, because
importing 2,000 unimported modules into one interpreter would let one `sys.exit()` or one global
mutation poison every verdict after it -- and several of these modules do exactly that.

Ablation is built in: `--no-probe` never executes anything, and every verdict must collapse to
"unproven". If it does not, the instrument is not measuring execution.
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA = "BRAIN_DARK_MATTER_ADJUDICATOR_V1"
ROOT = pathlib.Path(__file__).resolve().parents[2]

PROVEN = "PROVEN"
IMPORTS_ONLY = "IMPORTS_ONLY"
MISSING_SUBSTRATE = "MISSING_SUBSTRATE"
BROKEN = "BROKEN"
VERDICTS: Tuple[str, ...] = (PROVEN, IMPORTS_ONLY, MISSING_SUBSTRATE, BROKEN)

# The probe runs in its own interpreter. It never calls `main()`: a module's CLI may delete files,
# open sockets, or fork; a `self_check()` contract is the only thing safe to invoke unattended.
_PROBE = r'''
import importlib, json, sys, traceback
name = sys.argv[1]
out = {"module": name}
try:
    mod = importlib.import_module(name)
except BaseException as exc:  # noqa: BLE001 - a module may raise anything at import time
    out.update(stage="import", verdict="IMPORT_ERROR",
               error=f"{type(exc).__name__}: {str(exc)[:300]}")
    print(json.dumps(out)); sys.exit(3)
out["stage"] = "import"
check = getattr(mod, "self_check", None)
if check is None:
    check = getattr(mod, "_self_check", None)
if not callable(check):
    out.update(verdict="NO_SELF_CHECK")
    print(json.dumps(out)); sys.exit(4)
import inspect
try:
    _sig = inspect.signature(check)
    _required = [p.name for p in _sig.parameters.values()
                 if p.default is inspect.Parameter.empty
                 and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
except (TypeError, ValueError):
    _required = []
if _required:
    # A self-check that needs an argument is not a contract an unattended instrument can call.
    out.update(stage="self_check_signature", verdict="SELF_CHECK_NEEDS_ARGS", required=_required)
    print(json.dumps(out)); sys.exit(8)
try:
    result = check()
except BaseException as exc:  # noqa: BLE001
    out.update(stage="self_check", verdict="SELF_CHECK_RAISED",
               error=f"{type(exc).__name__}: {str(exc)[:300]}")
    print(json.dumps(out)); sys.exit(5)
if not isinstance(result, dict):
    out.update(stage="self_check", verdict="SELF_CHECK_NOT_A_DICT",
               returned=type(result).__name__)
    print(json.dumps(out)); sys.exit(6)
passed = result.get("pass")
if passed is None:
    passed = result.get("ok")
if passed is None:
    # Accept the repo's actual convention: "SELF_CHECK_PASS", "PASS", "OK", "ALL_PASSED".
    label = str(result.get("verdict") or "").upper()
    passed = ("PASS" in label or label == "OK") and "FAIL" not in label
passed = bool(passed)
out.update(stage="self_check", verdict="SELF_CHECK_PASSED" if passed else "SELF_CHECK_FAILED",
           checks=result.get("checks"), passed_count=result.get("passed"))
print(json.dumps(out))
sys.exit(0 if passed else 7)
'''

def module_name(path: pathlib.Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)


def unimported_modules(root: pathlib.Path = ROOT / "canonical") -> List[pathlib.Path]:
    """Modules no other module imports by name. Entry points are legitimately unimported, which is
    why this is a *candidate* list and not a death list."""
    modules = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    imported: set[str] = set()
    for path in modules:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module)
                    for alias in node.names:
                        imported.add(f"{node.module}.{alias.name}")
                else:  # relative import: `from .sibling import thing`
                    for alias in node.names:
                        imported.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)

    # Compare on the *last* dotted component. `from canonical.swe_kernel.x_v1 import Y` reaches
    # `x_v1` exactly as surely as `import x_v1` does, and an earlier version of this rule compared
    # a bare filename stem against fully dotted names -- which "found" thousands of dark modules
    # that something in the tree was already importing.
    reached = {name.rsplit(".", 1)[-1] for name in imported}
    return [
        p for p in modules
        if p.stem not in reached and p.stem not in {"__init__", "conftest"}
    ]


_REPO_TOP_LEVEL = {
    "canonical", "execution_guard", "intake", "tools", "scripts", "arena", "docs", "tests",
}
_SUBSTRATE_MODULE_RE = re.compile(r"No module named '([^']+)'")
_SUBSTRATE_NAME_RE = re.compile(r"cannot import name '([^']+)' from '([^']+)'")
_SUBSTRATE_HINTS = (
    "temporary failure in name resolution", "connection refused", "cuda", "nvidia",
    "no cuda", "cuda driver", "out of memory", "no such file or directory: '/usr",
)


def _is_third_party(module: str) -> bool:
    root = (module or "").split(".")[0]
    if not root:
        return False
    if root in _REPO_TOP_LEVEL or root in sys.stdlib_module_names:
        return False
    return True


def all_modules(root: pathlib.Path = ROOT / "canonical") -> List[pathlib.Path]:
    """Every module under `canonical/`, whether or not something imports it.

    The no-importer list is not the whole unproven mass: most modules *are* reached by a peer and
    still cannot prove they run. This census is what says so.
    """
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _classify_failure(error: str) -> str:
    """Third-party absence is not the same finding as a broken module, and conflating them inflates
    the quarantine. Classify on the *error text only* -- never on the module's own name, which is
    how `.../torch_utils.py` used to masquerade as a missing GPU."""
    blob = error or ""
    lowered = blob.lower()
    match = _SUBSTRATE_MODULE_RE.search(blob)
    if match:
        return MISSING_SUBSTRATE if _is_third_party(match.group(1)) else BROKEN
    match = _SUBSTRATE_NAME_RE.search(blob)
    if match:
        # `cannot import name 'x' from 'canonical.y'` is a broken in-repo import, not missing kit.
        return MISSING_SUBSTRATE if _is_third_party(match.group(2)) else BROKEN
    if any(hint in lowered for hint in _SUBSTRATE_HINTS):
        return MISSING_SUBSTRATE
    # A path we cannot touch outside the repo is the environment's limit, not a defect in the code.
    if ("PermissionError" in blob or "FileNotFoundError" in blob) and re.search(
            r"'(/[^']*)'", blob):
        outside = re.findall(r"'(/[^']*)'", blob)
        if all(not str(ROOT) in path for path in outside):
            return MISSING_SUBSTRATE
    return BROKEN


@dataclass
class Verdict:
    module: str
    path: str
    loc: int
    verdict: str
    stage: str
    elapsed_ms: float
    evidence: Dict[str, Any]

    def ok(self) -> bool:
        return self.verdict == PROVEN


@dataclass
class _Probe:
    payload: Dict[str, Any]
    returncode: int
    stderr: str
    elapsed_ms: float


def _probe(name: str, *, timeout: float,
           extra_paths: Optional[Sequence[str]] = None) -> _Probe:
    """Run the probe in its own interpreter, in a scratch cwd.

    The scratch cwd is deliberate: several of the 1,996 candidates write files at import time, and
    adjudicating them from inside the repository would let the measurement mutate the thing it
    measures.
    """
    import os
    import tempfile

    t0 = time.perf_counter()
    env = {**os.environ,
           "PYTHONPATH": ":".join([str(ROOT)] + [str(x) for x in (extra_paths or [])]),
           "HOME": "/tmp"}
    try:
        with tempfile.TemporaryDirectory(prefix="dm_probe_") as scratch:
            done = subprocess.run([sys.executable, "-c", _PROBE, name], cwd=scratch,
                                  capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return _Probe({"module": name, "verdict": "TIMEOUT", "stage": "timeout",
                       "error": f"no finish in {timeout}s"},
                      124, "", round((time.perf_counter() - t0) * 1000.0, 2))
    payload: Dict[str, Any] = {}
    for line in (done.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
    return _Probe(payload, done.returncode, done.stderr or "",
                  round((time.perf_counter() - t0) * 1000.0, 2))


def _to_verdict(name: str, path: str, loc: int, probe: _Probe) -> Verdict:
    """One mapping from probe payload to fail-closed state, so the two call paths cannot drift."""
    verdict = str(probe.payload.get("verdict") or "")
    stage = str(probe.payload.get("stage") or "import")
    evidence: Dict[str, Any] = {"probe": verdict or "no_json", "returncode": probe.returncode}
    if probe.payload.get("error"):
        evidence["error"] = probe.payload["error"]
    if probe.payload.get("required"):
        evidence["required_arguments"] = probe.payload["required"]
    if probe.payload.get("checks") is not None:
        evidence["checks"] = probe.payload.get("checks")
        evidence["passed_count"] = probe.payload.get("passed_count")
    if probe.stderr.strip():
        evidence["stderr_tail"] = probe.stderr.strip().splitlines()[-1:]
    if verdict == "SELF_CHECK_PASSED":
        return Verdict(name, path, loc, PROVEN, "self_check", probe.elapsed_ms, evidence)
    if verdict == "NO_SELF_CHECK":
        return Verdict(name, path, loc, IMPORTS_ONLY, "import", probe.elapsed_ms, evidence)
    if verdict == "TIMEOUT":
        return Verdict(name, path, loc, BROKEN, "timeout", probe.elapsed_ms, evidence)
    if verdict in {"IMPORT_ERROR", "SELF_CHECK_RAISED"}:
        return Verdict(name, path, loc, _classify_failure(str(probe.payload.get("error") or "")),
                       stage, probe.elapsed_ms, evidence)
    # SELF_CHECK_FAILED / NOT_A_DICT / unknown: the module answered, and the answer was not proof.
    return Verdict(name, path, loc, BROKEN, stage, probe.elapsed_ms, evidence)


def adjudicate_one(path: pathlib.Path, *, timeout: float, probe: bool = True) -> Verdict:
    name = module_name(path)
    rel = str(path.relative_to(ROOT))
    loc = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    if not probe:
        return Verdict(name, rel, loc, IMPORTS_ONLY, "ablation", 0.0,
                       {"probe": "disabled", "reason": "ABLATION_NO_EXECUTION"})
    return _to_verdict(name, rel, loc, _probe(name, timeout=timeout))


def adjudicate_importable(name: str, *, timeout: float = 25.0,
                          extra_paths: Optional[Sequence[str]] = None) -> Verdict:
    """Probe by dotted name (self-check fixtures, and callers that already resolved a name)."""
    return _to_verdict(name, name, 0, _probe(name, timeout=timeout, extra_paths=extra_paths))


def run(
    *,
    limit: Optional[int] = None,
    workers: int = 24,
    timeout: float = 25.0,
    probe: bool = True,
    min_loc: int = 0,
    include_tests: bool = False,
    patterns: Optional[Sequence[str]] = None,
    modules: Optional[Iterable[pathlib.Path]] = None,
    everything: bool = False,
) -> Dict[str, Any]:
    if modules is not None:
        candidates = list(modules)
    elif everything:
        candidates = all_modules()
    else:
        candidates = unimported_modules()
    if not include_tests:
        candidates = [p for p in candidates if "tests" not in p.parts and not p.stem.startswith("test_")]
    if patterns:
        lowered = [p.lower() for p in patterns]
        candidates = [p for p in candidates if any(s in p.stem.lower() for s in lowered)]
    if min_loc > 0:
        candidates = [
            p for p in candidates
            if len(p.read_text(encoding="utf-8", errors="replace").splitlines()) >= min_loc
        ]
    candidates = sorted(candidates)
    if limit is not None:
        candidates = candidates[:limit]

    t0 = time.perf_counter()
    verdicts: List[Verdict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(adjudicate_one, p, timeout=timeout, probe=probe): p
                   for p in candidates}
        for fut in concurrent.futures.as_completed(futures):
            try:
                verdicts.append(fut.result())
            except Exception as exc:  # noqa: BLE001 - a worker crash is a BROKEN candidate
                p = futures[fut]
                verdicts.append(Verdict(module_name(p), str(p.relative_to(ROOT)), 0, BROKEN,
                                        "worker", 0.0, {"error": f"{type(exc).__name__}: {exc}"}))

    counts = {v: 0 for v in VERDICTS}
    for verdict in verdicts:
        counts[verdict.verdict] = counts.get(verdict.verdict, 0) + 1
    proven = sorted((v for v in verdicts if v.ok()), key=lambda v: -v.loc)
    body = {
        "schema": SCHEMA,
        "candidates": len(candidates),
        "candidate_scope": "every_module" if everything else "no_importer",
        "probe_enabled": probe,
        "min_loc": min_loc,
        "timeout_s": timeout,
        "workers": workers,
        "counts": counts,
        "proven_loc": sum(v.loc for v in proven),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "verdicts": [asdict(v) for v in sorted(verdicts, key=lambda v: v.module)],
        "proven_ranked": [{"module": v.module, "path": v.path, "loc": v.loc} for v in proven],
    }
    body["digest"] = hashlib.sha256(
        json.dumps({k: v for k, v in body.items() if k != "elapsed_ms"}, sort_keys=True).encode()
    ).hexdigest()
    return body


def self_check() -> Dict[str, Any]:
    """Four fabricated modules, one per verdict, in a scratch package. If the instrument cannot
    separate these four it cannot be trusted on 6,114 real ones."""
    import importlib
    import tempfile

    checks: List[bool] = []
    with tempfile.TemporaryDirectory() as tmp:
        pkg = pathlib.Path(tmp) / "probe_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "good_v1.py").write_text(
            "def self_check():\n    return {'pass': True, 'checks': 3, 'passed': 3}\n"
        )
        (pkg / "says_no_v1.py").write_text(
            "def self_check():\n    return {'pass': False, 'checks': 3, 'passed': 1}\n"
        )
        (pkg / "raises_v1.py").write_text(
            "def self_check():\n    raise RuntimeError('boom')\n"
        )
        (pkg / "no_check_v1.py").write_text("VALUE = 1\n")

        results = {}
        for name in ("good_v1", "says_no_v1", "raises_v1", "no_check_v1"):
            importlib.invalidate_caches()
            results[name] = adjudicate_importable(f"probe_pkg.{name}", timeout=20.0,
                                                  extra_paths=[tmp])

        checks.append(results["good_v1"].verdict == PROVEN)
        checks.append(results["says_no_v1"].verdict == BROKEN)
        checks.append(results["raises_v1"].verdict == BROKEN)
        checks.append(results["no_check_v1"].verdict == IMPORTS_ONLY)
        checks.append(len({r.verdict for r in results.values()}) == 3)
    return {
        "schema": f"{SCHEMA}_SELF_CHECK",
        "checks": len(checks),
        "passed": sum(1 for c in checks if c),
        "verdict": "SELF_CHECK_PASS" if all(checks) else "SELF_CHECK_FAIL",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Adjudicate unimported modules: proven or claim?")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--min-loc", type=int, default=0)
    parser.add_argument("--pattern", action="append", default=[])
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--all-modules", action="store_true",
                        help="census every module, not only the ones nothing imports")
    parser.add_argument("--no-probe", action="store_true", help="ablation: never execute anything")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)

    if args.self_check:
        report = self_check()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["verdict"] == "SELF_CHECK_PASS" else 1

    report = run(
        limit=args.limit or None,
        workers=args.workers,
        timeout=args.timeout,
        probe=not args.no_probe,
        min_loc=args.min_loc,
        include_tests=args.include_tests,
        patterns=args.pattern or None,
        everything=args.all_modules,
    )
    if args.json:
        path = pathlib.Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {path}")

    print(f"candidates {report['candidates']} ({report['candidate_scope']})  "
          f"probe={report['probe_enabled']}  "
          f"{report['elapsed_ms']} ms")
    for verdict in VERDICTS:
        print(f"  {verdict:<18} {report['counts'][verdict]:>5}")
    print(f"  proven lines       {report['proven_loc']:>5}")
    for row in report["proven_ranked"][:10]:
        print(f"    PROVEN {row['loc']:>5}L  {row['module']}")
    print("digest", report["digest"][:16])
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
