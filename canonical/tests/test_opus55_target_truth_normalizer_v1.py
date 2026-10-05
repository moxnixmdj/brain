import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "runtime" / "opus55_target_truth_normalizer_v1.py"


class TargetTruthNormalizerTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location("target_truth", MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def row(self, **kw):
        base = {
            "benchmark": "B",
            "benchmark_version": "1",
            "model": "Claude Opus 5.5",
            "effort": "max",
            "evaluator": "Owner",
            "harness": "H1",
            "fallback_policy": "default",
            "score": 10.0,
            "unit": "percent",
            "observed_at": "2026-10-01T00:00:00Z",
            "authority": "BENCHMARK_OWNER",
            "source_url": "https://example.com/a",
        }
        base.update(kw)
        return base

    def test_newer_same_tuple_supersedes_older(self):
        m = self.load()
        old = self.row(score=10, observed_at="2026-10-01T00:00:00Z")
        new = self.row(score=11, observed_at="2026-10-02T00:00:00Z", source_url="https://example.com/b")
        out = m.normalize([old, new])
        self.assertEqual(out["status"], "PASS__EXACT_TARGET_TUPLES_BOUND__NO_CROSS_CONFIGURATION_MERGE")
        self.assertEqual(out["selected"][0]["score"], 11)

    def test_different_effort_is_incomparable_not_overwrite(self):
        m = self.load()
        a = self.row(score=10, effort="xhigh")
        b = self.row(score=20, effort="max", source_url="https://example.com/b")
        out = m.normalize([a, b])
        self.assertEqual(out["exact_tuple_count"], 2)
        self.assertEqual(len(out["incomparable_benchmarks"]), 1)

    def test_different_evaluator_is_incomparable_not_overwrite(self):
        m = self.load()
        a = self.row(score=10, evaluator="Provider")
        b = self.row(score=20, evaluator="Independent", source_url="https://example.com/b")
        out = m.normalize([a, b])
        self.assertEqual(out["exact_tuple_count"], 2)
        self.assertEqual(len(out["incomparable_benchmarks"]), 1)

    def test_same_tuple_same_time_conflict_fails_closed(self):
        m = self.load()
        a = self.row(score=10, source_url="https://example.com/a")
        b = self.row(score=20, source_url="https://example.com/b")
        out = m.normalize([a, b])
        self.assertTrue(out["status"].startswith("FAIL_CLOSED"))

    def test_legacy_rebind_requires_exact_tuple(self):
        m = self.load()
        current = self.row(score=20, evaluator="Independent")
        out = m.normalize([current])
        legacy = self.row(score=10, evaluator="Provider")
        verdict = m.compare_legacy_target(legacy, out)
        self.assertEqual(verdict["status"], "UNBOUND__NO_EXACT_CURRENT_TUPLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
