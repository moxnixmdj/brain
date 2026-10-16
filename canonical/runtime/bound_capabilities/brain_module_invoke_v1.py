"""Invoke one test-evidenced function of an existing Brain module, read-only, from a sentence.

Why this exists: 2,309 repository modules sit in the non-executing inventory.  Writing one
wrapper per module does not scale, and calling them blindly is unsafe.  This adapter makes every
module listed in ``MODULE_INVOCATION_EVIDENCE_V1.json`` callable through the one live entry:

* every public function of every inventory module that imports under the guard, in one of two
  tiers judged per test case: TEST_EVIDENCED (a passing test names it, no failing test does) or
  READ_ONLY_UNTESTED (no test names it; every result says so).  Functions named by a failing
  test case are refused.  Module and evidence test files are pinned by sha256;
* executed in a child process whose audit hook refuses file writes, deletes, renames,
  directory creation, subprocesses, ``os.system``/``exec``/``fork`` and sockets, with a timeout;
* the payload must match the function signature exactly (no guessed arguments);
* the result must be JSON; ``None`` is reported as ``null``, never as success.

What ``output_verified`` means here: the output file holds exactly the function's return value
and the evidence pins still matched at call time.  It does NOT mean an independent oracle checked
the answer; the result carries ``tier`` and ``result_correctness`` saying exactly what backs it.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

CAPABILITY_ID = "brain.module.function.invoke"
EVIDENCE_REL = "canonical/runtime/MODULE_INVOCATION_EVIDENCE_V1.json"
RUNNER_REL = "canonical/runtime/bound_capabilities/brain_module_invoke_runner_v1.py"
TIMEOUT_S = 60
MAX_RESULT_BYTES = 8 * 1024 * 1024
RESULT_MARKER = "\x00BRAIN_MODULE_INVOKE_RESULT\x00"
TIER_TESTED = "TEST_EVIDENCED"
TIER_UNTESTED = "READ_ONLY_UNTESTED"
CORRECTNESS = {
    TIER_TESTED: "NOT_INDEPENDENTLY_VERIFIED__MODULE_TESTS_PASSED_AT_THIS_SHA",
    TIER_UNTESTED: "NO_TEST_EVIDENCE__FAITHFUL_READ_ONLY_EXECUTION_ONLY",
}


class ModuleInvokeRefused(RuntimeError):
    pass


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    text = str(raw or "").strip()
    if not text:
        raise ModuleInvokeRefused("PATH_REQUIRED")
    path = (root / text).resolve()
    if root not in path.parents:
        raise ModuleInvokeRefused("PATH_OUTSIDE_REPOSITORY:" + text)
    return path


def load_evidence(root: pathlib.Path) -> dict[str, Any]:
    data = json.loads((root / EVIDENCE_REL).read_text(encoding="utf-8"))
    if data.get("schema") != "PROJECT_BRAIN_MODULE_INVOCATION_EVIDENCE_V1" or not isinstance(data.get("modules"), dict):
        raise ModuleInvokeRefused("EVIDENCE_INVALID")
    return data


def admitted(root: pathlib.Path, source_rel: str, function: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """{"module": row, "function": fn_row} after re-checking every pin, or raise."""
    evidence = evidence or load_evidence(root)
    why = ((evidence.get("refused") or {}).get(source_rel) or {}).get(function)
    if why:
        raise ModuleInvokeRefused("FUNCTION_REFUSED_BY_ITS_OWN_FAILING_TEST:%s:%s:%s" % (source_rel, function, why))
    row = evidence["modules"].get(source_rel)
    if not isinstance(row, dict):
        raise ModuleInvokeRefused("MODULE_NOT_ADMITTED:" + source_rel)
    fn_row = (row.get("functions") or {}).get(function)
    if not isinstance(fn_row, dict):
        raise ModuleInvokeRefused("FUNCTION_NOT_ADMITTED:%s:%s admitted=%s" % (source_rel, function, ",".join(sorted(row.get("functions") or {}))))
    if fn_row.get("tier") not in CORRECTNESS:
        raise ModuleInvokeRefused("FUNCTION_TIER_INVALID:" + function)
    if _sha(root / source_rel) != row.get("sha256"):
        raise ModuleInvokeRefused("MODULE_EVIDENCE_STALE:" + source_rel)
    if fn_row["tier"] == TIER_TESTED:
        for test_rel, test_sha in sorted((row.get("tests") or {}).items()):
            test_path = root / test_rel
            if not test_path.is_file() or _sha(test_path) != test_sha:
                raise ModuleInvokeRefused("TEST_EVIDENCE_STALE:" + test_rel)
    return {"module": row, "function": fn_row}


def write_record(root: pathlib.Path, output: pathlib.Path, source_rel: str, function: str, adm: dict[str, Any],
                 payload_path: pathlib.Path, result: Any, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    tier = adm["function"]["tier"]
    record = {
        "capability_id": CAPABILITY_ID,
        "source_path": source_rel,
        "function": function,
        "tier": tier,
        "source_sha256": adm["module"]["sha256"],
        "payload_sha256": _sha(payload_path),
        "result": result,
        "result_correctness": CORRECTNESS[tier],
        "evidence": {"passing_test_cases": adm["function"].get("passing_cases", 0),
                     "tests": sorted(adm["module"].get("tests") or {}) if tier == TIER_TESTED else []},
        "guard": "child process, audit hook: no writes, deletes, subprocesses or sockets; memory/CPU limits",
        **(extra or {}),
    }
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    reread = json.loads(output.read_text(encoding="utf-8"))
    verified = reread == json.loads(text) and _sha(root / source_rel) == adm["module"]["sha256"]
    return {
        "status": "MODULE_FUNCTION_INVOKED" if verified else "OUTPUT_MISMATCH",
        "source_path": source_rel,
        "function": function,
        "tier": tier,
        "result_type": type(result).__name__ if result is not None else "null",
        "output_path": output.relative_to(root).as_posix(),
        "output_sha256": _sha(output),
        "output_verified": verified,
    }


def probe_import(root: pathlib.Path, source_rel: str) -> list[str]:
    """Import the module under the read-only guard; return its public functions or raise."""
    return _child(root, {"root": str(root), "source": source_rel, "function": "__name__", "payload": None, "probe_import": True})


def invoke(root: pathlib.Path, source_rel: str, function: str, payload: Any) -> Any:
    """Run the admitted function in the guarded child process and return its JSON result."""
    return _child(root, {"root": str(root), "source": source_rel, "function": function, "payload": payload})


def _child(root: pathlib.Path, req: dict[str, Any]) -> Any:
    runner = root / RUNNER_REL
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "HOME", "TMPDIR", "SYSTEMROOT")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    request = json.dumps(req)
    try:
        proc = subprocess.run([sys.executable, "-I", str(runner)], input=request, capture_output=True,
                              text=True, timeout=TIMEOUT_S, cwd=str(root), env=env)
    except subprocess.TimeoutExpired:
        raise ModuleInvokeRefused("MODULE_CALL_TIMEOUT_%dS" % TIMEOUT_S) from None
    out = proc.stdout
    if RESULT_MARKER not in out:
        tail = (proc.stderr or "").strip().splitlines()[-1:] or ["no output"]
        raise ModuleInvokeRefused("MODULE_CALL_CRASHED:" + tail[0][:300])
    body = out.split(RESULT_MARKER, 1)[1]
    if len(body) > MAX_RESULT_BYTES:
        raise ModuleInvokeRefused("MODULE_RESULT_TOO_LARGE")
    reply = json.loads(body)
    if not reply.get("ok"):
        raise ModuleInvokeRefused(str(reply.get("error") or "MODULE_CALL_FAILED")[:500])
    return reply["result"]


def _canonical(value: Any) -> str:
    """Canonical JSON of a result, so two runs compare by content and not by repr."""
    return json.dumps(value, sort_keys=True, default=str)


def _code(exc: BaseException) -> str:
    """A stable machine-readable skip code: the exception's own code, never its free text."""
    return str(exc).split(":", 1)[0][:64]


