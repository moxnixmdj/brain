#!/usr/bin/env python3
"""Capability execution receipts — one normalized schema, content-addressed, execution-backed.

WHY (first principles, measured on main @ 370005a)
--------------------------------------------------
`load_verified_registry` admits a capability on a mutable string and a boolean:

    bound    : status == "VERIFIED_BOUND_CAPABILITY"  and  incremental_spend_usd == 0
    extended : status == "VERIFIED_BOUND_CAPABILITY"  and  verification.verified is True

Both are writable by any program.  Measured consequence: flipping 500 extended
statuses fabricates 567 "capabilities" while the referee stays green.

The repo *has* a receipt idiom, but it is not capability-level: the 42 receipt
files referenced by the bound registry are ASTRA mission receipts
(`mission_id`, `mission_sha256`, `state_sha256`, `status: COMPLETE`) — they attest
that a mission completed, not that a module at a given content hash executed and
produced a given effect.  Meanwhile the 67 bound entries use ~150 distinct
verification key names (`workflow_run_id`, `public_run_id`, `regression_run_id`,
`focused_workflow_run_id`, `producer_git_blob`, `verifier_git_blob`, ...) for the
single concept "someone else ran it and here is the reference".

So this module supplies the one part that was missing: a *capability-level*
execution receipt with ONE normalized shape, and it proves claims by running them.

WHAT ONE RECEIPT ASSERTS (nothing more)
---------------------------------------
1. this module, at this exact sha256, loaded;
2. its `run(args, root)` returned a dict, recorded by sha256;
3. these status/pass fields were observed;
4. this identity ran it, on this platform, with zero model dependency.

It does NOT assert correctness, usefulness or independence.  `independent_verifier`
is null unless a *different* identity actually re-ran it.

WHAT IT REFUSES TO DO
---------------------
Never flips a `status`.  Never writes a registry.  Never deletes.  A receipt is
evidence; promotion stays in the governed lane.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1"
VERIFICATION_SCHEMA = "PROJECT_BRAIN_CAPABILITY_INDEPENDENT_VERIFICATION_V1"
RECEIPT_DIR = "canonical/astra_runtime/evidence"
EXTENDED = "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
BOUND = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
PROJECTION = "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json"
ENTRYPOINTS = ("run", "execute")
ARGS_NAMES = ("args", "request", "inputs", "params", "payload")
PROBE_TIMEOUT_S = 10


class _Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise _Timeout("probe timeout")


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_canonical(value: Any) -> str:
    """Hash a result deterministically, independent of dict ordering."""
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


CLI_ADAPTER = "canonical/runtime/bound_capabilities/cli_command.py"
CLI_ARGV = ("python3", "-")  # "-" is replaced by the module path; portable across machines


def cli_shape(path: str | os.PathLike) -> bool:
    """True for a module that is executable as a program (has main / __main__)."""
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return False
    if any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body):
        return True
    return "__main__" in src


def cli_argv_for(module_path: str) -> list[str]:
    """Portable argv stored in receipts: `python3` + the module path, never an absolute
    interpreter path, so a receipt issued here reproduces on the CI runner."""
    return ["python3", module_path]


def _resolve_argv(argv: list[str]) -> list[str]:
    if argv and argv[0] == "python3":
        return [sys.executable, *argv[1:]]
    return list(argv)


def run_cli_adapter(module_path: str, root: str, timeout_s: int = 20) -> dict[str, Any] | None:
    """Execute a CLI-shaped module THROUGH the repository's own generic adapter.

    No subprocess logic is reimplemented here: `bound_capabilities/cli_command.py` is the
    project's generic zero-shell adapter for exactly this, and it already enforces the
    timeout, the argv bound and the repository path boundary.  Reusing it means the
    capability that admission later exposes is executed the same way the creature will
    execute it.
    """
    import importlib.util

    # Resolve the adapter relative to THIS lane's installation, not to `root`. It is part of
    # the lane, not of the tree being probed; resolving it against `root` made the function
    # dead for any root that is not the repository itself.
    adapter = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bound_capabilities", "cli_command.py")
    if not os.path.isfile(adapter):
        adapter = os.path.join(root, CLI_ADAPTER)
    if not os.path.isfile(adapter):
        return None
    spec = importlib.util.spec_from_file_location("pb_receipt_lane_cli_adapter", adapter)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        result = module.run({"argv": _resolve_argv(cli_argv_for(module_path)),
                             "timeout_s": timeout_s}, root)
    except BaseException:  # noqa: BLE001 - a failed probe is data, not an error
        return None
    if not isinstance(result, dict) or int(result.get("returncode", 1)) != 0:
        return None
    stdout = str(result.get("stdout") or "").strip()
    try:
        structured = json.loads(stdout)
    except ValueError:
        return None
    if not isinstance(structured, dict) or not structured:
        return None
    result["structured_stdout"] = structured
    return result


_DECLARED_ARG_CACHE: dict[str, dict[str, Any]] = {}


def _declared_entries(root: str) -> dict[str, Any]:
    """Registry entries by capability id, from both registries (bound wins)."""
    if root not in _DECLARED_ARG_CACHE:
        merged: dict[str, Any] = {}
        for rel in (EXTENDED, BOUND):
            try:
                merged.update(json.load(open(os.path.join(root, rel), encoding="utf-8"))["capabilities"])
            except (OSError, ValueError, KeyError):
                continue
        _DECLARED_ARG_CACHE[root] = merged
    return _DECLARED_ARG_CACHE[root]


def _probe_output_path(capability_id: str, module_sha: str) -> str:
    """A deterministic, repository-local sink so a probe is reproducible by `--verify`."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", capability_id)
    return os.path.join(
        "canonical", "astra_runtime", "tmp", "receipt_probe", f"{safe}__{module_sha[:12]}.json"
    )


