from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import regcap_context_selection_v1 as producer
from canonical.runtime import regcap_context_selection_verify_v1 as verifier
from canonical.runtime import r2_regcap_context_selection_direct_adequacy_v1 as direct
from canonical.runtime import r2_direct_end_to_end_adequacy_v21 as v21
from canonical.runtime import general_adequate_decision_fixed_point_v2 as fp
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"])
                for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


def case(text, source_id="doc:A"):
    return {
        "schema": verifier.CASE_SCHEMA,
        "source_id": source_id,
        "source_text": text,
    }


def ccob_text():
    return (
        "The loss-absorbing cushion is a 2.5% CET1 buffer "
        "above the regulatory minimum capital requirement."
    )


def ccyb_text():
    return (
        "The loss-absorbing cushion is released when system-wide risk "
        "crystallises or dissipates."
    )


def tlac_text():
    return (
        "For a G-SIB, the loss-absorbing cushion provides loss-absorbing "
        "and recapitalisation capacity available in resolution."
    )


def goal(inp="canonical/tmp/regcap_context_case.json", out="canonical/tmp/regcap_context_result.json"):
    return (
        "Using the bounded regulatory-capital context case at "
        + inp
        + ', identify which of CCoB, CCyB, and TLAC is selected for '
        + '"loss-absorbing cushion" and save the independently verified '
        + "bounded selection to "
        + out
        + "."
    )


def write_case(root: Path, text: str):
    p = root / "canonical/tmp/regcap_context_case.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(case(text)), encoding="utf-8")
    return p


def compute_fake(c, *, repo_root=None):
    return producer.compute(
        c,
        repo_root=repo_root,
        projection_verifier=fake_projection,
    )


def verify_fake(c, result, *, repo_root=None):
    return verifier.verify(
        c,
        result,
        repo_root=repo_root,
        projection_verifier=fake_projection,
    )


