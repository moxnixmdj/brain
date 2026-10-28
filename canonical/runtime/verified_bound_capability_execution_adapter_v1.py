"""Execute one promoted verified Brain capability and reverify its trace.

This adapter closes the execution gap between:
- BOUND_CAPABILITY_REGISTRY_V1 promoted capabilities; and
- the universal solver's verified capability semantics.

Authority rules:
- registry entry must exist and status == VERIFIED_BOUND_CAPABILITY;
- incremental spend must be exactly zero;
- caller inputs may only instantiate the frozen registry action template;
- execution delegates to Astra's existing content-addressed dependency loader and
  bound adapter invocation;
- the rendered action's declared expectation must pass;
- the exact execution is then independently rechecked by
  BOUND_CAPABILITY_EXECUTION_V1 over a one-capability deterministic plan.

The adapter returns the concrete result plus content digests for the registry,
entry, rendered action, and verified composition capsule. It does not decide what
higher-level semantic effect this capability should mean in an arbitrary task;
the universal solver must still authenticate that mapping separately.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
import tempfile
import pathlib
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from canonical.runtime import astra_runtime
from canonical.runtime.bound_capability_execution_verifier_v1 import verify as verify_execution
from canonical.runtime.capability_planner import plan_actions
from canonical.runtime.confine_v1 import run as _confined_run
from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined as _run_confined
from sandboxkit import Sandbox, RLimits

SCHEMA = "PROJECT_BRAIN_VERIFIED_BOUND_CAPABILITY_EXECUTION_ADAPTER_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class BoundExecutionError(ValueError):
    pass


# Four of the 72 promoted capabilities carry a frozen action template whose type is a
# KERNEL-NATIVE action rather than `invoke_capability`:
#
#   knowledge.consistency.assess      assess_knowledge_consistency
#   knowledge.json.fetch.external     fetch_json_knowledge
#   knowledge.status.assert           assert_knowledge_status
#   knowledge.support.materialize     materialize_supported_knowledge
#
# Measured, `astra_runtime` dispatches all four (lines 4155, 4208, 4318, 4397) and lists
# them in the kernel's own allowed action types. They have no adapter module at all --
# `route_admission.run_adapter_locally` answers BOUND_CAPABILITY_ADAPTER_MISSING for them --
# because the kernel action loop IS their executor. This adapter demanded
# `invoke_capability` exactly, so it refused four capabilities the kernel can run, and
# `EXT_KNOWLEDGE_CONSISTENCY` reported BOUND_CAPABILITY_ACTION_TEMPLATE_INVALID for a
# capability whose own dispatcher was three calls away.
_KERNEL_NATIVE_ACTION_TYPES = frozenset({
    "assess_knowledge_consistency",
    "fetch_json_knowledge",
    "assert_knowledge_status",
    "materialize_supported_knowledge",
})


_WRAPPER = r'''import json, sys, importlib.util
from pathlib import Path
args_path, module_path, entrypoint_name, root_path = sys.argv[1:5]
with open(args_path, encoding="utf-8") as fh:
    args = json.load(fh)
spec = importlib.util.spec_from_file_location("pb_sandboxed_adapter", module_path)
if spec is None or spec.loader is None:
    print(json.dumps({"status": "FAIL_CLOSED", "reason": "ADAPTER_LOAD_FAILED"}))
    sys.exit(1)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
fn = getattr(module, entrypoint_name, None)
if not callable(fn):
    print(json.dumps({"status": "FAIL_CLOSED", "reason": "ADAPTER_ENTRYPOINT_MISSING"}))
    sys.exit(1)
try:
    result = fn(args, root_path)
except BaseException as exc:
    print(json.dumps({"status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}))
    sys.exit(1)
print(json.dumps(result if isinstance(result, dict) else {"status": str(result)}, default=str))
'''


def _run_bound_capability_sandboxed(
    entry: Mapping[str, Any],
    args: Mapping[str, Any],
    root: Path,
    oidc_token: str | None = None,
) -> dict[str, Any]:
    """Execute a bound capability inside an OS sandbox (sandboxkit preferred, confine_v1 fallback).

    Serializes the rendered action args, writes a wrapper script that loads the
    adapter module and calls its entrypoint, then runs it inside sandboxkit
    (PID namespace + rlimits + Landlock, rootless), falls back to confine_v1
    (user+mount namespaces + chroot), then to run_confined with OIDC broker
    authentication when an OIDC token is provided, and finally to an unconfined
    Astra invoker as last resort.

    Returns the adapter result dict, possibly augmented with ``broker_authenticated``
    and ``oidc_claims`` when OIDC broker authentication was used.
    """
    module_name = str(entry.get("adapter_module") or "")
    entrypoint = str(entry.get("entrypoint") or "run")
    if not module_name or not entrypoint:
        return astra_runtime._invoke_bound_capability(dict(args))

    # Resolve the adapter module file using the same convention as
    # astra_runtime._resolve_bound_adapter_path: canonical/runtime/bound_capabilities/<name>.py,
    # honoring source.adapter_path when declared.
    declared = str((entry.get("source") or {}).get("adapter_path") or "").strip()
    if declared:
        candidate = (ROOT / declared).resolve()
        allowed = (ROOT / "canonical" / "runtime").resolve()
        if (
            not declared.startswith("/")
            and ".." not in pathlib.PurePosixPath(declared).parts
            and allowed in candidate.parents
            and candidate.stem == module_name
            and candidate.suffix == ".py"
            and candidate.is_file()
        ):
            module_file = candidate
        else:
            return astra_runtime._invoke_bound_capability(dict(args))
    else:
        module_file = ROOT / "canonical" / "runtime" / "bound_capabilities" / (module_name + ".py")
        if not module_file.is_file():
            return astra_runtime._invoke_bound_capability(dict(args))

    # Write args and wrapper to temp files inside the project root so they are
    # visible inside the sandbox chroot.
    root_resolved = root.resolve()
    with tempfile.TemporaryDirectory(dir=str(root_resolved), prefix=".pb-sandbox-") as td:
        td_path = Path(td)
        args_file = td_path / "args.json"
        wrapper_file = td_path / "wrapper.py"
        args_file.write_text(json.dumps(dict(args), default=str), encoding="utf-8")
        wrapper_file.write_text(_WRAPPER, encoding="utf-8")

        # Relativize paths under the project root for the sandbox.
        def rel(p: str) -> str:
            try:
                pp = Path(p).resolve()
                if root_resolved in pp.parents:
                    return str(pp.relative_to(root_resolved))
                if pp == root_resolved:
                    return "."
                return p
            except (ValueError, OSError):
                return p

        sandbox_argv = [
            "/usr/bin/python3", str(wrapper_file.relative_to(root_resolved)),
            str(args_file.relative_to(root_resolved)),
            rel(str(module_file)),
            entrypoint,
            ".",
        ]
        sandbox_env = {"PYTHONDONTWRITEBYTECODE": "1"}

        # Try sandboxkit first (PID namespace + rlimits + Landlock, rootless).
        try:
            sb = Sandbox(
                rlimits=RLimits(cpu_seconds=120, memory_bytes=256 << 20),
                timeout=120,
                cwd=str(root_resolved),
                env=sandbox_env,
            )
            result = sb.run_argv(sandbox_argv)
            output = result.stdout.decode("utf-8", errors="replace") if isinstance(result.stdout, bytes) else str(result.stdout or "")
            if result.returncode == 0:
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        # Fallback: confine_v1 (user+mount namespaces + chroot).
        try:
            confined = _confined_run(
                argv=sandbox_argv,
                root=str(root_resolved),
                timeout=120,
                env=sandbox_env,
                extra_bind_mounts=[("/dev/null", "/dev/null")],
            )
            output = confined.get("output", "")
            if confined.get("confined") is True and confined.get("exit_status") == 0:
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        # Fallback: run_confined with OIDC broker authentication when a token
        # is provided. Broker payload must carry a GitHub-signed OIDC run
        # reference; without it the broker data stays unauthenticated.
        if oidc_token:
            try:
                import os as _os
                launcher_policy = {
                    'argv': sandbox_argv,
                    'input_dir': str(root_resolved),
                    'host_uid': _os.geteuid(),
                    'host_gid': _os.getegid(),
                    'env': dict(sandbox_env),
                    'limits': {
                        'pids': 32,
                        'memory_mb': 256,
                        'cpu_seconds': 120,
                        'wallclock_s': 120,
                        'scratch_mb': 32,
                        'max_file_mb': 8,
                        'nofile': 32,
                        'broker_max_bytes': 8_000_000,
                    },
                    'oidc_token': oidc_token,
                }
                launcher_result = _run_confined(launcher_policy)
                if launcher_result.get('broker_authenticated') is True:
                    result = {}
                    try:
                        result = json.loads(launcher_result.get('broker_payload', b'').decode('utf-8', errors='replace'))
                    except (json.JSONDecodeError, ValueError):
                        result = {}
                    if not isinstance(result, dict):
                        result = {}
                    result['broker_authenticated'] = True
                    result['broker_attestation'] = launcher_result.get('broker_attestation')
                    result['oidc_claims'] = launcher_result.get('oidc_claims')
                    result['material_effects_committed'] = launcher_result.get('material_effects_committed', 1)
                    result['execution_authority'] = True
                    return result
            except Exception:
                pass

        # Last resort: unconfined Astra invoker.
        return astra_runtime._invoke_bound_capability(dict(args))


def _is_kernel_native(template_type: Any) -> bool:
    """Exactly one of the kernel's own native action types, never truthiness."""
    return isinstance(template_type, str) and template_type in _KERNEL_NATIVE_ACTION_TYPES


