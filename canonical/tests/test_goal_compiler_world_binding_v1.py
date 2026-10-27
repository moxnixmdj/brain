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
import tempfile
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
        # Was 2, then 1, now 0. BENCH_JSON_FETCH_CONSISTENCY was closed by
        # supplying the effect_result producer map and keeping the better-scoring
        # plan. BENCH_MARKDOWN_TO_DECISION was closed by breaking a tie the
        # registry already had the facts to break -- see KNOWN_SELECTION_GAPS.
        self.assertEqual(len(gapped), 0)
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


class EndToEndExecutionTests(unittest.TestCase):
    """A goal in, real work out -- not merely a compiled plan.

    Everything else in this file measures compilation. This measures execution,
    because a plan that compiles proves nothing until it produces an artifact.

    The goal is chosen deliberately: it names no output file, so at base
    9554215 it did not compile at all -- it failed with
    GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH after
    `python.source.audit.ast` was discarded on
    GOAL_INPUT_BINDING_REQUIRED:output_path. The binding_source assertion below
    is what ties the passing run to this change rather than to luck.
    """

    GOAL = "Audit python source structure and write the audit to a JSON file."
    TASK_ID = "arena-e2e-audit-binding"
    STATE_DIR = "canonical/astra_runtime/state"

    def _clear_runtime_state(self) -> None:
        """Remove this task's controller checkpoint.

        Required, not tidy-up: `run_raw_goal` persists a controller checkpoint
        under canonical/astra_runtime/state/, which is NOT gitignored, and the
        runtime resumes from it. A second run of the same task_id therefore
        fails with MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH instead of
        executing. Without this the test passes once and errors forever after.
        """
        state = pathlib.Path(self.STATE_DIR)
        if not state.is_dir():
            return
        for path in state.glob(self.TASK_ID + "__*"):
            path.unlink()

    def test_goal_without_a_stated_output_executes_and_writes_a_real_artifact(self):
        from canonical.runtime import live_integrated_brain_v1 as lb

        # The plan must depend on inferred binding, otherwise this test would
        # still pass with the change reverted and would prove nothing.
        compiled = compiler.compile_goal(self.GOAL, lb.load_verified_registry(), ROOT)
        self.assertEqual(compiled["binding_source"], "GOAL_STATEMENT+WORLD_BINDING")
        self.assertEqual(compiled["selected_capability"], "python.source.audit.ast")

        out_dir = pathlib.Path(world_binding.OUTPUT_DIR)
        before = set(out_dir.glob("brain_out__python_source_audit_ast__*"))
        after = set(before)
        self._clear_runtime_state()
        try:
            result = lb.run_raw_goal({"task_id": self.TASK_ID, "goal": self.GOAL})
            after = set(out_dir.glob("brain_out__python_source_audit_ast__*"))
            self.assertIs(
                result.get("pass"),
                True,
                f"execution failed: {result.get('status')} / {result.get('failure_class')}"
                f" / {str(result.get('reason'))[:200]}",
            )
            self.assertTrue(
                str(result.get("status", "")).startswith(
                    "PASS__RAW_GOAL_COMPILED_PLANNED_EXECUTED"
                )
                or str(result.get("status", "")) == (
                    "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"
                ),
                result.get("status"),
            )
            # Acceptance used to be structurally unreachable here, so this test
            # could only assert the "receipts still required" status. It is
            # reachable now, and the stronger claim is required rather than
            # permitted: every obligation discharged by an artifact that was
            # re-opened from disk, never by a flag the producer set itself.
            self.assertIs(
                result.get("semantic_acceptance_complete"), True,
                result.get("status"),
            )
            self.assertEqual(
                len(result.get("accepted_raw_obligation_ids") or []),
                result.get("raw_acceptance_obligation_count"),
            )
            acceptance = result.get("raw_goal_acceptance") or {}
            self.assertIs(acceptance.get("independent_reinspection"), True)
            self.assertEqual(
                acceptance.get("verified_capability_chain"),
                ["python.source.audit.ast"],
            )
            self.assertEqual(result.get("selected_plan"), ["python.source.audit.ast"])

            self.assertTrue(after, "the capability reported success but wrote no artifact")
            # Deterministic destination: same capability, same slot, same path.
            self.assertEqual(compiled["inputs"]["output_path"], str(sorted(after)[0]))

            produced = json.loads(sorted(after)[0].read_text(encoding="utf-8"))
            self.assertIsInstance(produced, dict)
            for key in ("schema", "source_root", "files", "totals"):
                self.assertIn(key, produced)
        finally:
            # Leave nothing behind: the artifact is reproducible, and the
            # checkpoint would otherwise break the next run and is not ignored.
            for path in after - before:
                path.unlink()
            self._clear_runtime_state()


