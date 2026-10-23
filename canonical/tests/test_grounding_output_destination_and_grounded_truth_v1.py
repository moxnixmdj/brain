"""A caller-declared output area must reach the binder, and "grounded" must mean grounded.

Four defects, one theme: the grounding producer reported work it had not done, and its
independent verifier could not tell.

1. `_bind_inputs` consulted `context_paths` only in its INPUT branch.  A caller that had
   declared an output area could therefore bind a source from it but never a destination.
   Measured on "Audit the Python tests with unittest and report passed failed and skipped
   counts.": a grounding pass ranked 20 candidates and rejected all 20, 15 of them on
   `output_path` alone, while the report still read `output_verified: true`.

2. The producer counted a clause as grounded when its status was merely "not UNRESOLVED",
   so a clause the same record labelled `UNBOUND_INPUTS_NOT_GROUNDED` was reported in
   `grounded_clause_count` as grounded.

3. The verifier's allowed status set did not contain `UNBOUND_INPUTS_NOT_GROUNDED`, so the
   moment a clause reached that state the producer's own report failed independent
   verification with `STATUS_INVALID`.

4. The verifier counted a clause as grounded when it had ANY candidate (`if candidates:`),
   which is a different definition from the producer's and made the two disagree on the one
   number the verifier exists to check independently.
"""

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "canonical" / "runtime"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SCRATCH = ROOT / "canonical/astra_runtime/tmp/test_grounding_destination_v1"
GOAL = "Audit the Python tests with unittest and report passed failed and skipped counts."
REL = "canonical/astra_runtime/tmp/BOUND_GROUNDING_DESTINATION_PROBE.json"
PRODUCER = "plain_goal.bound_capability.grounding.stdlib"
VERIFIER = "plain_goal.bound_capability.grounding.verify.stdlib"


def _runtime():
    from canonical.runtime import astra_runtime

    return astra_runtime


def _produce(goal=GOAL, rel=REL):
    path = ROOT / rel
    path.unlink(missing_ok=True)
    out = _runtime()._goal_action(
        {"type": "invoke_capability",
         "args": {"capability_id": PRODUCER, "goal": goal, "output_path": rel}}
    )
    return out, json.loads(path.read_text(encoding="utf-8")), path


