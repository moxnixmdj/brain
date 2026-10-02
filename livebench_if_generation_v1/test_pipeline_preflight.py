"""End-to-end pre-flight of the whole pipeline except the LLM, on the 300 public IFBench dev prompts.

Skipped unless ALL of these are set (they point at checkouts the project already pins elsewhere):
  LIVEBENCH_ROOT      LiveBench/LiveBench at commit 8f8e5c381a16e3f24257776edd53471fe86f8091
  IFBENCH_TEST_JSONL  allenai/IFBench data/IFBench_test.jsonl (sha256 pinned below; data license ODC-BY-1.0)
  NLTK_REAL_DIR       the project's pinned nltk_data artifacts, unzipped (punkt, punkt_tab, stopwords, taggers)

A local mock stands in for the LLM and returns a fixed placeholder. Everything else is real: the
conversion, the generation kit (budget cap, frozen policy, provenance), the repo's verified response
adapter and ID-set preflight, and LiveBench's own scorer with all 58 checkers. The point is that a
real run later fails only because of the model, never because of plumbing.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from livebench_if_generation_v1 import generate_responses as gr
from livebench_if_generation_v1 import ifbench_to_questions as conv
from livebench_if_generation_v1 import score_livebench_if as sc

LIVEBENCH_ROOT = os.environ.get("LIVEBENCH_ROOT")
IFBENCH_JSONL = os.environ.get("IFBENCH_TEST_JSONL")
NLTK_DIR = os.environ.get("NLTK_REAL_DIR")
IFBENCH_SHA256 = "d2ada7da94a38cfe406351614c4e686846ed2da6d1b339db95fa5ead19554a4a"
PLACEHOLDER = b"This is a placeholder response that makes no attempt to satisfy any constraint."
READY = bool(LIVEBENCH_ROOT and IFBENCH_JSONL and NLTK_DIR and Path(LIVEBENCH_ROOT, "livebench").is_dir()
             and Path(IFBENCH_JSONL).is_file() and Path(NLTK_DIR, "tokenizers", "punkt").is_dir())


def _purge():
    for name in [n for n in sys.modules if n == "livebench" or n.startswith("livebench.")]:
        del sys.modules[name]


@unittest.skipUnless(READY, "set LIVEBENCH_ROOT, IFBENCH_TEST_JSONL and NLTK_REAL_DIR to run the end-to-end pre-flight")
class PipelinePreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(Path(IFBENCH_JSONL).read_bytes()).hexdigest() != IFBENCH_SHA256:
            raise unittest.SkipTest("IFBench_test.jsonl is not the pinned version")
        _purge()
        cls._path, cls._env = list(sys.path), os.environ.get("NLTK_DATA")
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        stub = tmp / "stubs" / "spacy"
        stub.mkdir(parents=True)
        (stub / "__init__.py").write_text("class _U:\n    @staticmethod\n    def is_package(n):\n        return True\nutil = _U()\n")
        (stub / "cli.py").write_text("def download(*a, **k):\n    raise RuntimeError('no downloads')\n")
        os.environ["NLTK_DATA"] = NLTK_DIR
        import nltk

        cls._nltk_paths, cls._download = list(nltk.data.path), nltk.download
        nltk.data.path.insert(0, NLTK_DIR)
        sys.path.insert(0, str(tmp / "stubs"))
        cls.utils, cls.lib = sc.load_upstream(Path(LIVEBENCH_ROOT))

        rows = [json.loads(x) for x in Path(IFBENCH_JSONL).read_text(encoding="utf-8").splitlines() if x.strip()]
        cls.questions = conv.convert(rows)
        cls.qpath = tmp / "dev_questions.jsonl"
        cls.qpath.write_text("\n".join(json.dumps(q) for q in cls.questions) + "\n")
        cls.cfg = tmp / "cfg.json"
        cls.cfg.write_text(json.dumps({"config_id": "PREFLIGHT_DUMMY", "system_prompt": None, "max_completion_tokens": 256}))

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(PLACEHOLDER)

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{cls.server.server_address[1]}/"
        cls.out = tmp / "gen"
        cls.summary = gr.run(questions_path=cls.qpath, config_path=cls.cfg, out_dir=cls.out, model_id="mock", transport=gr.PlainTransport(url),
                             max_total_tokens=50_000_000, assert_no_frozen_questions=True, sleep=lambda s: None)
        cls.answers = json.loads((cls.out / "model_answers.json").read_text())
        cls.scores = sc.score_run(sc.load_questions(cls.qpath), cls.answers, "brain", cls.utils, cls.lib)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import nltk

        nltk.download = cls._download
        nltk.data.path[:] = [p for p in cls._nltk_paths if p != NLTK_DIR]
        sys.path[:] = cls._path
        if cls._env is None:
            os.environ.pop("NLTK_DATA", None)
        else:
            os.environ["NLTK_DATA"] = cls._env
        _purge()
        cls.tmp.cleanup()

    def test_dev_set_shape_and_checker_coverage(self):
        from livebench.if_runner.ifbench import instructions_registry as reg

        self.assertEqual(len(self.questions), 300)
        used = {i for q in self.questions for i in q["instruction_id_list"]}
        self.assertEqual(used, set(reg.INSTRUCTION_DICT), "the dev prompts must exercise every one of the 58 checkers")

    def test_generation_adapter_and_provenance(self):
        s = self.summary
        self.assertEqual((s["status"], s["answered"], s["calls_made_this_run"]), ("COMPLETE", 300, 300))
        self.assertTrue(s["provenance_chain_ok"])
        self.assertEqual(s["adapter_preflight"], {"status": "PASS", "count": 300, "content_inspected": False})
        self.assertEqual(s["frozen"]["policy"], "ASSERTED_NO_FROZEN_QUESTIONS")
        self.assertEqual(set(self.answers["brain"]), {q["question_id"] for q in self.questions})

    def test_every_checker_runs_with_no_scorer_exception(self):
        self.assertEqual(self.scores["scorer_exceptions"], {"count": 0, "by_type": {}, "question_ids": []})

    def test_scoring_is_hermetic_deterministic_and_sane(self):
        import nltk

        self.assertIn("_download", nltk.download.__name__)  # the fail-closed local-presence check, never the network
        again = sc.score_run(sc.load_questions(self.qpath), self.answers, "brain", self.utils, self.lib)
        self.assertEqual(again["per_question"], self.scores["per_question"])
        score = self.scores["leaderboard_style_category_score"]
        self.assertTrue(0 < score < 40, f"a placeholder response must score low but not zero, got {score}")
        d = self.scores["diagnostics_not_the_leaderboard_metric"]
        self.assertLessEqual(d["prompt_level_strict_accuracy"], self.scores["question_mean_score"] + 1e-9)
        self.assertLessEqual(self.scores["question_mean_score"], d["instruction_level_strict_accuracy"] + 1e-9)

    def test_no_prompt_text_in_any_stored_output(self):
        needle = self.questions[0]["turns"][0][:60]
        for name in ("provenance.jsonl", "ledger.json", "summary.json", "responses.jsonl"):
            self.assertNotIn(needle, (self.out / name).read_text(), name)
        self.assertNotIn(needle, json.dumps(self.scores))


if __name__ == "__main__":
    unittest.main()
