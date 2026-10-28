#!/usr/bin/env python3
"""The toolchain a capability calls is part of the capability, so it must be declared.

Measured on a clean checkout of this branch: the same commit, the same code, and the same
22-task hardcore-SE probe read

    bare python3        bind 22/22  select 19/22  pass 14/22
    with the toolchain  bind 22/22  select 22/22  pass 22/22

Eight capabilities appearing and disappearing on the strength of an environment nobody had
declared.  In the live registry the dependency is stored as prose -- `source.module` is
"mypy" for one entry and "python stdlib ast/pytest + git" for another -- and
`declared_dependency_executables` is empty for all 419 verified entries.  Nothing could
install the toolchain and nothing could tell a missing package from a broken adapter: the
adapters exit their process, so an ABSENT capability reports itself as a BROKEN one.

These tests hold the three things that made that possible, and the one thing that keeps the
declaration from drifting away from the code:

  1. the declaration is complete and internally consistent (a blocked task must be a real task);
  2. the check FAILS when a distribution is missing and when a pin has drifted -- a gate that
     can only report PASS is not a gate, so both directions are asserted;
  3. every `blocks` row was produced by measurement, and the measurement is re-runnable
     (`--attribute` blocks each distribution with an import hook and re-runs the probe).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "canonical/runtime/TOOLCHAIN_DECLARATION_V1.json"
PREFLIGHT = ROOT / "execution_guard/toolchain_preflight_v1.py"
PROBE = ROOT / "execution_guard/hardcore_se_reachability_v1.py"


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _declaration() -> dict:
    return json.loads(DECLARATION.read_text(encoding="utf-8"))


def _task_tags() -> set[str]:
    return {tag for tag, _cid, _goal in _load(PROBE, "_se_probe").PROBES}


def test_every_declared_distribution_names_an_import_a_version_and_its_blast_radius():
    for name, entry in _declaration()["distribution"].items():
        assert entry.get("import"), name
        assert entry.get("version"), name
        assert isinstance(entry.get("blocks"), list), name
        assert "absent_effect" in entry, name


def test_every_blocked_task_is_a_task_the_probe_actually_runs():
    tags = _task_tags()
    for name, entry in _declaration()["distribution"].items():
        unknown = [task for task in entry["blocks"] if task not in tags]
        assert not unknown, (name, unknown)


def test_every_attributed_capability_exists_in_the_live_registry():
    from canonical.runtime import live_integrated_brain_v1 as live
    registry = live.load_verified_registry()
    for name, entry in _declaration()["distribution"].items():
        capability = entry.get("declared_by_capability")
        if capability:
            assert capability in registry, (name, capability)


def test_the_check_is_honest_about_an_absent_distribution(tmp_path, monkeypatch):
    """A missing package must FAIL the check, not pass with a note."""
    preflight = _load(PREFLIGHT, "_preflight_absent")
    spec = _declaration()
    spec["distribution"] = {"definitely-not-installed-package": {
        "import": "definitely_not_installed_package", "version": "1.0.0",
        "blocks": ["review_type"], "absent_effect": "nothing runs"}}
    fake = tmp_path / "declaration.json"
    fake.write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.setattr(preflight, "DECLARATION", fake)
    assert preflight.main.__module__  # the module loaded
    assert preflight.report("", "") == 1


def test_the_check_is_honest_about_version_drift(tmp_path, monkeypatch):
    """A drifted pin is the exact state that changed 22/22 into 14/22, so it must fail."""
    preflight = _load(PREFLIGHT, "_preflight_drift")
    spec = _declaration()
    spec["distribution"] = {"json": {"import": "json", "version": "0.0.0-nothing-this-is",
                                     "blocks": [], "absent_effect": "none"}}
    fake = tmp_path / "declaration.json"
    fake.write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.setattr(preflight, "DECLARATION", fake)
    assert preflight.report("", "") == 1


def test_the_check_passes_when_the_declared_import_is_present(tmp_path, monkeypatch):
    """The other direction: a present distribution whose pin matches must PASS."""
    preflight = _load(PREFLIGHT, "_preflight_present")
    spec = {"distribution": {"json": {"import": "json", "version": "",
                                      "blocks": [], "absent_effect": "none"}}}
    fake = tmp_path / "declaration.json"
    fake.write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.setattr(preflight, "DECLARATION", fake)
    assert preflight.report("", "") == 0


def test_a_malformed_declaration_is_a_refusal_not_a_pass(tmp_path, monkeypatch):
    preflight = _load(PREFLIGHT, "_preflight_broken")
    fake = tmp_path / "declaration.json"
    fake.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(preflight, "DECLARATION", fake)
    try:
        preflight.declaration()
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - the refusal is the whole point
        raise AssertionError("an unreadable declaration must not be treated as satisfied")


def test_the_declaration_records_the_measurement_it_was_built_from():
    """The two interpreters' numbers are the evidence; losing them loses the reason."""
    measurements = _declaration().get("measurements") or {}
    assert measurements["clean_image_bare_python3"]["pass"] == "14/22"
    assert measurements["with_this_declaration_installed"]["pass"] == "22/22"
    assert len(measurements["clean_image_bare_python3"]["failing"]) == 8