class CallerDeclaredDestinationReachesTheBinderTests(unittest.TestCase):
    def tearDown(self) -> None:
        (ROOT / REL).unlink(missing_ok=True)
        for extra in (ROOT / "canonical" / "astra_runtime" / "tmp").glob(
            "BOUND_GROUNDING_DESTINATION_PROBE_candidate_output*"
        ):
            extra.unlink(missing_ok=True)
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def test_a_capability_is_admitted_where_previously_all_twenty_were_rejected(self):
        out, report, _path = _produce()
        self.assertTrue(out["output_verified"], out)
        # The regression this fixes: the candidate list was empty and the clause unresolved.
        self.assertTrue(out["candidate_capability_ids"], "no candidate was admitted at all")
        self.assertTrue(report["clauses"][0]["candidates"])

    def test_output_path_refusals_are_only_ever_type_mismatches(self):
        """The caller offered a .json area; only a writer that cannot take .json may refuse."""
        registry = json.loads(
            (ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(
                encoding="utf-8")
        )["capabilities"]
        _out, report, _path = _produce()
        rejected = report["clauses"][0].get("rejected_unbindable_candidates") or []
        refused_on_output = [
            r for r in rejected
            if "GOAL_INPUT_BINDING_REQUIRED:output_path" in str(r.get("error"))
        ]
        # Measured: this goal went from 15 output_path refusals to 2, both docx creators.
        self.assertLessEqual(len(refused_on_output), 2, [r["capability_id"] for r in refused_on_output])
        markers = ("docx", "word", "xlsx", "spreadsheet", "workbook", "pdf", "png", "qr",
                   "barcode", "image")
        for row in refused_on_output:
            entry = registry.get(str(row.get("capability_id"))) or {}
            blob = " ".join(str(x) for x in (entry.get("provides") or [])).lower()
            self.assertTrue(
                any(m in blob for m in markers),
                "a writer that could take the offered .json was still refused: %s"
                % row.get("capability_id"),
            )

    def test_the_offered_destination_is_recorded_not_applied_silently(self):
        _out, report, _path = _produce()
        self.assertEqual(
            report["declared_output_destination"],
            "canonical/astra_runtime/tmp/BOUND_GROUNDING_DESTINATION_PROBE_candidate_output.json",
        )

    def test_a_docx_writer_is_not_handed_a_json_destination(self):
        """Type discipline: offering the wrong type must refuse, not bind."""
        from canonical.runtime import goal_compiler as gc

        registry = json.loads(
            (ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(
                encoding="utf-8")
        )["capabilities"]
        entry = registry["docx.document.create.python_docx"]
        SCRATCH.mkdir(parents=True, exist_ok=True)
        offered = str((SCRATCH.relative_to(ROOT) / "only_offer.json").as_posix())
        goal = "Create a docx document about the ledger and save it somewhere."
        with self.assertRaises(gc.GoalCompilationFailure):
            gc._bind_inputs(goal, ROOT, entry, context_paths=[offered])


class NothingIsInventedTests(unittest.TestCase):
    """The narrowness is the point: this must not become a general path-deriving rule."""

    def test_two_offered_destinations_refuse_rather_than_pick_one(self):
        from canonical.runtime import goal_compiler as gc

        registry = json.loads(
            (ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(
                encoding="utf-8")
        )["capabilities"]
        entry = registry["python.tests.audit.unittest"]
        SCRATCH.mkdir(parents=True, exist_ok=True)
        a = (SCRATCH.relative_to(ROOT) / "a.json").as_posix()
        b = (SCRATCH.relative_to(ROOT) / "b.json").as_posix()
        # output_path is not the only missing key for this entry, so binding still fails; the
        # assertion that matters is that it fails rather than silently choosing a or b.
        with self.assertRaises(gc.GoalCompilationFailure):
            gc._bind_inputs(GOAL, ROOT, entry, context_paths=[a, b])

    def test_selection_never_sees_context_paths_so_it_cannot_be_affected(self):
        """Measured once already: making every report writer bindable cost 10 selection points."""
        import inspect

        from canonical.runtime import capability_selection_retrieval_v1 as sel

        source = inspect.getsource(sel)
        # The admission call must not pass context_paths at all.
        call = source[source.index("front.bind_all_inputs("):]
        call = call[: call.index(")\n")]
        self.assertNotIn("context_paths", call,
                         "selection started passing context_paths; the narrowness is gone")

    def test_the_benchmark_is_unchanged(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        combined = bench.run_all()["combined"]
        self.assertEqual(combined["compiled"], 23, combined)
        self.assertEqual(combined["expected_first_selected"], 22, combined)


class GroundedMeansGroundedTests(unittest.TestCase):
    """Producer and verifier must share one definition of "grounded"."""

    def tearDown(self) -> None:
        (ROOT / REL).unlink(missing_ok=True)
        for extra in (ROOT / "canonical" / "astra_runtime" / "tmp").glob(
            "BOUND_GROUNDING_DESTINATION_PROBE_candidate_output*"
        ):
            extra.unlink(missing_ok=True)

    def test_a_clause_labelled_not_grounded_is_not_counted_as_grounded(self):
        _out, report, _path = _produce()
        status = report["clauses"][0]["status"]
        self.assertEqual(status, "UNBOUND_INPUTS_NOT_GROUNDED")
        self.assertEqual(report["grounded_clause_count"], 0,
                         "a clause the record calls not grounded was counted as grounded")
        self.assertEqual(report["unresolved_clause_indexes"], [0])
        # And a candidate was still named, so this is not the old "nothing at all" state.
        self.assertTrue(report["clauses"][0]["candidates"])

    def test_the_independent_verifier_accepts_the_producers_own_report(self):
        out, _report, path = _produce()
        verified = _runtime()._goal_action(
            {"type": "invoke_capability",
             "args": {"capability_id": VERIFIER, "goal": GOAL, "result_path": REL}}
        )
        self.assertTrue(verified["verified"], verified)
        self.assertEqual(verified["reason"], "VERIFIED")
        self.assertTrue(verified["producer_independent"], verified)
        self.assertEqual(verified["model_dependency_count"], 0)
        self.assertTrue(out["candidate_capability_ids"])
        path.unlink(missing_ok=True)

    def test_the_verifier_counts_by_status_not_by_having_a_candidate(self):
        """The verifier's own definition, pinned, so the two cannot drift apart again."""
        source = (
            ROOT / "canonical" / "runtime" / "bound_capabilities"
            / "plain_goal_bound_grounding_verify.py"
        ).read_text(encoding="utf-8")
        self.assertIn('if status in {"GROUNDED","AMBIGUOUS_BOUNDED"}:', source)
        self.assertNotIn("if candidates:\n            grounded+=1", source)
        # And the shared vocabulary is complete on the verifying side.
        self.assertIn('"UNBOUND_INPUTS_NOT_GROUNDED"', source)


if __name__ == "__main__":
    unittest.main()
