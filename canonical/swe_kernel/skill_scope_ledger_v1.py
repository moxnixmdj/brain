#!/usr/bin/env python3
"""A skill's scope is its syntax: the fields that name its class are decorative.

PROBLEM 2, STATED IN THE TREE'S OWN VOCABULARY
----------------------------------------------
The owner's two problems are exact recall (solved) and generalization (not solved). The tree
already contains the first-principles answer to the second, in `canonical/runtime/applicability_v1`:

    "The missing quantity is not more demonstrations. It is the STATE each outcome happened in.
     A success is a point: it shows the plan worked somewhere. A failure in a DIFFERENT state is
     what separates 'always' from 'only when'."
    "A caller may only withhold a plan on IDENTIFIED."

That learner is wired into `macro_v1`, `precondition_discovery_v1` and `contrast_selection_v1`.
It is NOT wired into the skill store. So this module asks the only question that decides whether
the shipped skills generalize, and answers it by running them rather than by reading their prose:

  1. WHAT DECIDES WHERE A RULE APPLIES? Perturb or delete each field the rule declares and see
     whether its behaviour over a probe corpus declared in advance changes at all. A field that can
     be replaced with a class the rule never claimed -- or removed -- without any change is
     DECORATIVE: it is a label on the record, not a constraint on the rule.
  2. WHAT EVIDENCE UNIT DOES THE RECORD CARRY? `verified_hits` is a count. A count has no state, so
     it cannot support a scope claim, however large it grows.
  3. MAY THE SKILL BE CALLED GENERALIZING? Only on `applicability_v1.IDENTIFIED`, which is the
     tree's own law. Anything less is labelled EXACT_MATCH_ONLY -- Problem 1, named as itself.

WHAT THIS MODULE REFUSES TO DO
------------------------------
It never invents a state for a record that does not carry one. It never reports a refusal as a
scope: a rule that fires on nothing is reported as firing on nothing. It never credits an untested
dimension -- the probe corpus is a fixed constant and every row reports which dimensions it covered.
It executes no declared command and writes nothing into the tree it measures.

WHAT IT DOES NOT SAY
--------------------
That the shipped rules are wrong, or that they over-apply in production. Measured: each fires on
exactly one of the eight probes and refuses the other seven, including a near-miss and cross-language
text. The refusals are real. They are produced by the token matcher, not by the declared class --
which is the point, because a refusal that comes from syntax cannot say "this match is outside my
class", only "this text did not match". Narrowness is not a scope.
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_SKILL_SCOPE_LEDGER_V1"
BUNDLE = "canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json"

GENERALIZING = "GENERALIZING__SCOPE_IDENTIFIED"
EXACT_MATCH_ONLY = "EXACT_MATCH_ONLY__SCOPE_NOT_IDENTIFIED"

DECORATIVE = "DECORATIVE__PERTURBING_IT_CHANGES_NO_BEHAVIOUR"
ENFORCING = "ENFORCING__PERTURBING_IT_CHANGES_BEHAVIOUR"

#: Declared before any measurement and never tuned after one. Eight probes: the shape each of the
#: five shipped rules was taught on, one near-miss that differs by a single token, one unrelated
#: source, and the empty source. A corpus this small cannot prove a scope; it can prove which
#: fields constrain behaviour, which is what this ledger claims and nothing more.
PROBE_CORPUS: dict[str, str] = {
    "python_return_add_mul": "def f(x, y):\n    return x + x * y\n",
    "python_return_call_sub": "return f(a, b) - c\n",
    "go_var_map": "var counts map[string]int\n",
    "ts_return_member": "function g(a){ return a.b; }\n",
    "rust_range_len": "for i in 0..=v.len() {\n",
    "near_miss_one_token": "def f(x, y):\n    return x + y * y\n",
    "unrelated_source": "import os\nprint(os.getcwd())\n",
    "empty_source": "",
}

#: Fields a rule record carries that NAME its class rather than spell its match.
CLASS_FIELDS: tuple[str, ...] = ("language", "error_class", "domain", "hole_count",
                                 "skeleton_fp", "skill_id")
#: The two fields that spell the match itself. These are the instrument's positive control: if
#: perturbing these also changed nothing, the sweep would be measuring a broken apply path and
#: every "decorative" verdict would be an artefact.
MATCHER_FIELDS: tuple[str, ...] = ("pattern_tokens", "replacement_tokens")


def firing_signature(rule: Mapping[str, Any], corpus: Mapping[str, str] = PROBE_CORPUS) -> tuple:
    """What the rule does across the whole corpus, as bytes out. None means it refused."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import apply_crystallized_code_rule
    return tuple((name, apply_crystallized_code_rule(text, rule)) for name, text in sorted(corpus.items()))


