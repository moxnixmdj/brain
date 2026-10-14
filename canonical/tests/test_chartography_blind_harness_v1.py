import json
import os
import pathlib
import tempfile
import unittest

from canonical.runtime import chartography_blind_harness_v1 as h


def _write_pack(root: pathlib.Path, rows: list[dict]) -> pathlib.Path:
    pack = root / "pack"
    (pack / "images").mkdir(parents=True)
    with open(pack / "tasks.jsonl", "w", encoding="utf-8") as out:
        for i, r in enumerate(rows):
            img = pack / "images" / f"{i:04d}.png"
            img.write_bytes(b"\x89PNG-fake-" + str(i).encode())
            out.write(json.dumps({**r, "__image_file": f"images/{img.name}", "__row_index": i}) + "\n")
    return pack


ROWS = [
    {"id": "t1", "question": "How long until the 25 degC / 0.03 K/m line reaches 1500 metres?", "answer": "78.5 years", "accepted_range": [76, 79]},
    {"id": "t2", "question": "What is the value of revenue in 2021?", "answer": 42.0},
    {"id": "t3", "question": "Which region has the highest share?", "answer": "Europe"},
    {"id": "t4", "question": "What is the CAGR of sales between 2015 and 2020?", "answer": 7.1},
]


class ChartographyBlindHarnessTests(unittest.TestCase):
    def test_views_hold_out_everything_except_id_image_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            pack = _write_pack(root, ROWS)
            m = h.build_views(pack, root / "views")
            self.assertEqual(m["task_count"], 4)
            self.assertEqual(set(m["held_out_columns"]), {"answer", "accepted_range"})
            self.assertTrue(m["leakage_check"]["pass"])
            tasks = [json.loads(l) for l in (root / "views/solver_view/tasks.jsonl").read_text().splitlines()]
            self.assertTrue(all(set(t) == {"id", "image", "prompt"} for t in tasks))
            self.assertNotIn("Europe", (root / "views/solver_view/tasks.jsonl").read_text())

    def test_fail_closed_without_answer_like_column(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            pack = _write_pack(root, [{"id": "x", "question": "q", "notes": "n"}])
            with self.assertRaises(SystemExit):
                h.build_views(pack, root / "views")

    def test_run_and_score_with_in_process_stub(self):
        answers = {"t1": 78.52, "t2": 43.0, "t3": "europe", "t4": None}

        def stub(image: pathlib.Path, prompt: str):
            tid = image.stem
            key = {"0000": "t1", "0001": "t2", "0002": "t3", "0003": "t4"}[tid]
            v = answers[key]
            if v is None:
                return {"status": "ABSTAIN__UNSUPPORTED", "answer": None, "raw_value": None}
            return {"status": "PASS", "route": "STUB", "answer": str(v), "raw_value": v if isinstance(v, float) else None}

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            pack = _write_pack(root, ROWS)
            h.build_views(pack, root / "views")
            info = h.run_solver(root / "views", root / "results.jsonl", solver=stub)
            self.assertTrue(info["scorer_view_sealed_during_run"])
            self.assertEqual(oct(os.stat(root / "views/scorer_view").st_mode & 0o777), "0o700")
            rec = h.score(root / "results.jsonl", root / "views")
            by = {r["id"]: r for r in rec["per_task"]}
            self.assertTrue(by["t1"]["pass"])            # inside explicit range
            self.assertTrue(by["t2"]["pass"])            # 43 vs 42 within 5 % assumed tolerance
            self.assertTrue(by["t3"]["pass"])            # normalized exact match
            self.assertFalse(by["t4"]["pass"]); self.assertFalse(by["t4"]["attempted"])
            self.assertEqual((rec["attempted"], rec["abstained"], rec["passed"]), (3, 1, 3))
            self.assertEqual(rec["score_percent"], 75.0)
            self.assertFalse(rec["meets_target_under_assumed_semantics"])
            self.assertIn("ASSUMED", rec["scorer_semantics_label"])
            self.assertFalse(rec["gold_values_in_receipt"])
            self.assertNotIn("Europe", json.dumps(rec))
            self.assertEqual(rec["taxonomy_census"]["CAGR"]["tasks"], 1)
            self.assertEqual(rec["accounting"]["terminal_credit_delta"], 0)

    def test_question_classifier(self):
        cases = {
            "What is the CAGR of sales?": "CAGR",
            "By what percent did exports increase?": "PERCENT_CHANGE",
            "What is the ratio of A to B?": "RATIO",
            "What is the difference between 2019 and 2020?": "DIFFERENCE",
            "Which year had the highest value?": "EXTREMA",
            "What is the total of all bars?": "AGGREGATE",
            "How long until the line reaches 1500 metres?": "THRESHOLD_INTERSECTION",
            "What is the value of revenue in 2021?": "LOOKUP",
            "Describe the chart.": "UNCLASSIFIED",
        }
        for prompt, expected in cases.items():
            self.assertEqual(h.classify_question(prompt), expected, prompt)

    def test_scrubbed_env_drops_secrets(self):
        os.environ["HF_TOKEN"] = "x"
        os.environ["SOME_API_KEY"] = "y"
        try:
            env = h._scrubbed_env()
            self.assertNotIn("HF_TOKEN", env)
            self.assertNotIn("SOME_API_KEY", env)
            self.assertEqual(env["CHARTOGRAPHY_BLIND_MODE"], "1")
        finally:
            del os.environ["HF_TOKEN"], os.environ["SOME_API_KEY"]


if __name__ == "__main__":
    unittest.main()
