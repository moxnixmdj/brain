"""Regression tests for two-phase goal->capability binding.

What changed, and why these tests exist
---------------------------------------
`goal_compiler._bind_inputs` binds what a goal SAYS. It fails closed for values
a goal merely IMPLIES -- an `output_path` that does not exist yet, or a
`source_root` one step away from a named file -- which silently disabled
capabilities that had been selected correctly. Measured on a fixed benchmark of
nine ordinary goals, only 1 of 9 compiled.

The fix wires the already-verified `world_binding_v1` in as a SECOND pass, and
that ordering is the whole point:

  * pass 1 ranks only capabilities bindable from the goal's own words;
  * pass 2 runs only if pass 1 found nothing.

An earlier attempt admitted inferred candidates into the SAME ranking. That
regressed three existing tests, because inference makes almost anything
bindable and so destroys the disambiguation bindability provides: a barcode
DECODER outranked the barcode GENERATOR the goal asked for.
`test_grounded_binding_is_never_outbid_by_inferred` exists so that mistake
cannot come back unnoticed.

Zero external model. Zero spend. Everything here is deterministic.
"""
from __future__ import annotations

import json
import pathlib
import unittest

from canonical.runtime import goal_compiler as compiler
from canonical.runtime import world_binding_v1 as world_binding
from canonical.runtime.goal_compiler import GoalCompilationFailure

ROOT = pathlib.Path(__file__).resolve().parents[2]

# The goal set whose measured compile rate moved from 1/9 to 5/9. Asserted as a
# floor so a future change that silently narrows the bindable set fails loudly.
BENCHMARK_COMPILE_FLOOR = 6
BENCHMARK_EXPECTED_FIRST_FLOOR = 4


def _synthetic_registry():
    """A capability that cannot be bound honestly, and nothing else.

    `world_binding_v1` deliberately refuses to invent `pattern`/`glob` values,
    so this entry is the minimal case where widening the binder must still
    refuse rather than guess.
    """
    return {
        "test.pattern_only.capability": {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "action_template": {
                "type": "invoke_capability",
                "args": {
                    "capability_id": "test.pattern_only.capability",
                    "pattern": "${input.pattern}",
                },
                "expect": {
                    "type": "field_equals",
                    "field": "output_verified",
                    "value": True,
                },
            },
            "provides": ["test.pattern_only"],
            "requires": [],
            "keywords": ["zebrafish", "pattern"],
            "source": {"type": "stdlib"},
            "adapter_module": "python_stub",
        },
    }


class GroundedBindingPrecedenceTests(unittest.TestCase):
    """Pass 1 must win outright. Pass 2 must never displace it."""

    @classmethod
    def setUpClass(cls):
        from canonical.runtime import live_integrated_brain_v1 as lb

        cls.registry = dict(lb.load_verified_registry())

    def test_grounded_binding_is_never_outbid_by_inferred(self):
        """The exact regression this ordering prevents.

        Both goals name every input and output, so they bind in pass 1. The
        decoder capabilities also become bindable once inference is allowed,
        and they match the vocabulary just as well -- if inferred candidates
        ever share a ranking with grounded ones, these select the wrong
        capability again.
        """
        barcode = (
            "Generate a Code 128 barcode image for the text PROJECT BRAIN and "
            "save it as canonical/astra_runtime/tmp/PROJECT_BRAIN_BARCODE.png."
        )
        out = compiler.compile_goal(barcode, self.registry, ROOT)
        self.assertEqual(out["selected_capability"], "auto.apt.zint")
        self.assertNotEqual(out["selected_capability"], "image.qr.generate.qrencode")
        self.assertEqual(out["binding_source"], "GOAL_STATEMENT")

        qr = (
            "Generate a QR code image for the text PROJECT BRAIN and save it "
            "as canonical/astra_runtime/tmp/PROJECT_BRAIN_QR.png."
        )
        out = compiler.compile_goal(qr, self.registry, ROOT)
        self.assertEqual(out["selected_capability"], "image.qr.generate.qrencode")
        self.assertEqual(out["binding_source"], "GOAL_STATEMENT")

    def test_fully_stated_goal_reports_no_inference(self):
        """A grounded plan must not carry world-binding provenance."""
        goal = (
            "Generate a Code 128 barcode image for the text PROJECT BRAIN and "
            "save it as canonical/astra_runtime/tmp/PROJECT_BRAIN_BARCODE.png."
        )
        out = compiler.compile_goal(goal, self.registry, ROOT)
        self.assertEqual(out["binding_source"], "GOAL_STATEMENT")
        self.assertNotIn("binding_provenance", out)
        self.assertEqual(
            out["inputs"]["output_path"],
            "canonical/astra_runtime/tmp/PROJECT_BRAIN_BARCODE.png",
        )

    def test_rank_helper_respects_the_allow_flag(self):
        """Pass 1 finds nothing for an unstated-output goal; pass 2 does."""
        goal = "Audit python source structure and write the audit to a JSON file."
        grounded = compiler._rank_bindable_candidates(
            goal, self.registry, ROOT, allow_world_binding=False
        )
        self.assertEqual(grounded, [])
        inferred = compiler._rank_bindable_candidates(
            goal, self.registry, ROOT, allow_world_binding=True
        )
        self.assertTrue(inferred)
        self.assertEqual(inferred[0][2], "python.source.audit.ast")
        # Every candidate returned by pass 2 is inferred, never a mix.
        self.assertTrue(all(row[6] for row in inferred))


class WorldBindingFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from canonical.runtime import live_integrated_brain_v1 as lb

        cls.registry = dict(lb.load_verified_registry())

    def test_unstated_output_path_is_synthesized_and_reported(self):
        goal = "Audit python source structure and write the audit to a JSON file."
        out = compiler.compile_goal(goal, self.registry, ROOT)
        self.assertEqual(out["selected_capability"], "python.source.audit.ast")
        self.assertEqual(out["binding_source"], "GOAL_STATEMENT+WORLD_BINDING")

        output = out["inputs"]["output_path"]
        self.assertTrue(
            output.startswith(world_binding.OUTPUT_DIR + "/"),
            f"synthesized output escaped the scratch dir: {output}",
        )
        self.assertTrue(output.endswith(".json"))

        provenance = out["binding_provenance"]
        self.assertIn("output_path", provenance["filled_by_world_binding"])

    def test_inference_is_shown_not_buried(self):
        """Which slots were filled, and from where, must be visible."""
        goal = "Audit python source structure and write the audit to a JSON file."
        out = compiler.compile_goal(goal, self.registry, ROOT)
        provenance = out["binding_provenance"]
        self.assertEqual(
            set(provenance),
            {
                "filled_by_world_binding",
                "filled_from_world_not_goal",
                "filled_from_companion_not_goal",
                "filled_from_demonstrated_case",
            },
        )

    def test_synthesized_output_is_deterministic(self):
        first = world_binding.synthesize_output_path("python.source.audit.ast", "output_path", ROOT)
        second = world_binding.synthesize_output_path("python.source.audit.ast", "output_path", ROOT)
        self.assertEqual(first, second)
        self.assertNotEqual(
            first,
            world_binding.synthesize_output_path("sqlite.table.create_from_json_records", "output_path", ROOT),
        )


class FailClosedTests(unittest.TestCase):
    def test_unjustifiable_placeholder_is_refused_not_guessed(self):
        """Widening the binder must never invent an input."""
        goal = "Check the zebrafish pattern."
        with self.assertRaises(GoalCompilationFailure) as ctx:
            compiler.compile_goal(goal, _synthetic_registry(), ROOT)
        self.assertEqual(ctx.exception.code, "GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH")

    def test_world_binding_reports_missing_rather_than_partial(self):
        entry = _synthetic_registry()["test.pattern_only.capability"]
        completed = world_binding.complete_inputs(
            "Check the zebrafish pattern.", ROOT, entry, compiler=compiler
        )
        self.assertIn("pattern", completed["missing"])

    def test_compiler_never_leaks_attribute_error(self):
        """A compiler defect must refuse, not crash.

        `_compile_compound_goal` used to dereference a part whose input mapping
        was None and raised AttributeError out of the planner. Every exception
        escaping `compile_goal` must be a named GoalCompilationFailure.
        """
        from canonical.runtime import live_integrated_brain_v1 as lb

        registry = dict(lb.load_verified_registry())
        adversarial = [
            "Compile a plain goal into a bound capability and verify the grounding.",
            "Extract evidence from a source, then rank it, then bind it to a claim.",
            "Then then then.",
            "Create and verify and verify and.",
            "Audit . then audit . then audit .",
        ]
        for goal in adversarial:
            try:
                compiler.compile_goal(goal, registry, ROOT)
            except GoalCompilationFailure:
                continue
            except AttributeError as exc:  # pragma: no cover - the defect itself
                self.fail(f"AttributeError escaped compile_goal for {goal!r}: {exc}")


