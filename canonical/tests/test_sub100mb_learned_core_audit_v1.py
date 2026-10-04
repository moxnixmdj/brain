from __future__ import annotations

import copy
import unittest

from canonical.runtime.sub100mb_learned_core_audit_v1 import (
    INPUT_SCHEMA,
    LEARNED_STATE_BUDGET_BYTES,
    audit_sub100mb_contract,
)


def base():
    return {
        "schema": INPUT_SCHEMA,
        "persistent_state_components": [
            {"id": "kernel", "class": "LEARNED", "bytes": 70_000_000},
            {"id": "router", "class": "LEARNED", "bytes": 5_000_000},
            {"id": "program_library", "class": "DETERMINISTIC", "bytes": 500_000_000},
            {"id": "knowledge_index", "class": "EXTERNAL_KNOWLEDGE", "bytes": 2_000_000_000},
        ],
        "scored_execution": {
            "external_learned_capability_providers": [],
            "external_knowledge_sources": ["knowledge://public-corpus"],
        },
        "atomic_predicates": [
            {"id": f"P{i:02d}", "accepted": True} for i in range(38)
        ],
        "capability_families": [
            {"id": f"F{i:02d}", "accepted": True} for i in range(19)
        ],
    }


class Sub100MBLearnedCoreAuditTests(unittest.TestCase):
    def test_exact_success(self):
        out = audit_sub100mb_contract(base())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["learned_state_bytes"], 75_000_000)

    def test_nonlearned_state_does_not_consume_learned_budget(self):
        d = base()
        d["persistent_state_components"][2]["bytes"] = 20_000_000_000
        d["persistent_state_components"][3]["bytes"] = 50_000_000_000
        out = audit_sub100mb_contract(d)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["learned_state_bytes"], 75_000_000)

    def test_budget_is_decimal_100mb_and_fail_closed(self):
        d = base()
        d["persistent_state_components"][0]["bytes"] = LEARNED_STATE_BUDGET_BYTES
        d["persistent_state_components"][1]["bytes"] = 1
        out = audit_sub100mb_contract(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("LEARNED_STATE_BUDGET_EXCEEDED:100000001>100000000", out["errors"])

    def test_external_frontier_provider_is_forbidden(self):
        d = base()
        d["scored_execution"]["external_learned_capability_providers"] = [
            "provider://frontier-model"
        ]
        out = audit_sub100mb_contract(d)
        self.assertFalse(out["pass"])
        self.assertIn("EXTERNAL_LEARNED_CAPABILITY_PROVIDER_PRESENT", out["errors"])

    def test_one_open_predicate_keeps_terminal_open(self):
        d = base()
        d["atomic_predicates"][7]["accepted"] = False
        out = audit_sub100mb_contract(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN")
        self.assertEqual(out["accepted_atomic_predicates"], 37)

    def test_one_open_family_keeps_terminal_open(self):
        d = base()
        d["capability_families"][3]["accepted"] = False
        out = audit_sub100mb_contract(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["accepted_capability_families"], 18)

    def test_duplicate_component_id_fails_closed(self):
        d = base()
        duplicate = copy.deepcopy(d["persistent_state_components"][0])
        duplicate["bytes"] = 1
        d["persistent_state_components"].append(duplicate)
        out = audit_sub100mb_contract(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("COMPONENT_ID_DUPLICATE:kernel", out["errors"])

    def test_missing_predicates_cannot_be_hidden(self):
        d = base()
        d["atomic_predicates"] = d["atomic_predicates"][:37]
        out = audit_sub100mb_contract(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ATOMIC_PREDICATE_COUNT_INVALID:37", out["errors"])

    def test_missing_families_cannot_be_hidden(self):
        d = base()
        d["capability_families"] = d["capability_families"][:18]
        out = audit_sub100mb_contract(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CAPABILITY_FAMILY_COUNT_INVALID:18", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
