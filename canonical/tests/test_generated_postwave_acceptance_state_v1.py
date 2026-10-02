from __future__ import annotations
import json
import unittest
from pathlib import Path

from canonical.runtime.generated_postwave_acceptance_state_v1 import evaluate as compile_state
from canonical.runtime.postwave_evidence_reconciler_v1 import evaluate as reconcile

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def live_reconciliation(self):
        return reconcile(
            load("canonical/governance/POSTWAVE_EVIDENCE_RECONCILIATION_INPUT_V1.json"),
            load("canonical/verification/CURRENT_OBJECTIVE_BINDINGS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"),
            load("canonical/governance/OPUS55_REOPENED_OBJECTIVE_ROUTE_RESIDUAL_V1.json"),
            load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
            load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        )

    def live(self):
        return dict(
            policy=load("canonical/governance/POSTWAVE_ACCEPTANCE_STATE_POLICY_V1.json"),
            registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            hypergraph=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json"),
            reconciliation=self.live_reconciliation(),
        )

    def test_live_state_is_current_and_fail_closed(self):
        out = compile_state(**self.live())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["phase"], "POSTWAVE_ACCEPTANCE")
        self.assertEqual(out["predicate_count"], 38)
        self.assertEqual(out["proved_predicate_count"], 8)
        self.assertEqual(out["unresolved_predicate_count"], 30)
        self.assertEqual(out["strict_closed_family_count"], 3)
        self.assertEqual(out["terminal_family_count"], 19)
        self.assertFalse(out["global_terminal_promotion"])
        self.assertFalse(out["legacy_behavioral_global_residual_live_input_authoritative"])

        by_id = {x["predicate_id"]: x for x in out["predicates"]}
        d = by_id["DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"]
        self.assertEqual(d["state"], "OPEN")
        self.assertEqual(len(d["candidate_witnesses"]), 1)
        r = by_id["RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR"]
        self.assertEqual(r["state"], "OPEN")
        self.assertEqual(len(r["scope_valid_terminal_evidence"]), 1)

    def test_candidate_never_self_promotes(self):
        x = self.live()
        out = compile_state(**x)
        by_id = {r["predicate_id"]: r for r in out["predicates"]}
        self.assertEqual(by_id["DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"]["state"], "OPEN")
        self.assertEqual(out["strict_closed_family_count"], 3)

    def test_unresolved_without_action_fails(self):
        x = self.live()
        x["hypergraph"] = json.loads(json.dumps(x["hypergraph"]))
        for action in x["hypergraph"]["actions"]:
            action["target_predicates"] = [
                p for p in action.get("target_predicates", [])
                if p != "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"
            ]
        out = compile_state(**x)
        self.assertFalse(out["pass"])
        self.assertIn(
            "UNRESOLVED_WITHOUT_DISCHARGE_ACTION:DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
            out["errors"],
        )

    def test_proved_predicate_live_target_fails(self):
        x = self.live()
        x["hypergraph"] = json.loads(json.dumps(x["hypergraph"]))
        x["hypergraph"]["actions"].append({
            "id": "BAD",
            "target_predicates": ["TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"],
        })
        out = compile_state(**x)
        self.assertFalse(out["pass"])
        self.assertIn("PROVED_STILL_TARGETED:TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR", out["errors"])

    def test_nonindependent_proved_claim_fails(self):
        x = self.live()
        x["evidence"] = json.loads(json.dumps(x["evidence"]))
        claim = next(c for c in x["evidence"]["claims"] if c.get("state") == "PROVED")
        claim["independent_or_objective"] = False
        out = compile_state(**x)
        self.assertFalse(out["pass"])
        self.assertTrue(any(e.startswith("PROVED_NOT_INDEPENDENT_OR_OBJECTIVE:") for e in out["errors"]))

    def test_reconciliation_must_pass_if_present(self):
        x = self.live()
        x["reconciliation"] = {"status": "FAIL_CLOSED"}
        out = compile_state(**x)
        self.assertFalse(out["pass"])
        self.assertIn("RECONCILIATION_NOT_PASS", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
