"""Tests for the LiveBench-IF scoring driver.

Layer A (always runs) uses a stub upstream to test plumbing: id checks, aggregation arithmetic,
commit pinning, and that no prompt or response text reaches the summary.

Layer B (runs only when LIVEBENCH_ROOT points at a checkout of LiveBench/LiveBench at the pinned
commit, with pandas, nltk, emoji, syllapy, langdetect, immutabledict and absl-py installed) calls
the REAL upstream scorer on synthetic questions built from three checkers that need no NLTK data
(words:no_consecutive, count:word_count_range, count:unique_word_count). It executes the facts
recorded in the public-bar receipt: the per-question score is the mean of "all followed" and
"fraction followed", the check is strict, <solution> tags are honoured, prompt-level accuracy never
exceeds the official score, and loose can differ from strict.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from livebench_if_generation_v1 import score_livebench_if as sc

LIVEBENCH_ROOT = os.environ.get("LIVEBENCH_ROOT")
SENTINEL = "SENTINEL-PROMPT-AND-RESPONSE-TEXT-MUST-NOT-LEAK"


def _purge():
    for name in [n for n in sys.modules if n == "livebench" or n.startswith("livebench.")]:
        del sys.modules[name]


STUB_UTILS = textwrap.dedent('''
    def ifbench_process_results(question, llm_answer, debug=False):
        # stub: all instructions followed iff the answer contains every keyword in kwargs[i]["kw"]
        flags = [kw.get("kw", "") in llm_answer for kw in question["kwargs"]]
        return ((1 if all(flags) else 0) + sum(flags) / len(flags)) / 2
''')
STUB_LIB = textwrap.dedent('''
    class InputExample:
        def __init__(self, key, instruction_id_list, prompt, kwargs):
            self.key, self.instruction_id_list, self.prompt, self.kwargs = key, instruction_id_list, prompt, kwargs

    class _Out:
        def __init__(self, flags):
            self.follow_instruction_list = flags
            self.follow_all_instructions = all(flags)

    def test_instruction_following_strict(inp, response):
        return _Out([kw.get("kw", "") in response for kw in inp.kwargs])

    def test_instruction_following_loose(inp, response):
        return _Out([kw.get("kw", "").lower() in response.lower() for kw in inp.kwargs])
''')


def make_stub_root(root: Path) -> None:
    for rel, body in (("livebench/__init__.py", ""), ("livebench/process_results/__init__.py", ""),
                      ("livebench/process_results/instruction_following/__init__.py", ""),
                      ("livebench/process_results/instruction_following/utils.py", STUB_UTILS),
                      ("livebench/if_runner/__init__.py", ""), ("livebench/if_runner/ifbench/__init__.py", ""),
                      ("livebench/if_runner/ifbench/evaluation_lib.py", STUB_LIB)):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)


def question(qid, kws, task="t1", prompt=None):
    return {"question_id": qid, "task": task, "turns": [prompt or f"{SENTINEL} <instructions>x</instructions>"],
            "instruction_id_list": [f"stub:{i}" for i in range(len(kws))], "kwargs": [{"kw": k} for k in kws]}


def answers(mapping, model_id="brain"):
    return {model_id: {qid: {"question_id": qid, "choices": [{"turns": [text]}]} for qid, text in mapping.items()}}


class StubLayer(unittest.TestCase):
    def setUp(self):
        _purge()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_stub_root(self.root)
        self._path = list(sys.path)
        self.utils, self.lib = sc.load_upstream(self.root, verify_commit=False)

    def tearDown(self):
        sys.path[:] = self._path
        _purge()
        self.tmp.cleanup()

    def test_leaderboard_style_aggregation_is_the_mean_of_task_means(self):
        qs = [question("a1", ["x"], "A"), question("a2", ["x"], "A"), question("a3", ["x"], "A"), question("b1", ["x"], "B")]
        ans = answers({"a1": "x", "a2": "nope", "a3": "nope", "b1": "x"})
        s = sc.score_run(qs, ans, "brain", self.utils, self.lib)
        self.assertAlmostEqual(s["task_means"]["A"], 100 / 3)
        self.assertEqual(s["task_means"]["B"], 100.0)
        self.assertAlmostEqual(s["leaderboard_style_category_score"], (100 / 3 + 100) / 2)
        self.assertEqual(s["question_mean_score"], 50.0)  # differs from the leaderboard-style category score
        self.assertNotAlmostEqual(s["question_mean_score"], s["leaderboard_style_category_score"])

    def test_the_official_score_is_the_mean_of_all_followed_and_fraction_followed(self):
        s = sc.score_run([question("q", ["x", "y"])], answers({"q": "x alone"}), "brain", self.utils, self.lib)
        self.assertEqual(s["per_question"][0]["score"], 0.25)
        self.assertEqual(s["diagnostics_not_the_leaderboard_metric"]["prompt_level_strict_accuracy"], 0.0)
        self.assertEqual(s["diagnostics_not_the_leaderboard_metric"]["instruction_level_strict_accuracy"], 50.0)

    def test_id_set_mismatch_and_missing_model_fail_closed(self):
        qs = [question("a", ["x"]), question("b", ["x"])]
        with self.assertRaises(sc.Blocked) as cm:
            sc.score_run(qs, answers({"a": "x"}), "brain", self.utils, self.lib)
        self.assertIn("ID_SET_MISMATCH", str(cm.exception))
        with self.assertRaises(sc.Blocked):
            sc.score_run(qs, answers({"a": "x", "b": "x", "c": "x"}), "brain", self.utils, self.lib)
        with self.assertRaises(sc.Blocked):
            sc.score_run(qs, answers({"a": "x", "b": "x"}, model_id="other"), "brain", self.utils, self.lib)

    def test_question_validation(self):
        base = question("a", ["x"])
        for label, rows in (("missing field", [{k: v for k, v in base.items() if k != "kwargs"}]),
                            ("duplicate", [base, dict(base)]),
                            ("kwargs length", [{**base, "kwargs": []}]),
                            ("empty", [])):
            p = Path(self.tmp.name) / "q.json"
            p.write_text(json.dumps(rows))
            with self.subTest(case=label), self.assertRaises(sc.Blocked):
                sc.load_questions(p)

    def test_scorer_exceptions_score_zero_but_are_counted_and_reported(self):
        self.utils.ifbench_process_results = lambda q, a, debug=False: (_ for _ in ()).throw(IndexError("handler crash")) if a == "RAISE" else 1.0
        qs = [question("ok", ["x"]), question("bad", ["x"])]
        s = sc.score_run(qs, answers({"ok": "x", "bad": "RAISE"}), "brain", self.utils, self.lib)
        self.assertEqual({r["question_id"]: r["score"] for r in s["per_question"]}, {"ok": 1.0, "bad": 0.0})
        self.assertEqual(s["scorer_exceptions"], {"count": 1, "by_type": {"IndexError": 1}, "question_ids": ["bad"]})

    def test_cli_exits_3_on_scorer_exceptions_unless_allowed(self):
        qpath, apath = (Path(self.tmp.name) / n for n in ("q.jsonl", "a.json"))
        qpath.write_text(json.dumps(question("bad", ["x"])) + "\n")
        apath.write_text(json.dumps(answers({"bad": "RAISE"})))
        self.utils.ifbench_process_results = lambda q, a, debug=False: (_ for _ in ()).throw(ValueError("boom"))
        orig = sc.load_upstream
        sc.load_upstream = lambda root, verify_commit=True: (self.utils, self.lib)
        try:
            args = ["--questions", str(qpath), "--model-answers", str(apath), "--livebench-root", self.tmp.name]
            self.assertEqual(sc.main(args + ["--out", str(Path(self.tmp.name) / "o1.json")]), 3)
            self.assertEqual(sc.main(args + ["--out", str(Path(self.tmp.name) / "o2.json"), "--allow-scorer-exceptions"]), 0)
            self.assertEqual(json.loads((Path(self.tmp.name) / "o1.json").read_text())["scorer_exceptions"]["count"], 1)
        finally:
            sc.load_upstream = orig

    def test_no_prompt_or_response_text_reaches_the_summary_or_stdout(self):
        qs_path, ans_path, out = (Path(self.tmp.name) / n for n in ("q.jsonl", "a.json", "s.json"))
        qs_path.write_text(json.dumps(question("q1", ["x"])) + "\n")
        ans_path.write_text(json.dumps(answers({"q1": SENTINEL + " x"})))
        # CLI with an unpinned stub root must refuse, so exercise score_run + JSON dump path directly
        s = sc.score_run(sc.load_questions(qs_path), json.loads(ans_path.read_text()), "brain", self.utils, self.lib)
        dumped = json.dumps(s)
        self.assertNotIn(SENTINEL, dumped)
        self.assertEqual(s["execution_authority"], False)
        self.assertEqual((s["capability_credit_delta"], s["incremental_spend_usd"]), (0, 0))

    def test_upstream_checkout_must_be_at_the_pinned_commit_and_unmodified(self):
        _purge()
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make_stub_root(root)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x"], check=True)
            with self.assertRaises(sc.Blocked) as cm:
                sc.load_upstream(root)  # real commit != pinned
            self.assertIn("NOT_AT_PINNED_COMMIT", str(cm.exception))
            with self.assertRaises(sc.Blocked):
                sc.load_upstream(root / "livebench")  # not a root holding the package
            old = sc.PINNED_COMMIT
            try:
                sc.PINNED_COMMIT = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
                (root / "livebench" / "process_results" / "instruction_following" / "utils.py").write_text(STUB_UTILS + "\n# local edit\n")
                with self.assertRaises(sc.Blocked) as cm2:
                    sc.load_upstream(root)
                self.assertIn("LOCAL_EDITS", str(cm2.exception))
            finally:
                sc.PINNED_COMMIT = old

    def test_hermetic_nltk_never_downloads_and_fails_closed(self):
        try:
            import nltk
        except ImportError:
            self.skipTest("nltk not installed")
        original, saved_paths = nltk.download, list(nltk.data.path)
        try:
            with tempfile.TemporaryDirectory() as t:
                (Path(t) / "corpora" / "stopwords").mkdir(parents=True)
                nltk.data.path[:] = [t]  # search ONLY this folder, independent of any earlier test or NLTK_DATA
                self.assertTrue(sc.install_hermetic_nltk())
                self.assertIs(nltk.download("stopwords"), True)  # present locally: no-op
                with self.assertRaises(RuntimeError) as cm:
                    nltk.download("punkt")  # missing locally: refuse, do not fetch
                self.assertIn("NLTK_RESOURCE_MISSING", str(cm.exception))
                with self.assertRaises(RuntimeError) as cm2:
                    nltk.download("some_other_corpus")
                self.assertIn("NOT_ALLOWED_IN_HERMETIC_RUN", str(cm2.exception))
        finally:
            nltk.download = original
            nltk.data.path[:] = saved_paths

    def test_solution_extraction_used_by_the_diagnostics(self):
        self.assertEqual(sc._extract("noise <solution>\n inner text \n</solution> tail"), "inner text")
        self.assertEqual(sc._extract("  no tags here  "), "no tags here")
        self.assertEqual(sc._extract("<solution>a</solution> <solution>b</solution>"), "a")  # first match, like upstream

    def test_the_pinned_commit_matches_the_one_bound_in_the_repo(self):
        binding = json.loads((Path(__file__).resolve().parents[1] / "canonical/governance/LIVEBENCH_IF_VERIFIER_BINDING_V1.json").read_text())
        self.assertEqual(binding["upstream"]["commit"], sc.PINNED_COMMIT)


@unittest.skipUnless(LIVEBENCH_ROOT and Path(LIVEBENCH_ROOT, "livebench").is_dir(), "set LIVEBENCH_ROOT to a LiveBench checkout at the pinned commit")
class RealUpstreamLayer(unittest.TestCase):
    """Executes the facts recorded in the public-bar receipt against the real upstream code."""

    @classmethod
    def setUpClass(cls):
        _purge()
        cls._path = list(sys.path)
        cls._env = os.environ.get("NLTK_DATA")
        cls.tmp = tempfile.TemporaryDirectory()
        stubs = Path(cls.tmp.name) / "stubs" / "spacy"
        stubs.mkdir(parents=True)
        (stubs / "__init__.py").write_text("class _U:\n    @staticmethod\n    def is_package(n):\n        return True\nutil = _U()\n")
        (stubs / "cli.py").write_text("def download(*a, **k):\n    raise RuntimeError('no downloads in the hermetic verification run')\n")
        data_dir = os.environ.get("NLTK_REAL_DIR")  # optional: the project's pinned NLTK data, unzipped
        if not data_dir:
            data_dir = str(Path(cls.tmp.name) / "nltk_data")
            for sub in ("tokenizers/punkt", "tokenizers/punkt_tab"):
                (Path(data_dir) / sub).mkdir(parents=True)  # empty folders satisfy upstream's import-time lookup
        os.environ["NLTK_DATA"] = data_dir
        import nltk

        cls._nltk_paths = list(nltk.data.path)
        nltk.data.path.insert(0, data_dir)  # NLTK reads NLTK_DATA only at import time; extend explicitly
        sys.path.insert(0, str(Path(cls.tmp.name) / "stubs"))
        cls.utils, cls.lib = sc.load_upstream(Path(LIVEBENCH_ROOT))

    @classmethod
    def tearDownClass(cls):
        sys.path[:] = cls._path
        import nltk

        nltk.data.path[:] = [p for p in cls._nltk_paths if p != os.environ.get("NLTK_DATA")]
        if cls._env is None:
            os.environ.pop("NLTK_DATA", None)
        else:
            os.environ["NLTK_DATA"] = cls._env
        _purge()
        cls.tmp.cleanup()

    NO_CONSEC = ("words:no_consecutive", {})
    WORDS_3_6 = ("count:word_count_range", {"min_words": 3, "max_words": 6})
    UNIQUE_3 = ("count:unique_word_count", {"N": 3})

    def q(self, qid, checks, task="t1"):
        return {"question_id": qid, "task": task, "turns": ["Write something. <instructions>synthetic</instructions>"],
                "instruction_id_list": [c[0] for c in checks], "kwargs": [c[1] for c in checks]}

    def score(self, questions, texts):
        return sc.score_run(questions, answers(texts), "brain", self.utils, self.lib)

    def one(self, checks, text):
        s = self.score([self.q("q", checks)], {"q": text})
        return s["per_question"][0]["score"], s["diagnostics_not_the_leaderboard_metric"]

    def test_the_registry_has_58_checkers(self):
        from livebench.if_runner.ifbench import instructions_registry as reg
        self.assertEqual(len(reg.INSTRUCTION_DICT), 58)

    def test_mean_of_all_followed_and_fraction_followed(self):
        both = [self.NO_CONSEC, self.WORDS_3_6]
        self.assertEqual(self.one(both, "apple banana cherry")[0], 1.0)
        score, diag = self.one(both, "apple apricot cherry")  # no_consecutive violated, word count fine
        self.assertEqual(score, 0.25)
        self.assertEqual(diag["prompt_level_strict_accuracy"], 0.0)
        self.assertEqual(diag["instruction_level_strict_accuracy"], 50.0)
        self.assertEqual(self.one(both, "apple apricot")[0], 0.0)
        three = [self.NO_CONSEC, self.WORDS_3_6, self.UNIQUE_3]
        self.assertAlmostEqual(self.one(three, "apple banana banana")[0], 1 / 6)
        self.assertEqual(self.one(three, "apple banana cherry date elder")[0], 1.0)

    def test_solution_tags_are_honoured_by_upstream(self):
        both = [self.NO_CONSEC, self.WORDS_3_6]
        self.assertEqual(self.one(both, "banana banana <solution>apple banana cherry</solution>")[0], 1.0)
        self.assertLess(self.one(both, "banana banana apple banana cherry")[0], 1.0)

    def test_diagnostics_use_the_same_extraction_as_the_official_score(self):
        both = [self.NO_CONSEC, self.WORDS_3_6]
        score, diag = self.one(both, "banana banana <solution>apple banana cherry</solution>")
        self.assertEqual(score, 1.0)
        self.assertEqual(diag["prompt_level_strict_accuracy"], 100.0)
        self.assertEqual(diag["instruction_level_strict_accuracy"], 100.0)

    def test_prompt_level_accuracy_never_exceeds_the_official_score_which_never_exceeds_the_instruction_level(self):
        both = [self.NO_CONSEC, self.WORDS_3_6]
        for text in ("apple banana cherry", "apple apricot cherry", "apple apricot", "x", "a b c d e f g h"):
            with self.subTest(text=text):
                s = self.score([self.q("q", both)], {"q": text})
                official = s["per_question"][0]["score"] * 100
                d = s["diagnostics_not_the_leaderboard_metric"]
                self.assertLessEqual(d["prompt_level_strict_accuracy"], official + 1e-9)
                self.assertLessEqual(official, d["instruction_level_strict_accuracy"] + 1e-9)

    def test_loose_can_be_more_lenient_than_the_strict_check_the_leaderboard_uses(self):
        both = [self.NO_CONSEC, self.WORDS_3_6]
        score, diag = self.one(both, "Here is the answer:\napple banana cherry")
        self.assertEqual(score, 0.0)  # strict: the preamble breaks both checks
        self.assertEqual(diag["prompt_level_strict_accuracy"], 0.0)
        self.assertEqual(diag["prompt_level_loose_accuracy"], 100.0)  # loose strips the first line

    def test_prompt_level_loose_accuracy_and_the_official_score_have_no_fixed_order(self):
        both = [self.NO_CONSEC, self.WORDS_3_6]
        # loose above official: preamble case
        s1 = self.score([self.q("q", both)], {"q": "Here is the answer:\napple banana cherry"})
        # official above loose: one of two instructions followed in both checks
        s2 = self.score([self.q("q", both)], {"q": "apple apricot cherry"})
        self.assertGreater(s1["diagnostics_not_the_leaderboard_metric"]["prompt_level_loose_accuracy"], s1["question_mean_score"])
        self.assertLess(s2["diagnostics_not_the_leaderboard_metric"]["prompt_level_loose_accuracy"], s2["question_mean_score"])

    def test_leaderboard_aggregation_over_tasks_with_the_real_scorer(self):
        both = [self.NO_CONSEC, self.WORDS_3_6]
        qs = [self.q("a1", both, "A"), self.q("a2", both, "A"), self.q("b1", both, "B")]
        s = self.score(qs, {"a1": "apple banana cherry", "a2": "apple apricot", "b1": "apple banana cherry"})
        self.assertEqual(s["task_means"], {"A": 50.0, "B": 100.0})
        self.assertEqual(s["leaderboard_style_category_score"], 75.0)
        self.assertAlmostEqual(s["question_mean_score"], 200 / 3)

    def test_cli_refuses_an_upstream_checkout_that_is_not_the_pinned_commit(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make_stub_root(root)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            self.assertEqual(sc.main(["--questions", str(root / "q"), "--model-answers", str(root / "a"), "--livebench-root", str(root), "--out", str(root / "o")]), 2)


if __name__ == "__main__":
    unittest.main()
