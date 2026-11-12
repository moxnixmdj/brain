"""A PASS must mean the claim held, not that a process started.

Measured 2026-11-12 on this tree, before the change: `auditability_report_v1 --audit` ran 605
predicates and reported 495 PASS / 0 FAIL / 110 UNRUNNABLE. Of those 605, **595 declared no
expectation field at all**, and **52 exited non-zero** -- 37 at exit 1, 14 at exit 2, one
`npm run gate` at 254 -- while being recorded as PASS. Examples that were PASS and never ran:

    python /home/sprite/verify_r2_v33_terminal_projection.py   exit 2  can't open file
    python full_ocr_integration.py                             exit 2  can't open file
    python canonical/tests/test_astra_runtime_model_independence.py  exit 1

So the instrument whose stated purpose is "how much of verified can still be shown true" could
show almost nothing false: FAIL was reachable only through the 10 specs (1.7%) carrying an
expectation. That contradicts its own docstring -- "deliberately able to go red: a metric that
cannot decrease is not a metric" -- which is why this file exists.

Every test here is two-sided on purpose. A gate that fails everything is as useless as one that
passes everything, and an env-prefix fix that quietly turned every unrunnable claim into a PASS
would be the always-pass grader this repo has already documented once. So each new behaviour is
pinned next to the behaviour that must NOT change because of it.
"""
from __future__ import annotations

import json
import os
import pathlib
import stat
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.tools import auditability_report_v1 as A   # noqa: E402


def py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def write_record(root: pathlib.Path, verification: dict) -> None:
    (root / "canonical").mkdir(parents=True, exist_ok=True)
    (root / "canonical" / "record.json").write_text(json.dumps({
        "status": "VERIFIED_BOUND_CAPABILITY",
        "adapter_module": "a",
        "verification": verification,
    }), encoding="utf-8")


# ---------------------------------------------------------------------------
# THE FIX: an undeclared expectation is the strictest one
# ---------------------------------------------------------------------------
def test_a_command_that_exits_non_zero_with_no_expectation_FAILS():
    """The whole point. Exit 3 with nothing declared is not a verification that held."""
    result = A.run_predicate({"argv": py("raise SystemExit(3)")})
    assert result["verdict"] == "FAIL"
    assert result["reason"] == "EXIT 3 WITHOUT_EXPECTATION"
    assert result["exit"] == 3


def test_a_command_that_exits_zero_with_no_expectation_still_passes():
    """Two-sided: the gate must not redden honest runs, or it measures nothing."""
    result = A.run_predicate({"argv": py("pass")})
    assert result["verdict"] == "PASS"
    assert result["exit"] == 0
    assert result["expectations"] == []


def test_a_declared_expect_exit_keeps_a_non_zero_exit_a_pass():
    """A negative control stays expressible. This is the escape hatch that makes the gate
    honest rather than merely strict: a command that SHOULD fail must say so, because a
    negative control that does not declare itself is indistinguishable from a broken claim."""
    result = A.run_predicate({"argv": py("raise SystemExit(3)"), "expect_exit": 3})
    assert result["verdict"] == "PASS"
    assert result["exit"] == 3
    assert result["expectations"] == ["expect_exit"]


def test_a_wrong_exit_still_FAILS_when_one_was_declared():
    """The pre-existing gate must survive the new one."""
    result = A.run_predicate({"argv": py("raise SystemExit(3)"), "expect_exit": 0})
    assert result["verdict"] == "FAIL"
    assert "!=" in result["reason"]


def test_the_result_carries_the_exit_code_and_what_was_asserted():
    """Without these two fields a reader cannot audit the audit: 'PASS' alone does not say
    whether anything was checked."""
    result = A.run_predicate({"argv": py("print('x')"), "expect_stdout_contains": "x"})
    assert result["exit"] == 0
    assert result["expectations"] == ["expect_stdout_contains"]
    assert result["verdict"] == "PASS"


def test_a_stored_verification_that_exits_non_zero_reddens_the_report(tmp_path):
    """End to end: one receipt whose declared command fails must gate, and exit 1."""
    write_record(tmp_path, {"argv": py("raise SystemExit(3)")})
    report = A.audit(tmp_path, run=True)
    assert report["predicate_verdicts"]["FAIL"] == 1
    assert report["red"] is True
    assert A.main(["--root", str(tmp_path), "--audit", "--json"]) == 1


# ---------------------------------------------------------------------------
# the split that makes the headline number legible
# ---------------------------------------------------------------------------
def test_PASS_is_split_into_checked_and_only_started(tmp_path):
    """495 PASS read as 495 verified claims. It was 10 checked and 485 processes that
    launched. The report now says which is which."""
    (tmp_path / "canonical").mkdir(parents=True)
    (tmp_path / "canonical" / "checked.json").write_text(json.dumps({
        "status": "VERIFIED_BOUND_CAPABILITY", "adapter_module": "a",
        "verification": {"argv": py("print('promised')"),
                         "expect_stdout_contains": "promised"}}), encoding="utf-8")
    (tmp_path / "canonical" / "started.json").write_text(json.dumps({
        "status": "VERIFIED_BOUND_CAPABILITY", "adapter_module": "b",
        "verification": {"argv": py("pass")}}), encoding="utf-8")

    report = A.audit(tmp_path, run=True)
    assert report["predicate_verdicts"]["PASS"] == 2
    assert report["pass_checked"] == 1
    assert report["pass_started"] == 1
    assert report["predicates_declaring_an_expectation"] == 1


