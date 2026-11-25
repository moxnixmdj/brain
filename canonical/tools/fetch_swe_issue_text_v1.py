#!/usr/bin/env python3
"""Fetch the real issue text for SWE-bench Verified instances, from GitHub, once.

WHY THIS IS NOT A MODEL CALL
----------------------------
This is a plain HTTPS fetch of public issue bodies plus our own parsing. No model, no search API, no
summariser. It is the same class of operation as reading a README, which §2 explicitly allows as the
instant-knowledge channel.

WHY IT IS ALLOWED FOR TESTING AT ALL
------------------------------------
The task text is what a solver is GIVEN at t=0, not the answer. The answer (the reference patch) is never
fetched. Nothing here tells our system which capability or which file is correct.

WHY IT IS NEEDED
----------------
The routing gate's failure was measured on four hand-written goals, which is not a sample. 80 SWE-bench
Verified instance ids appear in this repository's own receipts; their issue bodies are the real
distribution of what this system is asked to read.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "canonical" / "corpus" / "swe_verified_issue_text_20261124_V1.json"
RECEIPT = (REPO / "canonical" / "verification" /
           "FIX_CONTENT_IN_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json")


def instance_ids() -> list[str]:
    payload = json.loads(RECEIPT.read_text())
    return sorted(payload.get("per_task") or {})


def split_instance(instance: str) -> tuple[str, int]:
    owner_repo, number = instance.rsplit("-", 1)
    return owner_repo.replace("__", "/"), int(number)


def fetch(owner_repo: str, number: int) -> dict[str, str] | None:
    """One issue or pull request, by number. Issue bodies live at the issues endpoint."""
    for url in (f"repos/{owner_repo}/issues/{number}",
                f"repos/{owner_repo}/pulls/{number}"):
        result = subprocess.run(["gh", "api", url, "--jq",
                                 "{title: .title, body: .body, html_url: .html_url}"],
                                capture_output=True, text=True, check=False, timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            try:
                cell = json.loads(result.stdout)
            except ValueError:
                continue
            if cell.get("title") or cell.get("body"):
                return {"title": cell.get("title") or "", "body": cell.get("body") or "",
                        "url": cell.get("html_url") or ""}
    return None


def main() -> int:
    ids = instance_ids()
    fetched: dict[str, dict[str, str]] = {}
    failed: list[str] = []
    for index, instance in enumerate(ids, 1):
        owner_repo, number = split_instance(instance)
        cell = fetch(owner_repo, number)
        if cell is None:
            failed.append(instance)
        else:
            fetched[instance] = cell
        if index % 10 == 0:
            print(f"  {index}/{len(ids)} fetched={len(fetched)} failed={len(failed)}", flush=True)
        time.sleep(0.15)                    # be a good citizen; the budget is 5000/hour

    lengths = [len(re.sub(r"\s+", " ", (c["title"] + " " + c["body"])).strip())
               for c in fetched.values()]
    payload = {
        "schema": "BRAIN_SWE_VERIFIED_ISSUE_TEXT_V1",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": ("GitHub issue and pull-request bodies for the instance ids recorded in "
                   "FIX_CONTENT_IN_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json. Reference patches and "
                   "test patches were NOT fetched."),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "network_during_build": 1, "kind_of_network": "plain public issue fetch"},
        "summary": {
            "instances_attempted": len(ids),
            "issue_text_fetched": len(fetched),
            "fetch_failed": failed,
            "median_text_chars": sorted(lengths)[len(lengths) // 2] if lengths else 0,
            "min_text_chars": min(lengths) if lengths else 0,
            "max_text_chars": max(lengths) if lengths else 0,
            "what_this_is_not": ("not a benchmark result. It is the distribution of the input this system "
                                 "is handed before it does anything, so that a gate measured on four "
                                 "hand-written goals can be measured on the real thing."),
        },
        "per_instance": fetched,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(payload["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