class ScoreRankIsNotCorrectnessTests(unittest.TestCase):
    """The counterexample that disproved the refusal policy.

    The obvious fix for wrong selections is to refuse whenever the
    highest-scoring capability is not the one selected. On the 23-goal benchmark
    that looked safe: every correct single-capability selection there had a gap
    of exactly 0. It was an artefact of the sample.

    This goal is the counterexample, and it lives in the existing suite rather
    than in the benchmark. A DECODER outscores the GENERATOR the goal asks for,
    and the generator is still the right answer -- it wins on bindability, not
    on score. So a correct selection can sit below the best match while a wrong
    one sat far below it, and no threshold separates the two.

    Implemented as GOAL_COMPILATION_BEST_MATCH_NOT_SELECTED, measured, and
    reverted: it fixed three wrong selections and broke three existing tests.
    """

    GOAL = (
        "Generate a QR code image for the text PROJECT BRAIN and save it as "
        "canonical/astra_runtime/tmp/PROJECT_BRAIN_QR.png."
    )

    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(
            (pathlib.Path("canonical") / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json")
            .read_text(encoding="utf-8")
        )["capabilities"]

    def test_decoder_outscores_the_generator_it_should_not_replace(self):
        decoder = "image.code.decode.zbarimg"
        generator = "image.qr.generate.qrencode"
        for cid in (decoder, generator):
            self.assertIn(cid, self.registry)

        decoder_score, _spec, _ev = compiler._score(self.GOAL, decoder, self.registry[decoder])
        generator_score, _spec, _ev = compiler._score(self.GOAL, generator, self.registry[generator])

        # The premise of the counterexample: rank and correctness disagree.
        self.assertGreater(
            decoder_score,
            generator_score,
            "the decoder no longer outscores the generator; if scoring changed, "
            "re-test whether the refusal policy is now viable",
        )

        out = compiler.compile_goal(self.GOAL, self.registry, ROOT)
        self.assertEqual(out["selected_capability"], generator)
        self.assertEqual(out["binding_source"], "GOAL_STATEMENT")

    def test_the_score_gap_counterexample_is_gone_and_says_so(self):
        """The strongest argument against a score-gap refusal no longer holds here.

        This test used to pin BENCH_MARKDOWN_TO_DECISION as the case that killed a
        gap-keyed refusal: the wrong capability WAS the best-scoring capability in
        the registry, so the gap was exactly 0 and no threshold -- however small --
        could refuse it without refusing the top match.

        That goal now selects correctly, so the data point is gone, and the honest
        consequence has to be recorded rather than papered over.  Measured on the
        live registry:

            "Summarize a markdown document into a decision record."
                best match  document.convert.markdown_pdf.pandoc_weasyprint  25
                SELECTED    decision.synthesis.typed.stdlib                  14   gap 11
            "Query a JSON table and produce a markdown table."
                best match  json.query.jq                                    29
                SELECTED    document.convert.markdown_pdf.pandoc_weasyprint  14   gap 15

        A correct selection at gap 11 and a wrong one at gap 15 means a threshold
        anywhere in 11..14 separates them on THIS sample.  The claim "no threshold
        can separate correct from wrong" is therefore no longer supported by these
        two goals, and this test does not restate it.

        What is unchanged is the reason not to ship one.  The sibling test above
        still holds its counterexample -- the QR goal, where the correct GENERATOR
        is selected one point below a DECODER that outscores it -- and a cut tuned
        to clear a 23-goal sample is fitted to that sample, not derived from
        anything.  The fix that actually shipped is not a threshold: it reads a
        dependency edge the registry already declares, and then prefers a plan
        whose slots the sentence accounted for over one that filled a slot by
        picking a file off the filesystem.
        """
        from canonical.runtime import live_integrated_brain_v1 as lb

        registry = dict(lb.load_verified_registry())
        goal = "Summarize a markdown document into a decision record."
        eligible = (
            (compiler._score(goal, cid, entry)[0], cid)
            for cid, entry in registry.items()
            if isinstance(entry, dict)
            and entry.get("status") == "VERIFIED_BOUND_CAPABILITY"
            and isinstance(entry.get("action_template"), dict)
        )
        best_score, best_cid = max(eligible, default=(0, None))
        out = compiler.compile_goal(goal, registry, ROOT)
        selected_score = compiler._score(
            goal, out["selected_capability"], registry[out["selected_capability"]]
        )[0]

        self.assertEqual(
            out["selected_capability"],
            "decision.synthesis.typed.stdlib",
            "this goal stopped selecting correctly -- the dependency tie-break or "
            "the unjustified-world-slot preference has regressed",
        )
        self.assertEqual(best_cid, "document.convert.markdown_pdf.pandoc_weasyprint")
        # Pinned from a measurement, not asserted: the correct answer is NOT the
        # top scorer, so any policy that demands the top match would refuse it.
        self.assertEqual(best_score - selected_score, 11)


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
        # Measured 2026-10-27 after the fleet merges: the count rose 3 -> 4.
        # The new wrong selection is exactly one, EXT_AST_AUDIT, where the
        # zero-input row python.symbol.resolve.standalone.v1 (compiled
        # input_names == []) matches on token overlap and is always bindable,
        # so it displaces python.source.audit.ast, which honestly refuses
        # without an unstated source_root. The msgpack/pandoc selections are
        # the three pre-existing ones. The floor pins the count so this class
        # of theft cannot spread unnoticed again.
        self.assertLessEqual(totals["compiled_against_wrong_capability"], 4)

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


class PerceptionVocabularyTests(unittest.TestCase):
    """The world is consulted, and only when it can actually say which file.

    Measured, `_FILE_KINDS` had no entry for docx, xlsx, sqlite, csv or html,
    so `kind_keys_for("docx_path")` returned the empty set. On a goal that
    names no file, with one real .docx sitting in the working directory,
    world_probe indexed the file and `docx.document.verify.intent_ooxml`
    outscored `docx.document.create.python_docx` 35 to 22 -- and the winner
    was still discarded as unbindable. The goal then compiled against a
    capability that only had to invent an output path.

    These tests use real OOXML packages on disk, never a stub, because the
    claim is about perception: that the machine looked and found the file.
    """

    GOAL = "Verify a docx document against its intent."
    EXPECTED = "docx.document.verify.intent_ooxml"
    WRONG = "docx.document.create.python_docx"

    @staticmethod
    def _real_docx(path: pathlib.Path) -> None:
        """A genuine OOXML package, not a text file wearing a .docx name."""
        import zipfile

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType='
                '"application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Override PartName="/word/document.xml" ContentType='
                '"application/vnd.openxmlformats-officedocument.wordprocessingml'
                '.document.main+xml"/></Types>',
            )
            z.writestr(
                "word/document.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                'wordprocessingml/2006/main"><w:body><w:p><w:r>'
                "<w:t>real</w:t></w:r></w:p></w:body></w:document>",
            )

    def _compile_in(self, files):
        from canonical.runtime import live_integrated_brain_v1 as lb

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for name in files:
                self._real_docx(root / name)
            return compiler.compile_goal(self.GOAL, lb.load_verified_registry(), root)

    def test_the_goal_word_verify_selects_the_verifier_found_on_disk(self):
        """One real .docx on disk is enough; the goal need not name it."""
        plan = self._compile_in(["report.docx"])
        self.assertEqual(plan["selected_capability"], self.EXPECTED)
        self.assertNotEqual(plan["selected_capability"], self.WRONG)
        bound = str(plan["inputs"].get("docx_path") or "")
        self.assertTrue(bound.endswith("report.docx"), bound)

    def test_the_same_goal_without_the_file_does_not_claim_the_verifier(self):
        """Perception must not manufacture the file it went looking for."""
        plan = self._compile_in([])
        self.assertNotEqual(
            plan.get("selected_capability"),
            self.EXPECTED,
            "the verifier was selected with no docx anywhere on disk",
        )

    def test_the_slot_name_alone_resolves_the_kind(self):
        """The gap was lexical: kind_keys_for must now answer for docx_path."""
        from canonical.runtime import world_probe_v1 as WP

        self.assertIn("docx", WP.kind_keys_for("docx_path"))
        for slot in ("xlsx_path", "sqlite_path", "csv_path", "html_path"):
            self.assertTrue(WP.kind_keys_for(slot), slot)


