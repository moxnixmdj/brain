from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import tempfile
import zipfile
from unittest.mock import patch
import unittest

from canonical.runtime import professional_quality_p1_router_v4 as r


def contract():
    return {
        "behavior_id": r.target_sem.BEHAVIOR_ID,
        "inputs": "User objective, audience, source evidence, artifact type, constraints and current draft/render",
        "environment_state": "professional state",
        "allowed_information": "constraints and evidence",
        "required_output_or_action": "choose a plan",
        "success_condition": "quality improves",
        "failure_condition": "quality does not improve",
        "terminal_consequence": "professional task outcome",
        "verification_route": "independent evaluation",
        "dependency_boundary": "declared dependencies",
        "scope": "professional artifacts",
    }


def registry():
    return {"active_contracted_residuals": [contract()]}


def profile():
    return {
        "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_V3",
        "behavior_id": r.target_sem.BEHAVIOR_ID,
    }


def target():
    return {
        "objective": "Improve the report",
        "audience": "executives",
        "source_evidence": ["source-a"],
        "artifact_type": "DOCX",
        "constraints": ["no unsupported claims"],
        "current_draft_or_render": "draft-v1",
    }


def loader(root, rel, blob):
    if rel == r.PROFILE_PATH:
        return profile()
    if rel == r.CONTRACT_REGISTRY_PATH:
        return registry()
    raise AssertionError(rel)


class ProfessionalQualityP1RouterV4Tests(unittest.TestCase):
    def _write_docx(self, path: Path, text: str) -> None:
        content_types = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>'
        ).encode()
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>'
        ).encode()
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("word/document.xml", body)

    def _all_v1_steps_pass(self):
        root = Path(__file__).resolve().parents[2]
        p = root / "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json"
        profile = json.loads(p.read_text())
        return {step: "PASS" for step in profile["steps"]}

    def test_missing_target_instance_fails_closed(self):
        out = r.route({})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_INSTANCE_NOT_OBJECT")

    def test_missing_target_field_fails_closed(self):
        t = target()
        t.pop("audience")
        out = r.route({"target_instance": t})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_INSTANCE_MISSING_FIELDS:audience", out["reason"])

    def test_unknown_target_field_fails_closed(self):
        t = target()
        t["mystery"] = 1
        out = r.route({"target_instance": t})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_INSTANCE_UNKNOWN_FIELDS:mystery", out["reason"])

    @patch.object(r, "_load_json_bound", side_effect=loader)
    @patch.object(r.base, "route")
    def test_valid_target_binds_exact_instance_before_v3(self, base_route, _load):
        base_route.return_value = {
            "status": "ROUTE__P1_ORDINARY",
            "route": "P1",
            "quality_authority": False,
            "terminal_authority": False,
        }
        state = {"target_instance": target(), "detected_triggers": [], "step_results": {}}
        out = r.route(state)
        self.assertTrue(out["target_instance_bound"], out)
        self.assertEqual(
            out["target_instance_binding"]["target_instance_sha256"],
            r._digest(target()),
        )
        self.assertEqual(
            out["target_instance_binding"]["contract_sha256"],
            r.target_sem.digest(contract()),
        )
        delegated = base_route.call_args.args[0]
        self.assertNotIn("target_instance", delegated)
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    @patch.object(r, "_load_json_bound")
    def test_profile_behavior_drift_fails_closed(self, load):
        bad = profile()
        bad["behavior_id"] = "OTHER"
        load.side_effect = [bad, registry()]
        out = r.route({"target_instance": target()})
        self.assertEqual(out["reason"], "PROFILE_BEHAVIOR_ID_MISMATCH")

    @patch.object(r, "_load_json_bound", side_effect=loader)
    @patch.object(r.target_sem, "certify")
    def test_semantic_certificate_failure_blocks_routing(self, certify, _load):
        certify.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["CONTRACT_DRIFT"],
        }
        out = r.route({"target_instance": target()})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_SEMANTIC_CERTIFICATE_FAILED")

    def test_target_bound_preflight_self_attestation_is_still_forbidden(self):
        out = r.route({
            "target_instance": target(),
            "step_results": {r.base.PREFLIGHT_STEP: "PASS"},
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PREFLIGHT_SELF_ATTESTATION_FORBIDDEN")

    def test_target_bound_preflight_input_pair_is_still_required(self):
        for state in (
            {"artifact_paths": ["a.docx"], "step_results": {}},
            {"hard_defect_profile_id": "BRAIN_PROFESSIONAL_OOXML_SANITY_V1", "step_results": {}},
        ):
            state = {**state, "target_instance": target()}
            with self.subTest(state=state):
                out = r.route(state)
                self.assertEqual(out["status"], "FAIL_CLOSED")
                self.assertEqual(out["reason"], "PREFLIGHT_INPUT_PAIR_REQUIRED")

    def test_actual_clean_docx_preserves_v3_success_with_target_binding(self):
        with tempfile.TemporaryDirectory() as td:
            artifact = Path(td) / "clean.docx"
            self._write_docx(artifact, "Hello")
            out = r.route({
                "target_instance": target(),
                "artifact_paths": [str(artifact)],
                "hard_defect_profile_id": "BRAIN_PROFESSIONAL_OOXML_SANITY_V1",
                "step_results": self._all_v1_steps_pass(),
                "detected_triggers": [],
            })
        self.assertEqual(out["status"], "ROUTE__P1_ORDINARY", out)
        self.assertEqual(out["route"], "P1")
        self.assertTrue(out["target_instance_bound"])
        self.assertTrue(out["hard_defect_preflight_result"]["pass"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_actual_blank_docx_preserves_v3_hard_failure_with_target_binding(self):
        with tempfile.TemporaryDirectory() as td:
            artifact = Path(td) / "blank.docx"
            self._write_docx(artifact, "")
            out = r.route({
                "target_instance": target(),
                "artifact_paths": [str(artifact)],
                "hard_defect_profile_id": "BRAIN_PROFESSIONAL_OOXML_SANITY_V1",
                "step_results": self._all_v1_steps_pass(),
                "detected_triggers": [],
            })
        self.assertEqual(out["status"], "ABSTAIN__P1_HARD_FAILURE", out)
        self.assertEqual(out["route"], "ABSTAIN")
        self.assertTrue(out["target_instance_bound"])
        self.assertFalse(out["hard_defect_preflight_result"]["pass"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main()
