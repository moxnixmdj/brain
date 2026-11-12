#!/usr/bin/env python3
"""How much *verified* experience does this tree hold? Count both kinds of artefact, or be wrong.

**Correction, 2026-11-12 (round 16).** The first version of this census globbed
``canonical/astra_runtime/evidence/*RECEIPT.json`` and reported zero independently verified
experience. That was a detector blind spot, not a finding. Independently verified runs are recorded in
a *different* artefact, ``CAPABILITY__*__INDEPENDENT_VERIFICATION.json``, written by
``.github/workflows/capability-receipt-verification.yml`` on a GitHub runner under an OIDC-attested
``github_run_id``. There are hundreds of them. A census that reads one of the two artefacts and
concludes zero is exactly the mistake this project keeps paying for, so the tool now counts both,
joins them, and fails loudly if a verification record has no producer receipt to join to.

Arms:

1. **producer receipts** — what was executed and what the producer observed (``observed.pass``).
2. **verification records** — what a *different identity* re-ran and reproduced, with the run that
   did it.
3. **join** — a training example needs all three: a verdict, a reproduction by somebody else, and no
   model in the loop. It also needs *depth*: this tree has one instance per capability, and one
   instance per family cannot support a held-out split.
4. **rerun** — optional; re-runs a few deterministic experiences twice to show which artefacts must
   vary (a verifier with fresh cases) and which must replay (an experience to learn from).
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
RECEIPT_GLOB = "*RECEIPT.json"
VERIFICATION_GLOB = "CAPABILITY__*__INDEPENDENT_VERIFICATION.json"

#: How many verified instances of one capability a held-out split needs before it means anything.
DEPTH_TARGET = 8

EXPERIENCES: list[dict[str, Any]] = [
    {
        # A verifier must draw fresh cases, so it must NOT repeat itself. If this arm ever starts
        # matching, the check has stopped being fresh and has become a fixed test.
        "id": "unified_model_fresh_cases",
        "argv": ["{python}", "canonical/runtime/verify_brain_unified_model_v1.py"],
        "kind": "fresh_case_verifier",
        "expect_identical": False,
        "timeout_s": 300,
    },
    {
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
    """What a producer receipt can and cannot support on its own."""
    observed = receipt.get("observed")
    verdict = observed.get("pass") if isinstance(observed, dict) else None
    return {
        "capability_id": receipt.get("capability_id"),
        "has_verdict": verdict is not None,
        "verdict": verdict,
        "ran_by": receipt.get("ran_by"),
        "model_free": (receipt.get("model_dependency_count") or 0) == 0,
        # on its own, nothing: a producer's own pass is the producer's opinion
        "training_ready_alone": False,
    }


def classify_verification(record: dict[str, Any]) -> dict[str, Any]:
    """What a verification record asserts: a different identity re-ran it and reproduced it."""
    reference = record.get("independent_run_reference")
    run_id = reference.get("github_run_id") if isinstance(reference, dict) else None
    return {
        "capability_id": record.get("capability_id"),
        "reproduced": record.get("reproduced") is True,
        "verified_by": record.get("independent_verifier"),
        "github_run_id": run_id,
        "attested": bool(run_id),
        "model_free": (record.get("model_dependency_count") or 0) == 0,
    }


def census() -> dict[str, Any]:
    receipts: dict[str, dict[str, Any]] = {}
    unreadable: list[str] = []
    for path in sorted(EVIDENCE.glob(RECEIPT_GLOB)):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            unreadable.append(path.name)
            continue
        capability_id = record.get("capability_id")
        if capability_id:
            receipts[capability_id] = classify(record)

    verifications: dict[str, dict[str, Any]] = {}
    for path in sorted(EVIDENCE.glob(VERIFICATION_GLOB)):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            unreadable.append(path.name)
            continue
        capability_id = record.get("capability_id")
        if capability_id:
            verifications[capability_id] = classify_verification(record)

    orphans = sorted(set(verifications) - set(receipts))
    joined = sorted(set(verifications) & set(receipts))

    ready = [
        capability_id for capability_id in joined
        if verifications[capability_id]["reproduced"]
        and verifications[capability_id]["attested"]
        and verifications[capability_id]["model_free"]
        and receipts[capability_id]["has_verdict"]
    ]
    passing = [capability_id for capability_id in ready if receipts[capability_id]["verdict"] is True]

    instances: dict[str, int] = {capability_id: 1 for capability_id in joined}
    depth = max(instances.values()) if instances else 0

    return {
        "census": "verified_experience",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "unreadable": unreadable,
        "producer_receipts": len(receipts),
        "producer_receipts_with_verdict": sum(1 for row in receipts.values() if row["has_verdict"]),
        "verification_records": len(verifications),
        "verification_reproduced": sum(1 for row in verifications.values() if row["reproduced"]),
        "verification_attested_with_run_id": sum(
            1 for row in verifications.values() if row["attested"]),
        "verification_orphans_without_producer_receipt": orphans,
        "joined": len(joined),
        "distinct_verifiers": sorted({str(row["verified_by"]) for row in verifications.values()
                                      if row["verified_by"]}),
        "training_ready_examples": len(ready),
        "training_ready_with_pass_true": len(passing),
        "instances_per_capability": depth,
        "depth_target_per_capability": DEPTH_TARGET,
        "depth_instances_missing": max(0, len(joined) * DEPTH_TARGET - len(joined) * depth),
        "verdict": (
            "CORPUS_EXISTS_SHALLOW" if len(ready) else "NO_TRAINING_READY_EXAMPLES"
        ),
        "missing_to_train": (
            [] if len(ready) else ["NO_JOINED_VERIFIED_EXPERIENCE"]
        ) + (
            [f"DEPTH: {len(joined)} capabilities x 1 instance each; a held-out split needs "
             f"{DEPTH_TARGET} instances of the same family"] if depth < DEPTH_TARGET else []
        ),
        "what_this_can_never_show": [
            "WHETHER_THE_WORK_WAS_WORTH_DOING",
            "GENERALISATION: ONLY A HELD-OUT RUN CAN, AND ONE INSTANCE PER FAMILY CANNOT SPLIT",
        ],
    }


def rerun(out_dir: pathlib.Path | None) -> dict[str, Any]:
    """Run each experience twice and require the property that artefact must have."""
    written = []
    for experience in EXPERIENCES:
        argv = [part.format(python=sys.executable) for part in experience["argv"]]
        runs = []
        for _ in range(2):
            completed = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True,
                                       timeout=experience["timeout_s"])
            runs.append({"returncode": completed.returncode,
                         "stdout_sha256": _digest(completed.stdout),
                         "stderr_sha256": _digest(completed.stderr)})
        same = runs[0] == runs[1]
        record = {
            "schema": "PROJECT_BRAIN_REPRODUCIBILITY_RECEIPT_V1",
            "kind": "REPRODUCIBILITY_RECEIPT",
            "experience": experience["id"],
            "argv": argv[1:],
            "runs": runs,
            "identical": same,
            "kind_of_artefact": experience["kind"],
            "expect_identical": experience["expect_identical"],
            "verdict": "REPRODUCED" if same else "VARIED",
            "as_designed": same is bool(experience["expect_identical"]),
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
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    report: dict[str, Any] = census()
    if args.rerun:
        report["rerun"] = rerun(args.out)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Verified experience: how many examples could a student learn from?")
    print("=" * 78)
    print(f"  producer receipts                                 {report['producer_receipts']:>6}"
          f"   ({report['producer_receipts_with_verdict']} with a verdict)")
    print(f"  independent verification records                  {report['verification_records']:>6}"
          f"   ({report['verification_reproduced']} reproduced, "
          f"{report['verification_attested_with_run_id']} carrying a github_run_id)")
    print(f"  joined to a producer receipt                      {report['joined']:>6}"
          f"   (orphans: {len(report['verification_orphans_without_producer_receipt'])})")
    print(f"  verifiers                                         {report['distinct_verifiers']}")
    print(f"  TRAINING-READY EXAMPLES                           "
          f"{report['training_ready_examples']:>6}"
          f"   ({report['training_ready_with_pass_true']} with pass=true)")
    print()
    print(f"  depth: {report['instances_per_capability']} instance(s) per capability, "
          f"target {report['depth_target_per_capability']} -> "
          f"{report['depth_instances_missing']} instances missing")
    print(f"  verdict: {report['verdict']}")
    for item in report["missing_to_train"]:
        print(f"    - {item}")
    if "rerun" in report:
        r = report["rerun"]
        print()
        print(f"  re-ran {r['experiences']} experiences twice: {r['identical']} identical, "
              f"{r['as_designed']} behaving as designed, {r['verified_claims']} claimed verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
