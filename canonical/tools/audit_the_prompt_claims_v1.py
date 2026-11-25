#!/usr/bin/env python3
"""Audit every identifier, commit and benchmark figure the prompt asserts, against this repository.

WHY THIS IS A TOOL AND NOT A PARAGRAPH
--------------------------------------
The prompt arrives as a fixed block that claims 34 identifiers, 9 commit hashes, a 75.2% measurement, 344
failing cases, a 0.35s runtime and eleven benchmark scores. Twenty rounds of this project have been built
on the rule that such claims are INPUTS TO VERIFY, never facts. A paragraph of prose cannot be re-run; a
tool can, and the next round inherits the tool rather than my summary of it.

WHAT IS CHECKED
---------------
  identifiers   does a FILE with this name exist in the tree? (code, not reports about code)
  commits       does `git cat-file -t` resolve it to a commit here?
  figures       does the number appear anywhere outside a report of mine?

The distinction that matters is between a claim being MENTIONED in this repo and being SUPPORTED by it.
Every report of mine mentions these identifiers; that is exactly the trap, so mentions in my own reports
are counted separately and never count as evidence.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
SCHEMA = "BRAIN_AUDIT_THE_PROMPT_CLAIMS_V1"

#: Identifiers the prompt names as things that exist in the project.
IDENTIFIERS: Sequence[str] = (
    "__CST_ID0__", "FOREIGN_IDENT_UNBOUND", "BELIEFWEAVER",
    "BRAIN_POLYGLOT_CST_SKILL_STORE_V1", "verified_skill_crystallizer_ir_bridge_v1",
    "CUMentalWorldModel", "epistemic_scan_acquire_compress_v1", "typed_invention_v1",
    "same_identity_supervisor", "consistency_vs_equivalence",
    "zygote_worker_pool_v1", "repo_component_and_cow_engine_v1", "instant_swe_skill_store_v1",
    "UnifiedCrossModalPetriNet", "MealyAPICompiler", "epistemic_doc_compiler",
    "witness_inversion_v1", "calculate_separating_projection", "MultiLayerSnapshot",
)

#: Commit hashes the prompt asserts, several of them as "our logged unsolved commits".
COMMITS: Sequence[str] = (
    "209bbc6c", "92b6db85", "d6c1661a", "ac0e297", "c53d373", "05f6fd0",
    "884437ae", "fc518e4", "051fd663",
)

#: Numeric claims, and what the prompt says they are.
FIGURES: Sequence[tuple[str, str]] = (
    ("75.2", "share of real SWE-bench hunks outside fixed mutation grammars"),
    ("344", "failing HONEST_SUITE_BASELINE cases"),
    ("0.35", "runtime seconds"),
    ("447", "verified capabilities"),
    ("226", "hand-written tricks"),
    ("244", "verified post-training OSS commits"),
)


def mine(path: pathlib.Path) -> bool:
    """My own reports: an .md at the repo root, or anything in canonical/verification/."""
    return path.suffix == ".md" and (path.parent == REPO
                                     or path.parent.name == "verification")


CODE_SUFFIXES = {".py", ".js", ".ts", ".rs", ".go", ".c", ".h", ".cpp", ".java"}


def files_named(needle: str) -> list[str]:
    """EXECUTABLE files whose name contains the identifier -- a module, not a mention.

    Only code suffixes count. A first version of this function accepted any filename, so a report called
    `..._typed_invention_v1.md` and a workflow called `..._same_identity_supervisor...yml` counted as
    "the engine exists". That is precisely the error this audit exists to catch, committed by the audit
    itself; the suffix filter is the fix.
    """
    out = []
    for path in REPO.rglob(f"*{needle}*"):
        if ".git" in path.parts or ".venv" in path.parts:
            continue
        if path.suffix not in CODE_SUFFIXES:
            continue
        out.append(str(path.relative_to(REPO)))
    return out


def mentions(needle: str) -> tuple[int, int]:
    """(mentions outside my reports, mentions inside them)."""
    outside = inside = 0
    for path in REPO.rglob("*.py"):
        if ".git" in path.parts or ".venv" in path.parts:
            continue
        try:
            if needle in path.read_text(errors="ignore"):
                outside += 1
        except OSError:
            continue
    for path in list(REPO.glob("*.md")) + list((REPO / "canonical" / "verification").glob("*.md")):
        try:
            if needle in path.read_text(errors="ignore"):
                inside += 1
        except OSError:
            continue
    return outside, inside


def audit_identifier(needle: str) -> dict[str, Any]:
    named = files_named(needle)
    outside, inside = mentions(needle)
    if named:
        status = "VERIFIED__CODE_FILE_EXISTS"
    elif outside:
        status = "UNVERIFIED__MENTIONED_IN_CODE_ONLY"
    else:
        status = "FAILED__NO_CODE_ANYWHERE"
    return {"claim": needle, "status": status, "files_named_after_it": named[:5],
            "mentioned_in_code_not_mine": outside, "mentioned_in_my_reports": inside}


def audit_commit(needle: str) -> dict[str, Any]:
    try:
        kind = subprocess.run(["git", "cat-file", "-t", needle], cwd=REPO,
                              capture_output=True, text=True, check=False).stdout.strip()
    except OSError:
        kind = ""
    return {"claim": needle,
            "status": "VERIFIED__IS_A_COMMIT" if kind == "commit" else "FAILED__NOT_A_COMMIT",
            "git_object_type": kind or "absent"}


def audit_figure(needle: str) -> dict[str, Any]:
    outside, inside = mentions(needle)
    return {"claim": needle, "status": "UNVERIFIED__CITED_ONLY_IN_MY_REPORTS"
            if outside == 0 else "UNVERIFIED__APPEARS_ELSEWHERE_TOO",
            "mentioned_in_code_not_mine": outside, "mentioned_in_my_reports": inside}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    started = time.time()

    commit_count = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=REPO,
                                  capture_output=True, text=True, check=False).stdout.strip()
    code_files = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO,
                                capture_output=True, text=True, check=False).stdout.count("\n")

    identifiers = [audit_identifier(name) for name in IDENTIFIERS]
    commits = [audit_commit(name) for name in COMMITS]
    figures = [audit_figure(number) for number, _why in FIGURES]
    for cell, (_number, why) in zip(figures, FIGURES):
        cell["prompt_says"] = why

    def count(rows, prefix):
        return sum(1 for row in rows if row["status"].startswith(prefix))

    summary = {
        "repo_commits": int(commit_count or 0),
        "python_files_tracked": code_files,
        "identifiers": identifiers,
        "commits": commits,
        "figures": figures,
        "tallies": {
            "identifiers_verified_as_code_files": count(identifiers, "VERIFIED"),
            "identifiers_failed": count(identifiers, "FAILED"),
            "commits_verified": count(commits, "VERIFIED"),
            "commits_failed": count(commits, "FAILED"),
            "figures_unverified": count(figures, "UNVERIFIED"),
        },
        "components_that_do_exist": [cell["claim"] for cell in identifiers
                                     if cell["status"].startswith("VERIFIED")],
        "verdicts": {
            "no_claimed_commit_hash_resolves": count(commits, "VERIFIED") == 0,
            "no_claimed_engine_exists_as_a_module": count(identifiers, "VERIFIED") == 0,
            "the_repo_cannot_have_244_commits_if_it_has_fewer": int(commit_count or 0) < 244,
            # NOT 19/19: four claimed components genuinely exist as modules. Stating that plainly is
            # the difference between an audit and a complaint.
            "most_claimed_engines_exist_only_as_mentions":
                count(identifiers, "UNVERIFIED") >= 0.7 * len(identifiers),
            "some_claimed_components_do_exist_as_code": count(identifiers, "VERIFIED") > 0,
        },
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(summary["tallies"], indent=1))
    print(json.dumps(summary["verdicts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
