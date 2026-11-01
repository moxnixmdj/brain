from __future__ import annotations
import pathlib
import subprocess
import unittest

from canonical.runtime import capability_discovery as discovery
from canonical.runtime import root3_read_only_declared_query_executor_v2 as ro
from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED


class ReadOnlyDeclaredQueryExecutorV2Tests(unittest.TestCase):
    def tearDown(self):
        try:
            mediator.uninstall()
        except Exception:
            subprocess.run = mediator._ORIGINAL_RUN
            subprocess.Popen = mediator._ORIGINAL_POPEN
            mediator._AUTHORIZER = None
            mediator._AUTHORITY_ID = None
            mediator._CLASS_EXECUTORS = {}
            mediator._INSTALLED = False

    def allow(self, request):
        return {"allowed": True, "authorization_sha256": "a" * 64}

    def test_supported_set_is_exact_current_read_only_class(self):
        # 2026-11-01: re-measured on the current tree. The executor supports
        # the four current file-query sites (current line numbers; the legacy
        # sqlite_verify_cli.py:66 site was discharged to in-process sqlite3)
        # plus the three apt-cache discovery profiles. Every file-query entry
        # must normalize to a legacy READ_ONLY_DECLARED_QUERY key.
        from canonical.runtime.root3_subprocess_effect_class_registry_v2 import _norm_key
        file_query = {
            ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py", 53, "subprocess.run"),
            ("canonical/runtime/bound_capabilities/jq_query.py", 41, "subprocess.run"),
            ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py", 44, "subprocess.run"),
            ("canonical/runtime/bound_capabilities/yq_yaml_json.py", 23, "subprocess.run"),
        }
        apt = {
            ("canonical/runtime/capability_discovery.py", 267, "subprocess.run"),
            ("canonical/runtime/capability_discovery.py", 359, "subprocess.run"),
            ("canonical/runtime/capability_discovery.py", 368, "subprocess.run"),
        }
        self.assertEqual(set(ro.APT_SUPPORTED), apt)
        self.assertEqual(set(ro.SUPPORTED) - apt, file_query)
        legacy_ro = {k for k, v in EXPECTED.items() if v == "READ_ONLY_DECLARED_QUERY"}
        for key in file_query:
            self.assertIn(_norm_key(*key), legacy_ro)

    def _ctx(self, line, argv, timeout):
        return {
            "effect_class": "READ_ONLY_DECLARED_QUERY",
            "callsite": {
                "module_path": "canonical/runtime/capability_discovery.py",
                "lineno": line,
                "process_api": "subprocess.run",
            },
            "args": (argv,),
            "kwargs": {"text": True, "capture_output": True, "timeout": timeout},
        }

    def test_apt_query_regex_metacharacters_deny_before_snapshot(self):
        with self.assertRaisesRegex(ro.ReadOnlyQueryDenied, "SEARCH_SHAPE_OR_QUERY_INVALID"):
            ro._prepare_apt(self._ctx(267, ["apt-cache","search","json.*"], 20))

    def test_apt_policy_option_injection_denies(self):
        with self.assertRaisesRegex(ro.ReadOnlyQueryDenied, "POLICY_SHAPE_OR_PACKAGE_INVALID"):
            ro._prepare_apt(self._ctx(359, ["apt-cache","policy","-o"], 10))

    def test_apt_show_selector_injection_denies(self):
        with self.assertRaisesRegex(ro.ReadOnlyQueryDenied, "SHOW_PACKAGE_OR_VERSION_INVALID"):
            ro._prepare_apt(self._ctx(368, ["apt-cache","show","bash=1;id"], 15))

    @unittest.skipUnless(pathlib.Path("/var/lib/apt/lists").is_dir() and pathlib.Path("/usr/bin/apt-cache").exists(), "APT unavailable")
    def test_confined_search_matches_host(self):
        direct = mediator._ORIGINAL_RUN(["apt-cache","search","json"], text=True, capture_output=True, timeout=20)
        ex = ro.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
        got = ex(self._ctx(267, ["apt-cache","search","json"], 20))
        self.assertEqual(got.returncode, direct.returncode)
        self.assertEqual(got.stdout, direct.stdout)

    @unittest.skipUnless(pathlib.Path("/var/lib/apt/lists").is_dir() and pathlib.Path("/usr/bin/apt-cache").exists(), "APT unavailable")
    def test_confined_policy_and_show_match_host(self):
        direct_policy = mediator._ORIGINAL_RUN(["apt-cache","policy","bash"], text=True, capture_output=True, timeout=10)
        ex = ro.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
        got_policy = ex(self._ctx(359, ["apt-cache","policy","bash"], 10))
        self.assertEqual(got_policy.returncode, direct_policy.returncode)
        self.assertEqual(got_policy.stdout, direct_policy.stdout)
        version = None
        for line in direct_policy.stdout.splitlines():
            if line.strip().startswith("Candidate:"):
                version = line.split(":",1)[1].strip()
                break
        self.assertTrue(version and version != "(none)")
        direct_show = mediator._ORIGINAL_RUN(["apt-cache","show","bash="+version], text=True, capture_output=True, timeout=15)
        got_show = ex(self._ctx(368, ["apt-cache","show","bash="+version], 15))
        self.assertEqual(got_show.returncode, direct_show.returncode)
        self.assertEqual(got_show.stdout, direct_show.stdout)

    @unittest.skipUnless(pathlib.Path("/var/lib/apt/lists").is_dir() and pathlib.Path("/usr/bin/apt-cache").exists(), "APT unavailable")
    def test_legacy_discovery_result_identical_through_mediator(self):
        direct = discovery._legacy_search_apt_packages("json data", limit=3)
        ex = ro.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
        mediator.install(
            self.allow,
            authority_id="TEST",
            class_executors={"READ_ONLY_DECLARED_QUERY": ex},
        )
        mediated = discovery._legacy_search_apt_packages("json data", limit=3)
        self.assertEqual(mediated, direct)

    @unittest.skipUnless(pathlib.Path("/var/lib/apt/lists").is_dir() and pathlib.Path("/usr/bin/apt-cache").exists(), "APT unavailable")
    def test_current_full_catalog_search_fits_existing_broker_cap_after_base64(self):
        p = mediator._ORIGINAL_RUN(["apt-cache","search","."], capture_output=True, timeout=60)
        self.assertEqual(p.returncode, 0)
        encoded_upper = 4 * ((len(p.stdout) + 2) // 3)
        self.assertLess(encoded_upper + 4096, 8_000_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
