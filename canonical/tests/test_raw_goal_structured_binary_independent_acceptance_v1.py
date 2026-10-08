from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import raw_goal_structured_binary_independent_acceptance_v1 as codec
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract


GOAL = (
    "Create canonical/astra_runtime/tmp/R2_CODEC_SOURCE.json containing exactly "
    "three records with fields id and text: 1 alpha, 2 beta, 3 gamma. "
    "Encode those exact records as BSON and save "
    "canonical/astra_runtime/tmp/R2_CODEC_RECORDS.bson. "
    "Independently decode the BSON artifact using an implementation that is not "
    "provided by the BSON producer package, and verify the decoded records are "
    "exactly identical to canonical/astra_runtime/tmp/R2_CODEC_SOURCE.json in "
    "values, order, field names, and record count."
)


class RawGoalStructuredBinaryIndependentAcceptanceV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pf = codec.preflight(GOAL)
        if cls.pf.get("matched") is not True:
            raise AssertionError(cls.pf)
        cls.contract = compile_contract(
            GOAL,
            source_id="user",
            routing_target_effects=cls.pf["routing_target_effects"],
        )
        if cls.contract.get("pass") is not True:
            raise AssertionError(cls.contract)

    def test_preflight_matches_current_cross_supplier_codec_compiler(self):
        pf = self.pf
        self.assertTrue(pf["matched"], pf)
        self.assertEqual(pf["format"], "bson")
        self.assertEqual(pf["producer_capability_id"], "auto.pypi.bson-modern")
        self.assertEqual(pf["verifier_supplier_class"], "npm_javascript_library")
        self.assertEqual(
            pf["verifier_action_type"],
            "verify_with_independent_npm_codec",
        )
        self.assertFalse(pf["preflight_execution_authority"])

    def test_self_decode_variant_is_not_direct_adequacy(self):
        goal = GOAL.replace(
            " using an implementation that is not provided by the BSON producer package",
            "",
        )
        out = codec.preflight(goal)
        self.assertFalse(out["matched"])

    def test_extra_unmodeled_clause_is_not_direct_adequacy(self):
        out = codec.preflight(GOAL + " Then email the binary artifact.")
        self.assertFalse(out["matched"])

    def _raw_result(self, root: Path):
        pf = self.pf
        source = root / pf["source_path"]
        binary = root / pf["binary_path"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            json.dumps(pf["expected_records"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        binary.write_bytes(b"verified-binary-placeholder")

        if pf["verifier_action_type"] == "verify_with_independent_npm_codec":
            verify_result = {
                "type": pf["verifier_action_type"],
                "verified": True,
                "producer_capability_id": pf["producer_capability_id"],
                "producer_project": pf["producer_project"],
                "producer_independent": True,
                "implementation_independent": True,
                "supplier_class_independent": True,
                "format": pf["format"],
            }
        else:
            verify_result = {
                "type": pf["verifier_action_type"],
                "verified": True,
                "producer_capability_id": pf["producer_capability_id"],
                "producer_project": pf["producer_project"],
                "producer_independent": True,
                "dependency_independent": True,
                "format": pf["format"],
            }

        trace = [
            {
                "plan": {
                    "type": "write_json_records",
                    "args": {
                        "output_path": pf["source_path"],
                        "fields": pf["fields"],
                        "records": deepcopy(pf["expected_records"]),
                    },
                },
                "result": {"verified": True},
            },
            {
                "plan": {
                    "type": "invoke_capability",
                    "args": {
                        "capability_id": pf["producer_capability_id"],
                        "json_path": pf["source_path"],
                        "output_path": pf["binary_path"],
                    },
                },
                "result": {
                    "output_verified": True,
                    "source_path": pf["source_path"],
                    "output_path": pf["binary_path"],
                },
            },
            {
                "plan": {
                    "type": pf["verifier_action_type"],
                    "args": {
                        "format": pf["format"],
                        "json_path": pf["source_path"],
                        "binary_path": pf["binary_path"],
                        "producer_project": pf["producer_project"],
                        "producer_capability_id": pf["producer_capability_id"],
                    },
                },
                "result": verify_result,
            },
            {
                "plan": {
                    "type": "finish",
                    "args": {"summary": "COMPOUND_GOAL_COMPLETE"},
                },
                "result": {"summary": "COMPOUND_GOAL_COMPLETE"},
            },
        ]
        return {
            "pass": True,
            "compiler_mode": "DETERMINISTIC_COMPOUND_ACTION_PLAN",
            "compiled_part_count": 3,
            "controller_action_count": 4,
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": self.contract["task_contract_sha256"],
            "raw_source_coverage_complete": True,
            "raw_acceptance_obligation_count": len(
                self.contract["acceptance_contract"]["obligations"]
            ),
            "model_dependency_count": 0,
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "controller_execution": {
                "returncode": 0,
                "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
                "final_summary": "COMPOUND_GOAL_COMPLETE",
                "trace": trace,
            },
        }

    def _verify(self, root: Path, raw):
        with patch.object(codec, "preflight", return_value=deepcopy(self.pf)), patch.object(
            codec, "compile_contract", return_value=deepcopy(self.contract)
        ):
            return codec.verify(goal=GOAL, raw_result=raw, root=root)

    def test_full_cross_supplier_roundtrip_accepts_every_raw_obligation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._raw_result(root)
            out = self._verify(root, raw)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["source_exact"])
        self.assertTrue(out["producer_output_verified"])
        self.assertTrue(out["independent_semantic_verification_verified"])
        self.assertEqual(
            len(out["accepted_obligation_ids"]),
            out["required_obligation_count"],
        )

    def test_verifier_independence_tamper_fails_open(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._raw_result(root)
            raw["controller_execution"]["trace"][2]["result"][
                "producer_independent"
            ] = False
            out = self._verify(root, raw)
        self.assertFalse(out["pass"])
        self.assertFalse(out["independent_semantic_verification_verified"])
        self.assertEqual(out["accepted_obligation_ids"], [])

    def test_source_artifact_drift_fails_open(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._raw_result(root)
            source = root / self.pf["source_path"]
            source.write_text('[{"id":999,"text":"tampered"}]', encoding="utf-8")
            out = self._verify(root, raw)
        self.assertFalse(out["pass"])
        self.assertFalse(out["source_exact"])

    def test_model_dependency_cannot_gain_direct_adequacy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = self._raw_result(root)
            raw["model_dependency_count"] = 1
            out = self._verify(root, raw)
        self.assertFalse(out["pass"])
        self.assertFalse(out["semantic_acceptance_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
