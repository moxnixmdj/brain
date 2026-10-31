"""Check whether the lossless receipt gate authenticates its asserted verifiers.

This uses caller-written, content-addressed JSON in a disposable directory. No
requested action is performed and the verifier identities are invented. It
probes the gate and the direct-admission consumer, not the live goal front door.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id  # noqa: E402
from canonical.runtime.lossless_raw_task_acceptance_gate_v1 import (  # noqa: E402
    RECEIPT_SCHEMA, VERIFY_SCHEMA, evaluate,
)
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract  # noqa: E402
from canonical.runtime.semantic_elision_db_admission_v1 import evaluate as admit  # noqa: E402


GOALS = (
    ("delete", "Delete other.txt."),
    ("modify", "Modify other.txt."),
    ("copy", "Copy other.txt to copy.txt."),
    ("archive", "Compress other.txt to other.gz."),
)


def _write(root: Path, relative: str, document: dict) -> dict:
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": relative, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def measure() -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-acceptance-auth-") as temporary:
        root = Path(temporary)
        (root / "other.txt").write_text("unchanged\n")
        candidate = sha256(b"unrelated-unmaterialized-candidate").hexdigest()
        for label, goal in GOALS:
            contract = compile_contract(goal, source_id="user", routing_target_effects=["candidate.ready"])
            pairs = []
            for index, obligation in enumerate(contract["acceptance_contract"]["obligations"]):
                binding = {
                    "task_contract_sha256": contract["task_contract_sha256"],
                    "task_sha256": contract["task_sha256"],
                    "obligation_id": obligation["obligation_id"],
                    "segment_sha256": obligation["segment_sha256"],
                    "candidate_sha256": candidate,
                    "verifier_class": "DETERMINISTIC",
                    "verifier_id": "invented-producer",
                    "accepted": True,
                }
                receipt = _write(root, f"{label}/receipt-{index}.json", {"schema": RECEIPT_SCHEMA, **binding})
                verification = _write(root, f"{label}/verification-{index}.json", {
                    "schema": VERIFY_SCHEMA, **binding,
                    "subject_git_blob_sha": receipt["git_blob_sha"],
                    "independent_verifier_id": "invented-independent-verifier",
                    "independent_verified": True, "acceptance_semantics_verified": True, "pass": True,
                })
                pairs.append({"receipt": receipt, "verification": verification})
            body = {"task_contract": contract, "candidate_sha256": candidate,
                    "obligation_receipts": pairs, "repo_root": str(root)}
            gate = evaluate(contract, candidate_sha256=candidate, obligation_receipts=pairs, repo_root=root)
            admission = admit({
                "route": "C_DIRECT_END_TO_END_ACCEPTANCE", "payload": body,
                "cell_id": "invented-cell", "policy_id": "invented-policy",
                "brain_owned_candidate_proved": True, "deployed_route_exactly_realizes_candidate": True,
                "authorized_resource_bound_proved": True,
            })
            unperformed = ((root / "other.txt").read_text() == "unchanged\n"
                           and not (root / "copy.txt").exists()
                           and not (root / "other.gz").exists())
            rows.append({
                "case": label, "requested_effect_unperformed": unperformed,
                "gate_pass": gate.get("pass") is True, "gate_status": gate.get("status"),
                "direct_admission_authorized": admission.get("db_admission_authorized") is True,
                "required_obligations": len(pairs),
            })
    unsafe = sum(row["requested_effect_unperformed"] and row["gate_pass"] for row in rows)
    return {
        "schema": "BRAIN_ACCEPTANCE_RECEIPT_AUTHENTICITY_PROBE_V1",
        "status": "FAIL__UNAUTHENTICATED_RECEIPTS_ACCEPTED" if unsafe else "NO_UNSAFE_ACCEPTANCE_OBSERVED",
        "case_count": len(rows), "unsafe_gate_count": unsafe, "rows": rows,
        "scope": "caller-written receipts; gate and direct-admission consumer; not the live front door",
        "terminal_authority": False,
    }


def main() -> int:
    report = measure()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["unsafe_gate_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
