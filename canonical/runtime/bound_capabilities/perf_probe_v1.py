# PROJECT_BRAIN
"""python.perf.{memory_profile,cpu_profile,benchmark}.v1 — the three performance measurements a
senior engineer actually runs, on the stdlib instruments that were already installed.

The inventory's performance row read 2/6 bound and four acts absent: no memory profile, no CPU
hotspot ranking, no growth-class inference.  None of that needs a new dependency.  `tracemalloc`
measures where the bytes went, `cProfile` + `pstats` rank where the time went, and a wall clock
plus a shape test infers whether the cost grows linearly, quadratically or worse.  The instruments
are in the interpreter; what was missing was a verb that states the answer in a form a reader can
check.

Three laws, all of them consequences of measuring:

1. **Profile in a child, never in this process.** A program being profiled may crash, hang or eat
   the box; the same isolation the fuzzer uses applies here, so a measurement that cannot complete
   is an outcome, not a lost run.
2. **A number without its worst case is a rumour.** A memory profile reports the peak it saw, the
   call that produced it, and the cases that ran; a CPU profile reports the ranked hotspots of the
   slowest call, not an average of everything.
3. **A growth class is a FIT, stated as a fit.** Benchmarking reports the measured times, the
   candidate classes and the residual spread of each — the class is the shape that explains the
   measurements best, and the runner-up is printed beside it, so nobody reads a curve as a theorem.

Inputs (kwargs, repo-confined):
  source_root        the file or project to measure
  qualname           the function to measure (default: every public function in scope)
  max_cases          cases per function (default 16, from the same annotation-directed generator)
  sizes              input sizes for the growth fit (default 64,128,256,512)
  n_index            which positional parameter carries the size (default 0)
  repeat             timed repetitions per size (default 3, minimum kept)
  case_timeout_s     per-case wall clock (default 10)
  output_path        the artifact

result_fields: adapter, capability_id, act, target, module, qualname, cases_run, peak_bytes,
hotspots, best_class, timings, gate, complete, output_path, output_sha256, output_verified.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from canonical.runtime.bound_capabilities.dynamic_probe_v1 import (
    DEFAULT_CASE_TIMEOUT_S,
    _cases,
    _locate,
    _public_functions,
    _target_function,
)
from canonical.runtime.bound_capabilities.quality_v1 import (
    QualityError,
    _base,
    _destination,
    _fail,
    _write,
)

ACTS = ("memory_profile", "cpu_profile", "benchmark")
DEFAULT_CASES = 16
DEFAULT_SIZES = (64, 128, 256, 512, 1024, 2048)
# A PROFILER MEASURES SHAPE, NOT EXTREMES.  The fuzzer's generator deliberately draws 2**63 and
# `sys.maxsize`, which is right for finding a crash and wrong for measuring cost: a case that eats
# the box until the wall clock kills it reports nothing about where the bytes or the time go.
# Perf cases are the same generator's output, filtered to inputs a profile can finish.
_PERF_MAX_INT = 4096
_PERF_MAX_STR = 256
_PERF_MAX_SEQ = 512


def _measurable(value) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return abs(value) <= _PERF_MAX_INT
    if isinstance(value, float):
        return math.isfinite(value) and abs(value) <= _PERF_MAX_INT
    if isinstance(value, (str, bytes)):
        return len(value) <= _PERF_MAX_STR
    if isinstance(value, (list, tuple)):
        return len(value) <= _PERF_MAX_SEQ and all(_measurable(item) for item in value)
    return value is None
DEFAULT_REPEAT = 5

# The child measures and prints exactly one JSON line.  It loads the module BY PATH under a private
# alias, so the module under measurement cannot be shadowed by a package of the same name.
_HARNESS = r"""
import cProfile, io, json, pstats, sys, time, tracemalloc, importlib.util
spec = json.loads(sys.argv[1])

def load(path, alias):
    loader = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(loader)
    sys.modules[alias] = module
    loader.loader.exec_module(module)
    return module