def _zero_argument_tested(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    """Every TEST_EVIDENCED function that requires no argument, in deterministic order."""
    out: list[tuple[str, str]] = []
    for rel, row in sorted(evidence["modules"].items()):
        for name, fn_row in sorted((row.get("functions") or {}).items()):
            if fn_row.get("tier") != TIER_TESTED:
                continue
            if not list((fn_row.get("signature") or {}).get("required") or []):
                out.append((rel, name))
    return out


def select_self_test(root: pathlib.Path, evidence: dict[str, Any] | None = None) -> tuple[str, str]:
    """The first TEST_EVIDENCED function (sorted) that requires no argument.

    Deterministic by construction, so two runs compare equal, and chosen from the pinned
    evidence at call time, so a receipt names exactly what ran.
    """
    candidates = _zero_argument_tested(evidence or load_evidence(root))
    if not candidates:
        raise ModuleInvokeRefused("NO_ZERO_ARGUMENT_TEST_EVIDENCED_FUNCTION")
    return candidates[0]


def self_test(root: pathlib.Path, max_attempts: int = 8) -> dict[str, Any]:
    """The zero-input form: exercise the whole path once and let it prove itself.

    This is what the receipt lane executes (`fn({}, root)` -> dict) and what the CI runner
    re-executes to mint independent verification, so the capability cannot be admitted on a
    description: the evidence pins are re-checked, the guarded child runs a real function, and
    the result is compared against the same function called without the guard by the
    repository's own differential oracle.  Agreement, not assertion, is the status.

    Candidates are walked in sorted order and a function that returns a non-JSON object is
    skipped (the capability refuses those by design), but a candidate that *disagrees* stops
    the walk and fails closed: skipping past a disagreement would be cherry-picking evidence.
    """
    from canonical.runtime import module_invocation_evidence_v1 as evidence  # heavy; off the hot path
    data = load_evidence(root)
    attempts: list[dict[str, Any]] = []
    for rel, function in _zero_argument_tested(data):
        if len(attempts) >= max_attempts:
            break
        try:
            adm = admitted(root, rel, function, data)
        except ModuleInvokeRefused as exc:
            attempts.append({"source_path": rel, "function": function, "skipped": _code(exc)})
            continue
        try:
            first = invoke(root, rel, function, {})
            second = invoke(root, rel, function, {})
        except ModuleInvokeRefused as exc:
            attempts.append({"source_path": rel, "function": function, "skipped": _code(exc)})
            continue
        if _canonical(first) != _canonical(second):
            # The runner re-executes this and compares result hashes, so a candidate that does
            # not reproduce on THIS machine cannot be the one the capability is admitted on.
            attempts.append({"source_path": rel, "function": function, "skipped": "NON_DETERMINISTIC"})
            continue
        direct = evidence._oracle_direct(root, rel, function)
        agreed = _canonical(first) == _canonical(direct)
        attempts.append({"source_path": rel, "function": function, "tier": adm["function"]["tier"],
                         "result_type": type(first).__name__ if first is not None else "null",
                         "agreed": agreed})
        return {
            "status": "MODULE_FUNCTION_INVOKED" if agreed else "FAIL_CLOSED__SELF_TEST_DIFFERENTIAL_DISAGREEMENT",
            "pass": bool(agreed),
            "capability_id": CAPABILITY_ID,
            "source_path": rel,
            "function": function,
            "tier": adm["function"]["tier"],
            "result_type": type(first).__name__ if first is not None else "null",
            "result_sha256": hashlib.sha256(_canonical(first).encode("utf-8")).hexdigest(),
            "differential": {
                "compared": 1,
                "agreed": 1 if agreed else 0,
                "oracle": "module_invocation_evidence_v1._oracle_direct (separate child, no audit hook)",
                "repeatable": True,
            },
            "attempts": attempts,
            "result_correctness": "ZERO_ARGUMENT_SELF_TEST__DIFFERENTIAL_AGREEMENT__NOT_PER_CALL_CORRECTNESS",
            "guard": "child process, audit hook: no writes, deletes, subprocesses or sockets",
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
    return {
        "status": "FAIL_CLOSED__NO_USABLE_ZERO_ARGUMENT_TEST_EVIDENCED_FUNCTION",
        "pass": False,
        "capability_id": CAPABILITY_ID,
        "attempts": attempts,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    if not str(args.get("source_path") or "").strip():
        # Zero-input form.  A caller with nothing to name is answered with the capability's own
        # self-test instead of an argument error, which is what makes this capability
        # executable by the receipt lane and by the CI runner that verifies the receipt.
        return self_test(root)
    source = _repo_path(root, args.get("source_path"))
    source_rel = source.relative_to(root).as_posix()
    function = str(args.get("function") or "").strip()
    if not function.isidentifier() or function.startswith("_"):
        raise ModuleInvokeRefused("FUNCTION_NAME_INVALID:" + function)
    payload_path = _repo_path(root, args.get("json_path"))
    output = _repo_path(root, args.get("output_path"))
    if output in (source, payload_path):
        raise ModuleInvokeRefused("OUTPUT_PATH_EQUALS_AN_INPUT")
    adm = admitted(root, source_rel, function)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    result = invoke(root, source_rel, function, payload)
    return write_record(root, output, source_rel, function, adm, payload_path, result)
