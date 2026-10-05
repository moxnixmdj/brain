from __future__ import annotations

import pathlib

from canonical.runtime.root3_runtime_process_universe_v2 import compile_universe


def write(root: pathlib.Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_aliases_reduce_to_two_chokepoints(tmp_path):
    write(tmp_path, "canonical/runtime/a.py", "import subprocess as sp\nsp.run(['x'])\n")
    write(tmp_path, "canonical/runtime/b.py", "from subprocess import Popen as P\nP(['x'])\n")
    out = compile_universe(tmp_path)
    assert out["direct_process_source_site_count"] == 2
    assert out["interception_api_counts"] == {
        "subprocess.Popen": 1,
        "subprocess.run": 1,
    }
    assert out["two_chokepoint_preconditions_proved_for_parseable_runtime_python"]


def test_check_output_normalizes_to_run(tmp_path):
    write(
        tmp_path,
        "canonical/runtime/a.py",
        "import subprocess\nsubprocess.check_output(['x'])\n",
    )
    out = compile_universe(tmp_path)
    assert out["process_sites"][0]["source_api"] == "subprocess.check_output"
    assert out["process_sites"][0]["interception_api"] == "subprocess.run"


def test_unmediated_os_system_keeps_proof_open(tmp_path):
    write(tmp_path, "canonical/runtime/a.py", "import os\nos.system('x')\n")
    out = compile_universe(tmp_path)
    assert out["unmediated_process_sites"][0]["source_api"] == "os.system"
    assert not out["two_chokepoint_preconditions_proved_for_parseable_runtime_python"]
    assert out["minimum_direct_python_mediation_chokepoints"] == []


def test_parse_failure_is_explicit_and_content_addressed(tmp_path):
    write(tmp_path, "canonical/runtime/bad.py", "def nope(:\n")
    out = compile_universe(tmp_path)
    assert out["python_file_count"] == 1
    assert out["standard_python_nonexecutable_file_count"] == 1
    row = out["standard_python_nonexecutable_files"][0]
    assert row["module_path"] == "canonical/runtime/bad.py"
    assert len(row["git_blob_sha"]) == 40


def test_process_import_rebinding_fails_two_chokepoint_precondition(tmp_path):
    write(
        tmp_path,
        "canonical/runtime/a.py",
        "import subprocess\nsubprocess = object()\n",
    )
    out = compile_universe(tmp_path)
    assert out["process_import_rebindings"]
    assert not out["two_chokepoint_preconditions_proved_for_parseable_runtime_python"]


def test_literal_getattr_is_not_a_bypass(tmp_path):
    write(
        tmp_path,
        "canonical/runtime/a.py",
        "import subprocess\ngetattr(subprocess, 'run')(['x'])\n",
    )
    out = compile_universe(tmp_path)
    assert out["direct_process_source_site_count"] == 1
    assert out["process_sites"][0]["reflection"] == "LITERAL_GETATTR"
