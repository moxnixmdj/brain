"""Does the issue text contain the oracle, in executable form?

Measured fact (THE_ORACLE_WAS_NOT_HANDED_TO_US): 43 of 45 real fix commits require a
test that does not exist in the parent tree, and the benchmark constructs its tasks so
that this is always true. So P(oracle) from the test suite is 0 by construction, and
every engine in this repo refuses entry before generation begins.

But the benchmark's own validation pipeline does not conjure the oracle either: it
applies the human's test patch and confirms fail2pass. A human, given only the issue,
writes that test by reading the issue. The question this script answers, mechanically
and with zero model calls:

    of 45 real fix commits, on how many does the issue/PR body already contain
    a concrete call with an expected-vs-actual pair, a traceback, or a runnable
    reproducer -- i.e. enough to assemble an executable assertion?

Classification is pure regex over fenced code blocks and prose. It is deliberately
coarse and deliberately *conservative*: a row counts as ORACLE_IN_ISSUE only if a
fenced block contains something a test could be built from (a call, an assert, an
exception), not merely the identifier names.

Verdicts:
    ORACLE_IN_ISSUE   a code block shows a call/assert/error the fix must satisfy
    PROSE_ONLY        an issue exists but no executable fragment
    NO_ISSUE          no associated issue or PR body was retrievable
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import time
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
CORPUS = REPO / "canonical" / "corpus" / "single_line_fix_commits_20261123_V1.json"

SLUGS = {"attrs": "python-attrs/attrs", "click": "pallets/click",
         "httpx": "encode/httpx", "jinja": "pallets/jinja",
         "more-itertools": "more-itertools/more-itertools",
         "packaging": "pypa/packaging", "pluggy": "pytest-dev/pluggy",
         "starlette": "encode/starlette", "tqdm": "tqdm/tqdm",
         "urllib3": "urllib3/urllib3", "werkzeug": "pallets/werkzeug",
         "flask": "pallets/flask", "boltons": "mahmoud/boltons",
         "pyjwt": "jpadilla/pyjwt"}

FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
# A fragment a test can be built from. Deliberately requires an *operation*,
# not just a bare identifier.
CALL = re.compile(r"\b[A-Za-z_][\w.]*\s*\(")
ASSERT = re.compile(r"\bassert\b|\bshould\b|\bexpected\b|\breturns?\b.*\bnot\b")
ERROR = re.compile(r"Traceback \(most recent call last\)|"
                   r"\b[A-Z]\w*(?:Error|Exception|Warning)\b\s*[:(]")
RAISES = re.compile(r"raises?\b[^\n]{0,40}\b[A-Z]\w*(?:Error|Exception)\b")


CACHE = pathlib.Path("/tmp/rel/gh_cache")
CACHE.mkdir(parents=True, exist_ok=True)


def gh(path: str, attempts: int = 6) -> Any:
    """Cached, retried GitHub API. A flaky fetch silently becomes a fake PROSE_ONLY,
    which would understate the oracle rate -- so never let a transient 502 do that."""
    key = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", path) + ".json")
    if key.exists():
        try:
            return json.loads(key.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            key.unlink()
    for attempt in range(attempts):
        done = subprocess.run(["gh", "api", path], capture_output=True, text=True,
                              errors="replace")
        if done.returncode == 0 and done.stdout.strip():
            try:
                payload = json.loads(done.stdout)
            except json.JSONDecodeError:
                payload = None
            if payload is not None:
                key.write_text(json.dumps(payload), encoding="utf-8")
                return payload
        time.sleep(1.5 * (attempt + 1))
    return None


def classify(body: str) -> tuple[str, list[str]]:
    blocks = [b.strip() for b in FENCE.findall(body or "") if b.strip()]
    reasons: list[str] = []
    for block in blocks:
        hits = []
        if ERROR.search(block):
            hits.append("traceback")
        if RAISES.search(block):
            hits.append("raises")
        if ASSERT.search(block):
            hits.append("assertion")
        if CALL.search(block) and len(block.splitlines()) >= 1:
            hits.append("call")
        if "traceback" in hits or ("raises" in hits and "call" in hits) or \
                ("assertion" in hits and "call" in hits):
            return "ORACLE_IN_ISSUE", hits
        if hits:
            reasons.append("+" .join(hits))
    if not (body or "").strip():
        return "NO_ISSUE", []
    return "PROSE_ONLY", reasons[:3]


CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*#(\d+)", re.I)


def one(entry: dict[str, Any]) -> dict[str, Any]:
    slug = SLUGS.get(entry["repo"])
    row: dict[str, Any] = {"repo": entry["repo"], "commit": entry["commit"][:10]}
    if not slug:
        return {**row, "verdict": "NO_ISSUE", "note": "no slug"}
    bodies: list[str] = []
    pull_meta: list[str] = []
    pulls = gh(f"repos/{slug}/commits/{entry['commit']}/pulls") or []
    for pull in pulls:
        pull_meta.append(f"pr#{pull['number']}")
        if pull.get("body"):
            bodies.append(pull["body"])
    commit = gh(f"repos/{slug}/commits/{entry['commit']}")
    message = (commit or {}).get("commit", {}).get("message") or ""
    if message:
        bodies.append(message)

    # The PR body is usually just "Fixes #1354". The oracle, if it exists, is in the
    # linked ISSUE (and its comments), not in the PR. Follow the references.
    refs = sorted({int(n) for text in bodies for n in CLOSES.findall(text)})
    for number in refs[:3]:
        issue = gh(f"repos/{slug}/issues/{number}")
        if not issue or "pull_request" in issue:
            continue
        pull_meta.append(f"issue#{number}")
        bodies.append(f"{issue.get('title','')}\n{issue.get('body') or ''}")
        comments = gh(f"repos/{slug}/issues/{number}/comments?per_page=20") or []
        for comment in comments:
            if comment.get("body"):
                bodies.append(comment["body"])
    if not bodies:
        bodies.append(message)
    body = "\n\n".join(bodies)
    verdict, reasons = classify(body)
    row.update({"verdict": verdict, "sources": pull_meta[:6],
                "body_chars": len(body), "reasons": reasons,
                "fetched": pull_meta[:6],
                "has_fence": "```" in body})
    if pulls:
        row["pr"] = pulls[0].get("html_url", "")
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--only", default="")
    args = parser.parse_args(argv)

    tasks = json.loads(CORPUS.read_text(encoding="utf-8"))["tasks"]
    wanted = {p.strip() for p in args.only.split(",") if p.strip()}
    if wanted:
        tasks = [t for t in tasks if any(t["commit"].startswith(w) for w in wanted)]

    rows = []
    for index, entry in enumerate(tasks, 1):
        row = one(entry)
        rows.append(row)
        print(f"[{index}/{len(tasks)}] {row['repo']:14s} {row['commit']} "
              f"{row['verdict']:16s} {row.get('body_chars', 0):6d}ch "
              f"{','.join(row.get('reasons') or [])[:30]}", flush=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    total = len(rows) or 1
    receipt = {
        "schema": "DOES_THE_ISSUE_CONTAIN_THE_ORACLE_V1",
        "question": "on how many of the 45 real fix commits does the issue/PR body "
                    "already carry an executable fragment a test can be built from?",
        "method": "regex over fenced code blocks; zero model calls",
        "counts": dict(sorted(counts.items())),
        "rate": {k: round(v / total, 4) for k, v in sorted(counts.items())},
        "rows": rows,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print("\n== counts")
    for name, count in receipt["counts"].items():
        print(f"  {name:18s} {count:2d}  {100*count/total:5.1f}%")
    print(f"\nreceipt -> {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
