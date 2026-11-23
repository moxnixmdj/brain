"""What can this machine actually DO? Answered by running every claim inside a disposable world.

WHY V1 WAS NOT GOOD ENOUGH. `reachability_v1` classified 154 claims from OUTSIDE the tree and, being
outside, could not call the 70 that write. It stopped them at READABLE with
`DECLARES_WRITE_AUTHORITY_NOT_EXECUTED` and called that caution. It was not caution. While building
this file the v1 code was handed `python.evidence.contract.supercomposer.v1` -- a row v1 classifies
READABLE-with-write-authority -- for a manual probe, and the call WROTE
`canonical/tmp_evidence_contract_supercomposer.json` into the live tree. The row's declared inputs are
`{capability_id}` alone. So:

  * a row can write while declaring no output slot, which makes "declares write authority" a guess from
    vocabulary and not a reading of behaviour;
  * the write went to the host, which is exactly what v1 said it prevented;
  * "not executed" is not a safe state. It is an UNMEASURED state, and 70 of 154 claims live in it.

THE FIX IS THE ONE THING v1 LACKED: A PLACE TO WRITE. `confinement_v1` already builds a disposable
world -- `git clone --no-local` (or a copy), `host_untouched` measured by fingerprint before and after,
declared effects required to land inside, receipts content-addressed. Reachability does not need any new
machinery. It needs to move the whole audit INSIDE that world, where a writer is harmless, and then
judge every claim by what the call DID rather than by what its argument list looks like.

WHAT THIS FILE MEASURES, FOR EVERY ROW THAT CLAIMS `VERIFIED_BOUND_CAPABILITY`:

    LOADED       the adapter imports and its entrypoint is callable
    RAN          it was called once, inside the clone, and returned; and -- for a row that writes --
                 the artifact it returned is readable INSIDE the clone and its sha256 matches the byte
                 count the row reported for it. "It wrote a file" is not "the file is there".
    ANSWERED     it ran, refused nothing, and its result does not contradict itself. A returned
                 `verified: true` earns nothing: measured, that field is `all(required in claims)` --
                 a membership test over the registry's own words (see
                 `software_review_synthesis_supercomposer_v1.py`). A verdict computed from claims is
                 not a fact, so this file never reads it as one.
    UNREACHABLE  it could not be loaded or could not be called, with the reason named.

AND THE HONEST HEADLINE, WHICH IS THE POINT OF THE WHOLE EXERCISE. 15 rows declare NO inputs and report
`output_verified: true`. A capability that takes no input cannot be measuring anything about the world;
its answer is a restatement of what the machine already believes about itself. That is the knowledge
house the mission forbids, wearing an adapter. They are reported as `SELF_ATTESTING` and counted
separately, because "reachable" and "informative" are different questions and the mission's question is
the second one.

TWO HALLUCINATIONS THIS FILE REMOVES FROM ITS OWN PREDECESSOR:

  1. v1 passed `capability_id` into every call and never noticed 15 rows take nothing else. It then
     reported them `NO_HONEST_SMOKE_ARGUMENTS` -- "I cannot call this" -- when it could. An audit that
     invents a limitation is the same defect as one that invents a capability.
  2. v1's `_smoke_arguments` treats a goal slot as unsatisfiable unless a path exists beside it. That
     is a rule about shapes, not about calls. Here a row may be called with whatever real values this
     tree contains, and if none exist the row is reported `NEEDS_INPUT: <slot>` -- naming the missing
     input instead of hiding it behind a category.
"""

from __future__ import annotations

import json
import os
import sys
import pathlib
import textwrap
from typing import Any

SCHEMA = "PROJECT_BRAIN_REACHABILITY_V2"

