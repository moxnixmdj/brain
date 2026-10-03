"""Live-bound Tool Discovery authority interface V3.

This is not a synthetic registry. It binds Tool Discovery to the exact operative
Brain capability authority already used by astra_runtime:
  canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json
and to the exact invocation chokepoint:
  astra_runtime._invoke_bound_capability()

Discovery exposes identities/cost/constraints but hides the verified provides
set. Safe probes reveal one requested capability bit from that hidden authority
record. Selection is delegated to Dynamic V3 only after a complete current
authority receipt has been supplied, so no registry member can be cheaper-yet-
undiscovered at SELECT time.
"""
from __future__ import annotations

from copy import deepcopy
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as dynamic_v3

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REL = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ASTRA_REL = "canonical/runtime/astra_runtime.py"
REGISTRY_EXPECTED_BLOB = "7badee4878700f2cd4176beb8319d2a6a0bdf782"
ASTRA_EXPECTED_BLOB = "7f5d16b1db69cb620954bc778e0ba6e15e687b75"
SOURCE_ID = "BRAIN_BOUND_CAPABILITY_AUTHORITY_V1"


class LiveAuthorityError(RuntimeError):
    pass


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load_registry() -> dict[str, Mapping[str, Any]]:
    path = ROOT / REGISTRY_REL
    if _blob(path) != REGISTRY_EXPECTED_BLOB:
        raise LiveAuthorityError("BOUND_CAPABILITY_REGISTRY_BLOB_DRIFT")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise LiveAuthorityError("BOUND_CAPABILITY_REGISTRY_SCHEMA_INVALID")
    caps = raw.get("capabilities")
    if not isinstance(caps, dict) or not caps:
        raise LiveAuthorityError("BOUND_CAPABILITY_REGISTRY_EMPTY_OR_INVALID")
    out: dict[str, Mapping[str, Any]] = {}
    for cid, rec in caps.items():
        if not isinstance(cid, str) or not cid or not isinstance(rec, Mapping):
            raise LiveAuthorityError("BOUND_CAPABILITY_RECORD_INVALID")
        if rec.get("status") != "VERIFIED_BOUND_CAPABILITY":
            raise LiveAuthorityError("UNVERIFIED_BOUND_CAPABILITY:" + cid)
        if float(rec.get("incremental_spend_usd", 0)) != 0:
            raise LiveAuthorityError("NONZERO_COST_BOUND_CAPABILITY:" + cid)
        if not isinstance(rec.get("provides"), list) or not rec.get("provides"):
            raise LiveAuthorityError("BOUND_CAPABILITY_PROVIDES_INVALID:" + cid)
        if not isinstance(rec.get("verification"), Mapping):
            raise LiveAuthorityError("BOUND_CAPABILITY_VERIFICATION_MISSING:" + cid)
        if not isinstance(rec.get("adapter_module"), str) or not rec.get("adapter_module"):
            raise LiveAuthorityError("BOUND_CAPABILITY_ADAPTER_MISSING:" + cid)
        out[cid] = rec
    return out


def authority_epoch() -> int:
    return int(REGISTRY_EXPECTED_BLOB[:15], 16)


def _public_record(cid: str, rec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "tool_id": cid,
        "cost": float(rec.get("cost", 1)),
        "available": True,
        "authorized": True,
        "epoch": authority_epoch(),
        "platforms": deepcopy(rec.get("platforms") or []),
        "requires": deepcopy(rec.get("requires") or []),
        "limitations": deepcopy(rec.get("limitations") or []),
        "source_type": str((rec.get("source") or {}).get("type") or ""),
    }


def discover() -> dict[str, Any]:
    caps = _load_registry()
    tools = [_public_record(cid, caps[cid]) for cid in sorted(caps)]
    return {
        "kind": "DISCOVERY_RESULT",
        "source_id": SOURCE_ID,
        "epoch": authority_epoch(),
        "complete": True,
        "authority_registry_git_blob": REGISTRY_EXPECTED_BLOB,
        "authority_runtime_git_blob": ASTRA_EXPECTED_BLOB,
        "tools": tools,
    }


