#!/usr/bin/env python3
"""Reconcile stale frontier mirrors to the live goal hierarchy.

ACTIVE_GOAL_HIERARCHY_V1 is the single authority for the live frontier. Every
other surface that restates it is a mirror, and mirrors rot: each frontier
advance leaves them carrying the previous blocker and next action, which makes
enforce_goal_hierarchy fail every frontier-sensitive PR permanently.

This tool recomputes the mirrors from the authority. It never edits the
hierarchy's blocker or next action (that is a frontier redefinition and requires
RECONCILE_FRONTIER evidence), and it never moves a scoreboard counter (that would
imply a promotion).

    python3 canonical/runtime/reconcile_frontier_mirrors.py --check   # report only
    python3 canonical/runtime/reconcile_frontier_mirrors.py           # write
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys
from typing import Any

HIERARCHY="canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json"
POINTER="canonical/CANONICAL_POINTER.json"
QUEUE="canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json"
SCOREBOARD="canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"
COUNTERS=(
    "reusable_capabilities_inherited","verified_real_tasks_completed",
    "fresh_reuse_passes","frontier_dependencies_removed","residual_gaps_localized",
)
# Pointer control paths that must declare the current, non-superseded artifact.
CONTROL_PATH_KEYS=(
    "pre_action_gate_path","goal_hierarchy_action_gate_path",
    "recursive_obs_receipt_schema_path","recursive_obs_action_intent_template_path",
    "capability_acquisition_engine_law_path","capability_arbitrage_strategy_path",
    "frontier_capability_obsolescence_mission_lock_path",
    "white_box_capability_harvesting_law_path","white_box_capability_capsule_schema_path",
)
SUPERSEDED_MARKER="SUPERSEDED / DO NOT EXECUTE"


class Doc:
    """A JSON document that re-serializes byte-identically unless edited."""

    def __init__(self,root:pathlib.Path,rel:str):
        self.root,self.rel,self.path=root,rel,root/rel
        self.data=json.loads(self.path.read_text(encoding="utf-8"))
        self.dirty=False

    def get(self,*keys:str)->Any:
        node:Any=self.data
        for key in keys:
            if not isinstance(node,dict):
                return None
            node=node.get(key)
        return node

    def put(self,value:Any,*keys:str)->str|None:
        """Set a nested key. Returns a change description, or None if already equal."""
        node=self.data
        for key in keys[:-1]:
            node=node.setdefault(key,{})
        if node.get(keys[-1])==value:
            return None
        before=node.get(keys[-1])
        node[keys[-1]]=value
        self.dirty=True
        return f"{self.rel}: {'.'.join(keys)}\n      was: {str(before)[:76]}\n      now: {str(value)[:76]}"

    def write(self)->None:
        self.path.write_text(json.dumps(self.data,indent=2)+"\n",encoding="utf-8")


NOT_VERSIONED="NOT_VERSIONED"
FAMILY_UNRESOLVED="FAMILY_UNRESOLVED"


def current_version(root:pathlib.Path,declared:str)->tuple[int,int]|str:
    """Return (declared_version, max_version_in_family) for a versioned path.

    Returns NOT_VERSIONED when the path carries no _V<n> suffix, and
    FAMILY_UNRESOLVED when no sibling version exists to compare against, so the
    two very different situations are never conflated.
    """
    match=re.search(r"^(.*_V)(\d+)(\.(?:json|md))$",str(declared))
    if not match:
        return NOT_VERSIONED
    versions=[]
    for candidate in root.glob(match.group(1)+"*"+match.group(3)):
        found=re.search(r"_V(\d+)\.",candidate.name)
        if found:
            versions.append(int(found.group(1)))
    if not versions:
        return FAMILY_UNRESOLVED
    return int(match.group(2)),max(versions)


def reconcile(root:pathlib.Path,*,write:bool,fix_control_paths:bool,
              align_hierarchy_progress_event:bool)->int:
    changes:list[str]=[]
    reports:list[str]=[]
    pending_mirrors:list[tuple[str,str]]=[]

    # Fail closed on absent authority or mirror files rather than raising, so a
    # direct call behaves like the CLI and never leaves a partial write behind.
    for rel in (HIERARCHY,POINTER,QUEUE,SCOREBOARD):
        if not (root/rel).is_file():
            print(f"REFUSED: required canonical file missing: {rel}")
            return 2

    hierarchy=Doc(root,HIERARCHY)
    blocker=hierarchy.get("current_parent_blocker")
    action=hierarchy.get("next_required_action_class")
    target=hierarchy.get("active_capability_target")
    if not isinstance(blocker,str) or not blocker.strip():
        print("REFUSED: hierarchy declares no current_parent_blocker"); return 2
    if not isinstance(action,str) or not action.strip():
        print("REFUSED: hierarchy declares no next_required_action_class"); return 2
    if not isinstance(target,str) or not target.strip():
        print("REFUSED: hierarchy declares no active_capability_target"); return 2

    pointer=Doc(root,POINTER)
    queue=Doc(root,QUEUE)
    scoreboard=Doc(root,SCOREBOARD)
    target_rel=f"canonical/capabilities/frontier/{target}.json"
    if not (root/target_rel).is_file():
        print(f"REFUSED: active target record missing: {target_rel}"); return 2
    record=Doc(root,target_rel)

    counters_before=json.dumps(scoreboard.get("counters_since_epoch_start"),sort_keys=True)

    # --- the eleven mirror fields -----------------------------------------
    for doc,keys in (
        (pointer,("current_frontier","critical_blocker")),
        (queue,("immediate_frontier","exact_blocker")),
        (scoreboard,("active_frontier_accounting","residual_gap")),
        (record,("residual_gap",)),
        # enforce_goal_hierarchy.py checks the target record's atomic pair, while
        # tests/test_frontier_target_mirror.py checks residual_gap/next_action via
        # active_target_mirror_errors. Both pairs are mirrors of the same authority
        # fields, so the tool maintains all of them; covering only one half would
        # let test_live_repository_is_reconciled pass on a tree the guard fails.
        (record,("current_atomic_blocker",)),
    ):
        changed=doc.put(blocker,*keys)
        if changed: changes.append(changed)
    for doc,keys in (
        (pointer,("current_frontier","next_step")),
        (queue,("immediate_frontier","next_action")),
        (scoreboard,("next_progress_event_target",)),
        (scoreboard,("active_frontier_accounting","next_required_action")),
        (record,("next_action",)),
        (record,("current_atomic_next_action",)),
    ):
        changed=doc.put(action,*keys)
        if changed: changes.append(changed)

    # --- identity mirrors are reported, never rewritten --------------------
    for doc,keys in (
        (pointer,("current_frontier","active_capability_target")),
        (queue,("immediate_frontier","selected_capability")),
        (record,("capability_id",)),
    ):
        value=doc.get(*keys)
        if value!=target:
            reports.append(
                f"IDENTITY_DRIFT {doc.rel}: {'.'.join(keys)} = {str(value)[:60]} "
                f"!= hierarchy {target[:60]} (frontier redefinition; needs RECONCILE_FRONTIER, not this tool)"
            )

    # --- the hierarchy's own progress-event target -------------------------
    if hierarchy.get("next_progress_event_target")!=action:
        if align_hierarchy_progress_event:
            changed=hierarchy.put(action,"next_progress_event_target")
            if changed: changes.append(changed)
        else:
            reports.append(
                "HIERARCHY_PROGRESS_EVENT_DRIFT next_progress_event_target = "
                f"{str(hierarchy.get('next_progress_event_target'))[:60]} != next_required_action_class "
                "(authoritative file; pass --align-hierarchy-progress-event to edit it)"
            )

    # --- pointer control-path currency -------------------------------------
    boot=pointer.get("boot_requirements") or {}
    for key in CONTROL_PATH_KEYS:
        declared=boot.get(key)
        if not isinstance(declared,str) or not declared.strip():
            reports.append(f"CONTROL_PATH_MISSING {key}"); continue
        if not (root/declared).is_file():
            reports.append(f"CONTROL_PATH_FILE_MISSING {key}: {declared}"); continue
        pair=current_version(root,declared)
        if pair==NOT_VERSIONED:
            reports.append(f"CONTROL_PATH_NOT_VERSIONED {key}: {declared}"); continue
        if pair==FAMILY_UNRESOLVED:
            reports.append(f"CONTROL_PATH_FAMILY_UNRESOLVED {key}: {declared}"); continue
        declared_version,max_version=pair
        if declared_version!=max_version:
            if fix_control_paths:
                advanced=re.sub(r"_V\d+(\.(?:json|md))$",f"_V{max_version}\\1",declared)
                if not (root/advanced).is_file():
                    reports.append(f"CONTROL_PATH_ADVANCE_TARGET_MISSING {key}: {advanced}"); continue
                changed=pointer.put(advanced,"boot_requirements",key)
                if changed: changes.append(changed)
                pending_mirrors.append((declared,advanced))
            else:
                reports.append(
                    f"CONTROL_PATH_NOT_CURRENT {key}: declared V{declared_version}, current V{max_version} "
                    "(pass --fix-control-paths to advance)"
                )
        elif declared.endswith(".md"):
            try:
                if SUPERSEDED_MARKER in (root/declared).read_text(encoding="utf-8"):
                    reports.append(f"CONTROL_PATH_SUPERSEDED {key}: {declared}")
            except OSError as exc:
                reports.append(f"CONTROL_PATH_UNREADABLE {key}: {type(exc).__name__}")

    # --- invariants that must never be violated ----------------------------
    docs=[pointer,queue,scoreboard,record]+([hierarchy] if align_hierarchy_progress_event else [])
    if json.dumps(scoreboard.data.get("counters_since_epoch_start"),sort_keys=True)!=counters_before:
        print("REFUSED: this tool must never move a scoreboard counter")
        return 2
    if write and changes:
        for doc in docs:
            if doc.dirty:
                doc.write()
        # Non-boot mirror references inside the pointer must not contradict boot.
        if pending_mirrors:
            raw=pointer.path.read_text(encoding="utf-8")
            for declared,advanced in pending_mirrors:
                count=raw.count(declared)
                if count:
                    raw=raw.replace(declared,advanced)
                    changes.append(
                        f"{POINTER}: mirror references to {declared.split('/')[-1]} x{count} -> "
                        f"{advanced.split('/')[-1]}"
                    )
            pointer.path.write_text(raw,encoding="utf-8")
            json.loads(pointer.path.read_text(encoding="utf-8"))

    if reports:
        print("REPORTS")
        for item in reports: print(" -",item)
    if changes:
        print("MIRROR_CHANGES" if write else "MIRROR_DRIFT")
        for item in changes: print(" -",item)
        if write:
            print(f"WROTE {len([d for d in docs if d.dirty])} file(s)")
        else:
            print("DRIFT_PRESENT (no files written; re-run without --check to reconcile)")
    elif not reports:
        print("MIRRORS_CONSISTENT no drift found")
    # A report is drift this run did NOT repair: identity drift needs
    # RECONCILE_FRONTIER, hierarchy progress-event drift needs the explicit
    # opt-in, control-path drift needs --fix-control-paths. Exiting 0 on an
    # unrepaired report is fail-open: test_live_repository_is_reconciled would
    # stay green while enforce_goal_hierarchy.py fails the same tree, which is
    # exactly the lying-green-check this tool exists to prevent.
    if reports or (changes and not write):
        print("UNREPAIRED_DRIFT_PRESENT (fail closed; see REPORTS above)")
        return 1
    return 0


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo_root",type=pathlib.Path,nargs="?",default=pathlib.Path("."))
    ap.add_argument("--check",action="store_true",help="report drift without writing")
    ap.add_argument("--fix-control-paths",action="store_true",
                    help="advance stale pointer control paths to the current family version")
    ap.add_argument("--align-hierarchy-progress-event",action="store_true",
                    help="also align the authoritative hierarchy's next_progress_event_target")
    ns=ap.parse_args()
    root=ns.repo_root.resolve()
    for rel in (HIERARCHY,POINTER,QUEUE,SCOREBOARD):
        if not (root/rel).is_file():
            print(f"REFUSED: required canonical file missing: {rel}"); return 2
    return reconcile(root,write=not ns.check,fix_control_paths=ns.fix_control_paths,
                     align_hierarchy_progress_event=ns.align_hierarchy_progress_event)


if __name__=="__main__":
    raise SystemExit(main())