def perturb(rule: Mapping[str, Any], field: str) -> dict[str, Any]:
    """The same rule with one field made to claim something it never claimed."""
    mutated = copy.deepcopy(dict(rule))
    if field in MATCHER_FIELDS:
        mutated[field] = []                      # destroy the matcher
    elif field == "hole_count":
        mutated[field] = 99                      # a hole count no pattern can satisfy
    elif field in mutated:
        mutated[field] = "ZZ_A_CLASS_THIS_RULE_NEVER_CLAIMED_ZZ"
    return mutated


def field_verdicts(rule: Mapping[str, Any],
                   corpus: Mapping[str, str] = PROBE_CORPUS) -> dict[str, Any]:
    """Which declared fields constrain behaviour, and which are labels.

    Returns the per-field verdict plus `positive_control_held`, which is False when perturbing the
    matcher changed nothing -- in that case the sweep proved nothing and the caller must not report
    any field as decorative.
    """
    base = firing_signature(rule, corpus)
    out: dict[str, Any] = {"fields": {}, "fires_on": [n for n, v in base if v is not None]}
    for field in tuple(rule):
        if field in MATCHER_FIELDS:
            verdict = ENFORCING if firing_signature(perturb(rule, field), corpus) != base else DECORATIVE
        elif field in CLASS_FIELDS:
            verdict = DECORATIVE if firing_signature(perturb(rule, field), corpus) == base else ENFORCING
        else:
            verdict = DECORATIVE if firing_signature(perturb(rule, field), corpus) == base else ENFORCING
        out["fields"][field] = verdict
    out["positive_control_held"] = all(
        out["fields"].get(f) == ENFORCING for f in MATCHER_FIELDS if f in rule)
    return out


def evidence_pairs(record: Mapping[str, Any]) -> tuple[list[tuple[frozenset[str], bool]], str]:
    """The (state, succeeded) pairs a record actually carries -- not the ones it implies.

    `verified_hits` is a count and `provenance` is a list of {at, hits, origin}. Neither names the
    state the success happened in, so neither can enter `applicability_v1.learn`. Returning an empty
    list here is the honest answer; inventing a state from the rule's own `language` field would let
    a record scope itself, which is exactly the circularity this ledger exists to refuse.
    """
    hits = record.get("verified_hits")
    prov = record.get("provenance") or []
    if not isinstance(hits, int) or hits <= 0:
        return [], "NO_SUCCESS_RECORDED"
    # A provenance entry is usable only if it names the state it happened in. An entry that says
    # merely "it failed" is as unusable as a bare count: it cannot separate always from only-when,
    # because only-when is a statement about states.
    usable = [p for p in prov if isinstance(p, Mapping) and p.get("state")]
    # Successes and failures are disjoint. Reading every stateful entry as a success and then
    # appending the failures again puts each failure in the version space twice, as True and as
    # False, and the learner then reports INCONSISTENT for evidence that identifies cleanly.
    successes = [p for p in usable if p.get("succeeded") is not False]
    failures = [p for p in usable if p.get("succeeded") is False]
    if not usable:
        return [], "A_COUNT_IS_NOT_A_STATE__SUCCESSES_RECORDED_WITHOUT_THE_STATE_THEY_HAPPENED_IN"
    pairs = [(frozenset(p["state"]), True) for p in successes]
    pairs += [(frozenset(p["state"]), False) for p in failures]
    return pairs, "EVIDENCE_CARRIES_STATES"