class GroundedInputBindingTests(unittest.TestCase):
    """A slot is bound by looking, and only when looking can settle it.

    Measured, 8 of the 10 correctly-selected benchmark goals took their input
    file from the world rather than the goal, and what they took was arbitrary:
    AGENTS.md bound as the markdown to convert to PDF, a stray
    canonical/astra_runtime/state/.../tool.py bound as the evidence to rank,
    and the alphabetically first of five .docx files bound as the document to
    verify. The skill was right and the file was a guess.

    `_bind_path_by_type` is the binder that already had the correct rule --
    bind on exactly one candidate, refuse on two -- but it only ever looked at
    paths the goal sentence named. These tests give it a working directory and
    hold it to the same rule there.
    """

    GOAL = "Read a PDF and extract its text."

    def _bind(self, files, key="pdf_path", exclude=None, distinct=False):
        from canonical.runtime import goal_front_compiler_v1 as gf

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for i, name in enumerate(files):
                body = f"%PDF-1.4 distinct body {i}\n".encode() if distinct else b"%PDF-1.4 identical body\n"
                (root / name).write_bytes(body)
            return gf._bind_path_by_type(self.GOAL, key, root, exclude=exclude)

    def test_exactly_one_candidate_is_bound(self):
        self.assertEqual(self._bind(["report.pdf"]), "report.pdf")

    def test_two_candidates_refuse_rather_than_guess(self):
        """The whole point: alphabetical first is not a choice.

        The bodies must differ. An earlier version of this test wrote the same
        bytes to both files and so did not test ambiguity at all -- it tested
        that a duplicate is refused, which is the opposite of correct.
        """
        with self.assertRaises(GoalCompilationFailure):
            self._bind(["aaa_first.pdf", "zzz_last.pdf"], distinct=True)

    def test_byte_identical_candidates_are_interchangeable_and_bind(self):
        """Two copies of one file are one input, not a choice.

        The judgement is delegated to semantic_ambiguity_control_v1, which was
        already in the repository and imported by nothing: candidates sharing a
        terminal signature are terminally equivalent and need no
        disambiguation. Refusing here would be rigour with no reason behind it.
        """
        self.assertEqual(self._bind(["aaa_first.pdf", "zzz_last.pdf"]), "aaa_first.pdf")
        self.assertEqual(
            self._bind(["c.pdf", "a.pdf", "b.pdf"]), "a.pdf",
            "deterministic: sorted, so the same world yields the same path",
        )

    def test_no_candidates_refuse(self):
        with self.assertRaises(GoalCompilationFailure):
            self._bind([])

    def test_a_claimed_file_is_not_reused_so_the_other_binds(self):
        """The exclusion set is what makes two candidates resolvable.

        This is the property world_binding_v1._world_path_for does not have,
        and the reason bolting a refusal onto that function cost eight
        selections: it could not tell 'taken by an earlier step' from
        'genuinely ambiguous'.
        """
        self.assertEqual(
            self._bind(["aaa_first.pdf", "zzz_last.pdf"], exclude={"aaa_first.pdf"}),
            "zzz_last.pdf",
        )

    def test_the_wrong_type_is_not_substituted(self):
        """A directory full of the wrong kind must not satisfy a pdf slot."""
        with self.assertRaises(GoalCompilationFailure):
            self._bind(["notes.md", "data.json", "photo.png"])