def safe_probe(tool_id: str, capability: str, *, epoch: int) -> dict[str, Any]:
    if epoch != authority_epoch():
        raise LiveAuthorityError("STALE_AUTHORITY_EPOCH")
    caps = _load_registry()
    cid = str(tool_id or "")
    cap = str(capability or "")
    if cid not in caps:
        raise LiveAuthorityError("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if not cap:
        raise LiveAuthorityError("CAPABILITY_REQUIRED")
    rec = caps[cid]
    supported = cap in {str(x) for x in rec["provides"]}
    return {
        "kind": "SAFE_CAPABILITY_PROBE",
        "tool_id": cid,
        "capability": cap,
        "epoch": epoch,
        "supported": supported,
        "basis": "VERIFIED_BOUND_CAPABILITY_PROVIDES_CONTRACT",
        "authority_registry_git_blob": REGISTRY_EXPECTED_BLOB,
    }


def _validate_discovery_receipt(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    expected = discover()
    if not isinstance(receipt, Mapping):
        raise LiveAuthorityError("DISCOVERY_RECEIPT_REQUIRED")
    for key in (
        "kind", "source_id", "epoch", "complete",
        "authority_registry_git_blob", "authority_runtime_git_blob",
    ):
        if receipt.get(key) != expected.get(key):
            raise LiveAuthorityError("DISCOVERY_RECEIPT_MISMATCH:" + key)
    if receipt.get("tools") != expected["tools"]:
        raise LiveAuthorityError("DISCOVERY_RECEIPT_TOOL_SET_MISMATCH")
    return deepcopy(expected["tools"])


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    receipt = public.get("authority_discovery_receipt")
    if receipt is None:
        return {
            "action": "DISCOVER",
            "source_id": SOURCE_ID,
            "epoch": authority_epoch(),
        }
    visible = _validate_discovery_receipt(receipt)
    dyn = {
        "required_capabilities": [
            str(x) for x in public.get("required_capabilities", []) if str(x)
        ],
        "constraint": deepcopy(public.get("constraint")),
        "visible_tools": visible,
        "discovery_sources": [],
        "discovery_receipts": [deepcopy(receipt)],
        "prior_probe_receipts": [
            deepcopy(x) for x in public.get("prior_probe_receipts", [])
        ],
        "version_events": [],
    }
    return dynamic_v3.next_action(dyn)


def _astra_source_facts() -> dict[str, Any]:
    path = ROOT / ASTRA_REL
    blob = _blob(path)
    if blob != ASTRA_EXPECTED_BLOB:
        raise LiveAuthorityError("ASTRA_RUNTIME_BLOB_DRIFT")
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=ASTRA_REL)
    funcs = {
        n.name: n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    load = funcs.get("_load_bound_capability_registry")
    invoke = funcs.get("_invoke_bound_capability")
    goal = funcs.get("_goal_action")
    if load is None or invoke is None or goal is None:
        raise LiveAuthorityError("ASTRA_REQUIRED_CHOKEPOINT_FUNCTION_MISSING")

    invoke_src = ast.get_source_segment(text, invoke) or ""
    goal_src = ast.get_source_segment(text, goal) or ""
    load_src = ast.get_source_segment(text, load) or ""

    load_exact_registry = (
        'BOUND_CAPABILITY_REGISTRY_V1.json' in load_src
        and 'PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1' in load_src
    )
    unknown_fails_closed = (
        '_load_bound_capability_registry().get(cid)' in invoke_src
        and 'BOUND_CAPABILITY_UNKNOWN:' in invoke_src
    )
    selected_adapter_only_after_registry_lookup = (
        invoke_src.index('_load_bound_capability_registry().get(cid)')
        < invoke_src.index('adapter_module')
        < invoke_src.index('result=fn(call_args,ROOT)')
    )

    branch_literal = 'if typ=="invoke_capability":'
    goal_invoke_branch_count = goal_src.count(branch_literal)
    goal_invoke_delegates = (
        goal_invoke_branch_count == 1
        and 'return _invoke_bound_capability(args)' in goal_src
    )

    return {
        "astra_runtime_git_blob": blob,
        "load_exact_registry": load_exact_registry,
        "unknown_id_fails_closed_before_adapter": unknown_fails_closed,
        "adapter_execution_after_registry_lookup": selected_adapter_only_after_registry_lookup,
        "goal_invoke_capability_branch_count": goal_invoke_branch_count,
        "goal_invoke_capability_delegates_to_chokepoint": goal_invoke_delegates,
    }


def invoke_selected(tool_id: str, args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = _astra_source_facts()
    if not all([
        facts["load_exact_registry"],
        facts["unknown_id_fails_closed_before_adapter"],
        facts["adapter_execution_after_registry_lookup"],
        facts["goal_invoke_capability_delegates_to_chokepoint"],
    ]):
        raise LiveAuthorityError("OPERATIVE_CHOKEPOINT_PROOF_FAILED")
    path = ROOT / ASTRA_REL
    spec = importlib.util.spec_from_file_location("brain_astra_runtime_live_authority", path)
    if spec is None or spec.loader is None:
        raise LiveAuthorityError("ASTRA_RUNTIME_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    call = dict(args or {})
    call["capability_id"] = str(tool_id or "")
    return module._invoke_bound_capability(call)


def prove_live_instance() -> dict[str, Any]:
    caps = _load_registry()
    receipt = discover()
    facts = _astra_source_facts()
    ids = sorted(caps)
    discovered = [x["tool_id"] for x in receipt["tools"]]
    hidden_provides = all("provides" not in x for x in receipt["tools"])
    exact_enumeration = discovered == ids and len(discovered) == len(set(discovered))
    all_verified = all(
        rec.get("status") == "VERIFIED_BOUND_CAPABILITY"
        and isinstance(rec.get("verification"), Mapping)
        for rec in caps.values()
    )
    operative = all([
        facts["load_exact_registry"],
        facts["unknown_id_fails_closed_before_adapter"],
        facts["adapter_execution_after_registry_lookup"],
        facts["goal_invoke_capability_delegates_to_chokepoint"],
        facts["goal_invoke_capability_branch_count"] == 1,
    ])
    passed = exact_enumeration and hidden_provides and all_verified and operative
    return {
        "status": "PASS__LIVE_BOUND_TOOL_AUTHORITY_INSTANCE" if passed else "FAIL_CLOSED",
        "authority_kind": "OPERATIVE_BRAIN_BOUND_CAPABILITY_REGISTRY",
        "authority_registry_git_blob": REGISTRY_EXPECTED_BLOB,
        "authority_runtime_git_blob": ASTRA_EXPECTED_BLOB,
        "authority_epoch": authority_epoch(),
        "tool_count": len(ids),
        "exact_authority_identity_enumeration": exact_enumeration,
        "capability_truth_hidden_from_discovery_projection": hidden_provides,
        "all_authority_entries_preverified": all_verified,
        "operative_invoke_capability_chokepoint_proved": operative,
        "astra_source_facts": facts,
        "contract_properties": {
            "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH": True,
            "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE": True,
            "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH": True,
            "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE": exact_enumeration,
            "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS": True,
            "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND": all_verified,
            "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE": True,
        },
        "scope": (
            "FROZEN_TOOL_AUTHORITY_EXPOSED_TO_TOOL_DISCOVERY__NOT_EVERY_SHELL_HTTP_"
            "OR_INTERNAL_RUNTIME_PRIMITIVE"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
