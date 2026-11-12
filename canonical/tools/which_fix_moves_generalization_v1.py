#!/usr/bin/env python3
"""Which fix actually makes generalization work, priced on the metric that is scored.

THE OWNER'S PROBLEM 2, TAKEN LITERALLY
--------------------------------------
"Problem 1: exact recall -- solved. Problem 2: generalization -- if I see a SIMILAR task, I can
adapt. NOT SOLVED. Focus on solving problem 2 perfectly with the smartest solutions in the
fastest way."

The tree already has a ranked list of next operators
(`ONE_TRY_COVERS_A_FRACTION_20261112_V1.md` §8: import-only 60 askings, call-shape 50,
block-shape 34, names 22). That list is counted in **askings**, and the tree's own law says what
that is worth:

    A census finds symptoms; only a counterfactual finds causes. A blocker is not the first
    obstacle. It is the obstacle whose removal makes the thing work.

Nobody has run that counterfactual for Problem 2. So this tool does one thing: for every proposed
fix, it removes exactly that refusal, replays the same 440 one-example askings on the same 89
files of other people's code, and reports what the scored quantity actually becomes.

WHAT IS SCORED, AND WHY BOTH
----------------------------
The recorded corpus has two different scoring conventions and quoting one while arguing about the
other is the mistake this tree already caught once:

* **strict** (`repeated_change_one_example_measure_v1.score`): statement-level diff. Recall is
  computed against `developers_changes_not_imports`, so **an import-only change can never score**.
* **marker** (`edits_repeated_across_projects_v1.answers`): per question, where a question is a
  statement of the before-file holding a marker that the person changed one-for-one.

Both are reported for the baseline and for every counterfactual, so a fix that only moves one
cannot be sold as moving "coverage".

HOW A COUNTERFACTUAL IS RUN WITHOUT EDITING THE ORGAN
-----------------------------------------------------
`edit_by_example_v1.rewrite` builds the complete list of places first and raises on unshown uses
before writing anything. So the refusal class is recoverable from the text: catch the organ's
refusal, and if it is the targeted class, re-ask with `leave_unshown=True` (its own documented way
of proceeding past that exact class) and count what it writes. Nothing in the organ changes, no
number is widened, and a fix that is not targeted is reported as "not this class".

WHAT THIS DOES NOT DO
---------------------
It does not edit the learner, register a capability, or claim a fix is safe. `leave_unshown=True`
is the organ's *ceiling*: it changes the uses it was shown and leaves the rest. A real
call-shape operator must additionally check the new callee accepts the call, which costs a
signature resolution the record does not contain. So every number here is an **upper bound on the
gain from that class**, and the price to realise it is stated per class.

    python3 canonical/tools/which_fix_moves_generalization_v1.py --pulls /tmp/pulls_v3.json
    python3 canonical/tools/which_fix_moves_generalization_v1.py --pulls ... --out RECORD.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import signal
import sys
import time
import warnings
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_WHICH_FIX_MOVES_GENERALIZATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
CALL_LIMIT_S = 30

#: The refusal classes the tree's own §8 roadmap proposes to buy, and how each one is recognised in
#: the organ's own sentence. These strings are the organ's words, not a paraphrase of them: if the
#: organ's wording changes, `reason_class` stops matching and the counterfactual reports "not this
#: class" rather than silently counting something else.
CLASSES: dict[str, dict[str, str]] = {
    "IMPORT_ONLY_EXAMPLE": {
        "match": "apart from import lines",
        "what": "the example differs only in import lines; the algebra learns only expression changes",
        "real_price": (
            "an import rewrite operator: apply the same import-line change. Mechanically checkable "
            "(the module resolves). No search, no oracle. This is the cheapest class in the tree."
        ),
    },
    "CALL_SHAPE_NOT_SHOWN": {
        "match": "the examples showed it called with",
        "what": "the callee is shown with a different number of arguments or keywords",
        "real_price": (
            "a pure-rename operator that leaves arguments untouched PLUS a signature check that the "
            "new callee accepts the call. The second half is the risk: without it this is how a "
            "rename silently breaks a call site."
        ),
    },
    "NAME_NOT_AVAILABLE": {
        "match": "which the file does not define, import or receive",
        "what": "the new code reads a name the file does not define, import or receive",
        "real_price": (
            "a bring-from-the-example's-imports rule. Cheap when the example's own file imported the "
            "name; a project-graph operation when it did not."
        ),
    },
    "CONFLICTING_CONTEXT": {
        "match": "was changed, but the same code was left alone",
        "what": "the same code was changed in one place and left alone in another",
        "real_price": (
            "not an operator at all: this is genuinely underdetermined by one showing, and the "
            "document's own answer is a second demonstration chosen to settle it."
        ),
    },
    "BLOCK_SHAPE": {
        "match": "reshapes whole statements",
        "what": "the change adds, removes or reshapes whole statements",
        "real_price": (
            "a new algebra of statement-level edits plus a test oracle. This is the expensive one and "
            "the reason it is ranked last here rather than first."
        ),
    },
    "NO_FORM_IN_FILE": {
        "match": "nothing in the file has the form",
        "what": "the demonstrated change does not occur in this file",
        "real_price": (
            "NOT A FIX. Nothing is missing: the change genuinely does not apply here. Removing this "
            "refusal would be a defect, so it is listed to be ruled out, not bought."
        ),
    },
}


class TookTooLong(Exception):
    pass


def _alarm(signum, frame):
    raise TookTooLong()


def _bounded(ask: Callable[[], Any]) -> Any:
    previous = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(CALL_LIMIT_S)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ask()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def organ_module():
    from canonical.swe_kernel.taught_actions import edit_by_example_v1
    return edit_by_example_v1


def learn_fails(example: Mapping[str, str]) -> str | None:
    """The class of refusal raised while READING THE EXAMPLE, or None when the example can be learned.

    This split is the whole point of the tool. A refusal at apply time says "the operator cannot say
    this yet" and an operator would fix it. A refusal at learn time says "the demonstration itself is
    outside the algebra" -- and then NO apply-time operator can help, because there is no rule to
    apply. The roadmap counted both together, so 60 askings looked like 60 opportunities.
    """
    organ = organ_module()
    try:
        _bounded(lambda: organ.learn(example["before"], example["after"]))
        return None
    except Exception as error:
        return classify("refused: " + str(error))


def classify(why: str | None) -> str:
    """The roadmap class this refusal belongs to, or `EDITED` / `OTHER`."""
    if why is None:
        return "EDITED"
    for name, spec in CLASSES.items():
        if spec["match"] in why:
            return name
    return "OTHER"


# --------------------------------------------------------------------------- #
# the three ways of asking, all of them the organ's own documented behaviour
# --------------------------------------------------------------------------- #
def ask_strict(target: str, before: str, after: str) -> tuple[str | None, str | None]:
    organ = organ_module()
    try:
        return _bounded(lambda: organ.edit_by_example(target, before, after)), None
    except Exception as error:
        return None, "refused: " + str(error)


def ask_past_unshown(target: str, before: str, after: str) -> tuple[str | None, str | None]:
    """The organ's `repeat_shown`: change the uses it was shown, leave the others alone."""
    organ = organ_module()
    try:
        rules = _bounded(lambda: organ.learn(before, after))
        return _bounded(lambda: organ.repeated(rules, target, "the example", leave_unshown=True)), None
    except Exception as error:
        return None, "refused: " + str(error)


