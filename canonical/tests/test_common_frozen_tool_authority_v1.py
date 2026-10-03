from __future__ import annotations

import itertools
import unittest

from canonical.runtime.common_frozen_tool_authority_v1 import (
    AuthorityError,
    CommonFrozenToolAuthority,
    prove_common_authority_instance,
)
from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5


def entries(mask: int = 0b1011):
    caps = ["A", "B"]
    out = []
    for i, cost in enumerate((1.0, 2.0, 3.0, 4.0)):
        hidden = []
        if mask & (1 << i):
            hidden = list(caps)
        out.append({
            "tool_id": f"T{i}",
            "cost": cost,
            "available": True,
            "authorized": True,
            "hidden_capabilities": hidden,
            "meta": {"tier": i},
        })
    return out


def drive(authority: CommonFrozenToolAuthority, required=("A", "B"), *, receipts=()):
    public = authority.initial_public(required, prior_probe_receipts=receipts)
    actions = []
    for _ in range(64):
        action = v5.next_action(public)
        actions.append(dict(action))
        kind = action["action"]
        if kind == "DISCOVER":
            public["discovery_receipts"].append(authority.discover(required))
            continue
        if kind == "PROBE":
            public["prior_probe_receipts"].append(
                authority.probe(
                    action["tool_id"],
                    action["capability"],
                    episode_epoch=public["decision_epoch"],
                    required_capabilities=required,
                )
            )
            continue
        if kind == "SELECT":
            authority.gate_invoke("BRAIN", action["tool_id"], episode_epoch=public["decision_epoch"])
            return action["tool_id"], actions, public
        if kind == "ESCALATE":
            return None, actions, public
        raise AssertionError(action)
    raise AssertionError("action budget exceeded")


class CommonFrozenToolAuthorityTests(unittest.TestCase):
    def test_common_authority_is_exact_and_symmetric(self):
        out = prove_common_authority_instance(entries(), ["A", "B"])
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertTrue(out["identity_universe_complete"])
        self.assertTrue(out["same_brain_comparator_authority"])
        self.assertTrue(out["identities_initially_hidden"])
        self.assertTrue(out["hidden_capability_truth_not_disclosed"])
        self.assertTrue(out["all_exact_requirement_probes_safely_decidable"])

    def test_unregistered_identity_rejected_for_both_roles(self):
        a = CommonFrozenToolAuthority(entries())
        for role in ("BRAIN", "COMPARATOR"):
            with self.assertRaisesRegex(AuthorityError, "UNREGISTERED_TOOL_ID"):
                a.gate_invoke(role, "GHOST", episode_epoch=a.epoch)

    def test_discovery_does_not_leak_capability_truth(self):
        a = CommonFrozenToolAuthority(entries())
        r = a.discover(["A", "B"])
        text = repr(r).lower()
        self.assertNotIn("hidden_capabilities", text)
        self.assertNotIn("supported", text)
        self.assertEqual(
            tuple(sorted(x["tool_id"] for x in r["tools"])),
            a.registry_ids(),
        )

    def test_v5_discovers_before_any_probe_or_select(self):
        a = CommonFrozenToolAuthority(entries())
        public = a.initial_public(["A", "B"])
        first = v5.next_action(public)
        self.assertEqual(first["action"], "DISCOVER")
        public["discovery_receipts"].append(a.discover(["A", "B"]))
        second = v5.next_action(public)
        self.assertEqual(second["action"], "PROBE")

    def test_v5_selects_global_least_cost_sufficient_tool_for_all_small_support_masks(self):
        for mask in range(16):
            a = CommonFrozenToolAuthority(entries(mask))
            selected, _, _ = drive(a)
            expected = next((f"T{i}" for i in range(4) if mask & (1 << i)), None)
            self.assertEqual(selected, expected, mask)

    def test_no_sufficient_route_escalates_only_after_negative_evidence(self):
        a = CommonFrozenToolAuthority(entries(0))
        selected, actions, _ = drive(a)
        self.assertIsNone(selected)
        self.assertEqual(actions[0]["action"], "DISCOVER")
        probed = {(x["tool_id"], x["capability"]) for x in actions if x["action"] == "PROBE"}
        self.assertEqual(
            probed,
            {(f"T{i}", cap) for i in range(4) for cap in ("A", "B")},
        )
        self.assertEqual(actions[-1]["action"], "ESCALATE")

    def test_transfer_reuses_current_epoch_receipts(self):
        a = CommonFrozenToolAuthority(entries(0b0010))
        selected, actions, public = drive(a)
        self.assertEqual(selected, "T1")
        earned = list(public["prior_probe_receipts"])
        selected2, actions2, _ = drive(a, receipts=earned)
        self.assertEqual(selected2, "T1")
        # All exact current evidence was reusable; no second-task probing is needed.
        self.assertEqual([x for x in actions2 if x["action"] == "PROBE"], [])

    def test_epoch_change_invalidates_prior_positive_receipts(self):
        a0 = CommonFrozenToolAuthority(entries(0b0001))
        selected, _, public0 = drive(a0)
        self.assertEqual(selected, "T0")
        old = list(public0["prior_probe_receipts"])

        changed = entries(0b0010)
        a1 = a0.replace(changed)
        public1 = a1.initial_public(["A", "B"], prior_probe_receipts=old)
        self.assertEqual(v5.next_action(public1)["action"], "DISCOVER")
        public1["discovery_receipts"].append(a1.discover(["A", "B"]))
        first_after_discovery = v5.next_action(public1)
        self.assertEqual(first_after_discovery, {"action": "PROBE", "tool_id": "T0", "capability": "A"})

        with self.assertRaisesRegex(AuthorityError, "EPOCH_CHANGED_RESTART_EPISODE"):
            a1.gate_invoke("BRAIN", "T0", episode_epoch=0)

    def test_safe_probe_is_exact_requirement_bound(self):
        a = CommonFrozenToolAuthority(entries())
        with self.assertRaisesRegex(AuthorityError, "PROBE_OUTSIDE_EXACT_REQUIREMENT_QUERY"):
            a.probe("T0", "UNREQUESTED", episode_epoch=a.epoch, required_capabilities=["A", "B"])

    def test_availability_and_authorization_filtering(self):
        rows = entries(0)
        rows[0]["hidden_capabilities"] = ["A", "B"]
        rows[0]["available"] = False
        rows[1]["hidden_capabilities"] = ["A", "B"]
        rows[1]["authorized"] = False
        rows[2]["hidden_capabilities"] = ["A", "B"]
        a = CommonFrozenToolAuthority(rows)
        selected, _, _ = drive(a)
        self.assertEqual(selected, "T2")

    def test_arbitrary_identity_names_and_cost_orders_preserve_completeness(self):
        names = ("z", "a", "mid")
        for costs in itertools.permutations((1.0, 2.0, 3.0)):
            rows = [
                {
                    "tool_id": tid,
                    "cost": cost,
                    "available": True,
                    "authorized": True,
                    "hidden_capabilities": ["A"],
                }
                for tid, cost in zip(names, costs)
            ]
            a = CommonFrozenToolAuthority(rows)
            out = prove_common_authority_instance(rows, ["A"])
            self.assertTrue(out["identity_universe_complete"], (names, costs))
            selected, _, _ = drive(a, required=("A",))
            expected = min(rows, key=lambda x: (x["cost"], x["tool_id"]))["tool_id"]
            self.assertEqual(selected, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
