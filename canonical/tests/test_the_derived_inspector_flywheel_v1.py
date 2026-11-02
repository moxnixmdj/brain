"""The flywheel must be able to refuse its own inspector.

WHY THIS EXISTS
---------------
Deriving inspectors removes the human from the loop, which is the only way coverage grows faster
than one capability per session. The danger of removing the human is obvious: a bad derivation
registers itself, coverage rises, and every number downstream becomes a fiction.

So the decisive case in this file is not the successful registration. It is:

    a deliberately over-permissive derivation, whose inspector accepts the negative control,
    must be REFUSED and must not enter the registry.

If that case ever passes the other way, the flywheel is worse than writing inspectors by hand and
the module should be deleted rather than tuned.
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import derived_inspector_flywheel_v1 as W  # noqa: E402

CHECKER = '''\
REQUIRED = ["REPORT TOTAL", "PERIOD 2026-01"]
def check(text):
    for need in REQUIRED:
        if need not in text:
            return False
    return True
'''

ARTIFACT = "REPORT TOTAL: 42\nPERIOD 2026-01\n"
DECOY = "REPORT TOTAL: 42\nPERIOD 2025-12\n"  # differs in exactly one required respect


class FlywheelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "check_report.py").write_text(CHECKER)
        (self.root / "report.txt").write_text(ARTIFACT)
        (self.root / "decoy.txt").write_text(DECOY)

    def tearDown(self):
        self.tmp.cleanup()

    def _derive(self, checker="check_report.py"):
        return W.derive(capability_id="report.total.v1", checker_paths=[checker], root=self.root)

    def test_it_reads_requirements_out_of_the_environments_own_checker(self):
        d = self._derive()
        self.assertFalse(d.refused, d.reason)
        literals = [r.literal for r in d.requirements]
        self.assertIn("REPORT TOTAL", literals)
        self.assertIn("PERIOD 2026-01", literals)
        self.assertNotIn("check_report.py", literals)  # paths are not content requirements

    def test_a_positive_artifact_passes_and_the_decoy_is_refused(self):
        flight = W.Flight()
        row = flight.attempt(
            derivation=self._derive(),
            positive={"root": self.root, "artifact": "report.txt"},
            negative={"root": self.root, "artifact": "decoy.txt"},
        )
        self.assertEqual(row["status"], "REGISTERED", row)
        self.assertIn("report.total.v1", flight.registry)
        metrics = flight.metrics()
        self.assertEqual(metrics["registered"], 1)
        self.assertEqual(metrics["over_permissive_derivations"], 0)

    def test_an_inspector_that_accepts_the_decoy_is_refused_and_not_registered(self):
        # A checker that states nothing a decoy can violate: the derivation will accept anything.
        (self.root / "weak_check.py").write_text('print("ok")\n')
        (self.root / "weak_artifact.txt").write_text("anything at all\n")
        (self.root / "weak_decoy.txt").write_text("something else entirely\n")
        d = self._derive("weak_check.py")
        flight = W.Flight()
        row = flight.attempt(derivation=d,
                             positive={"root": self.root, "artifact": "weak_artifact.txt"},
                             negative={"root": self.root, "artifact": "weak_decoy.txt"})
        # Either the derivations were too thin to build from, or they do not hold on the positive.
        # Both are refusals, and neither may register. "print(\"ok\")" now yields nothing at all:
        # short literals are noise, measured while writing this test.
        self.assertIn(row["status"], {"REFUSED__NOTHING_TO_DERIVE",
                                      "REFUSED__DERIVATION_DOES_NOT_HOLD_ON_THE_POSITIVE"}, row)
        self.assertEqual(flight.registry, {})

    def test_a_forged_over_permissive_inspector_is_caught_by_the_negative_control(self):
        # Force the failure mode directly: a derivation whose inspector ignores its requirements.
        d = self._derive()
        d.requirements = []
        flight = W.Flight()
        # With no requirements the built inspector accepts everything, including the decoy.
        row = flight.attempt(derivation=d,
                             positive={"root": self.root, "artifact": "report.txt"},
                             negative={"root": self.root, "artifact": "decoy.txt"})
        self.assertEqual(row["status"], "REFUSED__INSPECTOR_ACCEPTED_THE_NEGATIVE_CONTROL", row)
        self.assertEqual(flight.registry, {})
        self.assertEqual(flight.metrics()["over_permissive_derivations"], 1)

    def test_a_missing_checker_is_refused_rather_than_guessed(self):
        d = self._derive("no_such_checker.py")
        self.assertTrue(d.refused)
        self.assertEqual(d.reason, "NO_CHECKER_IN_THE_ENVIRONMENT")

    def test_a_derived_inspector_goes_stale_when_its_checker_moves(self):
        d = self._derive()
        inspector = d.build()
        ok, _ = inspector({"root": self.root, "artifact": "report.txt"})
        self.assertTrue(ok)
        (self.root / "check_report.py").unlink()
        ok, reason = inspector({"root": self.root, "artifact": "report.txt"})
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("DERIVED_INSPECTOR_CHECKER_MISSING"), reason)

    def test_a_derived_inspector_refuses_an_artifact_outside_the_root(self):
        inspector = self._derive().build()
        ok, reason = inspector({"root": self.root, "artifact": "../escape.txt"})
        self.assertFalse(ok)
        self.assertEqual(reason, "DERIVED_INSPECTOR_ARTIFACT_OUTSIDE_ROOT")

    def test_derivation_does_not_hoover_up_every_literal(self):
        d = self._derive()
        self.assertLessEqual(len(d.requirements), 8)
        names = [r.literal for r in d.requirements]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
