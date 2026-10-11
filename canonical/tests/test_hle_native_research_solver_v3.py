from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime.hle_native_research_solver_v3 import propose

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "governance" / "HLE_NATIVE_RESEARCH_SOLVER_V3_PREEXPOSURE_20261011_V1.json"


class HLENativeResearchSolverV3Tests(unittest.TestCase):
    def test_all_frozen_synthetic_cases(self):
        doc = json.loads(PRE.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["cases"]), 6)
        for case in doc["cases"]:
            seen_queries = []

            def search_fn(query, limit=12):
                seen_queries.append(query)
                return {"status":"PASS", "results":case["search_results"][:limit]}

            def fetch_fn(url, max_bytes=600000):
                body = case["fetches"].get(url)
                if body is None:
                    return {"status":"FAILED", "url":url}
                return {
                    "status":"PASS",
                    "url":url,
                    "final_url":url,
                    "body_excerpt":body,
                    "body_sha256":hashlib.sha256(body.encode()).hexdigest(),
                }

            out = propose(
                task_id=case["task_id"],
                question=case["question"],
                search_fn=search_fn,
                fetch_fn=fetch_fn,
            )
            self.assertEqual(out.get("candidate_answer"), case["expected"], (case["id"], out))
            self.assertFalse(out["candidate_answer_authority"])
            self.assertFalse(out["correctness_claimed"])
            self.assertFalse(out["gold_accessed"])
            self.assertEqual(out["external_model_calls"], 0)
            self.assertEqual(out["external_reasoning_model_calls"], 0)
            self.assertEqual(out["model_dependency_count"], 0)
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"], 0)
            for query in seen_queries:
                self.assertNotEqual(
                    " ".join(query.split()).casefold(),
                    " ".join(case["question"].split()).casefold(),
                    (case["id"], query),
                )

    def test_host_dedup_prevents_one_domain_from_impersonating_two_sources(self):
        question = "Who discovered the synthetic Zephyr particle in the fictional Alder experiment?"
        calls = []
        def search_fn(query, limit=12):
            return {"status":"PASS","results":[
                {"url":"https://same.example/a"},
                {"url":"https://same.example/b"},
            ]}
        def fetch_fn(url, max_bytes=600000):
            calls.append(url)
            body = "The synthetic Zephyr particle was discovered by Dr. Mira Sol in the fictional Alder experiment."
            return {"status":"PASS","url":url,"final_url":url,"body_excerpt":body}
        out = propose(task_id="dedup", question=question, search_fn=search_fn, fetch_fn=fetch_fn)
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["independent_support_host_count"], 1)

    def test_mcq_is_deferred(self):
        out = propose(
            task_id="m",
            question="Synthetic stem?\nAnswer Choices:\nA. One\nB. Two",
            search_fn=lambda *a, **k: self.fail("search must not run"),
            fetch_fn=lambda *a, **k: self.fail("fetch must not run"),
        )
        self.assertIsNone(out["candidate_answer"])
        self.assertEqual(out["status"], "NO_CANDIDATE__MCQ_DEFER_TO_MCQ_LANE")

    def test_symbolic_is_deferred(self):
        out = propose(
            task_id="s",
            question="Solve the synthetic equation x + 4 = 9 for x.",
            search_fn=lambda *a, **k: self.fail("search must not run"),
            fetch_fn=lambda *a, **k: self.fail("fetch must not run"),
        )
        self.assertIsNone(out["candidate_answer"])
        self.assertEqual(out["status"], "NO_CANDIDATE__SYMBOLIC_DEFER_TO_SYMBOLIC_LANE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
