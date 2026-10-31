"""Real normal-entry task binding and report replay; no mocked tools/adapters."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import time

import pytest

from canonical.runtime import crossfile_task_binding_v1 as binding
from canonical.runtime import goal_compiler
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import raw_goal_trace_acceptance_v1 as raw_acceptance
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as workflow
from canonical.tests.test_task_bound_crossfile_workflow_v1 import repo as fixture_repo, contents

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def task():
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="front-crossfile-", dir=parent) as raw:
        path = fixture_repo.__wrapped__(Path(raw))
        yield path


def request(path, mode="issue", verb="Write"):
    rel = path.relative_to(ROOT).as_posix()
    return {"task_id": "CROSSFILE_PUBLIC_ENTRY", "goal":
            f"{verb} a cross-file repair report to {rel}/out/report.json "
            f"for the source root {rel}/src using the {mode} path {rel}/{mode}.json"}


def reverify(result, goal=None):
    goal = result["raw_goal"] if goal is None else goal
    registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_bytes())["capabilities"]
    contract = compile_contract(goal, source_id="user", routing_target_effects=registry[binding.CAPABILITY_ID]["provides"])
    return raw_acceptance.verify(goal=goal, compiled_plan={"selected_capability": binding.CAPABILITY_ID},
                                 execution=result["controller_execution"]["trace"],
                                 raw_contract=contract, root=ROOT)


@pytest.mark.parametrize("mode,verb", [("issue", "Write"), ("task", "Write"), ("issue", "Create")])
def test_normal_entry_binds_and_replays_actual_crossfile_change(task, mode, verb):
    req = request(task, mode, verb)
    before = contents(task / "src")
    request_before = deepcopy(req)
    started = time.perf_counter_ns()
    result = door.solve(req)
    wall = time.perf_counter_ns() - started
    assert result["pass"] is True, result
    assert 0.9 * wall <= result["elapsed_ns"] <= wall
    assert result["compiled_capability_id"] == binding.CAPABILITY_ID
    assert result["crossfile_acceptance_complete"] is True
    assert result["semantic_acceptance_complete"] is True
    assert len(result["accepted_raw_obligation_ids"]) == result["raw_acceptance_obligation_count"]
    evidence = result["raw_goal_acceptance"]["reinspection_ledger"][0]["reinspection"]
    assert evidence["patches_reconstructed"] == 3
    assert evidence["tests_replayed"] == 1
    assert evidence["independent_semantic_oracle_credit"] is False
    assert result["terminal_credit_delta"] == 0
    assert before == contents(task / "src")
    assert req == request_before
    report = json.loads((task / "out/report.json").read_bytes())
    assert report["request_binding"]["input_key"] == mode + "_path"
    assert report["request_binding_sha256"] == binding.digest(report["request_binding"])
    assert not list((task / "out").glob(".crossfile-*"))


def test_normal_entry_move_can_create_a_module(task):
    (task / "issue.json").write_text(json.dumps({"issue_id": "MOVE",
        "title": "Move helper from pkg/core.py to pkg/ops.py"}))
    result = door.solve(request(task))
    assert result["pass"] is True, result
    report = json.loads((task / "out/report.json").read_bytes())
    created = [p for p in report["patches"] if p["created"]]
    assert [p["relative_path"] for p in created] == ["pkg/ops.py"]
    assert result["crossfile_acceptance_complete"] is True
    assert not (task / "src/pkg/ops.py").exists()


def test_request_local_binding_does_not_mutate_registry(task):
    req = request(task)
    original = live.compile_against_live_registry(req["goal"], ROOT)
    before = deepcopy(original)
    updated = binding.bind_context(req["goal"], original, ROOT)
    assert original == before
    assert "issue_path" not in original[2]["inputs"]
    assert updated[2]["inputs"]["issue_path"].endswith("/issue.json")
    assert "request_binding" not in original[1][binding.CAPABILITY_ID]["action_template"]["args"]


@pytest.mark.parametrize("extra", [" and preserve every secret file", "; then deploy the service",
                                   " where all hidden requirements hold"])
def test_extra_goal_requirements_refuse_before_execution(task, extra):
    req = request(task)
    req["goal"] += extra
    before = contents(task)
    result = door.solve(req)
    assert result["pass"] is False
    assert result["executed"] is False
    assert result["failure_class"] == "CROSSFILE_TASK_UNBOUND"
    assert contents(task) == before


@pytest.mark.parametrize("change", ["malformed", "unknown_field", "missing_title", "missing_file"])
def test_invalid_issue_binding_has_no_tool_side_effects(task, change):
    issue = task / "issue.json"
    if change == "malformed":
        issue.write_text("not JSON")
    elif change == "missing_file":
        issue.unlink()
    else:
        payload = json.loads(issue.read_bytes())
        if change == "unknown_field":
            payload["additional_requirements"] = "do not discard this"
        else:
            del payload["title"]
        issue.write_text(json.dumps(payload))
    before = contents(task)
    result = door.solve(request(task))
    assert result["pass"] is False
    assert result["executed"] is False
    assert contents(task) == before


def test_existing_report_is_not_overwritten(task):
    (task / "out").mkdir()
    report = task / "out/report.json"
    report.write_bytes(b"user-owned report")
    result = door.solve(request(task))
    assert result["pass"] is False
    assert result["executed"] is False
    assert report.read_bytes() == b"user-owned report"


def test_contract_checks_cannot_be_dropped_by_crossfile_route(task):
    req = request(task)
    req["contract_checks"] = [{"source_path": "pkg/core.py"}]
    result = door.solve(req)
    assert result["pass"] is False
    assert result["executed"] is False
    assert result["structured_contract_acceptance_complete"] is False
    assert not (task / "out").exists()


def test_unrelated_regression_failure_cannot_be_retried_away(task):
    (task / "src/tests/test_other.py").write_text("def test_other():\n    assert 1 == 2\n")
    result = door.solve(request(task))
    assert result["pass"] is False
    assert result["executed"] is True
    assert result["crossfile_acceptance_complete"] is False
    assert "typed_swe_retry" not in result
    report = json.loads((task / "out/report.json").read_bytes())
    assert report["regression"]["failed"] == 1
    assert report["patches"] == []


@pytest.mark.parametrize("target", ["issue", "source"])
def test_bound_preimage_changes_refuse_before_adapter_side_effects(task, target):
    req = request(task)
    plan = binding.bind_context(req["goal"], live.compile_against_live_registry(req["goal"], ROOT), ROOT)
    action = goal_compiler._render_template(plan[1][binding.CAPABILITY_ID]["action_template"], plan[2]["inputs"])
    if target == "issue":
        (task / "issue.json").write_text('{"issue_id":"CHANGED","title":"Rename helper to other"}')
    else:
        (task / "src/pkg/core.py").write_text("def helper(x):\n    return 100\n")
    before = contents(task)
    with pytest.raises(ValueError, match="CROSSFILE_REQUEST_PREIMAGE_CHANGED"):
        workflow.run(action["args"], ROOT)
    assert contents(task) == before


@pytest.mark.parametrize("mutation", ["binding", "edits", "candidate_hash", "patch_hash", "empty_patches",
                                       "preimage_hash", "diff", "test_count", "zero_tests", "failed_tests",
                                       "diff_hash", "report_source", "oracle_credit"])
def test_reinspection_refuses_tampered_real_artifact_even_with_new_artifact_hash(task, mutation):
    result = door.solve(request(task))
    assert result["pass"] is True
    report_path = task / "out/report.json"
    report = json.loads(report_path.read_bytes())
    if mutation == "binding":
        report["request_binding"]["input_sha256"] = "0" * 64
    elif mutation == "edits":
        report["planned_edits"][0]["new_name"] = "unrequested"
    elif mutation == "candidate_hash":
        report["candidate_content_sha256"] = "0" * 64
    elif mutation == "patch_hash":
        report["patches"][0]["candidate_sha256"] = "0" * 64
    elif mutation == "preimage_hash":
        report["patches"][0]["original_sha256"] = "0" * 64
    elif mutation == "empty_patches":
        report["patches"] = []
    elif mutation == "diff":
        report["unified_diff"] += "unrelated data"
    elif mutation == "failed_tests":
        report["regression"]["pass"] = False
    elif mutation == "diff_hash":
        report["diff_sha256"] = "0" * 64
    elif mutation == "report_source":
        report["source_root"] = "unrelated"
    elif mutation == "oracle_credit":
        report["independent_semantic_oracle_credit"] = True
    else:
        report["regression"]["completed"] = True if mutation == "test_count" else 0
    data = json.dumps(report).encode()
    report_path.write_bytes(data)
    # Preserve the generic artifact-hash check so task/candidate reinspection
    # must reject the forgery, not merely its stale digest.
    new_hash = hashlib.sha256(data).hexdigest()
    result["controller_execution"]["trace"][0]["result"]["output_sha256"] = new_hash
    checked = reverify(result)
    assert checked["pass"] is False
    assert checked["semantic_acceptance_complete"] is False


def test_reinspection_rejects_requirement_added_after_execution(task):
    result = door.solve(request(task))
    assert result["pass"] is True
    checked = reverify(result, result["raw_goal"] + " and deploy to production")
    assert checked["pass"] is False
    assert checked["semantic_acceptance_complete"] is False


def test_reinspection_detects_source_change_after_execution(task):
    result = door.solve(request(task))
    assert result["pass"] is True
    (task / "src/pkg/core.py").write_text("def helper(x):\n    return 500\n")
    assert reverify(result)["pass"] is False


@pytest.mark.parametrize("weaken_tests", [False, True])
def test_forged_patch_cannot_change_behavior_or_weaken_tests_even_with_consistent_hashes(task, weaken_tests):
    import difflib
    from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
    result = door.solve(request(task))
    assert result["pass"] is True
    path = task / "out/report.json"
    report = json.loads(path.read_bytes())
    after = {}
    for patch in report["patches"]:
        rel = patch["relative_path"]
        original = (task / "src" / rel).read_text()
        candidate = door._acceptance._apply_unified_diff(original, patch["unified_diff"])
        if rel == "pkg/core.py":
            candidate = candidate.replace("return len(str(x).strip()) + 1", "return 999")
        if weaken_tests and rel == "tests/test_core.py":
            candidate = candidate.replace("assert compute(' A ') == 2", "assert True")
            candidate = candidate.replace("assert twice(' A ') == 4", "assert True")
        after[rel] = candidate.encode()
        patch["unified_diff"] = "".join(difflib.unified_diff(
            original.splitlines(keepends=True), candidate.splitlines(keepends=True),
            fromfile="a/" + rel, tofile="b/" + rel))
        patch["candidate_sha256"] = hashlib.sha256(after[rel]).hexdigest()
    manifest = tree_manifest(task / "src")
    for row in manifest["files"]:
        if row["path"] in after:
            row["sha256"] = hashlib.sha256(after[row["path"]]).hexdigest()
            row["bytes"] = len(after[row["path"]])
    report["candidate_content_sha256"] = binding.digest({"files": manifest["files"]})
    report["unified_diff"] = "".join(p["unified_diff"] for p in report["patches"])
    report["diff_sha256"] = hashlib.sha256(report["unified_diff"].encode()).hexdigest()
    data = json.dumps(report).encode()
    path.write_bytes(data)
    result["controller_execution"]["trace"][0]["result"]["output_sha256"] = hashlib.sha256(data).hexdigest()
    checked = reverify(result)
    assert checked["pass"] is False
    assert "DIFF_IS_NOT_THE_EXACT_REQUESTED_TRANSFORMATION" in checked["reason"]


def test_producer_success_is_insufficient_when_separate_replay_fails(task):
    marker = task / "test-invocation-count.txt"
    test = task / "src/tests/test_core.py"
    test.write_text(test.read_text() +
        f"\n    counter = pathlib.Path({str(marker)!r})\n"
        "    count = int(counter.read_text()) + 1 if counter.exists() else 1\n"
        "    counter.write_text(str(count))\n"
        "    assert count <= 2\n")
    result = door.solve(request(task))
    report = json.loads((task / "out/report.json").read_bytes())
    assert report["pass"] is True  # selected suite + producer's full suite passed
    assert marker.read_text() == "3"  # the verifier really ran another process
    assert result["pass"] is False
    assert result["semantic_acceptance_complete"] is False
    assert result["crossfile_acceptance_complete"] is False
    assert "REPLAY_DOES_NOT_CONFIRM_REPORTED_TESTS" in result["raw_goal_acceptance"]["reason"]


@pytest.mark.parametrize("key", ["title", "body", "additional_requirements"])
def test_structured_task_cannot_hide_prose_requirements_as_metadata(task, key):
    path = task / "task.json"
    payload = json.loads(path.read_bytes())
    payload[key] = "Also deploy the service and preserve every undocumented behavior"
    path.write_text(json.dumps(payload))
    before = contents(task)
    result = door.solve(request(task, "task"))
    assert result["pass"] is False
    assert result["executed"] is False
    assert contents(task) == before
