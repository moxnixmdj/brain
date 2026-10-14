"""The repository must pass its own integrity guard, and the guard must demonstrably work.

This test is the in-suite copy of the CI check in .github/workflows/repo-integrity-guard.yml.
Both exist on purpose: deleting one is caught by the other.
"""
from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "execution_guard" / "repo_integrity_guard_v1.py"


def _load_guard():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("execution_guard.repo_integrity_guard_v1")


class RepoIntegrityGuardV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = _load_guard()

    def test_guard_files_exist(self):
        self.assertTrue(GUARD.is_file(), "execution_guard/repo_integrity_guard_v1.py is missing")
        self.assertTrue((ROOT / ".github/workflows/repo-integrity-guard.yml").is_file(), "the guard workflow is missing")
        self.assertTrue((ROOT / ".github/CODEOWNERS").is_file(), "CODEOWNERS is missing")
        self.assertTrue((ROOT / "canonical/governance/REPO_INTEGRITY_POLICY_V1.json").is_file(), "integrity policy is missing")

    def test_self_test_proves_every_rule_fires(self):
        failures = self.guard.self_test()
        self.assertEqual(failures, [], "guard rules that do not fire on their own fixtures: " + "; ".join(failures))

    def test_repository_passes_static_rules(self):
        report = self.guard.run(ROOT, static_only=True)
        self.assertTrue(report.ok, "repository violates its integrity guard:\n" + "\n".join(str(v) for v in report.violations))

    def test_no_test_pin_ledger_and_no_hijacking_conftest(self):
        self.assertFalse((ROOT / "canonical/tests/historical_test_commits.json").exists())
        for conftest in ROOT.rglob("conftest.py"):
            if any(part in self.guard.SKIP_DIRS for part in conftest.parts):
                continue
            text = conftest.read_text(encoding="utf-8")
            for needle in ("Path.read_bytes =", "builtins.open =", "SourceFileLoader", "cat-file", "urlopen =", "sys.modules["):
                self.assertNotIn(needle, text, f"{conftest}: '{needle}' is the e0a256f8 hijack pattern")

    def test_terminal_achievement_requires_owner_countersign(self):
        self.assertIsNone(self.guard.TERMINAL_ACHIEVED_COUNTERSIGN_SHA256, "countersign constant must stay None until the owner sets it in person")
        authority = json.loads((ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json").read_text(encoding="utf-8"))
        self.assertIs(authority["truth"]["achieved"], False)

    def test_protected_paths_are_covered_by_codeowners(self):
        owners = (ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8")
        for rel in self.guard.PROTECTED_PATHS:
            top = "/" + rel.split("/")[0]
            self.assertTrue(("/" + rel) in owners or top + "/" in owners or top in owners, f"{rel} is not covered by CODEOWNERS")

    def test_policy_document_matches_guard_constants(self):
        policy = json.loads((ROOT / "canonical/governance/REPO_INTEGRITY_POLICY_V1.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["guard"]["path"], "execution_guard/repo_integrity_guard_v1.py")
        self.assertEqual(sorted(policy["guard"]["protected_paths"]), sorted(self.guard.PROTECTED_PATHS))
        limits = policy["guard"]["per_pull_request_limits"]
        self.assertEqual(limits["family_flips"], self.guard.MAX_FAMILY_FLIPS_PER_PR)
        self.assertEqual(limits["atomic_proved_delta"], self.guard.MAX_ATOMIC_PROVED_DELTA_PER_PR)
        self.assertEqual(limits["new_capabilities"], self.guard.MAX_NEW_CAPABILITIES_PER_PR)
        self.assertEqual(limits["new_receipts"], self.guard.MAX_NEW_RECEIPTS_PER_PR)
        self.assertEqual(limits["test_weakenings"], self.guard.MAX_TEST_WEAKENINGS_PER_PR)
        self.assertEqual(limits["deleted_test_files"], self.guard.MAX_DELETED_TEST_FILES_PER_PR)


if __name__ == "__main__":
    unittest.main()
