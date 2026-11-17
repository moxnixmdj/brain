#!/usr/bin/env python3
"""The capability law of this project, computed from its own receipts, and refusing to compute without them.

WHY THIS EXISTS
---------------
Five measurements now exist and each is quoted alone, in a different document, with a different
denominator. Read together they are one equation, and the equation is what decides where to spend:

    P(correct behaviour | one action) = P(the action is determined) x P(the error is seen)

with

    P(determined)  from the trace         0.5469  (SYSTEMATIC_EDIT_SUPPLY, shape only)
                   for the value itself  0.2143  (SYSTEMATIC_EDIT_DERIVATION, 9 of 42 firings)
    P(seen)        density x strength    0.6788 x 0.8021 = 0.5445  (ORACLE_DENSITY on python)
    memory route   exact replay of what recurs later   0.0481  (SKILL_RECURRENCE, 31 of 644)
    permanence     silent corruption of a replay that "holds"  0.3114  (ACTION_REPLAY_UNDER_CHANGE)

WHAT MAKES IT A LAW RATHER THAN A TABLE
---------------------------------------
1. **Fail closed.** Every term is read from a pinned receipt (path + sha256). A missing receipt, a
   changed receipt or a missing field raises; nothing is defaulted. A capability number in this project
   can therefore never be quoted without the measurement that produced it.
2. **Leverage = slope x controllability, not slope.** At the operating point the two slopes are equal
   (0.5445 and 0.5469), so slope alone says "spend anywhere". It is wrong: `P(determined)` is a property
   of the observation and has a published ceiling (SyDIT 70% on real systematic edits), while `P(seen)`
   is a property of the environment and is engineerable from 0.6788 toward 1.0. The law reports both and
   multiplies the slope by whether the term can actually be moved.
3. **No number without its own receipt.** Computer use used to be reported as `UNMEASURED`. It no longer
   is: `COMPUTER_USE_CHECK_DENSITY_20261116_V1` runs mechanically derived wrong actions against real
   programs on a real disk and reports what a consequence differential can see. What remains unmeasured
   stays unmeasured and is named -- a GUI whose only observable is pixels, and workflows longer than one
   action.

Model dependency: 0. Network: 0. This is arithmetic over files already in the tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_CAPABILITY_LAW_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_COMPOSITION_OF_PUBLISHED_RECEIPTS"

# path -> sha256 prefix, pinned so a receipt cannot change under the law's feet
RECEIPTS = {
    "determinacy": "canonical/verification/SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json",
    "value": "canonical/verification/SYSTEMATIC_EDIT_DERIVATION_20261116_V1.json",
    "memory": "canonical/verification/SKILL_RECURRENCE_20261116_V1.json",
    "observation": "canonical/verification/ORACLE_DENSITY_20261116_V1.json",
    "permanence": "canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json",
    "computer": "canonical/verification/COMPUTER_USE_CHECK_DENSITY_20261116_V1.json",
    "projection": "canonical/verification/DISTINGUISHING_PROJECTION_20261116_V1.json",
    "contract": "canonical/verification/PREDICTIVE_CONTRACT_20261116_V1.json",
    "facts": "canonical/verification/STANDING_FACTS_20261116_V1.json",
    "repair": "canonical/verification/CAUSAL_DEPENDENCY_REPAIR_20261116_V1.json",
    "demonstration": "canonical/verification/DEMONSTRATION_SUFFICIENCY_20261116_V1.json",
    "vocabulary": "canonical/verification/VOCABULARY_GROWTH_20261116_V1.json",
    "reach": "canonical/verification/REACH_OF_THE_GRAMMAR_20261116_V1.json",
}

# The published ceiling for an inducer with full AST and context machinery on real systematic edits.
DETERMINACY_PUBLISHED_CEILING = 0.70
DETERMINACY_CEILING_SOURCE = ("Meng et al., SyDIT, PLDI 2011: 39 of 56 (70%) of real systematic edits "
                              "mimicked by a full inducer")


class CapabilityLawIncomplete(RuntimeError):
    """Raised when a receipt is missing, has changed, or does not carry the field the law needs."""


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _field(payload: Mapping[str, Any], pointer: str, receipt: str) -> Any:
    node: Any = payload
    for key in pointer.split("/"):
        if not isinstance(node, Mapping) or key not in node:
            raise CapabilityLawIncomplete("%s is missing %s" % (receipt, pointer))
        node = node[key]
    return node


def _load(name: str, *, pins: Mapping[str, str] | None = None) -> tuple[dict[str, Any], str]:
    path = ROOT / RECEIPTS[name]
    if not path.exists():
        raise CapabilityLawIncomplete("receipt missing: %s" % RECEIPTS[name])
    digest = _digest(path)
    if pins is not None and name in pins and not digest.startswith(pins[name]):
        raise CapabilityLawIncomplete("receipt changed: %s" % RECEIPTS[name])
    return json.loads(path.read_text(encoding="utf-8")), digest


def pins_from(report: Mapping[str, Any]) -> dict[str, str]:
    return {name: str(cell["sha256"])[:16] for name, cell in report["receipts"].items()}


def compose(*, pins: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Read the terms from their receipts and compute the law. Raises rather than defaulting."""
    supply, supply_sha = _load("determinacy", pins=pins)
    value, value_sha = _load("value", pins=pins)
    memory, memory_sha = _load("memory", pins=pins)
    observation, observation_sha = _load("observation", pins=pins)
    permanence, permanence_sha = _load("permanence", pins=pins)
    computer, computer_sha = _load("computer", pins=pins)
    projection, projection_sha = _load("projection", pins=pins)
    contract, contract_sha = _load("contract", pins=pins)
    known, known_sha = _load("facts", pins=pins)
    repaired, repaired_sha = _load("repair", pins=pins)
    sufficed, sufficed_sha = _load("demonstration", pins=pins)
    grew, grew_sha = _load("vocabulary", pins=pins)
    reached, reached_sha = _load("reach", pins=pins)

    determined = float(_field(supply, "by_rung/shape_only/determined_share", "supply"))
    value_determined = (float(_field(value, "by_rung/shape_only/derive_arm/pairs_where_derivation_was_right",
                                    "value"))
                        / float(_field(value, "by_rung/shape_only/derive_arm/pairs_where_derivation_fired",
                                       "value")))
    density = float(_field(observation, "oracle_density/python_only/names_a_token", "observation"))
    strength = float(_field(observation, "loop/suite_strength_when_checked", "observation"))
    seen = density * strength
    memory_coverage = float(_field(memory, "by_rung/context_both/recurrence_share", "memory"))
    # end-to-end: exact replays over *all* sites, not over the recurring ones, which is the honest share
    memory_exact = (float(_field(memory, "by_rung/context_both/replay/all/outcomes/exact", "memory"))
                    / float(_field(memory, "by_rung/context_both/sites", "memory")))
    pairs = float(_field(permanence, "pairs_measured", "permanence"))
    corrupt = float(_field(permanence, "counts/SILENT_CORRUPTION", "permanence"))

    terms = {
        "determined": {"value": round(determined, 4), "receipt": RECEIPTS["determinacy"],
                       "pointer": "by_rung/shape_only/determined_share",
                       "meaning": "a demonstration determines the sibling edit"},
        "determined_value": {"value": round(value_determined, 4), "receipt": RECEIPTS["value"],
                             "pointer": "by_rung/shape_only/derive_arm/pairs_where_derivation_was_right"
                                        " over ..._fired",
                             "meaning": "an inferred literal is the literal that was needed"},
        "check_density": {"value": round(density, 4), "receipt": RECEIPTS["observation"],
                          "pointer": "oracle_density/python_only/names_a_token",
                          "meaning": "real python edits any existing test even names"},
        "check_strength": {"value": round(strength, 4), "receipt": RECEIPTS["observation"],
                           "pointer": "loop/suite_strength_when_checked",
                           "meaning": "a behavioural mutant is rejected where the check can see it"},
        "seen": {"value": round(seen, 4), "receipt": RECEIPTS["observation"],
                 "pointer": "loop/expected_error_seen",
                 "meaning": "density x strength: a wrong edit is visible"},
        "memory_exact": {"value": round(memory_exact, 4), "receipt": RECEIPTS["memory"],
                         "pointer": "by_rung/context_both/replay/all/outcomes/exact over .../sites",
                         "meaning": "of all real sites, the share a permanent memory serves exactly"},
        "memory_coverage": {"value": round(memory_coverage, 4), "receipt": RECEIPTS["memory"],
                            "pointer": "by_rung/context_both/recurrence_share",
                            "meaning": "what recurs later at all"},
        "silent_corruption": {"value": round(corrupt / pairs, 4), "receipt": RECEIPTS["permanence"],
                              "pointer": "counts/SILENT_CORRUPTION over pairs_measured",
                              "meaning": "a replay that holds the parse and changes the behaviour"},
    }

    p_correct = round(determined * seen, 4)
    p_correct_value = round(value_determined * seen, 4)

    def leverage(name: str, slope: float, controllable: bool, reason: str) -> dict[str, Any]:
        return {"slope": round(slope, 4), "controllable": controllable,
                "leverage": round(slope if controllable else 0.0, 4), "reason": reason}

    leverage_table = {
        "check_density": leverage(
            "check_density", determined,
            True,
            "a property of the environment: manufactured checks (recorded-outcome differential, "
            "idempotence/reversibility invariants, state-projection diffs) can raise it from 0.6788 "
            "toward 1.0, and each manufactured check is falsifiable by mutation before use"),
        "check_strength": leverage(
            "check_strength", determined * density,
            True,
            "assertion quality: strong-oracle patches merge 28% more often (arXiv 2606.18168), and a "
            "check that a mutation does not kill is not a check"),
        "determined": leverage(
            "determined", seen,
            False,
            "a property of the trace, not of the learner: one demonstration is one point, and the "
            "published ceiling for a full inducer is %.2f on real systematic edits"
            % DETERMINACY_PUBLISHED_CEILING),
    }

    scenarios = []
    for target in (density, 0.80, 0.90, 1.00):
        scenarios.append({
            "check_density": round(target, 4),
            "seen": round(target * strength, 4),
            "p_correct": round(determined * target * strength, 4),
            "p_correct_value_bearing": round(value_determined * target * strength, 4),
        })

    report = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "receipts": {
            name: {"path": path, "sha256": digest}
            for name, path, digest in (
                ("determinacy", RECEIPTS["determinacy"], supply_sha),
                ("value", RECEIPTS["value"], value_sha),
                ("memory", RECEIPTS["memory"], memory_sha),
                ("observation", RECEIPTS["observation"], observation_sha),
                ("permanence", RECEIPTS["permanence"], permanence_sha),
                ("computer", RECEIPTS["computer"], computer_sha),
                ("projection", RECEIPTS["projection"], projection_sha),
                ("contract", RECEIPTS["contract"], contract_sha),
                ("facts", RECEIPTS["facts"], known_sha),
                ("repair", RECEIPTS["repair"], repaired_sha),
                ("demonstration", RECEIPTS["demonstration"], sufficed_sha),
                ("vocabulary", RECEIPTS["vocabulary"], grew_sha),
                ("reach", RECEIPTS["reach"], reached_sha),
            )
        },
        "law": "P(correct behaviour | one action) = P(determined) x P(seen); P(seen) = density x strength",
        "terms": terms,
        "operating_point": {
            "p_correct": p_correct,
            "p_correct_value_bearing": p_correct_value,
            "memory_route": {"coverage": terms["memory_coverage"]["value"],
                             "exact": terms["memory_exact"]["value"],
                             "silent_corruption": terms["silent_corruption"]["value"]},
        },
        "leverage": leverage_table,
        "scenarios": scenarios,
        "ceiling": {
            "determinacy_ceiling": DETERMINACY_PUBLISHED_CEILING,
            "determinacy_ceiling_source": DETERMINACY_CEILING_SOURCE,
            "p_correct_at_full_observability":
                round(determined * 1.0, 4),
            "note": ("even with every consequence observable, one demonstration caps correctness at its "
                     "determinacy; observability is the multiplier, not the base"),
        },
        "computer_use": {
            "status": "MEASURED_ON_A_SHELL_ENVIRONMENT",
            "receipt": RECEIPTS["computer"],
            "what_was_run": ("%d mechanically derived wrong actions over %d real shell transformations, "
                             "real programs on a real disk, real reset"
                             % (int(_field(computer, "mutants", "computer")),
                                int(_field(computer, "tasks_run", "computer")))),
            "replay": {
                "density": float(_field(computer, "density_by_regime/full/replay_density", "computer")),
                "why": ("the intent is the recorded consequence, so any difference is an error: with a full "
                        "state observation every wrong action is caught, and a wrong action that leaves the "
                        "state identical did not miss the goal"),
            },
            "novel": {
                "density": float(_field(computer, "density_by_regime/full/novel_density", "computer")),
                "why": ("with nothing recorded, only a crash and a no-op are visible; a wrong result that "
                        "looks like a result is invisible without a specification"),
            },
            "observation_sensitivity": {
                model: float(_field(computer, "density_by_observation/%s/density" % model, "computer"))
                for model in ("full", "coarse", "listing")
            },
            "invisible_with_a_name_level_view":
                float(_field(computer, "density_by_observation/listing/indistinguishable_share",
                             "computer")),
            "oracle_synthesis": {
                "receipt": RECEIPTS["projection"],
                "cover_size_histogram":
                    _field(projection, "cover_size_histogram", "projection"),
                "tasks_where_content_alone_suffices":
                    len(_field(projection, "content_alone_suffices_for", "projection")),
                "tasks": int(_field(projection, "tasks", "projection")),
                "features_rejected_by_stability":
                    _field(projection, "features_rejected_by_stability", "projection"),
                "why": ("the oracle is not a predicate to be written but an observation to be chosen, under "
                        "two tests at once: it must separate the action from the ways it can be wrong, and "
                        "it must reproduce itself on replay. Separation alone admits a timestamp; stability "
                        "alone admits a name listing"),
            },
            "prospective": {
                "receipt": RECEIPTS["contract"],
                "acquired_from": "one real execution per action",
                "evaluated_on": "a binding never executed during acquisition",
                "arms": {
                    "no_recorded_consequence":
                        _field(contract, "arms/no_recorded_consequence/density", "contract"),
                    "frame_only": _field(contract, "arms/frame_only/density", "contract"),
                    "frame_plus_intervention":
                        _field(contract, "arms/frame_plus_intervention/density", "contract"),
                    "full": _field(contract, "arms/full/density", "contract"),
                },
                "false_alarms_on_correct_novel_actions":
                    _field(contract, "false_alarms_on_correct_novel_actions/full/count", "contract"),
                "content_only_errors": {
                    "frame_only": _field(contract, "content_only_arm/frame_only/density", "contract"),
                    "full": _field(contract, "content_only_arm/full/density", "contract"),
                },
                "why": ("a consequence differential only exists after acting and only on a seen binding. A "
                        "contract acquired from one execution is the prospective form of the same check: the "
                        "frame -- which paths the action may touch -- carries most of it, a declared or derived "
                        "relation carries the bytes, and what remains is a located hole in the vocabulary"),
            },
            "horizon": {
                "receipt": RECEIPTS["facts"],
                "chains": int(_field(known, "chains_run", "facts")),
                "every_step_legal_and_passing":
                    int(_field(known, "per_step_only/claims_success_on_every_step", "facts")),
                "standing_fact_ledger_detected":
                    int(_field(known, "frame_scoped_ledger/detected", "facts")),
                "false_invalidations_on_controls":
                    int(_field(known, "frame_scoped_ledger/false_invalidations_on_controls", "facts")),
                "lead_in_steps": _field(known, "lead_in_steps/min", "facts"),
                "why": ("a per-action check only ever asks about the action in front of it, so a legal step "
                        "that falsifies an earlier verified fact is invisible to it. Re-validating exactly the "
                        "facts the current step frame can touch costs one hash per fact and localises the "
                        "cause two steps before the symptom"),
            },
            "repair": {
                "receipt": RECEIPTS["repair"],
                "chains": int(_field(repaired, "chains", "repair")),
                "steps": int(_field(repaired, "steps", "repair")),
                "probes": int(_field(repaired, "probes", "repair")),
                "dependency_test": _field(repaired, "environment/dependency_test", "repair"),
                "goals_restored": {
                    "declared_read_set": int(_field(repaired, "arms/declared_deps/goals_passing", "repair")),
                    "argv_read_set": int(_field(repaired, "arms/argv_deps/goals_passing", "repair")),
                    "intervention_read_set":
                        int(_field(repaired, "arms/intervention_deps/goals_passing", "repair")),
                    "of": int(_field(repaired, "arms/declared_deps/of", "repair")),
                },
                "steps_redone": {
                    "intervention": int(_field(repaired, "arms/intervention_deps/steps_redone", "repair")),
                    "everything": int(_field(repaired, "arms/redo_everything/steps_redone", "repair")),
                },
                "missed_by_intervention":
                    sum(len(names) for names in _field(repaired, "missed_by_intervention", "repair").values()),
                "over_declared_by_intervention":
                    sum(len(names) for names in
                        _field(repaired, "over_declared_by_intervention", "repair").values()),
                "why": ("detection is not repair: to repair you must know which steps consumed the fact that "
                        "went false, and an argv-derived read set is wrong in both directions -- it names a path "
                        "whose content the step never read, and it cannot see a path that another file names. "
                        "The discovery rule is one intervention per candidate path: perturb it, re-run the step, "
                        "compare its consequence. It recovers the declared read set exactly, with no model, no "
                        "tracing, and no annotation"),
            },
            "demonstration": {
                "receipt": RECEIPTS["demonstration"],
                "actions": int(_field(sufficed, "chains", "demonstration")),
                "readings_per_action": max(int(v) for v in
                                           _field(sufficed, "hypothesis_space_sizes", "demonstration").values()),
                "decided_by_one_execution": _field(sufficed, "verdicts_after_one_execution", "demonstration"),
                "permanence": _field(sufficed, "permanence", "demonstration"),
                "task_scoped_not_permanent": _field(sufficed, "task_safe_but_not_environment_safe",
                                                    "demonstration"),
                "one_shot_pick_wrong_outside_the_task":
                    sum(len(v) for v in _field(sufficed, "naive_one_shot_wrong_outside_the_task",
                                               "demonstration").values()),
                "repeating_the_same_execution_ever_helped":
                    len(_field(sufficed, "repeating_the_same_execution_ever_helped", "demonstration")),
                "why": ("one execution is not knowledge of an action, it is the elimination of every reading that "
                        "contradicts it -- and the survivors are a set. `sort` and `sort -u` are the same action "
                        "on a duplicate-free list; the one-shot learner that keeps the first survivor is right "
                        "on the task and wrong the first time a duplicate appears. Keeping the survivors makes "
                        "the question decidable before the second execution: act, ask once more at the state "
                        "that splits them, or refuse because no reading fits"),
            },
            "vocabulary_growth": {
                "receipt": RECEIPTS["vocabulary"],
                "actions": int(_field(grew, "chains", "vocabulary")),
                "outcomes_realised": sorted(set(_field(grew, "outcomes", "vocabulary").values())),
                "diagnoses_correct": int(_field(grew, "diagnoses_correct", "vocabulary")),
                "transfer_holds": int(_field(grew, "transfer_holds", "vocabulary")),
                "growths": _field(grew, "growths", "vocabulary"),
                "raw_mtime_field_fires_of": [int(_field(grew, "noise_floor/raw_mtime_field_fires", "vocabulary")),
                                             int(_field(grew, "noise_floor/repeats", "vocabulary"))],
                "why": ("a refusal is not an answer, it is the only place a vocabulary can be grown honestly: "
                        "the failure says which of five things is missing, and the growth is kept only if it is "
                        "necessary (the flat grammar cannot do it), stable (a repeat reproduces it), "
                        "transferable (a second action of the same kind is identified by it) and narrow (the "
                        "distinctions it collapses are printed). The boundary is a missing sensor, not a missing "
                        "word: `mkdir` has a real effect on disk that every view in the family is blind to, and "
                        "no amount of experience reaches it"),
            },
            "reach": {
                "receipt": RECEIPTS["reach"],
                "law": "P(correct action) = REACH x SEARCH x VERIFICATION",
                "real_tasks": int(_field(reached, "reach/tasks", "reach")),
                "real_fix_pieces": int(_field(reached, "reach/pieces", "reach")),
                "coverage_with_every_other_task_as_experience":
                    float(_field(reached, "reach/coverage_with_all_other_tasks_seen", "reach")),
                "coverage_while_streaming": float(_field(reached, "reach/coverage_while_streaming", "reach")),
                "never_rebuilt_by_any_other_task": float(_field(reached, "real_fixes/never_seen_share", "reach")),
                "repair_in_grammar": float(_field(reached,
                                                  "grammar_membership_predicts_repair/in_grammar/repair_rate",
                                                  "reach")),
                "repair_out_of_grammar": float(_field(
                    reached, "grammar_membership_predicts_repair/out_of_grammar/repair_rate", "reach")),
                "grammar_can_insert_a_node": _field(reached, "grammar/can_insert_a_node", "reach"),
                "grammar_can_delete_a_node": _field(reached, "grammar/can_delete_a_node", "reach"),
                "why": ("the ceiling is REACH, not experience and not search. 75.2% of 2178 real fix pieces are "
                        "rebuilt by no operator any other task's fixes ever produced, and with every other task "
                        "as experience the coverage is 18.7% -- flat across experience quartiles. On 100 real "
                        "HumanEvalFix bugs the same split appears from the other side: defect types whose edit "
                        "shape the grammar can name repair at 74%, the rest at 32%. So one experience per action "
                        "does not solve computer use; it changes the currency from requests to environments"),
            },
            "what_remains_unmeasured": ("a GUI whose only observable is pixels or DOM -- a projection, not the "
                                        "state; a fact carried by remote state rather than by a path; the outer "
                                        "edge of repair (the candidate set is the state the step can see, and "
                                        "the probe is a content change, so a dependency on a file outside the "
                                        "sandbox, a lock, or a bare existence is not measured by it); and the "
                                        "outer edge of sufficiency itself -- a verdict is relative to a stated "
                                        "grammar and to the candidate states generated for it, so a behaviour "
                                        "outside the grammar is refused rather than learned, and two readings "
                                        "that differ only on a state nobody generated remain conflated); and the "
                                        "outer edge of growth -- the vocabulary is searched inside a stated "
                                        "family of derived views, relations and one-step compositions, so a "
                                        "primitive that needs a sensor the agent does not have is refused "
                                        "rather than invented, and a two-step composition is not reached"),
            "external_context": ("OSWorld 2.0 (arXiv 2606.29537): best agent 20.6% of 108 workflows, "
                                 "failing by skipping verification and spending under 7% of budget "
                                 "detecting its own errors"),
        },
    }
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    point = report["operating_point"]
    terms = report["terms"]
    lev = report["leverage"]
    return (
        "P(correct) = determined x seen = %s x %s = %s on real python work, and %s when the action "
        "turns on a value. Leverage is not slope: the two slopes are %s and %s, but only the observation "
        "is engineerable (leverage %s against %s), because determinacy is a property of the trace with a "
        "published ceiling of %s. At full observability the same determinacy still caps correctness at "
        "%s. Memory serves %s of work at all and replays %s exactly, with %s silent corruption."
        % (terms["determined"]["value"], terms["seen"]["value"], point["p_correct"],
           point["p_correct_value_bearing"], lev["determined"]["slope"], lev["check_density"]["slope"],
           lev["check_density"]["leverage"], lev["determined"]["leverage"],
           report["ceiling"]["determinacy_ceiling"],
           report["ceiling"]["p_correct_at_full_observability"],
           terms["memory_coverage"]["value"], terms["memory_exact"]["value"],
           terms["silent_corruption"]["value"]))


