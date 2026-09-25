#!/usr/bin/env python3
"""Deterministic repository-local Python test-corpus execution audit."""
from __future__ import annotations
import hashlib, json, pathlib, re, subprocess, sys, time

def _safe_dir(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_dir():
        raise RuntimeError("TEST_AUDIT_ROOT_MISSING")
    return p

def _counts(text, returncode):
    ran=0
    m=re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+([0-9.]+)s",text)
    reported_duration=float(m.group(2)) if m else None
    if m: ran=int(m.group(1))
    failures=errors=skipped=0
    m=re.search(r"FAILED\s*\(([^)]*)\)",text)
    if m:
        for key,val in re.findall(r"(failures|errors|skipped)=(\d+)",m.group(1)):
            if key=="failures": failures=int(val)
            elif key=="errors": errors=int(val)
            elif key=="skipped": skipped=int(val)
    else:
        m=re.search(r"OK\s*\(([^)]*)\)",text)
        if m:
            sm=re.search(r"skipped=(\d+)",m.group(1))
            if sm: skipped=int(sm.group(1))
    passed=max(0,ran-failures-errors-skipped) if returncode==0 else max(0,ran-failures-errors-skipped)
    return ran,passed,failures,errors,skipped,reported_duration

def run(args, root):
    repo=pathlib.Path(root).resolve()
    source_root=_safe_dir(repo,args.get("source_root","canonical/tests"))
    pattern=str(args.get("pattern") or "test_*.py")
    timeout_s=max(1,min(int(args.get("timeout_s",180)),600))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    files=sorted(p for p in source_root.glob(pattern) if p.is_file())
    if not files:
        raise RuntimeError("TEST_AUDIT_EMPTY")
    records=[]
    totals={"files":0,"tests":0,"passed":0,"failed":0,"errors":0,"skipped":0}
    for path in files:
        started=time.monotonic()
        proc=subprocess.run([sys.executable,str(path)],cwd=repo,text=True,capture_output=True,timeout=timeout_s)
        elapsed=round(time.monotonic()-started,6)
        combined=(proc.stdout or "")+"\n"+(proc.stderr or "")
        ran,passed,failures,errors,skipped,reported_duration=_counts(combined,proc.returncode)
        rec={
          "path":str(path.relative_to(repo)).replace("\\","/"),
          "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
          "exit_code":proc.returncode,
          "tests":ran,
          "passed":passed,
          "failed":failures,
          "errors":errors,
          "skipped":skipped,
          "duration_s":elapsed,
          "reported_test_duration_s":reported_duration,
        }
        records.append(rec)
        totals["files"]+=1; totals["tests"]+=ran; totals["passed"]+=passed
        totals["failed"]+=failures; totals["errors"]+=errors; totals["skipped"]+=skipped
        if proc.returncode!=0:
            raise RuntimeError("TEST_FILE_FAILED:"+rec["path"]+":"+combined[-2000:].replace("\n"," "))
    report={
      "schema":"PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1",
      "source_root":str(source_root.relative_to(repo)).replace("\\","/"),
      "pattern":pattern,
      "records":records,
      "totals":totals,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    return {
      "adapter":"python_test_audit",
      "output_path":str(output.relative_to(repo)).replace("\\","/"),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "file_count":totals["files"],
      "test_count":totals["tests"],
      "passed_count":totals["passed"],
      "failed_count":totals["failed"],
      "error_count":totals["errors"],
      "skipped_count":totals["skipped"],
      "output_verified":totals["failed"]==0 and totals["errors"]==0,
    }
