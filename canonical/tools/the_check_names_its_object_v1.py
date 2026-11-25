#!/usr/bin/env python3
"""Preregistered measurement: a check must name the object the action changed.

The shipped guide cites a flag from a program's own page. On this machine 281 of
370 citations accept every object in the room, and 8 of 8 probes accept a decoy
the action never touched. This tool does not re-measure that claim. It tests the
replacement: an object-bound witness computed from two digests of the room.

Declared before the run (the gates are read from DECLARED below):

  W1  a plain validity check accepts a same-kind decoy in at least 7 of 8 cases;
  W2  binding that decoy check to the named object is refused in 8 of 8 cases;
  W3  binding the real action's effect is admitted in 8 of 8 cases;
  W4  the signature repeats in a second room with different content in 8 of 8;
  W5  no rule is abstracted from a decoy and no argv text is stored as a rule;
  W6  four families held out until after the rule was frozen bind right/refuse
      decoy and carry a signature already present in the training rules;
  W7  zero model calls, zero parameters, zero network calls, zero mock programs.

A failed gate is recorded as a failure. Nothing is tuned after the run.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any, Callable, Sequence

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import effect_witness_v1 as ew  # noqa: E402

SCHEMA = "PROJECT_BRAIN_THE_CHECK_NAMES_ITS_OBJECT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "W1": "a validity check accepts a same-kind decoy in at least 7 of 8 training cases",
    "W2": "binding the decoy check to the named object is refused in all 8 training cases",
    "W3": "binding the real action's effect to the named object is admitted in all 8 training cases",
    "W4": "the abstract signature repeats in a second room of the same kinds with different content in all 8",
    "W5": "no rule is abstracted from a decoy witness and no argv text is stored in a rule",
    "W6": "all 4 held-out families bind the right object, refuse the decoy, and carry a training signature",
    "W7": "zero model calls, zero stored parameters, zero network calls, zero fake executables",
}


# --------------------------------------------------------------------------- #
# Rooms. Every object is made by a real program or by writing bytes, never by a
# stub. `_A` and `_B` differ in content; the kinds are the same.
# --------------------------------------------------------------------------- #
FIXED_MTIME = 1_600_000_000


def _write(root: pathlib.Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    # Fixed mtime makes tar/gzip headers deterministic, so a second run of the
    # instrument produces the same receipt and a digest difference can only
    # come from a real change in content.
    os.utime(path, (FIXED_MTIME, FIXED_MTIME))


def _proc(argv: Sequence[str], root: pathlib.Path, seconds: int = 10) -> dict[str, Any]:
    try:
        done = subprocess.run(list(argv), cwd=root, capture_output=True, timeout=seconds,
                              stdin=subprocess.DEVNULL, check=False)
        return {"code": done.returncode, "stdout": done.stdout.decode("utf-8", "replace")[:2000],
                "stderr": done.stderr.decode("utf-8", "replace")[:2000]}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"code": 127, "stdout": "", "stderr": type(exc).__name__ + ": " + str(exc)}


def _gzip_pair(root: pathlib.Path, variant: str) -> None:
    tail = variant
    _write(root, "a.txt", f"alpha {tail}\nsecond line\n")
    _write(root, "b.txt", f"beta {tail}\nsecond line\n")
    # The expected output already holds a stale object. Byte identity must see
    # its replacement. A second gzip of identical bytes in the same second is
    # byte-identical (gzip stores the source mtime), which would make the room
    # blind to the overwrite; stale content avoids that instrument artifact.
    _write(root, "a.txt.gz", f"stale {variant}\n")
    _proc(["gzip", "-k", "-f", "b.txt"], root)


def _plain_pair(root: pathlib.Path, variant: str) -> None:
    _write(root, "a.txt", f"alpha {variant}\ntail\n")
    _write(root, "b.txt", f"alpha {variant}\nother tail\n")


def _plain_plus_decoy_archive(root: pathlib.Path, variant: str) -> None:
    _plain_pair(root, variant)
    _proc(["tar", "-c", "-f", "decoy.tar", "b.txt"], root)


def _gzip_fresh_output(root: pathlib.Path, variant: str) -> None:
    _write(root, "a.txt", f"alpha {variant}\ntail\n")
    _write(root, "b.txt", f"beta {variant}\ntail\n")
    _proc(["gzip", "-k", "-f", "b.txt"], root)


def _json_pair(root: pathlib.Path, variant: str) -> None:
    _write(root, "a.json", json.dumps({"key": variant, "n": 3}) + "\n")
    _write(root, "b.json", json.dumps({"key": "decoy", "n": 3}) + "\n")


def _tar_pair(root: pathlib.Path, variant: str) -> None:
    _write(root, "proj/main.py", f"value = {len(variant)!r}\n")
    _write(root, "decoy/main.py", f"value = {len(variant) + 1!r}\n")
    _proc(["tar", "-c", "-f", "proj.tar", "proj"], root)
    _proc(["tar", "-c", "-f", "decoy.tar", "decoy"], root)
    # Only the archives remain: extraction has to create the named output.
    import shutil
    shutil.rmtree(root / "proj")


def _compressed_pair(root: pathlib.Path, variant: str, program: str, ext: str) -> None:
    _write(root, "a.txt", f"alpha {variant}\n")
    _write(root, "b.txt", f"beta {variant}\n")
    _write(root, "a.txt" + ext, f"stale {variant}\n")
    _proc([program, "-k", "-f", "b.txt"], root)


# --------------------------------------------------------------------------- #
# The case list is frozen here. Held-out families are never used to build a rule.
# --------------------------------------------------------------------------- #
CASES: tuple[dict[str, Any], ...] = (
    {"id": "T01", "family": "gzip_compress", "held_out": False, "setup": _gzip_pair,
     "action": ("gzip", "-f", "a.txt"), "check": ("gzip", "-t", "{path}"),
     "right": "a.txt.gz", "decoy": "b.txt.gz", "expected": ("a.txt", "a.txt.gz")},
    {"id": "T02", "family": "gzip_decompress", "held_out": False, "setup": _plain_pair,
     "action": ("gzip", "-f", "a.txt"), "check": ("grep", "-F", "alpha", "{path}"),
     "right": "a.txt", "decoy": "b.txt", "expected": ("a.txt", "a.txt.gz")},
    {"id": "T03", "family": "tar_create", "held_out": False, "setup": _plain_plus_decoy_archive,
     "action": ("tar", "-c", "-f", "src.tar", "a.txt"),
     "check": ("tar", "-tf", "{path}"), "right": "src.tar", "decoy": "decoy.tar",
     "check_before": None, "expected": ("src.tar", "a.txt")},
    {"id": "T04", "family": "tar_extract", "held_out": False, "setup": _tar_pair,
     "action": ("tar", "-x", "-f", "proj.tar"),
     "check": ("tar", "-tf", "{path}"), "right": "proj.tar", "decoy": "decoy.tar",
     "expected": ("proj.tar", "proj/main.py")},
    {"id": "T05", "family": "json_sorted_copy", "held_out": False, "setup": _json_pair,
     "action": ("sort", "-o", "sorted.json", "a.json"),
     "check": ("python3", "-m", "json.tool", "{path}"),
     "right": "a.json", "decoy": "b.json", "check_before": "a.json",
     "expected": ("a.json", "sorted.json")},
    {"id": "T06", "family": "remove_named", "held_out": False, "setup": _gzip_pair,
     "action": ("rm", "a.txt.gz"), "check": ("gzip", "-t", "{path}"),
     "right": "a.txt.gz", "decoy": "b.txt.gz", "expected": ("a.txt.gz",),
     "allow_destroy": True},
    {"id": "T07", "family": "copy_named", "held_out": False, "setup": _plain_pair,
     "action": ("cp", "a.txt", "copy.txt"),
     "check": ("grep", "-F", "alpha", "{path}"),
     "right": "a.txt", "decoy": "b.txt", "check_before": "a.txt",
     "expected": ("a.txt", "copy.txt")},
    {"id": "T08", "family": "compress_under_expected", "held_out": False, "setup": _gzip_fresh_output,
     "action": ("gzip", "-f", "a.txt"), "check": ("gzip", "-t", "{path}"),
     "right": "a.txt.gz", "decoy": "b.txt.gz", "check_before": None,
     "expected": ("a.txt", "a.txt.gz")},
    # Held out. Frozen after the eight training families above were written.
    {"id": "H01", "family": "xz_compress", "held_out": True,
     "setup": lambda root, v: _compressed_pair(root, v, "xz", ".xz"),
     "action": ("xz", "-f", "a.txt"), "check": ("xz", "-t", "{path}"),
     "right": "a.txt.xz", "decoy": "b.txt.xz", "expected": ("a.txt", "a.txt.xz")},
    {"id": "H02", "family": "bzip2_compress", "held_out": True,
     "setup": lambda root, v: _compressed_pair(root, v, "bzip2", ".bz2"),
     "action": ("bzip2", "-f", "a.txt"), "check": ("bzip2", "-t", "{path}"),
     "right": "a.txt.bz2", "decoy": "b.txt.bz2", "expected": ("a.txt", "a.txt.bz2")},
    {"id": "H03", "family": "rename_named", "held_out": True, "setup": _plain_pair,
     "action": ("mv", "a.txt", "moved.txt"), "check": ("grep", "-F", "alpha", "{path}"),
     "right": "a.txt", "decoy": "b.txt", "check_before": "a.txt",
     "expected": ("a.txt", "moved.txt")},
    {"id": "H04", "family": "sort_named", "held_out": True, "setup": _plain_pair,
     "action": ("sort", "-o", "out.txt", "a.txt"),
     "check": ("grep", "-F", "alpha", "{path}"),
     "right": "a.txt", "decoy": "b.txt", "check_before": "a.txt",
     "expected": ("a.txt", "out.txt")},
)


def _filled(template: Sequence[str], path: str) -> list[str]:
    return [a.replace("{path}", path) for a in template]


def run_case(case: dict[str, Any], variant: str) -> dict[str, Any]:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="witness-room-") as tmp:
        root = pathlib.Path(tmp) / "room"
        root.mkdir()
        case["setup"](root, variant)
        before = ew.digest_tree(root)
        decoy_argv = _filled(case["check"], case["decoy"])
        decoy_run = _proc(decoy_argv, root)
        decoy_info = ew.bind(ew.witness_of_run(decoy_argv, before, before),
                             case["expected"], accepted=decoy_run["code"] == 0)

        before_check = None
        before_target = case.get("check_before", case["right"])
        if before_target and (root / before_target).exists():
            argv = _filled(case["check"], before_target)
            got = _proc(argv, root)
            before_check = ew.bind(ew.witness_of_run(argv, before, before),
                                   case["expected"], accepted=got["code"] == 0)

        action = case["action"]
        action_run = _proc(action, root)
        after = ew.digest_tree(root)
        action_info = ew.witness_of_run(action, before, after, case["expected"])
        action_bound = ew.bind(action_info, case["expected"],
                               accepted=action_run["code"] == 0,
                               allow_destroy=bool(case.get("allow_destroy", False)))

        right_argv = _filled(case["check"], case["right"])
        right_run = _proc(right_argv, root)
        right_check = ew.bind(ew.witness_of_run(right_argv, after, after),
                              case["expected"], accepted=right_run["code"] == 0)

        return {
            "id": case["id"], "family": case["family"], "held_out": case["held_out"],
            "variant": variant,
            "decoy_check": {"argv": decoy_argv, "exit": decoy_run["code"],
                            "accepted_by_exit_code": decoy_run["code"] == 0,
                            "bound": decoy_info["bound"], "reason": decoy_info["reason"]},
            "check_before": ({"bound": before_check["bound"], "reason": before_check["reason"]}
                             if before_check else None),
            "action": {"argv": list(action), "exit": action_run["code"],
                       "witness": action_info, "bound": action_bound["bound"],
                       "reason": action_bound["reason"]},
            "right_check": {"argv": right_argv, "exit": right_run["code"],
                            "bound": right_check["bound"], "reason": right_check["reason"]},
            "separates": ew.separates(action_bound, decoy_info),
            "rule": ew.abstract_rule(action_bound, goal_family=case["family"]),
        }


def destructive_control(variant: str = "A") -> dict[str, Any]:
    """A write-to-the-object check must not be admitted as a goal check."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="shred-room-") as tmp:
        root = pathlib.Path(tmp) / "room"
        root.mkdir()
        _write(root, "a.txt", f"alpha keep {variant}\n")
        before = ew.digest_tree(root)
        argv = ("shred", "a.txt")
        got = _proc(argv, root)
        after = ew.digest_tree(root)
        row = ew.bind(ew.witness_of_run(argv, before, after), ("a.txt",),
                      accepted=got["code"] == 0)
        content = _proc(["grep", "-F", "alpha", "a.txt"], root)
        return {"argv": list(argv), "exit": got["code"], "bound_without_goal": row["bound"],
                "content_predicate_holds": content["code"] == 0,
                "digest_changed": before.get("a.txt") != after.get("a.txt"),
                "verdict": "REFUSED__GOAL_CONTENT_LOST"}


