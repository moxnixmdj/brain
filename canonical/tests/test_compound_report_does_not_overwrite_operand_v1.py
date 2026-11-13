"""Preflight a rendered compound plan before any step can overwrite an operand."""
from __future__ import annotations

from time import perf_counter_ns

import pytest

from canonical.runtime import live_brain_route_admission_v1 as door


REPORTER = "python.software.request.semantic_behavior.compile.v1"
EDITOR = "python.source.edit.v1"
REGISTRY = {
    REPORTER: {"capability_id": REPORTER, "provides": ["acceptance_program_compiled"]},
    EDITOR: {"capability_id": EDITOR, "provides": ["python.source.edit.applied"]},
}


def _plan(path, *, cid=REPORTER, subgoal="", earlier=False):
    actions = []
    if earlier:
        actions.append({"type": "invoke_capability", "args": {
            "capability_id": "not.registered", "output_path": path}})
    actions.append({"type": "invoke_capability", "args": {"capability_id": cid, "output_path": path}})
    return {"controller_actions": actions, "compiled_parts": [
        {"selected_capability": cid, "subgoal": subgoal},
    ]}


def test_report_cannot_overwrite_any_existing_named_operand_even_in_later_step(tmp_path, monkeypatch):
    monkeypatch.setattr(door, "ROOT", tmp_path)
    (tmp_path / "src").mkdir()
    target = tmp_path / "src/file.txt"
    target.write_text("original", encoding="utf-8")
    goal = "Read src/file.txt and then inspect it"
    plan = _plan("src/file.txt", subgoal="inspect src/file.txt", earlier=True)
    result = door._execute("preflight", goal, plan, REGISTRY, perf_counter_ns())
    assert result["status"] == "FAIL_CLOSED__REPORT_OUTPUT_OVERWRITES_TASK_FILE"
    assert result["executed"] is False
    assert result["report_output_collision"]["index"] == 1
    assert target.read_text(encoding="utf-8") == "original"


def test_unrelated_clause_cannot_authorize_report_destination(tmp_path, monkeypatch):
    monkeypatch.setattr(door, "ROOT", tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/file.txt").write_text("original", encoding="utf-8")
    goal = "Read src/file.txt and then save the report to src/file.txt"
    plan = _plan("src/file.txt", subgoal="Read src/file.txt")
    assert door._compound_report_overwrites_named_file(goal, plan, REGISTRY)["path"] == "src/file.txt"


def test_explicit_destination_and_editor_are_not_report_collisions(tmp_path, monkeypatch):
    monkeypatch.setattr(door, "ROOT", tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/report.json").write_text("old", encoding="utf-8")
    goal = "Save the report to src/report.json"
    assert door._compound_report_overwrites_named_file(
        goal, _plan("src/report.json", subgoal=goal), REGISTRY) is None
    assert door._compound_report_overwrites_named_file(
        "Edit src/report.json", _plan("src/report.json", cid=EDITOR, subgoal="Edit src/report.json"), REGISTRY) is None


def test_ambiguous_capability_parts_do_not_grant_a_destination(tmp_path, monkeypatch):
    monkeypatch.setattr(door, "ROOT", tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/report.json").write_text("old", encoding="utf-8")
    goal = "Read src/report.json and save the report to src/report.json"
    plan = _plan("src/report.json", subgoal="Save the report to src/report.json")
    plan["compiled_parts"].append({"selected_capability": REPORTER, "subgoal": "Read src/report.json"})
    assert door._compound_report_overwrites_named_file(goal, plan, REGISTRY)["path"] == "src/report.json"


def test_real_compound_refusal_preserves_target_and_reports_no_execution(tmp_path):
    from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler
    if compiler._sandbox_for_taught_programs() is None:
        pytest.skip("namespace sandbox unavailable")
    # Put the file under the real project root, like an ordinary front-door request.
    import tempfile
    import pathlib
    root = pathlib.Path(door.ROOT)
    with tempfile.TemporaryDirectory(prefix="compound_report_", dir=root / "canonical/astra_runtime/tmp") as directory:
        target = pathlib.Path(directory) / "calc.py"
        original = "def compute(a, b):\n    tmp = a * b\n    return tmp\n"
        target.write_text(original, encoding="utf-8")
        rel = target.relative_to(root).as_posix()
        result = door.solve({"task_id": "COMPOUND_REPORT_GUARD", "memory_policy": "OFF",
                             "goal": f"rename the variable 'tmp' to 'product' in the function 'compute' in {rel} and then delete {rel}"})
        assert result["status"] == "FAIL_CLOSED__REPORT_OUTPUT_OVERWRITES_TASK_FILE"
        assert result["executed"] is False
        assert target.read_text(encoding="utf-8") == original
