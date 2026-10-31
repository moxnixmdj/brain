"""Measure existing namespace launcher with real pytest in disposable projects.

Exploratory feasibility probe, not a verification gate or security certification.
Copies the current virtual environment into temporary input; no package install,
model calls, or repository writes. The existing launcher and read-only-query
wrapper transport process status/output and a JUnit report, not authenticated
evidence. A constructed project plugin overrides status and forges that report.
Only local, bounded fixtures are exercised. Exit nonzero when a control differs
from the expected observations; zero is not an admission of gate safety.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import shutil
import socket
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from canonical.runtime import zero_ambient_namespace_launcher_v1 as namespace  # noqa: E402
from canonical.runtime.bound_capabilities.quality_flake_detect_v1 import _junit_cases  # noqa: E402
from canonical.runtime.root3_read_only_local_file_query_executor_v1 import _WRAPPER  # noqa: E402


def _run(input_dir: Path, argv: list[str]) -> dict:
    spec = {"argv": ["/usr/bin/env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", *argv],
            "cwd": "/input/project", "timeout": 20}
    encoded = base64.urlsafe_b64encode(json.dumps(spec).encode()).decode()
    result = namespace.run_confined({
        "input_dir": str(input_dir), "allow_dev_null": True,
        "argv": ["/usr/bin/python3", "-I", "-c", _WRAPPER, encoded],
        "limits": {"pids": 32, "memory_mb": 512, "cpu_seconds": 20,
                   "wallclock_s": 25, "scratch_mb": 64, "max_file_mb": 16,
                   "nofile": 64, "broker_max_bytes": 1000000},
    })
    if result["status"] != "CHILD_EXITED" or result["returncode"] != 0:
        raise RuntimeError("LAUNCHER_FAILED:" + str(result["status"]) + ":" + str(result["returncode"]))
    report = json.loads(result["broker_payload"])
    if report["timed_out"] or type(report["returncode"]) is not int:
        raise RuntimeError("PYTEST_TIMED_OUT_OR_INVALID")
    return {"returncode": report["returncode"],
            "stdout": base64.b64decode(report["stdout_b64"], validate=True).decode(errors="replace"),
            "stderr": base64.b64decode(report["stderr_b64"], validate=True).decode(errors="replace"),
            "launcher_ms": result["wallclock_ms"]}


def main() -> int:
    env_root = Path(sys.prefix).resolve()
    if sys.prefix == sys.base_prefix or not (env_root / "bin/python").exists():
        raise SystemExit("Run with a virtual environment containing pytest")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        with tempfile.TemporaryDirectory(prefix="brain-confined-pytest-") as td:
            root = Path(td)
            host_file = root / "host-secret.txt"
            host_file.write_text("unchanged", encoding="utf-8")
            bundle = root / "input"
            bundle.mkdir()
            started = time.perf_counter()
            shutil.copytree(env_root, bundle / "venv", symlinks=True)
            copy_ms = (time.perf_counter() - started) * 1000
            project = bundle / "project"
            project.mkdir()
            (project / "test_confined.py").write_text(
                "from pathlib import Path\nimport socket\nimport pytest\n"
                "def test_input_is_read_only():\n"
                "    with pytest.raises(OSError): Path(__file__).with_name('new.py').write_text('x')\n"
                "def test_host_path_is_hidden():\n"
                f"    p = Path({str(host_file)!r})\n"
                "    assert not p.exists()\n"
                "    with pytest.raises(OSError): p.write_text('changed')\n"
                "def test_host_tcp_is_unreachable():\n"
                "    s = socket.socket(); s.settimeout(1)\n"
                f"    assert s.connect_ex(('127.0.0.1', {port})) != 0\n"
                "    s.close()\n"
                "def test_private_scratch_is_writable():\n"
                "    p = Path('/work/pytest-proof'); p.write_text('ok'); assert p.read_text() == 'ok'\n",
                encoding="utf-8")
            (project / "test_writable.py").write_text(
                "from pathlib import Path\nimport pytest\n"
                "def test_private_worktree_is_writable():\n"
                "    p = Path(__file__).with_name('generated.txt'); p.write_text('created'); assert p.read_text() == 'created'\n"
                "def test_original_input_is_read_only():\n"
                "    with pytest.raises(OSError): Path('/input/project/generated.txt').write_text('escape')\n"
                "def test_private_worktree_location():\n"
                "    assert Path(__file__).resolve().is_relative_to('/work/project')\n"
                "def test_input_unchanged():\n"
                "    assert not Path('/input/project/generated.txt').exists()\n",
                encoding="utf-8")
            (project / "test_negative.py").write_text(
                "import pytest\ndef test_failed():\n    assert False\n"
                "@pytest.mark.skip(reason='negative control')\ndef test_skipped():\n    pass\n",
                encoding="utf-8")
            (project / "force_exit.py").write_text(
                "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n", encoding="utf-8")
            (project / "forge_report.py").write_text(
                "from pathlib import Path\n"
                "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n"
                "def pytest_unconfigure(config):\n"
                "    Path(config.option.xmlpath).write_text('<testsuite><testcase classname=\"fabricated\" name=\"pass\"/></testsuite>')\n",
                encoding="utf-8")
            base = ["/input/venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
            positives = [_run(bundle, [*base, "test_confined.py"]) for _ in range(4)]
            # Use the existing launcher private scratch, not a writable host bind.
            bootstrap = ("import shutil,subprocess,sys; "
                         "shutil.copytree('/input/project','/work/project'); "
                         "sys.exit(subprocess.run([sys.executable,'-m','pytest','-q','-p',"
                         "'no:cacheprovider','test_writable.py'],cwd='/work/project').returncode)")
            writable = [_run(bundle, ["/input/venv/bin/python", "-c", bootstrap]) for _ in range(4)]
            fail = _run(bundle, [*base, "test_negative.py::test_failed"])
            skipped = _run(bundle, [*base, "test_negative.py::test_skipped"])
            override = _run(bundle, [*base, "-p", "force_exit", "test_negative.py::test_failed"])
            # Exercise report transport separately. The inner process can still
            # forge the report: this is a counterexample, not trusted evidence.
            junit_bootstrap = (
                "import base64,json,pathlib,shutil,subprocess,sys; "
                "shutil.copytree('/input/project','/work/project'); "
                "p=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',"
                "'--junitxml=/work/results.xml',*sys.argv[1:]],cwd='/work/project',capture_output=True); "
                "data=pathlib.Path('/work/results.xml').read_bytes(); "
                "print(json.dumps({'rc':p.returncode,'junit':base64.b64encode(data).decode(),"
                "'stdout':p.stdout.decode(errors='replace')}))"
            )
            reports = {}
            for name, pytest_args in (
                ("pass", ["test_writable.py"]),
                ("fail", ["test_negative.py::test_failed"]),
                ("skip", ["test_negative.py::test_skipped"]),
                ("forged_failure", ["-p", "forge_report", "test_negative.py::test_failed"]),
            ):
                outer = _run(bundle, ["/input/venv/bin/python", "-c", junit_bootstrap, *pytest_args])
                if outer["returncode"] != 0:
                    raise RuntimeError("JUNIT_BOOTSTRAP_FAILED:" + outer["stderr"])
                payload = json.loads(outer["stdout"])
                path = root / (name + ".xml")
                path.write_bytes(base64.b64decode(payload["junit"], validate=True))
                cases = _junit_cases(path)
                outcomes = [outcome for _, outcome in cases]
                reports[name] = {"pytest_returncode": payload["rc"], "outcomes": outcomes,
                                 "gate_would_accept": payload["rc"] == 0 and "passed" in outcomes
                                 and "failed" not in outcomes,
                                 "pytest_stdout": payload["stdout"].strip()}
            host_unchanged = host_file.read_text(encoding="utf-8") == "unchanged"
            result = {
                "schema": "BRAIN_CONFINED_PYTEST_FEASIBILITY_PROBE_V1",
                "positive_runs": [{"returncode": x["returncode"], "stdout": x["stdout"].strip(),
                                   "launcher_ms": x["launcher_ms"]} for x in positives],
                "positive_median_ms": round(statistics.median(x["launcher_ms"] for x in positives), 3),
                "writable_worktree_runs": [{"returncode": x["returncode"], "stdout": x["stdout"].strip(),
                                            "launcher_ms": x["launcher_ms"]} for x in writable],
                "writable_worktree_median_ms": round(statistics.median(x["launcher_ms"] for x in writable), 3),
                "venv_copy_ms": round(copy_ms, 3),
                "failure_control": {"returncode": fail["returncode"], "stdout": fail["stdout"].strip()},
                "skipped_control": {"returncode": skipped["returncode"], "stdout": skipped["stdout"].strip()},
                "forced_zero_failure_control": {"returncode": override["returncode"],
                                                "stdout": override["stdout"].strip()},
                "host_fixture_unchanged": host_unchanged,
                "junit_transport_controls": reports,
                "limitations": "Synthetic Linux host fixture; launcher is not integrated with gates. "
                               "Writable project copy is a small fixture, not a general environment. The transported JUnit "
                               "is not authenticated: the constructed plugin forges it and overrides exit status. "
                               "No claim of complete confinement against all attacks.",
                "terminal_authority": False,
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return int(not (all(x["returncode"] == 0 and "4 passed" in x["stdout"] for x in positives)
                            and all(x["returncode"] == 0 and "4 passed" in x["stdout"] for x in writable)
                            and fail["returncode"] == 1 and skipped["returncode"] == 0
                            and "1 skipped" in skipped["stdout"] and override["returncode"] == 0
                            and "1 failed" in override["stdout"] and host_unchanged
                            and reports["pass"]["gate_would_accept"]
                            and not reports["fail"]["gate_would_accept"]
                            and not reports["skip"]["gate_would_accept"]
                            and reports["forged_failure"]["gate_would_accept"]
                            and "1 failed" in reports["forged_failure"]["pytest_stdout"]))
    finally:
        listener.close()


if __name__ == "__main__":
    raise SystemExit(main())
