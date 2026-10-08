from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import raw_goal_literal_json_acceptance_v1 as a


GOAL=(
    "Create canonical/tmp/LITERAL.json containing exactly two records "
    "with fields id and name: 1 alpha; 2 beta"
)


class LiteralJsonAcceptanceTests(unittest.TestCase):
    def test_preflight_matches_exact_grammar_and_rejects_path_escape(self):
        out=a.preflight(GOAL)
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["record_count"],2)
        self.assertEqual(
            out["expected_records"],
            [{"id":1,"name":"alpha"},{"id":2,"name":"beta"}],
        )
        bad=a.preflight(
            "Create ../escape.json containing exactly one record with fields id: 1"
        )
        self.assertFalse(bad["matched"])

    def _raw(self,goal,root):
        pf=a.preflight(goal,root=root)
        contract=a.compile_contract(
            goal,source_id="user",routing_target_effects=[a.ROUTING_EFFECT]
        )
        expected=pf["expected_records"]
        return {
            "pass":True,
            "compiler_mode":"DETERMINISTIC_LITERAL_JSON_RECORDS",
            "raw_goal_sha256":pf["goal_sha256"],
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_source_coverage_complete":True,
            "raw_acceptance_obligation_count":len(
                contract["acceptance_contract"]["obligations"]
            ),
            "controller_action_count":2,
            "model_dependency_count":0,
            "cognition_dependency_class":"MODEL_INDEPENDENT",
            "controller_execution":{
                "returncode":0,
                "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
                "final_summary":"LITERAL_JSON_GOAL_COMPLETE",
                "trace":[
                    {
                        "cycle":0,
                        "plan":{
                            "type":"write_json_records",
                            "args":{
                                "output_path":pf["output_path"],
                                "fields":pf["fields"],
                                "records":expected,
                            },
                        },
                        "result":{"type":"write_json_records","verified":True},
                    },
                    {
                        "cycle":1,
                        "plan":{
                            "type":"finish",
                            "args":{"summary":"LITERAL_JSON_GOAL_COMPLETE"},
                        },
                        "result":{
                            "type":"finish",
                            "summary":"LITERAL_JSON_GOAL_COMPLETE",
                        },
                    },
                ],
            },
        }

    def test_exact_artifact_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"canonical/tmp/LITERAL.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps([{"id":1,"name":"alpha"},{"id":2,"name":"beta"}]),
                encoding="utf-8",
            )
            raw=self._raw(GOAL,root)
            out=a.verify(goal=GOAL,raw_result=raw,root=root)
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["artifact_exact"])
            self.assertEqual(
                len(out["accepted_obligation_ids"]),
                out["required_obligation_count"],
            )

    def test_tampered_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"canonical/tmp/LITERAL.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps([{"id":1,"name":"wrong"},{"id":2,"name":"beta"}]),
                encoding="utf-8",
            )
            raw=self._raw(GOAL,root)
            out=a.verify(goal=GOAL,raw_result=raw,root=root)
            self.assertFalse(out["pass"])
            self.assertFalse(out["artifact_exact"])
            self.assertEqual(out["accepted_obligation_ids"],[])


if __name__=="__main__":
    unittest.main(verbosity=2)
