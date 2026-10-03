from __future__ import annotations

import copy
import hashlib
import json
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_complete_interface_candidate_v4 as v4
from canonical.runtime.tool_discovery_universal_scope_certificate_v2 import (
    REQUIRED_FACTS,
    ROOT,
    _load,
    _text,
    derive_source_facts,
    prove_from_facts,
    verify,
)


def _manifest(sources):
    rows = sorted(
        [
            {
                "source_id": x["source_id"],
                "epoch": x["epoch"],
                "cost": float(x["cost"]),
                "available": x["available"],
                "authorized": x["authorized"],
            }
            for x in sources
        ],
        key=lambda x: x["source_id"],
    )
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _context():
    return {
        "relation": _load("canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_SCOPE_RELATION_V1.json"),
        "registry": _load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        "protocol": _load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
        "terminal_binding": _load("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"),
        "firewall": _load("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"),
        "cut": _load("canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"),
        "bindings": _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
    }


def _facts(v4_source=None, v3_source=None, relation=None):
    c = _context()
    return derive_source_facts(
        v4_source if v4_source is not None else _text("canonical/runtime/tool_discovery_complete_interface_candidate_v4.py"),
        _text("canonical/runtime/tool_discovery_information_safe_candidate.py"),
        v3_source if v3_source is not None else _text("canonical/runtime/tool_discovery_dynamic_candidate_v3.py"),
        relation if relation is not None else c["relation"],
        c["registry"],
        c["protocol"],
        c["terminal_binding"],
        c["firewall"],
        c["cut"],
        c["bindings"],
    )


class ToolDiscoveryUniversalScopeV2Tests(unittest.TestCase):
    def test_live_exact_sources_derive_candidate_universal_scope_proof(self):
        out = verify()
        self.assertEqual(out["source_blob_drift"], [])
        self.assertTrue(out["universal_scope_proved"], out)
        self.assertTrue(out["scope_atom_satisfied_candidate"], out)
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"], "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        good = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(good)["universal_scope_proved"])
        for name in REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = prove_from_facts(mutant)
            self.assertFalse(out["universal_scope_proved"], name)
            self.assertIn(name, out["missing"])

    def test_v3_has_real_pre_discovery_least_cost_counterexample_and_v4_removes_it(self):
        visible = {
            "tool_id": "VISIBLE_EXPENSIVE",
            "cost": 10.0,
            "epoch": 0,
            "available": True,
            "authorized": True,
            "safe_probe_allowed": True,
        }
        old_public = {
            "required_capabilities": ["CAP"],
            "visible_tools": [visible],
            "prior_probe_receipts": [
                {
                    "kind": "SAFE_CAPABILITY_PROBE",
                    "tool_id": "VISIBLE_EXPENSIVE",
                    "capability": "CAP",
                    "epoch": 0,
                    "supported": True,
                }
            ],
            "version_events": [],
            "discovery_sources": [{"source_id": "S", "cost": 0.0, "available": True}],
            "discovery_receipts": [],
        }
        self.assertEqual(v3.next_action(old_public)["action"], "SELECT")

        sources = [
            {"source_id": "S", "epoch": 0, "cost": 0.0, "available": True, "authorized": True}
        ]
        new_public = {
            "required_capabilities": ["CAP"],
            "tools": [visible],
            "prior_probe_receipts": list(old_public["prior_probe_receipts"]),
            "version_events": [],
            "discovery_registry": {
                "kind": "COMPLETE_DISCOVERY_REGISTRY",
                "complete": True,
                "epoch": 0,
                "sources": sources,
                "source_manifest_sha256": _manifest(sources),
            },
            "discovery_receipts": [],
        }
        first = v4.next_action(new_public)
        self.assertEqual(first["action"], "DISCOVER")
        self.assertEqual(first["source_id"], "S")

        new_public["discovery_receipts"] = [{
            "kind": "DISCOVERY_RESULT",
            "source_id": "S",
            "registry_epoch": 0,
            "source_epoch": 0,
            "complete": True,
            "tools": [{
                "tool_id": "NEW_CHEAP",
                "cost": 1.0,
                "epoch": 0,
                "available": True,
                "authorized": True,
                "safe_probe_allowed": True,
            }],
        }]
        new_public["prior_probe_receipts"].append({
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "NEW_CHEAP",
            "capability": "CAP",
            "epoch": 0,
            "supported": True,
        })
        self.assertEqual(
            v4.next_action(new_public),
            {"action": "SELECT", "tool_id": "NEW_CHEAP", "epoch": 0},
        )

    def test_source_mutations_kill_their_formal_premises(self):
        source = _text("canonical/runtime/tool_discovery_complete_interface_candidate_v4.py")

        mutant = source.replace(
            'if "discovery_registry" not in public:',
            'if False and "discovery_registry" not in public:',
        )
        self.assertFalse(_facts(v4_source=mutant)["LEGACY_EXACT_PROJECTION"])

        mutant = source.replace(
            '"authorized": x["authorized"]',
            '"authorized_OMITTED": x["authorized"]',
        )
        self.assertFalse(
            _facts(v4_source=mutant)["REGISTRY_MANIFEST_BINDS_LOAD_BEARING_SOURCE_FIELDS"]
        )

        mutant = source.replace(
            'if tool.get("safe_probe_allowed") is not True:',
            'if False:',
        )
        self.assertFalse(_facts(v4_source=mutant)["SAFE_PROBE_AUTHORITY_ENFORCED"])

        mutant = source.replace(
            'eligible.sort(key=lambda x: (float(x["cost"]), str(x["tool_id"])))',
            'eligible.sort(key=lambda x: str(x["tool_id"]))',
        )
        self.assertFalse(
            _facts(v4_source=mutant)["GLOBAL_LEAST_COST_PROVED_SUFFICIENT_SELECTION"]
        )

    def test_interface_completeness_input_boolean_cannot_self_certify_theorem(self):
        relation = copy.deepcopy(_context()["relation"])
        relation["hard_nonclaims"] = [
            x for x in relation["hard_nonclaims"]
            if x != "THE_REGISTRY_COMPLETE_FIELD_DOES_NOT_SELF_CERTIFY_INTERFACE_COMPLETENESS"
        ]
        self.assertFalse(
            _facts(relation=relation)["INTERFACE_COMPLETENESS_NOT_SELF_CERTIFIED_BY_INPUT_FLAG"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
