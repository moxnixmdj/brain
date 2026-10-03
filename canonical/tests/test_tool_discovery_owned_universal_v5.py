from __future__ import annotations

import copy
import unittest

from canonical.runtime.tool_discovery_owned_universal_v5 import (
    AuthorityError,
    OwnedToolAuthorityV5,
    apply_discovery,
    next_action,
    theorem_invariants,
)


CAP = "CAP_A"


def row(
    tid: str,
    cost: float,
    *,
    source: str,
    supported: bool,
    available: bool = True,
    authorized: bool = True,
    admissible: bool = True,
    probe_allowed: bool = True,
):
    return {
        "tool_id": tid,
        "source_id": source,
        "cost": float(cost),
        "available": available,
        "authorized": authorized,
        "admissible": admissible,
        "safe_probe_capabilities": [CAP] if probe_allowed else [],
        "capabilities": [CAP] if supported else [],
        "schema_name": "opaque-" + tid,
    }


def execute(authority: OwnedToolAuthorityV5, *, prior=(), max_actions=100):
    public = authority.initial_public(
        required_capabilities=[CAP],
        prior_probe_receipts=prior,
    )
    actions = []
    for _ in range(max_actions):
        action = next_action(public)
        actions.append(copy.deepcopy(action))
        kind = action["action"]
        if kind == "DISCOVER":
            receipt = authority.discover(
                action["source_id"], episode_epoch=public["authority_epoch"]
            )
            apply_discovery(public, receipt)
        elif kind == "PROBE":
            rec = authority.safe_probe(
                action["tool_id"],
                action["capability"],
                episode_epoch=public["authority_epoch"],
            )
            public["prior_probe_receipts"].append(rec)
        elif kind in {"SELECT", "ESCALATE"}:
            return action, public, actions
        else:
            raise AssertionError(action)
    raise AssertionError("ACTION_BUDGET_EXHAUSTED")


