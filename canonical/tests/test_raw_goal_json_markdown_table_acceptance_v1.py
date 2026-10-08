from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import raw_goal_json_markdown_table_acceptance_v1 as a


def _goal(src="canonical/tmp/SOURCE.json",out="canonical/tmp/REPORT.md"):
    return f"Read {src}. Create {out} containing a table with every READY_STATUS."


def _source():
    return {
        "rows":{
            "b":{"name":"Beta","status":"OTHER","count":2},
            "a":{"name":"Alpha","status":"READY_STATUS","count":1},
            "c":{"name":"Pipe|Name","status":"READY_STATUS","count":3},
        }
    }


def _raw(goal,root):
    pf=a.preflight(goal,root=root)
    contract=a.compile_contract(goal,source_id="user",routing_target_effects=[a.ROUTING_EFFECT])
    return {
        "pass":True,
        "compiler_mode":"DETERMINISTIC_COMPOUND_ACTION_PLAN",
        "raw_goal_sha256":pf["goal_sha256"],
        "raw_task_contract_sha256":contract["task_contract_sha256"],
        "raw_source_coverage_complete":True,
        "raw_acceptance_obligation_count":len(contract["acceptance_contract"]["obligations"]),
        "controller_action_count":3,
        "model_dependency_count":0,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "controller_execution":{
            "returncode":0,
            "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
            "final_summary":"COMPOUND_GOAL_COMPLETE",
            "trace":[
                {
                    "cycle":0,
                    "plan":{
                        "type":"read_file",
                        "args":{"path":pf["input_path"]},
                        "expect":{"type":"field_nonempty","field":"content"},
                    },
                    "result":{"content":"source"},
                },
                {
                    "cycle":1,
                    "plan":{
                        "type":"invoke_capability",
                        "args":{
                            "capability_id":"json.query.jq",
                            "input_path":pf["input_path"],
                            "filter":"independently checked by artifact equality",
                            "output_path":pf["output_path"],
                            "raw_output":True,
                            "require_nonempty":True,
                            "timeout_s":60,
                        },
                        "expect":{"type":"field_equals","field":"output_verified","value":True},
                    },
                    "result":{"output_verified":True},
                },
                {
                    "cycle":2,
                    "plan":{"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}},
                    "result":{"summary":"COMPOUND_GOAL_COMPLETE"},
                },
            ],
        },
    }


class JsonMarkdownTableAcceptanceTests(unittest.TestCase):
    def test_exact_flat_source_and_artifact_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"canonical/tmp/SOURCE.json"
            out=root/"canonical/tmp/REPORT.md"
            src.parent.mkdir(parents=True)
            src.write_text(json.dumps(_source()),encoding="utf-8")
            pf=a.preflight(_goal(),root=root)
            self.assertTrue(pf["matched"],pf)
            out.write_text(pf["expected_markdown"],encoding="utf-8")
            result=a.verify(goal=_goal(),raw_result=_raw(_goal(),root),root=root)
            self.assertTrue(result["pass"],result)
            self.assertTrue(result["artifact_exact"])
            self.assertTrue(result["source_stable"])

    def test_artifact_tampering_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"canonical/tmp/SOURCE.json"
            out=root/"canonical/tmp/REPORT.md"
            src.parent.mkdir(parents=True)
            src.write_text(json.dumps(_source()),encoding="utf-8")
            out.write_text("wrong\n",encoding="utf-8")
            result=a.verify(goal=_goal(),raw_result=_raw(_goal(),root),root=root)
            self.assertFalse(result["pass"])
            self.assertFalse(result["artifact_exact"])

    def test_nested_records_are_not_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"canonical/tmp/SOURCE.json"
            src.parent.mkdir(parents=True)
            bad={"rows":{"a":{"status":"READY_STATUS","nested":{"x":1}}}}
            src.write_text(json.dumps(bad),encoding="utf-8")
            pf=a.preflight(_goal(),root=root)
            self.assertFalse(pf["matched"])

    def test_ambiguous_matching_collections_are_not_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"canonical/tmp/SOURCE.json"
            src.parent.mkdir(parents=True)
            bad={
                "left":{"a":{"status":"READY_STATUS","name":"A"}},
                "right":{"b":{"status":"READY_STATUS","name":"B"}},
            }
            src.write_text(json.dumps(bad),encoding="utf-8")
            pf=a.preflight(_goal(),root=root)
            self.assertFalse(pf["matched"])
            self.assertIn("MATCHING_COLLECTION_NOT_UNIQUE",pf.get("reason",""))

    def test_source_drift_after_raw_execution_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"canonical/tmp/SOURCE.json"
            out=root/"canonical/tmp/REPORT.md"
            src.parent.mkdir(parents=True)
            src.write_text(json.dumps(_source()),encoding="utf-8")
            pf=a.preflight(_goal(),root=root)
            raw=_raw(_goal(),root)
            out.write_text(pf["expected_markdown"],encoding="utf-8")
            changed=_source()
            changed["rows"]["a"]["count"]=999
            src.write_text(json.dumps(changed),encoding="utf-8")
            # Verification must recompute preflight from the changed source, so
            # the old raw goal hash alone cannot authorize the old artifact.
            result=a.verify(goal=_goal(),raw_result=raw,root=root)
            self.assertFalse(result["pass"])

    def test_extra_unmodeled_instruction_does_not_match(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"canonical/tmp/SOURCE.json"
            src.parent.mkdir(parents=True)
            src.write_text(json.dumps(_source()),encoding="utf-8")
            pf=a.preflight(_goal()+" Then upload it.",root=root)
            self.assertFalse(pf["matched"])


if __name__=="__main__":
    unittest.main(verbosity=2)
