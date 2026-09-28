#!/usr/bin/env python3
"""Fail-closed anti-drift validator for frontier-sensitive changes."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, pathlib, subprocess, sys, urllib.parse, urllib.request

ROOT=pathlib.Path(os.environ.get("GITHUB_WORKSPACE") or pathlib.Path.cwd()).resolve()

SENSITIVE_PREFIXES=(
    "canonical/runtime/",
    "canonical/experiments/",
    "canonical/capabilities/",
    "canonical/tasks/",
    "canonical/qualification/",
    "canonical/laws/",
    "canonical/gates/",
    "canonical/governance/",
    ".github/workflows/",
)
SENSITIVE_EXACT={"canonical/CANONICAL_POINTER.json"}
PROTECTED_GUARD_PATHS={
    "canonical/laws/GOAL_HIERARCHY_AND_DRIFT_IMMUNITY_LAW_V1.md",
    "canonical/laws/TRUTH_FIRST_AND_NO_DUPLICATE_EXECUTION_LAW_V1.md",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V1.json",
    "canonical/runtime/enforce_goal_hierarchy.py",
    ".github/workflows/drift-immunity-guard.yml",
}
ALLOWED_NO_PROBE_ACTIONS={
    "GOVERNANCE_GUARD",
    "RECONCILE_FRONTIER",
    "ORTHOGONAL_PROBE_SELECTION",
    "EVIDENCE_PRESERVATION",
}
FAIL=[]

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def fail(msg):
    FAIL.append(msg)

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()

def changed_files(base,head):
    out=git("diff","--name-only",f"{base}...{head}")
    return [x for x in out.splitlines() if x.strip()]

def added_diff(base,head,path):
    try:
        return git("diff","--unified=0",f"{base}...{head}","--",path)
    except subprocess.CalledProcessError:
        return ""

def is_sensitive(path):
    return path in SENSITIVE_EXACT or any(path.startswith(p) for p in SENSITIVE_PREFIXES)


def blocker_lease_key(intent):
    parts=[
        str(intent.get("canonical_generation") or ""),
        str(intent.get("capability_target") or ""),
        str(intent.get("causal_blocker") or ""),
        str(intent.get("action_kind") or ""),
    ]
    return "::".join(parts)

def _github_json(path):
    token=os.environ.get("GITHUB_TOKEN")
    repo=os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        raise RuntimeError("GITHUB_DEDUPE_CONTEXT_MISSING")
    req=urllib.request.Request(
        "https://api.github.com"+path,
        headers={
            "Authorization":"Bearer "+token,
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28",
            "User-Agent":"ProjectBrain-DriftGuard/1",
        },
    )
    with urllib.request.urlopen(req,timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _open_pr_intents():
    repo=os.environ.get("GITHUB_REPOSITORY")
    current=int(os.environ.get("CURRENT_PR_NUMBER") or "0")
    if not repo or not os.environ.get("GITHUB_TOKEN") or current<=0:
        return []
    prs=_github_json(f"/repos/{repo}/pulls?state=open&per_page=100")
    out=[]
    for pr in prs:
        number=int(pr.get("number") or 0)
        if number==current:
            continue
        files=_github_json(f"/repos/{repo}/pulls/{number}/files?per_page=100")
        for item in files:
            path=str(item.get("filename") or "")
            if not (path.startswith("canonical/action_intents/") and path.endswith(".json")):
                continue
            if item.get("status")=="removed":
                continue
            ref=str((pr.get("head") or {}).get("sha") or "")
            encoded=urllib.parse.quote(path,safe="/")
            try:
                payload=_github_json(f"/repos/{repo}/contents/{encoded}?ref={urllib.parse.quote(ref,safe='')}")
                raw=base64.b64decode(payload.get("content") or b"")
                intent=json.loads(raw.decode("utf-8"))
            except Exception as exc:
                raise RuntimeError(f"OPEN_PR_INTENT_READ_FAILED:{number}:{path}:{type(exc).__name__}") from exc
            out.append({"pr":number,"path":path,"intent":intent})
    return out

def enforce_blocker_lease(intent):
    expected=blocker_lease_key(intent)
    actual=str(intent.get("blocker_lease_key") or "")
    if actual!=expected:
        fail("BLOCKER_LEASE_KEY_MISSING_OR_MISMATCH")
        return
    try:
        peers=_open_pr_intents()
    except Exception as exc:
        fail("BLOCKER_LEASE_DEDUPE_CHECK_FAILED:"+str(exc))
        return
    for peer in peers:
        other=peer["intent"]
        if blocker_lease_key(other)!=expected:
            continue
        if str(other.get("blocker_lease_key") or "")!=expected:
            continue
        if bool(intent.get("intentional_route_race")) and bool(other.get("intentional_route_race")):
            race_a=str(intent.get("route_race_id") or "")
            race_b=str(other.get("route_race_id") or "")
            if race_a and race_a==race_b:
                continue
        fail(f"DUPLICATE_BLOCKER_LEASE_OPEN_PR:{peer['pr']}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True)
    ap.add_argument("--head",default="HEAD")
    ns=ap.parse_args()

    files=changed_files(ns.base,ns.head)
    sensitive=[x for x in files if is_sensitive(x)]
    if not sensitive:
        print("DRIFT_GUARD_PASS no frontier-sensitive changes")
        return 0

    pointer=load("canonical/CANONICAL_POINTER.json")
    hierarchy=load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
    queue=load("canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json")

    intents=[
        x for x in files
        if x.startswith("canonical/action_intents/") and x.endswith(".json")
    ]
    if not intents:
        fail("ACTION_INTENT_MISSING")
        intents=[]
    if len(intents)>1:
        fail("MULTIPLE_ACTION_INTENTS_IN_ONE_PR")
    intent=load(intents[0]) if intents else {}

    if intent:
        enforce_blocker_lease(intent)

    terminal=str(pointer.get("mission_lock",{}).get("terminal_objective") or "")
    if hierarchy.get("terminal_objective")!=terminal:
        fail("HIERARCHY_TERMINAL_OBJECTIVE_MISMATCH")
    if intent.get("terminal_objective")!=terminal:
        fail("INTENT_TERMINAL_OBJECTIVE_MISMATCH")

    program=str(pointer.get("current_frontier",{}).get("program") or "")
    if hierarchy.get("active_program")!=program:
        fail("HIERARCHY_ACTIVE_PROGRAM_MISMATCH")
    if intent.get("active_program")!=program:
        fail("INTENT_ACTIVE_PROGRAM_MISMATCH")

    selected=(queue.get("immediate_frontier") or {}).get("selected_capability")
    htarget=hierarchy.get("active_capability_target")
    if selected and selected!=htarget:
        fail("QUEUE_HIERARCHY_CAPABILITY_TARGET_MISMATCH")
    if intent.get("capability_target")!=htarget:
        fail("INTENT_CAPABILITY_TARGET_MISMATCH")

    if not intent.get("expected_parent_frontier_change"):
        fail("PARENT_LEVEL_STATE_CHANGE_MISSING")
    if intent.get("highest_leverage_now") is not True:
        fail("ACTION_NOT_ASSERTED_HIGHEST_LEVERAGE")
    if not intent.get("stop_condition"):
        fail("STOP_CONDITION_MISSING")

    action_kind=str(intent.get("action_kind") or "")
    probe=intent.get("probe_id")
    active_probe=hierarchy.get("active_probe")
    quarantined={
        str(x.get("probe_id"))
        for x in hierarchy.get("quarantined_probes",[])
        if x.get("may_define_frontier") is False
    }
    if probe and str(probe) in quarantined:
        fail("QUARANTINED_PROBE_CANNOT_DEFINE_NEW_ACTION")
    if probe and active_probe and probe!=active_probe:
        fail("INTENT_PROBE_NOT_ACTIVE_PROBE")
    if probe and active_probe is None and action_kind not in {"ORTHOGONAL_PROBE_SELECTION","RECONCILE_FRONTIER"}:
        fail("NO_ACTIVE_PROBE_BUT_ACTION_TARGETS_PROBE")
    if not probe and action_kind not in ALLOWED_NO_PROBE_ACTIONS:
        fail("PROBE_REQUIRED_FOR_THIS_ACTION_KIND")

    probe_specific=bool(intent.get("probe_specific"))
    one_probe_repair=bool(intent.get("generic_repair_from_single_probe"))
    recurrence=int(intent.get("orthogonal_recurrence_count") or 0)
    precommitted=bool(intent.get("precommitted_acceptance_gate_exception"))
    budget=hierarchy.get("probe_budget") or {}
    used=int(budget.get("repairs_used_on_active_probe") or 0)
    max_repairs=int(budget.get("max_repairs_from_single_probe") or 1)
    if one_probe_repair and used>=max_repairs and recurrence<2 and not precommitted:
        fail("SECOND_REPAIR_FROM_SINGLE_PROBE_FORBIDDEN")
    if probe_specific and recurrence<2 and not precommitted:
        fail("PROBE_SPECIFIC_REPAIR_REQUIRES_ORTHOGONAL_RECURRENCE")

    literals=[str(x).lower() for x in intent.get("probe_specific_literals",[]) if str(x).strip()]
    if probe_specific and not literals:
        fail("PROBE_SPECIFIC_ACTION_MUST_DECLARE_PROBE_LITERALS")
    runtime_changes=[x for x in sensitive if x.startswith("canonical/runtime/")]
    for path in runtime_changes:
        diff=added_diff(ns.base,ns.head,path).lower()
        added="\n".join(
            line[1:] for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        for lit in literals:
            if lit and lit in added:
                fail(f"PROBE_LITERAL_CONTAMINATION:{path}:{lit}")

    governance_change=any(x in PROTECTED_GUARD_PATHS for x in files)
    if governance_change and intent.get("governance_change") is not True:
        fail("GUARD_CHANGE_WITHOUT_GOVERNANCE_INTENT")
    if governance_change and intent.get("weakens_existing_guard") is True:
        auth=str(intent.get("explicit_user_authorization") or "").lower()
        if "weaken" not in auth and "disable" not in auth:
            fail("GUARD_WEAKENING_WITHOUT_EXPLICIT_USER_AUTHORIZATION")

    non_intent_sensitive=[
        x for x in sensitive if not x.startswith("canonical/action_intents/")
    ]
    if len(non_intent_sensitive)>15 and action_kind!="GOVERNANCE_GUARD":
        fail("FRONTIER_PR_SCOPE_TOO_BROAD_RECONCILE_AND_SPLIT")

    expected_generation=str(intent.get("canonical_generation") or "")
    actual_generation=str(pointer.get("canonical_generation") or "")
    if expected_generation!=actual_generation:
        fail("CANONICAL_GENERATION_MISMATCH")

    if FAIL:
        print("DRIFT_GUARD_FAIL")
        for item in FAIL:
            print(" -",item)
        return 1

    digest=hashlib.sha256(terminal.encode()).hexdigest()
    print("DRIFT_GUARD_PASS")
    print(" terminal_objective_sha256",digest)
    print(" capability_target",htarget)
    print(" action_id",intent.get("action_id"))
    print(" sensitive_files",len(non_intent_sensitive))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
