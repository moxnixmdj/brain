import copy
import hashlib
import unittest

from canonical.runtime.aa_briefcase_post_build_audit_v1 import (
    MANIFEST_SCHEMA,
    PostBuildAuditError,
    verify_post_build_audit,
)
from canonical.tests.test_aa_briefcase_pre_generation_contract_v1 import (
    contract as make_contract,
    ingress,
    parse_manifest,
)
from canonical.runtime.aa_briefcase_pre_generation_contract_v1 import verify_pre_generation_contract


def setup():
    sweep, review, c = make_contract()
    pre = verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)
    return c, pre


def audit(c, pre):
    artifacts = []
    for path in sorted({x["deliverable_path"] for x in c["outputs"]}):
        artifacts.append({
            "deliverable_path": path,
            "artifact_sha256": "f" * 64,
            "artifact_bytes": 1000,
            "mechanical_integrity_verified": True,
            "verification_receipt": "mechanical",
        })
    return {
        "schema": MANIFEST_SCHEMA,
        "pre_generation_contract_sha256": pre["pre_generation_contract_sha256"],
        "artifacts": artifacts,
        "requirement_results": [
            {
                "requirement_id": r["id"],
                "pass": True,
                "output_ids": r["output_ids"],
                "artifact_locations": ["Sheet1!A1"],
                "verification_receipt": "req",
            }
            for r in c["requirements"]
        ],
        "dimension_results": [
            {
                "dimension_id": d["dimension_id"],
                "pass": True,
                "artifact_locations": ["Sheet1!B1"],
                "verification_receipt": "dim",
            }
            for d in c["dimensions"]
        ],
        "convention_results": [
            {
                "convention_id": x["convention_id"],
                "pass": True,
                "effective_source_path": x["effective_source_path"],
                "artifact_locations": ["Legend!A1"],
                "verification_receipt": "conv",
            }
            for x in c["conventions"]
        ],
        "scenario_results": [
            {
                "axis_id": x["axis_id"],
                "pass": True,
                "realized_states": x["states"],
                "state_rationales": {s: "Source-grounded rationale" for s in x["states"]},
                "artifact_locations": ["Scenarios!A1"],
                "verification_receipt": "scenario",
            }
            for x in c["scenario_axes"]
        ],
        "reconciliation_results": [
            {
                "reconciliation_id": x["reconciliation_id"],
                "pass": True,
                "method_ids": x["method_ids"],
                "variance_explained": True,
                "output_id": x["output_id"],
                "artifact_locations": ["Audit!A1"],
                "verification_receipt": "recon",
            }
            for x in c["reconciliations"]
        ],
        "source_traceability": [
            {
                "source_path": x["source_path"],
                "source_sha256": x["content_sha256"],
                "provenance_recorded": True,
                "artifact_locations": ["Sources!A1"],
                "verification_receipt": "trace",
            }
            for x in c["authority_sources"]
        ],
        "formula_or_structural_error_scan_pass": True,
        "all_declared_outputs_reopened_after_write": True,
        "freeze_after_audit": True,
    }


class T(unittest.TestCase):
    def test_complete_post_build_audit_passes(self):
        c, pre = setup()
        out = verify_post_build_audit(pre, c, audit(c, pre))
        self.assertTrue(out["pre_freeze_audit_complete"])
        self.assertFalse(out["professional_quality_relative_to_opus_proved"])

    def test_missing_requirement_result_blocks(self):
        c, pre = setup()
        a = audit(c, pre)
        a["requirement_results"] = a["requirement_results"][:-1]
        with self.assertRaisesRegex(PostBuildAuditError, "REQUIREMENT_RESULT_SET_MISMATCH"):
            verify_post_build_audit(pre, c, a)

    def test_failed_convention_blocks(self):
        c, pre = setup()
        a = audit(c, pre)
        a["convention_results"][0]["pass"] = False
        with self.assertRaisesRegex(PostBuildAuditError, "CONVENTION_FAILED"):
            verify_post_build_audit(pre, c, a)

    def test_missing_scenario_state_blocks(self):
        c, pre = setup()
        a = audit(c, pre)
        a["scenario_results"][0]["realized_states"] = a["scenario_results"][0]["realized_states"][:1]
        with self.assertRaisesRegex(PostBuildAuditError, "SCENARIO_STATE_COVERAGE_MISMATCH"):
            verify_post_build_audit(pre, c, a)

    def test_missing_scenario_rationale_blocks(self):
        c, pre = setup()
        a = audit(c, pre)
        key = next(iter(a["scenario_results"][0]["state_rationales"]))
        a["scenario_results"][0]["state_rationales"].pop(key)
        with self.assertRaisesRegex(PostBuildAuditError, "SCENARIO_RATIONALE_SET_MISMATCH"):
            verify_post_build_audit(pre, c, a)

    def test_unexplained_reconciliation_blocks(self):
        c, pre = setup()
        a = audit(c, pre)
        a["reconciliation_results"][0]["variance_explained"] = False
        with self.assertRaisesRegex(PostBuildAuditError, "RECONCILIATION_VARIANCE_UNEXPLAINED"):
            verify_post_build_audit(pre, c, a)

    def test_missing_source_trace_blocks(self):
        c, pre = setup()
        a = audit(c, pre)
        a["source_traceability"] = a["source_traceability"][:-1]
        with self.assertRaisesRegex(PostBuildAuditError, "SOURCE_TRACE_SET_MISMATCH"):
            verify_post_build_audit(pre, c, a)

    def test_mechanical_integrity_required(self):
        c, pre = setup()
        a = audit(c, pre)
        a["artifacts"][0]["mechanical_integrity_verified"] = False
        with self.assertRaisesRegex(PostBuildAuditError, "ARTIFACT_MECHANICAL_INTEGRITY_UNVERIFIED"):
            verify_post_build_audit(pre, c, a)

    def test_reopen_required(self):
        c, pre = setup()
        a = audit(c, pre)
        a["all_declared_outputs_reopened_after_write"] = False
        with self.assertRaisesRegex(PostBuildAuditError, "OUTPUT_REOPEN_VERIFICATION_MISSING"):
            verify_post_build_audit(pre, c, a)

    def test_freeze_after_audit_required(self):
        c, pre = setup()
        a = audit(c, pre)
        a["freeze_after_audit"] = False
        with self.assertRaisesRegex(PostBuildAuditError, "OUTPUT_NOT_FROZEN_AFTER_AUDIT"):
            verify_post_build_audit(pre, c, a)
