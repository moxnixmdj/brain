"""Tests for the IFBench-to-questions converter (pure stdlib; no external data needed)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from livebench_if_generation_v1 import ifbench_to_questions as conv


def row(key=0, ids=("count:word_count_range",), kwargs=({"min_words": 3, "max_words": 6},), prompt="Write a poem."):
    return {"key": key, "prompt": prompt, "instruction_id_list": list(ids), "kwargs": list(kwargs)}


class Converter(unittest.TestCase):
    def test_field_mapping_and_ids(self):
        out = conv.convert([row(0), row(7, ids=("a:b", "c:d"), kwargs=({}, {"N": 3}))])
        self.assertEqual([q["question_id"] for q in out], ["ifbench-0", "ifbench-7"])
        self.assertEqual(out[0]["turns"], ["Write a poem."])
        self.assertEqual(out[1]["instruction_id_list"], ["a:b", "c:d"])
        self.assertEqual(out[1]["kwargs"], [{}, {"N": 3}])
        self.assertTrue(all(q["task"] == "ifbench_test" for q in out))
        self.assertNotIn("livebench_release_date", out[0])  # dev rows carry no release: frozen policy must be asserted explicitly

    def test_invalid_rows_are_rejected(self):
        bad = {
            "missing field": [{k: v for k, v in row().items() if k != "kwargs"}],
            "duplicate key": [row(1), row(1)],
            "length mismatch": [row(ids=("a:b", "c:d"), kwargs=({},))],
            "empty instructions": [row(ids=(), kwargs=())],
            "empty prompt": [row(prompt="  ")],
            "kwargs not a list": [{**row(), "kwargs": {"a": 1}}],
        }
        for label, rows in bad.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                conv.convert(rows)

    def test_cli_round_trip_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as t:
            src, dst = Path(t) / "in.jsonl", Path(t) / "out.jsonl"
            src.write_text("\n".join(json.dumps(r) for r in (row(0), row(1))) + "\n")
            self.assertEqual(conv.main(["--input", str(src), "--output", str(dst)]), 0)
            self.assertEqual(len(dst.read_text().splitlines()), 2)
            src.write_text(json.dumps(row(1)) + "\n" + json.dumps(row(1)) + "\n")
            self.assertEqual(conv.main(["--input", str(src), "--output", str(dst)]), 2)

    def test_converted_rows_load_in_the_generation_kit_and_the_scorer(self):
        from livebench_if_generation_v1 import generate_responses as gr, score_livebench_if as sc

        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "q.jsonl"
            p.write_text("\n".join(json.dumps(q) for q in conv.convert([row(0), row(1)])) + "\n")
            qs = gr.load_questions(p)  # prompt comes from turns[0]; release is None
            self.assertEqual([q["prompt"] for q in qs], ["Write a poem.", "Write a poem."])
            self.assertEqual([q["release"] for q in qs], [None, None])
            self.assertEqual(len(sc.load_questions(p)), 2)


if __name__ == "__main__":
    unittest.main()
