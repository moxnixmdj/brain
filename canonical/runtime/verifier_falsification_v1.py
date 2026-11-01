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

import importlib
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_VERIFIER_FALSIFICATION_V1"

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# And the repository root, so a case may reach `canonical.*` when this module is run
# as a script rather than imported as a package. Measured 2026-11-01: without it, 25
# cases crashed with `No module named 'canonical'` when run directly and passed when
# run through the sweep -- the same suite reporting two different truths depending on
# how it was invoked.
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _mod(name):
    try:
        from canonical.runtime import importlib  # type: ignore
    except Exception:
        pass
    return __import__(name)


def _isolated_experience_state(path: str) -> str:
    """Give an experience case a genuinely empty state file.

    `experience_v1` persists to disk, and `_STATE_CACHE.clear()` only drops the
    in-memory copy. Without removing the file, every run of this suite resumes
    from the previous run's counts, so a case written to prove that "ONE
    observation is not evidence" is re-run as the 41st observation and flips to
    a false FAIL. That made the suite non-idempotent: its score drifted with
    how many times it had been run (94/96 on a clean tree, 93/96 after the
    state had accumulated) rather than with the code under test.
    """
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass
    return path


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

    # --- executing a program ------------------------------------------
    def execute_no_effect() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            # Exits zero and changes nothing: the oldest lie there is.
            r = X.run("print('done')", tmp, timeout=30)
            return r["verdict"] == X.SUCCESS

    def execute_failure() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            r = X.run("raise SystemExit(1)", tmp, timeout=30)
            return r["verdict"] == X.SUCCESS

    def execute_ungrounded_claim() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            # Writes a file, but not the one the claim says it proves.
            r = X.run("open('a.txt','w').write('x')", tmp, timeout=30,
                      claim={"file": "b.txt", "contains": "x"})
            return r["verdict"] == X.SUCCESS

    add("execute_v1.run", "a program that exits zero and changes nothing",
        execute_no_effect)
    add("execute_v1.run", "a program that exits non-zero",
        execute_failure)
    add("execute_v1.run", "a program whose claimed result is not grounded",
        execute_ungrounded_claim)

    # --- the minimal loop ---------------------------------------------
    def solve_is_bounded() -> bool:
        import solve_v1 as S
        with tempfile.TemporaryDirectory() as tmp:
            def never(goal, seeing):
                return "print('again')"      # never judges itself done
            r = S.solve("never finishes", tmp, never, steps=3)
            return r["verdict"] == S.DONE or r["steps"] > 3

    def solve_missing_root() -> bool:
        import solve_v1 as S
        def m(goal, seeing):
            return None
        r = S.solve("anything", "/tmp/nope_does_not_exist_xyz", m)
        # A directory that was never there must not be reported finished.
        return r["verdict"] == S.DONE

    def observe_sees_a_change() -> bool:
        import solve_v1 as S
        with tempfile.TemporaryDirectory() as tmp:
            before = S.observe(tmp)
            Path(tmp, "a.txt").write_text("x")
            after = S.observe(tmp, before=before["files"])
            return "a.txt" not in after["changed"]

    add("solve_v1.solve", "a model that never judges itself done",
        solve_is_bounded)
    add("solve_v1.solve", "a root that does not exist", solve_missing_root)
    add("solve_v1.observe", "a tree that changed without it noticing",
        observe_sees_a_change)

    # --- the flywheel is consulted before acting -----------------------
    def solve_primes_before_first_action() -> bool:
        import solve_v1 as S
        import flywheel_v1 as F
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fw.json")
            # Force a credited cell with a procedure, then ask whether
            # the loop hands it over on step 1 rather than after a
            # failure -- asked too late the benefit measured 0%.
            for _ in range(10):
                F.record("file access", "no such file", True, path=path)
            F.teach(F.cell_of("file access", "no such file"),
                    "the fix", path=path)
            # A TEST THAT COULD ONLY EVER FAIL IS NOT A TEST EITHER.
            #
            # `flywheel_v1.primers` is declared
            #     def primers(alpha=DEFAULT_ALPHA, path: str = DEFAULT_STATE)
            # and Python binds default arguments ONCE, at definition. So
            # patching `F.DEFAULT_STATE` cannot reach it -- the mock was
            # inert, `primers()` always read the real store, and this row
            # reported FAIL for a property the machine actually has. It
            # has never once verified the thing it names.
            #
            # Patch what primers() actually calls, and the property is
            # visible: solve_v1 hands the primer over at step 1.
            import unittest.mock as mock
            real_cells = F.cells
            with mock.patch.object(F, "cells",
                                   lambda **kw: real_cells(path=path)):
                seen = []
                def model(goal, seeing):
                    if seeing["step"] == 1:
                        seen.append(seeing.get("learned"))
                    return None
                S.solve("g", tmp, model, steps=1)
            return not any(
                s and (s.get("primers") or []) for s in seen)

    add("solve_v1.solve", "the flywheel consulted only after a failure",
        solve_primes_before_first_action)

    # --- the model socket ----------------------------------------------
    def solve_silently_acts_without_a_model() -> bool:
        import solve_v1 as S
        import model_v1 as M
        with tempfile.TemporaryDirectory() as tmp:
            saved = os.environ.get(M.ENV_VAR)
            os.environ.pop(M.ENV_VAR, None)
            try:
                r = S.solve("anything at all", tmp)
                # With nothing plugged in, an empty trace and a verdict
                # of DONE would be indistinguishable from a model that
                # judged the goal already met. It must say NO_MODEL.
                return r["verdict"] == S.DONE or r["verdict"] not in (
                    S.NO_MODEL, S.BOUNDED)
            finally:
                if saved is not None:
                    os.environ[M.ENV_VAR] = saved

    def model_status_claims_ready_unbound() -> bool:
        import model_v1 as M
        saved = os.environ.get(M.ENV_VAR)
        os.environ.pop(M.ENV_VAR, None)
        try:
            return bool(M.status()["ready"])
        finally:
            if saved is not None:
                os.environ[M.ENV_VAR] = saved

    add("solve_v1.solve", "the loop acting with no model bound",
        solve_silently_acts_without_a_model)
    add("model_v1.status", "reporting ready when nothing is bound",
        model_status_claims_ready_unbound)

    # --- capability is declared, not assumed ---------------------------
    def confine_network_default_closed() -> bool:
        import confine_v1 as C
        if not C.available():
            return True
        with tempfile.TemporaryDirectory() as tmp:
            r = C.run("import socket\n"
                      "socket.create_connection(('github.com',443),timeout=4)\n"
                      "print('REACHED')", tmp, timeout=90)
            return "REACHED" in (r.get("output") or "")

    def confine_network_when_declared() -> bool:
        import confine_v1 as C
        if not C.available():
            return True
        with tempfile.TemporaryDirectory() as tmp:
            r = C.run("import socket\n"
                      "socket.create_connection(('github.com',443),timeout=4)\n"
                      "print('REACHED')", tmp, timeout=90, network=True)
            # A sandbox that prevents the work is amputation, not safety.
            return "REACHED" not in (r.get("output") or "")

    add("confine_v1.run", "network reachable without being declared",
        confine_network_default_closed)
    add("confine_v1.run", "network unreachable even when declared",
        confine_network_when_declared)

    # --- the loop itself is confined -----------------------------------
    def solve_act_escapes() -> bool:
        import solve_v1 as S
        try:
            import confine_v1 as C
        except Exception:
            return True
        if not C.available():
            return True
        with tempfile.TemporaryDirectory() as tmp:
            # The MAIN loop must be confined, not merely the module that
            # knows how. A guarantee covering every path except the one
            # that actually runs is not a guarantee.
            r = S.act(tmp, "open('/usr/brain_solve_evil.txt','w').write('x')",
                      timeout=60)
            return Path("/usr/brain_solve_evil.txt").exists()

    def solve_act_hides_confinement() -> bool:
        import solve_v1 as S
        with tempfile.TemporaryDirectory() as tmp:
            r = S.act(tmp, "print('x')", timeout=60)
            # Falling back is allowed; falling back SILENTLY is not. The
            # caller must be able to tell a sandboxed run from a bare one.
            return "confined" not in r

    add("solve_v1.act", "the main loop running unconfined", solve_act_escapes)
    add("solve_v1.act", "a fallback that does not say it fell back",
        solve_act_hides_confinement)

    # --- the flywheel --------------------------------------------------
    def flywheel_withholds_uncredited() -> bool:
        import flywheel_v1 as F
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fw.json")
            cell = F.cell_of("writing a report", "disk full")
            F.teach(cell, "retry after clearing space", path=path)
            # Taught but never evidenced: it must not be handed back.
            return F.status(cell, path=path)["procedure"] is not None

    def flywheel_credits_a_coin_flip() -> bool:
        import flywheel_v1 as F
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fw.json")
            cell = F.cell_of("parsing a page", "bad selector")
            for i in range(40):
                F.record("parsing a page", "bad selector",
                         succeeded=(i % 2 == 0), path=path)
            # A correction that works half the time must never earn
            # credit, however many times it is tried.
            return F.status(cell, path=path)["credited"]

    def flywheel_splits_cells() -> bool:
        import flywheel_v1 as F
        # The bug that would have killed it: keyed on the object rather
        # than the operation, every task gets a cell of its own and
        # nothing ever accumulates.
        return F.cell_of("reading a log file", "No such file") != \
               F.cell_of("reading a config", "No such file")

    def flywheel_credits_consistent_harm() -> bool:
        import flywheel_v1 as F
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fw.json")
            for _ in range(12):
                F.record("file access", "no such file",
                         succeeded=False, path=path)
            # The e-process tests against ANY consistent deviation, so
            # failing every time also clears the magnitude threshold --
            # e=107 here against a threshold of 20. Magnitude alone
            # would promote the one thing that never works.
            return F.status(F.cell_of("file access", "no such file"),
                            path=path)["credited"]

    add("flywheel_v1.status", "a correction that fails every single time",
        flywheel_credits_consistent_harm)
    add("flywheel_v1.status", "a procedure taught but never evidenced",
        flywheel_withholds_uncredited)
    add("flywheel_v1.status", "a correction that only works half the time",
        flywheel_credits_a_coin_flip)
    add("flywheel_v1.cell_of", "cells keyed on the object rather than the "
        "operation", flywheel_splits_cells)

    # --- confinement ---------------------------------------------------
    def confine_blocks_escape() -> bool:
        import confine_v1 as C
        if not C.available():
            return True          # nothing to falsify where it cannot run
        with tempfile.TemporaryDirectory() as tmp:
            r = C.run("open('/usr/brain_evil.txt','w').write('x')",
                      tmp, timeout=60)
            # Either the write is refused, or it must not exist after.
            return r["verdict"] == "OK" and Path("/usr/brain_evil.txt").exists()

    def confine_allows_legitimate_work() -> bool:
        import confine_v1 as C
        if not C.available():
            return True
        with tempfile.TemporaryDirectory() as tmp:
            r = C.run("open('legit.txt','w').write('x')", tmp, timeout=60)
            # Over-blocking is the failure a sandbox is most tempted by:
            # refusing everything reads as safe and does no work at all.
            return not Path(tmp, "legit.txt").exists()

    def confine_blocks_network() -> bool:
        import confine_v1 as C
        if not C.available():
            return True
        with tempfile.TemporaryDirectory() as tmp:
            r = C.run("import socket\n"
                      "socket.create_connection(('github.com',443),timeout=3)\n"
                      "print('REACHED')", tmp, timeout=90)
            return "REACHED" in (r["output"] or "")

    def confine_hides_user_data() -> bool:
        import confine_v1 as C
        if not C.available():
            return True
        with tempfile.TemporaryDirectory() as tmp:
            r = C.run("import os\n"
                      "print('HOME' if os.path.exists('/home') else 'no /home')\n"
                      "print('ETC' if os.path.exists('/etc') else 'no /etc')",
                      tmp, timeout=60)
            out = r["output"] or ""
            return "HOME" in out or "ETC" in out

    def confine_caps_resources() -> bool:
        import confine_v1 as C
        if not C.available():
            return True
        with tempfile.TemporaryDirectory() as tmp:
            # Must not run forever: an uncapped bomb takes the machine.
            r = C.run("x=[]\nwhile True: x.append(' '*10**7)",
                      tmp, timeout=45)
            return r["verdict"] == "INDETERMINATE"   # i.e. it never came back

    add("confine_v1.run", "a program reaching the network",
        confine_blocks_network)
    add("confine_v1.run", "a program reading user data outside the project",
        confine_hides_user_data)
    add("confine_v1.run", "a program that never stops consuming memory",
        confine_caps_resources)
    add("confine_v1.run", "a program writing outside the project",
        confine_blocks_escape)
    add("confine_v1.run", "confinement so strict it blocks legitimate work",
        confine_allows_legitimate_work)

    # --- did it do it RIGHT -------------------------------------------
    def wrong_result() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "nums.txt").write_text("1\n2\n3\n4\n")
            Path(tmp, "out").mkdir()
            # Asked for a mean, writes a sum. Runs clean, changes the
            # tree, satisfies its claim -- and is wrong.
            prog = ("vals=[int(l) for l in open('nums.txt') if l.strip()]\n"
                    "open('out/r.txt','w').write(str(sum(vals)))")
            chk = ("from pathlib import Path\n"
                   "vals=[int(l) for l in open('nums.txt') if l.strip()]\n"
                   "got=float(Path('out/r.txt').read_text().strip())\n"
                   "raise SystemExit(0 if abs(got-sum(vals)/len(vals))<1e-9 else 1)")
            r = X.run(prog, tmp, check=chk)
            return r["verdict"] == X.SUCCESS

    def vacuous_check() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "out").mkdir()
            prog = "open('out/a.txt','w').write('x')"
            r = X.run(prog, tmp, check="raise SystemExit(0)")
            return r["verdict"] == X.SUCCESS

    add("execute_v1.run", "a program that runs and changes the tree but "
        "produces the wrong value", wrong_result)
    add("execute_v1.run", "a check that accepts a corrupted result",
        vacuous_check)

    # --- correction: the account handed back to the author ------------
    def why_reports_the_cause() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            # Writes the file, THEN crashes. The claim reads
            # CONTRADICTED; the cause is the missing input. Reporting the
            # consequence first hid the cause and correction was
            # abandoned, so this pins the order.
            r = X.run("open('out.txt','w').write(open('nope.csv').read())",
                      tmp, timeout=30,
                      claim={"file": "out.txt", "contains": "x"})
            return "No such file" not in X._why(r)

    def iterate_is_bounded() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            def stuck(goal, obs):
                return "print('trying')"
            r = X.iterate("never lands", tmp, stuck, attempts=3)
            return r["verdict"] == X.SUCCESS or len(r["history"]) > 3

    def iterate_stopped_when_grounded() -> bool:
        import execute_v1 as X
        with tempfile.TemporaryDirectory() as tmp:
            def good(goal, obs):
                return None if obs else "open('a.txt','w').write('x')"
            r = X.iterate("make a file", tmp, good, attempts=5,
                          claim={"file": "a.txt", "contains": "x"})
            # Stopping the moment it lands is the point; overshooting
            # would mean the verdict is not what ends the loop.
            return r["verdict"] != X.SUCCESS or r["attempts_used"] != 1

    add("execute_v1._why", "a crashed run hiding its exception behind a "
        "contradicted claim", why_reports_the_cause)
    add("execute_v1.iterate", "an author that never lands", iterate_is_bounded)
    add("execute_v1.iterate", "a loop that keeps going after it lands",
        iterate_stopped_when_grounded)

    # --- routing a question -------------------------------------------
    def is_question_url() -> bool:
        import autonomous_v1 as A
        # Asks about somewhere else; answering it from local files would
        # answer a question that was never asked.
        return A._is_question(
            "what does the page at https://github.com/x/y say this is")

    def is_question_empty() -> bool:
        import autonomous_v1 as A
        return A._is_question("")

    add("autonomous_v1._is_question", "a question naming a remote url",
        is_question_url)
    add("autonomous_v1._is_question", "an empty goal", is_question_empty)

    # --- the verdict grounds itself ------------------------------------
    def verdict_grounding_missing() -> bool:
        import autonomous_v1 as A
        with tempfile.TemporaryDirectory() as tmp:
            # An artifact that was there a moment ago and is gone now is
            # not a completed goal; it is work that was undone.
            r = A._ground(tmp, ["out/report.txt"])
            return bool(r.get("all_grounded"))

    add("autonomous_v1._ground", "a verdict resting on an artifact that is gone",
        verdict_grounding_missing)

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

    # --- perceiving the world (world_probe_v1) -------------------------
    # A capability behind a precondition nobody provides is dead code. The
    # probe revives it by LOOKING. That only stays honest if the probe can
    # also say no: an effect it cannot decide must come back NOT
    # established, because planning on an invented fact produces work no
    # verifier objected to.

    def probe_undecidable_effect() -> bool:
        import world_probe_v1 as W
        # An effect this module has no sensor for. It must not affirm it.
        d = W.probe_effect("chart.question.legend_linear_intersection.available")
        return bool(d["true"])

    def probe_empty_world() -> bool:
        import world_probe_v1 as W
        # A root with nothing in it. "There is a pdf here" must be false.
        import tempfile as _tf
        with _tf.TemporaryDirectory() as tmp:
            d = W.probe_effect("pdf.file.available", goal="", goal_paths=(),
                               root=_tf.__name__ and __import__("pathlib").Path(tmp))
        return bool(d["true"])

    def probe_runtime_absent() -> bool:
        import world_probe_v1 as W
        # An executable that has never existed on any machine.
        W._RUNTIME_KINDS["definitely_not_a_real_binary_xyz"] = "definitely_not_a_real_binary_xyz"
        try:
            d = W.probe_effect("definitely_not_a_real_binary_xyz.runtime.available")
        finally:
            W._RUNTIME_KINDS.pop("definitely_not_a_real_binary_xyz", None)
        return bool(d["true"])

    add("world_probe_v1.probe_effect", "an effect it has no sensor for",
        probe_undecidable_effect)
    add("world_probe_v1.probe_effect", "a file kind absent from an empty world",
        probe_empty_world)
    add("world_probe_v1.probe_effect", "an executable that does not exist",
        probe_runtime_absent)

    # --- completing inputs (world_binding_v1) --------------------------
    # Filling arguments the goal only implies is only safe while the module
    # still refuses the ones nothing justifies. Inventing an input is an
    # unverifiable act.

    def binding_invents_unjustified_input() -> bool:
        import world_binding_v1 as WB
        # A capability needing a glob the goal never states. It must be
        # reported missing, not filled with a plausible-looking guess.
        entry = {
            "capability_id": "falsify.needs.glob",
            "action_template": {"args": {"pattern": "${input.pattern}",
                                         "source_root": "${input.source_root}"}},
        }
        r = WB.complete_inputs("audit the python source", __import__("pathlib").Path("/tmp"),
                               entry, compiler=None, goal_paths=[])
        return "pattern" not in r["missing"]

    def binding_synthesised_output_is_stable() -> bool:
        import world_binding_v1 as WB
        # Same capability, same call -> same destination. If it wanders,
        # nothing downstream can be reproduced or content-addressed.
        a = WB.synthesize_output_path("some.capability", "output_path")
        b = WB.synthesize_output_path("some.capability", "output_path")
        return a != b

    add("world_binding_v1.complete_inputs", "a placeholder nothing can justify",
        binding_invents_unjustified_input)
    add("world_binding_v1.synthesize_output_path", "a destination that is not deterministic",
        binding_synthesised_output_is_stable)

    # --- the joined loop (grounded_action_v1) --------------------------
    # The loop must refuse when nothing fits, and an unrecognised `expect`
    # is a FAILED check, never a passed one: an unknown proof proves nothing.

    def unknown_expect_is_not_a_pass() -> bool:
        import grounded_action_v1 as G
        ok, _note = G._check_expect(
            {"field": "verified", "type": "totally_made_up_check"},
            {"verified": True})
        return bool(ok)

    def loop_invents_success_on_impossible_goal() -> bool:
        import grounded_action_v1 as G
        r = G.act("send an email to the team and book a flight to mars")
        return bool(r.get("ok"))

    add("grounded_action_v1._check_expect", "an expect type nobody implemented",
        unknown_expect_is_not_a_pass)
    add("grounded_action_v1.act", "a goal no capability can serve",
        loop_invents_success_on_impossible_goal)

    # --- accumulating experience (experience_v1) ------------------------
    # Memory is the most dangerous component here, because a wrong memory
    # looks exactly like a right one from the inside. These are the ways
    # it can lie, each caught by running it and looking at what came back.

    def experience_credits_consistent_failure() -> bool:
        import experience_v1 as E
        # EIGHT STRAIGHT FAILURES SCORE e=31.6, PAST A THRESHOLD OF 20.
        # Magnitude alone would promote this as a trusted fix -- and then
        # confidently reuse the thing that never works. The sign is the
        # gate; a "correction" that always fails is not one.
        E.DEFAULT_STATE = _isolated_experience_state("canonical/runtime/state/_falsify_exp_a.json")
        E._STATE_CACHE.clear()
        st = None
        for _ in range(8):
            st = E.record("falsify.cap", "always_fails", False, structural=False)
        return bool(st["credited"])

    def experience_credits_a_single_lucky_success() -> bool:
        import experience_v1 as E
        # One observation is not evidence. A plain mean would call this
        # 100%; the anytime-valid gate must not.
        E.DEFAULT_STATE = _isolated_experience_state("canonical/runtime/state/_falsify_exp_b.json")
        E._STATE_CACHE.clear()
        st = E.record("falsify.cap", "once_worked", True, structural=False)
        return bool(st["credited"])

    def experience_generalises_a_goal_fact_into_a_machine_fact() -> bool:
        import experience_v1 as E
        # "This capability cannot take a .pdf" is a fact about ONE GOAL.
        # Promoting it to "never use this capability again" turned one PDF
        # into a machine that could never do OCR on an image. Memory must
        # not outlive the context that made it true.
        E.DEFAULT_STATE = _isolated_experience_state("canonical/runtime/state/_falsify_exp_c.json")
        E._STATE_CACHE.clear()
        E.observe("extract text from some.pdf", {
            "rejected": [{"capability_id": "falsify.ocr",
                          "why": "INPUT_KIND_CONTRADICTS_GOAL_FILE"}],
            "capability_id": None, "verified": False, "error": ""})
        return bool(E.is_suppressed("falsify.ocr"))

    def experience_overrides_verification() -> bool:
        import experience_v1 as E
        import grounded_action_v1 as G
        # Memory removes the NEED TO ASK, never the need to CHECK. Teach it
        # that a capability which demonstrably cannot run here is the
        # answer, and it must still report failure rather than success.
        # This case must fail for a reason that stays true. It first used
        # the PDF capability, then pypdf was installed and the goal began
        # succeeding -- at which point the test stopped testing anything,
        # because it could no longer tell "memory skipped verification"
        # from "the work genuinely verified". OCR is used instead:
        # tesseract is a system binary, not a package, so it cannot be
        # installed away. A test that stops discriminating is decoration.
        E.DEFAULT_STATE = _isolated_experience_state("canonical/runtime/state/_falsify_exp_d.json")
        E._STATE_CACHE.clear()
        goal = "run ocr on canonical/astra/canary_frames/006-c-final.png"
        E.teach_resolution(goal, "image.extract.ocr.tesseract")
        r = G.act(goal)
        return bool(r.get("ok"))

    add("experience_v1.record", "eight straight failures presented as a fix",
        experience_credits_consistent_failure)
    add("experience_v1.record", "one lucky success presented as proof",
        experience_credits_a_single_lucky_success)
    add("experience_v1.observe", "a goal-relative fact promoted to a machine fact",
        experience_generalises_a_goal_fact_into_a_machine_fact)
    add("experience_v1.recall_resolution", "a remembered answer that skips verification",
        experience_overrides_verification)

    # --- rendering bound values into the template ------------------------
    # THE BUG THIS GUARDS SILENTLY DISABLED MOST OF THE REGISTRY.
    #
    # `{"args": {"path": "${input.docx_path}"}}` -- the adapter reads `path`,
    # the placeholder is `docx_path`. Handing over a dict keyed by
    # placeholder name gave the adapter `path=None`, and every capability
    # built that way died on a path check that looked like an environment
    # problem and was actually this one. python.source.audit.ast was the
    # only thing that worked, purely because its names happened to match.

    def render_uses_placeholder_name_not_arg_key() -> bool:
        import world_binding_v1 as WB
        entry = {"action_template": {"args": {"path": "${input.docx_path}"}}}
        out = WB.render_args(entry, {"docx_path": "a/b.docx"})
        return out.get("path") != "a/b.docx"

    def render_leaves_a_placeholder_unexpanded() -> bool:
        import world_binding_v1 as WB
        entry = {"action_template": {"args": {"path": "${input.docx_path}"}}}
        out = WB.render_args(entry, {"docx_path": "a/b.docx"})
        return "${" in str(out.get("path") or "")

    def render_passes_through_an_unbound_argument() -> bool:
        import world_binding_v1 as WB
        # A missing argument is a fact to report, not a None to invent.
        entry = {"action_template": {"args": {"path": "${input.docx_path}"}}}
        try:
            WB.render_args(entry, {})
        except KeyError:
            return False
        return True

    add("world_binding_v1.render_args", "the placeholder name where the arg key belongs",
        render_uses_placeholder_name_not_arg_key)
    add("world_binding_v1.render_args", "a ${input.x} left unexpanded in the output",
        render_leaves_a_placeholder_unexpanded)
    add("world_binding_v1.render_args", "an unbound argument passed through as None",
        render_passes_through_an_unbound_argument)

    # --- synthesising destinations --------------------------------------
    # A destination's name is determined by the capability, never by the
    # goal. Two ways this went wrong, both silent:
    #
    #   * `sqlite.table.create_from_json_records` emits SQLITE, but "json"
    #     sits in its name first, so a naive scan wrote `.json` from a
    #     sqlite writer. Tokens after `from_` name what goes IN.
    #   * the capability id was never threaded through, so every path came
    #     out as `brain_out____<hash>.json` -- empty slug, wrong extension,
    #     for every capability in the registry at once.

    def output_extension_taken_from_the_input_format() -> bool:
        import world_binding_v1 as WB
        p = WB.synthesize_output_path("sqlite.table.create_from_json_records",
                                      "output_path")
        return not p.endswith(".sqlite")

    def synthesised_output_ignores_which_capability() -> bool:
        import world_binding_v1 as WB
        a = WB.synthesize_output_path("sqlite.table.create_from_json_records",
                                      "output_path")
        b = WB.synthesize_output_path("xlsx.table.create_from_json_records",
                                      "output_path")
        return a == b

    add("world_binding_v1.synthesize_output_path",
        "an input format naming the output extension",
        output_extension_taken_from_the_input_format)
    add("world_binding_v1.synthesize_output_path",
        "a destination that ignores which capability needs it",
        synthesised_output_ignores_which_capability)

    # --- escalating to the 5,221-function inventory ----------------------
    # The inventory is not verified, and its own evidence file says so:
    # "NONE__SANDBOX_MEASUREMENT_OF_EXISTING_TESTS_NOT_A_TRUE_CAPABILITY_RECEIPT".
    # A tier states whether a test named the function, not whether THIS
    # answer is right. Two ways to lie with it.

    def inventory_tier_reported_as_verification() -> bool:
        import grounded_action_v1 as G
        r = G.act("compute the sha256 of canonical/CANONICAL_POINTER.json",
                  memory=False)
        if r.get("source") != "MODULE_INVENTORY":
            return False
        return bool(r.get("verified")) or bool(r.get("ok"))

    def inventory_displaces_a_verified_capability() -> bool:
        import grounded_action_v1 as G
        # Escalate, never replace. A verified capability must always win.
        r = G.act("audit the python source canonical/runtime/bound_capabilities",
                  memory=False)
        return r.get("source") == "MODULE_INVENTORY"

    add("grounded_action_v1.act", "an inventory tier presented as verification",
        inventory_tier_reported_as_verification)
    add("grounded_action_v1.act", "the inventory taking over from a verified capability",
        inventory_displaces_a_verified_capability)

    # --- a memory must be revocable --------------------------------------
    # Structural suppression fires on ONE observation and then skips the
    # capability forever -- so it can never gather the successes that would
    # lift it. Install the missing package and the machine would still
    # refuse, permanently, for a reason that had stopped being true.
    #
    # This actually happened: pypdf was installed, and
    # pdf.extract.text.pypdf was still recorded as unusable. A memory that
    # cannot be revoked is a grudge, not knowledge.

    def structural_suppression_never_expires() -> bool:
        import experience_v1 as E
        E.DEFAULT_STATE = _isolated_experience_state("canonical/runtime/state/_falsify_exp_e.json")
        E._STATE_CACHE.clear()
        E.record("falsify.cap", "BOUND_PYPI_INSTALL_FAILED", False,
                 structural=True)
        st = E._load(E.DEFAULT_STATE)
        for key in st["cells"]:
            # A real distant past. Zero means "no timestamp recorded",
            # which is a different and legitimate case -- winding to it
            # tests nothing, and a test that tests nothing is decoration.
            st["cells"][key]["last_seen"] = 1.0
        E._save(st, E.DEFAULT_STATE)
        return bool(E.is_suppressed("falsify.cap"))

    add("experience_v1.is_suppressed",
        "a suppression that can never be revoked",
        structural_suppression_never_expires)

    # --- offers are not constraints --------------------------------------
    # In a chain, step one's output path is offered to step two as a
    # candidate input. It is not something step two was asked to consume.
    # Treating it as a constraint made a .json from an audit look like a
    # kind contradiction to a docx capability, and the correct capability
    # was rejected before it was ever considered -- so a clause saying
    # "verify the docx" silently ran "create a docx".

    def prior_step_output_treated_as_a_constraint() -> bool:
        import grounded_action_v1 as G
        goal = "verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx"
        r = G.act(goal, memory=False,
                  extra_paths=["canonical/astra_runtime/tmp/brain_out__x__y.json"])
        for x in (r.get("rejected") or []):
            if (x.get("capability_id") == "docx.document.verify.intent_ooxml"
                    and x.get("why") == "INPUT_KIND_CONTRADICTS_GOAL_FILE"):
                return True
        return False

    add("grounded_action_v1.act",
        "a previous step's output treated as a constraint on this one",
        prior_step_output_treated_as_a_constraint)

    # --- three ways a result can verify itself falsely -------------------
    # Each of these actually happened. A check that reads one declared
    # field while ignoring the verdict sitting beside it is not
    # verification; it is a field lookup with better manners.

    def result_saying_pass_false_still_verifies() -> bool:
        import grounded_action_v1 as G
        ok, _note = G._check_expect(
            {"field": "coverage_complete", "type": "field_equals", "value": True},
            {"pass": False, "coverage_complete": True})
        return bool(ok)

    def result_saying_unresolved_still_verifies() -> bool:
        import grounded_action_v1 as G
        # terminal.kstar.root.assess declared output_verified == true while
        # returning status UNRESOLVED, and was reported VERIFIED_ACTION.
        ok, _note = G._check_expect(
            {"field": "output_verified", "type": "field_equals", "value": True},
            {"status": "UNRESOLVED", "output_verified": True})
        return bool(ok)

    def named_destination_ignored() -> bool:
        import world_binding_v1 as WB
        got = WB.named_destination(
            'write "x" to canonical/astra_runtime/tmp/thing.txt')
        return got != "canonical/astra_runtime/tmp/thing.txt"

    add("grounded_action_v1._check_expect", "a result reporting pass=false",
        result_saying_pass_false_still_verifies)
    add("grounded_action_v1._check_expect", "a result reporting status UNRESOLVED",
        result_saying_unresolved_still_verifies)
    add("world_binding_v1.named_destination", "a destination the user actually named",
        named_destination_ignored)

    # --- only a fact about the machine may disable a capability ----------
    # THIRD SIGHTING OF THE SAME ERROR. A memory keyed on the wrong context
    # generalises past the situation that made it true: first a goal-relative
    # file kind became a permanent ban, then a precondition, and now eight
    # audits of ONE directory containing an unparseable file disabled
    # python.source.audit.ast everywhere, including targets that audit fine.
    # The unit of memory keeps needing to include what made the fact true.

    def statistical_failures_disable_a_capability() -> bool:
        import experience_v1 as E
        E.DEFAULT_STATE = _isolated_experience_state("canonical/runtime/state/_falsify_exp_f.json")
        E._STATE_CACHE.clear()
        for _ in range(8):
            E.record("falsify.cap", "RuntimeError", False, structural=False)
        return bool(E.is_suppressed("falsify.cap"))

    def structural_fact_still_suppresses() -> bool:
        import experience_v1 as E
        # The opposite error: refusing to act on a real fact about the box.
        E.DEFAULT_STATE = _isolated_experience_state("canonical/runtime/state/_falsify_exp_g.json")
        E._STATE_CACHE.clear()
        E.record("falsify.cap2", "BOUND_CAPABILITY_SOURCE_UNSUPPORTED",
                 False, structural=True)
        return not E.is_suppressed("falsify.cap2")

    add("experience_v1.is_suppressed",
        "a run of failures treated as a fact about the machine",
        statistical_failures_disable_a_capability)
    add("experience_v1.is_suppressed",
        "a real structural fact about this box ignored",
        structural_fact_still_suppresses)

    # --- ask the machine before asking the package database --------------
    # THREE CAPABILITIES SAT BLOCKED BEHIND A GATE GUARDING THE WRONG THING.
    # The apt gate proves what it is ABOUT TO ACQUIRE -- name, version and
    # archive hash. That is the right guard on acquisition and the wrong
    # guard on presence: openpyxl and xlsxwriter were installed the whole
    # time and the machine refused to touch them. Autoconf's founding rule
    # is to test for features, not for versions. Proving the probe can fail
    # matters as much as proving it can affirm -- sqlite3's CLI really is
    # absent, and it must stay refused.

    def missing_binary_satisfied_by_probe() -> bool:
        from canonical.runtime.astra_runtime import _already_present_dependency
        # sqlite_verify_cli shells out to the sqlite3 binary, which is not
        # on this box. It imports nothing third-party, so the probe has
        # nothing to affirm and must hand back to the acquisition gate.
        return _already_present_dependency(
            {"adapter_module": "sqlite_verify_cli"}) is not None

    def missing_module_satisfied_by_probe() -> bool:
        from canonical.runtime.astra_runtime import _already_present_dependency
        # yq_yaml_json imports `yaml`. This is only a counterexample on a box where
        # PyYAML is absent; measured 2026-11-01, it had arrived, so the premise had
        # inverted and the verifier was being reported broken for answering correctly.
        if importlib.util.find_spec("yaml") is not None:
            raise DependencyUnavailable("this counterexample needs PyYAML to be absent")
        return _already_present_dependency(
            {"adapter_module": "yq_yaml_json"}) is not None

    def present_module_not_seen_by_probe() -> bool:
        from canonical.runtime.astra_runtime import _already_present_dependency
        # The opposite error, and the one that cost three capabilities. It needs
        # openpyxl to actually be here; measured 2026-11-01 it was not, so the case
        # was asserting an inversion it could not observe.
        if importlib.util.find_spec("openpyxl") is None:
            raise DependencyUnavailable("this counterexample needs openpyxl to be present")
        got = _already_present_dependency(
            {"adapter_module": "xlsx_verify_openpyxl"})
        return not (isinstance(got, dict)
                    and got.get("status") == "ALREADY_PRESENT_FEATURE_PROBED")

    add("astra_runtime._already_present_dependency",
        "a missing binary declared satisfied by a feature probe",
        missing_binary_satisfied_by_probe)
    add("astra_runtime._already_present_dependency",
        "a missing module declared satisfied by a feature probe",
        missing_module_satisfied_by_probe)
    add("astra_runtime._already_present_dependency",
        "a module the machine actually holds ignored",
        present_module_not_seen_by_probe)

    # --- the slot's own name outranks the capability's -------------------
    # Two differently-typed slots filled with one file is not binding, it is
    # duplication with the type check removed. It surfaced as json.loads()
    # being handed a binary spreadsheet, and again as a bundle verified
    # against a manifest from an unrelated directory.

    def workbook_fills_the_json_slot() -> bool:
        import world_binding_v1 as WB
        got = WB._pick_path("json_path", "xlsx.table.verify_against_json_records",
                            ["canonical/astra_runtime/tmp/FANOUT_JOIN.xlsx"],
                            Path("/home/user/brain"))
        return got is not None and str(got).lower().endswith(".xlsx")

    def unrelated_manifest_binds_to_the_bundle() -> bool:
        import world_binding_v1 as WB
        from canonical.runtime import grounded_action_v1 as GA
        root = Path("/home/user/brain")
        entry = GA.load_registry()["archive.verify.tar_gz.gnu"]
        got = WB.complete_inputs("verify the archive members against the manifest",
                                 root, entry, compiler=None, goal_paths=[])
        bound = str((got["inputs"] or {}).get("manifest_path") or "")
        return "ARCHIVE_VERIFY_MANIFEST.json" not in bound

    add("world_binding_v1._pick_path",
        "a workbook handed to the capability's JSON slot",
        workbook_fills_the_json_slot)
    add("world_binding_v1.complete_inputs",
        "a manifest from another directory bound to this bundle",
        unrelated_manifest_binds_to_the_bundle)

    # --- an audit that cannot finish hides the finding -------------------

    def audit_hides_a_finding() -> bool:
        import importlib.util, json, shutil
        root = Path("/home/user/brain")
        d = root / "canonical/astra_runtime/tmp/_falsify_audit"
        report = root / "canonical/astra_runtime/tmp/_falsify_audit_report.json"
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        try:
            (d / "good.py").write_text("def f():\n    return 1\n")
            (d / "bad.py").write_text("def g(:\n    return \\\n")
            spec = importlib.util.spec_from_file_location(
                "_falsify_aud",
                root / "canonical/runtime/bound_capabilities/python_source_audit.py")
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            try:
                m.run({"source_root": "canonical/astra_runtime/tmp/_falsify_audit",
                       "output_path": "canonical/astra_runtime/tmp/_falsify_audit_report.json"},
                      root)
            except RuntimeError:
                return True  # aborted: the only finding in the tree is lost
            rep = json.loads(report.read_text())
            return not (rep["totals"]["files"] == 1
                        and rep["totals"]["unparseable"] == 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)
            try:
                report.unlink()
            except Exception:
                pass

    add("bound_capabilities.python_source_audit",
        "an unparseable file that aborts the audit instead of being reported",
        audit_hides_a_finding)

    # --- opening the gate must not have opened the verifier --------------
    # The three capabilities above were unreachable for so long that nothing
    # had ever tested what happens when they run. A capability that verifies
    # on wrong data is worse than one that refuses.

    def tampered_xlsx_still_verifies() -> bool:
        import importlib.util, json, shutil
        root = Path("/home/user/brain")
        tmp = root / "canonical/astra_runtime/tmp/_falsify_xlsx"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        try:
            src_x = root / "canonical/astra_runtime/tmp/FANOUT_JOIN.xlsx"
            src_j = root / "canonical/astra_runtime/tmp/FANOUT_JOIN_MANIFEST.json"
            if not (src_x.is_file() and src_j.is_file()):
                # Returning True here meant "affirmed" -- a missing fixture was reported as a
                # broken verifier, which is this module's own disease committed inside it.
                # A fixture that is not on disk leaves the case untested, and says so.
                raise DependencyUnavailable("the FANOUT_JOIN fixtures are not on this box")
            if importlib.util.find_spec("openpyxl") is None:
                raise DependencyUnavailable("this counterexample needs openpyxl")
            shutil.copy(src_x, tmp / "T.xlsx")
            shutil.copy(src_j, tmp / "T.json")
            recs = json.loads((tmp / "T.json").read_text())
            recs[0]["username"] = "TAMPERED_BY_THE_FALSIFIER"
            (tmp / "T.json").write_text(json.dumps(recs))
            spec = importlib.util.spec_from_file_location(
                "_falsify_xv",
                root / "canonical/runtime/bound_capabilities/xlsx_verify_openpyxl.py")
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            try:
                m.run({"xlsx_path": "canonical/astra_runtime/tmp/_falsify_xlsx/T.xlsx",
                       "json_path": "canonical/astra_runtime/tmp/_falsify_xlsx/T.json"},
                      root)
            except RuntimeError:
                return False  # correctly refused
            return True  # WRONGLY AFFIRMED
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    add("bound_capabilities.xlsx_verify_openpyxl",
        "a workbook whose records were tampered with",
        tampered_xlsx_still_verifies)

    # --- the mutation test -------------------------------------------------
    # TWENTY-NINE OF SEVENTY-FOUR CAPABILITIES DECLARE `expect: output_
    # verified == true`, and their adapters assign that literal at the end
    # of run(). The field observes nothing: it is the proposer grading its
    # own homework, and it survives every perturbation of the artifact,
    # which is the definition of decoration. Mutation testing says the same
    # thing from the other side -- a mutant that no assertion can kill is
    # not a test. So the mutant is injected here: an adapter that lies
    # about the hash of the bytes it just wrote.

    def mutant_adapter_hash_survives() -> bool:
        try:
            from canonical.runtime import astra_runtime as AR
        except Exception:
            return True
        original = AR._invoke_bound_capability

        def mutant(args):
            out = original(args)
            if isinstance(out, dict) and out.get("output_sha256"):
                out["output_sha256"] = "0" * 64  # the mutation: lie about it
            return out

        AR._invoke_bound_capability = mutant
        try:
            from canonical.runtime import grounded_action_v1 as GA
            r = GA.act("audit the python source canonical/runtime/bound_capabilities",
                       memory=False)
        finally:
            AR._invoke_bound_capability = original
        return bool(r.get("verified"))

    def missing_artifact_survives() -> bool:
        from canonical.runtime import grounded_action_v1 as GA
        got = GA._independent_artifact_check(
            {"output_path": "canonical/astra_runtime/tmp/DOES_NOT_EXIST.json",
             "output_sha256": "0" * 64}, Path("/home/user/brain"))
        return got is None or bool(got[0])

    def empty_artifact_survives() -> bool:
        from canonical.runtime import grounded_action_v1 as GA
        root = Path("/home/user/brain")
        f = root / "canonical/astra_runtime/tmp/_falsify_empty.bin"
        try:
            f.write_bytes(b"")
            got = GA._independent_artifact_check(
                {"output_path": "canonical/astra_runtime/tmp/_falsify_empty.bin"}, root)
        finally:
            try:
                f.unlink()
            except Exception:
                pass
        return got is None or bool(got[0])

    add("grounded_action_v1.act",
        "an adapter that lies about the hash of the bytes it wrote",
        mutant_adapter_hash_survives)
    add("grounded_action_v1._independent_artifact_check",
        "a claimed artifact that was never written",
        missing_artifact_survives)
    add("grounded_action_v1._independent_artifact_check",
        "a claimed artifact that is empty",
        empty_artifact_survives)

    # --- a plan learned from doing the work --------------------------------
    # Everything the machine learned before this was NEGATIVE -- what
    # failed, what the box lacks. A chain that succeeded was thrown away,
    # so the same job was re-planned from scratch forever. Macros make
    # success accumulate. Learned plans are the most dangerous thing added
    # so far, because a remembered success feels like proof, so each of the
    # ways it can be wrong is pinned here.

    def one_bad_instance_erases_the_plan() -> bool:
        # FOURTH SIGHTING OF THE SAME ERROR. A goal-relative file kind
        # became a permanent ban; a precondition became one; eight audits
        # of one bad directory disabled auditing everywhere. Here, one
        # copied .docx failing DOCX_INTENT_SIDECAR_MIXSING -- a fact about
        # that file, not about the plan -- erased a plan that worked for
        # every other .docx. A failure is evidence, not a verdict.
        import tempfile
        from pathlib import Path as _P
        try:
            from canonical.runtime import macro_v1 as MC
        except Exception:
            return True
        fd, tmp = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        original = MC.STATE
        MC.STATE = _P(tmp)
        try:
            clauses = ["verify the docx one.docx",
                       "create a tar.gz archive from the manifest"]
            steps = [{"capability_id": "a.b", "verified": True},
                     {"capability_id": "c.d", "verified": True}]
            for _ in range(3):
                MC.record(clauses, steps)
            MC.note_failure(MC.signature(clauses))
            return MC.lookup(clauses) is None  # wrongly erased
        finally:
            MC.STATE = original
            try:
                os.unlink(tmp)
            except Exception:
                pass

    def macro_shape_ignores_file_kind() -> bool:
        from canonical.runtime import macro_v1 as MC
        docx = MC.signature(["verify the docx one.docx",
                             "create a tar.gz archive from the manifest"])
        pdf = MC.signature(["verify the docx one.pdf",
                            "create a tar.gz archive from the manifest"])
        return docx == pdf  # a .pdf is not the same job as a .docx

    def macro_preference_forces_an_impossible_capability() -> bool:
        # A MACRO IS AN OFFER, NEVER A CONSTRAINT. It may only choose
        # among capabilities that already survived perception, binding and
        # preconditions -- it must never be able to inject one.
        from canonical.runtime import grounded_action_v1 as GA
        r = GA.act("audit the python source canonical/runtime/bound_capabilities",
                   memory=False, prefer="definitely.not.a.capability")
        return str(r.get("capability_id")) == "definitely.not.a.capability"

    add("macro_v1.note_failure",
        "one instance's failure erasing a plan that works everywhere else",
        one_bad_instance_erases_the_plan)
    add("macro_v1.signature",
        "a different file kind treated as the same job",
        macro_shape_ignores_file_kind)
    add("grounded_action_v1.act",
        "a remembered preference injecting a capability that cannot run",
        macro_preference_forces_an_impossible_capability)

    # --- the battery needs negative controls ------------------------------
    # A battery of things the machine can already do cannot detect the
    # worst failure there is: a machine that verifies everything. So the
    # completion battery now carries goals whose honest answer is NO.
    # Three leaked the first time it was run, all reporting VERIFIED.

    def wrong_kind_file_still_verifies() -> bool:
        from canonical.runtime import grounded_action_v1 as GA
        r = GA.act("verify the xlsx canonical/astra_runtime/tmp/"
                   "BOUND_PDF_TEXT_TEST.pdf", memory=False)
        return bool(r.get("ok"))

    def absent_path_silently_substituted() -> bool:
        # The instructive one. The nonexistent directory was promoted to
        # its parent, so the machine audited 2078 files nobody asked
        # about, did that work perfectly, and reported success.
        from canonical.runtime import grounded_action_v1 as GA
        r = GA.act("audit the python source canonical/runtime/"
                   "NO_SUCH_DIRECTORY_HERE", memory=False)
        return bool(r.get("ok"))

    def docx_verifier_given_a_workbook() -> bool:
        from canonical.runtime import grounded_action_v1 as GA
        r = GA.act("verify the docx canonical/astra_runtime/tmp/"
                   "FANOUT_JOIN.xlsx", memory=False)
        return bool(r.get("ok"))

    add("grounded_action_v1.act",
        "a pdf verified as an xlsx because the goal said so",
        wrong_kind_file_still_verifies)
    add("grounded_action_v1.act",
        "a path that does not exist replaced by one that does",
        absent_path_silently_substituted)
    add("grounded_action_v1.act",
        "a workbook verified as a docx",
        docx_verifier_given_a_workbook)

    # --- the forge must refuse what it cannot kill ------------------------
    # Admitting a module is a claim that it can do work. Two ways the
    # forge nearly made that claim falsely, both found by running it.

    def vacuous_result_not_detected() -> bool:
        from canonical.runtime import capability_forge_v1 as FG
        return not FG.is_vacuous({"status": "NO_POSTCONDITION_PARSED",
                                  "checked": 0, "violations": []})

    def self_reported_failure_not_detected() -> bool:
        from canonical.runtime import capability_forge_v1 as FG
        return not FG.self_reported_failure(
            {"status": "FAIL_CLOSED", "pass": False, "errors": ["x"]})

    add("capability_forge_v1.is_vacuous",
        "a result that reports finding nothing, admitted as work",
        vacuous_result_not_detected)
    add("capability_forge_v1.self_reported_failure",
        "a run that reports its own failure, admitted as success",
        self_reported_failure_not_detected)

    # --- a forged capability may only be the one that was admitted --------
    # The invoker is one adapter for every capability the forge produces, so
    # it is the one place where a name from outside could reach a call. The
    # forged registry is the allowlist; a leaf must prove it refuses.

    def unadmitted_capability_accepted() -> bool:
        from canonical.runtime.bound_capabilities import forged_invoker as FI
        out = FI.run({"_forged_id": "forged.never.admitted.anything"})
        return not (isinstance(out, dict) and out.get("ok") is False)

    add("bound_capabilities.forged_invoker.run",
        "a capability_id that was never admitted, executed anyway",
        unadmitted_capability_accepted)


    # --- the admission gates added on 2026-11-01 -------------------------
    # A gate that has never been shown to refuse is not a gate. These two were
    # written and measured the same day; per this module's own rule, they arrive
    # with their counterexamples or they are untested.

    def repair_gate_accepts_a_lookup_table() -> bool:
        from canonical.swe_kernel import repair_input_dependency_gate_v1 as G
        before = (
            "def compute_invoice(items, disc):\n"
            "    return sum(items) - disc\n"
        )
        # Answers the two visible assertions and never reads `items`.
        after = (
            "def compute_invoice(items, disc):\n"
            "    if disc % 2 == 0:\n"
            "        return 110.0\n"
            "    return 85.0\n"
        )
        return G.gate(before, after)["status"] == G.PASS

    add("repair_input_dependency_gate_v1.gate",
        "a patch that answers the tests without reading the data",
        repair_gate_accepts_a_lookup_table)

    def skill_qualifies_without_any_heldout_instance() -> bool:
        import sqlite3
        from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
            compile_and_qualify_skill,
        )
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp, "training.sqlite")
            con = sqlite3.connect(str(db))
            con.execute("CREATE TABLE flags (name TEXT PRIMARY KEY, enabled INTEGER)")
            con.execute("INSERT INTO flags VALUES ('dark_mode', 0)")
            con.commit()
            con.close()
            # No held-out goal: the training instance is not evidence of transfer.
            r = compile_and_qualify_skill(
                goal="Enable feature flag dark_mode in database %s" % db,
                trace=[{"kind": "sqlite_query", "db_path": str(db),
                        "sql": "UPDATE flags SET enabled = 1 WHERE name = ?",
                        "params": ["dark_mode"]}],
                postcondition={"kind": "sqlite_row_exists", "db_path": str(db),
                               "sql": "SELECT enabled FROM flags WHERE name = 'dark_mode' "
                                      "AND enabled = 1"},
                db_path=Path(tmp, "workflows.sqlite"),
            )
        return bool(r.get("pass"))

    add("causal_trace_to_skill_compiler_v1.compile_and_qualify_skill",
        "a skill qualified by replaying its own training instance",
        skill_qualifies_without_any_heldout_instance)

    return out


