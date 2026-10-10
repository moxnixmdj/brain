import json
import struct
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.chartography_synthetic_reasoning_suite_v1 import EXPECTED, generate_suite, verify_generated


class ChartographySyntheticReasoningSuiteTests(unittest.TestCase):
    def test_exact_six_case_suite_recomputes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            manifest=generate_suite(root)
            out=verify_generated(manifest)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["case_count"],6)
            self.assertEqual(out["distinct_skill_count"],6)
            self.assertEqual(out["terminal_cases_consumed"],0)
            self.assertEqual(out["judge_calls"],0)
            for row in manifest:
                expected,sha=EXPECTED[row["case_id"]]
                self.assertEqual(row["expected"],expected)
                self.assertEqual(row["sha256"],sha)
                data=(root/row["file"]).read_bytes()
                self.assertEqual(data[:2],b"BM")
                width,height=struct.unpack_from("<II",data,18)
                self.assertEqual((width,height),(256,192))

    def test_hash_mutation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            manifest=generate_suite(Path(td))
            bad=json.loads(json.dumps(manifest))
            bad[0]["sha256"]="0"*64
            out=verify_generated(bad)
            self.assertFalse(out["pass"])
            self.assertIn("HASH_DRIFT:1",out["errors"])

    def test_suite_source_has_no_external_dataset_or_model_judge(self):
        source=(Path(__file__).resolve().parents[1]/"runtime"/"chartography_synthetic_reasoning_suite_v1.py").read_text()
        for forbidden in ("requests", "huggingface", "ChartQA", "PlotQA", "gemini", "openai", "anthropic"):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main(verbosity=2)
