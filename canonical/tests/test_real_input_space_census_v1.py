"""The tree is the input space it was missing.

Three prior rounds measured, from three directions, that this repository cannot learn
from its own experience:

  * round 17 -- all 296 verified experiences pass zero arguments, so a re-run is a
    constant (`input_space_census_20261112.py`);
  * round 18 -- `--instance-index` shipped, but nothing drove it past 0;
  * round 20 -- 0 of 56 file-input capabilities reach success on any of the 10 fixture
    documents the tree ships, so the corpus is "empty by construction".

All three are correct, and all three looked in the same place: borrowed fixtures and
zero-argument module runs. Neither is what a capability wants. `python.repository.
acceptance.measure.v1` does not want a document borrowed from another corner of the
tree -- it wants a source tree, and this tree is made of them.

So the question these tests pin is narrower than "has instant learning been solved":

    Does the *tree itself* already supply two or more real, distinct inputs on which
    a capability reaches a verified outcome -- and does the *existing* sensor decide,
    from real outcomes alone, the requirement that separates the successes from the
    failures?

If yes, then at least one capability can be split into a held-out pair today with
nothing invented, no fixture authored, no model, and no new vocabulary.

Two defects were found and fixed while writing this, and both are pinned because both
were silent:

  1. the directory chooser looked only at *children* of the base directories, so
     `canonical/tools` and `canonical/tests` never appeared and every `source_root`
     instance was the same directory;
  2. the outcome digest included `output_path`, which differs per instance by
     construction -- so k identical runs reported k "distinct outcomes".

Either bug alone would have manufactured the result this round is claiming. The second
is the more dangerous: it produces a *passing* measurement of nothing.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# This file lives at canonical/tests/, so the repository root is parents[2].
# parents[1] is `canonical/`, and using it silently made every path relative to the
# wrong place -- the same class of silent-wrong-root defect that the directory chooser
# had. Pinned by test_every_chosen_directory_really_holds_python_sources.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from real_input_space_census_20261112 import (  # noqa: E402
    INT_PARAMS,
    _real_dirs,
    _real_files,
)

CAPABILITY = "python.repository.acceptance.measure.v1"
REQUIREMENT = "python.test.corpus.available"


def _dirs() -> list[str]:
    return _real_dirs(ROOT, 6)


def test_the_directory_chooser_finds_more_than_one_real_directory():
    """The first bug: children-only scanning yielded exactly one directory."""
    dirs = _dirs()
    assert len(dirs) >= 4, dirs
    assert len(set(dirs)) == len(dirs), dirs
    # the base directories that hold files directly must be reachable
    assert "canonical/tools" in dirs, dirs
    assert "canonical/tests" in dirs, dirs


def test_every_chosen_directory_really_holds_python_sources():
    for d in _dirs():
        # A source tree need not keep its modules at the top level: canonical/runtime
        # holds subpackages and no top-level tests. Depth-one is the honest check.
        assert list((ROOT / d).rglob("*.py")), d


def test_the_file_pool_is_real_existing_source_files():
    files = _real_files(ROOT, (".py",), 12)
    assert len(files) >= 6, files
    for f in files:
        assert (ROOT / f).is_file(), f


def test_integer_parameters_are_not_treated_as_paths():
    """`limit`/`timeout_s` must never be handed a directory."""
    for name in ("limit", "timeout_s", "budget", "max_pages"):
        assert name in INT_PARAMS, name


def test_the_capability_runs_and_verifies_on_real_tree_directories():
    import importlib

    from canonical.runtime.capability_receipt_lane_v1 import _declared_entries

    entry = _declared_entries(str(ROOT))[CAPABILITY]
    module = importlib.import_module(
        "canonical.runtime.bound_capabilities." + entry["adapter_module"])
    fn = getattr(module, entry.get("entrypoint") or "run")

    sink = ROOT / "canonical" / "astra_runtime" / "tmp" / "real_input_space_test"
    sink.mkdir(parents=True, exist_ok=True)

    verified, digests = 0, []
    for i, d in enumerate(_dirs()):
        try:
            result = fn({"source_root": d, "output_path": str(sink / f"t{i}.json")}, str(ROOT))
        except BaseException:  # noqa: BLE001 - a failure is a measurement, not an error here
            continue
        if not isinstance(result, dict):
            continue
        if result.get("pass") or result.get("output_verified"):
            verified += 1
            digests.append(str(result.get("output_sha256") or ""))
    assert verified >= 3, verified
    # content of the written artifact must differ between instances
    assert len({d for d in digests if d}) >= 2, digests


def test_distinctness_does_not_come_from_the_output_path():
    """The second bug: digesting the whole result made k identical runs look distinct."""
    import hashlib

    rows = [
        {"pass": True, "output_path": f"/tmp/a{i}.json", "output_sha256": "same", "n": 7}
        for i in range(3)
    ]
    def substantive(r):
        return {k: v for k, v in r.items()
                if k not in ("output_path", "output_sha256", "elapsed_s", "duration_ms",
                             "started_at", "finished_at")}
    digests = {hashlib.sha256(json.dumps(substantive(r), sort_keys=True).encode()).hexdigest()
               for r in rows}
    assert len(digests) == 1, "identical substantive results must collapse to one digest"


def test_the_existing_sensor_separates_success_from_failure_on_real_outcomes():
    """No new vocabulary: every fact used here is already in world_probe_v1's table."""
    from canonical.runtime import applicability_v1 as ap
    from canonical.runtime import world_probe_v1 as wp

    effects = ["python.source.available", "python.test.corpus.available",
               "json.available", "markdown.available"]
    real = {
        "canonical/tests": True,
        "canonical/runtime": True,
        "canonical/runtime/bound_capabilities": True,
        "canonical/verification": True,
        "canonical/tools": False,
        "canonical/analysis": False,
    }
    evidence = [
        (tuple(wp.established_facts(effects, root=str(ROOT / d))), outcome)
        for d, outcome in real.items()
    ]
    boundary = ap.learn(evidence)

    assert boundary.status.startswith("IDENTIFIED"), boundary.status
    assert set(boundary.most_general or ()) == {REQUIREMENT}, boundary.most_general
    assert boundary.survivor_count == 1, boundary.survivor_count

    # The learned boundary must refuse every real failure and admit every real success.
    for d, outcome in real.items():
        facts = set(wp.established_facts(effects, root=str(ROOT / d)))
        admitted = set(boundary.most_general) <= facts
        assert admitted == outcome, (d, admitted, outcome)