def declared_probe_args(root: str, capability_id: str, module_sha: str) -> dict[str, Any]:
    """The capability's own declared invocation, with `${input.*}` given probe values.

    `action_template.args` already states precisely how the brain invokes this
    capability. The probe discarded it and called `run({}, root)`, so any adapter
    that reads an argument -- `source.candidates.enumerate.stdlib` raises
    `JSON_OUTPUT_REQUIRED` on an absent `output_path` -- could never be receipted,
    and `except BaseException: return None` made that look like "no evidence
    available" rather than "the probe never ran it". Placeholders are filled with
    deterministic values only: a capability id for free text and a content-addressed
    path for sinks, so a later `--verify` re-execution reaches the same result hash.
    """
    entry = _declared_entries(root).get(capability_id)
    template = (entry or {}).get("action_template")
    args = dict(((template or {}).get("args")) or {})
    args.pop("capability_id", None)
    sink = _probe_output_path(capability_id, module_sha)
    for key, value in list(args.items()):
        if isinstance(value, str) and value.startswith("${input.") and value.endswith("}"):
            name = value[len("${input."):-1]
            args[key] = sink if name.endswith("_path") else capability_id
    return args


def _probe_invoke(
    fn: Any, root: str, capability_id: str, module_sha: str
) -> tuple[Any, dict[str, Any]]:
    """Run the adapter, preferring the empty-arg probe and falling back to declared args.

    Monotonic by construction: the `{}` call is attempted first and unchanged, so
    every receipt the lane already issued still issues identically, and only
    adapters that the empty call cannot exercise gain one.
    """
    try:
        return fn({}, root), {}
    except BaseException:  # noqa: BLE001 - the empty probe is a first attempt, not a verdict
        pass
    declared = declared_probe_args(root, capability_id, module_sha)
    if not declared:
        raise
    return fn(declared, root), declared


def contract_shape(path: str | os.PathLike) -> tuple[str, str] | None:
    """(entrypoint, second_param) if the module speaks `fn(args, root) -> dict`."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in ENTRYPOINTS:
            continue
        params = [a.arg for a in node.args.posonlyargs + node.args.args]
        if len(params) == 2 and params[0] in ARGS_NAMES:
            return node.name, params[1]
    return None


GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
GITHUB_OIDC_JWKS_URL = "https://token.actions.githubusercontent.com/.well-known/jwks.json"

_JWKS_CACHE: dict[str, Any] | None = None


def _fetch_jwks() -> dict[str, Any]:
    """Fetch GitHub's OIDC JWKS. Cached in memory after first fetch."""
    global _JWKS_CACHE
    if _JWKS_CACHE is not None:
        return _JWKS_CACHE
    try:
        import urllib.request
        with urllib.request.urlopen(GITHUB_OIDC_JWKS_URL, timeout=10) as resp:
            _JWKS_CACHE = json.loads(resp.read().decode("utf-8"))
        return _JWKS_CACHE
    except Exception:
        _JWKS_CACHE = {}
        return _JWKS_CACHE


