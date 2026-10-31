#!/usr/bin/env python3
"""Three performance acts the machine claimed and could not do: memory, CPU, and growth class.

The domain map read `performance engineering 2 / 6` and the missing-verb probe refused the memory
sentence.  None of the three needed a new engine: `tracemalloc`, `cProfile`/`pstats` and
`time.perf_counter` ship with the interpreter, and `dynamic_probe_v1` already knew how to locate a
package, enumerate its public functions, run each candidate case in its own interpreter and treat a
crash or a hang as an outcome rather than a lost run.  `perf_probe_v1` is that engine pointed at a
different set of observations.

Every number below was measured on this module, and four of the measurements were DEFECTS first.
They are pinned here because each one produced a confident, wrong answer:

  1. `stat.traceback.format()` on a default `tracemalloc.start()` reports ONE frame -- the harness's
     own `fn(*args)` line -- so every allocation in the report was `<string>:30`, 249 bytes.  The
     top site is now the frame in the file under measurement, from an 8-frame traceback.
  2. the snapshot was taken after the measured value had been dropped, so profiling `hog(512)`
     reported 55,670 peak bytes and a top site of 249 bytes: it was measuring the collector.  The
     value is now held across the snapshot.
  3. `cProfile.Profile.getstats()` rows do not unpack as `(key, values)`; the unpack raised and the
     hotspot list came back EMPTY, so all scores were 0 and the least-work case "won".  The rows come
     from `pstats.Stats`, and the harness's own frames are filtered out.
  4. the growth class was the minimum coefficient of variation over six shapes, which ALWAYS returns
     a winner: a noisy linear loop was confidently called `O(log n)`.  It is now a least-squares fit
     of log(time) against log(size), reported with `slope` and `r2`, and a class is claimed only when
     the line is straight and the exponent is within 0.25 of it.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
perf = pytest.importorskip("canonical.runtime.bound_capabilities.perf_probe_v1")

QUADRATIC = "def quadratic(n: int) -> int:\n    return sum(1 for _ in range(n) for _ in range(n))\n"
LINEAR = "def loop(n: int) -> int:\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
ALLOCATING = "def hog(n: int) -> list:\n    return [str(i) * 8 for i in range(n)]\n"


@pytest.fixture()
def project(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return pkg


# ------------------------------------------------------------------------ the growth fit, alone


def test_a_power_law_is_recovered_with_its_exponent_and_its_straightness():
    sizes = [64, 128, 256, 512, 1024, 2048]
    for exponent, expected in ((1, "O(n)"), (2, "O(n^2)"), (3, "O(n^3)")):
        seconds = [(n / 64) ** exponent * 1e-4 for n in sizes]
        fit = perf._fit(sizes, seconds)
        assert fit["best_class"] == expected, (exponent, fit)
        assert fit["slope"] == pytest.approx(exponent, abs=0.05)
        assert fit["r2"] >= 0.99
        assert fit["resolved"] is True


def test_a_logarithmic_curve_is_not_called_linear():
    sizes = [64, 128, 256, 512, 1024, 2048]
    fit = perf._fit(sizes, [1e-4 * math.log2(n) for n in sizes])
    assert fit["best_class"] == "O(log n)", fit


def test_noise_is_refused_rather_than_scored():
    """A noisy ladder can be NEAREST to a class while being no line at all."""
    sizes = [64, 128, 256, 512, 1024, 2048]
    fit = perf._fit(sizes, [1e-4, 9e-4, 2e-4, 7e-4, 3e-4, 8e-4])
    assert fit["best_class"] is None
    assert fit["resolved"] is False
    # the closest shape is still named, so a refusal still says what it saw
    assert fit["unresolved_best"] is not None
    assert fit["r2"] is not None
    assert "why" in fit


def test_too_few_points_is_a_refusal_not_a_guess():
    fit = perf._fit([64, 128], [1e-4, 4e-4])
    assert fit["best_class"] is None and fit["resolved"] is False


# ------------------------------------------------------------------------------- the three acts


def test_the_growth_class_of_a_quadratic_function_is_measured_not_assumed(project, tmp_path):
    (project / "work.py").write_text(QUADRATIC, encoding="utf-8")
    result = perf.run({"act_verb": "benchmark", "capability_id": "test.perf",
                       "source_root": str(project / "work.py"),
                       "output_path": str(tmp_path / "bench.json")}, project)
    assert result["best_class"] == "O(n^2)", result
    assert result["growth"]["r2"] >= 0.95
    assert result["qualname"] == "quadratic"
    assert list(result["sizes"]) == list(perf.DEFAULT_SIZES)
    assert len(result["timings"]) == len(result["sizes"])
    # a benchmark that measured nothing is a refusal, never a class
    assert all(t and t > 0 for t in result["timings"])


def test_the_worst_case_carries_the_allocation_and_the_line_that_holds_it(project, tmp_path):
    (project / "work.py").write_text(ALLOCATING, encoding="utf-8")
    result = perf.run({"act_verb": "memory_profile", "capability_id": "test.perf",
                       "source_root": str(project / "work.py"),
                       "output_path": str(tmp_path / "mem.json")}, project)
    assert result["peak_bytes"] >= 20000, result
    # the fuzzer's boundary draws cannot be profiled (2**63, long strings): the ladder is what
    # makes the measurement possible, and it must be there
    assert result["worst_case"] and result["worst_case"][0] >= 64
    sites = " ".join(result["allocating_sites"])
    assert "work.py" in sites, result["allocating_sites"]
    # the profiler's own frames are never the answer to "where did the bytes go"
    assert "<string>" not in sites, result["allocating_sites"]


def test_the_cpu_ranking_names_the_function_and_never_the_profiler(project, tmp_path):
    (project / "work.py").write_text(LINEAR, encoding="utf-8")
    result = perf.run({"act_verb": "cpu_profile", "capability_id": "test.perf",
                       "source_root": str(project / "work.py"),
                       "output_path": str(tmp_path / "cpu.json")}, project)
    assert result["cases_run"] >= 1
    assert result["hotspot_ranking"], result
    assert result["hotspot_ranking"][0] == "loop", result["hotspot_ranking"]
    assert "<method 'disable' of '_lsprof.Profiler' objects>" not in result["hotspot_ranking"]


def test_a_package_is_scanned_through_its_subdirectories(project, tmp_path):
    """The measured defect: `*.py` at the root found nothing in a normal package layout."""
    nested = project / "inner"
    nested.mkdir()
    (nested / "__init__.py").write_text("", encoding="utf-8")
    (nested / "work.py").write_text(QUADRATIC, encoding="utf-8")
    result = perf.run({"act_verb": "benchmark", "capability_id": "test.perf",
                       "source_root": str(project),
                       "output_path": str(tmp_path / "bench.json")}, project)
    assert result["qualname"] == "quadratic", result


def test_an_unmeasurable_boundary_draw_is_filtered_out():
    assert perf._measurable(2 ** 63) is False
    assert perf._measurable("x" * 10000) is False
    assert perf._measurable(512) is True
    assert perf._measurable("ok") is True


def test_the_returned_answer_carries_the_ranking_not_only_a_number(project, tmp_path):
    """Measured defect: a summary that carried only a peak byte count made every evidence
    predicate read an empty list, and the capability looked like it had found nothing."""
    (project / "work.py").write_text(ALLOCATING, encoding="utf-8")
    result = perf.run({"act_verb": "memory_profile", "capability_id": "test.perf",
                       "source_root": str(project / "work.py"),
                       "output_path": str(tmp_path / "mem.json")}, project)
    for key in ("worst_case", "peak_bytes", "top_sites", "allocating_sites", "hotspot_ranking",
                "growth", "best_class"):
        assert key in result, key
    assert result["output_verified"] is True
    artifact = json.loads(pathlib.Path(result["output_path"]).read_text(encoding="utf-8"))
    assert artifact["complete"] is True and artifact["claim"]


# ----------------------------------------------------------------------------- wired, not judged


@pytest.mark.parametrize("capability_id,provides", [
    ("python.perf.benchmark.v1", "perf.big_o_inference"),
    ("python.perf.cpu_profile.v1", "perf.hotspot_ranking"),
    ("python.perf.memory_profile.v1", "perf.allocation_growth"),
])
def test_the_registry_row_is_bound_to_this_module_as_it_is_on_disk(capability_id, provides):
    registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                          .read_text(encoding="utf-8"))["capabilities"]
    entry = registry[capability_id]
    assert entry["adapter_module"] == "perf_probe_v1"
    assert provides in entry["provides"]
    assert entry["status"] == "VERIFIED_BOUND_CAPABILITY"
    digest = hashlib.sha256((ROOT / "canonical/runtime/bound_capabilities/perf_probe_v1.py")
                            .read_bytes()).hexdigest()
    # a docstring edit is a module edit: the row must not claim a hash the file no longer has
    assert entry["verification"]["module_sha256"] == digest
    # the three acts are pure stdlib, so they declare no external toolchain
    tools = json.loads((ROOT / "canonical/runtime/TOOLCHAIN_DECLARATION_V1.json")
                       .read_text(encoding="utf-8"))["capability_tools"]
    assert tools[capability_id] == []