def test_the_split_sums_to_the_PASS_count(tmp_path):
    """A split that does not add up is a second, worse number."""
    write_record(tmp_path, {"argv": py("pass")})
    report = A.audit(tmp_path, run=True)
    assert report["pass_checked"] + report["pass_started"] == report["predicate_verdicts"]["PASS"]


# ---------------------------------------------------------------------------
# an env-prefixed command line is runnable; reading it as argv[0] was the defect
# ---------------------------------------------------------------------------
def test_an_env_prefixed_command_line_is_run_and_the_env_reaches_the_child():
    """30 runnable claims were reported BINARY_ABSENT because `PYTHONPATH=.` was read as a
    binary name. The assignment must reach the child, or the run is not the declared run."""
    probe = ("import os,sys; sys.exit(0 if os.environ.get('BRAIN_PROBE_ENV')=='42' else 1)")
    result = A.run_predicate({"argv": ["BRAIN_PROBE_ENV=42"] + py(probe)})
    assert result["verdict"] == "PASS"
    assert result["env_prefix"] == ["BRAIN_PROBE_ENV"]


def test_an_env_prefixed_command_with_the_wrong_value_FAILS():
    """Two-sided: peeling the prefix must not create a PASS factory. If the assignment is
    ignored rather than applied, this exits 1 and must be reported FAIL."""
    probe = ("import os,sys; sys.exit(0 if os.environ.get('BRAIN_PROBE_ENV')=='42' else 1)")
    result = A.run_predicate({"argv": ["BRAIN_PROBE_ENV=nope"] + py(probe)})
    assert result["verdict"] == "FAIL"
    assert result["reason"] == "EXIT 1 WITHOUT_EXPECTATION"


def test_several_env_prefixes_are_all_applied():
    probe = ("import os,sys;"
             "sys.exit(0 if os.environ.get('A')=='1' and os.environ.get('B')=='2' else 1)")
    result = A.run_predicate({"argv": ["A=1", "B=2"] + py(probe)})
    assert result["verdict"] == "PASS"
    assert result["env_prefix"] == ["A", "B"]


def test_an_env_assignment_with_no_command_after_it_is_unrunnable():
    """`PYTHONPATH=.` alone declares no program. Running it would test nothing."""
    result = A.run_predicate({"argv": ["PYTHONPATH=."]})
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("ENV_ASSIGNMENT_WITHOUT_COMMAND")


def test_an_absent_binary_is_still_unrunnable_after_the_env_fix():
    """Regression guard: parsing assignments must not swallow a real absence."""
    result = A.run_predicate({"argv": ["definitely-not-a-real-binary-9f2a1c"]})
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("BINARY_ABSENT")


def test_an_env_prefix_does_not_resurrect_an_absent_program():
    result = A.run_predicate({"argv": ["PYTHONPATH=.", "definitely-not-a-real-binary-9f2a1c"]})
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("BINARY_ABSENT")


# ---------------------------------------------------------------------------
# a command LINE stored as a list is not a command
# ---------------------------------------------------------------------------
def test_a_shell_operator_inside_an_argv_list_is_unrunnable_not_a_lying_FAIL():
    """`["jq","-r",".x","|","keys"]` hands `|` to jq as an argument and exits 2. Reporting
    that as FAIL would blame the claim for the harness misreading it, and reporting it as
    PASS is what happened before. `predicate_of` already refuses these in a string command
    for exactly this reason; a list is the same defect with the split done early."""
    result = A.run_predicate({"argv": ["jq", "-r", ".capabilities", "|", "keys"]})
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("SHELL_OPERATORS_IN_ARGV")