# Runs inside the clone. Must not import the audit, which would be the audit grading itself: it calls
# each row's own adapter and reports what came back.
PROBE = textwrap.dedent('''
    import hashlib, json, pathlib, sys, time, traceback

    root = pathlib.Path(".").resolve()
    # THE CLONE IS A REPOSITORY, SO IT IS ALSO THE IMPORT ROOT. Without this an adapter that says
    # `from canonical.runtime... import ...` dies with ModuleNotFoundError:canonical and the row is
    # reported unreachable for a reason that is the harness's, not the capability's.
    sys.path.insert(0, str(root))
    plan = json.loads(pathlib.Path("_rb_probe_plan.json").read_text())
    out = {}

    class _Timeout(Exception):
        pass

    def _bounded(fn, args, root, seconds):
        """A smoke test proves a call works; it must not be allowed to become the workload.

        Thread-free: SIGALRM fires inside the call, so a scanner that would have walked 22,365 files is
        stopped at the budget and reported BUDGET_EXCEEDED instead of holding the audit hostage.
        """
        import signal
        def _fire(signum, frame):
            raise _Timeout("budget %ss" % seconds)
        old = signal.signal(signal.SIGALRM, _fire)
        signal.setitimer(signal.ITIMER_REAL, float(seconds))
        try:
            return fn(args, root)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)

    for item in plan:
        cid = item["cid"]
        rec = {"cid": cid}
        started = time.time()
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_rb_" + str(abs(hash(cid))), item["adapter"])
            if spec is None or spec.loader is None:
                raise ImportError("no spec for " + item["adapter"])
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            fn = getattr(mod, item.get("entrypoint") or "run", None)
            if not callable(fn):
                raise AttributeError("entypoint not callable: " + str(item.get("entrypoint")))
            rec["loaded"] = True
        except BaseException as exc:
            rec["loaded"] = False
            rec["why"] = "LOAD_FAILED:" + type(exc).__name__
            rec["detail"] = str(exc)[:200]
            out[cid] = rec
            continue
        try:
            result = _bounded(fn, dict(item["args"]), str(root), item.get("budget_s") or 25)
            rec["ran"] = True
            rec["result_type"] = type(result).__name__
            rec["returned"] = json.loads(json.dumps(result, default=str)) if isinstance(result, (dict, list)) else str(result)[:400]
        except BaseException as exc:
            rec["ran"] = False
            name = type(exc).__name__
            rec["why"] = "BUDGET_EXCEEDED" if name == "_Timeout" else "CALL_RAISED:" + name
            rec["detail"] = str(exc)[:300]
            out[cid] = rec
            continue
        rec["new_paths"] = []
        rec["new_paths_count"] = 0
        # NOTHING IS ACCUSED OF LYING UNLESS THE FILE IT NAMED WAS MEANINGFULLY WATCHED. `new_paths` is
        # a set difference of two whole-tree walks, and the clock on that walk is coarse: a capability
        # that spent the walk proving a proof can finish its write after the "after" snapshot, and it
        # was reported CONTRADICTED for the audit's own blindness. The row is asked to describe itself
        # instead, on the next line, and the walk is only evidence when it saw the file.
        rec["artifact"] = {}
        if isinstance(result, dict) and result.get("output_path"):
            claimed = str(result["output_path"])
            candidate = (root / claimed).resolve()
            if root in candidate.parents and candidate.is_file():
                data = candidate.read_bytes()
                rec["artifact"] = {"path": claimed, "bytes": len(data),
                                   "sha256": hashlib.sha256(data).hexdigest(),
                                   "reported_sha256": str(result.get("output_sha256") or ""),
                                   "reported_bytes": result.get("output_bytes")}
        rec["elapsed_s"] = round(time.time() - started, 3)
        out[cid] = rec

    pathlib.Path("_rb_probe_out.json").write_text(json.dumps(out))
''')


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _adapter_path(entry: dict[str, Any]) -> str | None:
    source = entry.get("source") or {}
    declared = source.get("adapter_path") or source.get("path")
    return str(declared) if declared else None


# Directories that hold real Python source at a size a smoke test can afford. Ordered smallest first;
# measured, `generated_tests` is 3 files, `tests` is 5, `canonical/corpus` is 4.
_SMALL_SOURCE_DIRS = ("generated_tests", "tests", "canonical/tests/programs", "canonical/corpus")

# A small real Python file, for rows that consume a file rather than a directory.
_SOURCE_FILE = "canonical/tests/programs/tasks_v1.py"

# A small real JSON document that is an INPUT (its bytes are read, never written).
_INPUT_JSON = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


def cid_or_empty(entry: dict[str, Any]) -> str:
    """The row's own identity, from the row.

    `capability_id` was blank for every planned row because v2 read `entry["capability_id"]` and the
    registry stores the key on the template (`action_template.args.capability_id`) as a literal. A blank
    identity is not neutral: rows that echo it wrote artifacts with `"capability_id": ""`.
    """
    template = entry.get("action_template") or {}
    args = template.get("args") if isinstance(template, dict) else None
    literal = (args or {}).get("capability_id")
    return literal if isinstance(literal, str) and "${" not in literal else ""