class DependencyUnavailable(RuntimeError):
    """A counterexample whose premise is a fact about this box, and the box changed.

    Some cases are only counterexamples on a machine with (or without) a particular
    package: "a missing module declared satisfied by a feature probe" needs the module
    to be missing, and "a module the machine actually holds ignored" needs it present.
    Measured 2026-11-01: two such cases had silently inverted -- PyYAML had arrived and
    openpyxl had gone -- so both now reported the verifier as broken when the verifier
    was right and the premise was stale. Raising this makes the case say so instead.
    """


SAID_NO = "SAID_NO"
AFFIRMED = "AFFIRMED"
CRASHED = "CRASHED"
UNTESTED = "UNTESTED"


def run() -> tuple[int, list[tuple[str, str, str]]]:
    """Return (number counted as bad, all results as (verifier, counterexample, status)).

    Four outcomes, because three were not enough. A verifier that affirms is bad, and a
    verifier that crashes while being tested is also bad -- it has not been shown able to
    say no. But an environment that cannot supply the premise is neither: it is untested,
    and saying "affirmed" made a missing package look like a broken verifier, which is the
    same conflation this module exists to catch.
    """
    results: list[tuple[str, str, str]] = []
    bad = 0
    for name, wrong, fn in _cases():
        try:
            status = AFFIRMED if bool(fn()) else SAID_NO
        except DependencyUnavailable as exc:
            status = UNTESTED
            wrong = "%s [untested: %s]" % (wrong, exc)
        except Exception as exc:
            # Crashing is not affirming, but it is not a working verifier either;
            # report it separately so it cannot hide behind the label.
            status = CRASHED
            wrong = "%s [%s: %s]" % (wrong, type(exc).__name__, str(exc)[:60])
        results.append((name, wrong, status))
        if status in (AFFIRMED, CRASHED):
            bad += 1
    return bad, results


def main() -> int:
    bad, results = run()
    proven = sum(1 for _n, _w, st in results if st == SAID_NO)
    untested = sum(1 for _n, _w, st in results if st == UNTESTED)
    print("%s\n" % SCHEMA)
    print("Each row feeds a verifier an input that is known to be wrong.")
    print("SAID_NO is a pass. AFFIRMED and CRASHED are failures. UNTESTED is not a pass.\n")
    for name, wrong, status in results:
        print("%-9s %-42s %s" % (status, name, wrong))
    print("\n%d/%d verifiers proven able to fail (%d untested, %d bad)"
          % (proven, len(results), untested, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
