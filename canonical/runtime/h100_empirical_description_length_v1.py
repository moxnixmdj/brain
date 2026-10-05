"""Empirical incremental description-length and verifier-cost measurement for H100.

The encoding convention and cohort are frozen in
H100_EMPIRICAL_DESCRIPTION_LENGTH_PRECOMMIT_V1.json before measurement.

This module does NOT use source-file byte size as program length. It uses the
frozen canonical prefix-tree DSL and the frozen compiled-reference encoding.
"""
from __future__ import annotations

import json
import math
import statistics
import struct
import time
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_zero_learned_parametric_unary_v1 as param
from canonical.runtime import h100_zero_learned_transfer_v1 as transfer

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_EMPIRICAL_DESCRIPTION_LENGTH_PRECOMMIT_V1.json"
TRANSFER_PRE=ROOT/"canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json"
SCHEMA="PROJECT_BRAIN_H100_EMPIRICAL_DESCRIPTION_LENGTH_RESULT_V1"

OP_BITS=5
MODE_BITS=1
LIBRARY_SELECTOR_BITS=5
THRESHOLD=1e-7
WIDTHS=(16,32,64)

PARAMS={
    "linear_trend_sinusoid":("intercept","linear","sin_coefficient","cos_coefficient","omega"),
    "exp_abs":("scale","rate"),
    "threshold_step":("intercept","amplitude","threshold"),
}

# Frozen raw DSL structures from the precommit.
# Each tuple is (opcode_count, constant_payload_count).
RAW_LAYOUT={
    "linear_trend_sinusoid":(19,6),  # omega occurs in both sin and cos subtrees
    "exp_abs":(7,2),
    "threshold_step":(7,3),
}


class DescriptionLengthError(ValueError):
    pass


def _quantize(value: float, width: int) -> float:
    if width==16:
        fmt="<e"
    elif width==32:
        fmt="<f"
    elif width==64:
        fmt="<d"
    else:
        raise DescriptionLengthError("WIDTH_INVALID")
    try:
        return float(struct.unpack(fmt,struct.pack(fmt,float(value)))[0])
    except (OverflowError,struct.error) as exc:
        raise DescriptionLengthError("FLOAT_QUANTIZATION_FAILED") from exc


def quantized_candidate(candidate: Mapping[str,Any], width: int) -> dict[str,Any]:
    family=str(candidate.get("family") or "")
    names=PARAMS.get(family)
    if names is None:
        raise DescriptionLengthError("FAMILY_UNSUPPORTED")
    out={"family":family,"input_name":"x"}
    for name in names:
        if name not in candidate:
            raise DescriptionLengthError("PARAMETER_MISSING:"+name)
        out[name]=_quantize(float(candidate[name]),width)
    return out


def raw_program_bits(family: str, width: int) -> int:
    if family not in RAW_LAYOUT:
        raise DescriptionLengthError("FAMILY_UNSUPPORTED")
    opcodes,consts=RAW_LAYOUT[family]
    return opcodes*OP_BITS + consts*width


def compiled_reference_bits(family: str, width: int) -> int:
    names=PARAMS.get(family)
    if names is None:
        raise DescriptionLengthError("FAMILY_UNSUPPORTED")
    return MODE_BITS + LIBRARY_SELECTOR_BITS + len(names)*width


def _family_rows(task_id: str, transfer_pre: Mapping[str,Any]):
    train=transfer._rows(task_id,[float(x) for x in transfer_pre["training_x"]])
    hold=transfer._rows(task_id,[float(x) for x in transfer_pre["holdout_x"]])
    return train,hold


def _score(candidate: Mapping[str,Any], hold: list[dict[str,float]]) -> float:
    pred=[param.predict(candidate,row) for row in hold]
    return transfer._nrmse([r["y"] for r in hold],pred)


def _discover(train: list[dict[str,float]], expected_family: str) -> dict[str,Any]:
    out=param.discover(train,target="y",input_name="x",exact_nrmse=1e-8)
    c=out.get("best_candidate")
    if not isinstance(c,Mapping) or c.get("family")!=expected_family:
        raise DescriptionLengthError("EXPECTED_FAMILY_NOT_DISCOVERED:"+expected_family)
    return dict(c)


def _median_timing(fn, repetitions: int=7) -> float:
    fn()  # uncounted warmup
    values=[]
    for _ in range(repetitions):
        start=time.perf_counter()
        fn()
        values.append(time.perf_counter()-start)
    return float(statistics.median(values))


