from __future__ import annotations

import unittest

from canonical.runtime import root3_read_only_apt_legacy_executor_v1 as apt
from canonical.runtime import root3_read_only_declared_query_executor_v2 as full


def ctx(line, argv, timeout):
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


class ReadOnlyDeclaredQueryV2StaticTests(unittest.TestCase):
    def test_exact_current_eight_site_partition(self):
        c = full.coverage()
        self.assertEqual(c["current_site_count"], 8)
        self.assertEqual(c["local_file_site_count"], 5)
        self.assertEqual(c["apt_legacy_site_count"], 3)
        self.assertEqual(c["bound_site_count"], 8)
        self.assertTrue(c["complete"])

    def test_exact_apt_profiles_are_admitted(self):
        self.assertEqual(apt._call(ctx(267, ["apt-cache", "search", "jq"], 20))[2], "APT_SEARCH")
        self.assertEqual(apt._call(ctx(359, ["apt-cache", "policy", "jq"], 10))[2], "APT_POLICY")
        self.assertEqual(apt._call(ctx(368, ["apt-cache", "show", "jq=1.8.1-4ubuntu2"], 15))[2], "APT_SHOW")

    def test_profile_swap_fails_closed(self):
        with self.assertRaisesRegex(apt.AptLegacyDenied, "APT_SEARCH_SHAPE_INVALID"):
            apt._call(ctx(267, ["apt-cache", "policy", "jq"], 20))

    def test_generated_carrier_has_private_network_namespace(self):
        argv = apt._outer_command("/tmp/unused", ["apt-cache", "search", "jq"], 20)
        self.assertIn("--net", argv)
        self.assertIn("--pid", argv)
        self.assertIn("--mount", argv)

    def test_metadata_mounts_are_read_only(self):
        self.assertIn("remount,bind,ro,nosuid,nodev,noexec", apt._SETUP)
        for p in ("/etc/apt", "/etc/dpkg", "/var/lib/apt", "/var/lib/dpkg", "/var/cache/apt"):
            self.assertIn(p, apt._SETUP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