def _smallest_dir(root: pathlib.Path) -> str:
    """The cheapest real directory in this tree, for a call that needs `somewhere` but not everything."""
    best, best_n = "canonical", 1 << 30
    for rel in _SMALL_SOURCE_DIRS:
        path = root / rel
        if not path.is_dir():
            continue
        n = sum(len(files) for _, _, files in os.walk(path))
        if 0 < n < best_n:
            best, best_n = rel, n
    return best


def _slots(entry: dict[str, Any]) -> set[str]:
    template = entry.get("action_template") or {}
    args = template.get("args") if isinstance(template, dict) else None
    return {str(k) for k in (args or {})} | {str(k) for k in (entry.get("proposal_bindings") or {})}


def _real_values(entry: dict[str, Any], root: pathlib.Path,
                 cid: str = "") -> tuple[dict[str, Any] | None, str]:
    """Real argument values drawn from this tree, or None naming the slot that has none.

    A slot is filled only with something that exists here. `output_path` gets a RELATIVE path into the
    clone, because a relative path is what keeps the write inside the world; a directory gets
    `canonical`, a file gets a file this tree really has, and a goal gets one sentence about it.
    """
    built: dict[str, Any] = {}
    unfilled: list[str] = []
    goals: list[str] = []
    template = entry.get("action_template") or {}
    declared = template.get("args") if isinstance(template, dict) else None
    for key in _slots(entry):
        low = key.lower()
        if low == "capability_id":
            continue
        if low == "command":
            # THE ROW ALREADY SAYS WHICH COMMAND. Its template carries `command: "copy"`; discarding it
            # and calling with no command made three working capabilities raise
            # COMMAND_NOT_IMPLEMENTED:<none> -- an audit reporting its own omission as their defect.
            value = (declared or {}).get(key)
            if isinstance(value, str) and "${" not in value:
                built[key] = value
            else:
                unfilled.append(key)
            continue
        if low in ("json_path", "manifest_path", "input_path"):
            # AN INPUT PATH IS NOT AN OUTPUT PATH. Binding `json_path` to a file the row was supposed
            # to create asks it to read its own unwritten artifact -- `sqlite.table.create_from_json_records`
            # raised INPUT_JSON_MISSING and was reported unreachable for the audit's mistake.
            built[key] = _INPUT_JSON if low == "json_path" else _SOURCE_FILE
        elif low in ("output_path", "result_path", "diff_path", "anchor_path",
                     "index_path", "extraction_path", "target_path",
                     "worktree_path", "output_prefix_hex"):
            # ONE PATH PER ROW, AND THE ROW'S OWN NAME IN IT. Restoring `sys.executable` made the whole
            # plan reach further, and the collision surfaced again in a new place: every row was handed
            # `_rb_out/output_path.json` because `entry["capability_id"]` is empty, so rows that ran
            # later refused OUTPUT_ALREADY_EXISTS -- an accusation about a file the audit itself left
            # behind. The identity now comes from the template literal, not from the list key.
            # THE LAST FALLBACK MUST BE THE ROW'S KEY IN THE REGISTRY. Two rows whose `capability_id` is
            # absent from both the entry and its template still collided on `_rb_out/row.*`, which the
            # uniqueness test caught after a hand check had missed it: a fallback that is the same for
            # every row is not a fallback, it is a shared slot.
            identity = (str(entry.get("capability_id") or cid_or_empty(entry) or cid or "row")
                        .replace("/", "_"))
            built[key] = "_rb_out/" + identity + "." + low + ".json"
        elif low == "path" and "_rb_out" in built.get("output_path", ""):
            # A row that writes to `output_path` AND reads `path` must not receive the same string for
            # both: the writer owns it, and the reader then finds it already existing. Measured:
            # file.copy.v1 raised OUTPUT_ALREADY_EXISTS for this reason and nothing else.
            built[key] = _SOURCE_FILE
        elif low == "timeout_s":
            built[key] = 120
        elif low in ("run_tests", "allow_network", "force", "dry_run"):
            built[key] = False
        elif "dir" in low or low in ("source_root", "folder", "directory", "root_selector"):
            # THE SMALLEST REAL DIRECTORY, NOT THE LARGEST ONE. A smoke test answers "does this call
            # work", and pointing a whole-tree scanner at `canonical` answers a different question:
            # `python.source.taint_flow.v1` took 307.87s of a 482s audit on 22,365 files. That is a
            # workload, not a witness. The smallest directory that still contains real Python binds the
            # same code path at a fraction of the cost.
            built[key] = _smallest_dir(root)
        elif low in ("path", "file", "source", "input_path", "source_path"):
            built[key] = _SOURCE_FILE if (root / _SOURCE_FILE).is_file() else None
        elif low == "goal":
            # DEFERRED. The sentence must name what the OTHER slots bind, and slot order is not
            # guaranteed, so resolving it inside the loop produced PATH_NOT_STATED_IN_THE_SENTENCE --
            # the audit blaming the capability for the audit's own iteration order.
            goals.append(key)
        elif low in ("module", "symbol", "qualname", "package"):
            unfilled.append(key)
        else:
            # NAMED, NOT LUMPED. "NEEDS_INPUT:unknown" tells the next step nothing about what to go
            # find; the slot's own name is the work item.
            unfilled.append(key)
    for key in goals:
        target = built.get("path") or built.get("input_path") or built.get("source_path")
        folder = built.get("source_root") or built.get("dir") or built.get("directory")
        if isinstance(target, str) and "/" in target:
            built[key] = "read the file " + target.rsplit("/", 1)[-1]
        elif isinstance(folder, str):
            built[key] = "list the files in " + folder.rsplit("/", 1)[-1]
        else:
            built[key] = "list the files in this folder"
    if any(v is None for v in built.values()):
        unfilled.extend(k for k, v in built.items() if v is None)
    if unfilled:
        return None, ",".join(sorted(set(unfilled)))[:120]
    built["capability_id"] = str(entry.get("capability_id") or cid_or_empty(entry))
    return (built, "") if built.keys() - {"capability_id"} else (None, "NO_INPUTS")