def scope_of(rule: Mapping[str, Any], record: Mapping[str, Any],
             corpus: Mapping[str, str] = PROBE_CORPUS) -> dict[str, Any]:
    """One skill's scope: what constrains it, what evidence it rests on, and what it may be called."""
    from canonical.runtime import applicability_v1 as app

    pairs, unit = evidence_pairs(record)
    boundary = app.learn(pairs)
    fields = field_verdicts(rule, corpus)
    label = GENERALIZING if boundary.identified else EXACT_MATCH_ONLY
    return {
        "skill_id": record.get("skill_id"),
        "declared_class": {k: record.get(k) for k in ("language", "error_class", "domain")},
        "label": label,
        "boundary_status": boundary.status,
        "boundary_reason": boundary.reason,
        "required": list(boundary.required) if boundary.required else None,
        "survivor_count": boundary.survivor_count,
        "evidence_unit": unit,
        "successes_recorded": record.get("verified_hits"),
        "usable_evidence_pairs": len(pairs),
        "contrasting_failures_recorded": sum(1 for p in (record.get("provenance") or [])
                                             if isinstance(p, Mapping) and p.get("succeeded") is False),
        "fires_on": fields["fires_on"],
        "probes_run": len(corpus),
        "decorative_fields": sorted(f for f, v in fields["fields"].items() if v == DECORATIVE),
        "enforcing_fields": sorted(f for f, v in fields["fields"].items() if v == ENFORCING),
        "positive_control_held": fields["positive_control_held"],
    }


def price_next_probe(pairs: Sequence[tuple[Iterable[str], bool]],
                     candidate_states: Sequence[Iterable[str]]) -> dict[str, Any]:
    """The cheapest observation that would split what is left, priced in bits.

    Only meaningful once evidence exists: with no survivors there is nothing to split, and saying so
    is the answer. Uses the tree's own `VersionSpace.select_probe`, so there is one notion of
    information gain in the repository rather than a second one invented here.
    """
    from canonical.runtime import applicability_v1 as app
    from canonical.runtime.settlement_v1 import VersionSpace

    boundary = app.learn(pairs)
    if not boundary.survivors:
        return {"priced": False, "probe": None, "gain_bits": 0.0,
                "reason": "NO_SURVIVORS_TO_SPLIT__" + boundary.reason}
    space = VersionSpace([app.conjunction(s) for s in boundary.survivors])
    for state, ok in pairs:
        space.observe((frozenset(state),), ok)
    probes = [(frozenset(s),) for s in candidate_states]
    best, gain = space.select_probe(probes)
    if best is None:
        return {"priced": False, "probe": None, "gain_bits": float(gain),
                "reason": "NO_CANDIDATE_STATE_SPLITS_THE_SURVIVORS"}
    return {"priced": True, "probe": sorted(best[0]), "gain_bits": float(gain),
            "reason": "CHEAPEST_SPLITTING_OBSERVATION"}


