from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_complete_interface_instance_v1 as iface
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as policy


def specimen():
    return {
        "epoch_id": 0,
        "tools": [
            {
                "tool_id": "T0",
                "available": True,
                "authorized": True,
                "cost": 1.0,
                "meta": {"region": "US", "risk": 1, "tags": ["prod"]},
            },
            {
                "tool_id": "T1",
                "available": True,
                "authorized": True,
                "cost": 2.0,
                "meta": {"region": "EU", "risk": 1, "tags": ["safe"]},
            },
            {
                "tool_id": "T2",
                "available": True,
                "authorized": True,
                "cost": 3.0,
                "meta": {"region": "EU", "risk": 2, "tags": ["safe"]},
            },
        ],
        "sources": [
            {
                "source_id": "S0",
                "cost": 0.1,
                "available": True,
                "tool_ids": ["T0", "T1"],
            },
            {
                "source_id": "S1",
                "cost": 0.2,
                "available": True,
                "tool_ids": ["T2"],
            },
        ],
        "capability_truth": {
            "T0": {"CAP_A": False},
            "T1": {"CAP_A": True},
            "T2": {"CAP_A": False},
        },
        "initial_visible": ["T0"],
        "required_capabilities": ["CAP_A"],
    }


def drive(epoch, constraint=None, session=None, max_steps=64):
    session = session or iface.new_session(epoch, constraint=constraint)
    actions = []
    for _ in range(max_steps):
        public = iface.public_state(epoch, session)
        action = policy.next_action(public)
        kind = action.get("action")
        if kind == "DISCOVER":
            session = iface.apply_discovery(
                epoch,
                session,
                str(action.get("source_id") or ""),
                str(action.get("query") or ""),
            )
            actions.append(kind + ":" + str(action.get("source_id") or ""))
            continue
        if kind == "PROBE":
            session = iface.apply_probe(
                epoch,
                session,
                str(action.get("tool_id") or ""),
                str(action.get("capability") or ""),
            )
            rec = session["probe_receipts"][-1]
            actions.append(kind + ":" + rec["tool_id"] + ":" + str(rec["supported"]))
            continue
        if kind == "SELECT":
            tool_id = str(action.get("tool_id") or "")
            gate = iface.execution_admit(epoch, tool_id)
            if gate.get("admitted") is not True:
                return {"pass": False, "reason": "SELECT_NOT_EXECUTION_ADMITTED", "actions": actions}
            for cap in epoch["required_capabilities"]:
                if not any(
                    r.get("tool_id") == tool_id
                    and r.get("capability") == cap
                    and r.get("epoch") == epoch["epoch_id"]
                    and r.get("supported") is True
                    for r in session["probe_receipts"]
                ):
                    return {"pass": False, "reason": "SELECT_WITHOUT_CURRENT_TRUE_PROBE", "actions": actions}
            actions.append(kind + ":" + tool_id)
            return {
                "pass": True,
                "selected": tool_id,
                "escalated": False,
                "actions": actions,
                "session": session,
                "probes": session["probe_receipts"],
                "discoveries": session["discovery_receipts"],
            }
        if kind == "ESCALATE":
            actions.append(kind)
            return {
                "pass": True,
                "selected": None,
                "escalated": True,
                "actions": actions,
                "session": session,
                "probes": session["probe_receipts"],
                "discoveries": session["discovery_receipts"],
            }
        return {"pass": False, "reason": "UNKNOWN_ACTION", "actions": actions}
    return {"pass": False, "reason": "ACTION_BUDGET_EXHAUSTED", "actions": actions}


