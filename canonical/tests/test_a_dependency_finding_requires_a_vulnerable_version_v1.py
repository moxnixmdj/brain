"""A dependency audit that flags FIXED versions is worse than no audit.

Measured 2026-11-01 on main `6aa5dab`, the 49-sentence advanced census:

    "Audit the dependency list in <p>/requirements.txt for known vulnerabilities."
      -> PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
      -> vulnerabilities: requests==2.32.3, pyyaml==6.0.1, cryptography==43.0.0

Every one of those three versions is already PAST its fix, and the door certified the report as
exactly accepted.  The cause was one line: the audit flagged a package by MEMBERSHIP in its
advisory dict and never compared the pinned version with the fixed one, so the finding was a
constant of the package name rather than a fact about the version.

The laws pinned here:

  * a finding requires a pinned version BELOW the fixed version;
  * a dependency the table cannot judge is reported as unchecked, never silently clean;
  * a package already past its fix is not reported at all;
  * an unpinned range is "cannot judge", not "vulnerable" and not "safe".
"""
from __future__ import annotations

import pathlib
import shutil
import tempfile
import unittest

from canonical.swe_kernel import diagnostics_perf_and_design_engine_v1 as engine


class TheAuditComparesAgainstTheFixedVersionV1(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _audit(self, requirements: str) -> dict:
        f = self.tmp / "requirements.txt"
        f.write_text(requirements, encoding="utf-8")
        return engine.audit_dependency_vulnerabilities(f)

    def test_a_version_past_its_fix_is_not_reported(self) -> None:
        art = self._audit("requests==2.32.3\npyyaml==6.0.1\ncryptography==43.0.0\n")
        self.assertTrue(art["verified"], art)
        self.assertEqual(art["vulnerability_count"], 0, art.get("vulnerabilities"))
        self.assertEqual(art["unchecked_dependencies"], [])

    def test_a_version_below_its_fix_is_reported_with_the_fixed_version(self) -> None:
        art = self._audit("requests==2.19.0\npyyaml==5.1\n")
        found = {row["package"]: row for row in art["vulnerabilities"]}
        self.assertEqual(set(found), {"requests", "pyyaml"})
        self.assertEqual(found["requests"]["fixed_in"], "2.31.0")
        self.assertEqual(found["pyyaml"]["fixed_in"], "5.4")

    def test_a_dependency_the_table_cannot_judge_is_named_not_assumed_clean(self) -> None:
        art = self._audit("some-obscure-pkg==1.0.0\nrequests>=2.0\n")
        self.assertEqual(art["vulnerability_count"], 0)
        self.assertEqual(art["unchecked_dependencies"], ["requests", "some-obscure-pkg"])
        self.assertIn("ADVISORY_TABLE_IS_A_PINNED_SUBSET", art["coverage_note"])
        self.assertEqual(art["advisory_table_packages"], len(engine._KNOWN_ADVISORIES))

    def test_the_two_sides_of_one_boundary(self) -> None:
        # The nearest world in which the accepting rule must fail: one patch release below the fix.
        below = self._audit("requests==2.30.9\n")
        at = self._audit("requests==2.31.0\n")
        self.assertEqual(below["vulnerability_count"], 1)
        self.assertEqual(at["vulnerability_count"], 0)


if __name__ == "__main__":
    unittest.main()