def ledger(root: pathlib.Path = ROOT) -> dict[str, Any]:
    """Every skill the tree ships, scoped by running it. Reads one JSON file; writes nothing."""
    path = root / BUNDLE
    if not path.is_file():
        return {"schema": SCHEMA, "root": str(root), "skills": [], "summary": {},
                "error": "BUNDLE_ABSENT:" + BUNDLE}
    doc = json.loads(path.read_text(encoding="utf-8"))
    records = doc.get("rules") or []
    skills = []
    for record in records:
        rule = record.get("rule") or {}
        if not rule:
            skills.append({"skill_id": record.get("skill_id"), "label": EXACT_MATCH_ONLY,
                           "boundary_status": "UNDETERMINED__NO_CONTRASTING_OUTCOME",
                           "boundary_reason": "NO_RULE_TO_RUN", "evidence_unit": "NO_RULE",
                           "positive_control_held": False})
            continue
        skills.append(scope_of(rule, record))

    controlled = [s for s in skills if s.get("positive_control_held")]
    summary = {
        "skills_measured": len(skills),
        "labelled_generalizing": sum(1 for s in skills if s.get("label") == GENERALIZING),
        "labelled_exact_match_only": sum(1 for s in skills if s.get("label") == EXACT_MATCH_ONLY),
        "scope_identified": sum(1 for s in skills
                                if s.get("boundary_status", "").startswith("IDENTIFIED")),
        "evidence_is_a_count_without_states": sum(
            1 for s in skills if s.get("evidence_unit", "").startswith("A_COUNT_IS_NOT_A_STATE")),
        "contrasting_failures_recorded": sum(
            int(s.get("contrasting_failures_recorded") or 0) for s in skills),
        "fields_decorative_on_every_measured_skill": sorted(
            set.intersection(*[set(s["decorative_fields"]) for s in controlled]) if controlled else set()),
        "fields_enforcing_on_every_measured_skill": sorted(
            set.intersection(*[set(s["enforcing_fields"]) for s in controlled]) if controlled else set()),
        "positive_control_held_on_all": bool(controlled) and len(controlled) == len(skills),
        "probes_in_corpus": len(PROBE_CORPUS),
    }
    return {"schema": SCHEMA, "root": str(root), "authority": "NONE__SANDBOX_MEASUREMENT",
            "what_this_decides": ("WHICH_DECLARED_FIELDS_CONSTRAIN_WHERE_A_SKILL_APPLIES_AND_WHETHER_ANY_"
                                  "SKILL_MAY_BE_CALLED_GENERALIZING_UNDER_THE_TREE_S_OWN_LAW"),
            "declares_nothing_about": ("WHETHER_A_REPAIR_IS_CORRECT__NO_TEST_WAS_RUN_AND_NO_PROJECT_SEMANTICS_"
                                       "WERE_CONSULTED__A_REFUSAL_MEANS_THE_TOKENS_DID_NOT_MATCH_NOTHING_MORE"),
            "probe_corpus": PROBE_CORPUS, "skills": skills, "summary": summary}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true", help="emit the whole ledger as JSON to stdout")
    args = ap.parse_args(argv)
    doc = ledger(pathlib.Path(args.root))
    if args.json:
        print(json.dumps(doc, indent=1, sort_keys=True))
        return 0
    s = doc.get("summary") or {}
    print("skill scope ledger: what decides where a learned skill applies\n")
    print(f"  skills measured                    {s.get('skills_measured')}")
    print(f"  may be called GENERALIZING         {s.get('labelled_generalizing')}")
    print(f"  labelled EXACT_MATCH_ONLY          {s.get('labelled_exact_match_only')}")
    print(f"  evidence is a count, not a state   {s.get('evidence_is_a_count_without_states')}")
    print(f"  contrasting failures recorded      {s.get('contrasting_failures_recorded')}")
    print(f"  positive control held on all       {s.get('positive_control_held_on_all')}")
    print(f"\n  decorative on every skill: {', '.join(s.get('fields_decorative_on_every_measured_skill') or []) or '-'}")
    print(f"  enforcing  on every skill: {', '.join(s.get('fields_enforcing_on_every_measured_skill') or []) or '-'}")
    for skill in doc.get("skills") or []:
        print(f"\n  {skill.get('skill_id')}: {skill.get('label')}")
        print(f"     boundary {skill.get('boundary_status')} ({skill.get('boundary_reason')})")
        print(f"     fires on {skill.get('fires_on')} of {skill.get('probes_run')} probes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
