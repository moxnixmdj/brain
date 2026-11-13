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


def _real_source_directories(root: Path) -> list[Path]:
    """Every directory under `canonical/` at depth <= 2 that holds Python source directly.

    The rule never mentions tests, so it cannot be tuned to manufacture the failure the
    census needs: the tree decides which directories are successes and which are failures.
    """
    out: list[Path] = []
    for base in sorted(root.glob("canonical/*")):
        if not base.is_dir():
            continue
        for cand in [base] + [c for c in sorted(base.glob("*"))
                              if c.is_dir() and not c.name.startswith(("_", "."))]:
            if list(cand.glob("*.py")):
                out.append(cand)
    return out


def _guard_both_classes_present(real: dict) -> bool:
    """Guard 1: a census whose directories all agree proves nothing, in either direction."""
    return any(real.values()) and any(not v for v in real.values())


def _guard_a_failure_holds_source(real: dict, states: dict, source: str) -> bool:
    """Guard 2: some failure must hold Python source, or the weaker source fact wins.

    `python.source.available` excludes a failure only if that failure lacks source, so
    with at least one failure that HOLDS source the source fact is inconsistent and cannot
    become `most_general`. This is not the same as requiring every sampled directory to
    hold source: a Python-free failure is harmless alongside one that is not, and the
    stricter version of this guard was written first and rejected a sample that still
    identifies. `test_the_two_guards_are_exactly_the_condition_for_identification` pins
    the difference by calling this function on all four shapes.
    """
    return any(not real[d] and source in states[d] for d in real)


def test_the_existing_sensor_separates_success_from_failure_on_real_outcomes():
    """No new vocabulary: every fact used here is already in world_probe_v1's table.

    Until 2026-11-13 this test hard-coded six directories and their outcomes. Two
    concurrent rounds then added genuine `test_*.py` modules to `canonical/tools`
    (`ee9685dd`, `97684727`), so the pinned `canonical/tools: False` became a stale fact
    about the tree rather than a finding about the sensor. The failure was silent and
    worse than a red assertion: with no directory left holding source and no tests, the
    only remaining failure was `canonical/analysis`, which holds no Python at all, so
    `python.source.available` separated the evidence too -- and being weaker than the
    corpus fact it became `most_general`. The census still "passed" its admits check
    while identifying the wrong requirement (AMBIGUOUS, 2 survivors).

    So the sample is now derived from a rule that never mentions tests, and the outcomes
    from an independent `rglob("test_*.py")` count. Two guards pin *why* identification
    holds instead of assuming it: both outcome classes must be non-empty, or the census is
    vacuous; and at least one failure directory must hold Python source, or the weaker
    source fact separates the evidence too and becomes `most_general` exactly as it just
    did. Neither guard is the only thing that would fail -- each names the cause before a
    downstream assertion reports the symptom, which is the difference between a census
    that explains its own degradation and one that merely goes red.

    One mutation survives and cannot be killed from inside this file: replacing the
    independent `rglob("test_*.py")` oracle with the sensor's own verdict makes the
    comparison tautological and the test still passes, because on this tree the two agree
    everywhere. Oracle independence is a property of the code path, not something an
    assertion can enforce. What catches a sensor defect is the other suite,
    `test_a_test_corpus_is_a_naming_convention_not_a_substring_v1`, which builds
    directories whose names and contents disagree and pins both directions; this test's
    job is the real-tree comparison and the two guards above.
    """
    from canonical.runtime import applicability_v1 as ap
    from canonical.runtime import world_probe_v1 as wp

    effects = ["python.source.available", "python.test.corpus.available",
               "json.available", "markdown.available"]
    dirs = _real_source_directories(ROOT)
    real = {d: bool(list(d.rglob("test_*.py"))) for d in dirs}
    states = {d: set(wp.established_facts(effects, root=str(d))) for d in dirs}

    # Guard 1 -- a census whose directories all agree proves nothing, in either direction.
    assert _guard_both_classes_present(real), (
        "the census is vacuous: no real directory holds Python source without a test "
        "corpus, so nothing separates the corpus fact from the source fact")

    # Guard 2 -- this, not the absence of Python-free directories, is what makes the
    # corpus fact the MOST GENERAL separator. Measured: injecting a Python-free directory
    # into this sample changes nothing (still IDENTIFIED, still the corpus fact) precisely
    # because the other failures hold source. The census degraded on 2026-11-13 only
    # because its single remaining failure was Python-free.
    assert _guard_a_failure_holds_source(real, states, "python.source.available"), (
        "every failure directory lacks Python source, so `python.source.available` also "
        "separates the evidence and, being weaker than the corpus fact, becomes most_general")

    evidence = [(tuple(states[d]), real[d]) for d in dirs]
    boundary = ap.learn(evidence)

    assert boundary.status.startswith("IDENTIFIED"), boundary.status
    assert set(boundary.most_general or ()) == {REQUIREMENT}, boundary.most_general
    assert boundary.survivor_count == 1, boundary.survivor_count

    # The learned boundary must refuse every real failure and admit every real success,
    # and the sensor must agree with the independent count on every directory.
    for d in dirs:
        admitted = set(boundary.most_general) <= states[d]
        assert admitted == real[d], (d, admitted, real[d])
        assert (REQUIREMENT in states[d]) == real[d], (d, sorted(states[d]), real[d])


