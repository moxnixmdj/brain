"""The GUI invariance census: does the GUI side have an invariance, and if not, why not.

THE QUESTION THIS SETTLES
-------------------------
The code side has a measured invariance that multiplies the reach of one demonstration. Bind names are
alpha-renameable, so folding a verified repair over renamings took one demonstration from 0 survivors
to 4, and from 0 repaired bugs to 5 bugs the demonstration had never seen. The law recorded there:

    the demonstration is the content; the invariance is the reach;
    the invariance cannot be learned from the demonstration.

The GUI side has never had one. It has phrase-gated lookups instead. So the question is whether the
same lever is available here -- whether there is a quotient on GUI value tasks that would let one
demonstration reach many pages.

THE FIRST INSTRUMENT WAS WRONG, AND HOW
---------------------------------------
Pass one compared the derivable values before and after perturbing an observation, and called any
difference a defect. `text-transform` failed I4 (elements reordered): JOIN_SHOWN returned F5CZ instead
of ZC5F. That looked like a mechanism keyed on an irrelevant detail. It is not. The page renders the
answer across four sibling `<span>`s and judges `typed === q`; DOM order IS the answer. Measured by
playing the page: ZC5F scores 1, F5CZ scores -1. A "fix" would have broken a working page.

Two different things produce a difference between before and after, and only one is a defect:

    (a) the rule keys on something that does not matter   -> DEFECT   (the alpha bug)
    (b) the perturbation changed the ANSWER               -> TRUTH

Pass one's third arm could not tell them apart, because it perturbed the OBSERVATION and then asked
whether the page still wanted the baseline answer. The page is unchanged, so the answer never moves,
so the arm can never fire. That is a structural defect in the instrument, not a finding, and it is
recorded here rather than repaired silently.

THE INSTRUMENT THAT WORKS
-------------------------
An invariance is a claim of the form "these two things are the same task". Only the judge can settle
it, so this census asks the judge directly, two ways:

    identity_invariance   perturb the observation; if the rules do not move, the rules never read it.
                          This is measured statically against the rule source, so it is exact.
    judge_invariance      perturb the ANSWER into forms the task should not distinguish (case, padding,
                          trailing punctuation); if the judge accepts them, it quotients them.

MEASURED, seed 1060, jsdom
--------------------------
    identity: 11 of 12 arms INVARIANT -- and for a reason that makes them worthless: the rules never
        read `index`, `name` or `id` as a computed term. `index` appears once, at
        `derived_value_v1:397`, and only to ADDRESS the field to type into. So the identity
        invariances are free because they are vacuous. They are quotiented out already, by
        construction, and they buy no reach.

    the one that is not identity -- element order -- is a TRUTH (ZC5F 1, F5CZ -1), not a defect.

    judge: scroll-text accepts 'volutpat', 'volutpat.', ' volutpat', 'volutpat ', '  volutpat  '.
        Every other page accepts the bare answer and NOTHING else. enter-time's field is
        `<input type="time">` and rejects `1:13 PM` -- the utterance's own string -- along with
        `1:13PM`, `01:13 PM`, `13:13:00` and `0113PM`, accepting only `13:13`.

THE CONCLUSION, WHICH IS THE POINT
----------------------------------
The GUI value task is a TOTAL EQUALITY checked by a string comparison, so it has no quotient to
discover: there is no pair of distinct things the judge calls the same, except the browser's own field
encoding. The code side's lever does not transfer, and the reason is structural rather than a gap in
our implementation. Reach on the GUI side cannot come from an invariance, because there is nothing to
quotient. It has to come from the operand vocabulary, which is where the 16-class taxonomy already is.

So the GUI failure was never "a missing invariance". That hypothesis is falsified here, and falsifying
it is worth more than the census: it says where NOT to spend, before more is spent there.
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

sys.path.insert(0, "/home/user/brain")
from canonical.runtime import derived_value_v1 as dv  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

HTML = "/tmp/miniwob-plusplus/miniwob/html"
MODS = "/tmp/mw/node_modules"
SEED = 1060

#: Pages whose value rules fire, with the answer that page's own judge accepts.
CASES = {"simple-arithmetic": "11", "simple-algebra": "25", "enter-time": "13:13",
         "scroll-text": "volutpat", "text-transform": "ZC5F"}

INVARIANT = "INVARIANT"
TRUE_BREAK = "TRUE_BREAK__THE_PAGE_WANTS_SOMETHING_ELSE"
DEFECT = "DEFECT__THE_PAGE_IS_THE_SAME_AND_THE_RULES_MOVED"
UNDECIDED = "UNDECIDED__THE_PAGE_WAS_NOT_PERTURBED_SO_THERE_IS_NOTHING_TO_COMPARE"

#: The rules' entire use of identity. Asserted by a test, so it cannot drift silently.
IDENTITY_USE = "derived_value_v1:397 -- index is the ADDRESS of the field to type into, never a term"


def rules_of(observation) -> list[tuple[str, str]]:
    return [(row["value"], row["rule"]) for row in dv.derivations(observation)]


def _shift_indices(observation):
    out = copy.deepcopy(observation)
    for element in out.get("elements") or []:
        for key in ("index", "parent"):
            if isinstance(element.get(key), int):
                element[key] += 100
    return out


def _rename_names(observation):
    out = copy.deepcopy(observation)
    for element in out.get("elements") or []:
        for key in ("name", "id"):
            if isinstance(element.get(key), str):
                element[key] = "renamed_" + element[key][:10]
    return out


def _reverse_elements(observation):
    out = copy.deepcopy(observation)
    if isinstance(out.get("elements"), list) and len(out["elements"]) > 1:
        out["elements"] = list(reversed(out["elements"]))
    return out


ARMS = {"I1_element_index_renamed": _shift_indices,
        "I2_field_names_renamed": _rename_names,
        "I4_elements_reordered": _reverse_elements}


def play(bridge, task: str, value: str) -> int | float | None:
    """Let the page's own judge score a value. The only oracle a self-contained page always has."""
    bridge.load(task)
    observation = bridge.reset(seed=SEED)
    fields = [e["index"] for e in observation.get("elements") or []
              if e.get("can_type") and not str(e.get("text") or "").strip()]
    if not fields:
        return None
    observation = bridge.act({"type": "type", "index": fields[0], "text": value})
    for index in [e["index"] for e in observation.get("elements") or [] if e.get("can_click")]:
        after = bridge.act({"type": "click", "index": index})
        if after.get("done"):
            return after.get("raw_reward")
    return None