def ask_bringing_names(target: str, before: str, after: str) -> tuple[str | None, str | None]:
    """Lifts NAME_NOT_AVAILABLE the way a person actually does it: extend the import that is there.

    The organ refuses when the new code reads a name the target does not define, and it is right to:
    `datetime.now(UTC)` with no `UTC` in scope is broken code. Its own `bring` machinery declines to
    help here, and its comment says why -- a file that already has an import relationship with a
    module declares its own imports, so a line lifted off the example's standing imports is not put
    in. That is a conservative and defensible rule, and it is also exactly the case the people hit:
    their file already said `from datetime import datetime`, and they wrote `UTC` into that line.

    So the counterfactual is small and mechanical: take the line the lesson says it needs
    (`from datetime import UTC`), and if the target already imports from the same module, add the
    missing name to that existing line instead of adding a second import of the same module. Then ask
    the organ again with its normal gate, which will verify the name is now available.

    This is a genuine operator and it is checkable without an oracle: the module must be one the
    file already imports, and the added name must be one that module really exports, or the file
    will not import at all. Nothing here widens a tolerance.
    """
    organ = organ_module()
    try:
        rules = _bounded(lambda: organ.learn(before, after))
    except Exception as error:
        return None, "refused: " + str(error)
    needed: dict[str, str] = {}
    for rule in rules:
        for name, line in (getattr(rule, "bring", {}) or {}).items():
            needed[name] = line
    if not needed:
        return None, "refused: the lesson names nothing it needs imported"

    text = target
    added = []
    for name, line in sorted(needed.items()):
        statement = _bounded(lambda line=line: __import__("ast").parse(line).body[0])
        module = getattr(statement, "module", None)
        if not module:
            continue
        # is there already a line importing from that module?  extend it, as the person did
        pattern = re.compile(r"^(\s*)from\s+%s\s+import\s+([^\n#]+)$" % re.escape(module), re.M)
        found = pattern.search(text)
        if found:
            names = [piece.strip() for piece in found.group(2).split(",")]
            if name not in names:
                text = (text[:found.start(2)] + ", ".join(names + [name])
                        + text[found.end(2):])
                added.append("%s joined the existing `from %s` line" % (name, module))
            continue
        text = line + "\n" + text
        added.append("%s brought as `%s`" % (name, line))
    if not added:
        return None, "refused: no import could be extended"
    try:
        return _bounded(lambda: organ.repeated(rules, text, "the example", leave_unshown=True)), None
    except Exception as error:
        return None, "refused: " + str(error)