def test_the_two_guards_are_exactly_the_condition_for_identification():
    """The guards are not decoration: they fire exactly when the census cannot identify.

    Measured on the real tree on 2026-11-13, four sample shapes:

      every directory holds tests      no failure to separate       UNDETERMINED
      a failure that holds source      the corpus fact separates    IDENTIFIED
      that plus a Python-free failure  unchanged                    IDENTIFIED
      only a Python-free failure       the weaker source fact wins  most_general = source

    The last row is the degradation that actually happened, and it is the only row where
    guard 2 fires while guard 1 does not -- so guard 2 is load-bearing for precisely the
    failure mode the census survived. It does not reject the third row, which a stricter
    "no sampled directory may lack Python source" guard wrongly did: that version was
    written first, a scenario check showed it firing on a sample that still identifies,
    and it was replaced by the condition that actually decides identification.
    """
    from canonical.runtime import applicability_v1 as ap

    SRC, CORPUS = "python.source.available", REQUIREMENT
    JSON, MD = "json.available", "markdown.available"
    # The two successes must share no fact beyond source and corpus. A fact every row
    # holds is a constant, and `learn` keeps conjunctions that add a constant to the
    # requirement -- so a constant fact spawns extra survivors and the shape stops
    # matching the real census, whose directories differ on json and markdown. Redundant
    # literals are not ambiguity: {source, corpus} collapses to {corpus} because the
    # entailment relation knows corpus implies source.
    success_a = (SRC, CORPUS, JSON)
    success_b = (SRC, CORPUS, MD)
    failure_with_source = (SRC, JSON, MD)   # holds source, no test corpus
    failure_python_free = (JSON, MD)        # holds neither

    def shape(failures):
        rows = [(set(success_a), True), (set(success_b), True)]
        rows += [(set(f), False) for f in failures]
        states = {i: facts for i, (facts, _) in enumerate(rows)}
        real = {i: outcome for i, (_, outcome) in enumerate(rows)}
        boundary = ap.learn([(tuple(f), o) for f, o in rows])
        identifiable = (boundary.status.startswith("IDENTIFIED")
                        and set(boundary.most_general or ()) == {REQUIREMENT}
                        and boundary.survivor_count == 1)
        # the SAME two functions the census calls, not a restatement of them: a mutant
        # that makes either guard stricter or weaker is killed by the rows below.
        return (_guard_both_classes_present(real),
                _guard_a_failure_holds_source(real, states, SRC),
                identifiable, sorted(set(boundary.most_general or ())))

    assert shape([]) == (False, False, False, []), shape([])
    assert shape([failure_with_source]) == (True, True, True, [REQUIREMENT])
    assert shape([failure_with_source, failure_python_free]) == (True, True, True, [REQUIREMENT])

    guard1, guard2, identifiable, most_general = shape([failure_python_free])
    assert (guard1, guard2, identifiable) == (True, False, False), (guard1, guard2, identifiable)
    assert most_general == [SRC], most_general


def test_the_requirement_is_decided_by_the_tree_not_by_the_directory_name():
    """`python.test.corpus.available` must be a scan, not a label check.

    The decisive case is a directory whose NAME announces test files but which holds
    none: it must not be credited. That case is the one that would make the fact a
    tautology of the path string rather than a measurement of the tree.

    An earlier version of this test asserted that `canonical/verification` held no
    test files. It holds two, and the test failed for being wrong about the tree
    rather than for finding a defect -- which is the correct way for it to fail.

    Until 2026-11-13 this test's own assertion contradicted the paragraph above: it
    pinned `notatest.py` as CREDITED, with a comment naming the fix and declining to
    ship it. The sensor now decides the corpus by the `test_` filename prefix, so the
    assertion and the docstring agree, and the sibling check that compares the sensor
    to genuine `test_*.py` counts passes on the real tree for the first time since two
    `*tests*`-named tools landed in `canonical/tools`.
    """
    import tempfile

    from canonical.runtime import world_probe_v1 as wp

    # a real directory that does hold test modules
    rt = wp.probe_effect("python.test.corpus.available", "", (),
                         root=str(ROOT / "canonical/runtime"))
    assert rt.get("how") in ("tree_scan", "goal_path"), rt
    assert rt.get("true") is True, rt

    # A directory whose only .py file merely CONTAINS the substring "test" was credited until
    # 2026-11-13, because `_matches_kind` tested the substring against the whole relative path. The
    # comment that used to be here pinned that as CURRENT behaviour, not as correct behaviour, and
    # named the fix -- "require the stem to start with `test_`" -- without shipping it, because it
    # narrows a sensor every binding decision reads. It is shipped now, and the reason is measured
    # rather than aesthetic: 2662 files on this tree matched the substring and 2608 are genuine
    # `test_*.py` modules, so 54 announced a test corpus that is not one -- among them
    # `canonical/runtime/attested_state_v1.py` ("at-TEST-ed"), `python_test_audit.py` (a capability
    # ABOUT tests), and every `.py` under `canonical/tests/fixtures/`, whose PATH contains "tests"
    # and whose contents are defective fixtures, not tests. The consequence was not cosmetic:
    # `canonical/tools`, holding zero genuine test modules, sensed as IDENTICAL to
    # `canonical/tests`, which is the equal-facts wall `applicability_v1.vocabulary_gap` exists to
    # witness, and it left `test_the_real_tree_separation_is_backed_by_real_test_files` red.
    # Both directions are pinned, because a narrowing that credited nothing would pass the first.
    with tempfile.TemporaryDirectory(prefix="no_tests_here_") as empty:
        Path(empty, "notatest.py").write_text("x = 1\n")
        none = wp.probe_effect("python.test.corpus.available", "", (), root=empty)
        assert none.get("true") is False, none         # "test" inside a name is not a test
        Path(empty, "test_genuine.py").write_text("x = 1\n")
        some = wp.probe_effect("python.test.corpus.available", "", (), root=empty)
        assert some.get("true") is True, some          # and a genuine module is still credited
        assert some.get("evidence") == "test_genuine.py", some


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
