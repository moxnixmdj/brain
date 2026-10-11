from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.hle_native_total_solver_v3 import solve

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "governance" / "HLE_NATIVE_TOTAL_SOLVER_V3_PREEXPOSURE_20261011_V1.json"


def _lane(candidate=None, *, dep=0, reasoning=0, status="SYNTHETIC"):
    def fn(**kwargs):
        return {
            "status": status,
            "candidate_answer": candidate,
            "candidate_answer_authority": False,
            "external_model_calls": 0,
            "external_reasoning_model_calls": reasoning,
            "model_dependency_count": dep,
            "gold_accessed": False,
        }
    return fn


class HLENativeTotalSolverV3Tests(unittest.TestCase):
    def test_frozen_scenarios(self):
        doc=json.loads(PRE.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["scenarios"]),7)
        for s in doc["scenarios"]:
            calls=[]
            mcq_candidate="B" if s["id"]=="MCQ_ONLY" else None
            question=(
                "Synthetic stem?\nAnswer Choices:\nA. One\nB. Two\nC. Three"
                if s.get("mcq") else
                "Who discovered the synthetic Zephyr particle?"
            )
            def wrap(name, fn):
                def inner(**kwargs):
                    calls.append(name)
                    return fn(**kwargs)
                return inner
            out=solve(
                task_id=s["id"],
                question=question,
                mcq_proposer=wrap("MCQ_RETRIEVAL_VOTE",_lane(mcq_candidate)),
                symbolic_lark_proposer=wrap("SYMBOLIC_LARK_V2",_lane(s.get("lark_candidate"))),
                symbolic_surface_proposer=wrap("SYMBOLIC_SURFACE_V1",_lane(None)),
                research_proposer=wrap(
                    "NATIVE_RESEARCH_V3",
                    _lane(
                        s.get("research_candidate"),
                        dep=s.get("research_model_dependency_count",0),
                        reasoning=s.get("research_external_reasoning_model_calls",0),
                    ),
                ),
                retrieval_proposer=wrap("EXACT_RETRIEVAL_V2",_lane(s.get("legacy_candidate"))),
            )
            expected_answer=s.get("expected_answer",mcq_candidate)
            self.assertEqual(out["final_answer"],expected_answer,(s["id"],out))
            self.assertEqual(out["selected_lane"],s.get("expected_lane"),(s["id"],out))
            self.assertFalse(out["gold_accessed"])
            self.assertFalse(out["external_model_solver_output_used"])
            self.assertFalse(out["brain_capability_claim_from_external_model"])
            self.assertTrue(out["external_cognition_candidate_rejection_enforced"])
            self.assertFalse(out["answer_type_metadata_used"])
            self.assertFalse(out["correctness_claimed"])
            self.assertFalse(out["target_score_claimed"])
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"],0)
            if s.get("mcq"):
                self.assertEqual(calls,["MCQ_RETRIEVAL_VOTE"],(s["id"],calls))

    def test_model_dependent_candidate_is_recorded_but_never_selected(self):
        out=solve(
            task_id="anti",
            question="Who discovered synthetic Zephyr?",
            symbolic_lark_proposer=_lane(None),
            symbolic_surface_proposer=_lane(None),
            research_proposer=_lane("Forbidden",dep=2),
            retrieval_proposer=_lane("Safe"),
        )
        rejected=[x for x in out["attempts"] if x["lane"]=="NATIVE_RESEARCH_V3"][0]
        self.assertTrue(rejected["candidate_present"])
        self.assertFalse(rejected["candidate_eligible"])
        self.assertTrue(rejected["candidate_rejected_external_cognition"])
        self.assertEqual(out["final_answer"],"Safe")
        self.assertEqual(out["selected_lane"],"EXACT_RETRIEVAL_V2")

    def test_external_model_calls_candidate_is_also_rejected(self):
        def bad(**kwargs):
            return {
                "status":"SYNTHETIC",
                "candidate_answer":"Forbidden",
                "external_model_calls":1,
                "external_reasoning_model_calls":0,
                "model_dependency_count":0,
            }
        out=solve(
            task_id="anti2",
            question="Who discovered synthetic Zephyr?",
            symbolic_lark_proposer=_lane(None),
            symbolic_surface_proposer=_lane(None),
            research_proposer=bad,
            retrieval_proposer=_lane("Safe"),
        )
        self.assertEqual(out["final_answer"],"Safe")

    def test_external_cognition_image_observation_is_not_injected(self):
        seen=[]
        def bad_image(**kwargs):
            return {
                "status":"OBSERVED",
                "ocr_text":"FORBIDDEN COGNITION",
                "external_model_calls":0,
                "external_reasoning_model_calls":1,
                "model_dependency_count":0,
            }
        def symbolic(**kwargs):
            seen.append(kwargs["question"])
            return {
                "status":"NO",
                "candidate_answer":None,
                "external_model_calls":0,
                "external_reasoning_model_calls":0,
                "model_dependency_count":0,
            }
        out=solve(
            task_id="img",
            question="Who discovered synthetic Zephyr?",
            image="data:image/png;base64,AA==",
            image_observer=bad_image,
            symbolic_lark_proposer=symbolic,
            symbolic_surface_proposer=_lane(None),
            research_proposer=_lane(None),
            retrieval_proposer=_lane(None),
        )
        self.assertTrue(out["image_observation"]["external_cognition_rejected"])
        self.assertTrue(all("FORBIDDEN COGNITION" not in q for q in seen))


if __name__=="__main__":
    unittest.main(verbosity=2)
