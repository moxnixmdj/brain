#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

try:
    from trusted_terminal_progress_enforcement import (
        POINTER_PATH,
        ROOT_STATE_PATH,
        TOURNAMENT_PATH,
        CONTROL_LOOP_PATH,
        RESULT_BEARING_WORK_CLASSES,
        evaluate_postchange,
    )
except ImportError:
    from execution_guard.terminal_progress_enforcement import (
        POINTER_PATH,
        ROOT_STATE_PATH,
        TOURNAMENT_PATH,
        CONTROL_LOOP_PATH,
        RESULT_BEARING_WORK_CLASSES,
        evaluate_postchange,
    )

ROOT=pathlib.Path.cwd().resolve()

def git(*args: str) -> str:
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()

def changed_files(base: str,head: str) -> list[str]:
    out=git("diff","--name-only",f"{base}...{head}")
    return [x for x in out.splitlines() if x.strip()]

def exists(ref: str,path: str) -> bool:
    return subprocess.run(
        ["git","cat-file","-e",f"{ref}:{path}"],
        cwd=ROOT,text=True,capture_output=True,
    ).returncode==0

def load_at(ref: str,path: str):
    return json.loads(git("show",f"{ref}:{path}"))

def blob_at(ref: str,path: str) -> str:
    return git("rev-parse",f"{ref}:{path}")

def safe_path(path: str) -> str:
    if not isinstance(path,str) or not path.strip():
        raise ValueError("PATH_INVALID")
    pure=pathlib.PurePosixPath(path)
    if path.startswith("/") or ".." in pure.parts:
        raise ValueError("PATH_ESCAPE")
    return path

def one_action_intent(base: str,head: str) -> dict:
    intents=[
        p for p in changed_files(base,head)
        if p.startswith("canonical/action_intents/") and p.endswith(".json")
    ]
    if len(intents)!=1:
        raise ValueError("EXACTLY_ONE_CHANGED_ACTION_INTENT_REQUIRED")
    return load_at(head,intents[0])

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True)
    ap.add_argument("--head",required=True)
    ns=ap.parse_args()

    intent=one_action_intent(ns.base,ns.head)
    admission=intent.get("v22_prewrite_admission")
    if not isinstance(admission,dict):
        raise ValueError("V22_PREWRITE_ADMISSION_MISSING")
    work_class=str(admission.get("work_class") or "")
    if work_class not in RESULT_BEARING_WORK_CLASSES:
        print(json.dumps({
            "schema":"PROJECT_BRAIN_TERMINAL_PROGRESS_PR_VALIDATION_V1",
            "status":"PASS__NON_RESULT_BEARING_WORK_CLASS__ZERO_PROGRESS_CREDIT",
            "work_class":work_class,
        },sort_keys=True))
        return 0

    binding=admission.get("terminal_progress_evidence")
    if not isinstance(binding,dict):
        raise ValueError("TERMINAL_PROGRESS_EVIDENCE_BINDING_MISSING")
    path=safe_path(binding.get("path"))
    if not exists(ns.head,path):
        raise ValueError("TERMINAL_PROGRESS_EVIDENCE_FILE_MISSING")
    actual_blob=blob_at(ns.head,path)
    if binding.get("git_blob_sha")!=actual_blob:
        raise ValueError("TERMINAL_PROGRESS_EVIDENCE_BLOB_MISMATCH")
    evidence_record=load_at(ns.head,path)

    before_docs={}
    after_docs={}
    for source in (POINTER_PATH,ROOT_STATE_PATH,TOURNAMENT_PATH,CONTROL_LOOP_PATH):
        if not exists(ns.base,source) or not exists(ns.head,source):
            raise ValueError("CANONICAL_PROGRESS_SOURCE_MISSING:"+source)
        before_docs[source]=load_at(ns.base,source)
        after_docs[source]=load_at(ns.head,source)

    def resolve_receipt(raw_path: str):
        rp=safe_path(raw_path)
        ref=ns.head if exists(ns.head,rp) else ns.base
        if not exists(ref,rp):
            raise ValueError("TERMINAL_PROGRESS_RECEIPT_MISSING:"+rp)
        return load_at(ref,rp),blob_at(ref,rp)

    result=evaluate_postchange(
        work_class=work_class,
        target_truth_obligations=list(admission.get("target_truth_obligations") or []),
        before_documents=before_docs,
        after_documents=after_docs,
        evidence_record=evidence_record,
        resolve_receipt=resolve_receipt,
    )
    print(json.dumps({
        "schema":"PROJECT_BRAIN_TERMINAL_PROGRESS_PR_VALIDATION_V1",
        "status":"PASS",
        **result,
    },sort_keys=True))
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("TERMINAL_PROGRESS_PR_VALIDATION_DENIED:"+type(exc).__name__+":"+str(exc),file=sys.stderr)
        raise