def measure_family(task_id: str, expected_family: str, transfer_pre: Mapping[str,Any]) -> dict[str,Any]:
    train,hold=_family_rows(task_id,transfer_pre)

    base=_discover(train,expected_family)
    selected=None
    for width in WIDTHS:
        try:
            q=quantized_candidate(base,width)
            err=_score(q,hold)
        except (DescriptionLengthError,param.ParametricUnaryError,OverflowError,ValueError):
            continue
        if math.isfinite(err) and err<=THRESHOLD:
            selected=(width,q,err)
            break
    if selected is None:
        raise DescriptionLengthError("NO_FROZEN_PRECISION_RUNG_PRESERVES_UTILITY:"+expected_family)
    width,qcandidate,err=selected

    def discover_once():
        _discover(train,expected_family)

    descriptor=tuple(float(qcandidate[name]) for name in PARAMS[expected_family])
    def verify_once():
        # Reconstruct from the frozen descriptor representation, then score all holdout rows.
        c={"family":expected_family,"input_name":"x"}
        for name,value in zip(PARAMS[expected_family],descriptor):
            c[name]=value
        e=_score(c,hold)
        if not math.isfinite(e) or e>THRESHOLD:
            raise DescriptionLengthError("VERIFIER_REJECTED_DESCRIPTOR")
        return e

    discovery_s=_median_timing(discover_once)
    verification_s=_median_timing(verify_once)

    raw_bits=raw_program_bits(expected_family,width)
    compiled_bits=compiled_reference_bits(expected_family,width)
    delta=raw_bits-compiled_bits
    if delta<0:
        raise DescriptionLengthError("COMPILED_REFERENCE_LONGER_THAN_RAW")
    return {
        "task_id":task_id,
        "family":expected_family,
        "selected_float_precision_bits":width,
        "parameter_count":len(PARAMS[expected_family]),
        "holdout_nrmse":err,
        "raw_program_bits":raw_bits,
        "compiled_reference_bits":compiled_bits,
        "description_bit_reduction":delta,
        "generic_dovetail_bound_ratio_raw_over_compiled":"2^"+str(delta),
        "generic_dovetail_bound_ratio_log2":delta,
        "discovery_median_seconds":discovery_s,
        "verification_median_seconds":verification_s,
        "verification_holdout_rows":len(hold),
        "persistent_learned_bytes":0,
    }


def run() -> dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if pre.get("status")!="FROZEN_BEFORE_DESCRIPTION_LENGTH_AND_TIMING_OUTCOMES__RETROSPECTIVE_ON_ALREADY_VERIFIED_CAPABILITY_FAMILIES__ZERO_CREDIT":
        raise DescriptionLengthError("MEASUREMENT_PRECOMMIT_NOT_FROZEN")
    transfer_pre=json.loads(TRANSFER_PRE.read_text())
    family_rows=[]
    for family in transfer_pre["families"]:
        family_rows.append(measure_family(
            str(family["transfer_task"]["task_id"]),
            str(family["compiled_family"]),
            transfer_pre,
        ))
    deltas=[r["description_bit_reduction"] for r in family_rows]
    verifier=[r["verification_median_seconds"] for r in family_rows]
    discovery=[r["discovery_median_seconds"] for r in family_rows]
    compiled=[r["compiled_reference_bits"] for r in family_rows]
    return {
        "schema":SCHEMA,
        "status":"EMPIRICAL_REAL_REUSABLE_CAPABILITY_L_AND_T_MEASURED__THREE_FAMILIES__ZERO_CREDIT",
        "family_count":len(family_rows),
        "families":family_rows,
        "summary":{
            "compiled_reference_bits_min":min(compiled),
            "compiled_reference_bits_median":statistics.median(compiled),
            "compiled_reference_bits_max":max(compiled),
            "description_bit_reduction_min":min(deltas),
            "description_bit_reduction_median":statistics.median(deltas),
            "description_bit_reduction_max":max(deltas),
            "verification_median_seconds_across_families":statistics.median(verifier),
            "discovery_median_seconds_across_families":statistics.median(discovery),
        },
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "THREE_SYNTHETIC_BUT_INDEPENDENTLY_VERIFIED_REUSABLE_FAMILIES_DO_NOT_DEFINE_A_GENERAL_REAL_WORLD_DISTRIBUTION",
            "CANONICAL_DSL_LENGTH_IS_NOT_KOLMOGOROV_COMPLEXITY",
            "2^DELTA_IS_A_GENERIC_SEARCH_BOUND_RATIO_NOT_A_MEASURED_WALL_CLOCK_SPEEDUP",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
