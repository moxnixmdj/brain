#!/usr/bin/env python3
"""A capability is the adapter PLUS the software it calls, and the door must check both.

Measured on this commit, with `execution_guard/hardcore_se_missing_verb_probe_v1.py` over the same
43 hardcore-SE acts:

    .venv, before the gate      32 answered / 11 honest refusal /  0 owned-but-failed / 0 silent
    bare, before the gate       16 answered / 11 honest refusal / 13 owned-but-failed / 3 silent
    bare, after  the gate       18 answered / 25 honest refusal /  0 owned-but-failed / 0 silent

Thirteen acts -- lint, format, type_check, coverage, dead_code, complexity, async_audit,
exception_audit, secret_scan, vulnerability_audit and the three refactors that prove their edit by
running the suite -- were reported as BROKEN CAPABILITIES on a box where ruff, mypy, coverage,
pytest, bandit, detect-secrets and pip-audit had never been installed.  The capability was fine;
the shell was empty.  A model told "this capability is broken" learns the wrong lesson, and the
brain has now fixed this same misreporting at three layers (Class B, P1, here).

The gate turns each of those into one of two honest outcomes -- install the pinned tool, or refuse
by name with the command that installs it -- and it must not do the *opposite* error either:
refusing a working capability because a quoted word in its adapter looked like a program.  These
tests hold both directions:

  1. tool detection reads only forms that provably invoke something (`["-m", X]`,
     `_resolve_tool("X")`, `shutil.which("X")`), never a bare quoted string;
  2. the per-capability declaration wins over the shared adapter's union, and an EMPTY row is a
     claim ("calls no external tool") rather than an absence of one;
  3. a missing tool FAILS with its name, a managed interpreter installs first, and the refusal
     sentence carries both the pin and the command;
  4. the door itself refuses before it promises, and the plan's capability list is complete.
"""
from __future__ import annotations

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "canonical/runtime/TOOLCHAIN_DECLARATION_V1.json"
ADAPTERS = ROOT / "canonical/runtime/bound_capabilities"

ruff_lint = pytest.importorskip("canonical.runtime.toolchain_gate_v1")
admission = pytest.importorskip("canonical.runtime.live_brain_route_admission_v1")


def _declaration() -> dict:
    return json.loads(DECLARATION.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _cold_caches():
    """Every test starts with an empty memo, or an earlier answer leaks into the next."""
    ruff_lint._CACHE.clear()
    ruff_lint._TOOLS_CACHE.clear()
    yield
    ruff_lint._CACHE.clear()
    ruff_lint._TOOLS_CACHE.clear()


# ---------------------------------------------------------------- what counts as a dependency


def test_only_an_invocation_is_a_dependency_not_a_quoted_word(tmp_path):
    """`"perf"` as a display label and `"sqlite3"` as a connection key are not programs.

    This is a real regression, caught by measuring: the first version of the scan read both out
    of `quality_v1.py` and would have refused `python.quality.resource_leak.v1` -- which runs
    neither -- for two binaries it never touches.
    """
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        'KINDS = {"perf": "performance", "sqlite3": "sqlite connection"}\n'
        'def go():\n'
        '    subprocess.run([sys.executable, "-m", "ruff", "check", "."])\n'
        '    bandit = _resolve_tool("bandit")\n'
        '    git = shutil.which("git")\n'
        '    note = "coverage is not invoked here"\n',
        encoding="utf-8",
    )
    modules, binaries = ruff_lint.required_tools(adapter)
    assert modules == ["ruff", "bandit"]
    assert binaries == ["git"]
    assert "perf" not in modules + binaries
    assert "sqlite3" not in modules + binaries
    assert "coverage" not in modules


def test_an_adapter_that_names_nothing_needs_nothing(tmp_path):
    adapter = tmp_path / "quiet.py"
    adapter.write_text('"""Uses the stdlib only."""\nimport json\n', encoding="utf-8")
    assert ruff_lint.required_tools(adapter) == ([], [])


def test_a_missing_adapter_is_not_a_dependency_claim(tmp_path):
    """An unreadable source claims nothing; the gate must not invent a requirement."""
    assert ruff_lint.required_tools(tmp_path / "gone.py") == ([], [])