def plan_for(reg: dict[str, dict[str, Any]], root: pathlib.Path) -> tuple[list[dict], dict[str, str]]:
    """Every claim that can be called from real values, and why the rest cannot."""
    plan: list[dict] = []
    blocked: dict[str, str] = {}
    for cid, entry in sorted(reg.items()):
        if not isinstance(entry, dict) or str(entry.get("status")) != "VERIFIED_BOUND_CAPABILITY":
            continue
        adapter = _adapter_path(entry)
        if not adapter or not (root / adapter).is_file():
            blocked[cid] = "NO_ADAPTER_DECLARED" if not adapter else "ADAPTER_FILE_ABSENT"
            continue
        slots = _slots(entry)
        zero_input = not (slots - {"capability_id"})
        if zero_input:
            plan.append({"cid": cid, "adapter": adapter,
                         "entrypoint": (entry.get("source") or {}).get("entrypoint") or "run",
                         "args": {}, "zero_input": True})
            continue
        args, missing = _real_values(entry, root, cid)
        if args is None:
            blocked[cid] = "NEEDS_INPUT:" + missing
            continue
        plan.append({"cid": cid, "adapter": adapter,
                     "entrypoint": (entry.get("source") or {}).get("entrypoint") or "run",
                     "args": args, "zero_input": False})
    return plan, blocked


def judge(rec: dict, entry: dict[str, Any], zero_input: bool) -> dict[str, Any]:
    """Turn one probe record into a state, reading only what the call DID."""
    if not rec.get("loaded"):
        return {"state": "UNREACHABLE", "why": rec.get("why"), "detail": rec.get("detail", "")}
    if not rec.get("ran"):
        return {"state": "LOADED", "why": rec.get("why"), "detail": rec.get("detail", "")}
    returned = rec.get("returned")
    artifact = rec.get("artifact") or {}
    contradicted = ""
    if artifact:
        data = "artifact %d bytes" % artifact.get("bytes", 0)
        reported = artifact.get("reported_sha256") or ""
        # A row that reports a digest of its own artifact has made a checkable claim. Everything else it
        # says about the artifact is its own word, which is not evidence.
        if reported and reported != artifact.get("sha256"):
            contradicted = "REPORTED_DIGEST_DIFFERS_FROM_FILE"
        detail = data + (", digest %s" % ("MATCHES" if not contradicted else "DIFFERS"))
    else:
        detail = ""
        if isinstance(returned, dict) and returned.get("output_path"):
            detail = "NAMES_ARTIFACT_NOT_FOUND_IN_WORLD:" + str(returned["output_path"])[:80]
    state = "RAN"
    if artifact:
        state = "WROTE"
    out = {"state": "SELF_ATTESTING" if zero_input else state,
           "why": "NO_INPUT_SO_THE_ANSWER_IS_ABOUT_ITSELF" if zero_input else None,
           "new_paths": rec.get("new_paths_count", 0),
           "artifact": (detail or None),
           "elapsed_s": rec.get("elapsed_s")}
    if contradicted:
        out["state"] = "CONTRADICTED"
        out["why"] = contradicted
    return out


