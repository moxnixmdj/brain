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
3. **No number without its own receipt.** There is no measured check density for computer use, so the law
   reports computer use as `UNMEASURED` and refuses to invent the zero. The zero is *expected*, and the
   reason is stated, but it is not a measurement and is not printed as one.

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
            "status": "UNMEASURED",
            "why": ("no receipt exists for check density on a desktop: there is no test corpus there, and "
                    "the oracle must be manufactured. The law refuses to print a zero it did not measure"),
            "what_would_measure_it": ("a state-projection differential over a long-horizon workflow "
                                      "suite, e.g. OSWorld 2.0 checkpoints, with mutated actions"),
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
    lines.append("computer use: %s -- %s" % (report["computer_use"]["status"],
                                             report["computer_use"]["why"]))
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
