from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as regression
from canonical.runtime import tool_discovery_dynamic_universal_scope_certificate_v1 as cert


class ToolDiscoveryDynamicUniversalScopeV1Tests(unittest.TestCase):
    def test_live_exact_sources_derive_universal_scope_candidate(self):
        out=cert.verify()
        self.assertEqual(out["source_blob_drift"],[],out)
        self.assertTrue(out["universal_scope_proved"],out)
        self.assertTrue(out["scope_atom_satisfied_candidate"],out)
        self.assertEqual(out["basis_kind"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"],"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        good={name:True for name in cert.REQUIRED_FACTS}
        self.assertTrue(cert.prove_from_facts(good)["universal_scope_proved"])
        for name in cert.REQUIRED_FACTS:
            mutant=dict(good)
            mutant[name]=False
            out=cert.prove_from_facts(mutant)
            self.assertFalse(out["universal_scope_proved"],name)
            self.assertIn(name,out["missing"])

    def test_v3_counterexample_v4_discovers_before_expensive_visible_selection(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[
                {"tool_id":"EXPENSIVE_VISIBLE","cost":10.0,"available":True,"authorized":True,"epoch":0}
            ],
            "discovery_sources":[
                {"source_id":"CATALOG","cost":0.0,"available":True}
            ],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE_VISIBLE","capability":"CAP_A","epoch":0,"supported":True}
            ],
            "discovery_receipts":[],
            "version_events":[],
        }
        self.assertEqual(v3.next_action(public)["action"],"SELECT")
        self.assertEqual(v4.next_action(public),{
            "action":"DISCOVER","source_id":"CATALOG","query":"CAP_A"
        })

    def test_v4_selects_global_cheapest_after_complete_discovery(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[
                {"tool_id":"EXPENSIVE_VISIBLE","cost":10.0,"available":True,"authorized":True,"epoch":0},
                {"tool_id":"CHEAP_DISCOVERED","cost":1.0,"available":True,"authorized":True,"epoch":0},
            ],
            "discovery_sources":[{"source_id":"CATALOG","cost":0.0,"available":True}],
            "discovery_receipts":[{"kind":"DISCOVERY_RESULT","source_id":"CATALOG"}],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE_VISIBLE","capability":"CAP_A","epoch":0,"supported":True},
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP_DISCOVERED","capability":"CAP_A","epoch":0,"supported":True},
            ],
            "version_events":[],
        }
        self.assertEqual(v4.next_action(public),{
            "action":"SELECT","tool_id":"CHEAP_DISCOVERED"
        })

    def test_stale_positive_receipt_is_not_promoted(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[
                {"tool_id":"X","cost":1.0,"available":True,"authorized":True,"epoch":0}
            ],
            "discovery_sources":[],
            "discovery_receipts":[],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"X","capability":"CAP_A","epoch":0,"supported":True}
            ],
            "version_events":[
                {"kind":"TOOL_VERSION_CHANGED","tool_id":"X","new_epoch":1}
            ],
        }
        self.assertEqual(v4.next_action(public),{
            "action":"PROBE","tool_id":"X","capability":"CAP_A"
        })

    def test_v4_preserves_existing_dynamic_v3_regression_grid(self):
        out=regression.run_batch(20261003,120,v4.next_action)
        self.assertTrue(out["pass"],out["failures"][:5])
        self.assertEqual(out["failed"],0)
        self.assertEqual(set(out["classes"]),set(regression.CLASSES))

    def test_discovery_order_mutation_kills_scope_fact(self):
        src=cert._text(cert.CANDIDATE)
        mutant=src.replace("if sources:","if False and sources:",1)
        facts=cert.derive_source_facts(mutant)
        self.assertFalse(facts["DISCOVERY_EXHAUSTS_AVAILABLE_SOURCES"])

    def test_hardcoded_identity_kills_parametricity_fact(self):
        src=cert._text(cert.CANDIDATE)+'\nHARDCODED="T0"\n'
        facts=cert.derive_source_facts(src)
        self.assertFalse(facts["OPAQUE_IDENTITY_PARAMETRIC"])

    def test_cost_order_mutation_kills_global_order_fact(self):
        src=cert._text(cert.CANDIDATE)
        mutant=src.replace(
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))',
            'tools.sort(key=lambda t:str(t.get("tool_id") or ""))',
            1,
        )
        facts=cert.derive_source_facts(mutant)
        self.assertFalse(facts["DETERMINISTIC_GLOBAL_COST_ORDER"])


if __name__=="__main__":
    unittest.main(verbosity=2)
