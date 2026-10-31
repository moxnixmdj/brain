"""Demonstrate that plain caller-written OIDC claim dictionaries are admitted.

No JWT, signature, GitHub run, or actual independent execution is supplied.
This tests the direct receipt-admission functions against disposable files;
it does not modify the real registry or create a real capability receipt.
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

from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import _receipt_admits  # noqa: E402


REFERENCES = {
    "invented": {"github_run_id": 1, "oidc_claims": {
        "iss": lane.GITHUB_OIDC_ISSUER, "repository": "moxnixmdj/brain", "run_id": "1"}},
    "different_repository": {"github_run_id": 2, "oidc_claims": {
        "iss": lane.GITHUB_OIDC_ISSUER, "repository": "unrelated/repository", "run_id": "2"}},
    "mismatched_run_id": {"github_run_id": 3, "oidc_claims": {
        "iss": lane.GITHUB_OIDC_ISSUER, "repository": "moxnixmdj/brain", "run_id": "999"}},
    "wrong_workflow": {"github_run_id": 4, "oidc_claims": {
        "iss": lane.GITHUB_OIDC_ISSUER, "repository": "moxnixmdj/brain", "run_id": "4",
        "workflow_ref": "untrusted-workflow"}},
}


def measure() -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-oidc-audit-") as temporary:
        root = Path(temporary)
        module_rel = "canonical/runtime/bound_capabilities/never_run.py"
        module = root / module_rel
        module.parent.mkdir(parents=True)
        module.write_text("def run(args, root):\n    raise RuntimeError('never executed')\n")
        module_sha = sha256(module.read_bytes()).hexdigest()
        for label, ref in REFERENCES.items():
            receipt_rel = lane.receipt_path_for("fabricated." + label)
            receipt_path = root / receipt_rel
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt = {
                "schema": lane.SCHEMA, "capability_id": "fabricated." + label,
                "module_path": module_rel, "module_sha256": module_sha,
                "result_sha256": "a" * 64, "model_dependency_count": 0,
                "ran_by": "invented-producer",
            }
            verification = {
                "schema": lane.VERIFICATION_SCHEMA, "module_sha256": module_sha,
                "verifier_result_sha256": "a" * 64, "reproduced": True,
                "independent_verifier": "invented-verifier", "independent_run_reference": ref,
            }
            receipt_path.write_text(json.dumps(receipt))
            (root / lane.verification_path_for(receipt_rel)).write_text(json.dumps(verification))
            entry = {"source": {"path": module_rel}, "verification": {"receipt_path": receipt_rel}}
            rows.append({
                "case": label,
                "contains_signed_jwt": False,
                "lane_attested": lane.run_reference_is_attested(ref),
                "loader_receipt_admitted": _receipt_admits(entry, root),
            })
    unsafe = sum(row["loader_receipt_admitted"] for row in rows)
    return {
        "schema": "BRAIN_OIDC_CLAIM_AUTHENTICITY_PROBE_V1",
        "status": "FAIL__UNSIGNED_CLAIMS_ADMITTED" if unsafe else "NO_UNSIGNED_ADMISSION_OBSERVED",
        "case_count": len(rows), "unsigned_loader_admissions": unsafe, "rows": rows,
        "scope": "direct functions with disposable files; does not prove a real registry was altered",
        "terminal_authority": False,
    }


def main() -> int:
    report = measure()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["unsigned_loader_admissions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
