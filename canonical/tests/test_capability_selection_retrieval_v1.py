#!/usr/bin/env python3
"""One sentence selects one capability: retrieval PROPOSES, typed admission DISPOSES.

Measured on this tree, and this is the defect the layer exists for.  A request that literally asks
for the function-invocation surface:

    "Call the function classify_support in canonical/runtime/bounded_claim_support.py with the
     payload .../x.json and save the result to .../x_out.json"

failed closed with `GOAL_INPUT_BINDING_REQUIRED` naming a curated content-match capability, and
`compile_goal` answered `python.software.request.semantic_behavior.compile.v1` - a candidate whose
only declared inputs are `{goal, output_path}`, so it binds any sentence whatsoever.  Nothing was
wrong with the sentence; selection was.

What is asserted here is the behaviour, not the mechanism:

* the shortlist comes from the live receipt-backed ranker (`objective_relevance_bm25`, k=3) - over
  the whole derived surface the intended capability is in the top 3 for 295 of 295 (measured);
* admission is the pinned typed binder, so a sentence that does not state every declared input is
  REFUSED rather than guessed, and a shortlist with two structurally complete candidates selects
  nothing instead of picking one;
* retrieval never displaces anything the pinned scorer can already see - a capability admitted by
  the pinned path keeps its own sentence.  Measured why that scope is not optional: an unscoped
  version displaced `plain_goal.bound_capability.grounding.stdlib` from its own signature sentence
  in favour of a specific sibling, which is a misroute rather than a fix;
* selection is never execution, and the executed path is checked against a direct call.
"""
from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import capability_selection_retrieval_v1 as sel  # noqa: E402
from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402
from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as lib  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import run_raw_goal  # noqa: E402

ROOT = _ROOT
CID = "brain.module.function.invoke"
CLAIM_MODULE = "canonical/runtime/bounded_claim_support.py"
GROUNDING = "plain_goal.bound_capability.grounding.stdlib"
SCRATCH = ROOT / "canonical/astra_runtime/tmp/test_capability_selection_retrieval"
MISSION = "SELECTION_RETRIEVAL_TEST"
CATCH_ALL = {"goal", "output_path"}

_PAYLOAD = {"claim_text": "Orion budget is 40.",
            "evidence_text": "The audited ledger reports that Orion budget is 40."}


def tearDownModule() -> None:
    """A test run leaves no probe file and no controller checkpoint behind."""
    shutil.rmtree(SCRATCH, ignore_errors=True)
    for path in (ROOT / "canonical/astra_runtime/state").glob(MISSION + "*"):
        path.unlink()


def _registry() -> dict:
    return gc._platform_admissible_registry(dict(lib.load_verified_registry()))


def _rel(name: str) -> str:
    return (SCRATCH.relative_to(ROOT) / name).as_posix()


def _sentence() -> str:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "x.json").write_text(json.dumps(_PAYLOAD), encoding="utf-8")
    return (f"Call the function classify_support in {CLAIM_MODULE} with the payload {_rel('x.json')} "
            f"and save the result to {_rel('x_out.json')}")


def _checkpoint_path(result: dict) -> str | None:
    """`run_raw_goal` nests the checkpoint under the controller; `run` puts it at the top level."""
    top = (result.get("controller_checkpoint") or {})
    if isinstance(top, dict) and top.get("path"):
        return str(top["path"])
    nested = ((result.get("controller_execution") or {}).get("controller_checkpoint") or {})
    return str(nested.get("path")) if isinstance(nested, dict) and nested.get("path") else None


def _entry(cid: str, contract: dict, keywords: list[str]) -> dict:
    return {"capability_id": cid, "status": "VERIFIED_BOUND_CAPABILITY", "incremental_spend_usd": 0,
            "entrypoint": "run", "provides": ["x.y"], "keywords": keywords,
            "action_template": {"type": "invoke_capability", "args": contract,
                                "expect": {"type": "field_equals", "field": "status", "value": "OK"}}}