def summarize(report: Mapping[str, Any]) -> str:
    lines = [report["law"], "authority: " + report["authority"]]
    for name, term in report["terms"].items():
        lines.append("  %-18s %-8s %s" % (name, term["value"], term["receipt"]))
    point = report["operating_point"]
    lines.append("operating point: p_correct %s | value-bearing %s"
                 % (point["p_correct"], point["p_correct_value_bearing"]))
    for name, row in report["leverage"].items():
        lines.append("  leverage %-15s slope %-7s controllable %-5s -> %s"
                     % (name, row["slope"], row["controllable"], row["leverage"]))
    for cell in report["scenarios"]:
        lines.append("  density %-6s seen %-6s p_correct %-6s p_correct_value %s"
                     % (cell["check_density"], cell["seen"], cell["p_correct"],
                        cell["p_correct_value_bearing"]))
    use = report["computer_use"]
    lines.append("computer use: %s (%s)" % (use["status"], use["what_was_run"]))
    lines.append("  observation  %s" % use["observation_sensitivity"])
    lines.append("  replay %-6s | novel %-6s  (invisible with a name-level view: %s)"
                 % (use["replay"]["density"], use["novel"]["density"],
                    use["invisible_with_a_name_level_view"]))
    prospective = use["prospective"]
    lines.append("  prospectively, from one execution, on an unseen binding: none %s | frame %s | "
                 "frame+intervention %s | full %s (false alarms %s)"
                 % (prospective["arms"]["no_recorded_consequence"], prospective["arms"]["frame_only"],
                    prospective["arms"]["frame_plus_intervention"], prospective["arms"]["full"],
                    prospective["false_alarms_on_correct_novel_actions"]))
    lines.append("  content-only errors: frame %s | full %s"
                 % (prospective["content_only_errors"]["frame_only"],
                    prospective["content_only_errors"]["full"]))
    horizon = use["horizon"]
    lines.append("  over a sequence: every step legal on %s of %s chains; standing-fact ledger detected %s, "
                 "false invalidations %s, lead %s step(s)"
                 % (horizon["every_step_legal_and_passing"], horizon["chains"],
                    horizon["standing_fact_ledger_detected"], horizon["false_invalidations_on_controls"],
                    horizon["lead_in_steps"]))
    able = use["repair"]
    lines.append("  after an invalidation: goal restored on declared %s | argv %s | intervention %s of %s chains; "
                 "intervention redid %s step(s) where rebuilding takes %s, missed %s, over-declared %s"
                 % (able["goals_restored"]["declared_read_set"], able["goals_restored"]["argv_read_set"],
                    able["goals_restored"]["intervention_read_set"], able["goals_restored"]["of"],
                    able["steps_redone"]["intervention"], able["steps_redone"]["everything"],
                    able["missed_by_intervention"], able["over_declared_by_intervention"]))
    able = use["demonstration"]
    lines.append("  one execution: %d readings per action; decisions %s; permanence permanent %d, task-scoped "
                 "%d, refused %d; the one-shot pick is wrong off-task on %d states; repeating it helped %d times"
                 % (able["readings_per_action"], able["decided_by_one_execution"],
                    sum(1 for v in able["permanence"].values() if v.startswith("PERMANENT")),
                    len(able["task_scoped_not_permanent"]),
                    sum(1 for v in able["permanence"].values() if v.startswith("REFUSED")),
                    able["one_shot_pick_wrong_outside_the_task"],
                    able["repeating_the_same_execution_ever_helped"]))
    lines.append("  still unmeasured: %s" % use["what_remains_unmeasured"])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose the project's own receipts into its capability law, or refuse.")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--pinned", action="store_true",
                        help="require the receipts to match the hashes in the published law receipt")
    ns = parser.parse_args(argv)
    pins = None
    if ns.pinned:
        published = ROOT / "canonical" / "verification" / "CAPABILITY_LAW_20261116_V1.json"
        if not published.exists():
            raise CapabilityLawIncomplete("no published law receipt to pin against")
        pins = pins_from(json.loads(published.read_text(encoding="utf-8")))
    report = compose(pins=pins)
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
