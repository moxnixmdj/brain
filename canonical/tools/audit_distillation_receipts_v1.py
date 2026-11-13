#!/usr/bin/env python3
"""Read-only audit of receipt metadata for a potential trajectory-distillation pilot.

An independently reproduced capability receipt is not automatically an agent
trajectory. This counts the repository's capability-verification records and
checks their linked producer receipts. It never emits task content or creates a
training dataset. The optional structured-trajectory shape below is an audit
criterion, not a universal standard for agent experience or proof of safety.

Example: python3 canonical/tools/audit_distillation_receipts_v1.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = ROOT / "canonical/astra_runtime/evidence"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _load_object(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected object")
    return value


def _digest(value: Any) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _has_episode(receipt: dict[str, Any]) -> bool:
    """A deliberately specific, inspectable minimum shape, not semantic verification."""
    task = receipt.get("task")
    turns = receipt.get("trajectory")
    return (
        isinstance(task, str) and bool(task.strip())
        and isinstance(turns, list) and bool(turns)
        and all(isinstance(turn, dict)
                and isinstance(turn.get("observation"), str) and bool(turn["observation"].strip())
                and isinstance(turn.get("action"), str) and bool(turn["action"].strip())
                for turn in turns)
    )


def audit(evidence: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    """Return aggregate counts only. References cannot escape the evidence directory."""
    evidence, root = evidence.resolve(), root.resolve()
    counts: Counter[str] = Counter()
    for file in sorted(evidence.glob("CAPABILITY__*__INDEPENDENT_VERIFICATION.json")):
        counts["verification_records"] += 1
        try:
            # Do not follow verification-record symlinks outside the audited directory.
            if file.resolve().parent != evidence:
                raise ValueError("verification outside evidence directory")
            verification = _load_object(file)
            reference = verification.get("producer_receipt_path")
            if not isinstance(reference, str) or not reference:
                raise ValueError("missing producer reference")
            producer = (root / reference).resolve()
            if producer.parent != evidence or not producer.name.startswith("CAPABILITY__") or not producer.name.endswith("__EXECUTION_RECEIPT.json"):
                raise ValueError("producer reference outside evidence directory")
            receipt = _load_object(producer)
        except (OSError, UnicodeError, ValueError, TypeError):
            counts["unreadable_or_invalid_links"] += 1
            continue
        counts["linked_records"] += 1
        observed = receipt.get("observed")
        verdict = observed.get("pass") if isinstance(observed, dict) else None
        reference = verification.get("independent_run_reference")
        run_id = reference.get("github_run_id") if isinstance(reference, dict) else None
        producer_id = receipt.get("ran_by")
        verifier_id = verification.get("independent_verifier")
        producer_hash = verification.get("producer_result_sha256")
        verifier_hash = verification.get("verifier_result_sha256")
        module_hash = verification.get("module_sha256")
        metadata_consistent = (
            isinstance(receipt.get("capability_id"), str) and bool(receipt["capability_id"])
            and verification.get("capability_id") == receipt["capability_id"]
            and isinstance(producer_id, str) and bool(producer_id)
            and verification.get("producer_ran_by") == producer_id
            and isinstance(verifier_id, str) and bool(verifier_id) and verifier_id != producer_id
            and isinstance(run_id, (str, int)) and not isinstance(run_id, bool) and bool(str(run_id).strip()) and str(run_id) != "0"
            and verification.get("reproduced") is True
            and _digest(module_hash) and module_hash == receipt.get("module_sha256")
            and _digest(producer_hash) and producer_hash == receipt.get("result_sha256")
            and _digest(verifier_hash) and producer_hash == verifier_hash
        )
        counts["consistent_reproduction_metadata"] += int(metadata_consistent)
        counts["boolean_producer_verdict"] += int(type(verdict) is bool)
        counts["producer_pass"] += int(verdict is True)
        counts["empty_invocation_arguments"] += int(receipt.get("invoked_args") == {})
        has_episode = _has_episode(receipt)
        counts["structured_trajectory_present"] += int(has_episode)
        counts["passing_with_trajectory_and_consistent_metadata"] += int(
            has_episode and verdict is True and metadata_consistent)
    fields = ("verification_records", "linked_records", "unreadable_or_invalid_links",
              "consistent_reproduction_metadata", "boolean_producer_verdict", "producer_pass",
              "empty_invocation_arguments", "structured_trajectory_present",
              "passing_with_trajectory_and_consistent_metadata")
    return {
        "schema": "DISTILLATION_RECEIPT_AUDIT_V1",
        "authority": "PRODUCER_RUN_READ_ONLY_MEASUREMENT",
        "scope": "CAPABILITY__*__INDEPENDENT_VERIFICATION.json and their linked producer receipts",
        "counts": {key: counts[key] for key in fields},
        "limitations": [
            "Metadata consistency is not cryptographic attestation, independent rerun, or proof of correctness.",
            "A structured trajectory is not necessarily safe, useful, replayable, consented, or training-ready.",
            "Other experience stores and different trajectory representations are outside this census.",
            "No model, training, evaluation, or secrets screening is performed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--evidence", type=pathlib.Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    print(json.dumps(audit(args.evidence, args.root), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
