"""Static authority non-amplification proof for three non-actuating terminal helpers."""
from __future__ import annotations

import ast
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_NONACTUATING_HELPERS_NONAMPLIFICATION_RECEIPT_V1"
ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = Path("canonical/governance/NONACTUATING_TERMINAL_HELPERS_NONAMPLIFICATION_20261010_V1.json")
AUTHORITY_KEYS = {
    "execution_authority",
    "promotion_authority",
    "capability_promotion_authority",
    "terminal_authority",
    "physical_deletion_authority",
}
FORBIDDEN_IMPORT_ROOTS = {
    "subprocess", "requests", "httpx", "aiohttp", "socket", "urllib", "shutil"
}
FORBIDDEN_BUILTIN_CALLS = {"open", "exec", "eval", "compile"}
FORBIDDEN_PATH_METHODS = {"write_text", "write_bytes", "unlink", "mkdir", "touch", "rename"}
FORBIDDEN_OS_METHODS = {"system", "remove", "unlink", "rename", "replace", "mkdir", "makedirs"}
FORBIDDEN_SUBPROCESS_METHODS = {"run", "call", "Popen", "check_call", "check_output"}


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "nonamplification_verified": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _call_chain(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*_call_chain(node.value), node.attr)
    return ()


def _inspect(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad_imports: set[str] = set()
    bad_calls: list[str] = []
    authority_true: list[str] = []
    bad_credit = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    bad_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            root = str(node.module or "").split(".", 1)[0]
            if root in FORBIDDEN_IMPORT_ROOTS:
                bad_imports.add(str(node.module))

        if isinstance(node, ast.Call):
            chain = _call_chain(node.func)
            if len(chain) == 1 and chain[0] in FORBIDDEN_BUILTIN_CALLS:
                bad_calls.append(".".join(chain))
            elif chain and chain[-1] in FORBIDDEN_PATH_METHODS:
                bad_calls.append(".".join(chain))
            elif len(chain) >= 2 and chain[0] == "os" and chain[-1] in FORBIDDEN_OS_METHODS:
                bad_calls.append(".".join(chain))
            elif len(chain) >= 2 and chain[0] == "subprocess" and chain[-1] in FORBIDDEN_SUBPROCESS_METHODS:
                bad_calls.append(".".join(chain))

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    continue
                if key.value in AUTHORITY_KEYS and isinstance(value, ast.Constant) and value.value is True:
                    authority_true.append(key.value)
                if key.value == "terminal_credit" and isinstance(value, ast.Constant) and value.value is True:
                    bad_credit += 1
                if key.value == "terminal_credit_delta":
                    if not (isinstance(value, ast.Constant) and value.value == 0 and not isinstance(value.value, bool)):
                        bad_credit += 1

    return {
        "pass": not bad_imports and not bad_calls and not authority_true and bad_credit == 0,
        "git_blob_sha": _git_blob_sha(path),
        "forbidden_imports": sorted(bad_imports),
        "direct_effect_calls": sorted(set(bad_calls)),
        "authority_true_literals": sorted(authority_true),
        "nonzero_terminal_credit_literals": bad_credit,
    }


def prove(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    try:
        spec = _load(root / SPEC_PATH)
    except Exception as exc:
        return _fail("SPEC_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))
    if spec.get("schema") != "PROJECT_BRAIN_NONACTUATING_HELPER_CUT_V1":
        return _fail("SPEC_SCHEMA_INVALID")
    if spec.get("terminal_credit_delta") != 0:
        return _fail("SPEC_NONZERO_TERMINAL_CREDIT")

    subjects = spec.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 3:
        return _fail("SUBJECT_SET_INVALID")

    verification_path = root / str(spec.get("verification_receipt") or "")
    try:
        verification = _load(verification_path)
    except Exception as exc:
        return _fail("VERIFICATION_RECEIPT_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))
    rows = verification.get("exact_runtime_blobs")
    if not isinstance(rows, list):
        return _fail("VERIFICATION_RECEIPT_RUNTIME_ROWS_INVALID")
    by_path = {row.get("path"): row for row in rows if isinstance(row, Mapping)}

    checked = []
    total_tests = 0
    for subject in subjects:
        if not isinstance(subject, Mapping):
            return _fail("SUBJECT_INVALID")
        rel = str(subject.get("path") or "")
        expected = str(subject.get("git_blob_sha") or "")
        path = root / rel
        if not path.is_file() or _git_blob_sha(path) != expected:
            return _fail("SUBJECT_BLOB_MISMATCH", path=rel)
        static = _inspect(path)
        if static.get("pass") is not True:
            return _fail("NONAMPLIFICATION_STATIC_PROOF_FAILED", path=rel, static=static)
        evidence = by_path.get(rel)
        if not isinstance(evidence, Mapping):
            return _fail("COMPONENT_VERIFICATION_ROW_MISSING", path=rel)
        if (
            evidence.get("git_blob_sha") != expected
            or int(evidence.get("failures", -1)) != 0
            or int(evidence.get("errors", -1)) != 0
            or int(evidence.get("tests_run", 0)) <= 0
        ):
            return _fail("COMPONENT_VERIFICATION_ROW_INVALID", path=rel, evidence=dict(evidence))
        total_tests += int(evidence["tests_run"])
        checked.append({"path": rel, "git_blob_sha": expected, "static": static, "tests_run": int(evidence["tests_run"])})

    if total_tests != 28:
        return _fail("COMPONENT_TEST_COUNT_UNEXPECTED", observed=total_tests, expected=28)

    body = {
        "pass": True,
        "schema": SCHEMA,
        "status": "PASS__NONACTUATING_HELPER_AUTHORITY_NONAMPLIFICATION_VERIFIED",
        "nonamplification_verified": True,
        "subject_count": len(checked),
        "subjects": checked,
        "component_test_count": total_tests,
        "verification_receipt_git_blob_sha": _git_blob_sha(verification_path),
        "no_direct_external_effect_calls": True,
        "no_authority_true_literals": True,
        "no_nonzero_terminal_credit_literals": True,
        "exact_component_behavior_receipt_bound": True,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {**body, "receipt_sha256": sha256(_canon(body)).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(prove(ROOT), indent=2, sort_keys=True))