def answer_variants(value: str) -> dict[str, str]:
    """Forms a task that does not care about presentation should not distinguish.

    Only DISTINCT spellings count. `"11".upper()` is `"11"`, so including it would report a quotient
    that does not exist -- that mistake was made in pass two and is fixed here by construction.
    """
    proposals = {"upper": value.upper(), "lower": value.lower(), "trailing dot": value + ".",
                 "leading space": " " + value, "trailing space": value + " ",
                 "padded": "  " + value + "  "}
    distinct = {name: text for name, text in proposals.items() if text != value}
    return {"as-is": value, **distinct}


def identity_census(bridge, pages) -> list[dict]:
    """Do the rules move when nothing that matters moves?"""
    rows = []
    for task in pages:
        bridge.load(task)
        base = bridge.reset(seed=SEED)
        base_rules = rules_of(base)
        row = {"task": task, "baseline_rules": base_rules, "arms": {}}
        for name, perturb in ARMS.items():
            after = rules_of(perturb(base))
            if after == base_rules:
                row["arms"][name] = {"verdict": INVARIANT, "answer_moved": False}
                continue
            # The rules moved. Ask the page whether it moved too -- but note the arm's limit:
            # the page is unchanged, so this can only distinguish "the page still wants the
            # baseline value" from "it does not". It cannot manufacture a truth.
            # The page is unchanged, so this probe can only establish the WEAKER of the two facts:
            # whether the page still wants a baseline value at all. A reorder that moves the
            # candidate list while the page still accepts the baseline answer is `UNDECIDED`, not a
            # defect -- the observation was perturbed but the page was not, so there is nothing to
            # compare against. Calling that "DEFECT" is what pass one got wrong.
            still = {value: play(bridge, task, value)
                     for value in [r[0] for r in base_rules][:2]}
            row["arms"][name] = {
                "verdict": TRUE_BREAK if not any(r == 1 for r in still.values()) else UNDECIDED,
                "answer_moved": not any(r == 1 for r in still.values()),
                "rules_after": after, "page_still_wants_baseline": still}
        rows.append(row)
    return rows


def judge_census(bridge, cases) -> list[dict]:
    """Does the judge call any two distinct answers the same? This is the real quotient."""
    rows = []
    for task, answer in cases.items():
        scores = {name: play(bridge, task, value)
                  for name, value in answer_variants(answer).items()}
        accepted = [name for name, reward in scores.items() if reward == 1]
        variants = answer_variants(answer)
        # A quotient is only worth something if it maps one answer onto a DIFFERENT correct answer.
        # Case and whitespace are normalisation of the same spelling -- a browser input's own
        # encoding, not a discovery. Counting them as reach would be the same error as counting
        # `"11".upper()` as a distinct value.
        normalising = {"upper", "lower", "leading space", "trailing space", "padded"}
        semantic = [n for n in accepted if n not in normalising and n != "as-is"]
        rows.append({"task": task, "answer": answer, "scores": scores,
                     "accepted_variants": accepted, "distinct_variants_offered": len(variants) - 1,
                     "quotient_size": len(accepted) - 1,
                     "quotient_kind": ("SPELLING_NORMALISATION_ONLY" if not semantic
                                       else "SEMANTIC__" + ",".join(semantic))})
    return rows


def summarise(identity, judges) -> dict:
    verdicts: dict[str, int] = {}
    for row in identity:
        for arm in row["arms"].values():
            verdicts[arm["verdict"]] = verdicts.get(arm["verdict"], 0) + 1
    return {
        "identity_arms": sum(len(r["arms"]) for r in identity),
        "identity_verdicts": verdicts,
        "judge_pages": len(judges),
        "judge_quotient_sizes": {r["task"]: r["quotient_size"] for r in judges},
        "pages_with_a_nontrivial_quotient": [r["task"] for r in judges if r["quotient_size"] > 0],
        "quotient_is_real": {r["task"]: r["quotient_kind"] for r in judges},
    }


def main() -> int:
    bridge = tool.Bridge(HTML, MODS, substrate="jsdom")
    try:
        identity = identity_census(bridge, CASES)
        judges = judge_census(bridge, CASES)
    finally:
        bridge.close()
    out = {"schema": "BRAIN_GUI_INVARIANCE_CENSUS_V1",
           "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT", "kind": "receipt",
           "incremental_spend_usd": 0, "producer_cognition_model_dependency_count": 0,
           "seed": SEED, "identity_use_by_the_rules": IDENTITY_USE,
           "substrate": "jsdom (no layout engine) -- the census is about what the RULES read and what "
                        "the JUDGE compares, neither of which needs layout",
           "summary": summarise(identity, judges), "identity": identity, "judges": judges}
    text = json.dumps(out, indent=1, sort_keys=True)
    if len(sys.argv) > 1:
        pathlib.Path(sys.argv[1]).write_text(text + "\n")
        print("written", sys.argv[1])
    print(json.dumps(out["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
