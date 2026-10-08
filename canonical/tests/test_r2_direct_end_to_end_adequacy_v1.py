from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct


GOAL = (
    "Create a tar.gz archive from the manifest canonical/tmp/manifest.json, "
    "including all its verification_paths files, and save it to "
    "canonical/tmp/output.tar.gz."
)


class R2DirectEndToEndAdequacyV1Tests(unittest.TestCase):
    def test_exact_archive_goal_preflight_matches_without_execution(self):
        with patch.object(direct.live_bound, "run_raw_goal") as execute:
            out = direct.preflight({"task_id": "t", "goal": GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.ARCHIVE_ROUTE_ID)
        self.assertFalse(out["preflight_execution_authority"])
        self.assertEqual(
            out["bound_inputs"]["manifest_path"],
            "canonical/tmp/manifest.json",
        )
        execute.assert_not_called()

    def test_extra_unmodeled_text_does_not_match_exact_cell(self):
        out = direct.preflight({
            "task_id": "t",
            "goal": GOAL + " Also email it to somebody.",
        })
        self.assertFalse(out["pass"])
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NO_DIRECT_ADEQUACY_ROUTE")

    @patch.object(direct.live_bound, "run_raw_goal")
    def test_full_acceptance_is_direct_adequacy(self, execute):
        pf = direct.preflight({"task_id": "t", "goal": GOAL})
        execute.return_value = {
            "pass": True,
            "status": "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
            "compiled_capability_id": direct.ARCHIVE_CAPABILITY_ID,
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_source_coverage_complete": True,
            "raw_acceptance_obligation_count": 1,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "semantic_acceptance_complete": True,
            "raw_goal_acceptance": {
                "pass": True,
                "status": "PASS__EXACT_RAW_GOAL_ARCHIVE_ACCEPTED",
                "semantic_acceptance_complete": True,
                "accepted_obligation_ids": ["RAWREQ:x"],
            },
        }
        out = direct.run({"task_id": "t", "goal": GOAL})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])
        execute.assert_called_once()

    @patch.object(direct.live_bound, "run_raw_goal")
    def test_partial_acceptance_never_becomes_adequacy(self, execute):
        pf = direct.preflight({"task_id": "t", "goal": GOAL})
        execute.return_value = {
            "pass": True,
            "compiled_capability_id": direct.ARCHIVE_CAPABILITY_ID,
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_source_coverage_complete": True,
            "raw_acceptance_obligation_count": 2,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "semantic_acceptance_complete": False,
            "raw_goal_acceptance": {
                "pass": False,
                "semantic_acceptance_complete": False,
                "accepted_obligation_ids": [],
            },
        }
        out = direct.run({"task_id": "t", "goal": GOAL})
        self.assertFalse(out["pass"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        self.assertEqual(
            out["status"],
            "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",
        )


    def test_exact_literal_preflight_matches_without_execution(self):
        goal='Respond with exactly "READY_42".'
        with patch.object(direct.live_bound, "run_raw_goal") as execute:
            out=direct.preflight({"task_id":"t","goal":goal})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.EXACT_LITERAL_ROUTE_ID)
        self.assertIsNone(out["capability_id"])
        self.assertFalse(out["preflight_execution_authority"])
        execute.assert_not_called()

    def test_exact_literal_extra_unmodeled_text_does_not_match(self):
        out=direct.preflight({
            "task_id":"t",
            "goal":'Respond with exactly "READY_42". Then explain why.',
        })
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"],"NO_DIRECT_ADEQUACY_ROUTE")

    @patch.object(direct.live_bound, "run_raw_goal")
    @patch.object(direct.literal_acceptance, "verify")
    def test_exact_literal_full_acceptance_is_direct_adequacy(self, verify, execute):
        goal='Reply with exactly OK.'
        pf=direct.preflight({"task_id":"t","goal":goal})
        execute.return_value={
            "pass":True,
            "raw_goal_sha256":pf["goal_sha256"],
            "raw_source_coverage_complete":True,
        }
        verify.return_value={
            "pass":True,
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "accepted_obligation_ids":["RAWREQ:x"],
            "required_obligation_count":1,
        }
        out=direct.run({"task_id":"t","goal":goal})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(out["selected_policy_id"],direct.EXACT_LITERAL_ROUTE_ID)
        self.assertFalse(out["retry_by_other_route_authorized"])
        execute.assert_called_once()
        verify.assert_called_once()

    def test_literal_json_preflight_matches_without_execution(self):
        goal=(
            "Create canonical/astra_runtime/tmp/R2_LITERAL.json containing exactly "
            "two records with fields id and name: 1 alpha; 2 beta"
        )
        with patch.object(direct.live_bound,"run_raw_goal") as execute:
            out=direct.preflight({"task_id":"t","goal":goal})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.LITERAL_JSON_ROUTE_ID)
        self.assertEqual(
            out["output_path"],
            "canonical/astra_runtime/tmp/R2_LITERAL.json",
        )
        execute.assert_not_called()

    @patch.object(direct.live_bound,"run_raw_goal")
    @patch.object(direct.literal_json_acceptance,"verify")
    def test_literal_json_full_acceptance_is_direct_adequacy(self,verify,execute):
        goal=(
            "Create canonical/astra_runtime/tmp/R2_LITERAL.json containing exactly "
            "one record with fields id and name: 1 alpha"
        )
        pf=direct.preflight({"task_id":"t","goal":goal})
        execute.return_value={
            "pass":True,
            "raw_goal_sha256":pf["goal_sha256"],
        }
        verify.return_value={
            "pass":True,
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "artifact_exact":True,
            "accepted_obligation_ids":["RAWREQ:x"],
            "required_obligation_count":1,
        }
        out=direct.run({"task_id":"t","goal":goal})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(out["selected_policy_id"],direct.LITERAL_JSON_ROUTE_ID)
        self.assertFalse(out["retry_by_other_route_authorized"])


    @patch.object(direct.codec_adequacy, "preflight")
    def test_structured_binary_family_is_reachable_from_direct_preflight(self, codec_preflight):
        codec_preflight.return_value = {
            "matched": True,
            "status": "DIRECT_CODEC_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "auto.npm.msgpack-msgpack",
            "policy_id": "BOUND_CAPABILITY_POLICY::codec::goal",
            "goal_sha256": "g" * 64,
            "format": "msgpack",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.msgpack",
        }
        out = direct.preflight({"task_id": "codec", "goal": "not another direct grammar"})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.STRUCTURED_BINARY_CODEC_ROUTE_ID)
        self.assertEqual(out["capability_id"], "auto.npm.msgpack-msgpack")
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.codec_adequacy, "run")
    @patch.object(direct.codec_adequacy, "preflight")
    def test_structured_binary_verified_acceptance_becomes_direct_adequacy(
        self, codec_preflight, codec_run
    ):
        codec_preflight.return_value = {
            "matched": True,
            "status": "DIRECT_CODEC_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "auto.npm.msgpack-msgpack",
            "policy_id": "BOUND_CAPABILITY_POLICY::codec::goal",
            "goal_sha256": "g" * 64,
            "format": "msgpack",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.msgpack",
        }
        codec_run.return_value = {
            "pass": True,
            "status": "PASS__TRANSACTIONAL_STRUCTURED_BINARY_POLICY_ADEQUACY_VERIFIED",
            "capability_id": "auto.npm.msgpack-msgpack",
            "policy_id": "BOUND_CAPABILITY_POLICY::codec::goal",
            "goal_sha256": "g" * 64,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "raw_acceptance_obligation_count": 1,
            "raw_result": {"pass": True},
            "authority_boundary": "bounded codec family",
        }
        out = direct.run({"task_id": "codec", "goal": "not another direct grammar"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(out["selected_policy_id"], "BOUND_CAPABILITY_POLICY::codec::goal")
        codec_run.assert_called_once()

    @patch.object(direct.codec_adequacy, "run")
    @patch.object(direct.codec_adequacy, "preflight")
    def test_structured_binary_acceptance_failure_never_falls_through_to_other_execution(
        self, codec_preflight, codec_run
    ):
        codec_preflight.return_value = {
            "matched": True,
            "status": "DIRECT_CODEC_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "auto.npm.msgpack-msgpack",
            "policy_id": "BOUND_CAPABILITY_POLICY::codec::goal",
            "goal_sha256": "g" * 64,
            "format": "msgpack",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.msgpack",
        }
        codec_run.return_value = {
            "pass": False,
            "status": "OPEN__INDEPENDENT_CODEC_ACCEPTANCE_DID_NOT_VERIFY",
            "transaction_rolled_back": True,
        }
        with patch.object(direct.live_bound, "run_raw_goal") as legacy_execute:
            out = direct.run({"task_id": "codec", "goal": "not another direct grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        legacy_execute.assert_not_called()


    @patch.object(direct.docx_adequacy, "preflight")
    @patch.object(direct.codec_adequacy, "preflight")
    def test_docx_family_is_reachable_from_direct_preflight(self, codec_preflight, docx_preflight):
        codec_preflight.return_value = {"matched": False, "status": "NOT_APPLICABLE"}
        docx_preflight.return_value = {
            "matched": True,
            "status": "DIRECT_DOCX_ADEQUACY_ROUTE_MATCHED",
            "producer_capability_id": "docx.document.create.python_docx",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "d" * 64,
            "output_path": "canonical/report.docx",
            "intent_path": "canonical/report.docx.intent.json",
        }
        out = direct.preflight({"task_id": "docx", "goal": "bounded docx goal"})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.DOCX_ROUTE_ID)
        self.assertEqual(out["capability_id"], "docx.document.create.python_docx")
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.docx_adequacy, "run")
    @patch.object(direct.docx_adequacy, "preflight")
    @patch.object(direct.codec_adequacy, "preflight")
    def test_docx_verified_acceptance_becomes_direct_adequacy(
        self, codec_preflight, docx_preflight, docx_run
    ):
        codec_preflight.return_value = {"matched": False, "status": "NOT_APPLICABLE"}
        docx_preflight.return_value = {
            "matched": True,
            "status": "DIRECT_DOCX_ADEQUACY_ROUTE_MATCHED",
            "producer_capability_id": "docx.document.create.python_docx",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "d" * 64,
            "output_path": "canonical/report.docx",
            "intent_path": "canonical/report.docx.intent.json",
        }
        docx_run.return_value = {
            "pass": True,
            "status": "PASS__TRANSACTIONAL_DOCX_POLICY_ADEQUACY_VERIFIED",
            "capability_id": "docx.document.create.python_docx",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "d" * 64,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "accepted_raw_obligation_ids": ["RAWREQ:a", "RAWREQ:b"],
            "raw_acceptance_obligation_count": 2,
            "raw_result": {"pass": True},
            "authority_boundary": "bounded docx family",
        }
        out = direct.run({"task_id": "docx", "goal": "bounded docx goal"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(out["selected_policy_id"], "BOUND_CAPABILITY_POLICY::docx::goal")
        docx_run.assert_called_once()

    @patch.object(direct.docx_adequacy, "run")
    @patch.object(direct.docx_adequacy, "preflight")
    @patch.object(direct.codec_adequacy, "preflight")
    def test_docx_acceptance_failure_never_falls_through_to_other_execution(
        self, codec_preflight, docx_preflight, docx_run
    ):
        codec_preflight.return_value = {"matched": False, "status": "NOT_APPLICABLE"}
        docx_preflight.return_value = {
            "matched": True,
            "status": "DIRECT_DOCX_ADEQUACY_ROUTE_MATCHED",
            "producer_capability_id": "docx.document.create.python_docx",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "d" * 64,
            "output_path": "canonical/report.docx",
            "intent_path": "canonical/report.docx.intent.json",
        }
        docx_run.return_value = {
            "pass": False,
            "status": "OPEN__INDEPENDENT_DOCX_ACCEPTANCE_DID_NOT_VERIFY",
            "transaction_rolled_back": True,
        }
        with patch.object(direct.live_bound, "run_raw_goal") as legacy_execute:
            out = direct.run({"task_id": "docx", "goal": "bounded docx goal"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        legacy_execute.assert_not_called()

if __name__ == "__main__":
    unittest.main(verbosity=2)
