"""One runner serves 294 capabilities, so one inspector can re-inspect all of them.

Measured on ``e020898``: the 367-prose corpus passed 223 goals and certified
**none** of them. 221 of those 223 were stopped by a single reason --
``NO_INDEPENDENT_REINSPECTION_FOR:canonical/runtime/<name>.py.auto.v1`` -- and
every one of those rows executes through the same ``bound_capability_cli``
adapter and reports the same result shape: ``argv``, ``returncode``, ``stdout``,
``stderr``.

The inspector table was keyed on capability id, so a family of 294 capabilities
that share one runner needed 294 entries to be checkable and had none. Keying a
second lookup on the adapter covers the whole family with one entry.

  367-prose corpus exact-verified    0 of 223 -> 174 of 223

with pass/fail and failure kinds completely unchanged (223/144, kinds
CONTRACT_REFUSAL 138 / ENVIRONMENT_BLOCKER 3 / UNKNOWN 3).

What makes this honest rather than a rubber stamp is that the check is the same
one PR #6121 established: run it again and require returncode, stdout and stderr
to come back identical. Measured beforehand, 14 of 14 sampled scripts returned a
byte-identical result on a second run and left the working tree unchanged, so the
world does answer for them.

The interpreter allowance is deliberately the narrowest shape that covers the
family, and the tests below are mostly about what it refuses: extra arguments, a
script outside the repository, a path that is not a .py file, and a report whose
output does not reproduce. An interpreter in general is not read-only and is not
treated as one here.

The 46 rows that still refuse are recorded rather than papered over: they carry
``adapter=None`` because they are invoked in-process rather than through the
runner, so there is no argv to re-run and the refusal is correct.
"""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "canonical" / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import canonical.runtime.raw_goal_trace_acceptance_v1 as _acceptance  # noqa: E402

_ADAPTER_INSPECTORS = getattr(_acceptance, "_ADAPTER_INSPECTORS", None)
SCRATCH = "canonical/astra_runtime/tmp/p3v9k"
# A script that exists in the tree and is deterministic, so the re-run has
# something real to agree with.
REAL_SCRIPT = "canonical/runtime/compile_brain_unified_model_v1.py"


def _cli_inspector():
    if not _ADAPTER_INSPECTORS:
        raise AssertionError(
            "raw_goal_trace_acceptance_v1 has no adapter-keyed inspector, so the "
            "294 receipt-backed capabilities that all execute through "
            "bound_capability_cli have no re-inspection at all. Measured on "
            "e020898 that stopped 221 of the 223 passing goals."
        )
    return _ADAPTER_INSPECTORS["bound_capability_cli"]


def _inspect(argv, stdout, returncode=0, stderr=""):
    return _cli_inspector()(
        {"argv": argv},
        {"adapter": "bound_capability_cli", "stdout": stdout,
         "stderr": stderr, "returncode": returncode},
        ROOT,
    )


class TestTheFamilyHasAnInspector(unittest.TestCase):
    def test_the_cli_adapter_is_covered(self):
        self.assertTrue(_ADAPTER_INSPECTORS, "no adapter-keyed inspector exists")
        self.assertIn("bound_capability_cli", _ADAPTER_INSPECTORS)


