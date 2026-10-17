"""Prove that each verifier can say no.

A check that cannot fail is not a check. That was established early, when a
command wired to `exit 0` was excluded on principle rather than on
recognition -- and it keeps being established, because the same failure
returns in a new costume every few hours:

  * "Makefile:2: test" read as a report of two tests.
  * "typing: ok (4.65=setup...)" read as four tests having run.
  * a report file that exists, so the state diff fires, while containing
    no evidence that anything ran.
  * literals() raising, swallowed, and reporting a clean empty result.
  * a whole environment passing only because the previous run left a
    directory behind.

Every one of them was a check affirming when it should have stayed silent.
Not one was found by reasoning about the code; all were found by running
it. So the property is now tested directly, for every verifier, on an
input that is known to be wrong.

The rule is the one already applied to validators: a verifier with no
known-failing input is a verifier nobody has checked. Passing here does
not prove a verifier is correct -- nothing does -- but failing here proves
it is not one.

Adding a verifier means adding its counterexample here. A verifier added
without one is, by definition, untested.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_VERIFIER_FALSIFICATION_V1"

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _mod(name):
    try:
        from canonical.runtime import importlib  # type: ignore
    except Exception:
        pass
    return __import__(name)


def _cases() -> list[tuple[str, str, callable]]:
    """(verifier name, what the counterexample is, does it wrongly affirm)."""
    out: list[tuple[str, str, callable]] = []

    def add(name: str, wrong: str, fn: callable) -> None:
        out.append((name, wrong, fn))

    # --- reading a test run -------------------------------------------
    def tests_ran_forged() -> bool:
        import repair_v1 as R
        # A report that asserts success and shows nothing.
        ran, _n, _k = R.tests_ran("All tests passed\n")
        return ran

    def tests_ran_timing() -> bool:
        import repair_v1 as R
        # A type checker's timing summary, from a real repository.
        ran, _n, _k = R.tests_ran("typing: ok (4.65=setup[0.97]+cmd[1.35])")
        return ran

    def tests_ran_lineno() -> bool:
        import repair_v1 as R
        # The line number in a make error is not a count of tests.
        ran, _n, _k = R.tests_ran("make: *** [Makefile:2: test] Error 127")
        return ran

    def tests_ran_decoy() -> bool:
        import repair_v1 as R
        ran, _n, _k = R.tests_ran("no tests here")
        return ran

    add("repair_v1.tests_ran", "a report asserting success with no evidence",
        tests_ran_forged)
    add("repair_v1.tests_ran", "a tooling timing line, not a test count",
        tests_ran_timing)
    add("repair_v1.tests_ran", "a line number inside a make error",
        tests_ran_lineno)
    add("repair_v1.tests_ran", "the decoy that exits zero and runs nothing",
        tests_ran_decoy)

    # --- substituting a runner ----------------------------------------
    def runner_absent() -> bool:
        import repair_v1 as R
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "tests").mkdir()
            # Tests import pytest; this machine has no pytest.
            Path(tmp, "tests", "test_x.py").write_text("import pytest\n")
            cmd, _why = R._find_runner(tmp)
            if not cmd:
                return False
            # It may propose something, but only if it can actually run.
            ok, _w = R.command_runnable(cmd)
            return not ok

    add("repair_v1._find_runner",
        "proposing a runner whose module is not importable", runner_absent)

    def command_runnable_module() -> bool:
        import repair_v1 as R
        ok, _w = R.command_runnable(
            "python3 -m a_module_that_does_not_exist_anywhere -q")
        return ok

    add("repair_v1.command_runnable",
        "python3 exists, so the command is assumed to run",
        command_runnable_module)

    # --- attested state ------------------------------------------------
    def attested_indeterminate_is_not_pass() -> bool:
        import attested_state_v1 as A
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "out").mkdir()
            # The screen cannot be read here. That must be INDETERMINATE,
            # never UNCHANGED, and never a pass.
            r = A.attest("true", tmp, screen=True)
            return r["verdict"] == A.UNCHANGED

    def attested_forged_report() -> bool:
        import attested_state_v1 as A
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "out").mkdir()
            Path(tmp, "liar.py").write_text(
                "import pathlib\n"
                "pathlib.Path('out/report.txt').write_text('All tests passed\\n')\n")
            r = A.attest("python3 liar.py", tmp,
                         files=["out/report.txt"], trees=["out"],
                         check=A.tests_ran_in("out/report.txt"))
            return r["verdict"] == A.VERIFIED

    add("attested_state_v1.attest",
        "an unreadable channel reported as unchanged",
        attested_indeterminate_is_not_pass)
    add("attested_state_v1.attest",
        "a report that exists but evidences nothing",
        attested_forged_report)

    def sealed_receipt_reuse() -> bool:
        import attested_state_v1 as A
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "out").mkdir()
            r = A.attest("true", tmp, trees=["out"], spec={"goal": "one"})
            return A.matches(r, {"goal": "a completely different question"})

    add("attested_state_v1.matches",
        "evidence for one question answering another",
        sealed_receipt_reuse)

    # --- credit --------------------------------------------------------
    def credit_one_flip() -> bool:
        import credit_gates_v1 as G
        return G.credit({"a": 0}, {"a": 1})["credited"]

    def credit_no_change() -> bool:
        import credit_gates_v1 as G
        before = {"a": 0, "b": 1, "c": 0, "d": 1}
        return G.credit(before, dict(before))["credited"]

    add("credit_gates_v1.credit", "a single lucky flip",
        credit_one_flip)
    add("credit_gates_v1.credit", "nothing changed at all",
        credit_no_change)

    def e_process_never_invents() -> bool:
        import credit_gates_v1 as G
        # All noise, no effect: the e-process must stay below threshold.
        ep = G.e_process([1.0, -1.0, 1.0, -1.0, 1.0, -1.0])
        return ep["e_value"] >= 20.0

    add("credit_gates_v1.e_process", "six alternating flips read as evidence",
        e_process_never_invents)

    # --- validators ----------------------------------------------------
    def validator_that_cannot_fail() -> bool:
        import autonomous_v1 as A
        # Hardwired to succeed: an oracle whose job is to be able to say no.
        return A._can_fail("echo no tests here && exit 0")

    add("autonomous_v1._can_fail", "a command wired to exit zero",
        validator_that_cannot_fail)

    # --- properties ----------------------------------------------------
    def property_vacuous() -> bool:
        import property_v1 as P
        with tempfile.TemporaryDirectory() as tmp:
            # `true` certifies everything and therefore nothing.
            r = P.score("true", "rows: 3\ntotal: 42\n", workdir=tmp)
            return bool(r["admissible"])

    def property_rejects_truth() -> bool:
        import property_v1 as P
        with tempfile.TemporaryDirectory() as tmp:
            r = P.score("false", "rows: 3\n", workdir=tmp)
            return bool(r["admissible"])

    def property_accepts_empty() -> bool:
        import property_v1 as P
        with tempfile.TemporaryDirectory() as tmp:
            # Rejects a corruption marker, so it accepts the good artifact
            # and also accepts the empty one -- which nothing is about.
            # Disqualified outright, not merely scored down.
            r = P.score("! grep -q CORRUPTION artifact.txt",
                        "rows: 3\n", workdir=tmp)
            return bool(r["admissible"]) or not r["disqualified"]

    add("property_v1.score", "a property that certifies everything",
        property_vacuous)
    add("property_v1.score", "a property that rejects the known-good output",
        property_rejects_truth)
    add("property_v1.score", "a property accepting the empty artifact",
        property_accepts_empty)

    # --- grounding claims ---------------------------------------------
    def grounding_missing_file() -> bool:
        import grounding_v1 as G
        with tempfile.TemporaryDirectory() as tmp:
            r = G.check({"file": "nope.py", "contains": "def f"}, tmp)
            return r["verdict"] == G.GROUNDED

    def grounding_escape() -> bool:
        import grounding_v1 as G
        with tempfile.TemporaryDirectory() as tmp:
            r = G.check({"file": "../outside.py", "contains": "x"}, tmp)
            return r["verdict"] == G.GROUNDED

    def grounding_malformed() -> bool:
        import grounding_v1 as G
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.py").write_text("x = 1\n")
            # names a file but asserts nothing about it
            r = G.check({"file": "a.py"}, tmp)
            return r["verdict"] == G.GROUNDED

    def grounding_contradicted() -> bool:
        import grounding_v1 as G
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.py").write_text("def f():\n")
            r = G.check({"file": "a.py", "contains": "def g()"}, tmp)
            return r["verdict"] == G.GROUNDED

    def grounding_unverifiable_not_all_grounded() -> bool:
        import grounding_v1 as G
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.py").write_text("def f():\n")
            r = G.check_all([{"file": "a.py", "contains": "def f"},
                             {"file": "absent.py", "contains": "x"}], tmp)
            # Nine tenths grounded is not a grounded report.
            return bool(r["all_grounded"])

    add("grounding_v1.check", "a claim about a file that is not there",
        grounding_missing_file)
    add("grounding_v1.check", "a claim citing a path outside the project",
        grounding_escape)
    add("grounding_v1.check", "a claim naming a file but asserting nothing",
        grounding_malformed)
    add("grounding_v1.check", "a claim the file contradicts",
        grounding_contradicted)
    add("grounding_v1.check_all", "one uncheckable claim among grounded ones",
        grounding_unverifiable_not_all_grounded)

    # --- environment fit -------------------------------------------------
    def fit_rejects_empty_project() -> bool:
        import environment_fit_v1 as EF
        with tempfile.TemporaryDirectory() as tmp:
            cmd, _src, _why = EF.best_test_command(tmp)
            return cmd is not None

    add("environment_fit_v1.best_test_command",
        "an empty directory yielding a test command",
        fit_rejects_empty_project)

    return out


def run() -> tuple[int, list[tuple[str, str, bool]]]:
    """Return (number that wrongly affirmed, all results)."""
    results: list[tuple[str, str, bool]] = []
    bad = 0
    for name, wrong, fn in _cases():
        try:
            affirmed = bool(fn())
        except Exception:
            # Crashing is not affirming, but it is not a working verifier
            # either; report it so it cannot hide behind the exception.
            affirmed = True
        results.append((name, wrong, affirmed))
        bad += 1 if affirmed else 0
    return bad, results


def main() -> int:
    bad, results = run()
    print("%s\n" % SCHEMA)
    print("Each row feeds a verifier an input that is known to be wrong.")
    print("PASS means it said no. FAIL means it affirmed.\n")
    for name, wrong, affirmed in results:
        print("%-8s %-42s %s" % ("FAIL" if affirmed else "PASS", name, wrong))
    print("\n%d/%d verifiers proven able to fail"
          % (len(results) - bad, len(results)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
