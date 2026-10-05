import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "runtime" / "domain_behavior_universe_anchor_v1.py"

class DomainBehaviorUniverseAnchorTests(unittest.TestCase):
    def load_module(self):
        if not MODULE.exists():
            self.fail("anchor module missing")
        spec = importlib.util.spec_from_file_location("anchor", MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_exact_five_domain_frontier_and_fail_closed_status(self):
        mod = self.load_module()
        out = mod.compile_anchor()
        self.assertEqual(out["domain_count"], 5)
        self.assertEqual(out["closed_domain_count"], 0)
        self.assertEqual(out["status"], "PASS__AUTHORITATIVE_SOURCE_ANCHOR_BOUND__ALL_DOMAIN_CLOSURE_REMAINS_FAIL_CLOSED")

    def test_missing_authoritative_source_rejected(self):
        mod = self.load_module()
        manifest = mod.default_manifest()
        manifest["sources"] = []
        with self.assertRaisesRegex(mod.AnchorError, "AUTHORITATIVE_SOURCE_SET_EMPTY"):
            mod.validate_manifest(manifest)

    def test_domain_cannot_close_from_domain_label_or_source_mention_alone(self):
        mod = self.load_module()
        manifest = mod.default_manifest()
        manifest["domains"]["CYBERSECURITY"]["state"] = "CLOSED"
        with self.assertRaisesRegex(mod.AnchorError, "UNSOUND_DOMAIN_CLOSURE"):
            mod.validate_manifest(manifest)

    def test_unknown_leaf_is_preserved_not_silently_deleted(self):
        mod = self.load_module()
        manifest = mod.default_manifest()
        manifest["domains"]["HEALTHCARE"]["observed_surfaces"] = []
        out = mod.validate_manifest(manifest)
        self.assertIn("HEALTHCARE", out["source_incomplete_domains"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
