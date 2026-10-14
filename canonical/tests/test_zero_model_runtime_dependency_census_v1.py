import json
import pathlib
import tempfile
import unittest

from canonical.runtime import zero_model_runtime_dependency_census_v1 as census


class ZeroModelCensusTests(unittest.TestCase):
    def _run(self, files: dict[str, str]) -> dict:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for rel, body in files.items():
                p = root / "surf" / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            return census.run_census(root, ["surf"])

    def test_clean_surface_exits_zero(self):
        out = self._run({"a.py": "import json\nprint(json.dumps({}))\n"})
        self.assertEqual(out["model_dependent_file_count"], 0)
        self.assertEqual(out["classification_counts"], {"CLEAN": 1})
        self.assertEqual(out["accounting"]["terminal_credit_delta"], 0)

    def test_import_level_dependency_is_flagged(self):
        out = self._run({"a.py": "from openai import OpenAI\n"})
        self.assertEqual(out["model_dependent_files"][0]["classification"], "IMPORT_LEVEL_MODEL_DEPENDENCY")

    def test_call_level_dependency_is_flagged(self):
        out = self._run({"a.py": "URL = 'http://127.0.0.1:8080/v1/chat/completions'\n"})
        self.assertEqual(out["model_dependent_files"][0]["classification"], "CALL_LEVEL_MODEL_DEPENDENCY")

    def test_identifier_level_dependency_is_flagged(self):
        out = self._run({"a.py": "LLAMA_CPP_REVISION = 'abc'\nclass QwenPlanner:\n    doc = 'Qwen planner'\n"})
        self.assertEqual(out["model_dependent_files"][0]["classification"], "IDENTIFIER_LEVEL_MODEL_DEPENDENCY")

    def test_string_reference_only_is_not_dependent(self):
        out = self._run({"a.py": "TASK = 'vllm-deepseek-streaming verifier fixture'\n"})
        self.assertEqual(out["model_dependent_file_count"], 0)
        self.assertEqual(out["classification_counts"], {"STRING_REFERENCE_ONLY": 1})

    def test_parse_error_and_missing_surface_fail_closed(self):
        out = self._run({"a.py": "def broken(:\n"})
        self.assertEqual(out["model_dependent_files"][0]["classification"], "PARSE_ERROR_FAILS_CLOSED")
        with tempfile.TemporaryDirectory() as td:
            out2 = census.run_census(pathlib.Path(td), ["does_not_exist"])
        self.assertEqual(out2["model_dependent_file_count"], 1)

    def test_committed_receipt_matches_live_census_shape(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        receipt = json.loads((root / "canonical/verification/ZERO_MODEL_RUNTIME_DEPENDENCY_CENSUS_RECEIPT_20261014_V1.json").read_text())
        self.assertEqual(receipt["census"]["schema"], census.SCHEMA)
        self.assertGreater(receipt["census"]["model_dependent_file_count"], 0)
        self.assertEqual(receipt["accounting"]["terminal_credit_delta"], 0)
        self.assertIn("F1_CENTRAL_RUNTIME_RETAINS_GENERAL_MODEL_PLANNER_CODE_PATH", [f["id"] for f in receipt["material_findings"]])


if __name__ == "__main__":
    unittest.main()
