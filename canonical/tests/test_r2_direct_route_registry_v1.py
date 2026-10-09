from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import r2_direct_end_to_end_adequacy_v8 as legacy_v8
from canonical.runtime import r2_direct_route_registry_v1 as registry_router


ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"

EXPECTED_ORDER = [
    "DIRECT_ADEQUACY::FINANCE_EXPLICIT_ORDERED_PAIR_FORMER_LATTER_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_BOUNDED_CONTEXTUAL_REFERENCE_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_STATE_KEYED_EXTERNAL_JSON_POLICY_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_EXPLICIT_ALIAS_TYPED_UNLESS_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_CROSS_DOCUMENT_JSON_BINDING_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_EXPLICIT_DEFINITION_UNLESS_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_NORMALIZED_IF_BRANCH_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_NORMALIZED_SOURCE_UNIVERSE_DECISION_FAMILY_V1",
    "DIRECT_ADEQUACY::ARCHIVE_MANIFEST_TAR_GZ_V1",
    "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1",
    "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1",
    "DIRECT_ADEQUACY::EXACT_ROR_AUTHORITY_IDENTITY_FAMILY_V1",
    "DIRECT_ADEQUACY::PROVENANCE_KNOWLEDGE_CONSISTENCY_FAMILY_V1",
    "DIRECT_ADEQUACY::UNIT_NORMALIZED_GROUNDED_NUMERIC_COMPARISON_FAMILY_V1",
    "DIRECT_ADEQUACY::EXPLICIT_GROUNDED_NUMERIC_COMPARISON_FAMILY_V1",
    "DIRECT_ADEQUACY::EXACT_GROUNDED_EVIDENCE_CLAIM_SUPPORT_FAMILY_V1",
    "DIRECT_ADEQUACY::PYPI_PINNED_ARTIFACT_PROVENANCE_FAMILY_V1",
    "DIRECT_ADEQUACY::STATE_KEYED_HTTPS_JSON_OBSERVATION_FAMILY_V1",
    "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1",
    "DIRECT_ADEQUACY::PLAIN_MARKDOWN_PDF_FAMILY_V1",
    "DIRECT_ADEQUACY::VISUAL_CODE_QR_CODE128_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_CONTROLLED_TYPED_UNLESS_FAMILY_V1",
    "DIRECT_ADEQUACY::FINANCE_NORMALIZED_UNLESS_BRANCH_FAMILY_V1",
    "DIRECT_ADEQUACY::TYPED_EVIDENCE_DECISION_FAMILY_V1",
    "DIRECT_ADEQUACY::STRUCTURED_TABLE_ARTIFACT_FAMILY_V1",
    "DIRECT_ADEQUACY::STRUCTURED_BINARY_CODEC_FAMILY_V1",
    "DIRECT_ADEQUACY::LITERAL_DOCX_OOXML_FAMILY_V1",
    "DIRECT_ADEQUACY::DOCX_JSON_RECORD_FAMILY_V1",
]


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class R2DirectRouteRegistryV1Tests(unittest.TestCase):
    def test_current_pointer_binds_immutable_selection_metadata(self):
        registry = registry_router.load_registry()
        self.assertEqual(registry["route_count"], 28)
        self.assertEqual(len(registry["routes"]), 28)
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        target = ROOT / pointer["target"]["path"]
        self.assertEqual(git_blob_sha(target), pointer["target"]["git_blob_sha"])
        self.assertEqual(
            pointer["role"],
            "LEGACY_PRECEDENCE_METADATA_ONLY__DEPLOYABLE_UNIVERSE_COMES_FROM_CURRENT_R2_ACTIVATION",
        )

    def test_current_effective_universe_has_exact_28_verified_routes(self):
        state = registry_router.effective_state()
        self.assertEqual(state["deployable_route_count"], 28)
        self.assertEqual(state["baseline_activation_route_count"], 28)
        self.assertEqual(state["dynamic_admission_route_count"], 0)
        self.assertEqual(state["legacy_selection_metadata_count"], 28)
        self.assertEqual(state["auto_admitted_route_count"], 0)
        self.assertEqual(state["stale_selection_metadata_route_ids"], [])
        self.assertEqual(set(state["deployable_route_ids"]), set(legacy_v8.ROUTES))

    def test_migration_preserves_exact_v8_to_v1_precedence(self):
        registry = registry_router.load_registry()
        observed = [
            row["route_id"]
            for row in sorted(registry["routes"], key=lambda row: row["priority"])
        ]
        self.assertEqual(observed, EXPECTED_ORDER)

    def test_exact_literal_preflight_is_behaviorally_equivalent(self):
        request = {"task_id": "literal-equivalence", "goal": 'Reply with exactly "hello".'}
        old = legacy_v8.preflight(request)
        new = registry_router.preflight(request)
        self.assertTrue(old.get("matched"))
        self.assertTrue(new.get("matched"))
        self.assertEqual(new.get("route_id"), old.get("route_id"))
        self.assertEqual(new.get("capability_id"), old.get("capability_id"))
        self.assertEqual(new.get("goal_sha256"), old.get("goal_sha256"))
        self.assertEqual(new.get("semantic_scope"), old.get("semantic_scope"))

    def test_nonmatching_request_falls_through_equivalently(self):
        request = {
            "task_id": "registry-no-match",
            "goal": "Analyze this deliberately unstructured request with no bounded direct-route syntax.",
        }
        old = legacy_v8.preflight(request)
        new = registry_router.preflight(request)
        self.assertIs(old.get("matched"), False)
        self.assertIs(new.get("matched"), False)

    def test_dynamic_activation_route_derives_unique_match_fail_closed_policy(self):
        activation = registry_router.load_current_activation()
        row = next(
            r for r in activation["routes"]
            if r.get("runtime") and isinstance(r.get("verification"), dict)
        )
        derived = registry_router._derive_dynamic_row(
            row,
            activation_index=0,
            root=ROOT,
        )
        self.assertEqual(derived["route_id"], row["route_id"])
        self.assertEqual(
            derived["selection_class"],
            registry_router.DYNAMIC_SELECTION_CLASS,
        )
        self.assertTrue(derived["automatic_live_admission"])
        self.assertEqual(
            derived["collision_policy"],
            "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
        )

    def test_dynamic_collision_fails_closed_without_executing_priority_guess(self):
        dynamic_a={"route_id":"DYN_A","selection_class":registry_router.DYNAMIC_SELECTION_CLASS,"activation_index":0}
        dynamic_b={"route_id":"DYN_B","selection_class":registry_router.DYNAMIC_SELECTION_CLASS,"activation_index":1}
        state={
            "rows":[dynamic_a,dynamic_b],
            "deployable_route_ids":["DYN_A","DYN_B"],
            "legacy_selection_metadata_route_ids":[],
            "auto_admitted_route_ids":["DYN_A","DYN_B"],
            "stale_selection_metadata_route_ids":[],
            "deployable_route_count":2,
            "legacy_selection_metadata_count":0,
            "auto_admitted_route_count":2,
            "current_activation_path":"x",
            "current_activation_git_blob_sha":"y",
        }
        def fake_pf(row, request, repo_root):
            return {"matched":True,"route_id":row["route_id"]}
        with mock.patch.object(registry_router,"effective_state",return_value=state):
            with mock.patch.object(registry_router,"_preflight_row",side_effect=fake_pf):
                out=registry_router.preflight({"task_id":"t","goal":"g"})
        self.assertEqual(out["status"],"FAIL_CLOSED__DIRECT_ROUTE_COLLISION")
        self.assertEqual(out["matching_route_ids"],["DYN_A","DYN_B"])

    def test_fixed_point_no_longer_depends_on_version_chained_router(self):
        source = FIXED_POINT.read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy",
            source,
        )
        self.assertNotIn(
            "from canonical.runtime import r2_direct_end_to_end_adequacy_v8 as direct_adequacy",
            source,
        )

    def test_future_route_growth_requires_neither_source_nor_registry_edit(self):
        catalog = registry_router.catalog()
        self.assertTrue(catalog["pass"])
        self.assertEqual(catalog["route_count"], 28)
        self.assertIs(catalog["future_route_source_edit_required"], False)
        self.assertIs(catalog["future_route_registry_edit_required"], False)
        self.assertIs(catalog["future_route_current_r2_edit_required"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