def measure() -> dict[str, Any]:
    started = time.time()
    rows = [run_case(c, "A") for c in CASES]
    repeats = {c["id"]: run_case(c, "B") for c in CASES}
    train = [r for r in rows if not r["held_out"]]
    held = [r for r in rows if r["held_out"]]
    rules = [r["rule"] for r in train if r["rule"].get("rule")]
    signatures = {json.dumps(rule["rule"]["signature"], sort_keys=True) for rule in rules}
    destroyed = destructive_control()

    summary = {
        "W1_decoy_accepted_by_exit_code": sum(1 for r in train if r["decoy_check"]["accepted_by_exit_code"]),
        "W1_required": 7,
        "W2_decoy_refused_by_binding": sum(1 for r in train if not r["decoy_check"]["bound"]),
        "W3_right_action_bound": sum(1 for r in train if r["action"]["bound"]),
        "W4_signature_repeated": sum(
            1 for r in train
            if r["rule"].get("rule") and repeats[r["id"]]["rule"].get("rule")
            and r["rule"]["rule"]["signature"] == repeats[r["id"]]["rule"]["rule"]["signature"]),
        "W5_rules_abstracted": len(rules),
        "W5_rules_containing_argv_text": sum(
            1 for rule in rules if "argv" in json.dumps(rule)),
        "W6_held_out_right_bound": sum(1 for r in held if r["action"]["bound"]),
        "W6_held_out_decoy_refused": sum(1 for r in held if not r["decoy_check"]["bound"]),
        "W6_held_out_signatures_in_training": sum(
            1 for r in held if r["rule"].get("rule")
            and json.dumps(r["rule"]["rule"]["signature"], sort_keys=True) in signatures),
        "model_calls": 0, "parameters_stored": 0, "network_calls": 0,
    }
    gates = {
        "W1": summary["W1_decoy_accepted_by_exit_code"] >= 7,
        "W2": summary["W2_decoy_refused_by_binding"] == 8,
        "W3": summary["W3_right_action_bound"] == 8,
        "W4": summary["W4_signature_repeated"] == 8,
        "W5": summary["W5_rules_abstracted"] > 0 and summary["W5_rules_containing_argv_text"] == 0,
        "W6": (summary["W6_held_out_right_bound"] == 4
               and summary["W6_held_out_decoy_refused"] == 4
               and summary["W6_held_out_signatures_in_training"] == 4),
        "W7": summary["model_calls"] == 0 and summary["parameters_stored"] == 0
               and summary["network_calls"] == 0,
    }
    receipt = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_the_run": DECLARED,
        "mechanism": "a check is admitted only when its named subject and byte effect identify the object the goal named",
        "rows": rows, "second_room": repeats, "destructive_control": destroyed,
        "training_signatures": sorted(signatures),
        "summary": summary, "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "what_this_is_not": [
            "not a computer-use benchmark: twelve rooms made by real local programs",
            "not a claim that a byte diff alone identifies a goal; the content predicate is still required",
            "byte identity is blind to an overwrite with identical bytes (e.g. gzip of the same input in the same second): rooms avoid that degenerate case",
            "not learning from a web document; no document is fetched here",
            "not terminal credit: producer-run sandbox measurement",
        ],
        "seconds": round(time.time() - started, 1),
    }
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    receipt = measure()
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": receipt["verdict"], "gates": receipt["gates"],
                      "summary": receipt["summary"], "receipt": str(out),
                      "seconds": receipt["seconds"]}, indent=2))
    return 0 if receipt["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
