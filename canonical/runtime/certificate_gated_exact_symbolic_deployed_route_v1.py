from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.obsolescence import run_exact_symbolic_v1 as exact_symbolic
from canonical.runtime.certificate_gated_selected_route_router_v1 import (
    AdmissionReceipt,
    RouterFailClosed,
    select_certified_route,
)

SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_EXACT_SYMBOLIC_DEPLOYED_ROUTE_V1"
ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = "canonical/obsolescence/suites/EXACT_SYMBOLIC_COMPUTATION_SUITE_V1.json"
RUNNER_PATH = "canonical/obsolescence/run_exact_symbolic_v1.py"
ROUTER_PATH = "canonical/runtime/certificate_gated_selected_route_router_v1.py"
ADMISSION_PATH = "canonical/governance/EXACT_SYMBOLIC_ROUTER_ADMISSION_CERTIFICATE_20261007_V1.json"
ADEQUACY_PATH = "canonical/capabilities/obsolescence/EXACT_SYMBOLIC_COMPUTATION_V1_ADJUDICATION.json"
ROUTE_GOVERNANCE_PATH = "canonical/governance/EXACT_SYMBOLIC_SELECTED_LEAF_ROUTE_20261007_V1.json"

EXPECTED_BLOBS = {
    SUITE_PATH: "1a0154d44963ce08ed78920978fb64ba054334cb",
    RUNNER_PATH: "8f6f04fee00664b26ddf1a45a65698399c7ca6c3",
    ROUTER_PATH: "4b99ef1e95e033badfb21ab7af7355122933224a",
    ADMISSION_PATH: "5fbbce8f7fe59f6b090c6f97c1af16f1fff9231b",
    ADEQUACY_PATH: "a691d49ef377fa216bbbeff70183112d65445463",
    ROUTE_GOVERNANCE_PATH: "ba48f9024787e25308f9ad1dd74a83064f467865",
}
SUITE_SHA256 = "38460d8e0a4886575743a50829e19b8aee02911962b3b668f38867883338e76f"
CONTEXT_DIGEST = "sha256:" + SUITE_SHA256
CELL_ID = "OBS-EXACT-SYMBOLIC-001"
ROUTE_ID = "accepted.exact_symbolic"


class DeployedRouteFailClosed(RuntimeError):
    pass


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _read_bound(path: str) -> bytes:
    data = (ROOT / path).read_bytes()
    observed = _git_blob(data)
    expected = EXPECTED_BLOBS[path]
    if observed != expected:
        raise DeployedRouteFailClosed(f"BOUND_BLOB_DRIFT:{path}:{observed}")
    return data


def _load_bound_suite() -> tuple[dict, str]:
    raw = _read_bound(SUITE_PATH)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SUITE_SHA256:
        raise DeployedRouteFailClosed("SUITE_SHA256_DRIFT")
    suite = json.loads(raw)
    if suite.get("suite_id") != CELL_ID:
        raise DeployedRouteFailClosed("SUITE_ID_DRIFT")
    if suite.get("capability_id") != "EXACT_SYMBOLIC_COMPUTATION_V1":
        raise DeployedRouteFailClosed("CAPABILITY_ID_DRIFT")
    return suite, "sha256:" + digest


def _receipt(context_digest: str) -> AdmissionReceipt:
    _read_bound(ROUTER_PATH)
    _read_bound(RUNNER_PATH)
    _read_bound(ADMISSION_PATH)
    _read_bound(ADEQUACY_PATH)
    _read_bound(ROUTE_GOVERNANCE_PATH)
    return AdmissionReceipt(
        context_digest=context_digest,
        cell_id=CELL_ID,
        route_id=ROUTE_ID,
        route_blob_sha=EXPECTED_BLOBS[RUNNER_PATH],
        adequacy_certificate_blob_sha=EXPECTED_BLOBS[ADEQUACY_PATH],
        admission_certificate_blob_sha=EXPECTED_BLOBS[ADMISSION_PATH],
        admitted=True,
    )


def run() -> dict:
    """Execute the fixed accepted exact-symbolic cell only after router admission."""
    suite, context_digest = _load_bound_suite()
    receipt = _receipt(context_digest)
    try:
        selected = select_certified_route(
            actual_context_digest=context_digest,
            receipts=[receipt],
        )
    except RouterFailClosed as exc:
        raise DeployedRouteFailClosed(f"ROUTER_FAIL_CLOSED:{exc}") from exc

    if selected.route_id != ROUTE_ID or selected.cell_id != CELL_ID:
        raise DeployedRouteFailClosed("ROUTER_SELECTED_UNEXPECTED_ROUTE")

    results = []
    for task in suite["tasks"]:
        try:
            output, ok = exact_symbolic.run_task(task)
            error = None
        except Exception as exc:
            output, ok = None, False
            error = type(exc).__name__ + ":" + str(exc)
        results.append({
            "id": task["id"],
            "operation": task["operation"],
            "pass": bool(ok),
            "output": output,
            "expected": task["expected"],
            "error": error,
        })

    passes = sum(1 for row in results if row["pass"])
    failures = len(results) - passes
    required = int(suite["acceptance"]["pass_count_required"])
    if passes != required or failures != int(suite["acceptance"]["fail_count_required"]):
        raise DeployedRouteFailClosed(
            f"ACCEPTED_ROUTE_REGRESSION:pass={passes}:fail={failures}"
        )

    return {
        "schema": SCHEMA,
        "router_selected": True,
        "context_digest": context_digest,
        "cell_id": selected.cell_id,
        "route_id": selected.route_id,
        "route_blob_sha": selected.route_blob_sha,
        "adequacy_certificate_blob_sha": selected.adequacy_certificate_blob_sha,
        "admission_certificate_blob_sha": selected.admission_certificate_blob_sha,
        "pass_count": passes,
        "fail_count": failures,
        "exact_correctness": passes / len(results),
        "incremental_spend_usd": 0,
        "results": results,
        "terminal_credit_delta": 0,
    }


def main() -> int:
    try:
        out = run()
    except DeployedRouteFailClosed as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 23
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