def test_a_legitimate_argument_is_not_mistaken_for_a_shell_operator():
    """Two-sided: `grep -e '|'` and `--filter=a|b` are arguments, not redirections. Only a
    token that IS an operator counts, or the fix would disable ordinary commands."""
    result = A.run_predicate({"argv": py("pass"), "expect_exit": 0})
    assert result["verdict"] == "PASS"
    keep = A.run_predicate({"argv": [sys.executable, "-c",
                                     "import sys; print(sys.argv[1])", "a|b"]})
    assert keep["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# naming the absence, because the causes have different fixes
# ---------------------------------------------------------------------------
def test_an_unfilled_template_is_not_reported_as_an_absent_binary():
    """`argv: ["${input.argv}"]` means no command was ever declared. That is a different
    fact from 'the tool is not installed', and only one of them is fixed by provisioning."""
    result = A.run_predicate({"argv": ["${input.argv}"]})
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("UNFILLED_TEMPLATE")
    assert "BINARY_ABSENT" not in result["reason"]


def test_a_program_in_the_tree_that_is_not_executable_is_named_not_borrowed(tmp_path):
    """A receipt that declares `script.py` directly, where the tree holds it at mode 644,
    cannot be re-run as declared. Running `python3 script.py` instead would test a DIFFERENT
    command than the one claimed -- a borrowed PASS. Named instead."""
    script = tmp_path / "declared.py"
    script.write_text("print('hi')\n", encoding="utf-8")
    script.chmod(0o644)

    result = A.run_predicate({"argv": ["declared.py"]}, cwd=tmp_path)
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("DECLARED_PROGRAM_NOT_EXECUTABLE")
    assert not str(result.get("reason")).startswith("PermissionError")


def test_the_same_program_becomes_runnable_when_the_tree_makes_it_executable(tmp_path):
    """Two-sided, and the reason the previous test is not just a shrug: chmod +x is the fix,
    and after it the declared command really does run and really can fail."""
    script = tmp_path / "declared.py"
    script.write_text("#!/usr/bin/env python3\nraise SystemExit(3)\n", encoding="utf-8")
    script.chmod(0o644 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    result = A.run_predicate({"argv": ["./declared.py"]}, cwd=tmp_path)
    assert result["verdict"] == "FAIL"
    assert result["exit"] == 3


def test_a_path_shaped_absence_is_distinguished_from_an_absent_tool():
    """/home/sprite/... and .venv/bin/python are claims about a machine that is not here;
    `qrencode` is a claim about a tool nobody installed. Different fixes, different names."""
    gone = A.run_predicate({"argv": ["/home/sprite/verify_r2_v33_terminal_projection.py"]})
    assert gone["verdict"] == "UNRUNNABLE"
    assert gone["reason"].startswith("DECLARED_PROGRAM_ABSENT")

    tool = A.run_predicate({"argv": ["qrencode", "--version"]})
    assert tool["verdict"] == "UNRUNNABLE"
    assert tool["reason"].startswith("BINARY_ABSENT")


def test_a_bare_filename_is_resolved_through_PATH_not_the_working_directory(tmp_path):
    """execvp -- and a shell -- resolve a bare name via PATH, never via cwd. So the declared
    command genuinely does not run even though the file is sitting right there. Rewriting it
    to `./x` would invent a command nobody declared."""
    script = tmp_path / "ledger.py"
    script.write_text("print('hi')\n", encoding="utf-8")
    script.chmod(0o755)

    result = A.run_predicate({"argv": ["ledger.py"]}, cwd=tmp_path)
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("BARE_FILENAME_NOT_ON_PATH")


# ---------------------------------------------------------------------------
# the guards that must keep holding
# ---------------------------------------------------------------------------
def test_a_shell_script_prefix_is_still_unrunnable_never_a_pass():
    """Pinned elsewhere too; repeated here because the env-prefix parser sits next to it and
    must not become a way through. `set -euo pipefail cmd` run as argv[0] always succeeds."""
    result = A.run_predicate({"argv": ["set", "-euo", "pipefail", "echo", "hi"]})
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"].startswith("SHELL_SCRIPT_PREFIX")


def test_an_empty_argv_is_a_FAIL_not_an_absence():
    result = A.run_predicate({"argv": []})
    assert result["verdict"] == "FAIL"
    assert result["reason"] == "EMPTY_ARGV"


def test_a_declared_stdout_expectation_is_still_enforced():
    result = A.run_predicate({"argv": py("print('actual')"),
                              "expect_stdout_contains": "promised"})
    assert result["verdict"] == "FAIL"
    assert result["expectations"] == ["expect_stdout_contains"]


def test_the_child_environment_is_not_leaked_into_the_audit_process():
    """Applying a prefix must not mutate the harness, or one receipt's PYTHONPATH would
    silently become the next receipt's."""
    before = dict(os.environ)
    A.run_predicate({"argv": ["BRAIN_PROBE_LEAK=1"] + py("pass")})
    assert "BRAIN_PROBE_LEAK" not in os.environ
    assert dict(os.environ) == before


def test_a_timeout_is_named_with_its_budget_not_as_a_crash():
    """19 of 605 predicates exceed the 30s budget once env-prefixed commands actually run,
    two of them invoking the whole test suite. 'Unmeasurable within the budget' is a fact
    about this instrument; a bare exception class name reads as a crash and hides that the
    fix is the budget, not the claim."""
    result = A.run_predicate({"argv": [sys.executable, "-c", "import time; time.sleep(5)"]},
                             timeout=0.25)
    assert result["verdict"] == "UNRUNNABLE"
    assert result["reason"] == "TIMEOUT_BUDGET_0.25s"
    assert "TimeoutExpired" not in result["reason"]
