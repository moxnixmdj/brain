from __future__ import annotations

import pathlib
import sys
import tempfile
import textwrap
import unittest

from canonical.runtime.bound_capabilities import python_interprocedural_value_provenance_v1 as prov


class InterproceduralValueProvenanceV1Tests(unittest.TestCase):
    def fixture(self, files):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        for name, body in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(body))
        return td, root

    def runp(self, root, tests):
        return prov.run({
            "source_root": ".",
            "test_paths": tests,
            "output_path": "out.json",
            "timeout_s": 5,
            "max_trace_events": 10000,
            "max_ranked_lines": 40,
            "max_ranked_symbols": 20,
        }, root)

    def base_files(self):
        return {
            "producer.py": """
                def produce(x):
                    return x + 1
            """,
            "consumer.py": """
                def consume(v):
                    return v * 2
            """,
            "pipeline.py": """
                from producer import produce
                from consumer import consume
                def pipeline(x):
                    y = produce(x)
                    return consume(y)
            """,
            "test_bad.py": """
                from pipeline import pipeline
                assert pipeline(2) == 999
            """,
            "test_good.py": """
                from pipeline import pipeline
                assert pipeline(1) == 4
            """,
        }

    def test_cross_module_direct_value_flow_is_activated_and_runtime_corroborated(self):
        td, root = self.fixture(self.base_files())
        with td:
            out = self.runp(root, ["test_bad.py", "test_good.py"])
            self.assertTrue(out["pass"], out)
            flows = out["activated_flows"]
            self.assertEqual(len(flows), 1)
            f = flows[0]
            self.assertEqual(f["producer"], "producer:produce")
            self.assertEqual(f["caller"], "pipeline:pipeline")
            self.assertEqual(f["consumer"], "consumer:consume")
            self.assertEqual(f["variable"], "y")
            self.assertEqual(f["consumer_param"], "v")
            self.assertTrue(f["runtime"]["corroborated_on_failing_test"])

    def test_provenance_expands_dynamic_repair_region_across_functions(self):
        td, root = self.fixture(self.base_files())
        with td:
            out = self.runp(root, ["test_bad.py", "test_good.py"])
            region = {(x["path"], x["symbol"]) for x in out["repair_region"]}
            self.assertIn(("pipeline.py", "pipeline"), region)
            self.assertTrue(
                ("producer.py", "produce") in region or ("consumer.py", "consume") in region,
                region,
            )
            self.assertGreaterEqual(len(out["provenance_hypotheses"]), 1)

    def test_complex_nested_call_is_not_overclaimed(self):
        files = self.base_files()
        files["pipeline.py"] = """
            from producer import produce
            from consumer import consume
            def pipeline(x):
                return consume(produce(x))
        """
        td, root = self.fixture(files)
        with td:
            out = self.runp(root, ["test_bad.py", "test_good.py"])
            self.assertFalse(out["pass"])
            self.assertEqual(out["activated_flow_count"], 0)
            self.assertEqual(out["status"], "OPEN__NO_ACTIVATED_DIRECT_VALUE_FLOW")

    def test_star_import_is_not_resolved(self):
        files = self.base_files()
        files["pipeline.py"] = """
            from producer import *
            from consumer import consume
            def pipeline(x):
                y = produce(x)
                return consume(y)
        """
        td, root = self.fixture(files)
        with td:
            out = self.runp(root, ["test_bad.py", "test_good.py"])
            self.assertFalse(out["pass"])
            self.assertEqual(out["activated_flow_count"], 0)

    def test_deterministic_and_read_only(self):
        td, root = self.fixture(self.base_files())
        with td:
            before = {
                p.relative_to(root).as_posix(): p.read_bytes()
                for p in root.glob("*.py")
            }
            a = self.runp(root, ["test_bad.py", "test_good.py"])
            b = self.runp(root, ["test_bad.py", "test_good.py"])
            self.assertEqual(a["activated_flows"], b["activated_flows"])
            self.assertEqual(a["repair_region"], b["repair_region"])
            for name, raw in before.items():
                self.assertEqual((root / name).read_bytes(), raw)
            self.assertEqual(a["source_mutation_count"], 0)
            self.assertTrue(a["source_restored"])

    def test_zero_external_cognition_and_zero_spend(self):
        td, root = self.fixture(self.base_files())
        with td:
            out = self.runp(root, ["test_bad.py", "test_good.py"])
            self.assertEqual(out["model_dependency_count"], 0)
            self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"], 0)
            self.assertEqual(out["external_capability_provider_count"], 0)
            self.assertEqual(out["incremental_spend_usd"], 0)

    def test_no_failing_test_fails_closed(self):
        files = self.base_files()
        files["test_bad.py"] = "from pipeline import pipeline\nassert pipeline(2) == 6\n"
        td, root = self.fixture(files)
        with td:
            with self.assertRaisesRegex(prov.ProvenanceError, "NO_FAILING_TEST"):
                self.runp(root, ["test_bad.py", "test_good.py"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