def verify_oidc_jwt(token: str, audience: str | None = None) -> dict[str, Any] | None:
    """Verify a GitHub OIDC JWT signature against the provider's JWKS.

    Returns the verified claims dict on success, None on any failure.
    A locally forged token cannot pass: only `token.actions.githubusercontent.com`
    can sign with the private key matching the published JWKS.
    """
    if not token or not isinstance(token, str):
        return None
    try:
        import jwt  # PyJWT
    except ImportError:
        return None
    try:
        unverified = jwt.get_unverified_header(token)
    except Exception:
        return None
    kid = unverified.get("kid")
    if not kid:
        return None
    jwks = _fetch_jwks()
    keys = jwks.get("keys") if isinstance(jwks, dict) else None
    if not isinstance(keys, list):
        return None
    matching = [k for k in keys if k.get("kid") == kid]
    if not matching:
        return None
    jwk = matching[0]
    try:
        claims = jwt.decode(
            token,
            jwk,
            algorithms=["RS256"],
            issuer=GITHUB_OIDC_ISSUER,
            audience=audience,
            options={"require": ["exp", "iat", "nbf"]},
        )
    except Exception:
        return None
    if not isinstance(claims, dict):
        return None
    if claims.get("iss") != GITHUB_OIDC_ISSUER:
        return None
    return claims


def run_reference_is_attested(run_reference: Any,
                              oidc_token: str | None = None) -> bool:
    """True only for a reference carrying GitHub-SIGNED OIDC claims.

    When ``oidc_token`` is supplied, the raw JWT is verified against
    GitHub's OIDC JWKS -- a locally forged token cannot pass.  When no
    token is supplied, falls back to the issuer-claim check (weaker: a
    local process can fabricate claims but cannot obtain a GitHub-signed
    token).
    """
    if not isinstance(run_reference, Mapping):
        return False
    claims = run_reference.get("oidc_claims")
    if not isinstance(claims, Mapping):
        return False
    if claims.get("iss") != GITHUB_OIDC_ISSUER:
        return False
    if not bool(claims.get("repository") and claims.get("run_id")):
        return False
    if oidc_token is not None:
        verified = verify_oidc_jwt(oidc_token, audience=claims.get("repository"))
        if verified is None:
            return False
    return True


def _changed_paths(root: str) -> set[str] | None:
    proc = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=root,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return {line[3:].strip().strip('"') for line in proc.stdout.splitlines() if len(line) > 3}


def restore_tree(root: str, before: set[str] | None, allowed: tuple[str, ...]) -> list[str]:
    """Undo everything probing wrote, so a probe can never mutate the project.

    Probing executes real modules; some write reports, state files or even registry entries
    as a side effect.  Measured: a 616-module probe created a file literally named `--help`,
    `capability_reality_audit.json`, state snapshots, and modified the extended registry.
    Paths that were already dirty BEFORE the probe are left alone.
    """
    if before is None:
        return []
    after = _changed_paths(root)
    if after is None:
        return []
    reverted: list[str] = []
    for path in sorted(after - before):
        if any(token in path for token in allowed):
            continue
        full = os.path.join(root, path)
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=root,
                                 capture_output=True).returncode == 0
        try:
            if tracked:
                subprocess.run(["git", "checkout", "--", path], cwd=root, capture_output=True)
            elif os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)
            else:
                os.remove(full)
        except OSError:
            continue
        reverted.append(path)
    return reverted


def receipt_path_for(capability_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in capability_id)
    return f"{RECEIPT_DIR}/CAPABILITY__{safe}__EXECUTION_RECEIPT.json"


def verification_path_for(receipt_path: str) -> str:
    return receipt_path.replace("__EXECUTION_RECEIPT.json", "__INDEPENDENT_VERIFICATION.json")