def resolve(module, qualname):
    fn = module
    for part in qualname.split("."):
        fn = getattr(fn, part)
    return fn

try:
    module = load(spec["path"], "brain_perf_target")
    fn = resolve(module, spec["qualname"])
except BaseException as exc:
    print(json.dumps({"outcome": "unimportable", "exc": type(exc).__name__, "msg": str(exc)[:300]}))
    raise SystemExit(0)

def call(args):
    # (the returned value, the outcome).  THE VALUE IS RETURNED, not just its repr: a snapshot
    # taken after the value was garbage-collected shows nothing, which is how a memory profile
    # came back with a peak of 55 KB and a top site of 249 bytes.
    try:
        value = fn(*args)
    except BaseException as exc:
        return None, {"outcome": "raised", "exc": type(exc).__name__, "msg": str(exc)[:300]}
    return value, {"outcome": "ok", "repr": repr(value)[:200]}

mode = spec["mode"]
if mode == "memory":
    # DEPTH MATTERS.  tracemalloc's default is ONE frame, which is this harness -- so every site
    # in the report was `<string>:30`, the profiler's own line, and never the code being measured.
    tracemalloc.start(8)
    base = tracemalloc.get_traced_memory()[0]
    held, result = call(spec["args"])
    current, peak = tracemalloc.get_traced_memory()
    sites = []
    if result["outcome"] == "ok":
        # taken while `held` is still alive, because the interesting bytes are the ones the call
        # RETURNED -- a profile of freed intermediates measures the collector, not the program
        snapshot = tracemalloc.take_snapshot()
        # A SITE MUST BE A SITE IN THE TARGET (or in a library it called).  The harness's own
        # lines live in `<string>`, and they used to sit at the top of the list.
        stats = [stat for stat in snapshot.statistics("lineno")[:32]
                 if not str(stat.traceback[0].filename).endswith("<string>")][:8]
        for stat in stats:
            # ATTRIBUTE TO THE TARGET, NOT TO THE HARNESS.  The deepest frame of the traceback is
            # the line that allocated; the outer frame is always this harness's own `fn(*args)`,
            # and reporting that would name the profiler instead of the code being measured.
            frame = stat.traceback[0]
            sites.append({"site": "%s:%s" % (str(frame.filename).rsplit("/", 1)[-1],
                                             frame.lineno),
                          "size_bytes": int(stat.size)})
    tracemalloc.stop()
    result.update({"peak_bytes": int(peak), "current_bytes": int(current),
                   "grew_bytes": int(peak - base), "top_sites": sites})
    del held
    print(json.dumps(result))
elif mode == "cpu":
    profiler = cProfile.Profile()
    profiler.enable()
    held, result = call(spec["args"])
    profiler.disable()
    rows = []
    # `Profile.getstats()` is a list of opaque entries; `pstats.Stats.stats` is the documented
    # mapping keyed by (file, line, function) -- measured: unpacking getstats() raised
    # ValueError: too many values, and the CPU profile came back empty for every case.
    stats = pstats.Stats(profiler)
    for (filename, line, name), values in stats.stats.items():
        cc, nc, tt, ct = values[:4]
        if filename.endswith("<string>"):
            continue
        # THE PROFILER'S OWN STUBS ARE NOT HOTSPOTS.  Measured: `<method 'disable' of
        # '_lsprof.Profiler' objects>` ranked third on a one-line loop, because the profiler
        # profiles the call that switches it off.
        if "_lsprof.Profiler" in name or name in ("enable", "disable", "call"):
            continue
        rows.append({"function": name, "file": filename.rsplit("/", 1)[-1], "line": line,
                     "ncalls": int(nc), "tottime_s": float(tt), "cumtime_s": float(ct)})
    rows.sort(key=lambda row: row["cumtime_s"], reverse=True)
    result.update({"wall_s": None, "hotspots": rows[:12]})
    print(json.dumps(result))