class ToolDiscoveryOwnedUniversalV5Tests(unittest.TestCase):
    def test_identity_is_genuinely_unknown_until_discovery(self):
        a = OwnedToolAuthorityV5([
            row("expensive", 10, source="S0", supported=True),
            row("cheap", 1, source="S1", supported=True),
        ])
        public = a.initial_public(required_capabilities=[CAP])
        self.assertEqual(public["visible_tools"], [])
        self.assertEqual(next_action(public)["action"], "DISCOVER")

    def test_complete_source_union_is_exact_registry_and_hides_capability_truth(self):
        a = OwnedToolAuthorityV5([
            row("a", 1, source="S0", supported=True),
            row("b", 2, source="S1", supported=False),
            row("c", 3, source="S1", supported=True),
        ], epoch=7)
        out = theorem_invariants(a)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["registry_ids"], ["a", "b", "c"])
        self.assertEqual(out["discovered_ids"], ["a", "b", "c"])
        self.assertTrue(out["source_union_exact_registry"])
        self.assertTrue(out["hidden_capabilities_absent_from_discovery"])

    def test_public_authority_digest_does_not_encode_hidden_capability_truth(self):
        yes = OwnedToolAuthorityV5([
            row("same-public", 1, source="S0", supported=True),
        ], epoch=3)
        no = OwnedToolAuthorityV5([
            row("same-public", 1, source="S0", supported=False),
        ], epoch=3)
        self.assertEqual(yes.registry_digest_sha256(), no.registry_digest_sha256())
        self.assertEqual(
            yes.discover("S0", episode_epoch=3),
            no.discover("S0", episode_epoch=3),
        )

    def test_cheaper_identity_hidden_in_later_source_cannot_be_preempted(self):
        a = OwnedToolAuthorityV5([
            row("expensive", 10, source="S0", supported=True),
            row("cheap", 1, source="S1", supported=True),
        ])
        final, _, actions = execute(a)
        self.assertEqual(final, {"action": "SELECT", "tool_id": "cheap"})
        first_select = next(i for i, x in enumerate(actions) if x["action"] == "SELECT")
        discover_count = sum(1 for x in actions[:first_select] if x["action"] == "DISCOVER")
        self.assertEqual(discover_count, 2)

    def test_exhaustive_small_finite_worlds_return_global_least_cost_sufficient_route(self):
        # 3 tools; exhaust capability, availability and authorization worlds.
        # 8 * 8 * 8 = 512 complete worlds, each starting with hidden identities.
        tids = ["T0", "T1", "T2"]
        costs = [1.0, 2.0, 3.0]
        for support_mask in range(8):
            for availability_mask in range(8):
                for authorization_mask in range(8):
                    entries = []
                    for i, tid in enumerate(tids):
                        entries.append(row(
                            tid,
                            costs[i],
                            source="S" + str(i % 2),
                            supported=bool(support_mask & (1 << i)),
                            available=bool(availability_mask & (1 << i)),
                            authorized=bool(authorization_mask & (1 << i)),
                        ))
                    a = OwnedToolAuthorityV5(entries)
                    final, _, _ = execute(a)
                    sufficient = [
                        entries[i]
                        for i in range(3)
                        if entries[i]["available"]
                        and entries[i]["authorized"]
                        and entries[i]["admissible"]
                        and CAP in entries[i]["capabilities"]
                    ]
                    expected = (
                        min(sufficient, key=lambda x: (x["cost"], x["tool_id"]))["tool_id"]
                        if sufficient else None
                    )
                    if expected is None:
                        self.assertEqual(final["action"], "ESCALATE", (support_mask, availability_mask, authorization_mask, final))
                        self.assertEqual(final["reason"], "NO_VERIFIED_ADMISSIBLE_SUFFICIENT_ROUTE")
                    else:
                        self.assertEqual(final, {"action": "SELECT", "tool_id": expected}, (support_mask, availability_mask, authorization_mask, final))

    def test_normalized_active_constraint_admissibility_is_load_bearing(self):
        a = OwnedToolAuthorityV5([
            row("cheap-but-blocked", 1, source="S0", supported=True, admissible=False),
            row("allowed", 2, source="S0", supported=True, admissible=True),
        ])
        final, _, _ = execute(a)
        self.assertEqual(final, {"action": "SELECT", "tool_id": "allowed"})

    def test_missing_probe_permission_fails_closed_instead_of_skipping_cheaper_unknown(self):
        a = OwnedToolAuthorityV5([
            row("cheap-unknowable", 1, source="S0", supported=True, probe_allowed=False),
            row("expensive", 10, source="S0", supported=True),
        ])
        final, _, _ = execute(a)
        self.assertEqual(final["action"], "ESCALATE")
        self.assertEqual(
            final["reason"],
            "SAFE_PROBE_PERMISSION_MISSING_FOR_UNRESOLVED_CHEAPER_ROUTE",
        )
        self.assertEqual(final["tool_id"], "cheap-unknowable")

    def test_second_task_reuses_current_epoch_evidence_without_reprobe(self):
        a = OwnedToolAuthorityV5([
            row("cheap", 1, source="S0", supported=True),
            row("other", 2, source="S1", supported=True),
        ], epoch=4)
        first, p1, actions1 = execute(a)
        self.assertEqual(first, {"action": "SELECT", "tool_id": "cheap"})
        receipts = list(p1["prior_probe_receipts"])
        self.assertGreater(sum(1 for x in actions1 if x["action"] == "PROBE"), 0)

        second, _, actions2 = execute(a, prior=receipts)
        self.assertEqual(second, {"action": "SELECT", "tool_id": "cheap"})
        self.assertEqual(sum(1 for x in actions2 if x["action"] == "PROBE"), 0)

    def test_authority_replacement_invalidates_old_evidence_by_epoch(self):
        entries = [
            row("cheap", 1, source="S0", supported=True),
            row("other", 2, source="S0", supported=True),
        ]
        a = OwnedToolAuthorityV5(entries, epoch=2)
        first, p1, _ = execute(a)
        self.assertEqual(first, {"action": "SELECT", "tool_id": "cheap"})
        old = list(p1["prior_probe_receipts"])
        a.replace_authority(entries)
        second, _, actions2 = execute(a, prior=old)
        self.assertEqual(second, {"action": "SELECT", "tool_id": "cheap"})
        self.assertGreater(sum(1 for x in actions2 if x["action"] == "PROBE"), 0)

    def test_unregistered_identity_is_uninvocable(self):
        a = OwnedToolAuthorityV5([row("known", 1, source="S0", supported=True)])
        with self.assertRaisesRegex(AuthorityError, "UNREGISTERED_TOOL_ID"):
            a.invoke("outside", episode_epoch=0)

    def test_duplicate_identity_fails_closed(self):
        x = row("same", 1, source="S0", supported=True)
        with self.assertRaisesRegex(AuthorityError, "DUPLICATE_TOOL_ID"):
            OwnedToolAuthorityV5([x, x])

    def test_no_requirement_fails_closed(self):
        a = OwnedToolAuthorityV5([row("known", 1, source="S0", supported=True)])
        public = a.initial_public(required_capabilities=[])
        self.assertEqual(
            next_action(public),
            {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