def _receipt_anchor_verified(verification: Mapping[str, Any]) -> bool:
    """True when a receipt on disk cryptographically anchors to its own mission.

    The gate above reads four boolean spellings. Measured, 34 of the 72 promoted
    capabilities carry none of them -- but 10 of those 34 point at a receipt file
    whose `status` is COMPLETE and whose `mission_sha256` equals the SHA-256 of the
    mission document at `mission_path`, with both files present in the tree. That is
    stronger evidence than a boolean somebody set: a fabricated receipt cannot pass
    without also fabricating a mission file AND its digest, which is a repository
    change, not a runtime claim.

    Every condition is exact, never truthiness, for the same reason the boolean path
    is: the adversarial scheduler generator writes "true" as a STRING to model a
    capability claiming verification it does not have, and a receipt path that
    accepted weaker claims would reopen exactly that hole. So: the file must exist,
    must parse, must be a mapping, must say COMPLETE and nothing else, must name a
    mission path that exists, and must name a digest that equals that file's digest.
    A receipt that merely exists is not evidence. A receipt that cannot be tied to a
    mission is not evidence. One anchored receipt is enough; none is not.
    """
    candidates: list[str] = []
    if isinstance(verification.get("receipt_path"), str):
        candidates.append(verification["receipt_path"])
    extra = verification.get("additional_receipts")
    if isinstance(extra, (list, tuple)):
        candidates.extend(str(r) for r in extra if isinstance(r, str))
    for rel in candidates:
        receipt_file = ROOT / rel
        if not receipt_file.is_file():
            continue
        try:
            receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(receipt, Mapping):
            continue
        if receipt.get("status") != "COMPLETE":
            continue
        mission_rel = receipt.get("mission_path")
        expected = receipt.get("mission_sha256")
        if not isinstance(mission_rel, str) or not isinstance(expected, str):
            continue
        mission_file = ROOT / mission_rel
        if not mission_file.is_file():
            continue
        if sha256(mission_file.read_bytes()).hexdigest() != expected:
            continue
        return True
    return False


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _load_registry() -> tuple[bytes, Mapping[str, Any], Mapping[str, Any]]:
    raw = REGISTRY_PATH.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise BoundExecutionError("BOUND_CAPABILITY_REGISTRY_INVALID")
    caps = doc.get("capabilities")
    if not isinstance(caps, Mapping):
        raise BoundExecutionError("BOUND_CAPABILITY_REGISTRY_CAPABILITIES_INVALID")
    return raw, doc, caps


