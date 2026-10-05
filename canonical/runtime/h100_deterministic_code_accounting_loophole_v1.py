"""Representation-dependence tests for learned-byte-only accounting.

If deterministic capability code is excluded from learned-state accounting, a
finite benchmark can always be memorized by an exact lookup table embedded in
deterministic code. Likewise, a capability-bearing bitstring can be represented
as a counted learned blob or embedded as a deterministic constant while
preserving total persistent information.

This does not change the user-defined H100 metric. It proves that the metric
alone is not representation-invariant and must be interpreted alongside
deterministic capability description size and fresh generalization.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_H100_DETERMINISTIC_CODE_ACCOUNTING_LOOPHOLE_V1"

class AccountingLoopholeError(ValueError):
    pass


def canonical_key(value: Any) -> str:
    try:
        raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    except Exception as exc:
        raise AccountingLoopholeError("INPUT_NOT_CANONICALIZABLE") from exc
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compile_finite_lookup(rows: Sequence[Mapping[str,Any]]) -> dict:
    if isinstance(rows,(str,bytes)) or not isinstance(rows,Sequence) or not rows:
        raise AccountingLoopholeError("ROWS_INVALID")
    table={}
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping) or "input" not in row or "output" not in row:
            raise AccountingLoopholeError(f"ROW_INVALID:{i}")
        key=canonical_key(row["input"])
        if key in table and table[key]!=row["output"]:
            raise AccountingLoopholeError(f"CONFLICTING_OUTPUT:{i}")
        table[key]=row["output"]
    encoded=json.dumps(table,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return {
        "schema":SCHEMA,
        "table":table,
        "deterministic_capability_bytes":len(encoded),
        "persistent_learned_bytes":0,
        "training_rows_embedded":len(rows),
    }


def lookup(program: Mapping[str,Any], value: Any) -> dict:
    table=program.get("table")
    if not isinstance(table,Mapping):
        raise AccountingLoopholeError("PROGRAM_INVALID")
    key=canonical_key(value)
    if key not in table:
        return {"status":"ABSTAIN_UNSEEN_INPUT","output":None}
    return {"status":"EXACT_LOOKUP_HIT","output":table[key]}


def finite_dataset_accuracy(program: Mapping[str,Any], rows: Sequence[Mapping[str,Any]]) -> float:
    if not rows:
        raise AccountingLoopholeError("ROWS_EMPTY")
    correct=0
    for row in rows:
        out=lookup(program,row["input"])
        correct+=int(out["status"]=="EXACT_LOOKUP_HIT" and out["output"]==row["output"])
    return correct/len(rows)


def syntax_only_accounting_same_payload(payload_bytes: int, wrapper_bytes: int=0) -> dict:
    if not isinstance(payload_bytes,int) or isinstance(payload_bytes,bool) or payload_bytes<0:
        raise AccountingLoopholeError("PAYLOAD_BYTES_INVALID")
    if not isinstance(wrapper_bytes,int) or isinstance(wrapper_bytes,bool) or wrapper_bytes<0:
        raise AccountingLoopholeError("WRAPPER_BYTES_INVALID")
    total=payload_bytes+wrapper_bytes
    return {
        "learned_blob_representation":{
            "counted_learned_bytes":payload_bytes,
            "deterministic_wrapper_bytes":wrapper_bytes,
            "total_persistent_bytes":total,
        },
        "embedded_code_representation":{
            "counted_learned_bytes":0,
            "deterministic_capability_bytes":total,
            "total_persistent_bytes":total,
        },
        "total_persistent_information_size_unchanged":True,
        "learned_byte_metric_changed_by_representation":payload_bytes>0,
    }


def certificate(training_rows: Sequence[Mapping[str,Any]], unseen_input: Any) -> dict:
    program=compile_finite_lookup(training_rows)
    acc=finite_dataset_accuracy(program,training_rows)
    unseen=lookup(program,unseen_input)
    return {
        "schema":SCHEMA,
        "status":"DETERMINISTIC_CODE_ACCOUNTING_REPRESENTATION_WARNING",
        "finite_training_accuracy":acc,
        "unseen_status":unseen["status"],
        "persistent_learned_bytes":program["persistent_learned_bytes"],
        "deterministic_capability_bytes":program["deterministic_capability_bytes"],
        "deduction":[
            "PERFECT_FINITE_DATASET_ACCURACY_IS_COMPATIBLE_WITH_ZERO_LEARNED_BYTES_VIA_EXACT_LOOKUP",
            "FRESH_UNSEEN_INPUTS_BLOCK_TRIVIAL_LOOKUP_GENERALIZATION",
            "LEARNED_BYTE_COUNT_ALONE_IS_NOT_REPRESENTATION_INVARIANT_IF_CAPABILITY_BEARING_DETERMINISTIC_CODE_IS_UNCOUNTED",
        ],
        "hard_nonclaims":[
            "DOES_NOT_SHOW_FRESH_HOLDOUT_RESULTS_ARE_LOOKUP",
            "DOES_NOT_SHOW_DETERMINISTIC_ALGORITHMS_SHOULD_BE_RECLASSIFIED_AS_LEARNED",
            "DOES_NOT_CHANGE_H100_ACCOUNTING",
        ],
        "h100_terminal_credit_delta":0,
    }