ARM_OF: dict[str, Callable[[str, str, str], tuple[str | None, str | None]]] = {
    "IMPORT_ONLY_EXAMPLE": ask_past_unshown,
    "CALL_SHAPE_NOT_SHOWN": ask_past_unshown,
    "CONFLICTING_CONTEXT": ask_past_unshown,
    "NAME_NOT_AVAILABLE": ask_bringing_names,
    "BLOCK_SHAPE": ask_past_unshown,
}


# --------------------------------------------------------------------------- #
# scoring: the recorded strict scorer AND the recorded marker scorer
# --------------------------------------------------------------------------- #
def score_strict(target: Mapping[str, str], got: str | None) -> dict[str, Any]:
    from canonical.tools import repeated_change_one_example_measure_v1 as measure
    return measure.score(target["before"], target["after"], got)


def score_marker(target: Mapping[str, str], got: str | None, marker: str | None) -> dict[str, int]:
    from canonical.tools import edits_repeated_across_projects_v1 as marker_tool
    if not marker:
        return {"questions": 0, "same": 0, "different": 0, "left": 0, "extra": 0}
    return marker_tool.answers(target["before"], target["after"], got, marker)


def markers_for_pulls(pulls: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Map each pull request's search phrase to the marker the recorded kinds carry for it.

    The marker scorer needs to know which statements are the questions. The pull requests were found
    by title phrases, and the recorded kinds table holds the phrase and the code marker together, so
    the marker is read from there rather than guessed. A phrase with no recorded kind gets no marker,
    and its marker columns stay empty rather than being filled with something approximate.
    """
    from canonical.tools import edits_repeated_across_projects_v1 as marker_tool
    by_phrase: dict[str, str] = {}
    for kinds in marker_tool.KINDS.values():
        for _name, words, marker in kinds:
            by_phrase.setdefault(words, marker)
    return {pull["name"]: by_phrase[pull["query"]] for pull in pulls
            if pull.get("query") in by_phrase}


# --------------------------------------------------------------------------- #
# the run
# --------------------------------------------------------------------------- #
def _blank() -> dict[str, Any]:
    return {
        "askings": 0,
        "edited": 0,
        "developers_changes_not_imports": 0,
        "right_not_imports": 0,
        "organ_changes": 0,
        "not_what_the_developers_did": 0,
        "questions": 0,
        "same": 0,
        "different": 0,
        "left": 0,
        "extra": 0,
        "classes": collections.Counter(),
        "learn_time_refusals": 0,
    }


def _add(total: dict[str, Any], one_strict: Mapping[str, Any], one_marker: Mapping[str, int],
         why: str | None) -> None:
    total["askings"] += 1
    total["edited"] += why is None
    for key in ("developers_changes_not_imports", "right_not_imports", "organ_changes",
                "not_what_the_developers_did"):
        total[key] += one_strict[key]
    for key in ("questions", "same", "different", "left", "extra"):
        total[key] += one_marker[key]
    total["classes"][classify(why)] += 1


def _rates(total: Mapping[str, Any]) -> dict[str, Any]:
    out = {key: value for key, value in total.items() if key != "classes"}
    out["classes"] = dict(sorted(total["classes"].items(), key=lambda item: (-item[1], item[0])))
    covered = total["developers_changes_not_imports"]
    organ_changes = total["organ_changes"]
    out["strict_coverage"] = round(total["right_not_imports"] / covered, 4) if covered else None
    out["strict_precision"] = (round(total["right_not_imports"] / organ_changes, 4)
                               if organ_changes else None)
    out["marker_same_share"] = (round(total["same"] / total["questions"], 4)
                                if total["questions"] else None)
    out["share_edited"] = round(total["edited"] / total["askings"], 4) if total["askings"] else None
    return out


def run(pulls: Sequence[Mapping[str, Any]], *, markers: Mapping[str, str] | None = None,
        say: Callable[[str], None] = lambda line: None) -> dict[str, Any]:
    """Baseline, then one counterfactual per class, on the same askings."""
    markers = dict(markers or {})
    baseline = _blank()
    # per class: the askings whose baseline refusal was that class, and what happens if it is lifted
    lifted: dict[str, dict[str, Any]] = {name: _blank() for name in CLASSES}
    per_pull: dict[str, Any] = {}

    for pull in pulls:
        name = pull["name"]
        marker = markers.get(name)
        row = {"baseline": _blank(), "lifted": {key: _blank() for key in CLASSES}}
        for index, example in enumerate(pull["files"]):
            unlearnable = learn_fails(example)
            for other, target in enumerate(pull["files"]):
                if other == index:
                    continue
                got, why = ask_strict(target["before"], example["before"], example["after"])
                strict = score_strict(target, got)
                marker_scores = score_marker(target, got, marker)
                _add(baseline, strict, marker_scores, why)
                _add(row["baseline"], strict, marker_scores, why)
                cls = classify(why)
                if unlearnable is not None:
                    # The example never became a rule, so every asking from it sits in the same
                    # class no matter what the target looks like. Counted apart: an operator for
                    # this class cannot reach these askings at all.
                    budget = lifted.setdefault(cls, _blank())
                    budget["askings"] += 1
                    budget["learn_time_refusals"] += 1
                    budget["classes"][cls] += 1
                    mine = row["lifted"].setdefault(cls, _blank())
                    mine["askings"] += 1
                    mine["learn_time_refusals"] += 1
                    mine["classes"][cls] += 1
                arm = ARM_OF.get(cls)
                if arm is None or unlearnable is not None:
                    continue                       # not a class a fix can buy
                got2, why2 = arm(target["before"], example["before"], example["after"])
                strict2 = score_strict(target, got2)
                marker2 = score_marker(target, got2, marker)
                _add(lifted[cls], strict2, marker2, why2)
                _add(row["lifted"][cls], strict2, marker2, why2)
        per_pull[name] = {
            "baseline": _rates(row["baseline"]),
            "lifted": {key: _rates(value) for key, value in row["lifted"].items()
                       if value["askings"]},
        }
        say(f"{name:45s} baseline covered {per_pull[name]['baseline']['right_not_imports']}"
            f"/{per_pull[name]['baseline']['developers_changes_not_imports']}")

    base = _rates(baseline)
    table = {}
    for cls in CLASSES:
        total = lifted.get(cls) or _blank()
        if not total["askings"] and not total["learn_time_refusals"]:
            continue
        rates = _rates(total)
        table[cls] = {
            "askings_of_this_class": total["askings"],
            "askings_where_the_example_itself_cannot_be_read": total["learn_time_refusals"],
            "askings_left_that_an_operator_could_reach":
                total["askings"] - total["learn_time_refusals"],
            "what_the_class_is": CLASSES[cls]["what"],
            "what_it_costs_to_really_buy_it": CLASSES[cls]["real_price"],
            "coverage_on_those_askings_alone": rates["strict_coverage"],
            "precision_on_those_askings_alone": rates["strict_precision"],
            "changes_this_class_could_ever_recover": total["right_not_imports"],
            # the whole point: what the corpus score becomes, not what the class does in isolation
            "corpus_strict_coverage_if_lifted": round(
                (base["right_not_imports"] + total["right_not_imports"]) / base["developers_changes_not_imports"], 4)
            if base["developers_changes_not_imports"] else None,
            "corpus_marker_same_if_lifted": round(
                (base["same"] + total["same"]) / base["questions"], 4) if base["questions"] else None,
            "organ_changes_added": total["organ_changes"],
            "not_what_the_developers_did_added": total["not_what_the_developers_did"],
        }

    def coverage(key: str) -> float:
        return table[key]["corpus_strict_coverage_if_lifted"] - base["strict_coverage"]

    ranked = sorted(table, key=lambda key: (-coverage(key), key))
    for key in ranked:
        table[key]["strict_coverage_gain_pp"] = round(100 * coverage(key), 2)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organ": ORGAN,
        "baseline": base,
        "classes": table,
        "ranked_by_measured_gain": ranked,
        "per_pull_request": per_pull,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    }


def code_sha256() -> dict[str, str]:
    out = {}
    for relative in (ORGAN, "canonical/tools/repeated_change_one_example_measure_v1.py",
                     "canonical/tools/edits_repeated_across_projects_v1.py",
                     "canonical/tools/which_fix_moves_generalization_v1.py"):
        path = ROOT / relative
        out[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "ABSENT"
    return out


ARMS: dict[str, str] = {
    "baseline": "the organ with the kept-name exemption switched off, so the gain is attributable",
    "call_shape": "a rename that leaves the arguments alone (pure rename + the organ's own gate)",
    "extend_import": "extend the import the file already has with the name the lesson needs",
    "both": "extend_import first, then call_shape on whatever is still refused",
}


def _arm(name: str) -> Callable[[Mapping[str, str], Mapping[str, str]], tuple[str | None, str | None]]:
    def baseline(target, example):
        """The organ with the kept-name exemption switched off, so the gain is attributable."""
        organ = organ_module()
        kept = organ.kept_alias
        organ.kept_alias = lambda rule: None
        try:
            return ask_strict(target["before"], example["before"], example["after"])
        finally:
            organ.kept_alias = kept

    def call_shape(target, example):
        return ask_past_unshown(target["before"], example["before"], example["after"])

    def extend_import(target, example):
        return ask_bringing_names(target["before"], example["before"], example["after"])

    def both(target, example):
        got, why = extend_import(target, example)
        if why is None:
            return got, why
        return call_shape(target, example)

    return {"baseline": baseline, "call_shape": call_shape,
            "extend_import": extend_import, "both": both}[name]


def compare_arms(pulls: Sequence[Mapping[str, Any]], markers: Mapping[str, str],
                 say: Callable[[str], None] = lambda line: None) -> dict[str, Any]:
    """Baseline and the two candidate operators, scored BOTH ways on the same askings.

    Both scorings are always reported because the two can disagree in sign. The strict scorer
    counts statements and cannot credit an import-only change; the marker scorer counts the
    per-question answer. An operator that helps one and hurts the other is reported as such.
    """
    from canonical.tools import edits_repeated_across_projects_v1 as marker_tool
    from canonical.tools import repeated_change_one_example_measure_v1 as measure

    table: dict[str, Any] = {}
    for name in ARMS:
        arm = _arm(name)
        covered = denominator = made = wrong = same = questions = 0
        askings = edited = 0
        for pull in pulls:
            marker = markers.get(pull["name"])
            for index, example in enumerate(pull["files"]):
                if learn_fails(example):
                    continue                 # no rule exists, so no arm can apply one
                for other, target in enumerate(pull["files"]):
                    if other == index:
                        continue
                    askings += 1
                    got, why = arm(target, example)
                    edited += why is None
                    strict = measure.score(target["before"], target["after"], got)
                    denominator += strict["developers_changes_not_imports"]
                    covered += strict["right_not_imports"]
                    made += strict["organ_changes"]
                    wrong += strict["not_what_the_developers_did"]
                    if marker:
                        one = marker_tool.answers(target["before"], target["after"], got, marker)
                        same += one["same"]
                        questions += one["questions"]
        table[name] = {
            "what_it_is": ARMS[name],
            "askings": askings,
            "share_edited": round(edited / askings, 4) if askings else None,
            "strict_coverage": round(covered / denominator, 4) if denominator else None,
            "strict_precision": round(covered / made, 4) if made else None,
            "marker_same_share": round(same / questions, 4) if questions else None,
            "organ_changes": made,
            "not_what_the_developers_did": wrong,
        }
        say("%-14s strict %s  precision %s  marker %s  wrong %d"
            % (name, table[name]["strict_coverage"], table[name]["strict_precision"],
               table[name]["marker_same_share"], wrong))
    return table


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    pulls = json.loads(args.pulls.read_text(encoding="utf-8"))
    if args.limit:
        pulls = pulls[: args.limit]

    started = time.time()
    record = run(pulls, markers=markers_for_pulls(pulls), say=print)
    record["code_sha256"] = code_sha256()
    record["pulls_sha256"] = hashlib.sha256(args.pulls.read_bytes()).hexdigest()
    record["pull_requests"] = [pull["name"] for pull in pulls]
    record["seconds"] = round(time.time() - started, 1)
    print()
    record["arms"] = compare_arms(pulls, markers_for_pulls(pulls), say=print)

    print()
    base = record["baseline"]
    print(f"BASELINE  strict coverage {base['strict_coverage']:.4f}  "
          f"precision {base['strict_precision']:.4f}  marker same {base['marker_same_share']}")
    print(f"{'class':24s} {'askings':>7s} {'+pp strict':>10s} {'+pp marker':>10s} "
          f"{'corpus coverage':>15s} {'+organ changes':>14s}")
    marker_base = base["marker_same_share"]
    for key in record["ranked_by_measured_gain"]:
        row = record["classes"][key]
        marker_gain = ("" if row["corpus_marker_same_if_lifted"] is None or marker_base is None
                       else "%+0.2f" % (100 * (row["corpus_marker_same_if_lifted"] - marker_base)))
        print(f"{key:24s} {row['askings_of_this_class']:7d} {row['strict_coverage_gain_pp']:10.2f} "
              f"{marker_gain:>10s} {row['corpus_strict_coverage_if_lifted']:15.4f} "
              f"{row['organ_changes_added']:14d}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
