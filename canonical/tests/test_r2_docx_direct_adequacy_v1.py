from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import r2_docx_direct_adequacy_v1 as docx


GOAL = (
    "Create canonical/astra_runtime/tmp/R2_DIRECT_DOCX.docx with title Project Brain Report, "
    "paragraph Verified cross-tool composition, and a table with columns Capability and Status "
    "containing Browser interaction | VERIFIED and Browser-to-XLSX composition | VERIFIED. "
    "Finally independently reopen the DOCX and verify all requested content."
)


class R2DocxDirectAdequacyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pf = docx.preflight({"task_id": "docx-preflight", "goal": GOAL})
        if cls.pf.get("matched") is not True:
            raise AssertionError(cls.pf)

    def test_real_current_compiler_preflight_matches_exact_family(self):
        pf = self.pf
        self.assertEqual(pf["status"], "DIRECT_DOCX_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(pf["producer_capability_id"], docx.PRODUCER)
        self.assertEqual(pf["verifier_capability_id"], docx.VERIFIER)
        self.assertEqual(pf["expected"]["title"], "Project Brain Report")
        self.assertFalse(pf["preflight_execution_authority"])
        self.assertGreater(pf["acceptance_obligation_count"], 0)

    def test_extra_instruction_is_not_in_exact_family(self):
        out = docx.preflight({
            "task_id": "docx-extra",
            "goal": GOAL + " Then upload it somewhere.",
        })
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    def _raw(self, root: Path, pf, *, sidecar_goal=None):
        output = root / pf["output_path"]
        intent = root / pf["intent_path"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"PK\x03\x04mock-docx")
        intent.write_text(
            json.dumps(
                {
                    "schema": "PROJECT_BRAIN_DOCUMENT_INTENT_V1",
                    "source_goal": sidecar_goal or pf["creation_clause"],
                    "output_path": pf["output_path"],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "pass": True,
            "compiler_mode": "DETERMINISTIC_COMPOUND_ACTION_PLAN",
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_source_coverage_complete": True,
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "controller_execution": {
                "returncode": 0,
                "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
                "final_summary": "COMPOUND_GOAL_COMPLETE",
                "trace": [
                    {
                        "plan": {
                            "type": "invoke_capability",
                            "args": {
                                "capability_id": docx.PRODUCER,
                                "goal": pf["creation_clause"],
                                "output_path": pf["output_path"],
                            },
                        },
                        "result": {
                            "output_verified": True,
                            "output_path": pf["output_path"],
                            "intent_path": pf["intent_path"],
                        },
                    },
                    {
                        "plan": {
                            "type": "invoke_capability",
                            "args": {
                                "capability_id": docx.VERIFIER,
                                "path": pf["output_path"],
                            },
                        },
                        "result": {
                            "verified": True,
                            "producer_independent_verifier": True,
                            "intent_source_goal": pf["creation_clause"],
                            "intent_derived_expected": deepcopy(pf["expected"]),
                        },
                    },
                    {
                        "plan": {
                            "type": "finish",
                            "args": {"summary": "COMPOUND_GOAL_COMPLETE"},
                        },
                        "result": {"summary": "COMPOUND_GOAL_COMPLETE"},
                    },
                ],
            },
        }

    def _evidence(self, pf):
        return {
            "verified": True,
            "producer_independent_verifier": True,
            "intent_source_goal": pf["creation_clause"],
            "intent_derived_expected": deepcopy(pf["expected"]),
            "expected": deepcopy(pf["expected"]),
            "title_ok": True,
            "paragraphs_ok": True,
            "table_ok": True,
        }

    def test_independent_ooxml_acceptance_commits_and_accepts_all_obligations(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pf = deepcopy(self.pf)
            with patch.object(docx, "preflight", return_value=pf), patch.object(
                docx.live_bound, "run_raw_goal"
            ) as execute, patch.object(
                docx.docx_verify_ooxml_intent, "run", return_value=self._evidence(pf)
            ):
                execute.side_effect = lambda _: self._raw(root, pf)
                out = docx.run({"task_id": "x", "goal": GOAL}, repo_root=root)
                self.assertTrue((root / pf["output_path"]).is_file())
                self.assertTrue((root / pf["intent_path"]).is_file())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertEqual(
            len(out["accepted_raw_obligation_ids"]),
            out["raw_acceptance_obligation_count"],
        )

    def test_sidecar_goal_tamper_fails_closed_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pf = deepcopy(self.pf)
            output = root / pf["output_path"]
            intent = root / pf["intent_path"]
            output.parent.mkdir(parents=True, exist_ok=True)
            old_output = b"old-docx"
            old_intent = b'{"old":true}'
            output.write_bytes(old_output)
            intent.write_bytes(old_intent)
            with patch.object(docx, "preflight", return_value=pf), patch.object(
                docx.live_bound, "run_raw_goal"
            ) as execute:
                execute.side_effect = lambda _: self._raw(
                    root, pf, sidecar_goal="different creation intent"
                )
                out = docx.run({"task_id": "x", "goal": GOAL}, repo_root=root)
            self.assertEqual(output.read_bytes(), old_output)
            self.assertEqual(intent.read_bytes(), old_intent)
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(
            out["reason"],
            "DOCX_INTENT_SIDECAR_RAW_GOAL_BINDING_INVALID",
        )

    def test_failed_independent_acceptance_removes_new_docx_and_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pf = deepcopy(self.pf)
            with patch.object(docx, "preflight", return_value=pf), patch.object(
                docx.live_bound, "run_raw_goal"
            ) as execute, patch.object(
                docx.docx_verify_ooxml_intent,
                "run",
                return_value={"verified": False},
            ):
                execute.side_effect = lambda _: self._raw(root, pf)
                out = docx.run({"task_id": "x", "goal": GOAL}, repo_root=root)
            self.assertFalse((root / pf["output_path"]).exists())
            self.assertFalse((root / pf["intent_path"]).exists())
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(out["policy_adequacy_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