class TestTheInterpreterAllowanceIsNarrow(unittest.TestCase):
    """Mostly about refusals. An interpreter is not read-only in general."""

    def test_a_bare_script_inside_the_repository_is_accepted(self):
        # Establish the real output first, so this is not a hardcoded expectation.
        import subprocess

        proc = subprocess.run(["python3", REAL_SCRIPT], cwd=ROOT,
                              capture_output=True, timeout=300)
        if proc.returncode != 0:
            self.skipTest("script does not run here")
        ok, reason, ledger = _inspect(
            ["python3", REAL_SCRIPT], proc.stdout.decode("utf-8", "replace"))
        self.assertTrue(ok, "refused an honest, reproducible run: %s" % reason)
        self.assertTrue(ledger.get("command_re_run"), "did not actually re-run")

    def test_a_forged_output_for_an_interpreter_run_is_refused(self):
        ok, reason, _ = _inspect(["python3", REAL_SCRIPT], "INVENTED OUTPUT\n")
        self.assertFalse(ok, "certified an interpreter run whose output is invented")
        self.assertEqual(reason, "COMMAND_OUTPUT_NOT_REPRODUCED")

    def test_an_interpreter_with_extra_arguments_is_refused(self):
        ok, reason, _ = _inspect(["python3", REAL_SCRIPT, "--anything"], "")
        self.assertFalse(ok, "an argv with extra tokens is not the narrow shape")
        self.assertEqual(reason, "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS")

    def test_a_script_outside_the_repository_is_refused(self):
        ok, reason, _ = _inspect(["python3", "/etc/whatever.py"], "")
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_SCRIPT_OUTSIDE_REPOSITORY")

    def test_a_non_python_path_is_refused(self):
        # Not the narrow shape, so python3 is treated as what it is in general --
        # an interpreter that is not known to be read-only -- rather than being
        # reported as a bad script path.  Either refusal is correct; asserting
        # the wrong one would pin a detail instead of the guarantee.
        ok, reason, _ = _inspect(["python3", "canonical/runtime"], "")
        self.assertFalse(ok, "ran an interpreter against a directory")
        self.assertEqual(reason, "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS")

    def test_an_arbitrary_interpreter_is_still_refused(self):
        for program in ("perl", "ruby", "node", "sh", "bash", "eval"):
            ok, reason, _ = _inspect([program, REAL_SCRIPT], "")
            self.assertFalse(ok, "treated %s as read-only" % program)
            self.assertEqual(reason, "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS")


class TestEndToEndAFamilyMemberIsCertified(unittest.TestCase):
    def test_a_receipt_backed_capability_reaches_exact_acceptance(self):
        import re

        from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
        from canonical.runtime.live_brain_route_admission_v1 import solve

        reg = dict(load_verified_registry())
        auto = [c for c in sorted(reg) if c.endswith(".py.auto.v1")]
        self.assertTrue(auto, "no receipt-backed capabilities to test")
        certified = 0
        checked = 0
        for cid in auto[:12]:
            stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
            stem = stem.replace("_", " ").replace(".", " ")
            result = solve({"task_id": "FAMILY_%s" % cid.replace(".", "_")[:40],
                            "goal": "Run the %s." % stem})
            if result.get("pass") is not True:
                continue
            checked += 1
            certified += str(result.get("status")).endswith(
                "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED")
        self.assertGreater(checked, 0, "nothing passed to certify")
        self.assertEqual(
            certified, checked,
            "only %d of %d passing family members were certified" % (certified, checked))


class TestWhatStillRefusesIsStillRefused(unittest.TestCase):
    """The honest remainder, pinned so coverage cannot be claimed by accident."""

    def test_a_capability_not_run_through_the_adapter_is_not_certified(self):
        import re

        from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
        from canonical.runtime.live_brain_route_admission_v1 import solve

        reg = dict(load_verified_registry())
        # These are invoked in-process, so their result carries no argv and
        # there is nothing to re-run.
        targets = [c for c in sorted(reg)
                   if "proof_instantiation_search_v1.py.auto.v1" in c]
        if not targets:
            self.skipTest("no in-process row present to test")
        cid = targets[0]
        stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
        stem = stem.replace("_", " ").replace(".", " ")
        result = solve({"task_id": "INPROC_%s" % cid.replace(".", "_")[:40],
                        "goal": "Run the %s." % stem})
        if result.get("pass") is not True:
            self.skipTest("row does not pass here")
        self.assertFalse(
            str(result.get("status")).endswith("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "certified a row that carries no argv to re-run",
        )


if __name__ == "__main__":
    unittest.main()
