"""A re-inspected operation is not proof of the rest of the user's task."""
from pathlib import Path
import tarfile

from canonical.runtime.bound_capabilities import archive_verify_gnu_tar, cli_command
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_trace_acceptance_v1 import verify
from execution_guard.raw_acceptance_obligation_gap_probe_v1 import measure
from execution_guard.raw_acceptance_uncovered_inspectors_probe_v1 import measure as measure_archive_followups


def test_other_capability_inspectors_do_not_credit_unperformed_instructions():
    report = measure_archive_followups()
    assert report["case_count"] == 4
    assert report["unsafe_acceptances"] == 0, report
    assert all(row["followup_unperformed"] is True for row in report["rows"])
    assert all(row["semantic_acceptance_complete"] is False for row in report["rows"])
    assert all(row["reason"] == "CAPABILITY_RAW_OBLIGATIONS_NOT_PROVEN" for row in report["rows"])


def test_a_real_complete_archive_check_is_accepted_when_the_whole_goal_is_bound(tmp_path: Path):
    (tmp_path / "canonical").mkdir()
    manifest = tmp_path / "canonical/manifest.json"
    manifest.write_text('{"records": []}')
    with tarfile.open(tmp_path / "bundle.tar.gz", "w:gz") as archive:
        archive.add(manifest, arcname="canonical/manifest.json")
    args = {"capability_id": "archive.verify.tar_gz.gnu", "archive_path": "bundle.tar.gz",
            "manifest_path": "canonical/manifest.json"}
    produced = archive_verify_gnu_tar.run(args, tmp_path)
    goal = "Verify bundle.tar.gz against canonical/manifest.json"
    contract = compile_contract(goal, source_id="user", routing_target_effects=["archive.verified"])
    result = verify(goal=goal, compiled_plan={"selected_capability": args["capability_id"]},
                    execution=[{"plan": {"args": args}, "result": produced},
                               {"result": {"type": "finish"}}],
                    raw_contract=contract, root=tmp_path)
    assert result["semantic_acceptance_complete"] is True
    assert result["independent_reinspection"] is True
    assert result["reinspection_ledger"][0]["reinspection"]["manifest_member_set_checked"] is True


def test_single_and_composed_traces_do_not_credit_the_unperformed_effect():
    report = measure()
    assert report["case_count"] == 16
    assert report["unsafe_acceptance_count"] == 0, report
    for row in report["rows"]:
        assert row["extra_action_not_performed"] is True
        assert row["semantic_acceptance_complete"] is False
        assert row["accepted_obligation_count"] == 0


def test_a_real_complete_two_step_command_trace_is_provisional_without_semantic_proof(tmp_path: Path):
    # This really did the two actions. The generic verifier currently has no
    # whole-goal proof for their composition, so it must not claim it does.
    (tmp_path / "source.txt").write_text("source\n")
    args = {"capability_id": "shell.command.run", "argv": ["cat", "source.txt"]}
    first = cli_command.run(args, str(tmp_path))
    second = cli_command.run(args, str(tmp_path))
    goal = "Run the shell command cat source.txt. Run the shell command cat source.txt."
    contract = compile_contract(goal, source_id="user", routing_target_effects=["shell.command.result"])
    plan = {"compiled_parts": [{"selected_capability": "shell.command.run"} for _ in range(2)]}
    trace = [{"plan": {"args": args}, "result": result} for result in (first, second)]
    trace.append({"result": {"type": "finish"}})
    result = verify(goal=goal, compiled_plan=plan, execution=trace,
                    raw_contract=contract, root=tmp_path)
    assert result["semantic_acceptance_complete"] is False
    assert result["accepted_obligation_ids"] == []
    assert result["reason"] == "MULTI_STEP_RAW_OBLIGATIONS_NOT_PROVEN"


def test_implicit_read_is_not_claimed_complete_without_a_whole_goal_verifier(tmp_path: Path):
    (tmp_path / "source.txt").write_text("source\n")
    args = {"capability_id": "shell.command.run", "argv": ["cat", "source.txt"]}
    produced = cli_command.run(args, str(tmp_path))
    goal = "Read source.txt"
    contract = compile_contract(goal, source_id="user", routing_target_effects=["shell.command.result"])
    trace = [{"plan": {"args": args}, "result": produced}, {"result": {"type": "finish"}}]
    result = verify(goal=goal, compiled_plan={"selected_capability": "shell.command.run"},
                    execution=trace, raw_contract=contract, root=tmp_path)
    assert result["semantic_acceptance_complete"] is False
    assert result["accepted_obligation_ids"] == []
    assert result["reason"] == "COMMAND_GOAL_HAS_UNVERIFIED_TEXT"