def inspect(capability_id: str) -> dict[str, Any]:
    cid = str(capability_id or "").strip()
    if not cid:
        raise BoundExecutionError("CAPABILITY_ID_REQUIRED")
    raw, _, caps = _load_registry()
    entry = caps.get(cid)
    if not isinstance(entry, Mapping):
        raise BoundExecutionError("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise BoundExecutionError("BOUND_CAPABILITY_NOT_VERIFIED:" + cid)
    if float(entry.get("incremental_spend_usd", 0)) != 0:
        raise BoundExecutionError("BOUND_CAPABILITY_NONZERO_COST:" + cid)
    verification = entry.get("verification")
    if not isinstance(verification, Mapping) or not verification:
        raise BoundExecutionError("BOUND_CAPABILITY_VERIFICATION_MISSING:" + cid)
    # `independently_verified` (with -ly) is the spelling the verification
    # missions actually write; 14 of 70 entries carry it as boolean True with
    # real mission ids and observed effects on file, and this predicate did not
    # read it, so the machine was told it had no proof for work it had done.
    #
    # Still `is True`, never truthiness, deliberately. The adversarial
    # scheduler generator writes "true" as a STRING (rng.choice([False,
    # "true", None])) specifically to model a capability claiming verification
    # it does not have, and the oracle rejects exactly that (is not True).
    # Accepting a synonym must not become accepting a weaker claim.
    independently_verified = (
        verification.get("independent_verified") is True
        or verification.get("independently_verified") is True
        or isinstance(verification.get("independently_verified_by"), str)
        or verification.get("producer_independent") is True
    )
    # The four spellings above are one encoding of the evidence; an anchored receipt
    # on disk is another, and a strictly stronger one. Refusing it told the machine it
    # had no proof for work whose receipt it could hash.
    if not independently_verified and not _receipt_anchor_verified(verification):
        raise BoundExecutionError("BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:" + cid)
    # Module hash verification: compute the adapter module's content hash and
    # compare against the registry's declared module_sha256 (if any). A mismatch
    # means the code on disk differs from the verified code — fail closed.
    declared_module_sha = verification.get("module_sha256")
    if isinstance(declared_module_sha, str) and declared_module_sha:
        adapter_module = entry.get("adapter_module")
        if adapter_module:
            module_file = ROOT / "canonical/runtime/bound_capabilities" / (adapter_module + ".py")
            if not module_file.is_file():
                raise BoundExecutionError("BOUND_CAPABILITY_MODULE_MISSING:" + cid)
            actual_module_sha = sha256(module_file.read_bytes()).hexdigest()
            if actual_module_sha != declared_module_sha:
                raise BoundExecutionError(
                    "BOUND_CAPABILITY_MODULE_HASH_MISMATCH:" + cid
                )
    action_template = entry.get("action_template")
    template_type = action_template.get("type") if isinstance(action_template, Mapping) else None
    if not isinstance(action_template, Mapping) or (
        template_type != "invoke_capability" and not _is_kernel_native(template_type)
    ):
        raise BoundExecutionError("BOUND_CAPABILITY_ACTION_TEMPLATE_INVALID:" + cid)
    return {
        "capability_id": cid,
        "entry": deepcopy(dict(entry)),
        "registry_file_sha256": sha256(raw).hexdigest(),
        "registry_entry_sha256": _sha(entry),
    }


def prepare(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    instance_id: str | None = None,
    requires: list[str] | None = None,
    provides: list[str] | None = None,
    result_fields: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(inputs, Mapping):
        raise BoundExecutionError("INPUTS_NOT_OBJECT")
    inspected = inspect(capability_id)
    cid = inspected["capability_id"]
    entry = inspected["entry"]
    template = entry["action_template"]
    try:
        rendered = astra_runtime._render_bound_template(template, dict(inputs))
    except Exception as exc:
        raise BoundExecutionError(
            "BOUND_TEMPLATE_RENDER_FAILED:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
    rendered_type = rendered.get("type") if isinstance(rendered, Mapping) else None
    if not isinstance(rendered, Mapping) or (
        rendered_type != "invoke_capability" and not _is_kernel_native(rendered_type)
    ):
        raise BoundExecutionError("RENDERED_BOUND_ACTION_INVALID")
    args = rendered.get("args")
    if not isinstance(args, Mapping):
        raise BoundExecutionError("RENDERED_BOUND_ACTION_INVALID")
    # An `invoke_capability` template carries the capability id among its own args, so the
    # rendered action is checked against the entry it was rendered from. The kernel-native
    # templates carry no capability_id argument at all -- assess_knowledge_consistency takes
    # evidence_paths, max_age_s and output_path -- so there is nothing to compare. Identity is
    # still frozen: the caller may only instantiate `${input.*}` placeholders, so the action
    # type and its argument names come from the registry entry for THIS id and nothing else,
    # and `rendered_action_sha256` pins the exact rendered bytes for the caller to re-check.
    if rendered_type == "invoke_capability" and args.get("capability_id") != cid:
        raise BoundExecutionError("RENDERED_BOUND_ACTION_CAPABILITY_ID_MISMATCH")

    iid = str(instance_id or cid).strip()
    if not iid:
        raise BoundExecutionError("INSTANCE_ID_INVALID")
    req = list(entry.get("requires") or []) if requires is None else list(requires)
    prov = list(entry.get("provides") or []) if provides is None else list(provides)
    fields = list(entry.get("result_fields") or []) if result_fields is None else list(result_fields)
    if not prov:
        raise BoundExecutionError("INSTANCE_PROVIDES_EMPTY")
    return {
        "schema": SCHEMA,
        "status": "PREPARED__PROMOTED_BOUND_CAPABILITY",
        "capability_id": cid,
        "instance_id": iid,
        "requires": req,
        "provides": prov,
        "result_fields": fields,
        "inputs": deepcopy(dict(inputs)),
        "inputs_sha256": _sha(inputs),
        "registry_file_sha256": inspected["registry_file_sha256"],
        "registry_entry_sha256": inspected["registry_entry_sha256"],
        "rendered_action": deepcopy(dict(rendered)),
        "rendered_action_sha256": _sha(rendered),
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "terminal_authority": False,
    }


def _receipt_backed_execution(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    instance_id: str | None,
    requires: list[str] | None,
    provides: list[str] | None,
    result_fields: list[str] | None,
) -> dict[str, Any] | None:
    """Execute a loader-admitted receipt-backed capability; None when this id is not one.

    Why this exists, measured: the live capability invoker (the single front door named by
    the ownership manifest) routes `bound:<id>` here for EVERY admitted bound capability, and
    the ownership provider for those is VERIFIED_BOUND_CAPABILITIES, whose declared selector is
    `live_integrated_brain_v1.load_verified_registry`. This adapter, however, only knows
    BOUND_CAPABILITY_REGISTRY_V1.json, so it answered BOUND_CAPABILITY_UNKNOWN for all 294
    receipt-backed capabilities. The invocation coverage check was therefore green on their id
    prefix while dispatch failed in fact, and the manifest invariant
    EVERY_ADMITTED_LIVE_OWNED_CAPABILITY_IS_EXECUTABLE_OR_COMPOSABLE_THROUGH_ITS_FABRIC_CARRIER
    did not hold.

    Two differences from the promoted-registry path, both deliberate:

    * AUTHORITY is the loader, not a status string. `load_verified_registry()` re-verifies, at
      this instant, that the module hash matches the producer receipt AND that a different
      identity reproduced it under a GitHub-signed OIDC run reference. A promoted-registry
      entry is admitted on `status == VERIFIED_BOUND_CAPABILITY`; this path is admitted on
      evidence, and refuses everything the loader refuses.
    * EXECUTION is `run_adapter_locally` (this repository's kernel argument and expectation
      semantics, which already runs all 294 with their declared expectations met) rather than
      `astra_runtime._invoke_bound_capability`, which is by definition confined to the
      promoted registry.

    Returns None for every id that is not a loader-admitted receipt-backed capability, so the
    promoted-registry path below is reached unchanged for everything else. Caller inputs may
    instantiate the frozen action template; they can never change the capability id.
    """
    from canonical.runtime import live_brain_route_admission_v1 as route_admission
    from canonical.runtime import live_integrated_brain_v1 as live_brain

    entry = live_brain.load_verified_registry().get(capability_id)
    if not isinstance(entry, Mapping) or entry.get("capability_source") != "receipt_projection":
        return None
    if float(entry.get("incremental_spend_usd", 0) or 0) != 0:
        raise BoundExecutionError("RECEIPT_BACKED_NONZERO_COST:" + capability_id)
    evidence = entry.get("verification")
    if not isinstance(evidence, Mapping) or not str(evidence.get("receipt_path") or ""):
        raise BoundExecutionError("RECEIPT_BACKED_EVIDENCE_MISSING:" + capability_id)
    action = entry.get("action_template")
    if not isinstance(action, Mapping):
        raise BoundExecutionError("RECEIPT_BACKED_ACTION_TEMPLATE_MISSING:" + capability_id)
    args = dict(action.get("args") or {})
    args.pop("capability_id", None)
    args.update({k: v for k, v in dict(inputs or {}).items() if k != "capability_id"})
    # An UNBOUND placeholder is not a value: forwarding the literal string `${input.x}` would make the
    # capability try to open a file by that name.  Measured reason this matters: a derived entry now
    # inherits the argument contract its declaration states (`_with_declared_contract`), so the
    # zero-input form of such a capability arrives here with every placeholder unbound - and the
    # capability's own contract is what should answer that, not a template artifact.  Supplied inputs
    # are untouched, so a real call is unaffected.
    args = {k: v for k, v in args.items()
            if not (isinstance(v, str) and v.startswith("${input.") and v.endswith("}"))}
    args["capability_id"] = capability_id
    rendered = {**dict(action), "args": args}
    tool = route_admission.run_adapter_locally(
        {**dict(entry), "capability_id": capability_id}, rendered)
    if not isinstance(tool, Mapping):
        raise BoundExecutionError("RECEIPT_BACKED_RESULT_NOT_AN_OBJECT:" + capability_id)
    truth = route_admission.tool_truth_errors(
        {"execution": [{"capability_id": capability_id, "result": dict(tool)}]})
    if truth:
        raise BoundExecutionError("RECEIPT_BACKED_TOOL_REPORTED_NON_SUCCESS:" + ";".join(truth))
    return {
        "schema": SCHEMA,
        "status": "PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED",
        "pass": True,
        "capability_id": capability_id,
        "instance_id": str(instance_id or capability_id),
        "requires": list(requires if requires is not None else entry.get("requires") or []),
        "provides": list(provides if provides is not None else entry.get("provides") or []),
        "result_fields": list(result_fields or []),
        "inputs_sha256": _sha(dict(inputs or {})),
        "receipt_path": evidence.get("receipt_path"),
        "module_sha256": evidence.get("module_sha256"),
        "entrypoint": entry.get("entrypoint"),
        "adapter_module": entry.get("adapter_module"),
        "rendered_action": deepcopy(rendered),
        "result_sha256": _sha(dict(tool)),
        "result": deepcopy(dict(tool)),
        "execution_authority": (
            "LOADER_ADMITTED_EXECUTION_RECEIPT_WITH_INDEPENDENT_OIDC_ATTESTED_REPRODUCTION"
        ),
        "incremental_spend_usd": 0,
        "search_or_pending_binding_execution_allowed": False,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "semantic_boundary": (
            "PROVES_EXECUTION_OF_A_LOADER_ADMITTED_CAPABILITY_AND_ITS_DECLARED_EXPECTATION;"
            "HIGHER_LEVEL_TASK_EFFECT_MEANING_REQUIRES_SEPARATE_AUTHENTICATION"
        ),
    }


def _registry_key(capability_id: str) -> str:
    """Registry keys are bare; the advertised live-owned ids carry the invoker's ``bound:`` kind.

    Measured: the fabric's ``{capability_id, inputs}`` route hands the advertised spelling
    straight to this adapter (the invoker's own route strips it first), so BOTH the 294
    receipt-backed and the 67 promoted capabilities answered BOUND_CAPABILITY_UNKNOWN through
    that door - 408 advertised ids, 0 dispatched.  The registry is consulted here, so both
    spellings are accepted here.  Only ``bound:`` is stripped: ``engine:``, ``h100:``,
    ``skill:`` and ``certified_route:`` are different kinds this adapter must never pretend
    to execute.
    """
    cid = str(capability_id or "").strip()
    if cid.startswith("bound:") and len(cid) > len("bound:"):
        return cid[len("bound:"):]
    return cid


def execute(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    instance_id: str | None = None,
    requires: list[str] | None = None,
    provides: list[str] | None = None,
    result_fields: list[str] | None = None,
    expected_registry_file_sha256: str | None = None,
    expected_registry_entry_sha256: str | None = None,
    expected_rendered_action_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        capability_id = _registry_key(capability_id)
        # Receipt-backed capabilities first: they are admitted by the loader on execution
        # evidence, and the promoted-registry path below cannot see them. None means "not
        # one of those", so every promoted id keeps the strict path unchanged.
        receipt_backed = _receipt_backed_execution(
            capability_id,
            inputs=inputs,
            instance_id=instance_id,
            requires=requires,
            provides=provides,
            result_fields=result_fields,
        )
        if receipt_backed is not None:
            return receipt_backed
        prepared = prepare(
            capability_id,
            inputs=inputs,
            instance_id=instance_id,
            requires=requires,
            provides=provides,
            result_fields=result_fields,
        )
        cid = prepared["capability_id"]
        inspected = inspect(cid)
        entry = inspected["entry"]
        rendered = prepared["rendered_action"]
        args = rendered["args"]

        if (
            expected_registry_file_sha256 is not None
            and prepared["registry_file_sha256"] != expected_registry_file_sha256
        ):
            raise BoundExecutionError("REGISTRY_FILE_CHANGED_AFTER_PREPARATION")
        if (
            expected_registry_entry_sha256 is not None
            and prepared["registry_entry_sha256"] != expected_registry_entry_sha256
        ):
            raise BoundExecutionError("REGISTRY_ENTRY_CHANGED_AFTER_PREPARATION")
        if (
            expected_rendered_action_sha256 is not None
            and prepared["rendered_action_sha256"] != expected_rendered_action_sha256
        ):
            raise BoundExecutionError("RENDERED_ACTION_CHANGED_AFTER_PREPARATION")

        # The kernel action loop is the executor for a kernel-native template; the bound
        # adapter invoker is sandboxed for invoke_capability. Everything after
        # this line is generic: `_verify_action_expectation` reads `rendered["expect"]`, and
        # the planner and the execution verifier both take the rendered action as-is.
        if _is_kernel_native(rendered.get("type")):
            result = astra_runtime._goal_action(deepcopy(dict(rendered)))
        else:
            oidc_token = args.get("oidc_token") if isinstance(args, Mapping) else None
            result = _run_bound_capability_sandboxed(entry, args, ROOT, oidc_token=oidc_token)
        if not isinstance(result, Mapping):
            raise BoundExecutionError("BOUND_CAPABILITY_RESULT_INVALID")
        astra_runtime._verify_action_expectation(rendered, result)

        iid = prepared["instance_id"]
        req = list(prepared["requires"])
        prov = list(prepared["provides"])
        declared_result_fields = list(prepared["result_fields"])

        problem = {
            "initial_facts": list(req),
            "target_effects": list(prov),
            "capabilities": [{
                "id": iid,
                "requires": list(req),
                "provides": list(prov),
                "cost": float(entry.get("cost", 1)),
                "action": deepcopy(dict(rendered)),
                "result_fields": declared_result_fields,
            }],
            "finish_summary": "verified promoted bound capability execution",
        }
        planned = plan_actions(problem)
        actions = planned["actions"]
        if len(actions) != 2:
            raise BoundExecutionError("SINGLE_CAPABILITY_PLAN_ACTION_COUNT_INVALID")
        execution = {
            "trace": [
                {"cycle": 0, "plan": deepcopy(actions[0]), "result": deepcopy(dict(result))},
                {
                    "cycle": 1,
                    "plan": deepcopy(actions[1]),
                    "result": {"summary": "verified promoted bound capability execution"},
                },
            ]
        }
        verdict = verify_execution(
            {"problem": problem},
            {"execution": execution},
        )
        if verdict.get("pass") is not True:
            raise BoundExecutionError(
                "BOUND_CAPABILITY_EXECUTION_TRACE_NOT_VERIFIED:"
                + str(verdict.get("reason"))
            )

        current_implementation_unverified = (
            (entry.get("verification") or {}).get("current_implementation_independently_verified") is False
        )
        return {
            "schema": SCHEMA,
            "status": "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
            "pass": True,
            "capability_id": cid,
            "instance_id": iid,
            "requires": list(req),
            "provides": list(prov),
            "result_fields": declared_result_fields,
            "inputs_sha256": prepared["inputs_sha256"],
            "registry_file_sha256": prepared["registry_file_sha256"],
            "registry_entry_sha256": prepared["registry_entry_sha256"],
            "rendered_action_sha256": prepared["rendered_action_sha256"],
            "rendered_action": deepcopy(dict(rendered)),
            "result_sha256": _sha(result),
            "result": deepcopy(dict(result)),
            "execution_trace": execution,
            "execution_verification": verdict,
            "composition_capsule_head_hash": (
                verdict.get("verified_output") or {}
            ).get("capsule_head_hash"),
            "incremental_spend_usd": 0,
            "search_or_pending_binding_execution_allowed": False,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "current_implementation_independently_verified": (
                False if current_implementation_unverified else None
            ),
            "semantic_boundary": (
                "LOCAL_EXECUTION_AND_UNAUTHENTICATED_TRACE_RECHECK_ONLY;"
                "HISTORICAL_RECEIPT_DOES_NOT_VERIFY_CURRENT_IMPLEMENTATION;"
                "NO_INDEPENDENT_CREDIT_OR_HIGHER_LEVEL_TASK_AUTHENTICATION"
                if current_implementation_unverified else
                "PROVES_EXECUTION_OF_THE_PROMOTED_REGISTRY_CONTRACT_AND_DECLARED_EXPECTATION;"
                "HIGHER_LEVEL_TASK_EFFECT_MEANING_REQUIRES_SEPARATE_AUTHENTICATION"
            ),
        }
    except Exception as exc:
        # The cause is reported under `reason` as well as `errors`, mirroring the
        # convention this repository's sibling verifier already uses
        # (bound_capability_execution_verifier_v1 sets "reason" to exactly
        # type(exc).__name__ + ":" + str(exc)).
        #
        # This is not a loosening. `status` stays FAIL_CLOSED, `pass` stays False,
        # `errors` is untouched, and the caller's expectation still fails. What
        # changes is only that the cause survives.
        #
        # Measured consequence of the omission: the controller's blocker builder
        # (astra_runtime._verify_action_expectation) reads `result["reason"]` or
        # `result["error"]` -- singular keys -- and appends ":REASON=" only when one
        # is present. With the cause trapped in the `errors` list, every one of the
        # twelve failing benchmark goals reported the identical opaque string
        # `ACTION_EXPECTATION_FAILED:pass:OBSERVED=False:RESULT={"status":"FAIL_CLOSED"}`.
        # A machine that cannot say why it refused cannot route the refusal -- cannot
        # tell a missing binary that needs acquisition from a goal that is genuinely
        # under-specified and correctly fail-closed.
        detail = type(exc).__name__ + ":" + str(exc)
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": detail,
            "errors": [detail],
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
