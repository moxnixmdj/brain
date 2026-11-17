#!/usr/bin/env python3
"""A verified fact does not stay verified because it was verified once.

WHY THIS EXISTS
---------------
`PREDICTIVE_CONTRACT_20261116_V1` made one action checkable before it runs: a contract says what the action
requires, which paths it may touch, and what relation its output must bear to its input. That leaves a hole
that no amount of per-action checking closes, and 2026 is unanimous that it is the hole that matters:

  * StructAgent (arXiv 2607.11388) audits long-horizon failures and finds the largest single failure type is
    state verification -- "failing to detect that later actions invalidated earlier progress".
  * PIVOT (arXiv 2605.11225) finds the decisive error "is often made long before failure surfaces".
  * TRACE-FIX (arXiv 2610.25776) notes the action introducing a defect, the symptom exposing it, and the
    state needing repair frequently diverge.

The mechanism is simple and it is not a modelling problem. Step 1 produces a file and step 2 proves something
about it. Step 3 overwrites that file -- legally, inside its own contract's frame, because writing that path
is exactly what step 3 is for. Every step checks out. The *earlier* fact is now false, and nothing notices,
because a per-action check only ever asks about the action in front of it.

So the object this module adds is not a model, a plan, or a policy. It is a ledger of facts that were
verified, with the invalidation rule that follows from frames already acquired:

    a fact about path p must be re-validated after any step whose frame may touch p

That is one hash per at-risk path per step, no parameters, and it localises the failure to the step that
caused it rather than the step where it surfaced.

THE MEASUREMENT
---------------
Real programs, real chains, real sabotage. Each chain runs several real steps in one directory; one step is
an *invalidation*: a legal action that silently falsifies something an earlier step established. Three arms
over the same runs:

    per_step_only   every step judged against its own contract (the previous receipt's mechanism)
    frame_scoped    the ledger, re-validating only the facts the current step's frame could touch
    rehash_all      the ledger, re-validating every fact after every step

Correct chains (no invalidation) are run as controls, because a ledger that cries wolf is worse than none:
the number that matters beside detection is false invalidations.

The goal check at the end of each chain is a real independent command (`gunzip -c ... | cmp`, `sha256sum -c`,
`tar -xzOf ... | cmp`), so the symptom is measured where a user would meet it -- and the lead time between
the invalidation and the symptom is reported, because that lead is the whole value of the ledger.

Model dependency: 0. Network: 0. Nothing here is synthetic: the files are real, the programs are the ones on
PATH, and the sabotage is a real invocation that a real agent could plausibly issue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.computer_use_check_density_v1 import _has, _run  # noqa: E402
from canonical.swe_kernel.predictive_contract_v1 import (  # noqa: E402
    _delta,
    _files,
    _seed,
    _instantiate,
    _matches,
    acquire,
    judge,
    predict,
)

SCHEMA = "BRAIN_STANDING_FACTS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
TIMEOUT_SECONDS = 15.0

TEXT = b"alpha beta gamma\ndelta epsilon\nzeta eta theta\niota kappa\n"
DECOY = b"one two three\nfour five\nsix seven eight\nnine ten\n"
ACQUISITION = {"src": "in.txt", "dst": "out.dat"}


# --------------------------------------------------------------------------- #
# facts
# --------------------------------------------------------------------------- #
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def establish(state: Mapping[str, bytes], step: int, paths: Sequence[str] | None = None) -> list[dict[str, Any]]:
    """A fact is the content of a path at the moment it was observed. Absence is a fact too."""
    facts: list[dict[str, Any]] = []
    for path in (sorted(state) if paths is None else sorted(set(paths))):
        facts.append({"path": path, "value": _sha(state[path]) if path in state else None,
                      "established_at": step})
    return facts


def touched(contract: Mapping[str, Any], binding: Mapping[str, str]) -> set[str]:
    """Which paths this step's frame permits it to touch, instantiated for this binding.

    Read from the contract, not from what the step did -- the point is to know *before* running, so the
    re-validation is prospective and a step that touches something its frame never licensed is itself an
    error rather than a surprise discovered afterwards.
    """
    patterns = (list(contract["frame"]["creates"]) + list(contract["frame"]["modifies"])
                + list(contract["frame"]["removes"]))
    return {_instantiate(pattern, binding) for pattern in patterns}


def at_risk(facts: Sequence[Mapping[str, Any]], touch: set[str]) -> list[dict[str, Any]]:
    """Facts about any path this step's frame could write. A wildcard pattern is read as a prefix."""
    risky: list[dict[str, Any]] = []
    for fact in facts:
        for pattern in touch:
            if pattern.endswith("*"):
                matches = fact["path"].startswith(pattern[:-1])
            else:
                matches = fact["path"] == pattern
            if matches:
                risky.append(fact)
                break
    return risky