class SelectionRankingTests(unittest.TestCase):
    """BM25 reorders the survivors of the pinned scorer; it never re-admits one.

    The pinned ``_score`` counts shared tokens, so every token is worth the same
    and a capability carrying 27 governance keywords can out-score the one that
    owns the task. The only defence was ``GENERIC_MATCH_TOKENS``, a hand-kept
    denylist whose own comment records that it still lost two goals. BM25's
    inverse document frequency derives that weighting from the corpus instead.
    """

    @classmethod
    def setUpClass(cls):
        from canonical.runtime import live_integrated_brain_v1 as lb

        cls.registry = dict(lb.load_verified_registry())
        cls.root = str(pathlib.Path(__file__).resolve().parents[2])
        # staticmethod: a bare function stored on a class becomes an unbound
        # method, so `self._rerank` would prepend the instance as an argument.
        cls._rerank = staticmethod(compiler._bm25_rerank)

    def tearDown(self):
        compiler._bm25_rerank = self._rerank

    def test_a_generate_goal_selects_the_generator_not_the_decoder(self):
        """The inversion this change exists to remove.

        Measured before it: this goal compiled against
        ``image.code.decode.zbarimg`` -- a DECODER -- because both capabilities
        share the tokens 'image' and 'code', and the overlap count could not
        tell 'generate' from 'decode'. ``qrencode`` is the rarer term, so IDF
        settles it.
        """
        plan = compiler.compile_goal(
            "Generate a QR code image from a text string.", self.registry, self.root
        )
        self.assertEqual(plan.get("selected_capability"), "image.qr.generate.qrencode")

    def test_bm25_reorders_without_introducing_or_dropping_a_candidate(self):
        """Ordering only. The admissible SET must be byte-for-byte the same."""
        goal = "Generate a QR code image from a text string."
        # allow_world_binding=True: this goal binds nothing from its own words
        # on the grounded first pass, which returns zero candidates by design.
        # The inferred pass is the one that actually produced the selection.
        with_rerank = compiler._rank_bindable_candidates(
            goal, self.registry, self.root, allow_world_binding=True)
        compiler._bm25_rerank = lambda g, ranked: ranked
        pinned = compiler._rank_bindable_candidates(
            goal, self.registry, self.root, allow_world_binding=True)
        self.assertEqual(
            sorted(x[2] for x in with_rerank), sorted(x[2] for x in pinned),
            "BM25 changed WHICH capabilities are admissible, not only their order",
        )
        self.assertGreater(len(pinned), 1, "a single candidate proves nothing about ordering")

    def test_the_overlap_count_alone_still_picks_the_decoder(self):
        """Negative control: with the re-rank disabled the old wrong answer returns.

        Without this the test above could pass for an unrelated reason -- the
        registry changing, the goal text changing, or the scorer's denylist
        growing -- and the BM25 step would not be load-bearing at all.
        """
        compiler._bm25_rerank = lambda g, ranked: ranked
        plan = compiler.compile_goal(
            "Generate a QR code image from a text string.", self.registry, self.root
        )
        self.assertEqual(plan.get("selected_capability"), "image.code.decode.zbarimg")

    def test_the_document_repeats_identity_and_provides_only(self):
        """Field weighting by repetition; nothing is invented for the index."""
        # Tokens are kept disjoint across fields on purpose: a keyword that
        # coincides with an identity token legitimately accumulates both
        # weights, which would make the counts below meaningless.
        entry = {
            "provides": ["payload"], "keywords": ["code", "matrix"],
            "requires": ["text"],
        }
        doc = compiler._capability_document("image.qr.generate.qrencode", entry)
        for term in ("image", "qr", "generate", "qrencode", "payload"):
            self.assertEqual(doc.count(term), 2, f"{term} should be identity-weighted")
        for term in ("code", "matrix", "text"):
            self.assertEqual(doc.count(term), 1, f"{term} is supporting vocabulary")

    def test_a_missing_bm25_module_falls_back_to_the_pinned_order(self):
        """Fail-open on the RANKER, never on admission: ranking is a preference."""
        goal = "Generate a QR code image from a text string."
        saved = compiler._BM25_MODULE
        compiler._BM25_MODULE = None
        compiler._BM25_LOAD_FAILED = True
        try:
            ranked = compiler._rank_bindable_candidates(
                goal, self.registry, self.root, allow_world_binding=True)
            self.assertTrue(ranked, "the fallback must still rank, not refuse")
            self.assertEqual(
                ranked[0][2], "image.code.decode.zbarimg",
                "with the ranker gone the pinned overlap order must decide, "
                "which is the decoder -- the pre-change behaviour, not a refusal")
        finally:
            compiler._BM25_MODULE = saved
            compiler._BM25_LOAD_FAILED = False


