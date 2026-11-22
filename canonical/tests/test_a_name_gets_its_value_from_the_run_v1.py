"""Pins the witness instrument, and pins the five ways it silently measured nothing.

Every test here except the last two needs no network and no real repository. The ones that
run a tracer use a toy package built in `tmp_path`, which is enough to prove the plumbing
because the plumbing -- not the corpus -- is what failed five times.
"""
from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import a_name_gets_its_value_from_the_run_v1 as W  # noqa: E402


def build_package(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    """A toy project with src/, tests/, and a suite that passes."""
    package = tmp_path / "demo"
    (package / "src" / "demo").mkdir(parents=True)
    (package / "src" / "demo" / "__init__.py").write_text(body)
    (package / "tests").mkdir()
    return package


def test_the_plugin_is_a_real_pytest_plugin_not_sitecustomize() -> None:
    """sitecustomize is imported before pytest exists, so its trace is replaced.

    The witness must be loadable as `-p brain_witness`, which means it must be a module
    and must install the trace from a pytest hook.
    """
    compile(W.WITNESS_PLUGIN, "<plugin>", "exec")
    assert "pytest_runtest_setup" in W.WITNESS_PLUGIN
    assert "sitecustomize" not in W.PLUGIN_NAME


def test_the_plugin_installs_the_trace_only_while_a_test_runs() -> None:
    """Tracing during collection re-traces pytest and turns 40 s into >900 s."""
    assert "pytest_runtest_teardown" in W.WITNESS_PLUGIN
    assert "sys.settrace(None)" in W.WITNESS_PLUGIN


def test_the_frame_filter_is_cached_per_code_object() -> None:
    """A path resolution per frame is what made the instrument take >900 s."""
    assert "MINE.get(code)" in W.WITNESS_PLUGIN


def test_the_child_interpreter_must_be_able_to_import_pytest() -> None:
    """A bare python3 exits 1, and the instrument then reports OK with import-time pairs."""
    chosen = W._interpreter_with_pytest()
    done = subprocess.run([chosen, "-c", "import pytest"], capture_output=True)
    assert done.returncode == 0, f"{chosen} cannot import pytest"


def test_a_witnessed_value_converts_a_site_and_a_type_only_one_does_not() -> None:
    """The distinction the whole claim rests on.

    A witnessed STRING is a usable prober token. A witnessed object type (`Tokenizer`) is
    not: knowing it is a Tokenizer does not say which one. Only the first is claimed.
    """
    sites = [{"callee": "f", "blocked_names": ["s"], "blocked_positions": [0],
              "file": "m.py", "line": 1},
             {"callee": "g", "blocked_names": ["tok"], "blocked_positions": [0],
              "file": "m.py", "line": 2}]
    seen = {"f|0": {"types": {"str": 3}, "values": {"str": ["abc"]}, "param": "s"},
            "g|0": {"types": {"Tokenizer": 5}, "values": {}, "param": "tok"}}
    converted = W.convert(sites, seen)
    assert [c["callee"] for c in converted] == ["f", "g"]
    real = [c for c in converted if all(w["values"] for w in c["witnessed"])]
    assert [c["callee"] for c in real] == ["f"], "a type-only witness must not be executable"


def test_two_different_types_for_one_name_does_not_convert() -> None:
    """A name seen as both str and int is not settled; refuse rather than pick."""
    sites = [{"callee": "f", "blocked_names": ["x"], "blocked_positions": [0],
              "file": "m.py", "line": 1}]
    seen = {"f|0": {"types": {"str": 2, "int": 1}, "values": {"str": ["a"]}, "param": "x"}}
    assert W.convert(sites, seen) == []


def test_the_witness_matches_by_argument_position_not_by_name() -> None:
    """The caller says `raw`, the callee calls it `value`. Matching by name finds nothing.

    This is the bug that made a first run report 23 conversions that were really 7: the
    only sites that "converted" were the ones where caller and callee happened to pick the
    same identifier. Position 0 is the binding, whatever either side calls it.
    """
    sites = [{"callee": "inner", "blocked_names": ["raw"], "blocked_positions": [0],
              "file": "m.py", "line": 5}]
    seen = {"inner|0": {"types": {"str": 2}, "values": {"str": ["WITNESSED"]},
                        "param": "value"}}
    converted = W.convert(sites, seen)
    assert len(converted) == 1, "a positional witness must convert despite differing names"
    assert converted[0]["witnessed"][0]["param"] == "value"


def test_an_unwitnessed_name_does_not_convert() -> None:
    sites = [{"callee": "f", "blocked_names": ["x"], "blocked_positions": [0],
              "file": "m.py", "line": 1}]
    assert W.convert(sites, {}) == []


def test_the_whole_loop_on_a_toy_package(tmp_path: pathlib.Path) -> None:
    """End to end: mine a blocked site, witness it from the suite, convert it."""
    package = build_package(tmp_path, (
        "def inner(value):\n"
        "    return value\n\n"
        "def outer(raw):\n"
        "    return inner(raw)\n"
    ))
    (package / "tests" / "test_demo.py").write_text(
        "import demo\n\n"
        "def test_outer():\n"
        "    assert demo.outer('WITNESSED') == 'WITNESSED'\n"
    )
    report = W.run(package)
    assert "passed" in (report["pytest"] or ""), report
    assert report["blocked_sites"] >= 1, report
    assert report["target_pairs_witnessed"] >= 1, report
    real = [c for c in report["converted"] if all(w["values"] for w in c["witnessed"])]
    assert real, report
    assert any(w["values"][0] == "WITNESSED" for c in real for w in c["witnessed"])


def test_a_failing_suite_is_not_reported_as_a_witness(tmp_path: pathlib.Path) -> None:
    """If the suite does not run, nothing may be claimed."""
    package = build_package(tmp_path, "def inner(value):\n    return value\n")
    (package / "tests" / "test_demo.py").write_text(
        "def test_broken(:\n    pass\n"
    )
    report = W.run(package)
    assert "passed" not in (report["pytest"] or ""), report
    assert report["converted_sites"] == 0, report


def test_no_model_and_no_network_in_the_instrument() -> None:
    source = (ROOT / "canonical/swe_kernel/a_name_gets_its_value_from_the_run_v1.py").read_text()
    for forbidden in ("openai", "anthropic", "requests.", "urllib.request"):
        assert forbidden not in source, f"runtime dependency found: {forbidden}"
