"""A check witnesses an action only for the object whose bytes that action changed.

This is the round that fills the citation from the room, as the previous round's §9 asked.
It does NOT repair the check. Every check below is still blind to WHICH object it is looking
at -- the eight probes from `A_CHECK_THAT_NOBODY_RUNS_20261203` still accept a same-kind decoy.
What changes is what gets credited: `room_witness_v1.witness()` binds a held check to the
byte-level delta of this action. A check that passes on a decoy the action never touched is
an INVARIANT, not a witness. A goal that was already true before the action is a FALSE DONE
and is refused, which is the failure OSWorld 2.0 measures as 75--83.3% premature stops.

Hard controls, all declared before the run in `judged()`:
  * 8 which-object probes, unchanged from the shipped audit;
  * false-done (no-op action, goal already satisfied);
  * all-reject verifier (VerifierBench's dominant false-rejection mode);
  * valid alternative producer and a different output name (no over-rejection);
  * an action that changes both the right object and the decoy (ambiguity);
  * deliberately wrong stored binding (wrong-memory control);
  * destroyed bytes reported as ACCEPTED_CHANGED, never ACCEPTED_INERT;
  * transfer to producers chosen after the rule was frozen (thin machine).

Zero model calls. Zero stored parameters. Zero network at measure time. Every check program
is one the machine already had; every producer in the decoy rooms is a fixture and is named
in the receipt. Authority NONE__PRODUCER_RUN_SANDBOX.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import time
import zipfile
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import room_witness_v1 as rw  # noqa: E402
from canonical.tools import (  # noqa: E402
    a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1 as audit,
    the_guide_is_an_action_grammar_v1 as guide,
)

SCHEMA = "BRAIN_THE_CHECK_IS_THE_OBJECT_THE_ACTION_PRODUCED_20261124_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-11-24"
DEFAULT_RECEIPT = (REPO / "canonical/verification/"
                   "THE_CHECK_IS_THE_OBJECT_THE_ACTION_PRODUCED_20261124_V1.json")

# Producers chosen AFTER the witness rule was frozen, i.e. not one of the four artifact kinds
# used to design it. They are read from the machine at run time, never from a page's prose.
TRANSFER_PRODUCERS: tuple[dict[str, str], ...] = (
    {"producer": "bzip2", "argv": "bzip2 -kf payload.txt", "right": "payload.txt.bz2",
     "decoy": "other.txt.bz2", "check": "bzip2 -t"},
    {"producer": "xz", "argv": "xz -kf payload.txt", "right": "payload.txt.xz",
     "decoy": "other.txt.xz", "check": "xz -t"},
    # sha256sum accepts EVERY object. A vacuous check is still a witness when it is bound to
    # the byte delta, and is not a witness for an untouched decoy.
    {"producer": "cp", "argv": "cp payload.txt made.out", "right": "made.out",
     "decoy": "other.out", "check": "sha256sum"},
)


# --------------------------------------------------------------------------- #
# 1. Rooms: the right object is PRODUCED BY the action, the decoy EXISTS BEFORE it
# --------------------------------------------------------------------------- #

def _base_room(root: pathlib.Path) -> None:
    (root / "notes").mkdir(parents=True, exist_ok=True)
    (root / "notes" / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (root / "notes" / "b.txt").write_text("one\ntwo\n", encoding="utf-8")
    (root / "payload.txt").write_text("the quick brown fox\n", encoding="utf-8")
    (root / "other.txt").write_text("a completely different sentence\n", encoding="utf-8")


def _fixture(root: pathlib.Path, kind: str, which: str) -> tuple[str, list[str]]:
    """Create right/decoy of one kind. Returns (path, argv the fixture ran)."""
    if kind == "gzip":
        name, src = (("payload.txt.gz", "payload.txt") if which == "right"
                     else ("other.txt.gz", "other.txt"))
        argv = ["gzip", "-kf", src]
        guide.run(argv, root)
        return name, argv
    if kind == "tar":
        name, src = (("right.tar", "notes/a.txt") if which == "right"
                     else ("decoy.tar", "notes/b.txt"))
        argv = ["tar", "-cf", name, src]
        guide.run(argv, root)
        return name, argv
    if kind == "zip":
        name, member = (("right.zip", "a.txt") if which == "right"
                        else ("decoy.zip", "b.txt"))
        with zipfile.ZipFile(root / name, "w") as archive:
            archive.writestr(member, "x\n")
        return name, ["<zipfile fixture>", name]
    if kind == "json":
        name = "right.json" if which == "right" else "decoy.json"
        (root / name).write_text('{"a": 1}\n' if which == "right" else '{"b": 2}\n',
                                 encoding="utf-8")
        return name, ["<write_text fixture>", name]
    raise ValueError(kind)


def _reread(root: pathlib.Path):
    def read(rel: str) -> str:
        return hashlib.sha256((root / rel).read_bytes()).hexdigest()
    return read


def _check_argv(probe: Sequence[str], path: str) -> list[str]:
    return [*probe, path]


def _check_rows(name: str, right: str, decoy: str,
                got_right: bool, got_decoy: bool) -> list[dict[str, Any]]:
    return [{"check": name, "held": got_right, "path": right},
            {"check": name, "held": got_decoy, "path": decoy}]


# --------------------------------------------------------------------------- #
# 2. The eight probes, unchanged from the shipped audit
# --------------------------------------------------------------------------- #

def which_object_round() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for kind, probes in audit.WHICH_PROBES.items():
        for probe in probes:
            with tempfile.TemporaryDirectory(prefix="witness-") as where:
                root = pathlib.Path(where) / "room"
                _base_room(root)
                decoy, _ = _fixture(root, kind, "decoy")
                before = rw.digest(root)
                right, producer = _fixture(root, kind, "right")
                after = rw.digest(root)
                right_got = guide.run(_check_argv(probe, right), root)
                decoy_got = guide.run(_check_argv(probe, decoy), root)
                checks = _check_rows(" ".join(probe), right, decoy,
                                     right_got["accepted"], decoy_got["accepted"])
                got = rw.witness(before, after, checks, decoys=[decoy], argv=producer,
                                 reread=_reread(root))
                rows.append({
                    "kind": kind, "check": " ".join(probe), "right": right, "decoy": decoy,
                    "producer": producer,
                    "check_accepts_right": right_got["accepted"],
                    "check_accepts_decoy": decoy_got["accepted"],
                    "check_is_blind": right_got["accepted"] and decoy_got["accepted"],
                    "witness_status": got["status"], "witness_held": got["held"],
                    "bound": got["bound"], "decoys_in_delta": got["decoys_in_delta"],
                    "invariants": got["invariants"],
                    "bound_to_right": got["bound"] == [right],
                    "decoy_not_credited": decoy not in got["bound"],
                    "bytes_in_delta": got["delta"]["created"],
                })
    return {
        "probes": len(rows),
        "checks_still_blind": sum(1 for r in rows if r["check_is_blind"]),
        "witnessed": sum(1 for r in rows if r["witness_held"]),
        "bound_to_right": sum(1 for r in rows if r["bound_to_right"]),
        "decoy_credited": sum(1 for r in rows if not r["decoy_not_credited"]),
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# 3. Controls in both error directions, plus the wrong-memory control
# --------------------------------------------------------------------------- #

def controls() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    # (a) FALSE DONE: the goal is already satisfied and the action changes nothing.
    for kind, probes in audit.WHICH_PROBES.items():
        with tempfile.TemporaryDirectory(prefix="false-done-") as where:
            root = pathlib.Path(where) / "room"
            _base_room(root)
            right, _ = _fixture(root, kind, "right")
            decoy, _ = _fixture(root, kind, "decoy")
            before = rw.digest(root)
            no_op = guide.run(["true"], root)             # changes no bytes
            after = rw.digest(root)
            got = guide.run(_check_argv(probes[0], right), root)
            checks = [{"check": " ".join(probes[0]), "held": got["accepted"], "path": right}]
            verdict = rw.witness(before, after, checks, decoys=[decoy], argv=["true"],
                                 reread=_reread(root))
            rows.append({"control": "FALSE_DONE", "kind": kind,
                         "action_accepted": no_op["accepted"],
                         "status": verdict["status"], "refused": not verdict["held"],
                         "invariants": verdict["invariants"]})

    # (b) ALL-REJECT: no check holds. Must not be reported as a false done.
    with tempfile.TemporaryDirectory(prefix="all-reject-") as where:
        root = pathlib.Path(where) / "room"
        _base_room(root)
        before = rw.digest(root)
        right, producer = _fixture(root, "gzip", "right")
        after = rw.digest(root)
        checks = [{"check": "gzip -t", "held": False, "path": right}]
        verdict = rw.witness(before, after, checks, argv=producer, reread=_reread(root))
        rows.append({"control": "ALL_REJECT", "status": verdict["status"],
                     "refused": not verdict["held"],
                     "names_the_real_defect": verdict["status"] == "REFUSED__NO_HELD_CHECK"})

    # (c) VALID ALTERNATIVES: a different producer and a different output name must still
    #     witness. Over-rejection is the frontier's dominant verifier error (VerifierBench).
    for label, producer, right in (
        ("ALTERNATE_PRODUCER", ["sh", "-c", "gzip -c payload.txt > payload.txt.gz"],
         "payload.txt.gz"),
        ("ALTERNATE_NAME", ["cp", "other.txt.gz", "renamed.gz"], "renamed.gz"),
    ):
        with tempfile.TemporaryDirectory(prefix="alt-") as where:
            root = pathlib.Path(where) / "room"
            _base_room(root)
            decoy, _ = _fixture(root, "gzip", "decoy")
            if label == "ALTERNATE_NAME":
                # renamed.gz needs a real source .gz that is NOT the decoy.
                shutil.copyfile(root / "payload.txt", root / "seed.txt")
                guide.run(["gzip", "-kf", "seed.txt"], root)
                producer = ["cp", "seed.txt.gz", "renamed.gz"]
            before = rw.digest(root)
            got_action = guide.run(producer, root)
            after = rw.digest(root)
            got = guide.run(_check_argv(["gzip", "-t"], right), root)
            checks = [{"check": "gzip -t", "held": got["accepted"], "path": right}]
            verdict = rw.witness(before, after, checks, decoys=[decoy], argv=producer,
                                 reread=_reread(root))
            rows.append({"control": label, "action_accepted": got_action["accepted"],
                         "check_held": got["accepted"], "status": verdict["status"],
                         "witnessed": verdict["held"], "bound": verdict["bound"],
                         "bound_to_right": verdict["bound"] == [right]})

    # (d) AMBIGUITY: the action changes both the right object and a same-kind decoy.
    with tempfile.TemporaryDirectory(prefix="ambiguous-") as where:
        root = pathlib.Path(where) / "room"
        _base_room(root)
        before = rw.digest(root)
        guide.run(["gzip", "-kf", "payload.txt"], root)
        guide.run(["gzip", "-kf", "other.txt"], root)
        after = rw.digest(root)
        got = guide.run(["gzip", "-t", "payload.txt.gz"], root)
        checks = [{"check": "gzip -t", "held": got["accepted"], "path": "payload.txt.gz"}]
        verdict = rw.witness(before, after, checks, decoys=["other.txt.gz"],
                             argv=["gzip", "-kf", "payload.txt | gzip -kf other.txt"],
                             reread=_reread(root))
        rows.append({"control": "AMBIGUOUS_DECOYS", "status": verdict["status"],
                     "refused": not verdict["held"],
                     "decoys_in_delta": verdict["decoys_in_delta"]})

    # (e) WRONG MEMORY: a stored rule names the untouched decoy as the checked object.
    with tempfile.TemporaryDirectory(prefix="wrong-memory-") as where:
        root = pathlib.Path(where) / "room"
        _base_room(root)
        decoy, _ = _fixture(root, "gzip", "decoy")
        before = rw.digest(root)
        right, producer = _fixture(root, "gzip", "right")
        after = rw.digest(root)
        checks = [{"check": "gzip -t", "held": True, "path": decoy}]
        verdict = rw.witness(before, after, checks, decoys=[decoy], argv=producer,
                             reread=_reread(root))
        rows.append({"control": "WRONG_STORED_BINDING", "right": right, "decoy": decoy,
                     "status": verdict["status"], "refused": not verdict["held"],
                     "decoy_credited": decoy in verdict["bound"]})

    # (f) STATE DRIFT: the bound object's bytes move between the action and the check.
    with tempfile.TemporaryDirectory(prefix="drift-") as where:
        root = pathlib.Path(where) / "room"
        _base_room(root)
        decoy, _ = _fixture(root, "gzip", "decoy")
        before = rw.digest(root)
        right, producer = _fixture(root, "gzip", "right")
        after = rw.digest(root)
        (root / right).write_bytes(b"moved after the action\n")
        checks = [{"check": "gzip -t", "held": True, "path": right}]
        verdict = rw.witness(before, after, checks, decoys=[decoy], argv=producer,
                             reread=_reread(root))
        rows.append({"control": "STATE_DRIFT", "status": verdict["status"],
                     "refused": not verdict["held"], "drift": verdict["drift"]})

    return {"rows": rows,
            "false_done_refused": sum(1 for r in rows if r["control"] == "FALSE_DONE"
                                      and r["refused"]),
            "false_done_cases": sum(1 for r in rows if r["control"] == "FALSE_DONE"),
            "all_reject_named": sum(1 for r in rows if r["control"] == "ALL_REJECT"
                                    and r["names_the_real_defect"]),
            "alternatives_witnessed": sum(1 for r in rows
                                          if r["control"].startswith("ALTERNATE")
                                          and r["witnessed"]),
            "alternatives": sum(1 for r in rows if r["control"].startswith("ALTERNATE")),
            "ambiguous_refused": sum(1 for r in rows if r["control"] == "AMBIGUOUS_DECOYS"
                                     and r["refused"]),
            "wrong_memory_refused": sum(1 for r in rows
                                        if r["control"] == "WRONG_STORED_BINDING"
                                        and r["refused"]),
            "drift_refused": sum(1 for r in rows if r["control"] == "STATE_DRIFT"
                                 and r["refused"])}


# --------------------------------------------------------------------------- #
# 4. Destroyed bytes are CHANGED, never INERT -- derived, not listed
# --------------------------------------------------------------------------- #

def destroyer_status_round() -> dict[str, Any]:
    """Find byte-mutating check flags by running them, then ask the byte-derived status."""
    names = ("shred", "stream", "stream-im6", "split", "ln", "wdctl", "truncate", "rm")
    pages: dict[str, Any] = {}
    for name in names:
        page = guide.page_of(name)
        # The SHIPPED rule, not the repaired one: this round measures the status of exactly the
        # candidates the last round caught writing bytes, so the two receipts are comparable.
        page["checks"] = audit.shipped_rule(page["declared"])
        pages[name] = page
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="destroy-") as where:
        template = pathlib.Path(where) / "room"
        guide.make_room(template)
        found = audit.certification_audit(pages, template, ["payload.txt"])
        for row in found["writer_detail"]:
            program, flag = row["check"].split(" ", 1)
            with tempfile.TemporaryDirectory(prefix="one-destroy-") as inner:
                root = pathlib.Path(inner) / "room"
                shutil.copytree(template, root)
                before = rw.digest(root)
                got = guide.run([program, flag, "payload.txt"], root)
                after = rw.digest(root)
                status = rw.status_of(before, after, got["accepted"])
                rows.append({"check": row["check"], "changed": row["changed"],
                             "accepted": got["accepted"], **status})
    return {"candidates_measured": found["certified"], "writers_found": found["writers"],
            "bytes_destroyed_reported_inert": sum(1 for r in rows
                                                  if r["accepted"] and r["changed"]
                                                  and r["status"] == "ACCEPTED_INERT"),
            "accepted_destroyers": sum(1 for r in rows if r["accepted"] and r["changed"]),
            "rows": rows}


# --------------------------------------------------------------------------- #
# 5. Thin machine: producers chosen after the rule was frozen
# --------------------------------------------------------------------------- #

def transfer_round() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for spec in TRANSFER_PRODUCERS:
        program = spec["check"].split()[0]
        if shutil.which(program) is None or shutil.which(spec["argv"].split()[0]) is None:
            rows.append({"producer": spec["producer"], "status": "UNAVAILABLE_ON_THIS_MACHINE"})
            continue
        with tempfile.TemporaryDirectory(prefix="transfer-") as where:
            root = pathlib.Path(where) / "room"
            _base_room(root)
            # a decoy of the same kind, made by the same producer, present BEFORE the action
            decoy_argv = spec["argv"].replace("payload.txt", "other.txt")
            if spec["producer"] == "cp":
                decoy_argv = "cp other.txt other.out"
            guide.run(decoy_argv.split(), root)
            before = rw.digest(root)
            action = guide.run(spec["argv"].split(), root)
            after = rw.digest(root)
            got = guide.run([*spec["check"].split(), spec["right"]], root)
            decoy_got = guide.run([*spec["check"].split(), spec["decoy"]], root)
            checks = _check_rows(spec["check"], spec["right"], spec["decoy"],
                                 got["accepted"], decoy_got["accepted"])
            verdict = rw.witness(before, after, checks, decoys=[spec["decoy"]],
                                 argv=spec["argv"].split(), reread=_reread(root))
            rows.append({"producer": spec["producer"], "action_accepted": action["accepted"],
                         "check_held": got["accepted"],
                         "check_accepts_decoy": decoy_got["accepted"],
                         "status": verdict["status"], "witnessed": verdict["held"],
                         "bound": verdict["bound"],
                         "bound_to_right": verdict["bound"] == [spec["right"]]})
    available = [r for r in rows if r["status"] != "UNAVAILABLE_ON_THIS_MACHINE"]
    return {"producers_tried": len(rows), "producers_available": len(available),
            "witnessed": sum(1 for r in available if r["witnessed"]),
            "bound_to_right": sum(1 for r in available if r["bound_to_right"]),
            "rows": rows}


# --------------------------------------------------------------------------- #
# 6. Gates, declared before the run
# --------------------------------------------------------------------------- #

def judged(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    w = report["which_object"]
    c = report["controls"]
    d = report["destroyers"]
    t = report["transfer"]

    def gate(claimed: str, measured: str, ok: bool) -> dict[str, Any]:
        return {"claimed": claimed, "measured": measured, "MET": bool(ok)}

    return {
        "W1_the_check_is_still_blind": gate(
            "the eight shipped which-object probes still accept a same-kind decoy; this round "
            "does not claim to have repaired the check",
            f"{w['checks_still_blind']}/{w['probes']} accept both objects",
            w["probes"] == 8 and w["checks_still_blind"] == 8),
        "W2_the_witness_binds_to_the_action": gate(
            "on all eight blind probes the witness binds to the object the action produced and "
            "credits zero untouched decoys",
            f"{w['bound_to_right']}/{w['probes']} bound to right, {w['decoy_credited']} decoys credited",
            w["bound_to_right"] == 8 and w["decoy_credited"] == 0 and w["witnessed"] == 8),
        "W3_false_done_is_refused": gate(
            "a goal already satisfied before a no-op action is never claimed as that action's success",
            f"{c['false_done_refused']}/{c['false_done_cases']} refused",
            c["false_done_cases"] == 4 and c["false_done_refused"] == 4),
        "W4_all_reject_is_named": gate(
            "an all-reject verifier is reported as no held check, not as a false done",
            f"{c['all_reject_named']}/1 named correctly",
            c["all_reject_named"] == 1),
        "W5_no_over_rejection": gate(
            "a valid alternative producer and a different output name both still witness",
            f"{c['alternatives_witnessed']}/{c['alternatives']} witnessed",
            c["alternatives"] == 2 and c["alternatives_witnessed"] == 2),
        "W6_ambiguity_and_wrong_memory_refused": gate(
            "an action that changes two same-kind objects, and a stored binding that names the "
            "untouched decoy, are both refused",
            f"ambiguous {c['ambiguous_refused']}/1, wrong memory {c['wrong_memory_refused']}/1, "
            f"drift {c['drift_refused']}/1",
            c["ambiguous_refused"] == 1 and c["wrong_memory_refused"] == 1
            and c["drift_refused"] == 1),
        "W7_destroyed_bytes_are_changed": gate(
            "no accepted check that destroys bytes is reported ACCEPTED_INERT",
            f"{d['bytes_destroyed_reported_inert']} of {d['accepted_destroyers']} accepted "
            f"destroyers reported INERT",
            d["writers_found"] > 0 and d["bytes_destroyed_reported_inert"] == 0),
        "W8_transfer_to_frozen_out_producers": gate(
            "the rule binds on at least two producers that were chosen after the rule was frozen",
            f"{t['witnessed']}/{t['producers_available']} available producers witnessed",
            t["producers_available"] >= 2 and t["witnessed"] == t["producers_available"]),
        "W9_zero": gate(
            "zero model calls, zero stored parameters, zero network at measure time",
            f"{report['cost']['model_calls']}/{report['cost']['parameters_stored']}/"
            f"{report['cost']['network_calls_at_run_time']}",
            report["cost"]["model_calls"] == 0
            and report["cost"]["parameters_stored"] == 0
            and report["cost"]["network_calls_at_run_time"] == 0),
    }


def measure() -> dict[str, Any]:
    started = time.time()
    report: dict[str, Any] = {
        "which_object": which_object_round(),
        "controls": controls(),
        "destroyers": destroyer_status_round(),
        "transfer": transfer_round(),
    }
    report["cost"] = {"seconds": round(time.time() - started, 1), "model_calls": 0,
                      "parameters_stored": 0, "network_calls_at_run_time": 0}
    report["verdict"] = judged(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, default=DEFAULT_RECEIPT)
    options = parser.parse_args(argv)
    report = measure()
    receipt = {
        "schema": SCHEMA, "authority": AUTHORITY, "date": DATE,
        "mode": "A_CHECK_IS_CREDITED_ONLY_FOR_THE_BYTES_THIS_ACTION_CHANGED",
        "declared_before_the_run": {k: v["claimed"] for k, v in report["verdict"].items()},
        "verdict": report["verdict"],
        **{k: v for k, v in report.items() if k != "verdict"},
        "what_this_is_not": [
            "not a repaired check: all eight probes still accept an untouched decoy",
            "not a benchmark result: no OSWorld, SWE-bench Pro, FrontierSWE or Terminal-Bench task was run",
            "not a claim that a goal naming only a kind can identify its object; a goal that "
            "names no object can still be witnessed on whichever object the action produced",
            "not a blacklist: the destroyer set is found by running flags, not by naming programs "
            "in the mechanism",
            "not independent verification: one producer, one machine, no separate verifier",
        ],
        "limits": [
            "the fixture producers for zip and json are Python stdlib writes, not programs read "
            "from a page; the check programs are the machine's own",
            "delta is over regular files only; a FIFO, a device or a symlink is not an object here",
            "a check whose target is a directory is bound through the files inside it, not the "
            "directory entry itself",
            "an action that changes only metadata (mode, mtime) changes no content digest and is "
            "correctly reported as INERT",
        ],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1, default=str) + "\n",
                               encoding="utf-8")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(json.dumps({
        "probes": receipt["which_object"]["probes"],
        "checks_still_blind": receipt["which_object"]["checks_still_blind"],
        "witnessed": receipt["which_object"]["witnessed"],
        "bound_to_right": receipt["which_object"]["bound_to_right"],
        "decoys_credited": receipt["which_object"]["decoy_credited"],
        "false_done_refused": receipt["controls"]["false_done_refused"],
        "destroyers_inert": receipt["destroyers"]["bytes_destroyed_reported_inert"],
        "transfer": f"{receipt['transfer']['witnessed']}/{receipt['transfer']['producers_available']}",
        "seconds": receipt["cost"]["seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