class ProducerVerifierTests(unittest.TestCase):
    def test_ccob_context_selects_ccob_and_independently_verifies(self):
        c = case(ccob_text())
        out = compute_fake(c)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCOB)
        checked = verify_fake(c, out)
        self.assertTrue(checked["verified"], checked)
        self.assertEqual(checked["expected_concept_id"], regcap.CCOB)

    def test_ccyb_context_selects_ccyb_and_independently_verifies(self):
        c = case(ccyb_text())
        out = compute_fake(c)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCYB)
        checked = verify_fake(c, out)
        self.assertTrue(checked["verified"], checked)

    def test_tlac_context_selects_tlac_and_independently_verifies(self):
        c = case(tlac_text())
        out = compute_fake(c)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.TLAC)
        checked = verify_fake(c, out)
        self.assertTrue(checked["verified"], checked)

    def test_generic_context_stays_open(self):
        c = case("The loss-absorbing cushion may be useful during stress.")
        out = compute_fake(c)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__BOUND_REGCAP_CONTEXT_SELECTION_UNRESOLVED",
        )
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["global_phrase_identity_authority"])

    def test_multiple_descriptor_occurrences_stay_open(self):
        c = case(
            "One loss-absorbing cushion exists. "
            "Another loss-absorbing cushion exists."
        )
        out = compute_fake(c)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__EXACTLY_ONE_DESCRIPTOR_OCCURRENCE_REQUIRED",
        )

    def test_independent_verifier_rejects_tampered_selection(self):
        c = case(ccyb_text())
        out = compute_fake(c)
        tampered = dict(out)
        tampered["selected_concept_id"] = regcap.TLAC
        checked = verify_fake(c, tampered)
        self.assertFalse(checked["verified"])
        self.assertIn("SELECTED_CONCEPT_MISMATCH", checked["errors"])

    def test_verifier_preserves_no_global_identity_boundary(self):
        c = case(ccob_text())
        out = compute_fake(c)
        checked = verify_fake(c, out)
        self.assertTrue(checked["verified"], checked)
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["global_phrase_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        self.assertFalse(checked["semantic_identity_authority"])
        self.assertFalse(checked["global_phrase_identity_authority"])


class DirectRouteTests(unittest.TestCase):
    def test_exact_route_closes_transactionally(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
            direct.producer, "compute", side_effect=compute_fake
        ), patch.object(
            direct.verifier, "verify", side_effect=verify_fake
        ):
            root = Path(td)
            write_case(root, ccyb_text())
            out = direct.run({"task_id": "x", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["selected_concept_id"], regcap.CCYB)
            self.assertTrue(out["semantic_acceptance_complete"])
            self.assertTrue(out["actual_goal_satisfaction_verified"])
            saved = json.loads(
                (root / "canonical/tmp/regcap_context_result.json").read_text()
            )
            self.assertEqual(saved["selected_concept_id"], regcap.CCYB)
            self.assertFalse(saved["global_phrase_identity_authority"])
            self.assertFalse(saved["open_world_candidate_set_complete"])

    def test_unresolved_case_surfaces_semantic_open_not_match(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
            direct.producer, "compute", side_effect=compute_fake
        ):
            root = Path(td)
            write_case(root, "The loss-absorbing cushion may be useful.")
            out = direct.preflight(
                {"task_id": "x", "goal": goal()},
                repo_root=root,
            )
            self.assertFalse(out["matched"])
            self.assertTrue(out["direct_route_semantic_open"])
            self.assertEqual(
                out["status"],
                "OPEN__REGCAP_CONTEXT_SELECTION_NOT_YET_PROVED",
            )

    def test_verifier_failure_rolls_back_existing_output(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
            direct.producer, "compute", side_effect=compute_fake
        ):
            root = Path(td)
            write_case(root, tlac_text())
            op = root / "canonical/tmp/regcap_context_result.json"
            op.write_text('{"old":true}\n', encoding="utf-8")
            old = op.read_bytes()
            calls = {"n": 0}

            def injected(c, result, *, repo_root=None):
                calls["n"] += 1
                if calls["n"] <= 2:
                    return verify_fake(c, result, repo_root=repo_root)
                return {
                    "verified": False,
                    "producer_independent": True,
                    "errors": ["forced"],
                }

            with patch.object(direct.verifier, "verify", side_effect=injected):
                out = direct.run(
                    {"task_id": "x", "goal": goal()},
                    repo_root=root,
                )
            self.assertFalse(out["pass"])
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(), old)

    def test_nonmatching_goal_delegates_to_v20(self):
        req = {"task_id": "x", "goal": "Unrelated task."}
        expected = {"matched": False, "status": "V20"}
        with patch.object(v21.v20, "preflight", return_value=expected) as prior:
            out = v21.preflight(req)
        self.assertEqual(out, expected)
        prior.assert_called_once()

    def test_v21_selects_regcap_route_before_v20(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
            direct.producer, "compute", side_effect=compute_fake
        ), patch.object(
            direct.verifier, "verify", side_effect=verify_fake
        ), patch.object(v21.v20, "preflight") as prior:
            root = Path(td)
            write_case(root, ccob_text())
            out = v21.preflight(
                {"task_id": "x", "goal": goal()},
                repo_root=root,
            )
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.ROUTE_ID)
        prior.assert_not_called()

    def test_fixed_point_uses_v21_direct_route(self):
        request = {"task_id": "x", "goal": goal()}
        direct_result = {
            "pass": True,
            "matched": True,
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "route_id": direct.ROUTE_ID,
            "execution_attempted": True,
        }
        with patch.object(
            fp.direct_adequacy,
            "preflight",
            return_value={"matched": True, "route_id": direct.ROUTE_ID},
        ), patch.object(
            fp.direct_adequacy,
            "run",
            return_value=direct_result,
        ):
            out = fp.run(request)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
        )
        self.assertEqual(
            out["r2_fixed_point_trace"][0]["route_id"],
            direct.ROUTE_ID,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
