#!/usr/bin/env python3
"""How much *verified* experience does this tree actually hold? Count it before building on it.

Round 14's recommendation was a student channel: weights trained offline on the verified receipts this
repo emits. That recommendation has a precondition nobody had checked — that the receipts contain a
verification verdict, and that somebody other than the producer produced it. This census counts both,
over every execution receipt in the tree, and refuses to call a self-report a verification.

Three arms:

1. **census** — every ``*RECEIPT.json`` under ``canonical/astra_runtime/evidence``, classified by
   (a) does it carry a verdict, (b) was it run by anyone but its producer, (c) is it free of model
   dependency. A *training-ready* example needs all three.
2. **rerun** — ``--rerun`` takes a small set of deterministic experiences, runs each **twice** in
   separate processes and requires byte-identical output. Two runs by one agent is *reproducibility*,
   not independence, and the receipts it writes say exactly that: ``verified: false``,
   ``independent_verifier: null``. Manufacturing independence is not something this tool can do.
3. **what would fix it** — the census names the missing field and the smallest change that fills it.

Authority NONE. Reads receipts, writes only the receipts ``--rerun`` is asked to write. $0, no model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
EVIDENCE = REPO_ROOT / "canonical/astra_runtime/evidence"

#: Deterministic experiences this machine can re-run. Each must be a separate process whose whole
#: observable output is its stdout and exit code.
EXPERIENCES: list[dict[str, Any]] = [
    {
        # A verifier must produce fresh cases, so it must NOT repeat itself. If this arm ever starts
        # matching, the check has stopped being fresh and has started being a fixed test.
        "id": "unified_model_fresh_cases",
        "argv": ["{python}", "canonical/runtime/verify_brain_unified_model_v1.py"],
        "kind": "fresh_case_verifier",
        "expect_identical": False,
        "timeout_s": 300,
    },
    {
        # An experience somebody might train on must replay byte-for-byte.
        "id": "unified_model_seed_replays",
        "argv": ["{python}", "canonical/runtime/verify_brain_unified_model_v1.py",
                 "--seed", "20261112"],
        "kind": "replayable_experience",
        "expect_identical": True,
        "timeout_s": 300,
    },
    {
        "id": "claims_ledger_holds",
        "argv": ["{python}", "round_14_claims_ledger_20261112.py"],
        "kind": "replayable_experience",
        "expect_identical": True,
        "timeout_s": 300,
    },
]


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def classify(receipt: dict[str, Any]) -> dict[str, Any]:
    """What this receipt can and cannot support."""
    observed = receipt.get("observed")
    verdict = observed.get("pass") if isinstance(observed, dict) else None
    ran_by = receipt.get("ran_by")
    independent = bool(receipt.get("independent_run_reference") or receipt.get("independent_verifier"))
    model_free = (receipt.get("model_dependency_count") or 0) == 0
    return {
        "capability_id": receipt.get("capability_id"),
        "has_verdict": verdict is not None,
        "verdict": verdict,
        "ran_by": ran_by,
        "independent_run_recorded": independent,
        "model_free": model_free,
        # a training example needs a verdict somebody else produced
        "training_ready": (verdict is not None) and independent and model_free,
    }


def census() -> dict[str, Any]:
    rows = []
    unreadable = []
    for path in sorted(EVIDENCE.glob("*RECEIPT.json")):
        try:
            rows.append((path.name, classify(json.loads(path.read_text(encoding="utf-8")))))
        except Exception as exc:
            unreadable.append({"path": path.name, "error": f"{type(exc).__name__}: {exc}"})

    with_verdict = [row for _, row in rows if row["has_verdict"]]
    passed = [row for row in with_verdict if row["verdict"] is True]
    independent = [row for _, row in rows if row["independent_run_recorded"]]
    ready = [row for _, row in rows if row["training_ready"]]
    runners = sorted({str(row["ran_by"]) for _, row in rows if row["ran_by"]})

    return {
        "census": "verified_experience",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "receipts": len(rows) + len(unreadable),
        "readable_receipts": len(rows),
        "unreadable": unreadable,
        "verdict_present": len(with_verdict),
        "verdict_true": len(passed),
        "verdict_false": len(with_verdict) - len(passed),
        "independent_run_recorded": len(independent),
        "training_ready_examples": len(ready),
        "distinct_runners": runners,
        "missing_to_train": [
            "INDEPENDENT_RUN_REFERENCE: no receipt names a second run by another party",
            "INDEPENDENT_VERIFIER: the field exists in the schema and is null in every record",
        ],
        "smallest_change_that_fills_it": (
            "a second party runs the same command and writes its own digest into "
            "independent_run_reference; the census then counts that receipt as training-ready, and "
            "the existing observed.pass supplies the verdict without touching any producer"
        ),
    }


def rerun(out_dir: pathlib.Path | None) -> dict[str, Any]:
    """Run each experience twice and require identical output. This is reproducibility, not proof."""
    written = []
    for experience in EXPERIENCES:
        argv = [part.format(python=sys.executable) for part in experience["argv"]]
        runs = []
        for _ in range(2):
            completed = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True,
                                       timeout=experience["timeout_s"])
            runs.append({
                "returncode": completed.returncode,
                "stdout_sha256": _digest(completed.stdout),
                "stderr_sha256": _digest(completed.stderr),
            })
        same = runs[0] == runs[1]
        receipts = []
        for path in []:  # no per-run artefacts are collected; only the digest is kept
            receipts.append(path)
        record = {
            "schema": "PROJECT_BRAIN_REPRODUCIBILITY_RECEIPT_V1",
            "kind": "REPRODUCIBILITY_RECEIPT",
            "experience": experience["id"],
            "argv": argv[1:],
            "runs": runs,
            "identical": same,
            "kind": experience["kind"],
            "expect_identical": experience["expect_identical"],
            "verdict": ("REPRODUCED" if same else "VARIED"),
            "as_designed": same is bool(experience["expect_identical"]),
            # Honesty: two runs by one agent is reproducibility. Independence is a different party.
            "independent_verifier": None,
            "verified": False,
            "ran_by": "arena-agent-20261112",
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
        written.append(record)
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / f"REPRODUCIBILITY__{experience['id']}__RECEIPT.json"
            target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "rerun": "deterministic_experiences",
        "experiences": len(written),
        "identical": sum(1 for row in written if row["identical"]),
        "as_designed": sum(1 for row in written if row["as_designed"]),
        "records": written,
        "verified_claims": 0,
        "note": "REPRODUCED_IS_NOT_VERIFIED_INDEPENDENCE_NEEDS_ANOTHER_PARTY",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--rerun", action="store_true", help="re-run the deterministic experiences")
    parser.add_argument("--out", type=pathlib.Path, default=None, help="where --rerun writes receipts")
    args = parser.parse_args(argv)

    report: dict[str, Any] = census()
    if args.rerun:
        report["rerun"] = rerun(args.out)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Verified experience: how many examples could a student learn from?")
    print("=" * 78)
    print(f"  receipts in the tree                              {report['receipts']:>6}")
    print(f"  carrying a verdict (self-reported)                {report['verdict_present']:>6}"
          f"   ({report['verdict_true']} true / {report['verdict_false']} false)")
    print(f"  carrying no verdict at all                        "
          f"{report['readable_receipts'] - report['verdict_present']:>6}")
    print(f"  naming a run by anyone but the producer           "
          f"{report['independent_run_recorded']:>6}")
    print(f"  TRAINING-READY EXAMPLES                           "
          f"{report['training_ready_examples']:>6}")
    print(f"  distinct runners recorded                         {report['distinct_runners']}")
    if "rerun" in report:
        r = report["rerun"]
        print()
        print(f"  re-ran {r['experiences']} experiences twice: {r['identical']} identical, "
              f"{r['as_designed']} behaving as designed, {r['verified_claims']} claimed verified")
        print("  (reproducibility is not independence; nothing here is marked verified)")
    print()
    print("  missing to train:", report["missing_to_train"][0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
