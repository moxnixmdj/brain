#!/usr/bin/env python3
"""Deterministic repository-local Python test-corpus execution audit."""
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, re, sys, time


def _load_patch_search():
    """The shared module that owns how a suite is executed.

    Imported by path, matching every other adapter in this directory that reaches it.
    """
    here = pathlib.Path(__file__).with_name('python_test_guided_patch_search_v1.py')
    spec = importlib.util.spec_from_file_location('_brain_patch_search', here)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PATCH = _load_patch_search()

def _text(value):
    """Partial subprocess buffers arrive as bytes even in text mode."""
    if value is None:
        return ""
    if isinstance(value,(bytes,bytearray)):
        return bytes(value).decode("utf-8","replace")
    return str(value)


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
    passed=max(0,ran-failures-errors-skipped)
    # A file that dies before unittest prints a summary (import error, syntax
    # error, segfault) reports no "Ran N tests" line at all. Counting that as
    # zero tests and zero failures records a hard crash as a clean file, which
    # is the one thing a pass-rate report must never do. Such a file is one
    # failed unit: the file itself.
    crashed=returncode!=0 and ran==0 and failures==0 and errors==0
    return ran,passed,failures,errors,skipped,reported_duration,crashed

def _report_is_consistent(raw, records, totals):
    """Re-read the artifact from disk and prove it accounts for what happened.

    This is a real check, not a flag the producer sets about itself. The report
    is parsed back out of the bytes that were written, every total is
    re-derived from the per-file records, and any file that exited nonzero must
    be accounted for as a failure, an error or a crash. A report that quietly
    under-counts a red file does not verify.
    """
    try:
        doc=json.loads(raw.decode("utf-8"))
    except Exception:
        return False
    if not isinstance(doc,dict):
        return False
    if doc.get("schema")!="PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1":
        return False
    recs=doc.get("records")
    tot=doc.get("totals")
    if not isinstance(recs,list) or not isinstance(tot,dict):
        return False
    if len(recs)==0 or recs!=records:
        return False
    for key in ("files","tests","passed","failed","errors","skipped","crashed","timed_out"):
        if tot.get(key)!=totals.get(key):
            return False
    if int(tot.get("files",-1))!=len(recs):
        return False
    for key in ("tests","passed","failed","errors","skipped"):
        if int(tot.get(key,-1))!=sum(int(r.get(key,0) or 0) for r in recs):
            return False
    if int(tot.get("crashed",-1))!=sum(1 for r in recs if r.get("crashed")):
        return False
    if int(tot.get("timed_out",-1))!=sum(1 for r in recs if r.get("timed_out")):
        return False
    scored=int(tot.get("tests",0))+int(tot.get("crashed",0))
    expected=round((int(tot.get("passed",0))/scored) if scored else 0.0,6)
    if abs(float(tot.get("pass_rate",-1))-expected)>1e-9:
        return False
    for r in recs:
        red=int(r.get("failed",0) or 0)+int(r.get("errors",0) or 0)+(1 if r.get("crashed") else 0)
        if int(r.get("exit_code",0) or 0)!=0 and red==0:
            return False
        if int(r.get("exit_code",0) or 0)==0 and red!=0:
            return False
    return True


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
    totals={"files":0,"tests":0,"passed":0,"failed":0,"errors":0,"skipped":0,
            "crashed":0,"timed_out":0}
    for path in files:
        started=time.monotonic()
        timed_out=False
        try:
            # Executing a test file as a script only starts the tests when the file carries a
            # __main__ guard, and 695 of the 2019 unittest files in this repository (34%,
            # measured) do not. Such a run exits 0 having executed nothing, so the audit counted
            # zero tests and zero failures for the file - a failing test became invisible rather
            # than red, which understates the whole corpus health report.
            proc=_PATCH._run_tests(repo,_PATCH.suite_argv(sys.executable,path),
                                   timeout_s,_PATCH._source_env(path))
            timed_out=proc["timed_out"]
            returncode=-1 if timed_out else proc["returncode"]
            combined=_text(proc["stdout"])+"\n"+_text(proc["stderr"])
            if timed_out:
                combined+="\nTIMED_OUT_AFTER_"+str(timeout_s)+"s"
        except _PATCH.PatchSearchError as exc:
            # This is a corpus report, not a green-only executor. A supervised
            # budget refusal is one red file unit; preserve the reason, then
            # continue to the remaining files. Unexpected runner errors still
            # propagate rather than being disguised as ordinary test failures.
            if str(exc)!="TEST_OUTPUT_LIMIT_EXCEEDED":
                raise
            returncode=-1
            combined=str(exc)
        elapsed=round(time.monotonic()-started,6)
        ran,passed,failures,errors,skipped,reported_duration,crashed=_counts(
            combined,returncode if returncode is not None else 1)
        if timed_out:
            # A hung file never printed a summary, so it produced no evidence
            # of passing anything. Count it as a crashed unit regardless.
            crashed=True
            passed=0
            ran=ran if ran else 0
        rec={
          "path":str(path.relative_to(repo)).replace("\\","/"),
          "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
          "exit_code":returncode,
          "tests":ran,
          "passed":passed,
          "failed":failures,
          "errors":errors,
          "skipped":skipped,
          "crashed":crashed,
          "timed_out":timed_out,
          "duration_s":elapsed,
          "reported_test_duration_s":reported_duration,
        }
        if returncode!=0:
            # Keep the tail of the output so the report says WHY the file is
            # red. Without it the report would name a failing file and give the
            # reader nothing to act on.
            rec["failure_tail"]=combined[-2000:].replace("\n"," ")
        records.append(rec)
        totals["files"]+=1; totals["tests"]+=ran; totals["passed"]+=passed
        totals["failed"]+=failures; totals["errors"]+=errors; totals["skipped"]+=skipped
        if crashed:
            totals["crashed"]+=1
        if timed_out:
            totals["timed_out"]+=1
        # The audit is a REPORT. Aborting on the first red file meant the
        # capability could only ever produce a report for a corpus that was
        # already green, so the rate it reported was always 100 percent and
        # carried no information. The report is the deliverable; whether the
        # corpus is clean is output_verified below, which stays strict.
    scored=totals["tests"]+totals["crashed"]
    pass_rate=(totals["passed"]/scored) if scored else 0.0
    totals["pass_rate"]=round(pass_rate,6)
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
      "crashed_count":totals["crashed"],
      "timed_out_count":totals["timed_out"],
      "pass_rate":totals["pass_rate"],
      # "The report is a faithful account of this run" -- separate from
      # "the corpus is clean", which is output_verified and which stays strict.
      "report_verified":_report_is_consistent(raw,records,totals),
      "output_verified":(totals["failed"]==0 and totals["errors"]==0
                         and totals["crashed"]==0 and totals["timed_out"]==0),
    }