class KnownSelectionGapTests(unittest.TestCase):
    """The two goals that compile against the WRONG capability, and why.

    These pin a measured diagnosis, not an opinion. The two causes are
    different, which is why neither is fixed by improving the scorer -- an
    attempt to do exactly that was measured and reverted (5/9 -> 2/9).
    """

    @classmethod
    def setUpClass(cls):
        from canonical.runtime import live_integrated_brain_v1 as lb

        cls.registry = dict(lb.load_verified_registry())

    def test_exactly_the_documented_goals_select_wrongly(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        report = bench.run()
        gapped = sorted(report["known_selection_gaps"])
        self.assertEqual(gapped, sorted(bench.KNOWN_SELECTION_GAPS))
        self.assertEqual(len(gapped), 2)
        for goal_id, cause in report["known_selection_gaps"].items():
            self.assertTrue(cause, f"{goal_id} has no recorded cause")

    def test_decision_synthesizer_exists_but_is_unbindable(self):
        """The right capability is present; it simply cannot be called.

        So the honest behaviour is to refuse, not to substitute a converter.
        """
        cid = "decision.synthesis.typed.stdlib"
        self.assertIn(cid, self.registry)
        goal = "Summarize a markdown document into a decision record."
        score, _spec, _ev = compiler._score(goal, cid, self.registry[cid])
        self.assertGreater(score, 0, "the correct capability no longer matches")
        self.assertIn(
            "structured.decision_evidence.available",
            self.registry[cid].get("requires") or [],
        )
        self.assertIsNone(
            compiler._complete_inputs_via_world_binding(goal, ROOT, cid, self.registry[cid]),
            "expected the synthesizer to remain unbindable without decision evidence",
        )

    def test_best_matching_capabilities_are_unbindable_for_json_goal(self):
        """The measured cause: 12 and 8 unbindable lose to 2 bindable.

        Pre-existing at base 9554215, verified by checking out the base
        goal_compiler.py and re-measuring. Score does not lose to score here;
        bindable beats unbindable regardless of score.
        """
        goal = "Fetch a JSON document and assess its internal consistency."
        for cid in ("knowledge.json.fetch.external", "knowledge.consistency.assess"):
            self.assertIn(cid, self.registry)
            score, _spec, _ev = compiler._score(goal, cid, self.registry[cid])
            self.assertGreaterEqual(score, 8, f"{cid} no longer matches well")
            self.assertIsNone(
                compiler._complete_inputs_via_world_binding(
                    goal, ROOT, cid, self.registry[cid]
                ),
                f"{cid} unexpectedly became bindable",
            )

        # What actually gets selected is far weaker, and binds only because it
        # can: a single identity token ("assess") is enough to be callable.
        ranked = compiler._rank_bindable_candidates(
            goal, self.registry, ROOT, allow_world_binding=False
        )
        self.assertTrue(ranked, "expected some bindable candidate")
        self.assertNotEqual(ranked[0][2], "knowledge.json.fetch.external")
        self.assertNotEqual(ranked[0][2], "knowledge.consistency.assess")

    def test_coverage_gap_is_recorded_separately_from_selection_gaps(self):
        """Insert is missing from the registry; that is not a wrong selection."""
        from canonical.runtime.goal_compilation_benchmark_v1 import (
            KNOWN_COVERAGE_GAPS,
            KNOWN_SELECTION_GAPS,
        )

        self.assertEqual(
            sorted(KNOWN_COVERAGE_GAPS), ["BENCH_SQLITE_CREATE_INSERT_QUERY"]
        )
        self.assertNotIn("BENCH_SQLITE_CREATE_INSERT_QUERY", KNOWN_SELECTION_GAPS)

    def test_no_capability_declares_insert(self):
        """A real coverage gap, not a selection bug: 0 of the live registry."""
        matching = []
        for cid, entry in self.registry.items():
            blob = " ".join(
                [str(x) for x in (entry.get("provides") or [])]
                + [str(x) for x in (entry.get("keywords") or [])]
                + [cid]
            ).lower()
            if "insert" in blob:
                matching.append(cid)
        self.assertEqual(matching, [])


class BenchmarkFloorTests(unittest.TestCase):
    def test_measured_compile_rate_holds_the_floor(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        report = bench.run()
        totals = report["totals"]
        self.assertGreaterEqual(
            totals["compiled"],
            BENCHMARK_COMPILE_FLOOR,
            f"compiled regressed to {totals['compiled']}: "
            + json.dumps(report["failure_causes"], sort_keys=True),
        )
        self.assertGreaterEqual(
            totals["expected_first_capability_selected"],
            BENCHMARK_EXPECTED_FIRST_FLOOR,
            "selection correctness regressed; compiling is not selecting correctly",
        )

    def test_every_benchmark_goal_is_a_real_live_capability(self):
        """The benchmark must not rot when a capability is renamed or removed."""
        from canonical.runtime import live_integrated_brain_v1 as lb
        from canonical.runtime.goal_compilation_benchmark_v1 import (
            BENCHMARK_GOALS,
            EXTENDED_BENCHMARK_GOALS,
        )

        registry = dict(lb.load_verified_registry())
        for spec in list(BENCHMARK_GOALS) + list(EXTENDED_BENCHMARK_GOALS):
            for cid in spec["expected"]:
                self.assertIn(cid, registry, f"{spec['id']} expects missing {cid}")

    def test_extended_tier_holds_its_floor(self):
        """The gain must generalise beyond the original nine goals.

        Measured at base 9554215 with the same registry and the base
        goal_compiler.py checked out: 4/14 compiled and 0/14 selected the
        expected capability. The original nine-goal tier turned out to be the
        pessimistic sample.
        """
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        report = bench.run(bench.EXTENDED_BENCHMARK_GOALS)
        totals = report["totals"]
        base = bench.BASELINE_MEASURED_AT_BASE_9554215["EXTENDED"]
        self.assertEqual(totals["goals"], base["goals"])
        # 11, not 12. Treating governance vocabulary as non-distinctive moved
        # EXT_CLAIM_BIND from "compiles against terminal.kstar.root.assess" to
        # an honest refusal, and moved EXT_EVIDENCE_RANK from that same wrong
        # capability to the correct one. So the compile count fell by one while
        # correct selections rose by one: a wrong execution traded for a
        # refusal is a gain, and the assertion below is what actually pins it.
        self.assertGreaterEqual(
            totals["compiled"],
            11,
            f"extended compile rate regressed to {totals['compiled']}/14: "
            + json.dumps(report["failure_causes"], sort_keys=True),
        )
        self.assertGreaterEqual(totals["expected_first_capability_selected"], 8)
        # And it must actually beat the recorded baseline, not merely sit on it.
        self.assertGreater(totals["compiled"], base["compiled"])
        self.assertGreater(
            totals["expected_first_capability_selected"],
            base["expected_first_selected"],
        )
        # The point of the change: fewer goals executing the wrong capability.
        self.assertLessEqual(totals["compiled_against_wrong_capability"], 3)

    def test_overmatching_capability_is_still_documented(self):
        """The pre-existing catch-all that explains most wrong selections."""
        from canonical.runtime import live_integrated_brain_v1 as lb
        from canonical.runtime.goal_compilation_benchmark_v1 import (
            KNOWN_OVERMATCHING_CAPABILITY,
        )

        registry = dict(lb.load_verified_registry())
        cid = KNOWN_OVERMATCHING_CAPABILITY
        self.assertIn(cid, registry)
        keywords = registry[cid].get("keywords") or []
        # The defect is the breadth of its vocabulary, so pin that it is broad.
        self.assertGreater(len(keywords), 20)


if __name__ == "__main__":
    unittest.main()
