"""The backlog split must separate the machine from the tree, and must not flatter either.

Why this test exists
--------------------
`AGENTS.md` (as of 2026-11-03) says the honest failure count "is the real backlog". Measured
today: 984 failures, of which 48 were a missing module on THIS machine and 642 were files that
were clean in the 2026-10-17 baseline. Three different kinds of thing, needing three different
kinds of work, all printing `F`.

`execution_guard/suite_backlog_split_v1.py` does that accounting. This test pins the accounting
itself, on a hand-built junit document where the right answer is known, so the tool cannot drift
into reporting a smaller backlog than the truth:

  * a missing module is ENVIRONMENT, never backlog, and it names the pip package;
  * an assertion failure in a file that also failed in the baseline is STANDING DEBT;
  * an assertion failure in a file that was clean in the baseline is a REGRESSION;
  * the tool never moves a real failure into the environment bucket to make the number look better.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "execution_guard/suite_backlog_split_v1.py"

JUNIT = """<?xml version="1.0"?>
<testsuites><testsuite name="pytest">
  <testcase classname="canonical.tests.test_clean" name="test_ok"/>
  <testcase classname="canonical.tests.test_clean" name="test_regressed">
    <failure message="AssertionError: 1 != 2">trace</failure>
  </testcase>
  <testcase classname="canonical.tests.test_old_debt" name="test_still_failing">
    <failure message="AssertionError: still wrong">trace</failure>
  </testcase>
  <testcase classname="canonical.tests.test_needs_cv2" name="test_a">
    <error message="ModuleNotFoundError: No module named 'cv2'">t</error>
  </testcase>
  <testcase classname="canonical.tests.test_needs_pil" name="test_b">
    <error message="ModuleNotFoundError: No module named 'PIL.Image'">t</error>
  </testcase>
  <testcase classname="canonical.tests.test_net" name="test_c">
    <error message="ConnectionError: Network is unreachable">t</error>
  </testcase>
</testsuite></testsuites>
"""

BASELINE = {
    "schema": "HONEST_SUITE_BASELINE_V1",
    "failing_cases": [
        {"file": "canonical/tests/test_old_debt.py", "test": "test_still_failing",
         "status": "failed", "bucket": "ASSERTION", "message_head": "AssertionError"},
    ],
}


def _run(tmp_path: Path) -> dict:
    junit = tmp_path / "j.xml"
    junit.write_text(JUNIT, encoding="utf-8")
    baseline = tmp_path / "b.json"
    baseline.write_text(json.dumps(BASELINE), encoding="utf-8")
    out = tmp_path / "split.json"
    subprocess.run(
        [sys.executable, str(TOOL), "--junit", str(junit), "--baseline", str(baseline),
         "--out", str(out), "--substrate-check", "SUBSTRATE_INCOMPLETE"],
        cwd=ROOT, check=True, capture_output=True, text=True, timeout=120,
    )
    return json.loads(out.read_text(encoding="utf-8"))


def test_a_missing_module_is_the_machine_and_is_not_counted_as_backlog(tmp_path):
    report = _run(tmp_path)
    assert report["environment_failures"] == 3          # cv2, PIL, network
    assert report["real_failures"] == 2                 # the two assertion failures
    # Never the reverse: a real failure must not be excused as an environment gap.
    assert report["environment_failures"] + report["real_failures"] == 5


def test_the_tool_names_the_package_to_install(tmp_path):
    report = _run(tmp_path)
    assert report["missing_modules"] == {"cv2": 1, "PIL": 1}
    # An absence must be actionable, not a red mark on a capability.
    assert "opencv-python-headless" in report["install_to_measure"]
    assert "pillow" in report["install_to_measure"]


def test_regression_and_standing_debt_are_different_lists(tmp_path):
    report = _run(tmp_path)
    assert report["regressions_vs_baseline"] == 1        # test_clean was clean on 17 Oct
    assert report["standing_debt_vs_baseline"] == 1      # test_old_debt was already failing
    regressed = [r["test"] for r in report["regression_detail"]]
    standing = [r["test"] for r in report["standing_detail"]]
    assert regressed == ["test_regressed"]
    assert standing == ["test_still_failing"]


def test_a_file_that_is_environment_blocked_is_named_never_measured(tmp_path):
    """42 files fail to COLLECT on the real tree and contribute zero cases to any count, so a
    'cases' total silently excludes them. They are named, not dropped."""
    report = _run(tmp_path)
    named = set(report["never_measured_files"])
    assert any("test_needs_cv2" in f for f in named)
    assert any("test_needs_pil" in f for f in named)
    # A file with a real failure is not 'never measured' -- it was measured and it failed.
    assert not any("test_clean" in f for f in named)


def test_the_report_carries_no_authority(tmp_path):
    report = _run(tmp_path)
    assert report["authority"].startswith("NONE")
    assert "RECEIPT" in report["authority"].upper()