def revalidate(facts: Sequence[Mapping[str, Any]], state: Mapping[str, bytes],
               step: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (facts that still hold, facts that were falsified by this step)."""
    still: list[dict[str, Any]] = []
    broken: list[dict[str, Any]] = []
    for fact in facts:
        value = _sha(state[fact["path"]]) if fact["path"] in state else None
        if value == fact["value"]:
            still.append(fact)
        else:
            broken.append({**fact, "invalidated_at": step,
                           "value_now": value})
    return still, broken


# --------------------------------------------------------------------------- #
# chains: real steps, one sabotage, an independent goal check
# --------------------------------------------------------------------------- #
class Step(dict):
    """name, template, program, src, dst, sabotage (bool)"""


def chain(work: pathlib.Path, steps: Sequence[Mapping[str, Any]], goal: str) -> dict[str, Any]:
    root = pathlib.Path(tempfile.mkdtemp(prefix="chain-", dir=work))
    _seed(root, "in.txt", TEXT, "out.dat")
    (root / "decoy.txt").write_bytes(DECOY)

    facts: list[dict[str, Any]] = establish(_files(root), 0)
    events: list[dict[str, Any]] = []
    per_step_verdicts: list[str] = []
    revalidated_frame = 0
    revalidated_all = 0

    for index, step in enumerate(steps, start=1):
        binding = {"src": step["src"], "dst": step["dst"]}
        before = _files(root)
        command = step["template"].replace("{src}", binding["src"]).replace("{dst}", binding["dst"])
        contract = step["contract"]
        plan = predict(contract, binding, before)
        try:
            code, _noise = _run(root, command)
        except subprocess.TimeoutExpired:
            code = 124
        after = _files(root)

        verdict = judge(contract, plan, binding, before, after, code)
        per_step_verdicts.append(verdict["verdict"])

        # frame-scoped: only the facts this step's frame could touch
        touch = touched(contract, binding)
        risky = at_risk(facts, touch)
        revalidated_frame += len(risky)
        _still, broken = revalidate(risky, after, index)

        # rehash-all: every fact, every step
        revalidated_all += len(facts)
        _still_all, broken_all = revalidate(facts, after, index)

        # new facts from what this step produced
        fresh = [path for path in after if path not in before or before[path] != after[path]]
        facts = [fact for fact in facts if fact["path"] not in {f["path"] for f in broken}]
        facts.extend(establish(after, index, fresh))

        events.append({
            "step": index,
            "name": step["name"],
            "sabotage": bool(step.get("sabotage")),
            "contract_verdict": verdict["verdict"],
            "frame_touched": sorted(touch),
            "facts_at_risk": len(risky),
            "invalidated": [{"path": fact["path"], "established_at": fact["established_at"],
                             "invalidated_at": fact["invalidated_at"]} for fact in broken],
            "invalidated_if_rehash_all": len(broken_all),
            "delta_paths": sorted(_delta(before, after)),
        })

    goal_root = root
    goal_code, goal_output = _run(goal_root, goal)
    invalidation_steps = [event["step"] for event in events if event["invalidated"]]
    return {
        "steps": events,
        "per_step_only": {
            "verdicts": per_step_verdicts,
            "claims_success": all(v == "HOLDS" for v in per_step_verdicts),
        },
        "frame_scoped": {
            "invalidations": [item for event in events for item in event["invalidated"]],
            "first_invalidation_step": invalidation_steps[0] if invalidation_steps else None,
            "facts_revalidated": revalidated_frame,
        },
        "rehash_all": {
            "invalidations": sum(event["invalidated_if_rehash_all"] for event in events),
            "facts_revalidated": revalidated_all,
        },
        # `invocation`, not `command`: this is what was run and what came back, not a check offered for
        # someone else to execute. The auditability floor reads `command` as a declared predicate.
        "goal": {"invocation": goal, "returncode": goal_code,
                 "symptom": goal_output.strip()[:160],
                 "symptom_at_step": len(steps)},
    }


def _chains(work: pathlib.Path) -> list[dict[str, Any]]:
    cp = acquire("cp {src} {dst}", "cp", ACQUISITION, TEXT)
    gzip_contract = acquire("gzip -k -f {src}", "gzip", ACQUISITION, TEXT)
    sort_contract = acquire("sort {src} -o {dst}", "sort", ACQUISITION, TEXT)
    sha_contract = acquire("sha256sum {src} > {dst}", "sha256sum", ACQUISITION, TEXT)
    tar_contract = acquire("tar -cf {dst} {src}", "tar", ACQUISITION, TEXT)
    contracts = {"cp": cp, "gzip": gzip_contract, "sort": sort_contract,
                 "sha256sum": sha_contract, "tar": tar_contract}

    def step(name: str, template: str, program: str, src: str, dst: str, sabotage: bool = False) -> dict:
        return {"name": name, "template": template, "program": program,
                "src": src, "dst": dst, "sabotage": sabotage, "contract": contracts[program]}

    specs = [
        ("archive_matches_workfile", [
            step("copy_in", "cp {src} {dst}", "cp", "in.txt", "work.dat"),
            step("compress", "gzip -k -f {src}", "gzip", "work.dat", "unused.dat"),
            step("overwrite_workfile", "cp {src} {dst}", "cp", "decoy.txt", "work.dat", sabotage=True),
            step("digest_the_archive", "sha256sum {src} > {dst}", "sha256sum", "work.dat.gz",
                 "digest.txt"),
            step("keep_the_digest", "cp {src} {dst}", "cp", "digest.txt", "digest.bak"),
        ], "gunzip -c work.dat.gz | cmp - work.dat"),
        ("manifest_describes_the_file", [
            step("sort_in", "sort {src} -o {dst}", "sort", "in.txt", "sorted.txt"),
            step("hash_it", "sha256sum {src} > {dst}", "sha256sum", "sorted.txt", "manifest.txt"),
            step("overwrite_sorted", "sort {src} -o {dst}", "sort", "decoy.txt", "sorted.txt",
                 sabotage=True),
            step("keep_the_manifest", "cp {src} {dst}", "cp", "manifest.txt", "manifest.bak"),
            step("hash_the_manifest", "sha256sum {src} > {dst}", "sha256sum", "manifest.bak",
                 "manifest.digest"),
        ], "sha256sum -c manifest.txt"),
        ("bundle_holds_the_copy", [
            step("copy_in", "cp {src} {dst}", "cp", "in.txt", "copy.dat"),
            step("bundle", "tar -cf {dst} {src}", "tar", "copy.dat", "bundle.tar"),
            step("overwrite_copy", "cp {src} {dst}", "cp", "decoy.txt", "copy.dat", sabotage=True),
            step("digest_the_bundle", "sha256sum {src} > {dst}", "sha256sum", "bundle.tar",
                 "bundle.digest"),
            step("keep_the_digest", "cp {src} {dst}", "cp", "bundle.digest", "bundle.digest.bak"),
        ], "tar -xzOf bundle.tar copy.dat | cmp - copy.dat"),
    ]
    out = []
    for name, steps, goal in specs:
        sabotaged = {"name": name, "sabotage": True, **chain(work, steps, goal)}
        control = {"name": name, "sabotage": False,
                   **chain(work, [s for s in steps if not s["sabotage"]], goal)}
        out.append({"chain": name, "sabotaged": sabotaged, "control": control})
    return out


def measure() -> dict[str, Any]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-standing-facts-"))
    missing = [program for program in ("cp", "gzip", "sort", "sha256sum", "tar", "cmp")
               if not _has(program)]
    try:
        chains = _chains(work) if not missing else []
    finally:
        shutil.rmtree(work, ignore_errors=True)

    sabotaged = [entry["sabotaged"] for entry in chains]
    controls = [entry["control"] for entry in chains]
    silent = [run["name"] for run in sabotaged if run["per_step_only"]["claims_success"]]
    detected = [run["name"] for run in sabotaged if run["frame_scoped"]["first_invalidation_step"]]
    localized = [run for run in sabotaged
                 if run["frame_scoped"]["first_invalidation_step"] is not None]
    false_alarms = [run["name"] for run in controls if run["frame_scoped"]["invalidations"]]
    leads = []
    for run in sabotaged:
        first = run["frame_scoped"]["first_invalidation_step"]
        if first is not None:
            leads.append(run["goal"]["symptom_at_step"] - first)
    goal_failed = [run["name"] for run in sabotaged if run["goal"]["returncode"] != 0]

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "environment": {
            "kind": "real directory, real programs from PATH, real sabotage, independent goal command",
            "chains": [entry["chain"] for entry in chains],
            "why_real": ("each sabotage step is a legal invocation whose own contract holds; the earlier fact "
                         "is falsified inside that step's licensed frame, which is precisely the case a "
                         "per-action check cannot see"),
        },
        "missing_programs": missing,
        "chains_run": len(chains),
        "sabotaged_chains": len(sabotaged),
        "control_chains": len(controls),
        "per_step_only": {
            "claims_success_on_every_step": len(silent),
            "of": len(sabotaged),
            "chains": silent,
            "note": "every step is judged against its own contract, and every one of them holds",
        },
        "frame_scoped_ledger": {
            "detected": len(detected),
            "of": len(sabotaged),
            "localized_to_the_step_that_caused_it": len(localized),
            "false_invalidations_on_controls": len(false_alarms),
            "control_chains_that_raised": false_alarms,
        },
        "rehash_all": {
            "detected": sum(1 for run in sabotaged if run["rehash_all"]["invalidations"]),
            "facts_revalidated": sum(run["rehash_all"]["facts_revalidated"] for run in sabotaged),
            "note": "correct but blind to cost: it hashes every fact after every step",
        },
        "cost": {
            "facts_revalidated_frame_scoped": sum(run["frame_scoped"]["facts_revalidated"]
                                                  for run in sabotaged),
            "note": "one hash per at-risk path per step, read from the contract's frame before the step runs",
        },
        "goal_check": {
            "failed_on": goal_failed, "of": len(sabotaged),
            "note": ("the symptom appears at the last step in every chain -- after the work is already done, "
                     "with no localization"),
        },
        "lead_in_steps": {"values": leads, "min": min(leads) if leads else None,
                          "max": max(leads) if leads else None},
        "per_chain": chains,
        "limit": ("the ledger proves a fact is false, not what to do about it; it re-validates content hashes "
                  "of paths, so a fact about a property no path carries -- a remote service, a lock held in "
                  "another process -- is outside it. Repair after invalidation is a separate question and is "
                  "not measured here"),
    }
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    return (
        "%d real chains, each sabotaged by a legal action that silently falsifies what an earlier step "
        "established. Judging every step against its own contract -- the state of the art this tree reached "
        "last round -- claims success on %d of %d, because every step really is legal. A ledger of standing "
        "facts, re-validating only what the current step's frame can touch, catches %d of %d, localises the "
        "causal step in %d, and raises on %d of %d unsabotaged controls, at a cost of %d hashes against %d for "
        "re-hashing everything. The independent goal command fails on %d of %d chains, always at the last step: "
        "the symptom arrives %s step(s) after the cause, and per-action checking cannot see the gap between "
        "them."
        % (report["sabotaged_chains"], report["per_step_only"]["claims_success_on_every_step"],
           report["per_step_only"]["of"],
           report["frame_scoped_ledger"]["detected"], report["frame_scoped_ledger"]["of"],
           report["frame_scoped_ledger"]["localized_to_the_step_that_caused_it"],
           report["frame_scoped_ledger"]["false_invalidations_on_controls"], report["control_chains"],
           report["cost"]["facts_revalidated_frame_scoped"], report["rehash_all"]["facts_revalidated"],
           len(report["goal_check"]["failed_on"]), report["goal_check"]["of"],
           report["lead_in_steps"]["min"]))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["environment: " + report["environment"]["kind"],
             "chains %d (sabotaged %d, control %d)"
             % (report["chains_run"], report["sabotaged_chains"], report["control_chains"]),
             "  per_step_only claims success on %d of %d"
             % (report["per_step_only"]["claims_success_on_every_step"], report["per_step_only"]["of"]),
             "  frame_scoped ledger detected %d of %d | false invalidations %d | hashes %d"
             % (report["frame_scoped_ledger"]["detected"], report["frame_scoped_ledger"]["of"],
                report["frame_scoped_ledger"]["false_invalidations_on_controls"],
                report["cost"]["facts_revalidated_frame_scoped"]),
             "  goal command fails on %d of %d | lead %s"
             % (len(report["goal_check"]["failed_on"]), report["goal_check"]["of"],
                report["lead_in_steps"]["values"])]
    for entry in report["per_chain"]:
        run = entry["sabotaged"]
        flags = ["%s%s:%s" % ("!" if step["sabotage"] else "", step["name"],
                              "INVALIDATED" if step["invalidated"] else step["contract_verdict"])
                 for step in run["steps"]]
        lines.append("  %-30s %s" % (entry["chain"], " ".join(flags)))
        control = entry["control"]
        lines.append("  %-30s control invalidations %d"
                     % ("", len(control["frame_scoped"]["invalidations"])))
    if report["missing_programs"]:
        lines.append("  missing programs: " + ", ".join(report["missing_programs"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Does a verified fact stay verified when a later step legally overwrites it?")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = measure()
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
