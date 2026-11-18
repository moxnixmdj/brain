#!/usr/bin/env python3
"""Measure permanence on real code: learn an action at one version, move the environment, count
what the learned check CANNOT see.

WHY THIS EXISTS (the question, and the law the tree already owns)
-----------------------------------------------------------------
The standing claim is "learn it once, keep it permanently". The tree already refuted the reasoning half
of it in `permanence_amplifies_check_v1`:

    permanence is a MULTIPLIER on the check, not an achievement. One demonstration leaves two rules; the
    simpler one is wrong; a weak check accepts 40/40 while 1 of 40 is correct.

The 2026 record says the environment also moves: 26% of library versions violate semantic versioning,
33.8% of patch and 64.4% of minor updates carry a semantic break, signature-based checkers are "almost
entirely ineffective" at those breaks, and static semantic differencing finds >4x more of them than unit
tests do.

What has never been measured, and is the only measurement that decides the claim on real code:

    of the actions the environment actually MOVED, what fraction does the learned check fail to see?

THE DESIGN (it must not be able to fool itself)
-----------------------------------------------
* `old` and `new` are the tree's own pinned real ranges: packaging 21.0 -> 24.0, itsdangerous 2.0.0 ->
  2.1.2, tomli 1.0.0 -> 2.0.2. Real libraries, real releases, no synthetic tasks.
* An ACTION is (module, callable, witness, shape): call it, record the observable. The witness is drawn
  from the environment's OWN vocabulary (string literals in the module) plus neutral tokens -- the same
  discipline as round 5's interventional grounding, and it intervenes in both the scalar and the element
  shape because round 5 measured that a str is not a list.
* Witnesses are split deterministically into LEARNED (even positions) and HELD OUT (odd positions).
  The learned ones are what a check built from experience can see. The held-out ones are what the
  environment knows and the check does not.
* MOVED      = some arm's observable differs between old and new.
  CAUGHT     = some LEARNED arm's observable differs   -> the check would have alarmed.
  BLIND       = moved, but every learned arm is identical -> the check says "still permanently correct"
                about an action the environment has already changed. This is the dangerous class, and it
                is the only class this module exists to count.
* NONDETERMINISM CONTROL: the old tree is executed TWICE. Any callable whose arms differ between those
  two runs at the SAME revision is excluded and named -- otherwise randomness would be reported as an
  environment change.
* THE STRUCTURAL OBSERVABLE: each callable's signature (names, defaults, annotations) is compared between
  revisions. That splits the blind class in two, and the split is the finding:
      blind + signature changed  -> a structural observable would have caught it;
      blind + signature identical -> NEITHER behaviour nor structure sees it. That is vocabulary
      insufficiency, counted exactly.

REUSED, NOT REBUILT
-------------------
`site_by_intervention_v1.candidate_sites` (which callables can be driven at all),
`checkability_by_differential_pin_v1.execute.probe` (one child process, real imports, real exceptions,
identity stripped), `witness_inversion_v1` (real clones, git-archive materialisation), and the tree's own
`CORPUS_REPOS` ranges. No model, no network at run time, no fitted parameter, no knowledge house.

Authority NONE. Producer-run sandbox measurement.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

_REPO = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from canonical.swe_kernel import checkability_by_differential_pin_v1 as execute  # noqa: E402
from canonical.swe_kernel import site_by_intervention_v1 as SITE  # noqa: E402
from canonical.swe_kernel import structural_check_of_real_changes_v1 as corpus  # noqa: E402
from canonical.swe_kernel import witness_inversion_v1 as witness  # noqa: E402

SCHEMA = "BRAIN_RENEWABLE_ACTION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
MAX_WITNESSES = 8
MAX_ARMS = 16
BATCH = 96
NEUTRAL = ("empty_str", "zero", "one", "none")
SHAPES = ("scalar", "element")

SKIP_DIRS = {"tests", "test", "docs", "doc", "build", "dist", "examples", "benchmark", "scripts",
             ".git", "__pycache__", ".github", "noxfile.py", "tasks"}


# --------------------------------------------------------------------------- #
# what an action is made of
# --------------------------------------------------------------------------- #
def package_modules(tree: pathlib.Path) -> dict[str, pathlib.Path]:
    """Every importable module in the tree, keyed by MODULE NAME.

    Keyed by name and not by path, because a module that moves from `packaging/x.py` to `src/packaging/x.py`
    is the same module. Keying by path made packaging 21.0 -> 24.0 report every module as GONE_AT_NEW, which
    would have published "nothing changed in the biggest bump of the corpus" -- a false zero produced by the
    instrument, which is the exact failure this tree refuses.
    """
    found: dict[str, pathlib.Path] = {}
    for path in sorted(tree.rglob("*.py")):
        relative = path.relative_to(tree)
        if any(part in SKIP_DIRS for part in relative.parts[:-1]):
            continue
        if relative.name in SKIP_DIRS or relative.name == "__init__.py":
            continue
        module = corpus.module_name_for(str(relative))
        if module and module not in found:
            found[module] = path
    return found


def witnesses(source: str, value_cap: int = MAX_WITNESSES) -> list[str]:
    """Deterministic witnesses: the module's own literals first, then neutral tokens.

    No randomness anywhere: the same source always produces the same witnesses, so the split into
    learned and held-out is a property of the module, not of a seed.
    """
    tokens: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                if 1 <= len(text) <= 40 and "\n" not in text and ("=" + text) not in tokens:
                    tokens.append("=" + text)
    for neutral in NEUTRAL:
        if neutral not in tokens:
            tokens.append(neutral)
    return tokens[:value_cap]


def split(tokens: Sequence[str]) -> tuple[list[str], list[str]]:
    """Even positions are learned, odd positions are held out. Fixed rule, stated, not tuned."""
    return list(tokens[0::2]), list(tokens[1::2])


def signatures(source: str) -> dict[str, str]:
    """The structural observable: what the callable DECLARES, independent of what it does."""
    out: dict[str, str] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for function in tree.body:
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        try:
            head = ast.unparse(function.args)
        except Exception:  # noqa: BLE001 - an unrenderable signature is still a signature
            head = "?"
        out[function.name] = "%s(%s)" % (function.name, head)
    return out


def _token(module: str, site: Mapping[str, Any], witness: str, shape: str) -> list[str]:
    required = int(site.get("required") or 0)
    value = witness
    if value.startswith("="):
        encoded = value if shape == "scalar" else "@json:" + json.dumps([value[1:]])
    else:
        encoded = value
    tokens = ["empty_str"] * max(required, 1)
    if required:
        tokens[int(site.get("value_index") or 0)] = encoded
        tokens = tokens[:required]
    else:
        tokens = []
    return tokens


def arms_for(sites: Sequence[Mapping[str, Any]], tokens: Sequence[str]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for site in sites:
        for position, witness in enumerate(tokens):
            for shape in SHAPES:
                if witness.startswith("=") and shape == "element":
                    pass  # an element arm of a string literal is the collection intervention
                calls.append({"function": site["function"], "witness": witness, "shape": shape,
                              "value_index": site.get("value_index", 0),
                              "args": _token("", site, witness, shape)})
    return calls[:MAX_ARMS * max(len(sites), 1)]


def _kind(arm: Mapping[str, Any]) -> str:
    """What KIND of move it was. A removal, a signature change and a changed value are different events
    and must not be added together into one number."""
    old, new = str(arm.get("old") or ""), str(arm.get("new") or "")
    if new.startswith("NOT_CALLABLE") or new.startswith("IMPORT_FAILED"):
        return "REMOVED"
    if new.startswith("RAISED") and old.startswith("RETURNED"):
        return "NOW_RAISES"
    if old.startswith("RAISED") and new.startswith("RETURNED"):
        return "NO_LONGER_RAISES"
    if old.startswith("RETURNED") and new.startswith("RETURNED"):
        return "VALUE_CHANGED"
    return "OTHER"


def _observable(outcome: Mapping[str, Any]) -> str:
    return "|".join(str(outcome.get(key) or "") for key in ("outcome", "type", "value_repr"))


def observe(tree: pathlib.Path, module: str, calls: Sequence[Mapping[str, Any]]) -> list[str]:
    """Batched real execution: one child per batch, no model anywhere."""
    observed: list[str] = []
    for start in range(0, len(calls), BATCH):
        chunk = calls[start:start + BATCH]
        stripped = [{"module": module, "function": call["function"], "args": call["args"]}
                    for call in chunk]
        observed.extend(_observable(outcome) for outcome in execute.probe(tree, stripped))
    return observed


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def measure_module(old_tree: pathlib.Path, new_tree: pathlib.Path, relative: str,
                   module: str, new_relative: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"module": module, "relative": relative,
                           "new_relative": new_relative or relative}
    old_source = (old_tree / relative).read_text(encoding="utf-8", errors="replace")
    new_source = (new_tree / (new_relative or relative)).read_text(encoding="utf-8", errors="replace")
    sites = SITE.candidate_sites(old_source)
    if not sites:
        row["state"] = "NO_DRIVABLE_CALLABLE"
        return row
    tokens = witnesses(old_source)
    learned, held_out = split(tokens)
    row["learned_witnesses"] = learned
    row["held_out_witnesses"] = held_out
    old_signatures, new_signatures = signatures(old_source), signatures(new_source)

    per_callable: dict[str, dict[str, Any]] = {}
    for site in sites:
        name = site["function"]
        if name in per_callable:
            continue
        per_callable[name] = {"function": name, "learned": [], "held_out": [],
                              "signature_old": old_signatures.get(name),
                              "signature_new": new_signatures.get(name)}
    plans = arms_for(sites, tokens)
    for call in plans:
        per_callable[call["function"]].setdefault("arms", []).append(call)

    # nondeterminism control: the SAME revision twice
    first = observe(old_tree, module, plans)
    second = observe(old_tree, module, plans)
    third = observe(new_tree, module, plans)
    verdicts: list[dict[str, Any]] = []
    for index, call in enumerate(plans):
        entry = per_callable[call["function"]]
        if index >= len(first) or index >= len(second) or index >= len(third):
            continue
        arm = {"witness": call["witness"], "shape": call["shape"],
               "old": first[index], "new": third[index],
               "learned": call["witness"] in learned}
        if first[index] != second[index]:
            entry.setdefault("unstable_arms", []).append(arm)
        entry[("learned" if arm["learned"] else "held_out")].append(arm)

    # a module that does not import at the OLD revision never ran, so nothing was learned from it. Counting
    # its callables as "moved" would report the instrument's import problem as an environment change.
    old_outcomes = [arm["old"] for entry in per_callable.values() for arm in (entry.get("learned") or [])]
    if old_outcomes and all(item.startswith("IMPORT_FAILED") for item in old_outcomes):
        row["state"] = "MODULE_DOES_NOT_IMPORT_AT_OLD"
        row["counts"] = {"EXCLUDED_MODULE_IMPORT": len(per_callable)}
        return row

    for name, entry in per_callable.items():
        arms = (entry.get("learned") or []) + (entry.get("held_out") or [])
        if not arms:
            entry["state"] = "NO_ARM"
        elif entry.get("unstable_arms"):
            entry["state"] = "EXCLUDED_UNSTABLE"
        else:
            # only arms that actually RETURNED at the old revision are learned actions. An arm that raised
            # there taught nothing, so a different exception at the new revision is not the environment
            # moving a learned action -- counting it would inflate the moved set with the instrument's own
            # type errors (measured: 17 of 33 "moves" in the first full run were exactly this).
            learned_usable = [arm for arm in (entry.get("learned") or [])
                              if str(arm["old"]).startswith("RETURNED")]
            held_usable = [arm for arm in (entry.get("held_out") or [])
                           if str(arm["old"]).startswith("RETURNED")]
            if not learned_usable:
                entry["state"] = "NEVER_OBSERVED_AT_OLD"
                verdicts.append(entry)
                continue
            arms = learned_usable + held_usable
            entry["learned"] = learned_usable
            moved = [arm for arm in arms if arm["old"] != arm["new"]]
            if not moved:
                entry["state"] = "STABLE"
            else:
                kinds = {_kind(arm) for arm in moved}
                entry["kind"] = (sorted(kinds)[0] if len(kinds) == 1 else "MIXED")
                caught = [arm for arm in moved if arm["learned"]]
                if caught:
                    entry["state"] = "CAUGHT"
                    entry["evidence"] = caught[0]
                else:
                    entry["state"] = "BLIND"
                    entry["evidence"] = moved[0]
                    entry["structural_change"] = entry.get("signature_old") != entry.get("signature_new")
                # the honest curve: a check that saw only the first k learned contrasts
                curve: dict[str, bool] = {}
                for k in range(1, min(len(entry.get("learned") or []), 4) + 1):
                    seen = any(arm["old"] != arm["new"] for arm in (entry.get("learned") or [])[:k])
                    curve[str(k)] = bool(seen)
                entry["seen_by_k"] = curve
                # PER-WITNESS blindness: would a check that learned from ONE arbitrary witness have seen
                # this move? That, not the 4-witness row, is the risk of "learn it once".
                learned_arms = entry.get("learned") or []
                blind_arms = [arm for arm in learned_arms if arm["old"] == arm["new"]]
                entry["per_witness"] = {"learned_arms": len(learned_arms),
                                        "blind_arms": len(blind_arms),
                                        "blind_risk": round(len(blind_arms) / len(learned_arms), 4)
                                        if learned_arms else None}
        entry.pop("arms", None)
        entry.pop("unstable_arms", None)
        verdicts.append(entry)
    row["callables"] = verdicts
    counts: dict[str, int] = {}
    for entry in verdicts:
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    row["counts"] = counts
    return row


def measure_repo(repo: str, old: str, new: str, cache: pathlib.Path,
                 work: pathlib.Path) -> dict[str, Any]:
    clone = witness.fetch(repo, old, new, cache)
    row: dict[str, Any] = {"repo": repo, "old": old, "new": new}
    if clone is None:
        row["state"] = "FETCH_FAILED"
        return row
    old_tree, note_old = witness.materialise(clone, old, work, suffix="-old")
    new_tree, note_new = witness.materialise(clone, new, work, suffix="-new")
    if old_tree is None or new_tree is None:
        row["state"] = "MATERIALISE_FAILED"
        row["detail"] = note_old or note_new
        return row
    modules: list[dict[str, Any]] = []
    old_modules, new_modules = package_modules(old_tree), package_modules(new_tree)
    for module, path in old_modules.items():
        relative = str(path.relative_to(old_tree))
        if module not in new_modules:
            modules.append({"module": module, "relative": relative, "state": "GONE_AT_NEW"})
            continue
        new_relative = str(new_modules[module].relative_to(new_tree))
        try:
            modules.append(measure_module(old_tree, new_tree, relative, module,
                                          new_relative=new_relative))
        except Exception as exc:  # noqa: BLE001 - an instrument failure is named, never counted
            modules.append({"module": module, "relative": relative,
                            "state": "INSTRUMENT_FAILED", "detail": type(exc).__name__ + ": " + str(exc)[:160]})
    row["modules"] = modules
    row["state"] = "MEASURED"
    return row


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    totals = {"callables": 0, "STABLE": 0, "CAUGHT": 0, "BLIND": 0, "EXCLUDED_UNSTABLE": 0,
              "NEVER_OBSERVED_AT_OLD": 0, "NO_ARM": 0, "modules": 0, "modules_failed": 0,
              "modules_excluded_import": 0,
              "blind_and_structural": 0, "blind_and_identical_signature": 0}
    kinds: dict[str, int] = {}
    curve: dict[str, dict[str, int]] = {}
    stats: list[dict[str, Any]] = []
    blind_examples: list[dict[str, Any]] = []
    for row in rows:
        if row.get("state") != "MEASURED":
            totals["modules_failed"] += 1
            continue
        for module in row.get("modules", []):
            totals["modules"] += 1
            if module.get("state") in ("INSTRUMENT_FAILED", "GONE_AT_NEW"):
                totals["modules_failed"] += 1
            if module.get("state") == "MODULE_DOES_NOT_IMPORT_AT_OLD":
                totals["modules_excluded_import"] += 1
            for entry in module.get("callables") or []:
                totals["callables"] += 1
                state = entry.get("state")
                if state in totals:
                    totals[state] += 1
                if state in ("CAUGHT", "BLIND") and entry.get("kind"):
                    kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
                if state in ("CAUGHT", "BLIND") and (entry.get("per_witness") or {}).get("learned_arms"):
                    stats.append(entry["per_witness"])
                for k, seen in (entry.get("seen_by_k") or {}).items():
                    bucket = curve.setdefault(k, {"callables_with_k_contrasts": 0, "moved": 0,
                                                 "caught": 0, "blind": 0})
                    bucket["callables_with_k_contrasts"] += 1
                    bucket["moved"] += 1
                    bucket["caught" if seen else "blind"] += 1
                if state == "BLIND":
                    if entry.get("structural_change"):
                        totals["blind_and_structural"] += 1
                    else:
                        totals["blind_and_identical_signature"] += 1
                    if len(blind_examples) < 12:
                        blind_examples.append({
                            "repo": row["repo"], "module": module["module"],
                            "function": entry["function"], "evidence": entry.get("evidence"),
                            "signature_old": entry.get("signature_old"),
                            "signature_new": entry.get("signature_new")})
    moved = totals["CAUGHT"] + totals["BLIND"]
    totals["moved"] = moved
    totals["blind_fraction_of_moved"] = (round(totals["BLIND"] / moved, 4) if moved else None)
    totals["blind_fraction_without_a_signature_observable"] = (
        round(totals["blind_and_identical_signature"] / moved, 4) if moved else None)
    for bucket in curve.values():
        bucket["blind_fraction"] = (round(bucket["blind"] / bucket["moved"], 4) if bucket["moved"] else None)
    totals["move_kinds"] = kinds
    if stats:
        totals["per_witness_blind_risk_mean"] = round(
            sum(item["blind_risk"] for item in stats) / len(stats), 4)
        totals["moves_with_at_least_one_blind_single_witness"] = sum(
            1 for item in stats if item["blind_arms"] > 0)
        totals["moves_measured_per_witness"] = len(stats)
    return {"totals": totals, "blind_by_number_of_contrasts": curve, "blind_examples": blind_examples}


MINOR_PAIRS = (("pypa/packaging", "24.0", "24.1"),)


def measure(cache: pathlib.Path, work: pathlib.Path, limit: int | None = None) -> dict[str, Any]:
    """The tree's own pinned major bumps, plus one real MINOR bump reported apart.

    The minor bump is here on purpose and not to move a number: 2026 measurements put 33.8% of patch and
    64.4% of minor releases at carrying a semantic break, i.e. exactly the regime where a system is most
    tempted to treat a learned action as permanently valid. It is reported as its own set.
    """
    pairs = list(witness.CORPUS_REPOS[:limit])
    rows = [measure_repo(repo, old, new, cache, work) for repo, old, new in pairs]
    minor_rows = [measure_repo(repo, old, new, cache, work) for repo, old, new in MINOR_PAIRS]
    summary = summarise(rows)
    summary["minor_bump_regime"] = summarise(minor_rows)
    return {"schema": SCHEMA, "authority": AUTHORITY, "model_calls": 0, "network_calls": 0,
            "incremental_spend_usd": 0, "repos": rows, "minor_bump_repos": minor_rows, **summary,
            "reproduce": ".venv/bin/python canonical/swe_kernel/renewable_action_v1.py --json "
                         "canonical/verification/RENEWABLE_ACTION_20261116_V1.json"}


def _headline(report: Mapping[str, Any]) -> str:
    totals = report.get("totals") or {}
    return (
        "%(callables)d learned actions over %(modules)d real modules in 3 real version bumps. "
        "%(STABLE)d never moved. %(moved)d moved: %(CAUGHT)d were seen by the learned witnesses, "
        "%(BLIND)d were NOT -- the check would have called a changed action permanently correct "
        "(%(blind_fraction_of_moved)s of the moved set). Of those blind cases, %(blind_and_structural)d "
        "carried a signature change a structural observable would have caught, and "
        "%(blind_and_identical_signature)d had an identical signature, so neither behaviour at the "
        "learned witnesses nor structure sees them: that is the vocabulary gap, counted. "
        "%(EXCLUDED_UNSTABLE)d were excluded as nondeterministic at the same revision and "
        "%(modules_excluded_import)d modules were excluded because they do not import at the old revision."
        % totals)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure what a learned check cannot see.")
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--cache", type=pathlib.Path, default=pathlib.Path("/tmp/perm-cache"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/perm-work"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    report = measure(args.cache, args.work, args.limit)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("written:", args.json)
    print(_headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
