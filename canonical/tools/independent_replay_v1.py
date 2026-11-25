#!/usr/bin/env python3
"""Replay generated candidates in fresh worktrees with a separate test runner.

This verifier shares no code with the generator: it reads only the receipt and
the pinned repositories, writes the candidate into a fresh parent worktree,
copies the post-fix test file (the declared oracle), and runs pytest directly.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

SUMMARY = re.compile(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) errors?)?")


def fresh_bytecode(root: pathlib.Path) -> dict[str, str]:
    cache = root / ".brain_independent_pycache"
    cache.mkdir(exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPYCACHEPREFIX"] = str(cache)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), str(root), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    return env


def replay(row: dict, seconds: int) -> dict:
    repo = pathlib.Path(str(row["repo_path"])).resolve()
    sha = str(row["sha"])
    source = str(row["sources"][0])
    test = str(row["tests"][0])
    candidate = row.get("candidate")
    if not isinstance(candidate, str) or not candidate:
        return {"sha": sha, "stage": "NO_CANDIDATE", "verified": False}
    post_tests = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{test}"],
                                capture_output=True, text=True).stdout
    if not post_tests:
        return {"sha": sha, "stage": "NO_ORACLE", "verified": False}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        made = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                               str(worktree), f"{sha}^"], capture_output=True, text=True)
        if made.returncode != 0:
            return {"sha": sha, "stage": "WORKTREE_FAILED", "verified": False}
        try:
            test_file = worktree / test
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(post_tests, encoding="utf-8")
            source_file = worktree / source
            parent_source = source_file.read_text(encoding="utf-8")
            source_file.write_text(candidate, encoding="utf-8")
            command = [sys.executable, "-m", "pytest", test, "-q", "--tb=short",
                       "-p", "no:cacheprovider"]
            try:
                done = subprocess.run(command, cwd=worktree, capture_output=True,
                                      text=True, timeout=seconds, stdin=subprocess.DEVNULL,
                                      env=fresh_bytecode(worktree))
            except subprocess.TimeoutExpired:
                return {"sha": sha, "stage": "TIMEOUT", "verified": False}
            finally:
                source_file.write_text(parent_source, encoding="utf-8")
            output = done.stdout + done.stderr
            found = SUMMARY.search(output)
            passed = int(found.group(1)) if found else 0
            failed = int(found.group(2) or 0) if found else 0
            errors = int(found.group(3) or 0) if found else 0
            return {"sha": sha, "stage": "REPLAYED", "verified": done.returncode == 0
                    and passed > 0 and failed == 0 and errors == 0,
                    "passed": passed, "failed": failed, "errors": errors,
                    "returncode": done.returncode, "tail": output[-400:]}
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--entries", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args(argv)
    report = json.loads(pathlib.Path(args.receipt).read_text(encoding="utf-8"))
    entries = {str(item["sha"]): item for item in
               json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))}
    rows = []
    for row in report["rows"]:
        entry = dict(entries.get(str(row["sha"]), {}))
        entry.update({key: row.get(key) for key in ("sha", "candidate")})
        replayed = replay(entry, args.seconds)
        rows.append({"sha": str(row["sha"]), "generator_verified": bool(row.get("verified")),
                     **replayed})
    verified = sum(1 for row in rows if row["verified"])
    result = {"schema": "PROJECT_BRAIN_INDEPENDENT_REPLAY_V1",
              "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "authority": "NONE__RECEIPT_AND_PINNED_REPOSITORIES_ONLY",
              "rows": rows,
              "summary": {"rows": len(rows), "independently_verified": verified,
                          "model_calls": 0, "network_calls": 0},
              "verdict": "PASS" if verified == len(rows) and verified else "FAIL"}
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True),
                                      encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "summary": result["summary"],
                      "rows": [{"sha": row["sha"][:12], "verified": row["verified"],
                                "passed": row.get("passed"), "failed": row.get("failed")}
                               for row in rows]}, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
