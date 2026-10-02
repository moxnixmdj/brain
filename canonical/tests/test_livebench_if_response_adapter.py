import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.livebench_if_response_adapter import (
    AdapterError,
    PINNED_IFBENCH_COMMIT,
    adapt_records,
    write_jsonl,
)


class LiveBenchIFAdapterTests(unittest.TestCase):
    def test_pinned_upstream_commit(self):
        self.assertEqual(PINNED_IFBENCH_COMMIT, "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d")

    def test_exact_prompt_and_response_preserved(self):
        rows = adapt_records([{"prompt": "  keep whitespace  ", "response": "answer"}])
        self.assertEqual(rows, [{"prompt": "  keep whitespace  ", "response": "answer"}])

    def test_duplicate_prompt_fails_closed(self):
        with self.assertRaises(AdapterError):
            adapt_records([
                {"prompt": "p", "response": "a"},
                {"prompt": "p", "response": "b"},
            ])

    def test_missing_or_invalid_fields_fail_closed(self):
        bad = [
            {},
            {"prompt": "", "response": "x"},
            {"prompt": "p"},
            {"prompt": "p", "response": 3},
        ]
        for record in bad:
            with self.subTest(record=record):
                with self.assertRaises(AdapterError):
                    adapt_records([record])

    def test_jsonl_schema_is_only_prompt_response(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "responses.jsonl"
            write_jsonl([{"prompt": "p", "response": "r", "ignored": "x"}], out)
            row = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(row, {"prompt": "p", "response": "r"})


if __name__ == "__main__":
    unittest.main()