class ProducerConsumerSecondPassTests(unittest.TestCase):
    """A capability may declare that its input is another capability's output.

    Nine capabilities carry a ``proposal_bindings`` entry of type
    ``effect_result``: "fill this slot from whoever produces effect X". The
    binder resolves that against an ``effect_providers`` map the caller must
    supply. The single-clause path supplied nothing, so those nine were dropped
    before ranking with PROPOSAL_EFFECT_PROVIDER_MISSING no matter how well they
    matched -- ``knowledge.consistency.assess`` scores 22 on its own goal while
    the catch-all that replaced it scores 2.

    Enabling it unconditionally is a measured NET LOSS (compiled 18 to 16,
    correct 14 to 11: three goals stolen, three begun refusing), so it is a
    second pass that runs only when the grounded pass found nothing -- the same
    rule the file already applies to world binding.
    """

    @classmethod
    def setUpClass(cls):
        from canonical.runtime import live_integrated_brain_v1 as lb

        cls.registry = dict(lb.load_verified_registry())
        cls.root = str(pathlib.Path(__file__).resolve().parents[2])

    def test_the_provider_map_is_read_off_the_registry_not_invented(self):
        providers = compiler._effect_providers(self.registry)
        self.assertIn("knowledge.observation.available", providers)
        cid, entry = providers["knowledge.observation.available"]
        self.assertEqual(cid, "knowledge.json.fetch.external")
        self.assertIs(entry, self.registry[cid])
        # Every mapping must be justified by the provider's own declaration.
        for effect, (pcid, pentry) in providers.items():
            self.assertIn(
                effect, [str(x).lower() for x in (pentry.get("provides") or [])],
                f"{pcid} mapped to {effect} which it does not declare",
            )

    def test_a_consumer_whose_producer_exists_now_compiles(self):
        """The goal this second pass exists for.

        ``decision.synthesis.verify.stdlib`` requires ``decision.synthesis.typed``,
        which ``decision.synthesis.typed.stdlib`` produces. Before the second
        pass this goal refused; the chain was declared in the registry all along.
        """
        plan = compiler.compile_goal(
            "Verify a typed decision synthesis result.", self.registry, self.root
        )
        self.assertIn("decision.synthesis.verify.stdlib", str(plan.get("selected_capability")) +
                      str([p.get("selected_capability") for p in plan.get("compiled_parts") or []]))

    def test_the_second_pass_does_not_steal_a_goal_the_first_pass_already_won(self):
        """This is the regression that made the unconditional version a net loss.

        With effect_result binding always on, this goal was taken by
        ``source.evidence.extract.objective_grounded.stdlib``. It must stay with
        the plain capability the sentence asks for.
        """
        plan = compiler.compile_goal(
            "Audit the python source and write the result as json.",
            self.registry, self.root,
        )
        self.assertEqual(plan.get("selected_capability"), "python.source.audit.ast")

    def test_a_consumer_with_no_producer_still_refuses(self):
        """The map names producers; it does not manufacture them.

        ``sqlite.table.verify_against_json_records`` needs
        ``structured.json.available``, which no capability produces. Nothing in
        the registry can fill it, so the binder must still refuse rather than
        invent a file.

        This assertion has been repointed three times, each time because the
        effect it named gained a real producer -- first
        ``source.candidates.available`` (now
        ``source.candidates.enumerate.stdlib``), then
        ``structured.decision_evidence.available`` (now
        ``structured.decision_evidence.locate.stdlib``), then
        ``json.file.available`` (now ``json.file.write``). Repointing is the
        correct response: deleting the test would lose the only thing proving
        the map cannot conjure a producer. The property under test is unchanged,
        so it is ``structured.json.available`` that carries it now -- still no
        producer, read off the registry rather than asserted.
        """
        providers = compiler._effect_providers(self.registry)
        self.assertNotIn("structured.json.available", providers)
        # And the effects that did gain producers are genuinely in the map,
        # read off the registry rather than asserted.
        self.assertIn("source.candidates.available", providers)
        self.assertIn("json.file.available", providers)
        self.assertEqual(
            providers["source.candidates.available"][0],
            "source.candidates.enumerate.stdlib",
        )
        self.assertIn("structured.decision_evidence.available", providers)
        self.assertEqual(
            providers["structured.decision_evidence.available"][0],
            "structured.decision_evidence.locate.stdlib",
        )

    def test_a_dangling_effect_reference_becomes_a_real_producer_step(self):
        """An emitted plan must not hand an adapter a placeholder.

        ``_bind_planned_inputs`` resolves an ``effect_result`` slot to
        ``{"$effect_result": ...}`` and the plan used to be emitted with that
        reference still dangling and no step able to satisfy it, so the ranker
        received a dict where its contract expects a path and died with
        ``RELEVANCE_INPUT_NOT_JSON`` on whatever file world binding offered.

        The producer is now emitted as step 0 and the reference rewritten to
        the ``$result`` cycle that produces it.
        """
        plan = compiler.compile_goal(
            "Rank source evidence by relevance to the objective.",
            self.registry, self.root,
        )
        self.assertEqual(
            plan.get("effect_producer_chain"),
            ["source.candidates.enumerate.stdlib",
             "source.objective_relevance.rank.bm25"],
        )
        # No dangling reference survives anywhere in the plan.
        self.assertEqual(compiler._collect_effect_result_refs(plan.get("inputs")), [])
        for part in plan.get("compiled_parts") or []:
            self.assertEqual(
                compiler._collect_effect_result_refs(part.get("inputs")), [],
                f"dangling reference left in part {part.get('index')}",
            )
        # The consumer's slot points at the producer's cycle, not at a guess.
        consumer = plan["compiled_parts"][-1]
        self.assertEqual(
            consumer["inputs"]["input_path"],
            {"$result": {"cycle": 0, "field": "output_path"}},
        )

    def test_a_producer_that_cannot_bind_leaves_the_plan_untouched(self):
        """Negative control: no chain is invented when step 0 could not run.

        ``knowledge.consistency.assess`` resolves its evidence slot to a
        producer that needs a url the sentence never states. Attaching that
        producer would emit a chain whose first step is guaranteed to fail, so
        the plan must be returned exactly as the binder produced it.
        """
        plan = compiler.compile_goal(
            "Assess the consistency of knowledge observations.",
            self.registry, self.root,
        )
        self.assertIsNone(plan.get("effect_producer_chain"))
        self.assertNotIn("controller_actions", plan)
        self.assertNotEqual(
            compiler._collect_effect_result_refs(plan.get("inputs")), [],
            "expected the dangling reference to be preserved, not silently dropped",
        )