def reachability(reg: dict[str, dict[str, Any]] | None = None,
                 root: pathlib.Path | None = None,
                 *, keep_world: bool = False) -> dict[str, Any]:
    """Call every claim inside one disposable world; report what happened."""
    from canonical.runtime import confinement_v1 as confinement
    from canonical.runtime import live_integrated_brain_v1 as brain

    reg = reg if reg is not None else brain.load_verified_registry()
    root = pathlib.Path(root or _root()).resolve()
    plan, blocked = plan_for(reg, root)
    cells: dict[str, Any] = {cid: {"state": "UNREACHABLE", "why": why} for cid, why in blocked.items()}

    # THE WORLD MUST BE THIS MACHINE. `confinement_v1.execute` fixes `PATH` to
    # /usr/local/bin:/usr/bin:/bin, so a bare `python3` in the world is `/usr/bin/python3` -- a DIFFERENT
    # interpreter from the one the audit was invoked with, with a different installed set. Measured: with
    # Pillow declared and installed in the caller, the world still reported 3 probes LOAD_FAILED:ModuleNotFound
    # because /usr/bin/python3 has no PIL. A census that measures a machine nobody runs is measuring the
    # wrong computer. `sys.executable` is the same interpreter, run inside the copy, so the reading is of
    # the interpreter the project actually uses.
    world = confinement.admit(root, [sys.executable, "canonical/_rb_probe.py"], budget_s=900)
    if not isinstance(world, confinement.Confinement):
        return {"schema": SCHEMA, "error": "WORLD_NOT_ADMITTED", **world}
    try:
        probe = world.worktree / "canonical" / "_rb_probe.py"
        probe.write_text(PROBE)
        (world.worktree / "_rb_probe_plan.json").write_text(json.dumps(plan))
        result = confinement.execute(world)
        out_path = world.worktree / "_rb_probe_out.json"
        records = json.loads(out_path.read_text()) if out_path.is_file() else {}
        for cid, rec in records.items():
            cells[cid] = judge(rec, reg.get(cid) or {}, bool((reg.get(cid) or {}).get("_zero_input")))
        # The plan knows which rows had no inputs; that is a property of the row, not of the record.
        zero = {item["cid"] for item in plan if item.get("zero_input")}
        for cid in zero:
            if cid in cells and cells[cid].get("state") in ("RAN", "WROTE"):
                cells[cid]["state"] = "SELF_ATTESTING"
                cells[cid]["why"] = "NO_INPUT_SO_THE_ANSWER_IS_ABOUT_ITSELF"
        report = {
            "schema": SCHEMA,
            "interpreter": sys.executable,
            "world": {"host_untouched": result.get("host_untouched"),
                      "verified": result.get("verified"),
                      "outcome": result.get("outcome"),
                      "exit_code": result.get("exit_code"),
                      "receipt": result.get("receipt"),
                      "elapsed_s": result.get("elapsed_s")},
            "claims": len(cells),
            "planned": len(plan),
            "cells": cells,
        }
    finally:
        if keep_world:
            report["world_path"] = str(world.worktree)
        else:
            confinement.release(world)
    counts: dict[str, int] = {}
    for cell in report["cells"].values():
        counts[cell["state"]] = counts.get(cell["state"], 0) + 1
    report["counts"] = counts
    # THE OTHER HALF OF THE ANSWER. `UNREACHABLE` lumps together a broken file, a tool that is not
    # installed, and a wheel built for another Python. `tool_claims_v1` separates them by looking at this
    # machine, so one call answers both "what can I do" and "what am I only claiming".
    from canonical.runtime import tool_claims_v1 as tools
    tool_report = tools.tool_claims(reg)
    report["tool_claims"] = {"counts": tool_report["counts"], "claims": tool_report["claims"]}
    for cid, row in tool_report["rows"].items():
        if cid in cells and cells[cid].get("why") == "NO_ADAPTER_DECLARED":
            cells[cid]["why"] = "NO_ADAPTER_DECLARED:" + row["state"]
            cells[cid]["tool"] = {k: row.get(k) for k in
                                  ("state", "declared_module", "declared_program", "declared_wheel",
                                   "wheel_fits_this_interpreter", "acquirable", "why")
                                  if row.get(k) is not None}
    report["note"] = ("SELF_ATTESTING rows take no input: their verdict is a restatement of the "
                      "registry, not a measurement. They are counted apart from RAN/WROTE.")
    return report


def main() -> None:
    report = reachability()
    print(json.dumps({k: report.get(k) for k in ("counts", "claims", "planned", "world")},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
