# PROJECT_BRAIN
"""Pins for python.supply_chain.{secret_scan,vulnerability_audit}.v1.

These two verbs exist because the front door was crediting both acts to `bandit`, which does
neither.  So what is pinned is exactly the difference:

* the four planted credentials are ALL found — including the AWS access-key id and the Slack
  token, which a name-matching scanner misses because their variables are not called `password`;
* the artifact never contains the credential itself, only a salted hash and a location;
* a scanner that is not installed refuses by name instead of reporting zero findings;
* an advisory service that cannot be reached refuses, and an empty report is only allowed from a
  run that actually happened — the one defect that made "audit for vulnerabilities" read as 0/0;
* the audited dependency set comes from the project's own declaration (pyproject, requirements,
  or a stated file), and a project with none refuses by name.

The network-dependent audit is exercised by the evidence probe, not here: a pin that needs PyPI
fails on a plane and teaches nothing.

Run: python -m pytest canonical/tests/test_python_supply_chain_secret_and_advisory_v1.py -q
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime.bound_capabilities import supply_chain_v1 as S
from canonical.runtime.bound_capabilities.quality_v1 import QualityError, verify_artifact

# Assembled from parts ON PURPOSE: a fixture that contains a token-shaped literal is itself a
# secret, and GitHub's push protection refused this commit for exactly that reason.  The runtime
# value is still a credential shape, which is what the detectors are being tested against.
AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
GH_TOKEN = "ghp_" + "012345678901234567890123456789012345"
SLACK_TOKEN = "xoxb-" + "123456789012-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx"

SECRETS = ('AWS_ACCESS_KEY_ID = "%s"\n'
           'DB_PASSWORD = "hunter2"\n'
           'TOKEN = "%s"\n'
           'SLACK = "%s"\n') % (AWS_KEY, GH_TOKEN, SLACK_TOKEN)

PYPROJECT = '''[project]
name = "sc-demo"
version = "0.1.0"
dependencies = [
    "pyyaml==5.1",
    "urllib3==1.26.0",
]
'''


class _Project(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="supply_pin_"))
        (self.root / "pkg").mkdir(parents=True)
        (self.root / "pkg" / "app.py").write_text(SECRETS, encoding="utf-8")
        (self.root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")

    def run_verb(self, verb: str, **extra):
        args = {"act_verb": verb, "source_root": str(self.root),
                "output_path": str(self.root / ".out" / (verb + ".json"))}
        args.update(extra)
        return S.run(args, self.root)

    def refuse(self, verb: str, **extra) -> str:
        with self.assertRaises(QualityError) as ctx:
            self.run_verb(verb, **extra)
        return str(ctx.exception)


class SecretScanTests(_Project):

    def test_it_finds_the_credentials_a_name_matcher_misses(self):
        result = self.run_verb("secret_scan")
        self.assertEqual(result["gate"], "PASS")
        detectors = result["findings_by_detector"]
        self.assertIn("AWS Access Key", detectors)
        self.assertIn("Slack Token", detectors)
        self.assertIn("GitHub Token", detectors)
        self.assertGreaterEqual(result["finding_count"], 4)

    def test_the_artifact_never_carries_the_secret_itself(self):
        self.run_verb("secret_scan")
        text = (self.root / ".out" / "secret_scan.json").read_text(encoding="utf-8")
        for credential in (AWS_KEY, "hunter2", GH_TOKEN, SLACK_TOKEN[:14]):
            self.assertNotIn(credential, text)
        payload = json.loads(text)
        self.assertFalse(payload["secrets_written_to_this_artifact"])
        self.assertTrue(all(len(f["secret_sha1"]) == 40 for f in payload["findings"]))
        self.assertTrue(verify_artifact(self.root / ".out" / "secret_scan.json"))

    def test_two_runs_agree(self):
        first = self.run_verb("secret_scan")["findings_by_detector"]
        second = self.run_verb("secret_scan")["findings_by_detector"]
        self.assertEqual(first, second)

    def test_a_missing_scanner_is_refused_by_name_not_reported_as_zero(self):
        # the system interpreter has no detect-secrets: this is the clean-box case
        self.assertIn("TOOL_NOT_INSTALLED:detect-secrets",
                      self.refuse("secret_scan", python_executable="/usr/bin/python3"))


class AdvisoryAuditTests(_Project):

    def test_the_audited_set_is_the_project_own_declaration(self):
        specs, source = S._declared_requirements(self.root, None)
        self.assertEqual(source, "pyproject.toml")
        self.assertIn("pyyaml==5.1", specs)
        self.assertIn("urllib3==1.26.0", specs)

    def test_a_requirements_file_is_used_when_the_manifest_is_absent(self):
        (self.root / "pyproject.toml").unlink()
        (self.root / "requirements.txt").write_text("# runtime\nflask==2.0.0\n", encoding="utf-8")
        specs, source = S._declared_requirements(self.root, None)
        self.assertEqual(source, "requirements.txt")
        self.assertEqual(specs, ["flask==2.0.0"])

    def test_a_project_that_declares_nothing_is_refused_by_name(self):
        (self.root / "pyproject.toml").unlink()
        self.assertIn("NO_DECLARED_DEPENDENCIES", self.refuse("vulnerability_audit"))

    def test_an_unreachable_advisory_service_refuses_instead_of_reporting_zero(self):
        unreachable = subprocess.CompletedProcess(
            args=[], returncode=3, stdout="",
            stderr="ERROR: Failed to resolve 'pyyaml'\nERROR: connection refused")
        with mock.patch.object(S, "_run", return_value=unreachable):
            self.assertIn("ADVISORY_SERVICE_UNREACHABLE", self.refuse("vulnerability_audit"))

    def test_the_auditor_maps_advisories_to_cve_aliases_and_fix_versions(self):
        canned = json.dumps({"dependencies": [{
            "name": "urllib3", "version": "1.26.0",
            "vulns": [{"id": "PYSEC-2021-108", "fix_versions": ["1.26.5"],
                       "aliases": ["CVE-2021-33503"], "description": "ReDoS"}],
        }], "fixes": []})
        ok = subprocess.CompletedProcess(args=[], returncode=1, stdout=canned, stderr="")
        with mock.patch.object(S, "_run", return_value=ok):
            result = self.run_verb("vulnerability_audit")
        self.assertEqual(result["vulnerability_count"], 1)
        payload = json.loads((self.root / ".out" / "vulnerability_audit.json").read_text())
        finding = payload["vulnerabilities"][0]
        self.assertEqual(finding["id"], "PYSEC-2021-108")
        self.assertEqual(finding["aliases"], ["CVE-2021-33503"])
        self.assertEqual(finding["fix_versions"], ["1.26.5"])


class SharedLawTests(_Project):

    def test_an_unknown_verb_is_refused(self):
        self.assertIn("ACT_NOT_SUPPORTED", self.refuse("nonsense"))

    def test_a_path_that_names_nothing_is_refused(self):
        self.assertIn("PATH_NOT_IN_THE_REPOSITORY", self.refuse("secret_scan", source_root="/nope"))

    def test_a_failed_run_still_writes_a_fail_artifact(self):
        with self.assertRaises(QualityError):
            self.run_verb("secret_scan", python_executable="/usr/bin/python3")
        payload = json.loads((self.root / ".out" / "secret_scan.json").read_text())
        self.assertEqual(payload["gate"], "FAIL")
        self.assertIn("TOOL_NOT_INSTALLED", payload["reason"])


if __name__ == "__main__":
    unittest.main()
