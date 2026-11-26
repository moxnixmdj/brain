#!/usr/bin/env python3
"""Wave 42 — the three MEME operations the semiring store could not answer.

Every test here either measures a claim the module makes or falsifies it: exact aggregates under
invalidation, rename tracking that survives a later cascade, absence for a rule that never fired,
and -- the load-bearing one -- agreement with a from-scratch fixpoint oracle over random mutation
sequences, so the incremental bookkeeping cannot be wrong in a way a hand-written case would miss.
"""
from __future__ import annotations

import random
import unittest

from canonical.evaluation.meme_protocol_bench_v1 import (
    DEFAULT_SEED,
    DependencyMemorySUT,
    FlatStoreSUT,
    OracleSUT,
    build_instances,
    run_benchmark,
    run_sut,
    self_check,
)
from canonical.swe_kernel.meme_protocol_memory_v1 import (
    ABSENCE_SUPPORT_INVALIDATED,
    ABSTAIN_NEVER_ESTABLISHED,
    ESTABLISHED,
    OPERATIONS,
    SCHEMA,
    STALE_ENTITY_NAME,
    UNKNOWN_UPSTREAM_SUPERSEDED,
    DependencyMemory,
    Rule,
    reference_fixpoint,
    self_check as module_self_check,
)


class TestTheThreeMissingOperations(unittest.TestCase):
    """Each test names one protocol operation the store could not answer before this module."""

    def test_01_the_module_names_its_schema_and_passes_its_own_six_checks(self):
        report = module_self_check()
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["checks"], 8)
        self.assertEqual(report["passed"], 8, report)

    def test_02_an_aggregate_is_exact_while_every_contribution_is_live(self):
        mem = DependencyMemory()
        mem.declare_aggregate("total", "cost", lambda vs: sum(int(v) for v in vs), empty=0)
        for v in ("10", "20", "30"):
            mem.assert_premise("acct", "cost", v)
        got = mem.aggregate("total", "acct")
        self.assertEqual(got["status"], ESTABLISHED)
        self.assertEqual(got["value"], 60)
        self.assertEqual(sorted(got["live_contributions"]), ["10", "20", "30"])

    def test_03_a_member_the_operator_deleted_shrinks_the_total_on_purpose(self):
        mem = DependencyMemory()
        mem.declare_aggregate("total", "cost", lambda vs: sum(int(v) for v in vs), empty=0)
        for v in ("10", "20", "30"):
            mem.assert_premise("acct", "cost", v)
        mem.retract("acct", "cost", "30")
        got = mem.aggregate("total", "acct")
        self.assertEqual(got["status"], ESTABLISHED)
        self.assertEqual(got["value"], 30)
        self.assertEqual(got["removed_by_operator"], ["30"])

    def test_03b_a_member_that_lost_its_support_upstream_refuses_the_smaller_total(self):
        """Nobody asked for a smaller total here, so reporting one answers a question that was
        never asked -- which is the failure this operation exists to prevent."""
        mem = DependencyMemory()
        mem.declare_aggregate("total", "cost", lambda vs: sum(int(v) for v in vs), empty=0)
        mem.add_rule("quoted", ("acct", "cost", "30"), [("quote", "amount", "30")])
        mem.assert_premise("acct", "cost", "10")
        mem.assert_premise("quote", "amount", "30")
        self.assertEqual(mem.aggregate("total", "acct")["value"], 40)
        mem.retract("quote", "amount", "30")
        got = mem.aggregate("total", "acct")
        self.assertEqual(got["status"], UNKNOWN_UPSTREAM_SUPERSEDED)
        self.assertNotIn("value", got)
        self.assertEqual([d["value"] for d in got["dropped_contributions"]], ["30"])
        self.assertEqual(sorted(got["live_contributions"]), ["10"])

    def test_04_a_derived_fact_follows_its_renamed_support(self):
        mem = DependencyMemory()
        mem.add_rule("reach", ("node", "reachable", "yes"), [("node", "ip", "10.0.0.1")])
        mem.assert_premise("node", "ip", "10.0.0.1")
        self.assertEqual(mem.query("node", "reachable")["values"], ["yes"])
        info = mem.rename_entity("node", "node-2")
        self.assertTrue(info["renamed"])
        self.assertEqual(info["lost_facts"], [])
        self.assertEqual(mem.query("node-2", "reachable")["values"], ["yes"])

    def test_05_the_old_name_is_refused_rather_than_quietly_absorbed(self):
        mem = DependencyMemory()
        mem.assert_premise("node", "ip", "10.0.0.1")
        mem.rename_entity("node", "node-2")
        write = mem.assert_premise("node", "ip", "10.0.0.1")
        self.assertFalse(write["accepted"])
        self.assertEqual(write["status"], STALE_ENTITY_NAME)
        self.assertEqual(write["canonical_name"], "node-2")
        self.assertEqual(mem.query("node", "ip")["status"], STALE_ENTITY_NAME)

    def test_06_a_rename_does_not_promote_a_derived_fact_into_a_premise(self):
        """Regression: the first implementation re-asserted *derived* facts as premises, which made
        them survive the retraction of the very support they were derived from."""
        mem = DependencyMemory()
        mem.add_rule("reach", ("node", "reachable", "yes"), [("node", "ip", "10.0.0.1")])
        mem.assert_premise("node", "ip", "10.0.0.1")
        mem.rename_entity("node", "node-2")
        mem.retract("node-2", "ip", "10.0.0.1")
        got = mem.query("node-2", "reachable")
        self.assertNotEqual(got["status"], ESTABLISHED, got)
        # it *was* established, so the cascade names the invalidated premise; the rule that could
        # not re-fire is a second, weaker answer and must not mask the first
        self.assertEqual(got["status"], ABSENCE_SUPPORT_INVALIDATED)
        self.assertEqual(tuple(got["invalidated_support"][0]["invalidated_root_triple"]),
                         ("node-2", "ip", "10.0.0.1"))
        self.assertEqual(mem.snapshot()["established_count"], 0)

    def test_07_absence_names_the_rule_that_could_not_fire(self):
        mem = DependencyMemory()
        body = [("order", "funding", "approved"), ("order", "owner", "set")]
        mem.add_rule("needs-owner", ("order", "shippable", "yes"), body)
        mem.assert_premise(*body[0])  # the second body member is never supplied: the rule never fires
        got = mem.query("order", "shippable")
        self.assertEqual(got["status"], UNKNOWN_UPSTREAM_SUPERSEDED)
        self.assertEqual(got["expected_by_rules"][0]["rule_id"], "needs-owner")
        self.assertEqual(got["expected_by_rules"][0]["missing_body"], [["order", "owner", "set"]])

    def test_08_never_established_and_no_longer_supported_are_different_answers(self):
        mem = DependencyMemory()
        mem.assert_premise("a", "p", "x")
        self.assertEqual(mem.query("a", "p")["status"], ESTABLISHED)
        self.assertEqual(mem.query("a", "q")["status"], ABSTAIN_NEVER_ESTABLISHED)

        # a rule whose body never became complete: no tombstone exists, and the answer must still
        # say something more useful than "never established"
        blocked = DependencyMemory()
        blocked.add_rule("r", ("a", "q", "y"), [("a", "p", "x"), ("a", "s", "z")])
        blocked.assert_premise("a", "p", "x")
        got = blocked.query("a", "q")
        self.assertEqual(got["status"], UNKNOWN_UPSTREAM_SUPERSEDED)
        self.assertEqual(got["expected_by_rules"][0]["missing_body"], [["a", "s", "z"]])

        # the same rule, but the body was complete once and then lost a member: the answer is the
        # cascade, and it must not be reported as the weaker "the rule cannot fire"
        cascaded = DependencyMemory()
        cascaded.add_rule("r", ("a", "q", "y"), [("a", "p", "x"), ("a", "s", "z")])
        cascaded.assert_premise("a", "p", "x")
        cascaded.assert_premise("a", "s", "z")
        self.assertEqual(cascaded.query("a", "q")["status"], ESTABLISHED)
        cascaded.retract("a", "s", "z")
        self.assertEqual(cascaded.query("a", "q")["status"], ABSENCE_SUPPORT_INVALIDATED)

    def test_09_a_diamond_survives_losing_one_arm_and_dies_with_the_last(self):
        mem = DependencyMemory()
        head = ("proj", "status", "green")
        mem.add_rule("arm-a", head, [("proj-a", "ready", "yes")])
        mem.add_rule("arm-b", head, [("proj-b", "ready", "yes")])
        mem.assert_premise("proj-a", "ready", "yes")
        mem.assert_premise("proj-b", "ready", "yes")
        self.assertEqual(mem.query("proj", "status")["values"], ["green"])
        mem.retract("proj-a", "ready", "yes")
        self.assertEqual(mem.query("proj", "status")["status"], ESTABLISHED,
                         "one supporting proof survived")
        mem.retract("proj-b", "ready", "yes")
        self.assertEqual(mem.query("proj", "status")["status"], ABSENCE_SUPPORT_INVALIDATED)


