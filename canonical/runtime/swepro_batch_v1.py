"""Run many published SWE-bench Pro V2 instances and report what actually resolved.

WHY A DENOMINATOR MATTERS MORE THAN ANOTHER SOLVED INSTANCE
-----------------------------------------------------------
§A152–§A154 produced two green instances. Two is not a rate, and a rate is the only thing that
tells you which mechanism to build next. This module answers one question per instance:

    given the published repository, test patch and named tests, does the system resolve it?

WHAT "THE SYSTEM" MAY USE, AND WHAT IT MAY NOT
----------------------------------------------
It reads only what the benchmark publishes for a solver to read:
    * the repository at the true base commit
    * the published test patch and the named `fail_to_pass` / `pass_to_pass` tests
    * the `instruction.md` requirement text
    * the failing test's own source and its own data

It never reads `solution/gold_patch.diff`. That is the answer sheet, and an attempt that consults
it is not an attempt. `_forbidden` in this file is a guard, not a comment.

NO LEAKAGE INTO THE MEASUREMENT
-------------------------------
An attempt may install a candidate, run the test, and keep the candidate only if it passes. What
it must not do is let the test's *expected values* become a lookup table keyed on the input, which
would pass the test and generalise to nothing. `looks_like_a_lookup` refuses candidates that
contain the expected literals as bare constants, and the refusal is recorded rather than hidden.

A refusal that costs a true positive is the correct price. A pass that is a lookup is worse than
an honest failure, because it is reported as capability.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

# This file is run as a script as well as imported, and `sys.path[0]` is the file's own
# directory in the former case -- so `import canonical...` fails. Put the repo root on the path
# once, here, instead of repeating the fix in every caller (measured, twice).
_REPO = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

__all__ = ["run_one", "run_batch", "forbidden_paths_touched"]

# The answer sheet. Nothing in this module may read these into an attempt.
FORBIDDEN = ("solution/gold_patch.diff", "solution/solve.sh")


def _forbidden(rel: str) -> bool:
    return any(rel.endswith(f) for f in FORBIDDEN)


def forbidden_paths_touched(touched: list[str]) -> bool:
    """True if any path an attempt read is the answer sheet. Used as an assertion by callers."""
    return any(_forbidden(p) for p in touched)


def _grade(room: pathlib.Path, f2p: list[str], p2p: list[str], python: str) -> dict:
    import os
    from canonical.runtime.swepro_instance_harness_v1 import _import_roots
    ids = list(f2p) + list(p2p)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(_import_roots(room))}
    proc = subprocess.run([python, "-m", "pytest", "-v", "--tb=no", "-p", "no:cacheprovider", *ids],
                          cwd=room, capture_output=True, text=True, env=env, timeout=1800)
    out = proc.stdout + proc.stderr
    seen: dict[str, bool] = {}
    for line in out.splitlines():
        parts = line.split()
        if parts and "::" in parts[0]:
            if "PASSED" in parts:
                seen[parts[0]] = True
            elif "FAILED" in parts or "ERROR" in parts:
                seen[parts[0]] = False
    unseen = [t for t in ids if seen.get(t) is None]
    return {"resolved": not unseen and all(seen.get(t) is True for t in ids),
            "unseen": unseen,
            "tail": [l for l in out.splitlines() if "passed" in l or "failed" in l][-1:]}


def _read_failure(room: pathlib.Path, test_id: str, python: str) -> str:
    import os
    from canonical.runtime.swepro_instance_harness_v1 import _import_roots
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(_import_roots(room))}
    proc = subprocess.run([python, "-m", "pytest", test_id, "-q", "--tb=long", "-p", "no:cacheprovider"],
                          cwd=room, capture_output=True, text=True, env=env, timeout=900)
    return proc.stdout + proc.stderr


def _module_of(test_id: str) -> str:
    return test_id.split("::")[0]


def _test_file(room: pathlib.Path, test_id: str) -> pathlib.Path | None:
    p = room / _module_of(test_id)
    return p if p.is_file() else None


def run_one(instance: str, workdir: pathlib.Path, python: str, *, fetch_only: bool = False) -> dict:
    """One instance: build, apply the published test patch, try to resolve, report honestly."""
    from canonical.runtime import swepro_instance_harness_v1 as H

    t0 = time.time()
    # Make BOTH absolute -- but do NOT resolve(). A venv's `bin/python` is a SYMLINK to the system
    # interpreter, so `.resolve()` turns a venv into /usr/bin/python3.11 and every `-m pytest`
    # dies with "No module named pytest". Measured exactly that: the venv was correct and the
    # path normalisation destroyed it. `absolute()` normalises without following the final link.
    python = str(pathlib.Path(os.path.abspath(python)))
    workdir = pathlib.Path(os.path.abspath(workdir))
    if workdir.exists():
        shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True, exist_ok=True)
    rec: dict = {"instance": instance, "stage": "start"}

    try:
        from canonical.runtime.derive_from_the_failure_v1 import load_contract
        meta = H.fetch_instance(instance, workdir / "meta")
        contract = load_contract(workdir / "meta")
        rec["f2p"], rec["p2p"] = contract["fail_to_pass"], contract["pass_to_pass"]
        # Guard: the answer sheet must never have been fetched into the attempt workspace.
        if any(_forbidden(str(p)) for p in (workdir / "meta").iterdir()):
            rec["error"] = "ANSWER_SHEET_PRESENT"
            return rec
        repo_slug, fix_sha = H._sha_from_instance(instance)
        base = H.resolve_base_commit(repo_slug, fix_sha)
        rec.update(repo=repo_slug, base=base)
        room = H.build_room(repo_slug, base, workdir / "room")
        ok, msg = H._apply(room, meta["tests/test_patch.patch"])
        if not ok:
            rec.update(stage="test_patch", error=msg[:200])
            return rec
        rec["stage"] = "baseline"
        before = _grade(room, contract["fail_to_pass"], contract["pass_to_pass"], python)
        rec["baseline"] = before
        if before["resolved"]:
            # The instance resolves with no change. That is a bench defect or a state problem,
            # and either way it is not our capability. Recorded, never counted as a success.
            rec["outcome"] = "ALREADY_RESOLVED_BEFORE_ANY_CHANGE"
            return rec
        if fetch_only:
            rec["outcome"] = "BASELINE_ONLY"
            return rec

        rec["stage"] = "attempt"
        attempt = _attempt(room, contract, python)
        rec["attempt"] = attempt
        after = _grade(room, contract["fail_to_pass"], contract["pass_to_pass"], python)
        rec["after"] = after
        rec["outcome"] = ("RESOLVED" if after["resolved"] and not after["unseen"]
                          else "NOT_RESOLVED")
    except Exception as exc:  # noqa: BLE001 - a batch must survive one bad instance
        rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
        rec["outcome"] = "ERROR"
    finally:
        rec["seconds"] = round(time.time() - t0, 1)
    return rec


def _attempt(room: pathlib.Path, contract: dict, python: str) -> dict:
    """Try the mechanisms in the order they cost: symbol, then body search.

    Every branch reports whether it fired and what it found. A branch that cannot read the
    failure returns NOT_DERIVABLE rather than looping, and the loop stops on the first branch
    that changes the repository.
    """
    from canonical.runtime import derive_from_the_failure_v1 as D
    from canonical.runtime import search_a_body_under_the_test_v1 as S

    f2p = contract["fail_to_pass"]
    if not f2p:
        return {"branch": "none", "note": "no fail_to_pass named"}
    test_id = f2p[0]
    out = _read_failure(room, test_id, python)
    miss = D.read_missing_member(out)
    if miss is not None:
        owner, name, is_module = miss
        tf = _test_file(room, test_id)
        if tf is None:
            return {"branch": "missing_member", "result": "TEST_FILE_NOT_FOUND"}
        params = D.call_signature_at(tf.read_text(encoding="utf-8", errors="replace"), name) or []
        loc = D.locate_class(room, owner)
        if loc is None:
            return {"branch": "missing_member", "result": "OWNER_NOT_FOUND", "owner": owner}
        rep = S.search_body(room,
                            owner_path=loc[0], owner_class=owner, member=name, params=params,
                            test_ids=list(f2p) + list(contract["pass_to_pass"]),
                            test_source=tf.read_text(encoding="utf-8", errors="replace"),
                            python=python)
        return {"branch": "missing_member", "owner": owner, "member": name, "params": params,
                "search": {k: rep.get(k) for k in ("found", "outcome", "candidate", "tried")}}
    # THE LAST `E ` LINE IS THE ERROR; the first match anywhere is often SOURCE CODE from the
    # traceback context. Measured: `RepresenterError("recursive objects are not allowed: %r" % d`
    # and `ValueError, TypeError) as e:` are lines of the file under test, not failures.
    errs = [l[1:].strip() for l in out.splitlines() if l.startswith("E ")]
    if not errs:
        errs = [l.strip() for l in out.splitlines() if "Error" in l or "Failed" in l]
    failure = (errs[-1] if errs else "")[:160]

    # BRANCH 2: an operator-protocol gap. The failure names the operator and both operand types;
    # the method's name is the language's own mapping, and it belongs on the class named second.
    gap = D.read_operator_gap(out)
    if gap is not None:
        loc = D.locate_class(room, gap["target_class"])
        if loc is not None:
            tf2 = _test_file(room, test_id)
            src_txt = tf2.read_text(encoding="utf-8", errors="replace") if tf2 else ""
            rep = S.search_body(room, owner_path=loc[0], owner_class=gap["target_class"],
                                member=gap["method"], params=["other"],
                                test_ids=list(f2p) + list(contract["pass_to_pass"]),
                                test_source=src_txt, python=python)
            return {"branch": "operator_gap", "gap": gap,
                    "search": {k: rep.get(k) for k in ("found", "outcome", "candidate", "tried")}}
        return {"branch": "operator_gap", "gap": gap, "result": "TARGET_CLASS_NOT_FOUND"}

    return {"branch": "edit", "result": "NOT_DERIVABLE_BY_THIS_SPACE", "failure": failure}


def run_batch(instances: list[str], workdir: pathlib.Path, python: str) -> dict:
    workdir = pathlib.Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, inst in enumerate(instances, 1):
        rec = run_one(inst, workdir / f"i{i:03d}", python)
        rows.append(rec)
        print(f"[{i}/{len(instances)}] {rec.get('outcome'):<32} {inst[:64]}", flush=True)
        (workdir / "results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    done = [r for r in rows if r.get("outcome") not in ("ERROR",)]
    return {
        "n": len(rows),
        "resolved": [r["instance"] for r in rows if r.get("outcome") == "RESOLVED"],
        "not_resolved": [r["instance"] for r in rows if r.get("outcome") == "NOT_RESOLVED"],
        "errors": [r["instance"] for r in rows if r.get("outcome") == "ERROR"],
        "already": [r["instance"] for r in rows if r.get("outcome") == "ALREADY_RESOLVED_BEFORE_ANY_CHANGE"],
        "baseline_only": [r["instance"] for r in rows if r.get("outcome") == "BASELINE_ONLY"],
        "measured": len(done),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: swepro_batch_v1.py <instances.json|names> <workdir> <python>", file=sys.stderr)
        return 2
    src = pathlib.Path(argv[1])
    names = json.loads(src.read_text()) if src.is_file() else argv[1].split(",")
    rep = run_batch(names, pathlib.Path(argv[2]), argv[3])
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in rep.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
