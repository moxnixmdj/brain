from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime import h100_generic_patch_search_transfer_v1 as patchlib
from canonical.runtime import tool_discovery_information_safe_candidate as tool_policy
from canonical.runtime import coding_control_kernel_v1 as coding_gate

ROOT = pathlib.Path(__file__).resolve().parents[2]
PRE_PATH = ROOT / "canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json"
SCHEMA = "PROJECT_BRAIN_MATCHED_CODING_DEBUG_TOOL_DISCOVERY_FRESH_V1"
FAMILIES = ("POWER", "HINGE", "GAUSSIAN", "TANH")
CASE_COUNT = 4
REQUIRED_CAP = "python_program_repair"
TOOLS = (
    {"tool_id": "noop_formatter", "cost": 0.1, "available": True, "authorized": True},
    {"tool_id": "generic_patch_search", "cost": 1.0, "available": True, "authorized": True},
    {"tool_id": "expensive_decoy", "cost": 5.0, "available": True, "authorized": True},
)
HIDDEN_SUPPORT = {
    "noop_formatter": False,
    "generic_patch_search": True,
    "expensive_decoy": False,
}


class FreshCodingCaseError(ValueError):
    pass


def _canon(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest_words(beacon: str, case_id: str) -> list[int]:
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise FreshCodingCaseError("BEACON_INVALID")
    if not isinstance(case_id, str) or not case_id.strip():
        raise FreshCodingCaseError("CASE_ID_INVALID")
    raw = hashlib.sha256(
        b"PROJECT_BRAIN_MATCHED_CODING_FRESH_V1\0"
        + beacon.strip().encode("utf-8")
        + b"\0"
        + case_id.strip().encode("utf-8")
    ).digest()
    return [int.from_bytes(raw[i:i+4], "big") for i in range(0, 32, 4)]


def _scaled_signed(word: int, *, magnitude: float) -> float:
    # Deterministic nonzero values on a predeclared rational grid.
    bucket = int(word % 2001) - 1000
    if -80 < bucket < 80:
        bucket = 80 if bucket >= 0 else -80
    return round(magnitude * bucket / 1000.0, 6)


def _shape_for(family: str, words: list[int], train_x: list[float]) -> float | int:
    if family == "POWER":
        return (2, 3, 4, 5, 6)[words[0] % 5]
    if family == "HINGE":
        grid = patchlib._hinge_grid(train_x)
        return float(grid[words[0] % len(grid)])
    if family == "GAUSSIAN":
        return round(0.1 * (1 + words[0] % 20), 1)
    if family == "TANH":
        return round(0.2 * (1 + words[0] % 10), 1)
    raise FreshCodingCaseError("FAMILY_INVALID:" + family)


def _feature(family: str, shape: float | int, x: float) -> float:
    if family == "POWER":
        return x ** int(shape)
    if family == "HINGE":
        return max(0.0, x - float(shape))
    if family == "GAUSSIAN":
        return math.exp(-float(shape) * x * x)
    if family == "TANH":
        return math.tanh(float(shape) * x)
    raise FreshCodingCaseError("FAMILY_INVALID:" + family)


def derive_hidden_case(beacon: str, ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 0 <= ordinal < CASE_COUNT:
        raise FreshCodingCaseError("ORDINAL_INVALID")
    pre = json.loads(PRE_PATH.read_text(encoding="utf-8"))
    train_x = [float(x) for x in pre["x_population"]["training_x"]]
    holdout_x = [float(x) for x in pre["x_population"]["holdout_x"]]
    family = FAMILIES[ordinal]
    case_id = f"CODING-FRESH-{ordinal}"
    words = _digest_words(beacon, case_id)
    shape = _shape_for(family, words, train_x)
    coeff = [
        _scaled_signed(words[1], magnitude=1.4),
        _scaled_signed(words[2], magnitude=0.7),
        _scaled_signed(words[3], magnitude=1.3),
    ]
    # Ensure the nonlinear component is load-bearing and the zero baseline fails.
    if abs(coeff[2]) < 0.25:
        coeff[2] = 0.25 if coeff[2] >= 0 else -0.25

    def truth(x: float) -> float:
        return coeff[0] + coeff[1] * x + coeff[2] * _feature(family, shape, x)

    public_rows = [{"x": x, "y": truth(x)} for x in train_x]
    hidden_rows = [{"x": x, "y": truth(x)} for x in holdout_x]
    hidden_spec = {
        "family_id": family,
        "shape_parameter": shape,
        "coefficients": coeff,
    }
    return {
        "schema": SCHEMA + "_HIDDEN_CASE_V1",
        "case_id": case_id,
        "ordinal": ordinal,
        "public_rows": public_rows,
        "hidden_rows": hidden_rows,
        "hidden_spec": hidden_spec,
        "beacon_commitment_sha256": hashlib.sha256(beacon.strip().encode("utf-8")).hexdigest(),
        "case_payload_sha256": hashlib.sha256(_canon(public_rows)).hexdigest(),
        "hidden_holdout_sha256": hashlib.sha256(_canon(hidden_rows)).hexdigest(),
    }


def _discover_tool() -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for _ in range(16):
        public = {
            "required_capabilities": [REQUIRED_CAP],
            "tools": [dict(x) for x in TOOLS],
            "prior_probe_receipts": [dict(x) for x in receipts],
            "version_events": [],
        }
        action = tool_policy.next_action(public)
        if not isinstance(action, Mapping):
            return {"pass": False, "reason": "ACTION_NOT_MAPPING", "actions": actions}
        kind = action.get("action")
        if kind == "PROBE":
            tid = str(action.get("tool_id") or "")
            cap = str(action.get("capability") or "")
            if cap != REQUIRED_CAP or tid not in HIDDEN_SUPPORT:
                return {"pass": False, "reason": "INVALID_PROBE", "actions": actions}
            key = (tid, cap)
            if key in seen:
                return {"pass": False, "reason": "DUPLICATE_PROBE", "actions": actions}
            seen.add(key)
            receipt = {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": tid,
                "capability": cap,
                "epoch": 0,
                "supported": HIDDEN_SUPPORT[tid],
            }
            receipts.append(receipt)
            actions.append({"action": "PROBE", "tool_id": tid, "capability": cap, "supported": receipt["supported"]})
            continue
        if kind == "SELECT":
            tid = str(action.get("tool_id") or "")
            selected = tid == "generic_patch_search" and HIDDEN_SUPPORT.get(tid) is True
            actions.append({"action": "SELECT", "tool_id": tid})
            return {
                "pass": selected,
                "selected_tool": tid,
                "actions": actions,
                "probe_receipts": receipts,
            }
        return {"pass": False, "reason": "UNEXPECTED_ACTION:" + str(kind), "actions": actions}
    return {"pass": False, "reason": "TOOL_DISCOVERY_BUDGET", "actions": actions}


def discover_patch(public_rows: list[dict[str, float]]) -> dict[str, Any]:
    if not public_rows:
        raise FreshCodingCaseError("PUBLIC_ROWS_REQUIRED")
    pre = json.loads(PRE_PATH.read_text(encoding="utf-8"))
    xs = [float(r["x"]) for r in public_rows]
    candidates = []
    for spec in patchlib._specs(pre, train_x=xs):
        row = patchlib._fit_candidate(public_rows, public_rows, *spec)
        if row is not None:
            candidates.append(row)
    exact = [x for x in candidates if float(x["train_nrmse"]) <= 1e-10]
    exact.sort(key=lambda x: (
        int(x["complexity_rank"]),
        float(x["train_nrmse"]),
        str(x["family_id"]),
        str(x["shape_parameter"]),
    ))
    if not exact:
        return {"status": "NO_EXACT_PUBLIC_TEST_PATCH", "candidate_count": len(candidates)}
    selected = exact[0]
    return {
        "status": "EXACT_PUBLIC_TEST_PATCH_FOUND",
        "family_id": selected["family_id"],
        "shape_parameter": selected["shape_parameter"],
        "complexity_rank": selected["complexity_rank"],
        "coefficients": [float(x) for x in selected["coefficients"]],
        "train_nrmse": float(selected["train_nrmse"]),
        "candidate_count": len(candidates),
    }


def _source_for_patch(patch: Mapping[str, Any]) -> str:
    c = [float(x) for x in patch["coefficients"]]
    family = str(patch["family_id"])
    param = patch.get("shape_parameter")
    if family == "POWER":
        feat = f"(x ** {int(param)})"
    elif family == "HINGE":
        feat = f"max(0.0, x - ({repr(float(param))}))"
    elif family == "GAUSSIAN":
        feat = f"math.exp(-({repr(float(param))}) * x * x)"
    elif family == "TANH":
        feat = f"math.tanh(({repr(float(param))}) * x)"
    else:
        raise FreshCodingCaseError("PATCH_FAMILY_UNSUPPORTED:" + family)
    return (
        "import math\n\n"
        "def predict(x: float) -> float:\n"
        f"    return ({repr(c[0])}) + ({repr(c[1])}) * x + ({repr(c[2])}) * ({feat})\n"
    )


def _test_source(rows: list[dict[str, float]]) -> str:
    body = [
        "import unittest",
        "from target import predict",
        "",
        "class PublicTests(unittest.TestCase):",
        "    def test_public_observations(self):",
    ]
    for row in rows:
        body.append(
            f"        self.assertAlmostEqual(predict({repr(float(row['x']))}), {repr(float(row['y']))}, places=7)"
        )
    body.extend(["", "if __name__ == '__main__':", "    unittest.main()", ""])
    return "\n".join(body)


def _run(cmd: list[str], cwd: pathlib.Path) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    return {
        "command": " ".join(cmd),
        "returncode": cp.returncode,
        "stdout": cp.stdout,
        "stderr": cp.stderr,
    }


def _hidden_holdout(hidden_rows: list[dict[str, float]], work: pathlib.Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("matched_target_hidden", work / "target.py")
    if spec is None or spec.loader is None:
        return {"pass": False, "reason": "TARGET_IMPORT_FAILED"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    truth = [float(r["y"]) for r in hidden_rows]
    pred = [float(mod.predict(float(r["x"]))) for r in hidden_rows]
    err = float(patchlib._nrmse(truth, pred))
    return {"pass": err <= 1e-8, "holdout_nrmse": err, "holdout_count": len(hidden_rows)}


def execute_case(beacon: str, ordinal: int) -> dict[str, Any]:
    hidden_case = derive_hidden_case(beacon, ordinal)
    public_rows = [dict(x) for x in hidden_case["public_rows"]]
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        (work / "target.py").write_text(
            "def predict(x: float) -> float:\n    return 0.0\n",
            encoding="utf-8",
        )
        (work / "test_target.py").write_text(_test_source(public_rows), encoding="utf-8")
        _run(["git", "init", "-q"], work)
        _run(["git", "config", "user.email", "brain@example.invalid"], work)
        _run(["git", "config", "user.name", "Project Brain"], work)
        _run(["git", "add", "target.py", "test_target.py"], work)
        _run(["git", "commit", "-q", "-m", "frozen buggy baseline"], work)

        initial_source = (work / "target.py").read_text(encoding="utf-8")
        fail_test = _run([sys.executable, "-m", "unittest", "-q"], work)
        discovery = _discover_tool()
        patch = discover_patch(public_rows)
        if discovery.get("pass") is not True or patch.get("status") != "EXACT_PUBLIC_TEST_PATCH_FOUND":
            return {
                "schema": SCHEMA + "_RESULT",
                "case_id": hidden_case["case_id"],
                "pass": False,
                "reason": "DISCOVERY_OR_PATCH_FAILED",
                "terminal_credit_delta": 0,
            }

        repaired_source = _source_for_patch(patch)
        (work / "target.py").write_text(repaired_source, encoding="utf-8")
        pass_test = _run([sys.executable, "-m", "unittest", "-q"], work)
        diff_check = _run(["git", "diff", "--check"], work)
        hidden = _hidden_holdout(hidden_case["hidden_rows"], work)

        control_trace = [
            {"cycle": 0, "action": {"type": "environment_exec", "args": {"command": pass_test["command"]}},
             "result": {"returncode": pass_test["returncode"], "stdout": pass_test["stdout"], "stderr": pass_test["stderr"]}},
            {"cycle": 1, "action": {"type": "environment_exec", "args": {"command": diff_check["command"]}},
             "result": {"returncode": diff_check["returncode"], "stdout": diff_check["stdout"], "stderr": diff_check["stderr"]}},
        ]
        finish = coding_gate.validate_finish({
            "summary": "Fresh precommitted failing tests diagnosed; information-safe repair tool discovered; patch applied; public tests and hidden holdout pass.",
            "known_relevant_failures": [],
            "verification_cycles": [0],
            "diff_inspection_cycles": [1],
            "acceptance_criteria": [{
                "criterion": "Public regression tests pass after repair and diff is clean.",
                "evidence_cycles": [0, 1],
            }],
        }, control_trace)

        passed = bool(
            fail_test["returncode"] != 0
            and discovery.get("selected_tool") == "generic_patch_search"
            and pass_test["returncode"] == 0
            and diff_check["returncode"] == 0
            and hidden.get("pass") is True
            and finish.get("pass") is True
            and repaired_source != initial_source
        )

        events = [
            {"seq": 0, "type": "CODE_REVISION", "source": "HARNESS", "revision": "BUGGY_BASELINE"},
            {"seq": 1, "type": "TEST_RESULT", "source": "HARNESS", "pass": fail_test["returncode"] == 0},
            {"seq": 2, "type": "DEBUG", "source": "HARNESS", "failure_observed": fail_test["returncode"] != 0},
            {"seq": 3, "type": "TOOL_DISCOVERY", "source": "HARNESS", "selected_tool": discovery.get("selected_tool")},
            {"seq": 4, "type": "CODE_REVISION", "source": "HARNESS", "revision": "REPAIRED"},
            {"seq": 5, "type": "TEST_RESULT", "source": "HARNESS", "pass": pass_test["returncode"] == 0, "hidden_holdout_pass": hidden.get("pass")},
            {"seq": 6, "type": "TERMINAL", "source": "HARNESS", "success": passed},
        ]

        return {
            "schema": SCHEMA + "_RESULT",
            "case_id": hidden_case["case_id"],
            "pass": passed,
            "case_payload_sha256": hidden_case["case_payload_sha256"],
            "hidden_holdout_sha256": hidden_case["hidden_holdout_sha256"],
            "beacon_commitment_sha256": hidden_case["beacon_commitment_sha256"],
            "candidate_visible_hidden_spec": False,
            "initial_test_failed": fail_test["returncode"] != 0,
            "tool_discovery": discovery,
            "patch": patch,
            "public_test_after_patch_pass": pass_test["returncode"] == 0,
            "hidden_holdout": hidden,
            "git_diff_check_pass": diff_check["returncode"] == 0,
            "coding_finish_gate": finish,
            "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
            "terminal_authority": False,
            "fresh_reality_authority": False,
            "terminal_credit_delta": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }


def run_fresh_batch(beacon: str) -> dict[str, Any]:
    rows = [execute_case(beacon, i) for i in range(CASE_COUNT)]
    passed = sum(int(r.get("pass") is True) for r in rows)
    return {
        "schema": SCHEMA + "_BATCH_RESULT",
        "case_count": CASE_COUNT,
        "passed": passed,
        "failed": CASE_COUNT - passed,
        "all_pass": passed == CASE_COUNT,
        "case_payload_sha256s": [r.get("case_payload_sha256") for r in rows],
        "beacon_commitment_sha256": hashlib.sha256(beacon.strip().encode("utf-8")).hexdigest(),
        "terminal_authority": False,
        "fresh_reality_authority": False,
        "terminal_credit_delta": 0,
    }