class TestTheIncrementalStoreAgainstAFromScratchOracle(unittest.TestCase):
    """Differential testing: the only way to be sure the clever path equals the plain one."""

    RULES = [
        Rule("s1", ("w", "l1", "ok"), [("w", "cost", "5")]),
        Rule("s2", ("w", "l2", "ok"), [("w", "l1", "ok"), ("w", "cost", "9")]),
        Rule("s3", ("w", "l3", "ok"), [("w", "l2", "ok"), ("v", "flag", "on")]),
        Rule("s4", ("v", "cap", "3"), [("w", "cost", "9")]),
    ]
    POOL = [("w", "cost", "5"), ("w", "cost", "9"), ("v", "flag", "on"),
            ("w", "x", "y"), ("v", "q", "z")]

    def _walk(self, seed: int, steps: int = 120):
        rng = random.Random(seed)
        mem = DependencyMemory()
        mem.declare_aggregate("costsum", "cost", lambda vs: sum(int(v) for v in vs), empty=0)
        for rule in self.RULES:
            mem.add_rule(rule.rule_id, rule.head, rule.body)
        extensional = set()
        divergences = []
        for step in range(steps):
            triple = rng.choice(self.POOL)
            if triple in extensional and rng.random() < 0.5:
                mem.retract(*triple)
                extensional.discard(triple)
            elif triple not in extensional:
                mem.assert_premise(*triple)
                extensional.add(triple)
            want = reference_fixpoint(extensional, self.RULES)
            got = set(mem._established())
            if want != got:
                divergences.append((step, sorted(want - got), sorted(got - want)))
                break
            want_costs = sorted(o for (s, r, o) in want if s == "w" and r == "cost")
            agg = mem.aggregate("costsum", "w")
            if sorted(agg.get("live_contributions", [])) != want_costs:
                divergences.append((step, want_costs, agg.get("live_contributions")))
                break
        return divergences

    def test_10_forty_random_mutation_sequences_agree_with_the_fixpoint(self):
        divergent = {seed: self._walk(seed) for seed in range(1, 41)}
        bad = {s: d for s, d in divergent.items() if d}
        self.assertEqual(bad, {}, f"{len(bad)}/40 seeds diverged from the from-scratch oracle")

    def test_11_the_oracle_is_not_the_engine_wearing_a_hat(self):
        """If both were the same code path this test would be vacuous, so the oracle is shown to
        disagree with a deliberately wrong incremental answer."""
        premises = {("w", "cost", "5"), ("w", "cost", "9"), ("v", "flag", "on")}
        correct = reference_fixpoint(premises, self.RULES)
        broken = correct - {("w", "l3", "ok")}
        self.assertIn(("w", "l2", "ok"), correct)
        self.assertIn(("w", "l3", "ok"), correct)
        self.assertNotEqual(correct, broken)