class ProposalTests(unittest.TestCase):
    def test_the_proposal_authority_is_the_live_ranker_and_the_shortlist_is_small(self):
        short = sel.shortlist(_sentence(), _registry(), ROOT)
        self.assertEqual(short["authority"], "PROPOSAL_ONLY__objective_relevance_bm25")
        self.assertEqual(short["k"], 3)
        self.assertTrue(short["proposals"])
        self.assertLessEqual(len(short["proposals"]), 3)
        self.assertEqual(short["candidate_count"], len(_registry()))

    def test_the_ranker_is_the_existing_capability_rather_than_a_second_implementation(self):
        from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25
        self.assertIs(sel.bm25, bm25)

    def test_the_intended_capability_is_recalled_into_the_shortlist(self):
        short = sel.shortlist(_sentence(), _registry(), ROOT)
        self.assertIn(CID, [row["capability_id"] for row in short["proposals"]])


class TypedAdmissionTests(unittest.TestCase):
    def test_every_declared_input_is_bound_from_the_sentence_itself(self):
        decision = sel.select(_sentence(), _registry(), ROOT)
        self.assertEqual(decision["status"], "SELECTED")
        self.assertEqual(decision["selected_capability"], CID)
        self.assertEqual(set(decision["inputs"]), {"source_path", "function", "json_path", "output_path"})
        self.assertEqual(decision["inputs"]["function"], "classify_support")
        self.assertEqual(decision["inputs"]["source_path"], CLAIM_MODULE)

    def test_an_unstated_input_is_refused_rather_than_guessed(self):
        """The payload file does not exist, so the sentence has not stated it: fail closed."""
        missing = f"Call the function classify_support in {CLAIM_MODULE} with the payload {_rel('absent.json')} " \
                  f"and save the result to {_rel('absent_out.json')}"
        decision = sel.select(missing, _registry(), ROOT)
        self.assertEqual(decision["status"], "NOT_SELECTED")
        refusals = [row for row in decision["admissions"] if row.get("admitted") is False]
        self.assertTrue(any(str(row.get("reason", "")).startswith("BINDING_REFUSED") for row in refusals),
                        decision["admissions"])
        self.assertEqual(decision["selected_capability"], None)

    def test_two_structurally_complete_candidates_select_nothing(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        (SCRATCH / "ledger.json").write_text("{}", encoding="utf-8")
        goal = (f"Convert the ledger file {_rel('ledger.json')} and save it to {_rel('converted.json')}")
        registry = {
            "convert.ledger.alpha.stdlib": _entry("convert.ledger.alpha.stdlib",
                                                  {"input_path": "${input.input_path}",
                                                   "output_path": "${input.output_path}"},
                                                  ["convert", "ledger", "file"]),
            "convert.ledger.beta.stdlib": _entry("convert.ledger.beta.stdlib",
                                                 {"input_path": "${input.input_path}",
                                                  "output_path": "${input.output_path}"},
                                                 ["convert", "ledger", "file"]),
        }
        decision = sel.select(goal, registry, ROOT)
        self.assertEqual(decision["status"], "NOT_SELECTED")
        self.assertIn("AMBIGUOUS_TYPED_ADMISSION", str(decision["reason"]))
        self.assertEqual([row["capability_id"] for row in decision["admissions"] if row.get("admitted")],
                         ["convert.ledger.alpha.stdlib", "convert.ledger.beta.stdlib"])

    def test_a_catch_all_alone_is_not_a_selection(self):
        """A capability whose only inputs are {goal, output_path} binds any sentence, so binding it
        is not evidence that the sentence asked for it."""
        SCRATCH.mkdir(parents=True, exist_ok=True)
        (SCRATCH / "any.json").write_text("{}", encoding="utf-8")
        registry = {"absorb.everything.stdlib": _entry("absorb.everything.stdlib",
                                                       {"goal": "${input.goal}",
                                                        "output_path": "${input.output_path}"},
                                                       ["summarise", "file", "save", "output"])}
        decision = sel.select(f"Summarise {_rel('any.json')} and save it to {_rel('any_out.json')}",
                              registry, ROOT)
        self.assertEqual(decision["status"], "NOT_SELECTED")
        self.assertIn("CATCH_ALL_ONLY", str(decision["reason"]))
        self.assertFalse(sel.is_specific(list(CATCH_ALL)))
        self.assertTrue(sel.is_specific(["source_path", "output_path"]))


class FrontCompilerIntegrationTests(unittest.TestCase):
    def test_the_structured_sentence_selects_the_invoker(self):
        compiled = front.compile_goal(_sentence(), _registry(), ROOT)
        self.assertEqual(compiled["selected_capability"], CID)
        self.assertIn("F17_RETRIEVAL_FIRST_TYPED_ADMISSION", compiled["front_compiler"]["rules_applied"])

    def test_a_pinned_catch_all_is_displaced_by_the_specific_capability_and_the_evidence_is_recorded(self):
        """The displacement block, on a two-entry registry so it is exactly one mechanism at work:
        the pinned scorer can only see the catch-all (the derived entry is invisible to it), so
        without F17 the sentence is answered by a capability that binds anything at all."""
        catch_all = _entry("absorb.everything.stdlib",
                           {"goal": "${input.goal}", "output_path": "${input.output_path}"},
                           ["call", "function", "classify", "support", "payload", "save", "result",
                            "canonical", "runtime", "bounded", "claim", "module"])
        registry = {**{cid: entry for cid, entry in _registry().items() if cid == CID},
                    **{catch_all["capability_id"]: catch_all}}
        self.assertEqual(registry[CID].get("capability_source"), "receipt_projection")
        compiled = front.compile_goal(_sentence(), registry, ROOT)
        self.assertEqual(compiled["selected_capability"], CID)
        evidence = compiled["match_evidence"]
        self.assertEqual(evidence.get("displaced_pinned_selection"), catch_all["capability_id"])
        self.assertFalse(sel.is_specific(list(evidence["displaced_catch_all_inputs"])))

    def test_a_capability_the_pinned_scorer_can_see_keeps_its_own_sentence(self):
        """Measured regression, asserted so it cannot come back: this sentence belongs to the
        catch-all `grounding.stdlib`, and its specific sibling must not take it."""
        SCRATCH.mkdir(parents=True, exist_ok=True)
        goal = ("Use ambiguity bound capability existing goal grounding plain registry reuse semantic "
                f"stdlib on and save it to {_rel('out_output_path.json')}")
        compiled = front.compile_goal(goal, _registry(), ROOT)
        self.assertEqual(compiled["selected_capability"], GROUNDING)
        self.assertNotIn("F17_RETRIEVAL_FIRST_TYPED_ADMISSION",
                         compiled["front_compiler"]["rules_applied"])

    def test_selection_never_executes_anything(self):
        before = lane._changed_paths(str(ROOT))
        sel.select(_sentence(), _registry(), ROOT)
        sel.shortlist(_sentence(), _registry(), ROOT)
        self.assertEqual(lane._changed_paths(str(ROOT)) - before, set())
        self.assertFalse((SCRATCH / "x_out.json").exists())


class GoalDrivenSelectionTests(unittest.TestCase):
    def test_a_plain_sentence_is_planned_executed_and_reverified_with_a_real_result(self):
        goal = _sentence()
        before = lane._changed_paths(str(ROOT))
        result = run_raw_goal({"task_id": MISSION, "goal": goal})
        try:
            self.assertTrue(result["pass"], result.get("status"))
            self.assertTrue(str(result["status"]).startswith("PASS__RAW_GOAL_COMPILED"))
            self.assertEqual(result["compiled_capability_id"], CID)
            self.assertEqual(result["selected_plan"], [CID])
            self.assertTrue(all(row.get("pass") for row in result["execution"]))
            # the artifact is a real module call, compared against a direct call of the same function
            record = json.loads((SCRATCH / "x_out.json").read_text(encoding="utf-8"))
            from canonical.runtime.bounded_claim_support import classify_support
            self.assertEqual(record["result"],
                             classify_support(_PAYLOAD["claim_text"], _PAYLOAD["evidence_text"]))
            self.assertEqual(record["result"]["relation"], "SUPPORTS")
            self.assertEqual(record["tier"], "TEST_EVIDENCED")
        finally:
            checkpoint = _checkpoint_path(result)
            if checkpoint and (ROOT / checkpoint).is_file():
                (ROOT / checkpoint).unlink()
            lane.restore_tree(str(ROOT), before, ())


if __name__ == "__main__":
    unittest.main()
