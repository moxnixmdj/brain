#!/usr/bin/env python3
"""Honest tests for environment_scan_know_v1 — the scan → known/unknown → gap flow.

Covers:
  - refusals by name (empty goal, not a directory, no evidence)
  - generic (non-Python) environments: scan, local guide, never fabricate
  - the Python run-tests path (broker-verified by execution) in a child process
    when a pytest-capable interpreter is available; honestly skipped otherwise
  - the flow never persists anything (the flow's own store stays absent)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel import environment_scan_know_v1 as es

REPO_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON = Path("/tmp/pytest_venv/bin/python")


def _build_generic_env(tmp: Path, *, with_docs: bool = True) -> Path:
    (tmp / "run.sh").write_text("#!/bin/sh\necho fixture\n")
    (tmp / "notes.txt").write_text("A tiny unseen shell environment.\n")
    if with_docs:
        (tmp / "README.md").write_text(
            "# Fixture\n\nThis environment counts a verification as a success only\n"
            "when run.sh prints fixture and exits zero.\n")
        (tmp / "AGENTS.md").write_text(
            "# Agents\n\nRun run.sh to verify this environment.\n")
    return tmp


def _build_python_env(tmp: Path) -> Path:
    (tmp / "src" / "fixturepkg").mkdir(parents=True)
    (tmp / "tests").mkdir(exist_ok=True)
    (tmp / "src" / "fixturepkg" / "__init__.py").write_text(
        '"""Fixture package."""\n\ndef double(n):\n    return n * 2\n')
    (tmp / "tests" / "test_fixturepkg.py").write_text(
        "from fixturepkg import double\n\n"
        "def test_double():\n    assert double(2) == 4\n")
    (tmp / "pyproject.toml").write_text(
        '[project]\nname = "fixturepkg"\nversion = "0.1.0"\n'
        'requires-python = ">=3.9"\ndependencies = ["pytest>=7"]\n')
    (tmp / "README.md").write_text(
        "# Fixture package\n\nThis environment counts a verification as a success only\n"
        "when pytest reports zero failures and exits with a zero return code.\n")
    return tmp


class ScanAndKnowRefusalsTests(unittest.TestCase):

    def test_empty_goal_refuses_by_name(self):
        with tempfile.TemporaryDirectory() as td:
            out = es.scan_and_know(td, "")
            self.assertEqual(out["verdict"], "REFUSE__EMPTY_GOAL")
            self.assertEqual(out["questions"], [])

    def test_missing_directory_refuses_by_name(self):
        with tempfile.TemporaryDirectory() as td:
            out = es.scan_and_know(Path(td) / "does-not-exist", "run the tests")
            self.assertEqual(out["verdict"], "REFUSE__NOT_A_DIRECTORY")

    def test_empty_directory_refuses_by_name(self):
        with tempfile.TemporaryDirectory() as td:
            out = es.scan_and_know(td, "run the tests")
            self.assertEqual(out["verdict"], "REFUSE__NO_EVIDENCE")
            self.assertEqual(out["unknown"], [])

    def test_refusal_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as td:
            before = set(os.listdir(td))
            es.scan_and_know(td, "run the tests")
            self.assertEqual(before, set(os.listdir(td)))


class ScanAndKnowGenericTests(unittest.TestCase):

    def test_scan_records_kind_docs_and_never_persists(self):
        with tempfile.TemporaryDirectory() as td:
            root = _build_generic_env(Path(td))
            files_before = set(os.listdir(root))
            out = es.scan_and_know(root, "run the verification",
                                   env_kind="generic")
            self.assertEqual(out["schema"], "PROJECT_BRAIN_ENVIRONMENT_SCAN_KNOW_V1")
            self.assertEqual(out["authority"], "NONE__OBSERVED_HOST_EVIDENCE_AND_GATES")
            self.assertEqual(out["scanned"]["kind"], "unknown")
            self.assertIn("README.md", out["scanned"]["docs"])
            self.assertIn("AGENTS.md", out["scanned"]["docs"])
            self.assertGreaterEqual(out["scanned"]["file_count"], 3)
            # the flow never persists anything
            self.assertEqual(out["persist"].startswith("NONE"), True)
            self.assertEqual(files_before, set(os.listdir(root)))

    def test_contract_question_answered_via_local_guide(self):
        with tempfile.TemporaryDirectory() as td:
            root = _build_generic_env(Path(td))
            out = es.scan_and_know(root, "run the verification")
            contract = next(q for q in out["questions"]
                            if q["question"] == "what counts as success")
            self.assertEqual(contract["status"], "KNOWN_LOCAL_GUIDE", contract)
            self.assertEqual(contract["source"], "local_guide")

    def test_no_docs_never_fabricates_a_runner(self):
        with tempfile.TemporaryDirectory() as td:
            root = _build_generic_env(Path(td), with_docs=False)
            out = es.scan_and_know(root, "run the verification")
            runner = next(q for q in out["questions"]
                          if q["question"] == "what runs/checks it")
            self.assertEqual(runner["status"], "UNKNOWN", runner)
            # and success was NOT fabricated either
            success = next(q for q in out["questions"]
                           if q["question"] == "what counts as success")
            self.assertEqual(success["status"], "UNKNOWN", success)

    def test_scan_is_goal_directed_not_dump(self):
        with tempfile.TemporaryDirectory() as td:
            root = _build_generic_env(Path(td))
            out = es.scan_and_know(root, "run the verification")
            # the questions are derived from the goal, not a fixed menu of
            # every filesystem fact
            self.assertEqual(
                out["questions"][0]["question"], "what is this thing")
            self.assertIn("what runs/checks it", out["known"] + out["unknown"])


@unittest.skipUnless(VENV_PYTHON.exists(),
                     "pytest-capable child interpreter not built (expected venv: "
                     f"{VENV_PYTHON}); refusing to pretend")
class ScanAndKnowPythonBrokerTests(unittest.TestCase):

    def test_python_broker_path_cold_and_warm(self):
        with tempfile.TemporaryDirectory() as td:
            root = _build_python_env(Path(td))
            mem = Path(td) / "pa-memory.json"
            broker_mem = Path(td) / "broker-cache.json"

            def _run():
                snippet = (
                    "from canonical.swe_kernel import environment_scan_know_v1 as es\n"
                    "import json, sys\n"
                    "out = es.scan_and_know(sys.argv[1], 'run the tests',\n"
                    "                         memory_path_=sys.argv[2],\n"
                    "                         broker_memory_path_=sys.argv[3])\n"
                    "print(json.dumps(out))\n")
                env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
                done = subprocess.run(
                    [str(VENV_PYTHON), "-c", snippet,
                     str(root), str(mem), str(broker_mem)],
                    capture_output=True, text=True, env=env, timeout=120)
                self.assertEqual(done.returncode, 0, done.stderr)
                return json.loads(done.stdout)

            cold = _run()
            warm = _run()

            # cold: broker executes the suite, passes honestly
            self.assertEqual(cold["questions"][2]["status"], "KNOWN_BROKER", cold)
            self.assertEqual(cold["questions"][2]["detail"]["verdict"],
                             "ENVIRONMENT_BROKERED", cold)
            self.assertFalse(cold["questions"][2]["detail"]["from_memory"])
            self.assertTrue(cold["questions"][2]["detail"]["runner"]["ok"])
            self.assertEqual(cold["questions"][2]["detail"]["runner"]["reported_passed"], 1)

            # warm: cache re-verified by re-execution, not trusted blindly
            self.assertEqual(warm["questions"][2]["status"], "KNOWN_BROKER", warm)
            self.assertEqual(warm["questions"][2]["detail"]["verdict"],
                             "ENVIRONMENT_BROKERED_FROM_MEMORY", warm)
            self.assertTrue(warm["questions"][2]["detail"]["from_memory"])

            # the flow never persists anything of its own
            self.assertFalse(mem.exists(), "flow must never persist")
            self.assertFalse(broker_mem.exists() is False,
                             "broker cache is the broker's store, not the flow's")

    def test_python_env_without_pytest_honestly_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = _build_python_env(Path(td))
            pip_out = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True, text=True, timeout=60)
            if pip_out.returncode == 0:
                self.skipTest("pytest is available in this interpreter; refusal test not needed")
            out = es.scan_and_know(
                root, "run the tests",
                memory_path_=Path(td) / "mem.json",
                broker_memory_path_=Path(td) / "broker.json")
            runner = next(q for q in out["questions"]
                          if q["question"] == "what runs/checks it")
            self.assertEqual(runner["status"], "UNKNOWN", runner)
            # honestly named, never a fake PASS
            self.assertTrue("REFUSE" in str(runner["detail"].get("verdict", "")))


if __name__ == "__main__":
    unittest.main()