# ---------------------------------------------------------------- the declaration wins, including its empty rows


def test_the_declaration_states_tools_per_capability_not_per_adapter():
    """One adapter serves five verbs; the union would make `ruff_format` demand mypy."""
    assert ruff_lint.declared_tools("python.toolchain.ruff_format.v1") == ["ruff"]
    assert ruff_lint.declared_tools("python.toolchain.mypy_typecheck.v1") == ["mypy"]
    assert ruff_lint.declared_tools("python.toolchain.bandit_security.v1") == ["bandit"]


def test_an_empty_row_is_a_claim_that_nothing_is_called():
    """Measured: without the empty rows the gate refused five working capabilities and the bare
    box fell from 18 answered acts back to 13."""
    for capability_id in ("python.quality.duplication.v1", "python.quality.license_scan.v1",
                          "python.quality.changelog.v1", "python.quality.api_compatibility.v1",
                          "python.quality.resource_leak.v1"):
        assert ruff_lint.declared_tools(capability_id) == [], capability_id
        assert ruff_lint.check(capability_id, ADAPTERS / "quality_v1.py")[:2] == (True, [])


def test_an_unstated_capability_falls_back_to_reading_its_adapter(monkeypatch):
    """`None` means "not stated", and that is different from "stated as nothing"."""
    assert ruff_lint.declared_tools("python.something.never.declared.v1") is None
    monkeypatch.setattr(ruff_lint, "_managed_interpreter", lambda: False)
    monkeypatch.setattr(ruff_lint, "_importable", lambda name: False)
    ok, missing, _installed, _detail = ruff_lint.check("python.something.never.declared.v1",
                                                       ADAPTERS / "toolchain_v1.py")
    assert ok is False
    # the adapter's UNION, which is exactly why a per-capability row exists for the verbs it feeds
    assert missing == ["bandit", "ruff", "mypy"]


def test_every_declared_row_names_a_real_capability_and_a_real_tool():
    """Drift guard: a typo in either column would silently disable the check."""
    from canonical.runtime import live_integrated_brain_v1 as live
    registry = live.load_verified_registry()
    distribution = _declaration()["distribution"]
    imports = {str(entry.get("import")) for entry in distribution.values()}
    # `pip` is invoked as a module and ships with the interpreter rather than with a declared pin
    known = imports | ruff_lint._BINARIES | {"pip"}
    rows = _declaration()["capability_tools"]
    assert len(rows) >= 29
    for capability_id, tools in rows.items():
        assert capability_id in registry, capability_id
        for tool in tools:
            assert tool in known, (capability_id, tool)


# ---------------------------------------------------------------- fail, install, or say why


def test_a_missing_tool_fails_and_names_itself(monkeypatch):
    """Nothing installed, nothing installable: the refusal names the one tool, not the union."""
    monkeypatch.setattr(ruff_lint, "_managed_interpreter", lambda: False)
    monkeypatch.setattr(ruff_lint, "_importable", lambda name: name != "ruff")
    ok, missing, installed, _detail = ruff_lint.check("python.toolchain.ruff_format.v1",
                                                      ADAPTERS / "toolchain_v1.py")
    assert (ok, missing, installed) == (False, ["ruff"], [])


def test_a_managed_interpreter_installs_the_pin_then_runs(monkeypatch):
    """Autonomy where it is safe: a venv we own does not need a human to pip install."""
    attempts: list[list[str]] = []

    def fake_install(modules, timeout_s=180):
        attempts.append(list(modules))
        return True, "installed"

    monkeypatch.setattr(ruff_lint, "_managed_interpreter", lambda: True)
    monkeypatch.setattr(ruff_lint, "_importable", lambda name: name != "ruff")
    monkeypatch.setattr(ruff_lint, "install", fake_install)
    ok, missing, installed, _detail = ruff_lint.check("python.toolchain.ruff_format.v1",
                                                      ADAPTERS / "toolchain_v1.py")
    assert ok is True and missing == [] and installed == ["ruff"]
    assert attempts == [["ruff"]]