elif mode == "benchmark_sweep":
    # THE WHOLE SWEEP IN ONE CHILD.  Importing the module and starting an interpreter cost more
    # than the measured call at small sizes, so one process per size put that noise straight into
    # the curve (measured: a linear loop came back with a 0.5 spread and no class at all).  One
    # child, one import, one warm-up and then the ladder -- with the parent still isolating if
    # this child dies.
    seconds = []
    outcomes = []
    for args in spec["args_by_size"]:
        call(args)
        best = None
        for _ in range(int(spec.get("repeat") or 1)):
            started = time.perf_counter()
            _value, result = call(args)
            elapsed = time.perf_counter() - started
            best = elapsed if best is None else min(best, elapsed)
        seconds.append(best)
        outcomes.append(result["outcome"])
    print(json.dumps({"outcome": "ok", "seconds": seconds, "outcomes": outcomes}))
else:
    started = time.perf_counter()
    held, result = call(spec["args"])
    elapsed = time.perf_counter() - started
    result.update({"seconds": float(elapsed), "outcome_time": result["outcome"]})
    print(json.dumps(result))
"""


def _child(python_exe: str, spec: dict, timeout_s: int) -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run([python_exe, "-c", _HARNESS, json.dumps(spec)],
                              capture_output=True, text=True, timeout=timeout_s, env=env,
                              check=False)
    except subprocess.TimeoutExpired:
        return {"outcome": "timeout", "exc": "Timeout", "msg": f"{timeout_s}s"}
    for line in (proc.stdout or "").strip().splitlines():
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {"outcome": "crashed", "exc": "ProcessCrash",
            "msg": f"rc={proc.returncode} {(proc.stderr or '').strip()[-200:]}"}


def _candidates(args: dict, project: Path, module_file: Path, module: str
                ) -> list[tuple[Path, str, str]]:
    """(file, dotted module, function) for everything the sentence puts in scope."""
    only = str(args.get("qualname") or "").strip()
    if module_file.is_dir():
        modules = [(path, (str(path.relative_to(project)).replace(os.sep, "/")
                           .removesuffix(".py").replace("/", ".")))
                   for path in sorted(module_file.rglob("*.py"))
                   if not path.name.startswith("_")]
        if not modules:
            _fail("NO_PYTHON_MODULE_IN:" + str(module_file))
    else:
        modules = [(module_file, module)]
    found: list[tuple[Path, str, str]] = []
    for path, dotted in modules:
        for name in ([only] if only else _public_functions(path)):
            found.append((path, dotted, name))
    if not found:
        _fail("NO_FUNCTION_TO_MEASURE_IN:" + module_file.name)
    return found


def _measures_for(args: dict, project: Path, path: Path, qualname: str) -> tuple[list, int]:
    try:
        node, params, defaults = _target_function(project, path, qualname)
    except QualityError:
        return [], 0
    max_cases = int(args.get("max_cases") or DEFAULT_CASES)
    seed = int(args.get("seed") or 0)
    arity = max(1, len(params) - defaults)
    generated = [case for case in _cases(node, params, defaults, seed, max_cases * 4)
                 if all(_measurable(value) for value in case)]
    # THE LADDER IS ALWAYS PRESENT.  The fuzzer's boundary corpus tops out at 2**63, which a
    # profile cannot finish, so the small draws left were 0, 1, 2 and 7 -- a memory profile of
    # "seven items" measures nothing.  A geometric ladder gives every measured call a size that
    # actually allocates and actually runs, and the filtered draws come along beside it.
    for size in (8, 64, 512):
        generated.append([size] * arity)
    unique: list[list] = []
    for case in generated:
        if case not in unique:
            unique.append(case)
    return unique[:max_cases], max_cases


def _memory_or_cpu(args: dict, mode: str, project: Path, module_file: Path, module: str,
                   python_exe: str) -> dict:
    case_timeout = int(args.get("case_timeout_s") or DEFAULT_CASE_TIMEOUT_S)
    # the child speaks `memory` / `cpu`; the ACT names say which measurement, not which harness
    child_mode = "memory" if mode == "memory_profile" else "cpu"
    rows: list[dict] = []
    worst: dict | None = None
    cases_run = 0
    for path, dotted, qualname in _candidates(args, project, module_file, module):
        cases, _max = _measures_for(args, project, path, qualname)
        for case in cases:
            outcome = _child(python_exe, {"mode": child_mode, "path": str(path),
                                          "qualname": qualname, "args": case}, case_timeout)
            cases_run += 1
            if outcome.get("outcome") == "unimportable":
                _fail("MODULE_NOT_IMPORTABLE:" + str(outcome.get("msg")))
            score = (int(outcome.get("peak_bytes") or 0) if child_mode == "memory"
                     else sum(float(row.get("cumtime_s") or 0.0)
                              for row in (outcome.get("hotspots") or [])))
            row = {"module": dotted, "qualname": qualname, "args": case,
                   "outcome": outcome.get("outcome"), "score": score}
            if child_mode == "memory":
                row["peak_bytes"] = int(outcome.get("peak_bytes") or 0)
                row["top_sites"] = outcome.get("top_sites") or []
            else:
                row["hotspots"] = outcome.get("hotspots") or []
            rows.append(row)
            if worst is None or score > worst["score"]:
                worst = row
    rows.sort(key=lambda item: item["score"], reverse=True)
    return {"cases_run": cases_run, "ranking": rows[:20], "worst": worst}


# The candidate shapes, each with the exponent that its log-log line has.  `n log n` sits just
# above 1 because over a finite ladder that is what it looks like; the point of the exponent is
# to say which SHAPE the data is nearest, not to define the shapes.
_GROWTH = (
    ("O(1)", 0.0),
    ("O(log n)", 0.1),
    ("O(n)", 1.0),
    ("O(n log n)", 1.1),
    ("O(n^2)", 2.0),
    ("O(n^3)", 3.0),
)


def _fit(sizes: list[int], seconds: list[float]) -> dict:
    """Which shape the measurements lie on, and how well they lie on it.

    The test is the standard one: a power law is a straight line in log-log space.  So fit
    `log t = p log n + c` by least squares, report `p` (the empirical exponent) and `r2` (how
    straight the line is), and take the candidate whose exponent is nearest `p`.

    A class is CLAIMED only when the line is straight (`r2 >= 0.98`) AND the exponent is within
    0.25 of that class -- because a noisy ladder can be nearest to `O(n^2)` while being no line at
    all, and calling that a growth class would be a confident wrong answer.  `slope` and `r2` are
    always reported, so an unresolved fit still says what it saw.
    """
    usable = [(float(n), float(t)) for n, t in zip(sizes, seconds) if t > 0 and n > 0]
    if len(usable) < 3:
        return {"best_class": None, "unresolved_best": None, "resolved": False,
                "slope": None, "r2": None, "scores": {},
                "why": "fewer than three positive measurements, so no line can be fitted"}
    xs = [math.log(n) for n, _t in usable]
    ys = [math.log(t) for _n, t in usable]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    if sxx == 0:
        return {"best_class": None, "unresolved_best": None, "resolved": False, "slope": None,
                "r2": None, "scores": {}, "why": "every size was the same"}
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    ss_res = sum(r * r for r in residuals)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    scored = sorted(((abs(slope - exponent), name) for name, exponent in _GROWTH))
    nearest_distance, nearest = scored[0]
    resolved = bool(r2 >= 0.98 and nearest_distance <= 0.25)
    return {"best_class": nearest if resolved else None,
            "unresolved_best": nearest,
            "resolved": resolved,
            "slope": round(slope, 3),
            "r2": round(r2, 4),
            "scores": {name: round(distance, 3) for distance, name in scored},
            "why": ("least-squares fit of log(time) against log(size): `slope` is the empirical "
                    "exponent and `r2` is how straight the line is; a class is claimed only when "
                    "the line is straight (r2 >= 0.98) and the exponent is within 0.25 of it")}


def _call_args(sizes: list[int], arity: int, n_index: int, takes_list: bool) -> list[list]:
    """The ladder, as one argument list per size, with the size in the parameter that carries it."""
    plans: list[list] = []
    for size in sizes:
        call_args = [0] * arity
        if n_index < arity:
            call_args[n_index] = [0] * size if takes_list else size
        plans.append(call_args)
    return plans


def _benchmark(args: dict, project: Path, module_file: Path, module: str, python_exe: str) -> dict:
    sizes = [int(n) for n in (args.get("sizes") or DEFAULT_SIZES)]
    repeat = max(1, int(args.get("repeat") or DEFAULT_REPEAT))
    n_index = int(args.get("n_index") or 0)
    case_timeout = int(args.get("case_timeout_s") or DEFAULT_CASE_TIMEOUT_S)
    measured: list[dict] = []
    for path, dotted, qualname in _candidates(args, project, module_file, module):
        try:
            _node, params, _defaults = _target_function(project, path, qualname)
        except QualityError:
            continue
        annotations = [str(getattr(param.annotation, "id", "")) for param in params]
        takes_list = ("list" in annotations[min(n_index, len(annotations) - 1)]
                      if annotations else False)
        plans = _call_args(sizes, len(params), n_index, takes_list)
        outcome = _child(python_exe, {"mode": "benchmark_sweep", "path": str(path),
                                      "qualname": qualname, "args_by_size": plans,
                                      "repeat": repeat}, case_timeout)
        if outcome.get("outcome") == "unimportable":
            _fail("MODULE_NOT_IMPORTABLE:" + str(outcome.get("msg")))
        timings = outcome.get("seconds") or []
        if len(timings) != len(sizes) or not any(timings):
            continue
        fit = _fit(sizes, [t or 0.0 for t in timings])
        measured.append({"module": dotted, "qualname": qualname, "sizes": sizes,
                         "seconds": timings,
                         "size_carried_by": "list" if takes_list else "int",
                         "outcomes": outcome.get("outcomes"),
                         "growth": fit})
        if str(args.get("qualname") or "").strip():
            break
    return {"comparisons": measured}


def run(args: dict, root) -> dict:
    root = Path(root)
    args = dict(args or {})
    capability_id = str(args.get("capability_id") or "")
    act = str(args.get("act_verb") or args.get("act") or "").strip()
    if act not in ACTS:
        _fail("ACT_NOT_SUPPORTED:" + (act or "<none>"))
    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        _fail("OUTPUT_PATH_NOT_STATED")
    destination = _destination(root, output_path)
    project, module_file, module = _locate(root, args, allow_directory_scan=True)
    python_exe = str(args.get("python_executable") or sys.executable)

    payload = _base(capability_id or f"python.perf.{act}.v1", act, module_file)
    payload.update({"target": str(module_file), "module": module})
    if act in ("memory_profile", "cpu_profile"):
        measured = _memory_or_cpu(args, act, project, module_file, module, python_exe)
        worst = measured["worst"]
        payload.update({
            "cases_run": measured["cases_run"],
            "ranking": measured["ranking"],
            "qualname": worst["qualname"] if worst else None,
            "worst_case": worst["args"] if worst else None,
            "peak_bytes": worst.get("peak_bytes") if worst else None,
            "top_sites": worst.get("top_sites") if worst else None,
            "hotspots": worst.get("hotspots") if worst else None,
            # THE STABLE FORM OF EACH FINDING.  Microseconds and traced-byte counts are readings of
            # the machine, so two identical runs never agree on them; the RANKING is the finding and
            # it does reproduce.  Both forms are written: the numbers for a human, the order for an
            # equality test.
            "hotspot_ranking": ([h.get("function") for h in (worst.get("hotspots") or [])]
                                if worst else None),
            "allocating_sites": ([s.get("site") for s in (worst.get("top_sites") or [])]
                                 if worst else None),
            "claim": ((f"MEMORY MEASURED: the peak traced allocation over "
                       f"{measured['cases_run']} cases, the call that produced it and the sites "
                       f"that hold it")
                      if act == "memory_profile" else
                      (f"CPU MEASURED: the ranked hotspots of the slowest of "
                       f"{measured['cases_run']} cases, by cumulative time"))
            if worst else "NOTHING MEASURED: no case in scope produced a measurement",
            "law": ("every case runs in its own interpreter with a wall clock, so a crash or a hang "
                    "is an outcome rather than a lost run; the worst case is reported with the "
                    "number, never an average alone"),
        })
    else:
        measured = _benchmark(args, project, module_file, module, python_exe)
        first = measured["comparisons"][0] if measured["comparisons"] else None
        payload.update({
            "qualname": first["qualname"] if first else None,
            "timings": first["seconds"] if first else None,
            "sizes": first["sizes"] if first else None,
            "size_carried_by": first["size_carried_by"] if first else None,
            "growth": first["growth"] if first else None,
            "best_class": (first["growth"]["best_class"] if first else None),
            "growth_unresolved_best": (first["growth"]["unresolved_best"] if first else None),
            "comparisons": measured["comparisons"],
            "claim": ((f"BENCHMARKED: measured times at {first['sizes']} and the shape that "
                       f"explains them best is {first['growth']['best_class']}")
                      if first and first["growth"]["best_class"] else
                      (f"BENCHMARKED, SHAPE UNRESOLVED: measured times at {first['sizes']}; the "
                       f"closest shape is {first['growth']['unresolved_best']} but the log-log line "
                       f"fits with r2={(first['growth']['r2'] or 0.0):.3f} over slope "
                       f"{(first['growth']['slope'] or 0.0):.2f}, so no growth class is claimed"
                       if first else "NOTHING BENCHMARKED: no call in scope produced a timing")),
            "law": ("the whole ladder runs in ONE child after a warm-up, because a fresh interpreter "
                    "per size cost more than the call at small sizes, and the minimum of the "
                    "repetitions is kept so one scheduler hiccup cannot become a curve; the growth "
                    "class is a FIT with `slope` and `r2` reported beside it, so a curve is never "
                    "read as a theorem"),
        })
    payload["complete"] = True
    written = _write(destination, payload)
    return {
        "adapter": "perf_probe_v1",
        "capability_id": payload["capability_id"],
        "act": act,
        "module": payload["module"],
        "qualname": payload.get("qualname"),
        "cases_run": payload.get("cases_run"),
        # THE RANKING IS PART OF THE ANSWER.  A caller that has to open the artifact to learn which
        # function or line was expensive has not been told the finding.  Measured: a summary that
        # carried only a peak byte count made every evidence predicate read an empty list.
        "worst_case": payload.get("worst_case"),
        "peak_bytes": payload.get("peak_bytes"),
        "top_sites": payload.get("top_sites"),
        "hotspots": payload.get("hotspots"),
        "hotspot_ranking": payload.get("hotspot_ranking"),
        "allocating_sites": payload.get("allocating_sites"),
        "sizes": payload.get("sizes"),
        "timings": payload.get("timings"),
        "growth": payload.get("growth"),
        "best_class": payload.get("best_class"),
        "gate": "PASS",
        "complete": True,
        "output_path": str(destination),
        "output_sha256": written.get("artifact_sha256"),
        "output_verified": json.loads(Path(destination).read_text(encoding="utf-8"))["artifact_sha256"]
        == written.get("artifact_sha256"),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--act_verb", required=True)
    parser.add_argument("--source_root", required=True)
    parser.add_argument("--qualname", default=None)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--max_cases", type=int, default=None)
    parser.add_argument("--sizes", nargs="*", type=int, default=None)
    ns = parser.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