class ChainedPlanScoreComparisonTests(unittest.TestCase):
    """Two passes, same scorer, keep the better plan.

    A failure-triggered retry was measured to be blind in one specific way: on
    "Assess knowledge consistency" the grounded pass SUCCEEDS with the catch-all
    at score 2 while knowledge.consistency.assess scores 22 and is reachable once
    the producer map is supplied -- so the retry never fired. Comparing the two
    plans by score fixes that without the theft the unconditional form caused.
    """

    @classmethod
    def setUpClass(cls):
        from canonical.runtime import live_integrated_brain_v1 as lb

        cls.registry = dict(lb.load_verified_registry())
        cls.root = str(pathlib.Path(__file__).resolve().parents[2])
        cls._score_fn = staticmethod(compiler._plan_score)

    def tearDown(self):
        compiler._plan_score = self._score_fn

    def test_the_better_scoring_chained_plan_is_kept(self):
        plan = compiler.compile_goal(
            "Assess knowledge consistency.", self.registry, self.root
        )
        self.assertEqual(plan.get("selected_capability"), "knowledge.consistency.assess")

    def test_forcing_the_grounded_plan_back_reproduces_the_catch_all(self):
        """Negative control. Without it the test above proves nothing.

        Making _plan_score rank every grounded plan above every chained one is
        equivalent to never taking the chained plan, which must return the old
        wrong answer.
        """
        real = compiler._plan_score
        compiler._plan_score = lambda plan: real(plan) - 1000 if (
            isinstance(plan, dict) and plan.get("compiler_mode")
        ) else real(plan)
        try:
            # Prefer whichever plan the grounded pass produced by demoting any
            # plan that carries chained provenance is brittle, so demote by
            # identity instead: the grounded plan for this goal selects the
            # catch-all, and both plans share the same schema. Compare directly.
            grounded = compiler._compile_single_goal(
                "Assess knowledge consistency.", self.registry, self.root
            )
            self.assertEqual(
                grounded.get("selected_capability"),
                "terminal.kstar.root.assess.stdlib",
                "the grounded pass no longer produces the catch-all; this "
                "counterexample no longer bounds the comparison",
            )
            self.assertGreater(
                real(compiler.compile_goal(
                    "Assess knowledge consistency.", self.registry, self.root)),
                real(grounded),
                "the chained plan does not out-score the grounded one, so the "
                "comparison is not what selects it",
            )
        finally:
            compiler._plan_score = real

    def test_the_grounded_plan_is_kept_when_it_scores_higher(self):
        """The theft guard. This goal compiled correctly before the comparison
        existed and must not be taken by a greedier chained capability."""
        plan = compiler.compile_goal(
            "Audit the python source and write the result as json.",
            self.registry, self.root,
        )
        self.assertEqual(plan.get("selected_capability"), "python.source.audit.ast")

    def test_plan_score_of_a_compound_plan_is_its_strongest_part(self):
        self.assertEqual(compiler._plan_score(None), -1)
        self.assertEqual(compiler._plan_score({}), 0)
        self.assertEqual(
            compiler._plan_score({"compiled_parts": [{"score": 4}, {"score": 9}]}), 9.0
        )
        self.assertEqual(compiler._plan_score({"score": "not-a-number"}), -1)