class ToolDiscoveryCompleteInterfaceInstanceV1Tests(unittest.TestCase):
    def test_exact_contract_properties_hold_on_valid_instance(self):
        epoch = iface.compile_epoch(specimen())
        cert = iface.contract_certificate(epoch)
        self.assertTrue(cert["all_required_properties_hold"], cert)
        self.assertEqual(
            set(cert["properties"]),
            set(iface.REQUIRED_PROPERTIES),
        )
        self.assertTrue(cert["source_union_exact"])
        self.assertTrue(cert["execution_authority_closed_world"])
        self.assertEqual(cert["capability_credit_delta"], 0)
        self.assertEqual(cert["family_credit_delta"], 0)
        self.assertFalse(cert["promotion_authority"])

    def test_source_union_missing_tool_fails_closed(self):
        spec = specimen()
        spec["sources"][1]["tool_ids"] = []
        with self.assertRaisesRegex(iface.InterfaceError, "SOURCE_UNION_INCOMPLETE:T2"):
            iface.compile_epoch(spec)

    def test_source_union_extraneous_tool_fails_closed(self):
        spec = specimen()
        spec["sources"][1]["tool_ids"] = ["T2", "TX"]
        with self.assertRaisesRegex(iface.InterfaceError, "SOURCE_REFERENCES_UNKNOWN_TOOL:TX"):
            iface.compile_epoch(spec)

    def test_multiple_source_ownership_fails_closed(self):
        spec = specimen()
        spec["sources"][1]["tool_ids"] = ["T1", "T2"]
        with self.assertRaisesRegex(iface.InterfaceError, "TOOL_ASSIGNED_TO_MULTIPLE_SOURCES:T1"):
            iface.compile_epoch(spec)

    def test_discovered_metadata_is_same_authority_used_by_execution_gate(self):
        epoch = iface.compile_epoch(specimen())
        receipt = iface.discover(epoch, "S0", "CAP_A")
        discovered = {x["tool_id"]: x for x in receipt["tools"]}["T1"]
        admitted = iface.execution_admit(epoch, "T1")
        self.assertTrue(admitted["admitted"])
        self.assertEqual(discovered, admitted["tool"])
        self.assertNotIn("capability_truth", discovered)
        self.assertNotIn("hidden_capabilities", discovered)

    def test_probe_is_exact_truth_and_epoch_bound(self):
        epoch = iface.compile_epoch(specimen())
        rec = iface.probe(epoch, "T1", "CAP_A")
        self.assertTrue(rec["supported"])
        self.assertEqual(rec["epoch"], 0)
        self.assertEqual(rec["epoch_fingerprint_sha256"], epoch["fingerprint_sha256"])

    def test_out_of_universe_execution_has_no_escape_hatch(self):
        epoch = iface.compile_epoch(specimen())
        out = iface.execution_admit(epoch, "TX")
        self.assertFalse(out["admitted"])
        self.assertEqual(out["reason"], "TOOL_ID_OUTSIDE_CONTENT_ADDRESSED_EPOCH_UNIVERSE")

    def test_in_place_epoch_mutation_fails_fingerprint(self):
        epoch = iface.compile_epoch(specimen())
        mutant = copy.deepcopy(epoch)
        mutant["capability_truth"]["T1"]["CAP_A"] = False
        with self.assertRaisesRegex(iface.InterfaceError, "EPOCH_FINGERPRINT_MISMATCH"):
            iface.probe(mutant, "T1", "CAP_A")

    def test_version_change_creates_new_epoch_and_stale_probe_is_not_reused(self):
        epoch0 = iface.compile_epoch(specimen())
        session0 = iface.new_session(epoch0)
        session0 = iface.apply_discovery(epoch0, session0, "S0", "CAP_A")
        session0 = iface.apply_probe(epoch0, session0, "T1", "CAP_A")
        epoch1 = iface.rotate_epoch(
            epoch0,
            new_epoch_id=1,
            capability_updates={"T1": {"CAP_A": False}, "T2": {"CAP_A": True}},
        )
        self.assertNotEqual(epoch0["fingerprint_sha256"], epoch1["fingerprint_sha256"])
        with self.assertRaisesRegex(iface.InterfaceError, "SESSION_EPOCH_MISMATCH_RESTART_REQUIRED"):
            iface.public_state(epoch1, session0)
        out = drive(epoch1)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected"], "T2")
        self.assertTrue(any(x.startswith("PROBE:T1:False") for x in out["actions"]))
        self.assertTrue(any(x.startswith("PROBE:T2:True") for x in out["actions"]))

    def test_dynamic_policy_discovers_initially_unknown_sufficient_tool(self):
        epoch = iface.compile_epoch(specimen())
        out = drive(epoch)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected"], "T1")
        self.assertIn("DISCOVER:S0", out["actions"])
        self.assertIn("PROBE:T0:False", out["actions"])
        self.assertIn("PROBE:T1:True", out["actions"])

    def test_dynamic_policy_exhausts_complete_sources_before_no_route(self):
        spec = specimen()
        for row in spec["capability_truth"].values():
            row["CAP_A"] = False
        epoch = iface.compile_epoch(spec)
        out = drive(epoch)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["escalated"], out)
        self.assertEqual(
            {x["source_id"] for x in out["discoveries"]},
            {"S0", "S1"},
        )
        self.assertEqual(
            {x["tool_id"] for x in out["probes"]},
            {"T0", "T1", "T2"},
        )

    def test_session_discovery_is_monotone_and_source_receipts_are_unique(self):
        epoch = iface.compile_epoch(specimen())
        session = iface.new_session(epoch)
        before = set(session["visible_tool_ids"])
        session = iface.apply_discovery(epoch, session, "S0", "CAP_A")
        after = set(session["visible_tool_ids"])
        self.assertTrue(before <= after)
        self.assertEqual(session["discovery_receipts"][-1]["source_id"], "S0")
        with self.assertRaisesRegex(iface.InterfaceError, "DISCOVERY_SOURCE_ALREADY_QUERIED:S0"):
            iface.apply_discovery(epoch, session, "S0", "CAP_A")

    def test_same_epoch_second_task_reuses_probe_evidence_without_rediscovery(self):
        epoch = iface.compile_epoch(specimen())
        first = drive(epoch)
        self.assertTrue(first["pass"], first)
        session = first["session"]
        discovery_count = len(session["discovery_receipts"])
        probe_count = len(session["probe_receipts"])
        second_action = policy.next_action(iface.public_state(epoch, session))
        self.assertEqual(second_action, {"action": "SELECT", "tool_id": "T1"})
        self.assertEqual(len(session["discovery_receipts"]), discovery_count)
        self.assertEqual(len(session["probe_receipts"]), probe_count)

    def test_arbitrary_finite_partition_family(self):
        # This is a regression grid, not the universal proof itself. The
        # universal argument is the constructor invariant source-union == U.
        for n in range(1, 9):
            tools = [
                {
                    "tool_id": f"T{i}",
                    "available": True,
                    "authorized": True,
                    "cost": float(i + 1),
                }
                for i in range(n)
            ]
            sources = [
                {
                    "source_id": f"S{j}",
                    "cost": float(j) / 10.0,
                    "available": True,
                    "tool_ids": [f"T{i}" for i in range(n) if i % 3 == j],
                }
                for j in range(3)
            ]
            truth = {f"T{i}": {"CAP_A": i == n - 1} for i in range(n)}
            epoch = iface.compile_epoch(
                {
                    "epoch_id": 0,
                    "tools": tools,
                    "sources": sources,
                    "capability_truth": truth,
                    "initial_visible": [],
                    "required_capabilities": ["CAP_A"],
                }
            )
            cert = iface.contract_certificate(epoch)
            self.assertTrue(cert["all_required_properties_hold"], (n, cert))
            out = drive(epoch)
            self.assertTrue(out["pass"], (n, out))
            self.assertEqual(out["selected"], f"T{n-1}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
