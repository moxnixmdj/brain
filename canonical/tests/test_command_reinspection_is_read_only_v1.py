"""Re-inspection must not change the world or accept a forged stdout artifact.

The CLI adapter is an existing shared path, not an independent proof by itself.
These tests exercise its actual inspector and the real namespace; the only mock
is the unavailable-namespace case, where falling back to the host is forbidden.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from unittest import mock

import pytest

from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
from canonical.runtime import zero_ambient_namespace_launcher_v1 as namespace
from canonical.runtime.bound_capabilities import cli_command
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract


def inspect(root: Path, argv: list[str], stdout: str = "", code: int = 0,
            stderr: str = ""):
    return acceptance._inspect_shell_command_run(
        {"argv": argv}, {"stdout": stdout, "returncode": code, "stderr": stderr}, root)


@pytest.fixture(scope="module")
def namespace_ready(tmp_path_factory):
    root = tmp_path_factory.mktemp("reinspection_namespace_probe")
    replay, reason = acceptance._replay_in_read_only_namespace(
        ["python3", "-c", "print('namespace-ready')"], root)
    if replay is None:
        pytest.skip("read-only namespace unavailable on this host: " + reason)
    assert replay["returncode"] == 0
    assert replay["stdout"] == b"namespace-ready\n"


def test_plain_cat_reopens_real_input_without_running_a_process(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"alpha\n")
    (tmp_path / "b.txt").write_bytes(b"beta\n")
    with mock.patch.object(namespace, "run_confined", side_effect=AssertionError("not needed")):
        ok, reason, evidence = inspect(tmp_path, ["cat", "a.txt", "b.txt"], "alpha\nbeta\n")
    assert ok, reason
    assert evidence["input_files_reopened"] == 2
    assert evidence["command_re_run"] is False
    (tmp_path / "b.txt").write_bytes(b"changed\n")
    ok, reason, _ = inspect(tmp_path, ["cat", "a.txt", "b.txt"], "alpha\nbeta\n")
    assert not ok
    assert reason == "COMMAND_OUTPUT_NOT_REPRODUCED"


def test_simple_line_count_reopens_real_bytes_without_a_process(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"alpha\nbeta\nnot-a-complete-line")
    with mock.patch.object(namespace, "run_confined", side_effect=AssertionError("not needed")):
        ok, reason, evidence = inspect(tmp_path, ["wc", "-l", "source"], "2 source\n")
    assert ok, reason
    assert evidence["input_files_reopened"] == 1
    assert evidence["command_re_run"] is False
    source.write_bytes(b"one\n")
    ok, reason, _ = inspect(tmp_path, ["wc", "-l", "source"], "2 source\n")
    assert not ok
    assert reason == "COMMAND_OUTPUT_NOT_REPRODUCED"


@pytest.mark.parametrize("argv", [
    ["find", ".", "-name", "victim", "-delete"],
    ["find", ".", "-name", "not-present", "-delete"],
    ["find", ".", "-exec", "sh", "-c", "echo changed > victim", ";"],
    ["sed", "-n", "w victim", "source"],
    ["sed", "-n", "s/a/b/w victim", "source"],
    ["sed", "-n", "s/a/b/e", "source"],
    ["sed", "-i.bak", "s/a/b/", "source"],
    ["sort", "-ovictim", "source"],
])
def test_mutating_or_unproven_command_shapes_are_not_replayed(tmp_path, argv):
    (tmp_path / "source").write_text("a\n", encoding="utf-8")
    victim = tmp_path / "victim"
    victim.write_text("keep\n", encoding="utf-8")
    # A matching empty producer report used to both mutate this file and be
    # accepted. No shell or interpreter needs to be executed to reject it.
    with mock.patch.object(namespace, "run_confined", side_effect=AssertionError("not needed")):
        ok, reason, _ = inspect(tmp_path, argv)
    assert not ok, (argv, reason)
    assert victim.read_text(encoding="utf-8") == "keep\n"
    assert (tmp_path / "source").read_text(encoding="utf-8") == "a\n"
    assert not (tmp_path / "source.bak").exists()


@pytest.mark.parametrize(("argv", "expected"), [
    (["sed", "-n", "1p", "source"], "alpha\n"),
    (["sed", "-e", "s|alpha|delta|", "source"], "delta\nbeta\n"),
    (["find", ".", "-name", "source", "-print"], "./source\n"),
    (["sort", "source"], "alpha\nbeta\n"),
])
def test_readers_remain_checkable_inside_the_namespace(namespace_ready, tmp_path, argv, expected):
    (tmp_path / "source").write_text("alpha\nbeta\n", encoding="utf-8")
    ok, reason, evidence = inspect(tmp_path, argv, expected)
    assert ok, (argv, reason)
    assert evidence["command_re_run"] is True
    assert evidence["replay_read_only_namespace"] is True
    assert (tmp_path / "source").read_text(encoding="utf-8") == "alpha\nbeta\n"


def test_python_script_is_confined_even_though_its_path_is_in_the_tree(namespace_ready, tmp_path):
    (tmp_path / "write.py").write_text(
        "from pathlib import Path\nPath('victim').write_text('changed')\n", encoding="utf-8")
    victim = tmp_path / "victim"
    victim.write_text("keep", encoding="utf-8")
    ok, reason, _ = inspect(tmp_path, ["python3", "write.py"])
    assert not ok
    assert reason == "COMMAND_RETURN_CODE_NOT_REPRODUCED"
    assert victim.read_text(encoding="utf-8") == "keep"


def test_a_read_only_python_script_still_reproduces(namespace_ready, tmp_path):
    (tmp_path / "read.py").write_text("print('hello')\n", encoding="utf-8")
    ok, reason, evidence = inspect(tmp_path, ["python3", "read.py"], "hello\n")
    assert ok, reason
    assert evidence["replay_read_only_namespace"] is True


def test_no_host_fallback_if_confinement_is_unavailable(tmp_path):
    (tmp_path / "write.py").write_text(
        "from pathlib import Path\nPath('marker').write_text('changed')\n", encoding="utf-8")
    with mock.patch.object(namespace, "run_confined", side_effect=RuntimeError("not available")):
        ok, reason, _ = inspect(tmp_path, ["python3", "write.py"])
    assert not ok
    assert reason == "COMMAND_REINSPECTION_CONFINEMENT_UNAVAILABLE"
    assert not (tmp_path / "marker").exists()


def test_a_repo_executable_named_cat_is_not_treated_as_system_cat(tmp_path):
    fake = tmp_path / "cat"
    fake.write_text("#!/bin/sh\necho altered > marker\n", encoding="utf-8")
    fake.chmod(0o755)
    (tmp_path / "source").write_text("source\n", encoding="utf-8")
    ok, _, _ = inspect(tmp_path, [str(fake), "source"], "source\n")
    assert not ok
    assert not (tmp_path / "marker").exists()


@pytest.mark.parametrize(("goal", "args", "expected"), [
    ("Run the shell command cat source.txt", {"argv": ["cat", "source.txt"]}, True),
    ("Run the shell command 'cat source.txt'", {"argv": ["cat", "source.txt"]}, True),
    ("Run the shell command cat 'and delete'", {"argv": ["cat", "and delete"]}, True),
    ("Run the shell command cat source.txt and delete other.txt",
     {"argv": ["cat", "source.txt"]}, False),
    ("Run the shell command cat source.txt and delete other.txt",
     {"argv": ["cat", "source.txt", "and", "delete", "other.txt"]}, False),
    ("Run the shell command cat source.txt && rm other.txt",
     {"argv": ["cat", "source.txt", "&&", "rm", "other.txt"]}, False),
    ("Run the shell command cat source.txt and save it to output.txt",
     {"argv": ["cat", "source.txt"], "write_stdout_to_output": "true",
      "output_path": "output.txt"}, True),
    ("Run the shell command cat source.txt and save it to other.txt",
     {"argv": ["cat", "source.txt"], "write_stdout_to_output": "true",
      "output_path": "output.txt"}, False),
])
def test_whole_explicit_command_sentence_has_no_unchecked_tail(goal, args, expected):
    assert acceptance._single_explicit_command_covers_sentence(goal, args) is expected


def test_extra_unperformed_obligations_never_receive_acceptance_credit_in_two_bounded_forms():
    from execution_guard.raw_acceptance_obligation_gap_probe_v1 import measure

    result = measure()
    rows = [row for row in result["rows"] if row["trace_shape"] in ("single_command", "single_text_write")]
    assert len(rows) == 8
    for row in rows:
        assert row["extra_action_not_performed"] is True
        assert row["localizer_semantic_residual_count"] > 0
        assert row["semantic_acceptance_complete"] is False
        assert row["accepted_obligation_count"] == 0
        expected = ("COMMAND_GOAL_HAS_UNVERIFIED_TEXT" if row["capability_id"] == "shell.command.run"
                    else "TEXT_WRITE_GOAL_HAS_UNVERIFIED_TEXT")
        assert row["verifier_reason"] == expected


@pytest.mark.parametrize(("goal", "content", "output", "expected"), [
    ("Write the text hello to the file out.txt", "hello", "out.txt", True),
    ("Write the text 'hello and delete' to the output file out.txt", "hello and delete", "out.txt", True),
    ("Write the file content hello to the file out.txt.", "hello", "out.txt", True),
    ("Delete other.txt, then write the text hello to the file out.txt", "hello", "out.txt", False),
    ("Write the text hello to the file out.txt and delete other.txt", "hello", "out.txt", False),
    ("Write the text HELLO to the file out.txt", "hello", "out.txt", False),
    ("Write the text hello to the file wrong.txt", "hello", "out.txt", False),
])
def test_literal_write_proof_covers_the_whole_sentence(goal, content, output, expected):
    assert acceptance._single_text_write_covers_sentence(
        goal, {"content": content, "output_path": output}) is expected


def test_complete_literal_text_write_still_gets_reinspected(tmp_path):
    from canonical.runtime.bound_capabilities import file_write_text

    goal = "Write the text 'hello' to the file out.txt"
    args = {"capability_id": "text.file.write", "content": "hello", "output_path": "out.txt"}
    result = file_write_text.run(args, tmp_path)
    contract = compile_contract(goal, source_id="user", routing_target_effects=["text.file.available"])
    trace = [{"plan": {"args": args}, "result": result}, {"result": {"type": "finish"}}]
    checked = acceptance.verify(goal=goal, compiled_plan={"selected_capability": "text.file.write"},
                                execution=trace, raw_contract=contract, root=tmp_path)
    assert checked["semantic_acceptance_complete"] is True, checked
    assert checked["reinspection_ledger"][0]["reinspection"]["file_reopened"] is True
    assert (tmp_path / "out.txt").read_bytes() == b"hello"


def test_acceptance_reopens_stdout_destination_not_just_its_claimed_hash(tmp_path):
    (tmp_path / "source.txt").write_bytes(b"SOURCE\n")
    goal = "Run the shell command cat source.txt and save it to output.txt"
    args = {"capability_id": "shell.command.run", "argv": ["cat", "source.txt"],
            "output_path": "output.txt", "write_stdout_to_output": "true"}
    result = cli_command.run(args, str(tmp_path))
    contract = compile_contract(goal, source_id="user", routing_target_effects=["shell.command.result"])
    trace = [{"plan": {"args": args}, "result": result}, {"result": {"type": "finish"}}]

    def verify():
        return acceptance.verify(goal=goal, compiled_plan={"selected_capability": "shell.command.run"},
                                 execution=trace, raw_contract=contract, root=tmp_path)

    good = verify()
    assert good["semantic_acceptance_complete"] is True, good
    assert good["reinspection_ledger"][0]["reinspection"]["stdout_destination_checked"] is True

    (tmp_path / "output.txt").write_bytes(b"FORGED\n")
    # Updating the producer's hash defeats a mere digest check; the verifier
    # must compare the actual destination bytes with independently read stdout.
    result["output_sha256"] = hashlib.sha256((tmp_path / "output.txt").read_bytes()).hexdigest()
    bad = verify()
    assert bad["semantic_acceptance_complete"] is False
    assert bad["reason"] == "COMMAND_STDOUT_DESTINATION_MISMATCH"


def test_optional_null_device_exposes_no_other_host_devices(namespace_ready, tmp_path):
    script = (
        "import json,os; "
        "f=open('/dev/null','r+'); before=f.read(); f.write('x'); f.flush(); "
        "os.write(int(os.environ['PROJECT_BRAIN_BROKER_FD']), "
        "json.dumps({'devices':os.listdir('/dev'),'null_read':before}).encode())"
    )
    result = namespace.run_confined({
        "input_dir": str(tmp_path), "allow_dev_null": True,
        "argv": ["/usr/bin/python3", "-I", "-c", script],
    })
    assert result["status"] == "CHILD_EXITED"
    assert result["returncode"] == 0
    import json
    assert json.loads(result["broker_payload"]) == {"devices": ["null"], "null_read": ""}


def test_null_device_permission_must_be_explicit_boolean(tmp_path):
    with pytest.raises(namespace.NamespaceConfinementError, match="ALLOW_DEV_NULL_MUST_BE_BOOLEAN"):
        namespace.canonical_policy({"input_dir": str(tmp_path), "argv": ["/usr/bin/python3"],
                                    "allow_dev_null": "yes"})


def test_confinement_primitives_do_not_follow_a_caller_controlled_path(namespace_ready, tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "unshare"
    marker = tmp_path / "host-marker"
    fake.write_text("#!/bin/sh\nprintf unsafe > '" + str(marker) + "'\n", encoding="utf-8")
    fake.chmod(0o755)
    with mock.patch.dict(os.environ, {"PATH": str(bindir) + ":/usr/bin:/bin"}):
        result = namespace.run_confined({
            "input_dir": str(tmp_path),
            "argv": ["/usr/bin/python3", "-I", "-c",
                     "import os; os.write(int(os.environ['PROJECT_BRAIN_BROKER_FD']), b'ok')"],
        })
    assert result["status"] == "CHILD_EXITED"
    assert result["returncode"] == 0
    assert result["broker_payload"] == b"ok"
    assert not marker.exists()


def test_launcher_finds_system_chroot_when_sbin_is_not_in_path(namespace_ready, tmp_path):
    # This host's chroot is /usr/sbin/chroot, but its non-root PATH omits sbin.
    # The launcher must find it without asking the caller to alter PATH globally.
    if not Path("/usr/sbin/chroot").is_file() or Path("/usr/bin/chroot").exists():
        pytest.skip("this host does not have the sbin-only chroot layout")
    with mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}):
        result = namespace.run_confined({
            "input_dir": str(tmp_path),
            "argv": ["/usr/bin/python3", "-I", "-c",
                     "import os; os.write(int(os.environ['PROJECT_BRAIN_BROKER_FD']), b'ok')"],
        })
    assert result["status"] == "CHILD_EXITED"
    assert result["returncode"] == 0
    assert result["broker_payload"] == b"ok"