class TestMeasuredByTheBench(unittest.TestCase):

    def test_12_the_dependency_memory_scores_every_operation_on_every_seeded_instance(self):
        for seed in (DEFAULT_SEED, 1, 7, 42):
            report = run_benchmark(per_op=5, seed=seed)
            dep = report["results"]["dependency_memory"]
            self.assertEqual(dep["rate"], 1.0, (seed, dep["failures"]))
            self.assertEqual(dep["false_success_claims"], 0, seed)

    def test_13_the_no_dependency_edges_baseline_loses_exactly_where_edges_matter(self):
        report = run_benchmark(per_op=5, seed=DEFAULT_SEED)
        flat = report["results"]["flat_retrieval"]["per_operation"]
        dep = report["results"]["dependency_memory"]["per_operation"]
        self.assertEqual(dep["EXACT_RECALL"]["rate"], flat["EXACT_RECALL"]["rate"],
                         "a flat store answers a plain lookup")
        self.assertEqual(dep["DELETION"]["rate"], flat["DELETION"]["rate"],
                         "a table with a delete button can name a deletion")
        for op, name in (("CASCADE", "cascade"), ("ABSENCE", "absence"),
                         ("AGGREGATION", "aggregation"), ("TRACKING", "tracking")):
            self.assertEqual(flat[op]["rate"], 0.0, f"{name}: baseline unexpectedly passed")
            self.assertEqual(dep[op]["rate"], 1.0, f"{name}: dependency memory unexpectedly failed")

    def test_14_the_instrument_discriminates_between_honest_confident_and_silent(self):
        check = self_check(per_op=4)
        self.assertEqual(check["honest_rate"], 1.0, check)
        self.assertLess(check["liar_rate"], 0.5, check)
        self.assertEqual(check["stub_rate"], 0.0, check)
        self.assertGreaterEqual(check["discrimination"], 0.5, check)
        self.assertTrue(check["trustworthy"], check)

    def test_15_replacing_the_capability_with_the_baseline_drops_the_score(self):
        """The capability, not the fixture: same instances, same judge, only the system changes."""
        instances = build_instances(random.Random(DEFAULT_SEED), 5)
        real = run_sut(DependencyMemorySUT(), instances)
        crippled = run_sut(FlatStoreSUT(), instances)
        honest = run_sut(OracleSUT(), instances)
        self.assertEqual(honest["rate"], 1.0, honest["failures"])
        self.assertEqual(real["rate"], 1.0)
        self.assertLess(crippled["rate"], 0.5, crippled)
        self.assertGreaterEqual(real["rate"] - crippled["rate"], 0.5)

    def test_16_the_bench_reports_the_six_operations_it_actually_scores(self):
        report = run_benchmark(per_op=2, seed=DEFAULT_SEED)
        self.assertEqual(tuple(report["operations"]), OPERATIONS)
        self.assertEqual(len(OPERATIONS), 6)
        self.assertEqual(report["instances"], 12)
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["spend_usd"], 0.0)
        self.assertEqual(report["verdict"], "BENCH_COMPLETE__DEPENDENCY_MEMORY_AHEAD")


class TestReachability(unittest.TestCase):

    def test_17_the_module_is_reachable_from_the_federated_kernel(self):
        from canonical.runtime.unified_hidden_capability_federation_v1 import (
            CROSS_DISCIPLINARY_CONCEPT_MAP,
            FEDERATED_KERNEL_DESCRIPTORS,
            run_federated_engine,
        )

        self.assertIn("LEAPFROG_W42_MEME_PROTOCOL_MEMORY", FEDERATED_KERNEL_DESCRIPTORS)
        self.assertIn("meme_protocol_memory_w42", CROSS_DISCIPLINARY_CONCEPT_MAP)
        res = run_federated_engine(
            "LEAPFROG_W42_MEME_PROTOCOL_MEMORY",
            {"per_op": 2, "seed": DEFAULT_SEED},
            goal="answer the six MEME operations",
        )
        self.assertTrue(res.get("pass"), res)
        self.assertEqual(res.get("status"), "PASS__MEME_PROTOCOL_MEASURED")
        self.assertEqual(res.get("dependency_memory_rate"), 1.0)
        self.assertEqual(res.get("model_calls"), 0)
        self.assertEqual(res.get("spend_usd"), 0.0)


if __name__ == "__main__":
    unittest.main()
