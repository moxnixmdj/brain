"""Real binding must preserve an explicitly stated destination, even if occupied.

No compiler/registry/filesystem mocks and no global spool manipulation. Tests
exercise existing capability selection and the public repair entry on owned
projects; no test result or successful repair is substituted.
"""
from copy import deepcopy
import pathlib
import tempfile
import uuid

import pytest

from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import swe_typed_plan_v1 as typed

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def project():
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stated-report-", dir=parent) as raw:
        root = pathlib.Path(raw)
        (root / "m.py").write_text('def f(x):\n    """post: _ == (x <= 3)"""\n    return x < 3\n')
        (root / "test_all.py").write_text(
            'from pathlib import Path\n'
            f'Path({str(root / "test-executions.txt")!r}).write_text("executed")\n'
            'from m import f\nassert f(3)\n')
        rel = root.relative_to(ROOT).as_posix()
        goal = (f"Write a measured acceptance repair report to {rel}/report.json "
                f"for the source root {rel} using the test path {rel}/test_all.py "
                "where `tests_pass` must be true and `python_parse_ok` must be true")
        yield root, goal


@pytest.mark.parametrize("occupied", [False, True])
@pytest.mark.parametrize("reuse_context", [False, True])
def test_typed_binding_preserves_stated_report_path(project, occupied, reuse_context):
    root, goal = project
    report = root / "report.json"
    if occupied:
        report.write_bytes(b"caller-owned report")
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    context = live.compile_against_live_registry(goal, ROOT) if reuse_context else None
    original = deepcopy(context)
    plan = typed.build_plan(goal, ROOT, compiled_context=context)
    assert plan is not None
    assert plan[2]["selected_capability"] == "python.software.repair.measured_acceptance.v1"
    assert plan[2]["inputs"]["output_path"] == report.relative_to(ROOT).as_posix()
    assert context == original
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}


@pytest.mark.parametrize("destination", ["report.json", "m.py", "test_all.py"])
def test_occupied_destination_refuses_before_execution_on_every_request(project, destination):
    root, goal = project
    goal = goal.replace("/report.json", "/" + destination)
    report = root / destination
    if not report.exists():
        report.write_bytes(b"caller-owned report")
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    for _ in range(3):
        request = {"task_id": "STATED_REPORT_" + uuid.uuid4().hex, "goal": goal,
                   "contract_checks": [{"source_path": "m.py", "max_examples": 20}]}
        result = door.solve(request)
        assert result["pass"] is False, result
        assert result["executed"] is False, result
        assert result["failure_class"] == "CONTRACT_CHECKS_UNBOUND", result
        assert result["reason"] == "CONTRACT_REPORT_ALREADY_EXISTS", result
        assert "typed_swe_retry" not in result
        assert before == {p.name: p.read_bytes() for p in root.iterdir()}


def test_two_explicit_report_destinations_are_not_arbitrarily_chosen(project):
    root, goal = project
    other = (root / "second.json").relative_to(ROOT).as_posix()
    goal = goal.replace(" for the source root", f" and save the report to {other} for the source root")
    assert typed.build_plan(goal, ROOT) is None
    assert not (root / "report.json").exists()
    assert not (root / "second.json").exists()


@pytest.mark.parametrize("suffix", ["/child.json", ".extra.json", "_other.json", "-other.json", "0.json"])
def test_destination_role_does_not_belong_to_a_prefix_of_the_path(project, suffix):
    root, _ = project
    short = (root / "input.json").relative_to(ROOT).as_posix()
    longer = short + suffix
    entry = live.load_verified_registry()["python.software.repair.measured_acceptance.v1"]
    goal = f"save the report to {longer} using the source {short}"
    assert front._named_output_destinations(goal, entry, ("output_path",), ROOT) == {longer}
    # The later occurrence is real and must still be recognized. A final period
    # terminates the sentence, whereas a dot followed by an extension does not.
    goal += f" then save the report to {short}."
    assert front._named_output_destinations(goal, entry, ("output_path",), ROOT) == {short, longer}
