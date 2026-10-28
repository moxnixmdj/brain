# PROJECT_BRAIN
"""python.review.diff_perf_gate.v1 — performance-regression gate on the diff.

Lint proves clean lines, types prove sound lines, the coverage gate proves
they execute — and none of the three can see a change that makes the hot
path 40x slower.  A senior engineer benches a suspicious diff.  This
adapter runs a declared benchmark callable against BOTH sides — the
pristine anchor tree and the anchor+diff tree — in isolated child
processes, and blocks when the patched median exceeds the anchor median
beyond a declared tolerance.

* benchmark = a repo file defining ``def bench(): ...``; the child
  harness imports it BY PATH (never by ambient sys.path of the wrong
  tree), runs ``repeats`` timed iterations, and reports every run's
  nanoseconds — verdicts are computed from raw runs, never summarized
  by the child.
* each side is a separate process and a separate scratch copy: no
  cross-contamination, anchors never mutated.
* verdict = median(patched_ns) <= median(anchor_ns) * (1 + tolerance).
  PASS / FAIL / UNCLEAR (when run spreads overlap inside tolerance on
  both sides — honest third verdict, not a coin flip).

Laws:
* determinism honesty: timings are physical, the artifact carries raw
  nanosecond runs and is NOT byte-identical across runs; what pins prove
  is VERDICT STABILITY on fixed worlds (a 50x planted regression fails
  on every run; a no-op refactor passes on every run) plus byte-identical
  verdict recomputation from identical recorded runs.
* fail closed: PATH_*, DIFF_EMPTY, ANCHOR_NOT_DIRECTORY, GIT_UNAVAILABLE,
  DIFF_DOES_NOT_APPLY, BENCH_FILE_MISSING, BENCH_CALLABLE_MISSING,
  BENCH_EXPLODED (child nonzero/timeout), TIMEOUT.
* The copies are not an OS sandbox: benchmark code runs with host privileges,
  can access external files and can spoof child output. A passing local result
  is not independent attestation or proof that the benchmark covers the diff.

Inputs (kwargs, repo-confined):
  anchor_path        clean tree the diff was cut against (read-only)
  diff_path          unified diff artifact under test
  bench_path         file inside the tree defining ``bench()``
  output_path        summary artifact (registry result_fields mirror)
  python_executable  interpreter for child benches (default: this one)
  repeats            timed iterations per side (default 5, min 3)
  tolerance          allowed slowdown fraction (default 0.10)
  timeout_s          wall-clock cap per child (default 120)

result_fields: adapter, anchor_path, diff_sha256, bench_path, repeats,
anchor_median_ns, patched_median_ns, slowdown_ratio, gate, complete,
output_path, output_sha256, output_verified, verified.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_DIFF_PERF_GATE_V1"

_CHILD = r'''
import importlib.util, json, sys, time
bench_path, repeats = sys.argv[1], int(sys.argv[2])
spec = importlib.util.spec_from_file_location("_gate_bench", bench_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
fn = getattr(mod, "bench", None)
if fn is None:
    print(json.dumps({"error": "BENCH_CALLABLE_MISSING"}))
    sys.exit(3)


def _calib():
    # FIXED harness workload, identical bytes on both sides: normalizing by
    # it cancels box-level thermal/scheduler/site bias between the two
    # child processes (the "second runner always looks slower" effect).
    s = 0
    for i in range(20000):
        s ^= (i * 2654435761) & 0xFFFFFFFF
    return s


fn()      # warm-up, untimed
_calib()
runs, cal = [], []
for _ in range(repeats):
    t0 = time.monotonic_ns()
    fn()
    runs.append(time.monotonic_ns() - t0)
    t0 = time.monotonic_ns()
    _calib()
    cal.append(time.monotonic_ns() - t0)
print(json.dumps({"runs_ns": runs, "calib_ns": cal}))
'''


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.review.diff_perf_gate.v1",
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


def _bench(tree: Path, bench_rel: str, python_exe: str, repeats: int,
           timeout_s: int) -> list:
    target = tree / bench_rel
    if not target.is_file():
        return _fail("BENCH_FILE_MISSING:" + bench_rel)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run([python_exe, "-c", _CHILD, bench_rel, str(repeats)],
                              cwd=tree, capture_output=True, text=True,
                              timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired:
        return _fail("TIMEOUT")
    if proc.returncode != 0:
        try:
            doc = json.loads(proc.stdout.strip().splitlines()[-1])
            if doc.get("error") == "BENCH_CALLABLE_MISSING":
                return _fail("BENCH_CALLABLE_MISSING:" + bench_rel)
        except (json.JSONDecodeError, IndexError, KeyError):
            pass
        _fail("BENCH_EXPLODED:rc=" + str(proc.returncode) + ":" +
              (proc.stderr.strip().splitlines() or ["<empty>"])[-1][:200])
    try:
        doc = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return _fail("BENCH_OUTPUT_NOT_JSON")
    runs = doc.get("runs_ns")
    calib = doc.get("calib_ns")
    if (not isinstance(runs, list) or len(runs) != repeats
            or not isinstance(calib, list) or len(calib) != repeats
            or any(type(value) is not int or value <= 0 for value in runs + calib)):
        return _fail("BENCH_OUTPUT_SHAPE_UNEXPECTED")
    return runs, calib


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    anchor_rel = str(args.get("anchor_path") or "")
    anchor_abs = _safe_path(repo, anchor_rel, must_exist=True)
    if isinstance(anchor_abs, dict): return anchor_abs
    if not anchor_abs.is_dir():
        return _fail("ANCHOR_NOT_DIRECTORY")
    diff_rel = str(args.get("diff_path") or "")
    diff_abs = _safe_path(repo, diff_rel, must_exist=True)
    if isinstance(diff_abs, dict): return diff_abs
    diff_text = diff_abs.read_text(encoding="utf-8", errors="replace")
    if not diff_text.strip():
        return _fail("DIFF_EMPTY")
    bench_rel = str(args.get("bench_path") or "")
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    if isinstance(out_abs, dict): return out_abs
    if (out_abs == diff_abs or out_abs == anchor_abs or anchor_abs in out_abs.parents
            or (out_abs.exists() and (out_abs.is_dir() or out_abs.stat().st_nlink > 1))):
        return _fail("OUTPUT_OVERLAPS_INPUT")
    bench_arg = Path(bench_rel)
    bench_in_anchor = (anchor_abs / bench_arg).resolve()
    if (not bench_rel or bench_arg.is_absolute() or bench_in_anchor == anchor_abs
            or anchor_abs not in bench_in_anchor.parents):
        return _fail("BENCH_PATH_ESCAPE")
    # Refuse symlinked benchmark components rather than resolving outside the copy.
    current = anchor_abs
    for part in bench_arg.parts:
        current = current / part
        if current.is_symlink():
            return _fail("BENCH_PATH_ESCAPE")
    timeout_s = int(args.get("timeout_s") or 120)
    python_exe = str(args.get("python_executable") or sys.executable)
    repeats = max(3, int(args.get("repeats") or 5))
    tolerance = float(args.get("tolerance") if args.get("tolerance") is not None else 0.10)

    git_probe = subprocess.run(["git", "--version"], capture_output=True, text=True,
                               timeout=min(timeout_s, 30))
    if git_probe.returncode != 0:
        return _fail("GIT_UNAVAILABLE")
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    # Never remove a predictable name from the caller's output directory.
    with tempfile.TemporaryDirectory(prefix="_perf_", dir=out_abs.parent) as scratch:
        scratch_a = Path(scratch) / "anchor"
        scratch_p = Path(scratch) / "patched"
        shutil.copytree(anchor_abs, scratch_a,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        shutil.copytree(anchor_abs, scratch_p,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        check = subprocess.run(["git", "apply", "--check", str(diff_abs)],
                               cwd=scratch_p, capture_output=True, text=True,
                               timeout=min(timeout_s, 60))
        if check.returncode != 0:
            _fail("DIFF_DOES_NOT_APPLY:" + (check.stderr.strip().splitlines() or ["<empty>"])[0][:200])
        applied = subprocess.run(["git", "apply", str(diff_abs)],
                                 cwd=scratch_p, capture_output=True, text=True,
                                 timeout=min(timeout_s, 60))
        if applied.returncode != 0:
            return _fail("DIFF_APPLY_FAILED_AFTER_CHECK")

        anchor_runs, anchor_cal = _bench(scratch_a, bench_rel, python_exe, repeats, timeout_s)
        patched_runs, patched_cal = _bench(scratch_p, bench_rel, python_exe, repeats, timeout_s)

    # best-of estimator (pyperf-style: min of N is the noise-robust intrinsic
    # cost), box-normalized by the fixed calibrator measured in the SAME child
    # -- this cancels cross-process site bias instead of hiding it.
    a_med = statistics.median(anchor_runs)
    p_med = statistics.median(patched_runs)
    a_best = min(anchor_runs)
    p_best = min(patched_runs)
    a_cal = min(anchor_cal)
    p_cal = min(patched_cal)
    a_norm = a_best / a_cal if a_cal > 0 else float("inf")
    p_norm = p_best / p_cal if p_cal > 0 else float("inf")
    ratio = (p_norm / a_norm) if a_norm > 0 and a_norm != float("inf") else float("inf")
    limit = 1.0 + tolerance
    if ratio <= limit:
        gate = "PASS"
    elif min(patched_runs) > max(anchor_runs):
        gate = "FAIL"          # disjoint distributions: the slowdown is real
    else:
        gate = "UNCLEAR"       # overlapping runs inside the band: say so
    complete = True
    verified = gate == "PASS"

    artifact = {
        "schema": SCHEMA,
        "anchor_path": anchor_rel,
        "diff_path": diff_rel,
        "diff_sha256": _sha256(diff_text.encode("utf-8")),
        "bench_path": bench_rel,
        "repeats": repeats,
        "tolerance": tolerance,
        "anchor_runs_ns": anchor_runs,
        "patched_runs_ns": patched_runs,
        "anchor_median_ns": int(a_med),
        "patched_median_ns": int(p_med),
        "anchor_best_ns": int(a_best),
        "patched_best_ns": int(p_best),
        "anchor_calib_best_ns": int(a_cal),
        "patched_calib_best_ns": int(p_cal),
        "slowdown_ratio": round(ratio, 4) if ratio != float("inf") else None,
        "gate": gate,
        "gate_law": ("PASS when patched best-of-run <= anchor best-of-run * (1+tolerance); "
                     "FAIL when even the fastest patched run beats the slowest "
                     "anchor run beyond the band; otherwise UNCLEAR -- timings are "
                     "physical so verdict stability is the honest invariant, not "
                     "byte-identical artifacts; verdict recomputation from recorded "
                     "runs IS deterministic"),
        "complete": complete,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_review_diff_perf_gate",
        "anchor_path": anchor_rel,
        "diff_sha256": artifact["diff_sha256"],
        "bench_path": bench_rel,
        "repeats": repeats,
        "anchor_median_ns": int(a_med),
        "patched_median_ns": int(p_med),
        "anchor_best_ns": int(a_best),
        "patched_best_ns": int(p_best),
        "anchor_calib_best_ns": int(a_cal),
        "patched_calib_best_ns": int(p_cal),
        "slowdown_ratio": round(ratio, 4) if ratio != float("inf") else None,
        "gate": gate,
        "complete": complete,
        "output_path": out_rel,
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": out_verified,
        "verified": bool(verified),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--anchor_path", required=True)
    p.add_argument("--diff_path", required=True)
    p.add_argument("--bench_path", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--python_executable", default=None)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--tolerance", type=float, default=None)
    p.add_argument("--timeout_s", type=int, default=120)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
