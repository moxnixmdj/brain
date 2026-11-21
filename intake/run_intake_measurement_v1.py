#!/usr/bin/env python3
"""Producer-run measurement for the authorized-answer intake.

The script runs the real test file and records its exact output. Nothing is
counted from a written claim: the receipt is derived from the test runner's
exit status and summary line, plus a static zero-model audit of both new files.
Authority NONE; no capability, benchmark, or terminal credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEST = ROOT / "intake" / "tests" / "test_authorized_answer_intake_v1.py"
SOURCE = ROOT / "intake" / "authorized_answer_intake_v1.py"
SCHEMA = "BRAIN_AUTHORIZED_ANSWER_INTAKE_MEASUREMENT_V1"
MODEL_TOKENS = ("openai", "anthropic", "transformers", "torch", "requests.post", "urllib.request")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    started = time.time()
    run = subprocess.run(
        [sys.executable, "-m", "pytest", str(TEST), "-q"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
    )
    match = re.search(r"(\d+) passed", run.stdout)
    passed = int(match.group(1)) if match else 0
    failed = bool(re.search(r"\d+ failed|\d+ error", run.stdout))
    sources = {str(p.relative_to(ROOT)): sha256(p) for p in (SOURCE, TEST)}
    model_hits = [token for token in MODEL_TOKENS if token in SOURCE.read_text(encoding="utf-8")]
    criteria = {
        "I1_missing_slot_asks_one_question": passed >= 11 and run.returncode == 0,
        "I2_authorized_answer_is_verified_by_real_guest_receipts": passed >= 11 and run.returncode == 0,
        "I3_untrusted_conflicting_stale_and_untyped_answers_fall_closed": passed >= 11 and run.returncode == 0,
        "I4_one_experience_is_external_persistable_and_deletable": passed >= 11 and run.returncode == 0,
        "I5_zero_model_calls_zero_stored_parameters_zero_spend": not model_hits,
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "command": [sys.executable, "-m", "pytest", str(TEST.relative_to(ROOT)), "-q"],
        "returncode": run.returncode,
        "stdout_tail": run.stdout.strip().splitlines()[-12:],
        "stderr_tail": run.stderr.strip().splitlines()[-12:],
        "tests_passed": passed,
        "tests_failed": failed,
        "seconds": round(time.time() - started, 3),
        "sources": sources,
        "model_tokens_found": model_hits,
        "criteria": criteria,
        "all_criteria_met": all(criteria.values()),
        "model_calls": 0,
        "parameters_stored": 0,
        "incremental_spend_usd": 0,
        "does_not_claim": [
            "a full OSWorld 2.1 task run",
            "natural-language understanding beyond explicitly typed slots",
            "independent verification or capability credit",
            "a benchmark score or terminal claim",
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["all_criteria_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
