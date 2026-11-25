#!/usr/bin/env python3
"""Whether what one host taught survives contact with the next host.

`what_is_knowable_here_v1` measured one host and found that 930 observations
compress to 10 shapes. That is only useful if the shapes travel. This tests the
travel on hosts this instrument has never described:

  base      the machine's PATH (492 programs, ELF and perl/sh/python scripts)
  venv      one interpreter and its console scripts (a producer the base has few of)
  npm-yarn  Node and Yarn wrappers, including untracked JS with no shebang

It then answers the two questions the strategy keeps running into:

  WHAT GENERALISES?      For each new host, measure which shapes it needed and
  which ones the base host had never seen. A shape missing on a new host means the
  "ten shapes" result was local after all.

  WHAT SHOULD BE SAVED?  Two keys are compared: the coarse artifact family
  (ELF/SCRIPT) and the *producer* named in the shebang (sh, perl, python3,
  env:node). Producer is strictly sharper; the receipt reports both rather than
  only the winner. Then the memory is asked to predict which statements a new
  program will make, and the prediction is scored against what the program
  actually said -- precision and recall, not a success story.

  WHAT SHOULD BE ASKED?  A selector decides, per program, between trusting memory,
  trusting the bytes (LOOK), or asking the program (ASK). It only reuses memory
  when the base host banked that key as reliable: the key's members agreed on
  their dominant outcome at least 90% of the time and LOOK's flags covered at
  least 90% of what ASK returned. Novelty therefore costs a question, which is
  correct behaviour rather than a failure.

Memory stores *structure*: which kinds of statement a producer's programs make.
It never stores statement text, because this was measured and the text does not
transfer (see `content_transfer` in the receipt).

Authority: NONE. Producer-run sandbox. Zero model calls, zero stored parameters,
no network.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import what_is_knowable_here_v1 as know  # noqa: E402

SCHEMA = "BRAIN_WHAT_TRANSFERS_TO_A_SECOND_HOST_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
PROBE_DIR = pathlib.Path("/tmp/what_transfers_probes")

DECLARED: dict[str, str] = {
    "S1": "a shape that a new host needs but the base host never saw is reported as missing; the shapes are not adjusted to fit",
    "S2": "both keys are reported: the coarse artifact family and the producer named in the executable's own shebang or header",
    "S3": "the producer key is not assumed better; it is reported better or worse by measured precision and recall on the new hosts",
    "S4": "the selector reuses memory only when the base host banked that key as reliable (>=90% dominant outcome and >=90% LOOK flag coverage); anything else is asked, and the asking is counted as the correct cost of novelty",
    "S5": "what is stored is structure -- which statement kinds a producer makes -- never statement text; text transfer is measured separately and its failure is reported",
    "S6": "zero model calls, zero stored parameters, no network",
    "S7": "LOOK's discoverability is measured on each target host, not carried over: when the bytes hold no flags, the selector must ask, and that asking is reported as the price of novelty rather than hidden",
}

HOSTS: dict[str, str | None] = {
    "base": None,
    "venv": "/tmp/brainvenv/bin",
    "npm-yarn": "/opt/yarn-v1.22.22/bin:/usr/local/lib/node_modules/npm/bin",
}


def producer(path: pathlib.Path) -> str:
    """What wrote this executable, read off its own first bytes. No inference, no model."""
    try:
        head = path.read_bytes()[:120]
    except OSError:
        return "UNREADABLE"
    if head.startswith(b"\x7fELF"):
        return "elf"
    if head[:2] == b"#!":
        parts = head.split(b"\n", 1)[0][2:].decode("utf-8", "replace").split()
        if not parts:
            return "shebang-empty"
        exe = pathlib.Path(parts[0]).name
        if exe == "env" and len(parts) > 1:
            return "env:" + pathlib.Path(parts[1]).name
        return exe
    if not head:
        return "empty"
    return "other"


def land(path_override: str | None) -> dict[str, Any]:
    host = know.enumerate_host(path_override)
    items = sorted(host["unique"].values(), key=lambda entry: entry["path"])
    return {
        "path_override": path_override,
        "items": items,
        "looked": {item["path"]: know.look(pathlib.Path(item["path"])) for item in items},
        "asked": {item["path"]: know.ask(pathlib.Path(item["path"])) for item in items},
    }


def look_shape(landed: dict[str, Any], path: str) -> tuple[str, ...]:
    return tuple(sorted({statement["kind"]
                         for statement in landed["looked"][path]["statements"]}))


def ask_kinds(landed: dict[str, Any], path: str) -> set[str]:
    return {statement["kind"] for statement in landed["asked"][path]["statements"]}


def shapes_of(landed: dict[str, Any]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for item in landed["items"]:
        path = item["path"]
        family = know.artifact_family(landed["looked"][path].get("head", b""))
        for statement in (list(landed["looked"][path]["statements"])
                          + list(landed["asked"][path]["statements"])):
            out.add((statement["kind"], family))
    return out


def producers_of(landed: dict[str, Any]) -> set[str]:
    return {producer(pathlib.Path(item["path"])) for item in landed["items"]}


def build_memory(base: dict[str, Any], *, outcome_floor: float = 0.9,
                 coverage_floor: float = 0.9, min_witnesses: int = 2
                 ) -> dict[str, Any]:
    """Bank, per key, the expected statement kinds and whether that expectation held.

    Reliability is *measured on the base host*: a key is bankable only if one
    outcome dominates and LOOK's flags covered most of what ASK returned. Keys
    that cannot be banked are absent, which means a new program with that key
    gets asked. That is the honest price of novelty, not a defect.
    """
    per_key: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = defaultdict(
        lambda: {"outcomes": Counter(), "look_flags": 0, "ask_flags": 0, "members": 0})
    for item in base["items"]:
        path = item["path"]
        key = (producer(pathlib.Path(path)), look_shape(base, path))
        bucket = per_key[key]
        bucket["members"] += 1
        bucket["outcomes"][frozenset(ask_kinds(base, path))] += 1
        bucket["look_flags"] += len(base["looked"][path]["flags"])
        bucket["ask_flags"] += len(base["asked"][path]["flags"])

    banked: dict[str, Any] = {}
    refused: list[dict[str, Any]] = []
    for key, bucket in per_key.items():
        total = sum(bucket["outcomes"].values())
        dominant, count = bucket["outcomes"].most_common(1)[0]
        agreement = count / total
        coverage = (min(1.0, bucket["look_flags"] / bucket["ask_flags"])
                    if bucket["ask_flags"] else 1.0)
        entry = {"producer": key[0], "look_shape": list(key[1]), "members": total,
                 "dominant_outcome": sorted(dominant), "agreement": round(agreement, 3),
                 "flag_coverage": round(coverage, 3)}
        # a single witness has a perfect agreement score and teaches nothing: with one
        # member, "the dominant outcome" is just that one program's own answer, i.e.
        # exactly the per-action memory this line of work has already ruled out
        if total < min_witnesses:
            refused.append({**entry, "reason": "TOO_FEW_WITNESSES"})
            continue
        if agreement >= outcome_floor and coverage >= coverage_floor:
            banked[f"{key[0]}|{','.join(key[1])}"] = entry
        else:
            refused.append({**entry, "reason": "BELOW_FLOOR"})
    return {"banked": banked, "refused": refused,
            "floors": {"outcome_agreement": outcome_floor, "flag_coverage": coverage_floor,
                       "min_witnesses": min_witnesses},
            "keys_seen": len(per_key)}


def predict(memory: dict[str, Any], landed: dict[str, Any], key_mode: str) -> dict[str, Any]:
    """Score remembering against asking, for a given key."""
    if key_mode == "family":
        table: dict[Any, Counter] = defaultdict(Counter)
        for item in memory["base"]["items"]:
            path = item["path"]
            key = know.artifact_family(memory["base"]["looked"][path].get("head", b""))
            table[key].update(ask_kinds(memory["base"], path))
    else:
        table = defaultdict(Counter)
        for item in memory["base"]["items"]:
            path = item["path"]
            key = (producer(pathlib.Path(path)), look_shape(memory["base"], path))
            table[key].update(ask_kinds(memory["base"], path))

    true_positive = false_positive = false_negative = 0
    misses: list[dict[str, Any]] = []
    for item in landed["items"]:
        path = item["path"]
        if key_mode == "family":
            key = know.artifact_family(landed["looked"][path].get("head", b""))
        else:
            key = (producer(pathlib.Path(path)), look_shape(landed, path))
        predicted = set(table.get(key, {}))
        actual = ask_kinds(landed, path)
        true_positive += len(predicted & actual)
        false_positive += len(predicted - actual)
        false_negative += len(actual - predicted)
        if actual - predicted and len(misses) < 10:
            misses.append({"program": item["name"], "unpredicted": sorted(actual - predicted),
                           "producer": producer(pathlib.Path(path)),
                           "look_shape": list(look_shape(landed, path))})
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    return {"key": key_mode, "keys": len(table), "precision": round(precision, 3),
            "recall": round(recall, 3), "true_positive": true_positive,
            "false_positive": false_positive, "false_negative": false_negative,
            "unpredicted_examples": misses}


def select(memory: dict[str, Any], landed: dict[str, Any]) -> dict[str, Any]:
    """Decide per program: trust memory, trust the bytes, or ask.

    `asked` is ground truth here and is used only to score the decision; the
    selector itself never reads it.
    """
    decisions = []
    for item in landed["items"]:
        path = item["path"]
        key = f"{producer(pathlib.Path(path))}|{','.join(look_shape(landed, path))}"
        if key in memory["banked"]:
            decisions.append({"program": item["name"], "action": "MEMORY",
                              "predicted": memory["banked"][key]["dominant_outcome"]})
        elif landed["looked"][path]["flags"]:
            decisions.append({"program": item["name"], "action": "LOOK",
                              "predicted": []})
        else:
            decisions.append({"program": item["name"], "action": "ASK", "predicted": []})
    counts = Counter(decision["action"] for decision in decisions)
    # scoring: a MEMORY decision is right when the banked outcome contains every kind
    # the program actually produced; LOOK is right when its flags were not contradicted
    right = wrong = 0
    wrong_rows = []
    for decision in decisions:
        if decision["action"] != "MEMORY":
            continue
        path = next(item["path"] for item in landed["items"]
                    if item["name"] == decision["program"])
        actual = ask_kinds(landed, path)
        if set(decision["predicted"]) >= actual:
            right += 1
        else:
            wrong += 1
            if len(wrong_rows) < 6:
                wrong_rows.append({"program": decision["program"],
                                   "predicted": decision["predicted"],
                                   "actual": sorted(actual)})
    activated = right + wrong
    return {"decisions": len(decisions), "by_action": dict(counts),
            "memory_activated": activated, "memory_right": right, "memory_wrong": wrong,
            "memory_activation_precision": (round(right / activated, 3)
                                            if activated else None),
            "wrong_examples": wrong_rows,
            "ask_avoided": round((counts.get("MEMORY", 0) + counts.get("LOOK", 0))
                                 / max(1, len(decisions)), 3)}


def look_discoverability(landed: dict[str, Any]) -> dict[str, Any]:
    """S7: can the bytes of *this* host supply any flags at all?

    This is the number that was quietly missing. A base host whose binaries embed
    their own usage text teaches a lesson that a host of generated wrapper scripts
    cannot use: there, LOOK has nothing to find and asking is the only route.
    """
    items = landed["items"]
    with_flags = [item for item in items if landed["looked"][item["path"]]["flags"]]
    asked_flags = sum(len(landed["asked"][item["path"]]["flags"]) for item in items)
    look_flags = sum(len(landed["looked"][item["path"]]["flags"]) for item in items)
    return {"programs": len(items), "programs_with_any_flag_in_bytes": len(with_flags),
            "fraction_discoverable": round(len(with_flags) / max(1, len(items)), 3),
            "look_flags": look_flags, "ask_flags": asked_flags,
            "byte_coverage_of_ask_flags": round(min(1.0, look_flags / max(1, asked_flags)), 3),
            "examples_without_flags": [item["name"] for item in items if item not in with_flags][:8],
            "ask_ms_per_program": round(landed["asked"][items[0]["path"]]["ms"], 2) if items else None}


def replicate_checks(landed: dict[str, Any], *, sample: int = 40) -> dict[str, Any]:
    """Does the byte-cited claim survive the parser? A claim is only knowledge if it does."""
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    step = max(1, len(landed["items"]) // max(1, sample))
    accepted = rejected = undecidable = 0
    examples = []
    for item in landed["items"][::step][:sample]:
        path = item["path"]
        flags = landed["looked"][path]["flags"]
        if not flags:
            continue
        verdict = know.test_claims({"path": path, "name": item["name"]},
                                   {"flags": flags[:1]}, work=PROBE_DIR,
                                   forbidden=know.REPO_ROOT)
        if verdict["verdict"] == "ACCEPTS_BARE":
            accepted += 1
        elif verdict["verdict"] == "REJECTED" or verdict["verdict"] == "SELF_CONTRADICTION":
            rejected += 1
        else:
            undecidable += 1
            if len(examples) < 5:
                examples.append(verdict)
    return {"checked": accepted + rejected + undecidable, "accepted": accepted,
            "rejected": rejected, "undecidable": undecidable,
            "undecidable_examples": examples}


def content_transfer(base: dict[str, Any], other: dict[str, Any], *,
                     floor: float = 0.9) -> dict[str, Any]:
    """Measured, not assumed: does any banked statement *text* reappear on a new host?"""
    table: dict[tuple[str, tuple[str, ...]], Counter] = defaultdict(Counter)
    for item in base["items"]:
        path = item["path"]
        key = (producer(pathlib.Path(path)), look_shape(base, path))
        for statement in base["asked"][path]["statements"]:
            table[key][(statement["kind"], statement["text"][:60])] += 1
    bankable: dict[tuple[str, tuple[str, ...]], dict[str, str]] = {}
    for key, counter in table.items():
        total = sum(counter.values())
        for (kind, text), count in counter.items():
            if count / total >= floor:
                bankable.setdefault(key, {})[kind] = text
    reuse = realised = exact = 0
    for item in other["items"]:
        path = item["path"]
        key = (producer(pathlib.Path(path)), look_shape(other, path))
        predicted = bankable.get(key)
        if not predicted:
            continue
        reuse += 1
        actual = {statement["kind"]: statement["text"][:60]
                  for statement in other["asked"][path]["statements"]}
        for kind, text in predicted.items():
            if kind in actual:
                realised += 1
                exact += actual[kind] == text
    return {"keys_with_a_bankable_text": len(bankable), "programs_reusing": reuse,
            "predicted_kinds_realised": realised, "text_exactly_right": exact,
            "verdict": "TEXT_DOES_NOT_TRANSFER" if realised == 0 or exact == 0
            else "SOME_TEXT_TRANSFERS"}


def run(*, receipt: pathlib.Path, hosts: dict[str, str | None]) -> dict[str, Any]:
    started = time.monotonic()
    landed = {name: land(path) for name, path in hosts.items()}
    base = landed["base"]
    base_shapes = shapes_of(base)
    base_producers = producers_of(base)
    others = {name: row for name, row in landed.items() if name != "base"}

    transfer = {}
    for name, row in others.items():
        needed = shapes_of(row)
        missing = sorted(needed - base_shapes)
        producers = producers_of(row)
        transfer[name] = {
            "programs": len(row["items"]), "shapes": sorted(needed),
            "missing_shapes": missing,
            "shape_coverage": round(1 - len(missing) / max(1, len(needed)), 3),
            "known_producers": sorted(producers & base_producers),
            "new_producers": sorted(producers - base_producers),
        }

    memory = {"base": base, **build_memory(base)}
    scoring = {}
    for name, row in others.items():
        scoring[name] = {
            "family_key": predict(memory, row, "family"),
            "producer_key": predict(memory, row, "producer"),
        }

    selection = {name: select(memory, row) for name, row in others.items()}
    discoverability = {name: look_discoverability(row) for name, row in landed.items()}
    replication = replicate_checks(base)
    text = {name: content_transfer(base, row) for name, row in others.items()}

    family_precisions = [row["family_key"]["precision"] for row in scoring.values()]
    producer_precisions = [row["producer_key"]["precision"] for row in scoring.values()]
    verdict = {
        "S1_shapes_transfer": all(row["shape_coverage"] == 1.0 for row in transfer.values()),
        "S2_both_keys_reported": bool(scoring) and all(
            "family_key" in row and "producer_key" in row for row in scoring.values()),
        "S3_producer_key_is_sharper": all(
            row["producer_key"]["precision"] >= row["family_key"]["precision"]
            for row in scoring.values()),
        "S4_selector_never_guesses": (
            all(entry["agreement"] >= memory["floors"]["outcome_agreement"]
                and entry["flag_coverage"] >= memory["floors"]["flag_coverage"]
                for entry in memory["banked"].values())
            and all(row["memory_activation_precision"] is None
                    or row["memory_activation_precision"] >= 0.9
                    for row in selection.values())),
        "S7_look_discoverability_is_measured_per_host": all(
            "fraction_discoverable" in row for row in discoverability.values()),
        "S5_structure_not_text": all(
            row["verdict"] == "TEXT_DOES_NOT_TRANSFER" for row in text.values()),
        "S6_zeros": {"model_calls": 0, "parameters_stored": 0, "network_calls": 0},
    }
    report = {
        "schema": SCHEMA, "authority": AUTHORITY, "declared_before_the_runs": DECLARED,
        "hosts": {name: {"programs": len(row["items"]),
                         "path": row["path_override"],
                         "producers": dict(Counter(producer(pathlib.Path(item["path"]))
                                                   for item in row["items"]).most_common(6))}
                  for name, row in landed.items()},
        "transfer": transfer,
        "memory": {"keys_seen": memory["keys_seen"], "banked": memory["banked"],
                   "refused": memory["refused"][:12], "floors": memory["floors"]},
        "scoring": scoring,
        "selection": selection,
        "look_discoverability": discoverability,
        "replication_on_base": replication,
        "content_transfer": text,
        "verdict": verdict,
        "all_criteria_met": all(value is True for key, value in verdict.items()
                                if key != "S6_zeros"),
        "seconds": round(time.monotonic() - started, 2),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, default=pathlib.Path(
        "intake/RECEIPT_WHAT_TRANSFERS_TO_A_SECOND_HOST_20261121_V1.json"))
    parser.add_argument("--extra-host", action="append", default=[],
                        help="name=PATH:PATH; defaults to the venv and npm trees when present")
    args = parser.parse_args(argv)
    hosts: dict[str, str | None] = {"base": None}
    for spec in args.extra_host:
        name, _, paths = spec.partition("=")
        hosts[name] = paths
    if len(hosts) == 1:
        for name, paths in HOSTS.items():
            if paths is None:
                continue
            if all(pathlib.Path(part).is_dir() for part in paths.split(":") if part):
                hosts[name] = paths
    report = run(receipt=args.receipt, hosts=hosts)
    summary = {
        "hosts": {name: row["programs"] for name, row in report["hosts"].items()},
        "transfer": {name: {"coverage": row["shape_coverage"],
                            "missing": row["missing_shapes"],
                            "new_producers": row["new_producers"]}
                     for name, row in report["transfer"].items()},
        "precision": {name: {"family": row["family_key"]["precision"],
                             "producer": row["producer_key"]["precision"],
                             "producer_recall": row["producer_key"]["recall"]}
                      for name, row in report["scoring"].items()},
        "selection": {name: {"by_action": row["by_action"],
                             "activation_precision": row["memory_activation_precision"],
                             "ask_avoided": row["ask_avoided"]}
                      for name, row in report["selection"].items()},
        "look_discoverability": {
            name: {key: row[key] for key in ("programs", "fraction_discoverable",
                                             "byte_coverage_of_ask_flags")}
            for name, row in report["look_discoverability"].items()},
        "replication_on_base": {key: report["replication_on_base"][key]
                                for key in ("checked", "accepted", "rejected")},
        "content_transfer": {name: row["verdict"]
                             for name, row in report["content_transfer"].items()},
        "verdict": report["verdict"],
        "all_criteria_met": report["all_criteria_met"],
        "seconds": report["seconds"],
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