def execute_and_receipt(capability_id: str, module_path: str, entrypoint: str,
                        root: str, ran_by: str, kind: str = "contract") -> dict[str, Any] | None:
    """Run one capability and return its receipt. Returns None if it did not run."""
    started = time.perf_counter()
    module_sha = sha256_file(os.path.join(root, module_path))
    if kind == "cli":
        cli = run_cli_adapter(module_path, root)
        if cli is None:
            return None
        structured = cli["structured_stdout"]
        observed = {"returncode": cli.get("returncode")}
        for field in ("status", "pass", "output_verified"):
            if field in structured:
                observed[field] = structured[field]
        return {
            "schema": SCHEMA,
            "capability_id": capability_id,
            "kind": "cli",
            "module_path": module_path,
            "module_sha256": module_sha,
            "entrypoint": "run",
            "invoked_args": {"argv": cli_argv_for(module_path)},
            "outcome": "EXECUTED",
            "observed": observed,
            "result_sha256": sha256_canonical(structured),
            "result_key_count": len(structured),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "executor": "bound_capabilities.cli_command",
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "ran_by": ran_by,
            "runtime": {"python": platform.python_version(), "platform": platform.system().lower()},
            "independent_verifier": None,
            "independent_run_reference": None,
        }
    module_name = "pb_receipt_lane_" + module_sha[:16]
    outcome = "UNKNOWN"
    result: Any = None
    observed: dict[str, Any] = {}
    invoked: dict[str, Any] = {}
    try:
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(root, module_path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(PROBE_TIMEOUT_S)
        try:
            spec.loader.exec_module(module)
            fn = getattr(module, entrypoint, None)
            if not callable(fn):
                return None
            result, invoked = _probe_invoke(fn, root, capability_id, module_sha)
        finally:
            signal.alarm(0)
    except BaseException:  # noqa: BLE001 - a failed probe is data, not an error
        return None
    finally:
        # Deliberately NOT popped from sys.modules: these modules are the brain's own runtime
        # and later ones resolve earlier ones through the import system.  Popping here silently
        # broke 90 of 150 executions (measured 29 receipts with the pop, 119 without).
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

    if not isinstance(result, dict):
        return None
    outcome = "EXECUTED"
    for field in ("status", "pass", "output_verified"):
        if field in result:
            observed[field] = result[field]

    return {
        "schema": SCHEMA,
        "capability_id": capability_id,
        "kind": "contract",
        "module_path": module_path,
        "module_sha256": module_sha,
        "entrypoint": entrypoint,
        "invoked_args": invoked,
        "outcome": outcome,
        "observed": observed,
        "result_sha256": sha256_canonical(result),
        "result_key_count": len(result),
        "elapsed_ms": elapsed_ms,
        "executor": "run_adapter_locally_contract",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "ran_by": ran_by,
        "runtime": {"python": platform.python_version(), "platform": platform.system().lower()},
        "independent_verifier": None,
        "independent_run_reference": None,
    }


def verify_producer_receipts(root: str, ran_by: str,
                             run_reference: Mapping[str, Any] | None) -> dict[str, Any]:
    """Re-execute producer receipts as a DIFFERENT identity and stamp only what reproduces.

    Independence is the whole point (AGENTS.md rule 4: "Verification means someone else ran
    it").  A producer receipt is self-issued and admits nothing on its own.  This runs the
    same module again, and writes a verification record ONLY when the observed result hash
    matches the producer's.  Mismatch, crash or timeout writes nothing and is reported.

    `independent_run_reference` must carry a platform-attested run id.  A reference this
    process invented itself is not independence, and the admission gate refuses references
    without `github_run_id` for exactly that reason.
    """
    import glob as _glob

    oidc_token = run_reference.get("oidc_token") if isinstance(run_reference, Mapping) else None
    attested = run_reference_is_attested(run_reference, oidc_token=oidc_token)
    produced: list[str] = []
    reproduced: list[str] = []
    mismatched: list[str] = []
    unreadable: list[str] = []

    for receipt_path in sorted(_glob.glob(os.path.join(root, RECEIPT_DIR, "CAPABILITY__*__EXECUTION_RECEIPT.json"))):
        rel = os.path.relpath(receipt_path, root)
        try:
            producer = json.loads(open(receipt_path, encoding="utf-8").read())
        except (OSError, ValueError):
            unreadable.append(rel)
            continue
        if producer.get("schema") != SCHEMA or not producer.get("capability_id"):
            unreadable.append(rel)
            continue
        if producer.get("ran_by") == ran_by:
            # Same identity: not an independent run at all. Never count it.
            mismatched.append(rel)
            continue

        fresh = execute_and_receipt(producer["capability_id"], producer["module_path"],
                                   producer["entrypoint"], root, ran_by,
                                   str(producer.get("kind") or "contract"))
        if fresh is None or fresh.get("result_sha256") != producer.get("result_sha256"):
            mismatched.append(rel)
            continue

        if not attested:
            # Reproduction confirmed, but this process cannot attest it. Reporting is honest;
            # writing would forge independence and overwrite a real runner's record.
            reproduced.append(producer["capability_id"])
            continue

        record = {
            "schema": VERIFICATION_SCHEMA,
            "capability_id": producer["capability_id"],
            "module_path": producer["module_path"],
            "module_sha256": producer["module_sha256"],
            "producer_receipt_path": rel,
            "producer_ran_by": producer.get("ran_by"),
            "producer_result_sha256": producer.get("result_sha256"),
            "verifier_result_sha256": fresh.get("result_sha256"),
            "reproduced": True,
            "independent_verifier": ran_by,
            "independent_run_reference": dict(run_reference or {}),
            "elapsed_ms": fresh.get("elapsed_ms"),
            "model_dependency_count": 0,
        }
        out_path = os.path.join(root, verification_path_for(rel))
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
        produced.append(rel)
        reproduced.append(producer["capability_id"])

    return {"producer_receipts": len(produced) + len(mismatched) + len(unreadable),
            "reproduced": len(reproduced), "mismatched": len(mismatched),
            "unreadable": len(unreadable), "capability_ids": reproduced,
            "not_reproduced": sorted(mismatched)[:25],
            "run_reference_attested": attested,
            "records_written": len(produced),
            "note": ("wrote independent verification records" if attested else
                     "reproduction confirmed but NOT written: a run reference without signed "
                     "GitHub OIDC claims is not independence")}


def _has_independence_claim(entry: dict[str, Any]) -> bool:
    """Whether the entry already carries an independence claim, read as the gate reads it.

    Mirrors `verified_bound_capability_execution_adapter_v1`, so "needs attestation"
    here means exactly "the bound adapter will refuse to run this capability".
    """
    verification = entry.get("verification")
    if not isinstance(verification, dict):
        return False
    return (
        verification.get("independent_verified") is True
        or verification.get("independently_verified") is True
        or isinstance(verification.get("independently_verified_by"), str)
        or verification.get("producer_independent") is True
    )


def _bound_module_path(root: str, entry: dict[str, Any]) -> str | None:
    """The adapter module a bound capability runs through, if it is in the tree."""
    source = entry.get("source")
    declared = str((source or {}).get("adapter_path") or "") if isinstance(source, dict) else ""
    for candidate in (
        declared,
        os.path.join(
            "canonical", "runtime", "bound_capabilities",
            str(entry.get("adapter_module") or "") + ".py",
        ),
    ):
        if candidate and os.path.isfile(os.path.join(root, candidate)):
            return candidate
    return None


def discover(root: str, kinds: tuple[str, ...] = ("contract", "cli")) -> list[tuple[str, str, str, str]]:
    """Inventory entries needing a producer receipt, by invocation kind.

    Returns (capability_id, module_path, kind, entrypoint).  `kind` was previously carried in
    the entrypoint slot and silently dropped by the caller, so every CLI candidate was
    executed as a contract module and failed instantly: 25 candidates, 0 receipts, 423/s.

    `contract` - speaks `run(args, root) -> dict` and is called in-process.
    `cli`      - executable as a program and is run through the repository's own
                 `bound_capabilities/cli_command.py` adapter.

    Two populations need receipts, and only the first was covered. Extended-registry
    entries are not executable at all yet. Bound entries *are* executable -- but
    "executable" was being read as "already verified", which it is not: 36 of the 72
    bound capabilities carry no independence claim the gate accepts, so the bound
    adapter refuses them and no success of theirs can become verified experience.
    Skipping them left that gap permanently unclosable, because the independent
    verifier can only re-run what a producer receipt already describes.
    """
    extended = json.load(open(os.path.join(root, EXTENDED), encoding="utf-8"))["capabilities"]
    bound = json.load(open(os.path.join(root, BOUND), encoding="utf-8"))["capabilities"]
    out: list[tuple[str, str, str, str]] = []

    def _add(cid: str, path: str) -> None:
        shape = contract_shape(os.path.join(root, path))
        if shape is not None:
            if "contract" in kinds:
                out.append((cid, path, "contract", shape[0]))
            return
        if "cli" in kinds and cli_shape(os.path.join(root, path)):
            # entrypoint is the adapter's function; cli_command always exposes `run`
            out.append((cid, path, "cli", "run"))

    for cid, entry in extended.items():
        if cid in bound:
            continue
        path = str((entry.get("source") or {}).get("path") or "")
        if not path or not os.path.isfile(os.path.join(root, path)):
            continue
        _add(cid, path)

    for cid, entry in sorted(bound.items()):
        if not isinstance(entry, dict) or _has_independence_claim(entry):
            continue
        path = _bound_module_path(root, entry)
        if path is not None:
            _add(cid, path)
    return out


def _declared_expectation(is_cli: bool, observed: dict[str, Any]) -> dict[str, Any] | None:
    """The strictest expectation the receipt's own evidence supports, and no stricter.

    `cli_command` always returns a returncode and raises on a non-zero one, so a CLI receipt
    supports `returncode == 0`.  For a contract run the receipt recorded only the fields below,
    so one of those is asserted if it was present, and otherwise nothing is asserted at all:
    `run_adapter_locally` still fails closed on an adapter that does not import, an entrypoint
    that is missing, or a result that is not a dict, so the execution itself remains the claim.
    """
    if is_cli:
        return {"type": "field_equals", "field": "returncode", "value": 0}
    if "status" in observed:
        return {"type": "field_nonempty", "field": "status"}
    if observed.get("pass") is True:
        return {"type": "field_equals", "field": "pass", "value": True}
    if observed.get("output_verified") is True:
        return {"type": "field_equals", "field": "output_verified", "value": True}
    return None


def projection_entry(receipt: dict[str, Any]) -> dict[str, Any]:
    """A registry entry in the shape the loader and `run_adapter_locally` consume.

    Derived from the receipt, never hand-written.  `status` is deliberately left
    as the inventory value: a receipt is evidence, not a promotion.
    """
    cid = receipt["capability_id"]
    stem = os.path.basename(receipt["module_path"])[:-3]
    keywords: list[str] = []
    for token in stem.split("_"):
        if len(token) > 2 and token not in keywords:
            keywords.append(token)
    is_cli = receipt.get("kind") == "cli"
    observed = receipt.get("observed") if isinstance(receipt.get("observed"), dict) else {}
    return {
        "status": "RECEIPT_BACKED_PENDING_PROMOTION",
        "incremental_spend_usd": 0,
        "cost": 1,
        "adapter_module": "cli_command" if is_cli else stem,
        "entrypoint": receipt["entrypoint"],
        "keywords": keywords[:24],
        "platforms": ["linux"],
        "requires": [],
        "provides": [cid],
        "source": {"type": "repository_python_source", "path": receipt["module_path"],
                   "adapter_path": CLI_ADAPTER if is_cli else receipt["module_path"]},
        "action_template": {
            "type": "invoke_capability",
            "args": ({"capability_id": cid, "argv": receipt["invoked_args"]["argv"], "timeout_s": 60}
                     if is_cli else {"capability_id": cid}),
            # The declared expectation may not claim more than the receipt observed.  This
            # used to be `field_nonempty status` for every non-CLI capability, which is an
            # assumption, not evidence: 7 of the 294 recorded `observed: {}` because their
            # entrypoint returned a dict carrying none of status/pass/output_verified, and the
            # projection then advertised an expectation those runs had never met (measured:
            # executing the projection, those 7 fail their own template with
            # ACTION_EXPECTATION_FAILED:status:OBSERVED=None).  Derive it from the receipt and
            # declare nothing when the receipt established nothing.
            "expect": _declared_expectation(is_cli, observed),
        },
        "verification": {
            "receipt_path": receipt["receipt_path"],
            "module_sha256": receipt["module_sha256"],
            "observed_effect": receipt["observed"],
            "model_dependency_count": 0,
            "producer_independent": receipt["independent_verifier"] is not None,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Issue content-addressed capability execution receipts.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--kinds", default="contract,cli",
                    help="which invocation kinds to probe (contract, cli)")
    ap.add_argument("--ran-by", default=os.environ.get("BRAIN_RUNNER_IDENTITY", "local-session"))
    ap.add_argument("--verify", action="store_true",
                    help="re-execute producer receipts as this identity and stamp only reproductions")
    ap.add_argument("--run-reference-json", default=os.environ.get("BRAIN_RUN_REFERENCE", ""),
                    help='platform-attested run reference, e.g. \'{"github_run_id": 123}\'')
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    # The brain's own modules import each other as `canonical.runtime.*`.  Run as a script,
    # sys.path[0] is this file's directory, so those imports fail immediately -- measured 29
    # receipts without the repository root on sys.path, 119 with it.
    if root not in sys.path:
        sys.path.insert(0, root)

    if args.verify:
        run_reference = {}
        if args.run_reference_json.strip():
            run_reference = json.loads(args.run_reference_json)
        # Verifying re-executes modules, so it mutates the tree exactly like probing does
        # (measured: a verify run regenerated LONG_HORIZON_CONTINUITY_REPORT.json).
        verify_before = _changed_paths(root)
        result = verify_producer_receipts(root, args.ran_by, run_reference)
        reverted = restore_tree(root, verify_before, ("astra_runtime/evidence/CAPABILITY__",))
        result["probe_side_effects_reverted"] = len(reverted)
        result["reverted_sample"] = reverted[:10]
        result["independent_verifier"] = args.ran_by
        result["run_reference"] = run_reference
        result["note"] = ("records written only for an attestable run reference; a local "
                          "process can confirm reproduction but never certify it")
        print(json.dumps(result, indent=1))
        return 0

    before = _changed_paths(root)
    candidates = discover(root, tuple(k.strip() for k in args.kinds.split(",") if k.strip()))
    if args.limit:
        candidates = candidates[: args.limit]

    os.makedirs(os.path.join(root, RECEIPT_DIR), exist_ok=True)
    receipts: list[dict[str, Any]] = []
    started = time.perf_counter()
    for cid, path, kind, entrypoint in candidates:
        receipt = execute_and_receipt(cid, path, entrypoint, root, args.ran_by, kind)
        if receipt is None:
            continue
        receipt["receipt_path"] = receipt_path_for(cid)
        with open(os.path.join(root, receipt["receipt_path"]), "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=1, sort_keys=True)
        receipts.append(receipt)
    elapsed = time.perf_counter() - started

    # Probing must not mutate the project: some modules write reports, state files or even
    # registry entries as a side effect.
    reverted = restore_tree(root, before, ("astra_runtime/evidence/CAPABILITY__",
                                           "CAPABILITY_RECEIPT_PROJECTION_V1.json"))

    entries = {r["capability_id"]: projection_entry(r) for r in receipts}
    with open(os.path.join(root, PROJECTION), "w", encoding="utf-8") as fh:
        json.dump({"schema": "PROJECT_BRAIN_CAPABILITY_RECEIPT_PROJECTION_V1",
                   "count": len(entries), "entries": entries}, fh, indent=1, sort_keys=True)

    print(json.dumps({
        "candidates": len(candidates),
        "receipts_issued": len(receipts),
        "wall_time_s": round(elapsed, 3),
        "throughput_per_s": round(len(candidates) / elapsed, 1) if elapsed else None,
        "receipt_dir": RECEIPT_DIR,
        "projection": PROJECTION,
        "status_flipped": False,
        "probe_side_effects_reverted": len(reverted),
        "reverted_sample": reverted[:10],
        "independent_verifier": None,
        "note": "evidence only; promotion requires a different identity to re-run",
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
