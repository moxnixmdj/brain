#!/usr/bin/env python3
"""Count capability receipt and verification metadata, not training examples.

The original census missed separate verification records. A later version counted
joined metadata but incorrectly called it a training-ready corpus and treated a
run ID as attestation. This tool does not validate provenance or payloads and
cannot establish training readiness, episode depth, or independent correctness.
It retains at most one receipt and verification record per capability ID. Its
optional rerun checks repeatability, not independent verification.
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


def _declares_model_free(record: dict[str, Any]) -> bool:
    count = record.get("model_dependency_count")
    return type(count) is int and count == 0


def classify(receipt: dict[str, Any]) -> dict[str, Any]:
    """Describe claims in a producer receipt without deciding training readiness."""
    observed = receipt.get("observed")
    verdict = observed.get("pass") if isinstance(observed, dict) else None
    return {
        "capability_id": receipt.get("capability_id"),
        "has_verdict": type(verdict) is bool,
        "verdict": verdict,
        "ran_by": receipt.get("ran_by"),
        "declares_model_free": _declares_model_free(receipt),
    }


def classify_verification(record: dict[str, Any]) -> dict[str, Any]:
    """Describe metadata claims; do not infer verified identity or attestation."""
    reference = record.get("independent_run_reference")
    run_id = reference.get("github_run_id") if isinstance(reference, dict) else None
    return {
        "capability_id": record.get("capability_id"),
        "reproduced": record.get("reproduced") is True,
        "verified_by": record.get("independent_verifier"),
        "github_run_id": run_id,
        "has_run_id": (type(run_id) is int and run_id > 0) or
                      (isinstance(run_id, str) and run_id.isascii() and run_id.isdecimal()
                       and bool(run_id.lstrip("0"))),
        "declares_model_free": _declares_model_free(record),
    }


def census() -> dict[str, Any]:
    receipts: dict[str, dict[str, Any]] = {}
    unreadable: list[str] = []
    ignored_without_capability_id: list[str] = []
    duplicate_receipts: set[str] = set()
    duplicate_verifications: set[str] = set()

    def read_records(pattern: str, rows: dict[str, dict[str, Any]],
                     duplicates: set[str], classifier: Any) -> None:
        for path in sorted(EVIDENCE.glob(pattern)):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(record, dict):
                    raise ValueError("record is not an object")
                capability_id = record.get("capability_id")
                if capability_id is None:
                    ignored_without_capability_id.append(path.name)
                    continue
                if not isinstance(capability_id, str) or not capability_id.strip():
                    raise ValueError("invalid capability ID")
                if capability_id in rows:
                    duplicates.add(capability_id)
                rows[capability_id] = classifier(record)
            except (OSError, UnicodeError, ValueError):
                unreadable.append(path.name)

    read_records(RECEIPT_GLOB, receipts, duplicate_receipts, classify)
    verifications: dict[str, dict[str, Any]] = {}
    read_records(VERIFICATION_GLOB, verifications, duplicate_verifications, classify_verification)

    orphans = sorted(set(verifications) - set(receipts))
    joined = sorted(set(verifications) & set(receipts))

    matching_metadata = [
        capability_id for capability_id in joined
        if verifications[capability_id]["reproduced"]
        and verifications[capability_id]["has_run_id"]
        and verifications[capability_id]["declares_model_free"]
        and receipts[capability_id]["declares_model_free"]
        and receipts[capability_id]["has_verdict"]
    ]
    passing = [capability_id for capability_id in matching_metadata
               if receipts[capability_id]["verdict"] is True]

    return {
        "census": "verified_experience",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "unreadable_or_invalid_records": unreadable,
        "ignored_without_capability_id": ignored_without_capability_id,
        "duplicate_producer_capability_ids": sorted(duplicate_receipts),
        "duplicate_verification_capability_ids": sorted(duplicate_verifications),
        "producer_receipts": len(receipts),
        "producer_receipts_with_verdict": sum(1 for row in receipts.values() if row["has_verdict"]),
        "verification_records": len(verifications),
        "verification_reproduced": sum(1 for row in verifications.values() if row["reproduced"]),
        "verification_records_with_run_id": sum(
            1 for row in verifications.values() if row["has_run_id"]),
        "verification_orphans_without_producer_receipt": orphans,
        "joined": len(joined),
        "distinct_verifiers_claimed": sorted({str(row["verified_by"]) for row in verifications.values()
                                              if row["verified_by"]}),
        "joined_reproduced_with_run_id_boolean_verdict_and_model_free_claims": len(matching_metadata),
        "joined_matching_metadata_with_pass_true": len(passing),
        "training_readiness_assessed": False,
        "independent_verification_performed": False,
        "limitations": [
            "Joins by capability ID; duplicate IDs are overwritten, not counted as distinct episodes.",
            "Run IDs and model-dependency fields are unverified metadata claims, not attestation.",
            "No trajectory, replayability, data rights, independent correctness or safety checks are performed.",
            "The number of underlying instances and availability of held-out splits are not measured.",
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

    print("Capability receipt metadata census (not a training-readiness assessment)")
    print("=" * 78)
    print(f"  producer capability IDs: {report['producer_receipts']} "
          f"({report['producer_receipts_with_verdict']} with a Boolean verdict)")
    print(f"  verification capability IDs: {report['verification_records']} "
          f"({report['verification_reproduced']} claim reproduction, "
          f"{report['verification_records_with_run_id']} carry a run ID)")
    print(f"  joined capability IDs: {report['joined']} "
          f"(orphans: {len(report['verification_orphans_without_producer_receipt'])})")
    print(f"  claimed verifiers: {report['distinct_verifiers_claimed']}")
    print(f"  joined with reproduction, run ID, Boolean verdict and model-free claims: "
          f"{report['joined_reproduced_with_run_id_boolean_verdict_and_model_free_claims']} "
          f"({report['joined_matching_metadata_with_pass_true']} claim pass=true)")
    print("  training readiness: NOT ASSESSED; counts are not training examples")
    for item in report["limitations"]:
        print(f"    - {item}")
    if "rerun" in report:
        r = report["rerun"]
        print()
        print(f"  re-ran {r['experiences']} experiences twice: {r['identical']} identical, "
              f"{r['as_designed']} behaving as designed, {r['verified_claims']} claimed verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
