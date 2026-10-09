from __future__ import annotations
import unittest

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import cross_document_residual_effect_frontier_v1 as f
from canonical.runtime import cross_document_residual_effect_frontier_verify_v1 as verify


def _e(eid,target,value):
    return {
        "effect_id":eid,
        "target_id":target,
        "effect_class":"DEFINE",
        "value":value,
        "conditions":{},
        "valid_from":None,
        "valid_until":None,
        "supersedes":[],
        "source_locator":"section:"+eid,
    }


def _slot(slot_id,*effects):
    return {
        "slot_id":slot_id,
        "hypothesis_set_complete":True,
        "hypotheses":[
            {"hypothesis_id":f"{slot_id}.h{i+1}","effect":effect}
            for i,effect in enumerate(effects)
        ],
    }


def _worldset(*effects,target="reporting.threshold"):
    return {
        "schema":w.SCHEMA,
        "case_id":"residual",
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":[
            {
                "document_id":"A",
                "effect_slots":[_slot("A.effect",*effects)],
            }
        ],
        "query":{
            "target_id":target,
            "as_of":"2026-10-09",
            "context":{},
        },
    }


def _source(
    text,
    *,
    scope_claim=None,
    inventory_claims=None,
):
    return {
        "document_id":"A",
        "source_id":"source-A",
        "source_text":text,
        "scope_claim":scope_claim,
        "inventory_claims":inventory_claims or [],
    }


def _problem(source,ws):
    return {
        "schema":f.SCHEMA,
        "case_id":"residual-frontier",
        "source_documents":[source],
        "worldset_problem":ws,
    }


class CrossDocumentResidualEffectFrontierV1Tests(unittest.TestCase):
    def test_unproved_raw_source_blocks_even_when_finite_worldset_passes(self):
        ws=_worldset(_e("A.t","reporting.threshold","10"))
        out=f.evaluate(_problem(
            _source("The threshold is ten."),
            ws,
        ))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__RESIDUAL_TOP_EFFECT_MAY_CHANGE_QUERY",
        )
        self.assertEqual(out["blocking_residual_document_ids"],["A"])
        self.assertTrue(verify.verify(_problem(_source("The threshold is ten."),ws),out)["verified"])
        self.assertEqual(
            out["finite_worldset_preview"]["effective_value"],
            "10",
        )
        self.assertEqual(
            out["next_proof_obligations"][0]["kind"],
            "PROVE_EFFECT_TARGET_SCOPE_OR_QUERY_EFFECT_ID_INVENTORY",
        )

    def test_exact_inventory_closes_residual_and_allows_finite_pass(self):
        ws=_worldset(_e("A.t","reporting.threshold","10"))
        text="Effect IDs only for reporting.threshold: A.t."
        source=_source(
            text,
            inventory_claims=[{
                "claim_id":"inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":"reporting.threshold",
                "effect_ids":["A.t"],
            }],
        )
        out=f.evaluate(_problem(source,ws))
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["status"],
            "PASS__RESIDUAL_TOP_CLOSED_FOR_QUERY_AND_FINITE_WORLDSET_PASSED",
        )
        self.assertEqual(out["effective_value"],"10")
        self.assertTrue(verify.verify(_problem(source,ws),out)["verified"])
        self.assertEqual(
            out["residuals"][0]["state"],
            "PROVED_QUERY_EFFECT_ID_INVENTORY_EXHAUSTIVE",
        )

    def test_exact_inventory_closes_omission_risk_but_not_value_ambiguity(self):
        ws=_worldset(
            _e("A.t","reporting.threshold","10"),
            _e("A.t","reporting.threshold","11"),
        )
        text="Effect IDs only for reporting.threshold: A.t."
        source=_source(
            text,
            inventory_claims=[{
                "claim_id":"inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":"reporting.threshold",
                "effect_ids":["A.t"],
            }],
        )
        out=f.evaluate(_problem(source,ws))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__RESIDUAL_TOP_CLOSED_FOR_QUERY__FINITE_WORLDSET_NOT_CLOSED",
        )
        self.assertEqual(
            set(out["finite_worldset_result"]["possible_outcomes"]),
            {"10","11"},
        )
        self.assertEqual(
            out["minimum_discriminator_slots"],
            ["A.effect"],
        )
        self.assertTrue(verify.verify(_problem(source,ws),out)["verified"])

    def test_inventory_mismatch_fails_closed(self):
        ws=_worldset(_e("A.t","reporting.threshold","10"))
        text="Effect IDs only for reporting.threshold: B.t."
        source=_source(
            text,
            inventory_claims=[{
                "claim_id":"inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":"reporting.threshold",
                "effect_ids":["B.t"],
            }],
        )
        out=f.evaluate(_problem(source,ws))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__MODELED_EFFECTS_INCONSISTENT_WITH_SOURCE_PROOF",
        )
        self.assertEqual(
            out["scope_consistency_errors"][0]["reason"],
            "MODELED_EFFECT_ID_INVENTORY_MISMATCH",
        )

    def test_scope_exclusion_discharges_query_residual(self):
        ws=_worldset(_e("A.other","other.target","x"))
        text="Effect targets only: other.target."
        source=_source(
            text,
            scope_claim={
                "claim_id":"scope",
                "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                "target_ids":["other.target"],
            },
        )
        out=f.evaluate(_problem(source,ws))
        self.assertFalse(out["pass"])
        self.assertEqual(out["blocking_residual_document_ids"],[])
        self.assertEqual(
            out["residuals"][0]["state"],
            "PROVED_QUERY_IRRELEVANT",
        )
        self.assertEqual(
            out["status"],
            "OPEN__RESIDUAL_TOP_CLOSED_FOR_QUERY__FINITE_WORLDSET_NOT_CLOSED",
        )

    def test_modeled_target_outside_proved_scope_fails_closed(self):
        ws=_worldset(_e("A.t","reporting.threshold","10"))
        text="Effect targets only: other.target."
        source=_source(
            text,
            scope_claim={
                "claim_id":"scope",
                "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                "target_ids":["other.target"],
            },
        )
        out=f.evaluate(_problem(source,ws))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__MODELED_EFFECTS_INCONSISTENT_WITH_SOURCE_PROOF",
        )

    def test_wrong_inventory_claim_does_not_discharge_residual(self):
        ws=_worldset(_e("A.t","reporting.threshold","10"))
        text="Effect IDs only for reporting.threshold: A.t."
        source=_source(
            text,
            inventory_claims=[{
                "claim_id":"inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":"reporting.threshold",
                "effect_ids":["X.t"],
            }],
        )
        out=f.evaluate(_problem(source,ws))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__RESIDUAL_TOP_EFFECT_MAY_CHANGE_QUERY",
        )
        self.assertEqual(out["blocking_residual_document_ids"],["A"])

    def test_source_and_worldset_document_sets_must_match(self):
        ws=_worldset(_e("A.t","reporting.threshold","10"))
        source=_source("Effect IDs only for reporting.threshold: A.t.")
        source["document_id"]="B"
        out=f.evaluate(_problem(source,ws))
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_WORLDSET_DOCUMENT_ID_MISMATCH",out["reason"])


if __name__=="__main__":
    unittest.main()
