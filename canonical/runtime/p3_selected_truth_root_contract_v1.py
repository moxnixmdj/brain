"""Strict root-task binding for the selected raw defined-term semantic fragment.

The upstream root task bytes are an explicit trust root. This module does NOT prove
that those bytes equal the user's true intent. It proves that the policy source,
fact source, and stable predicate identity consumed downstream are recomputed
losslessly from those exact root bytes with no caller-injected semantic fields.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context
from canonical.runtime.selected_semantic_predicate_identity_v1 import compile_identity

SCHEMA = "PROJECT_BRAIN_P3_SELECTED_TRUTH_ROOT_CONTRACT_V1"
CONTRACT = "P3_SELECTED_RAW_DEFINED_TERM_ROOT_V1"
TOP_KEYS = {"contract", "policy_source", "fact_source"}
SOURCE_KEYS = {"source_id", "text"}
FACT_KEYS = {"source_id", "raw_json"}


class RootContractError(ValueError):
    pass


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise RootContractError("DUPLICATE_JSON_KEY:" + str(key))
        out[key] = value
    return out


def _sha_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _exact(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise RootContractError(label + "_KEYS_INVALID")
    return value


def compile_root_task(raw_task: str | bytes) -> dict[str, Any]:
    try:
        raw = raw_task.encode("utf-8") if isinstance(raw_task, str) else raw_task
        if not isinstance(raw, bytes) or not raw:
            raise RootContractError("ROOT_TASK_BYTES_REQUIRED")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RootContractError("ROOT_TASK_NOT_UTF8") from exc
        try:
            doc = json.loads(text, object_pairs_hook=_pairs)
        except RootContractError:
            raise
        except Exception as exc:
            raise RootContractError("ROOT_TASK_JSON_INVALID") from exc

        doc = _exact(doc, TOP_KEYS, "TOP")
        if doc.get("contract") != CONTRACT:
            raise RootContractError("CONTRACT_KIND_INVALID")
        policy = _exact(doc.get("policy_source"), SOURCE_KEYS, "POLICY_SOURCE")
        facts = _exact(doc.get("fact_source"), FACT_KEYS, "FACT_SOURCE")

        source_id = policy.get("source_id")
        source_text = policy.get("text")
        fact_source_id = facts.get("source_id")
        fact_source = facts.get("raw_json")
        if not isinstance(source_id, str) or not source_id.strip():
            raise RootContractError("POLICY_SOURCE_ID_REQUIRED")
        if not isinstance(source_text, str) or not source_text:
            raise RootContractError("POLICY_SOURCE_TEXT_REQUIRED")
        if not isinstance(fact_source_id, str) or not fact_source_id.strip():
            raise RootContractError("FACT_SOURCE_ID_REQUIRED")
        if not isinstance(fact_source, str) or not fact_source:
            raise RootContractError("FACT_SOURCE_RAW_JSON_REQUIRED")

        identity = compile_identity(source_text, source_id=source_id)
        if identity.get("pass") is not True:
            raise RootContractError("POLICY_PREDICATE_IDENTITY_NOT_COMPILED")

        typed = compile_typed_context(fact_source, source_id=fact_source_id)
        if typed.get("status") != "COMPILED":
            raise RootContractError("FACT_SOURCE_TYPED_CONTEXT_NOT_COMPILED")

        root_sha = _sha_bytes(raw)
        source_sha = sha256(source_text.encode("utf-8")).hexdigest()
        fact_sha = sha256(fact_source.encode("utf-8")).hexdigest()
        truth_input = {
            "target_claim_id": "selected",
            "source_text": source_text,
            "source_id": source_id,
            "claims": [{
                "claim_id": "selected",
                "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            }],
            "fact_source": fact_source,
            "fact_source_id": fact_source_id,
        }
        receipt_material = json.dumps({
            "root_task_sha256": root_sha,
            "policy_source_sha256": source_sha,
            "fact_source_sha256": fact_sha,
            "predicate_id": identity["predicate_id"],
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__ROOT_TASK_SOURCES_LOSSLESSLY_BOUND",
            "root_task_sha256": root_sha,
            "policy_source_sha256": source_sha,
            "fact_source_sha256": fact_sha,
            "predicate_id": identity["predicate_id"],
            "truth_input": truth_input,
            "root_binding_receipt_sha256": sha256(receipt_material).hexdigest(),
            "root_task_source_binding_verified": True,
            "source_authorization_verified_relative_to_root_task": True,
            "root_task_authority_self_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "UPSTREAM_ROOT_TASK_BYTES_ARE_THE_UNAVOIDABLE_TRUST_ROOT__"
                "THIS_COMPILER_PROVES_ONLY_EXACT_DOWNSTREAM_SOURCE_BINDING__"
                "IT_DOES_NOT_PROVE_THE_ROOT_BYTES_EQUAL_USER_INTENT"
            ),
        }
    except RootContractError as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "root_task_source_binding_verified": False,
            "source_authorization_verified_relative_to_root_task": False,
            "root_task_authority_self_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