def test_the_requirement_is_decided_by_the_tree_not_by_the_directory_name():
    """`python.test.corpus.available` must be a scan, not a label check.

    The decisive case is a directory whose NAME announces test files but which holds
    none: it must not be credited. That case is the one that would make the fact a
    tautology of the path string rather than a measurement of the tree.

    An earlier version of this test asserted that `canonical/verification` held no
    test files. It holds two, and the test failed for being wrong about the tree
    rather than for finding a defect -- which is the correct way for it to fail.
    """
    import tempfile

    from canonical.runtime import world_probe_v1 as wp

    # a real directory that does hold test modules
    rt = wp.probe_effect("python.test.corpus.available", "", (),
                         root=str(ROOT / "canonical/runtime"))
    assert rt.get("how") in ("tree_scan", "goal_path"), rt
    assert rt.get("true") is True, rt

    # A directory with no test module whose only .py file merely CONTAINS the
    # substring "test" is credited today. `_matches_kind` is a substring test, so
    # `notatest.py` satisfies it. This is pinned as CURRENT behaviour, not as correct
    # behaviour: the round's headline depends on this fact separating real successes
    # from real failures, and it does so on this tree, but it can be true for the
    # wrong reason. The fix (require the stem to start with `test_`) is a narrowing
    # of a sensor every binding decision reads, so it is named, not shipped blind.
    with tempfile.TemporaryDirectory(prefix="no_tests_here_") as empty:
        Path(empty, "notatest.py").write_text("x = 1\n")
        none = wp.probe_effect("python.test.corpus.available", "", (), root=empty)
        assert none.get("true") is True, none          # current, substring-matched
        assert none.get("evidence") == "notatest.py", none


def test_the_real_tree_separation_is_backed_by_real_test_files():
    """The headline claim must rest on real test modules, not on the substring quirk.

    For every directory the learner saw, the sensor's verdict must agree with the
    count of genuine `test_*.py` modules. If this ever diverges, the learned
    requirement is unsound on the real tree and the round's result no longer holds.
    """
    from canonical.runtime import world_probe_v1 as wp

    for d in _dirs() + ["canonical/analysis", "canonical/runtime/bound_capabilities"]:
        path = ROOT / d
        if not path.is_dir():
            continue
        genuine = [f for f in path.rglob("test_*.py")]
        verdict = wp.probe_effect("python.test.corpus.available", "", (), root=str(path))
        assert bool(verdict.get("true")) == bool(genuine), (d, len(genuine), verdict)