def test_a_failed_install_is_a_refusal_not_a_pass(monkeypatch):
    monkeypatch.setattr(ruff_lint, "_managed_interpreter", lambda: True)
    monkeypatch.setattr(ruff_lint, "_importable", lambda name: name != "mypy")
    monkeypatch.setattr(ruff_lint, "install", lambda modules, timeout_s=180: (False, "boom"))
    ok, missing, _installed, detail = ruff_lint.check("python.toolchain.mypy_typecheck.v1",
                                                      ADAPTERS / "toolchain_v1.py")
    assert ok is False and missing == ["mypy"] and detail == "boom"


def test_the_refusal_sentence_carries_the_pin_and_the_command():
    reason = ruff_lint.refuse_reason(["ruff"])
    assert reason.startswith("TOOLCHAIN_MISSING:ruff")
    assert "ruff==" in reason, "a reader must know which version the machine declares"
    assert "toolchain_preflight_v1.py --bootstrap" in reason
    assert "CapabilityError" not in reason and "FAILED" not in reason


def test_a_binary_that_is_absent_is_reported_like_a_module(monkeypatch):
    monkeypatch.setattr(ruff_lint, "_managed_interpreter", lambda: False)
    monkeypatch.setattr(ruff_lint, "shutil", type("_S", (), {"which": staticmethod(lambda n: None)}))
    monkeypatch.setattr(ruff_lint, "declared_tools", lambda cid: ["git"])
    ok, missing, _installed, _detail = ruff_lint.check("anything.v1", None)
    assert (ok, missing) == (False, ["git"])


def test_the_status_note_names_the_interpreter_that_was_checked():
    status = ruff_lint.status()
    assert status["interpreter"]
    assert isinstance(status["managed"], bool)
    assert status["declared_distributions"] == len(_declaration()["distribution"])


# ---------------------------------------------------------------- the door refuses before it promises


def test_the_plan_lists_every_capability_it_will_call():
    compiled = {
        "selected_capability": "python.toolchain.ruff_lint.v1",
        "capability_dag": {"steps": [{"capability_id": "python.toolchain.ruff_lint.v1"},
                                     {"capability_id": "python.review.diff_static_triage.v1"}]},
        "compiled_parts": [{"capability_id": "python.review.diff_type_gate.v1"}],
    }
    assert admission._capability_ids_in(compiled) == [
        "python.toolchain.ruff_lint.v1",
        "python.review.diff_static_triage.v1",
        "python.review.diff_type_gate.v1",
    ]
    assert admission._capability_ids_in({}) == []


def test_the_door_refuses_a_plan_whose_engine_is_absent(monkeypatch):
    """The measured 13: this is the branch that turns `OWNED_BUT_FAILED` into a named refusal."""
    monkeypatch.setattr(ruff_lint, "_managed_interpreter", lambda: False)
    monkeypatch.setattr(ruff_lint, "_importable", lambda name: name != "ruff")
    compiled = {"selected_capability": "python.toolchain.ruff_lint.v1"}
    refusal = admission._toolchain_refusal(compiled)
    assert refusal is not None
    capability_id, reason = refusal
    assert capability_id == "python.toolchain.ruff_lint.v1"
    assert reason.startswith("TOOLCHAIN_MISSING:ruff")


def test_the_door_says_nothing_when_the_engine_is_present(monkeypatch):
    monkeypatch.setattr(ruff_lint, "check", lambda *a, **k: (True, [], [], ""))
    assert admission._toolchain_refusal({"selected_capability": "python.toolchain.ruff_lint.v1"}) is None


def test_the_door_says_nothing_about_a_capability_it_cannot_look_up(monkeypatch):
    """An unreadable registry claims nothing -- refusing on ignorance would block real work."""
    monkeypatch.setattr(admission, "load_verified_registry",
                        lambda: (_ for _ in ()).throw(RuntimeError("unreadable")))
    assert admission._toolchain_refusal({"selected_capability": "python.unknown.v1"}) is None


def test_the_refusal_status_is_its_own_failure_class():
    """`FAIL_CLOSED__LIVE_CONTROLLER_EXECUTION` blamed the controller for an empty shell."""
    source = (ROOT / "canonical/runtime/live_brain_route_admission_v1.py").read_text(encoding="utf-8")
    assert '"FAIL_CLOSED__TOOLCHAIN_MISSING"' in source
    assert "_missing_engine" in source