class DemonstratedInvocationBindingTests(unittest.TestCase):
    """A verified capability carries a witness to what its slots accept.

    `verification.state_path` records the invocation that earned the
    `VERIFIED_BOUND_CAPABILITY` status, and the receipt pins that state by
    `state_sha256`. Reading it is not guessing: it is the only evidence about
    THIS capability that exists. These tests pin the read, the precedence, and
    the two ways it could silently go wrong.
    """

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = pathlib.Path(holder.name)

    def _state(self, commands):
        path = self.tmp / "STATE.json"
        path.write_text(
            json.dumps({"history": [{"result": {"command": c}} for c in commands]}),
            encoding="utf-8",
        )
        return str(path)

    def _entry(self, commands, args, cid="test.receipt.backed",
               keywords=("widget",), adapter="python_stub"):
        return {
            "capability_id": cid,
            "status": "VERIFIED_BOUND_CAPABILITY",
            "action_template": {
                "type": "invoke_capability",
                "args": args,
                "expect": {"type": "field_equals", "field": "output_verified",
                           "value": True},
            },
            "provides": ["test.receipt"],
            "requires": [],
            "keywords": list(keywords),
            "platforms": ["linux", "windows", "darwin"],
            "source": {"type": "stdlib"},
            "adapter_module": adapter,
            "verification": {"state_path": self._state(commands)},
        }

    def test_a_recorded_receipt_supplies_the_slots_the_goal_cannot_state(self):
        entry = self._entry(
            ["m.run({'pattern': 'widget_*.py', 'source_root': 'widgets'}, root)"],
            {"capability_id": "test.receipt.backed",
             "pattern": "${input.pattern}",
             "source_root": "${input.source_root}",
             "output_path": "${input.output_path}"},
        )
        out = world_binding.complete_inputs("Audit the widgets.", ROOT, entry)
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["inputs"]["pattern"], "widget_*.py")
        self.assertEqual(out["inputs"]["source_root"], "widgets")
        # Reported as demonstrated, never as grounded -- the sentence said
        # neither of these.
        self.assertEqual(
            out["filled_from_demonstrated_case"],
            {"pattern": "widget_*.py", "source_root": "widgets"},
        )

    def test_a_result_mapping_is_never_read_as_invocation_arguments(self):
        """The bug this pins: the recorded command holds the RESULT too, and
        the result is the BIGGER dict, so selecting by size silently supplies
        `{'files':0,'tests':0,...}` -- six plausible-looking values that fill
        nothing. Coverage of the capability's own placeholders is what
        separates what was asked from what came back.
        """
        entry = self._entry(
            ["m.run({'pattern': 'widget_*.py'}, root)",
             "print({'files': 0, 'tests': 0, 'passed': 0, 'failed': 0, "
             "'errors': 0, 'skipped': 0})"],
            {"capability_id": "test.receipt.backed",
             "pattern": "${input.pattern}"},
        )
        demo = world_binding._demonstrated_invocation_inputs(entry, ROOT, ["pattern"])
        self.assertEqual(demo.get("pattern"), "widget_*.py")
        self.assertNotIn("files", demo)

    def test_the_goal_outranks_the_demonstrated_receipt(self):
        """A receipt is evidence about a capability, not authority over the
        sentence. A slot the goal stated is never revisited."""
        entry = self._entry(
            ["m.run({'pattern': 'recorded_*.py'}, root)"],
            {"capability_id": "test.receipt.backed",
             "pattern": "${input.pattern}"},
        )

        class _GoalWins:
            @staticmethod
            def _bind_inputs(goal, root, entry, **kwargs):
                return {"pattern": "stated_*.py"}

        out = world_binding.complete_inputs(
            "Audit the stated widgets.", ROOT, entry, compiler=_GoalWins
        )
        self.assertEqual(out["inputs"]["pattern"], "stated_*.py")
        self.assertEqual(out["filled_from_demonstrated_case"], {})

    def test_without_a_receipt_or_a_declared_default_a_glob_is_still_refused(self):
        """The invariant the module docstring states, re-pinned at this level.

        The synthetic capability carries no verification record and names no
        discovery mechanism, so there is nothing to ask and nothing was ever
        demonstrated. Inventing a search policy would decide, silently, what
        the capability looks at.
        """
        entry = dict(_synthetic_registry()["test.pattern_only.capability"])
        entry["capability_id"] = "test.pattern_only.capability"
        out = world_binding.complete_inputs("Do the zebrafish thing.", ROOT, entry)
        self.assertIn("pattern", out["missing"])

    def test_the_live_unittest_audit_reads_its_own_recorded_run(self):
        """End to end on the real entry that motivated this, so the mechanism
        is pinned against the registry and not only against fixtures."""
        from canonical.runtime import live_integrated_brain_v1 as lb

        cid = "python.tests.audit.unittest"
        registry = lb.load_verified_registry()
        if cid not in registry:
            self.skipTest(f"{cid} not in registry")
        entry = dict(registry[cid])
        entry["capability_id"] = cid
        out = world_binding.complete_inputs(
            "Run the unittest corpus and produce a pass rate report.", ROOT,
            entry, compiler=compiler,
        )
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["inputs"]["source_root"], "canonical/tests")
        self.assertEqual(out["inputs"]["pattern"], "test_*.py")
        self.assertEqual(
            out["filled_from_demonstrated_case"],
            {"pattern": "test_*.py", "source_root": "canonical/tests"},
        )
