#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from trusted_load_bearing_primary_admission import admission_errors
except ImportError:
    from execution_guard.load_bearing_primary_admission import admission_errors

ROOT = pathlib.Path.cwd().resolve()
QUOTIENT = "canonical/governance/FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json"
SENSITIVE_PREFIXES = (
    "canonical/action_intents/",
    "canonical/runtime/",
    "canonical/governance/",
    "canonical/capabilities/",
    "canonical/verification/",
    "execution_guard/",
    ".github/workflows/",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_at(ref: str, path: str):
    return json.loads(git("show", f"{ref}:{path}"))


def changed_files(base: str, head: str) -> list[str]:
    raw = git("diff", "--name-only", f"{base}...{head}")
    return [x for x in raw.splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ns = ap.parse_args()

    files = changed_files(ns.base, ns.head)
    sensitive = [x for x in files if any(x.startswith(p) for p in SENSITIVE_PREFIXES)]
    if not sensitive:
        print("LOAD_BEARING_ADMISSION_PASS no sensitive changes")
        return 0

    intents = [
        x for x in files
        if x.startswith("canonical/action_intents/") and x.endswith(".json")
    ]
    if len(intents) != 1:
        print("LOAD_BEARING_ADMISSION_FAIL")
        print(" - EXACTLY_ONE_ACTION_INTENT_REQUIRED")
        return 1

    quotient = load_at(ns.base, QUOTIENT)
    open_rows = quotient.get("independent_open_obligations")
    if (
        not isinstance(open_rows, list)
        or any(not isinstance(x, str) or not x.strip() for x in open_rows)
    ):
        print("LOAD_BEARING_ADMISSION_FAIL")
        print(" - CURRENT_OPEN_OBLIGATION_SET_INVALID")
        return 1

    intent = load_at(ns.head, intents[0])
    errors = admission_errors(intent, open_rows)
    if errors:
        print("LOAD_BEARING_ADMISSION_FAIL")
        for item in errors:
            print(" -", item)
        return 1

    binding = intent.get("load_bearing_primary") or {}
    print("LOAD_BEARING_ADMISSION_PASS")
    print(" open_obligation_count", len(open_rows))
    print(" direct_targets", ",".join(binding.get("open_obligation_ids") or []))
    print(
        " constructive_gap_targets",
        ",".join(binding.get("constructive_gap_for_open_obligation_ids") or []),
    )
    print(" scope_complete", bool(binding.get("scope_complete_discharge")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
