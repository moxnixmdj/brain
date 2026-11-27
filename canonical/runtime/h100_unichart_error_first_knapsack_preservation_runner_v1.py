from __future__ import annotations

import argparse
import base64
import gc
import json
import math
import struct
from pathlib import Path
from typing import Any

import numpy as np
import torch

from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import (
    EXPECTED_SOURCE_SHA256,
    H100_BUDGET_BYTES,
    PreservationError,
    _copy_aliases,
    _decode_full_group_block,
    _decode_remainder,
    answer_case,
    evaluate_subject,
    load_fp32_donor,
    make_model_and_processor,
)
from canonical.runtime.h100_unichart_lowbit_packer_v1 import MAGIC

PACKED_SCHEMA="PROJECT_BRAIN_H100_UNICHART_ERROR_FIRST_PACKED_CHECKPOINT_V1"


def read_knapsack_manifest(path: Path) -> tuple[dict[str,Any],bytes]:
    path=Path(path)
    size=path.stat().st_size
    with path.open("rb") as f:
        if f.read(len(MAGIC))!=MAGIC:
            raise PreservationError("KNAPSACK_MAGIC_MISMATCH")
        raw=f.read(8)
        if len(raw)!=8:
            raise PreservationError("KNAPSACK_MANIFEST_LENGTH_TRUNCATED")
        mlen=struct.unpack("<Q",raw)[0]
        if mlen<=0 or mlen>=size:
            raise PreservationError("KNAPSACK_MANIFEST_LENGTH_INVALID")
        f.seek(size-mlen)
        manifest=json.loads(f.read(mlen).decode("utf-8"))
    if manifest.get("schema")!=PACKED_SCHEMA:
        raise PreservationError("KNAPSACK_SCHEMA_MISMATCH")
    if manifest.get("source_sha256")!=EXPECTED_SOURCE_SHA256:
        raise PreservationError("KNAPSACK_SOURCE_LINEAGE_MISMATCH")
    try:
        bitmap=base64.b64decode(manifest["precision_bitmap_b64"],validate=True)
    except Exception as exc:
        raise PreservationError("KNAPSACK_PRECISION_BITMAP_INVALID") from exc
    need=math.ceil(int(manifest["total_f32_groups"])/8)
    if len(bitmap)!=need:
        raise PreservationError("KNAPSACK_PRECISION_BITMAP_LENGTH_MISMATCH")
    return manifest,bitmap


def _bit(bitmap: bytes, idx: int) -> int:
    return 4 if (bitmap[idx//8] & (1<<(idx%8))) else 3


def _load_full_groups_vectorized(
    mm: np.memmap,
    target: torch.Tensor,
    *,
    full_groups: int,
    group_start: int,
    data_start: int,
    bitmap: bytes,
) -> int:
    if full_groups==0:
        return data_start
    offsets=np.empty(full_groups,dtype=np.int64)
    bits_arr=np.empty(full_groups,dtype=np.uint8)
    pos=data_start
    for g in range(full_groups):
        bits=_bit(bitmap,group_start+g)
        bits_arr[g]=bits
        offsets[g]=pos
        pos += 4 + (96 if bits==3 else 128)

    rows=target[:full_groups*256].view(full_groups,256)
    for bits,row_bytes in ((3,100),(4,132)):
        group_ids=np.nonzero(bits_arr==bits)[0]
        for start in range(0,len(group_ids),2048):
            ids=group_ids[start:start+2048]
            offs=offsets[ids]
            gather=offs[:,None] + np.arange(row_bytes,dtype=np.int64)[None,:]
            block=np.asarray(mm[gather],dtype=np.uint8)
            vals,_=_decode_full_group_block(block,bits)
            tid=torch.from_numpy(ids.astype(np.int64))
            rows[tid]=torch.from_numpy(vals).to(dtype=rows.dtype)
    return pos


def load_knapsack_donor(model, packed_path: Path) -> dict[str,Any]:
    manifest,bitmap=read_knapsack_manifest(packed_path)
    state=model.state_dict()
    alias_rows={x["name"]:x for x in manifest["tensor_aliases"]}
    if set(alias_rows)!=set(state):
        raise PreservationError(
            f"KNAPSACK_STATE_KEY_MISMATCH:missing={sorted(set(state)-set(alias_rows))[:3]}:"
            f"extra={sorted(set(alias_rows)-set(state))[:3]}"
        )
    mm=np.memmap(packed_path,dtype=np.uint8,mode="r")
    counted_w4=0
    counted_groups=0
    with torch.no_grad():
        for storage in manifest["storages"]:
            aliases=storage["aliases"]
            first=aliases[0]
            target=state[first].reshape(-1)
            numel=int(storage["numel"])
            start=int(storage["data_start"])
            end=int(storage["data_end"])
            if target.numel()!=numel:
                raise PreservationError(f"KNAPSACK_TARGET_NUMEL_MISMATCH:{first}")
            if storage["dtype"]=="I64":
                arr=np.frombuffer(
                    np.ascontiguousarray(mm[start:end]).tobytes(),dtype="<i8"
                ).copy()
                _copy_aliases(state,aliases,torch.from_numpy(arr))
                continue

            group_start=int(storage["group_start"])
            full,rem=divmod(numel,256)
            pos=_load_full_groups_vectorized(
                mm,target,
                full_groups=full,
                group_start=group_start,
                data_start=start,
                bitmap=bitmap,
            )
            for g in range(full):
                counted_w4 += int(_bit(bitmap,group_start+g)==4)
            counted_groups += full
            if rem:
                bits=_bit(bitmap,group_start+full)
                rbytes=4+math.ceil(rem*bits/8)
                vals=_decode_remainder(np.asarray(mm[pos:pos+rbytes]),rem,bits)
                target[full*256:].copy_(torch.from_numpy(vals).to(dtype=target.dtype))
                counted_w4 += int(bits==4)
                counted_groups += 1
                pos += rbytes
            if pos!=end:
                raise PreservationError(
                    f"KNAPSACK_STORAGE_BOUNDARY_MISMATCH:{first}:{pos}!={end}"
                )
            for alias in aliases[1:]:
                other=state[alias].reshape(-1)
                if other.data_ptr()!=target.data_ptr():
                    other.copy_(target)
    if counted_groups!=int(manifest["total_f32_groups"]):
        raise PreservationError("KNAPSACK_GROUP_COUNT_MISMATCH")
    if counted_w4!=int(manifest["selected_w4_groups"]):
        raise PreservationError("KNAPSACK_W4_COUNT_MISMATCH")
    return {
        "tensor_count":manifest["tensor_count"],
        "storage_count":manifest["storage_count"],
        "packed_bytes":Path(packed_path).stat().st_size,
        "total_f32_groups":counted_groups,
        "selected_w4_groups":counted_w4,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preexposure",required=True)
    ap.add_argument("--image-dir",required=True)
    ap.add_argument("--fp32-source",required=True)
    ap.add_argument("--packed-source",required=True)
    ap.add_argument("--runtime-assets",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--max-cases",type=int)
    args=ap.parse_args()

    pre=json.load(open(args.preexposure))
    assets=json.load(open(args.runtime_assets))
    cases=pre["population"]["cases"]
    if args.max_cases is not None:
        cases=cases[:args.max_cases]

    model,processor=make_model_and_processor()
    fp32_load=load_fp32_donor(model,Path(args.fp32_source))
    fp32=evaluate_subject(model,processor,cases,Path(args.image_dir))
    del model
    gc.collect()

    model,processor=make_model_and_processor()
    packed_load=load_knapsack_donor(model,Path(args.packed_source))
    packed=evaluate_subject(model,processor,cases,Path(args.image_dir))

    agreements=sum(
        int(a["prediction"]==b["prediction"])
        for a,b in zip(fp32["rows"],packed["rows"])
    )
    agreement=agreements/len(cases)
    bundle_bytes=Path(args.packed_source).stat().st_size + int(assets["ancillary_total_bytes"])
    byte_pass=bundle_bytes<=H100_BUDGET_BYTES

    full_population=(args.max_cases is None and len(cases)==20)
    gate=pre["pass_gate"]
    capability_pass=(
        full_population
        and fp32["accuracy"] >= float(gate["minimum_fp32_relaxed_accuracy"])
        and packed["accuracy"] >= fp32["accuracy"] - float(gate["packed_noninferiority_margin_absolute"])
        and agreement >= float(gate["packed_vs_fp32_answer_agreement_minimum"])
    )
    passed=bool(byte_pass and capability_pass)

    out={
        "schema":"PROJECT_BRAIN_H100_UNICHART_ERROR_FIRST_CHARTQA_PRESERVATION_RESULT_V1",
        "status":"PASS__PUBLIC_NONTERMINAL_CAPABILITY_PRESERVATION" if passed else ("SMOKE_RESULT__NO_GATE" if not full_population else "FAIL__PRESERVATION_GATE"),
        "full_population":full_population,
        "case_count":len(cases),
        "fp32":fp32,
        "packed":packed,
        "exact_answer_agreement":agreement,
        "exact_answer_agreements":agreements,
        "bundle_bytes":bundle_bytes,
        "h100_budget_bytes":H100_BUDGET_BYTES,
        "byte_pass":byte_pass,
        "capability_pass":capability_pass,
        "pass":passed,
        "fp32_load":fp32_load,
        "packed_load":packed_load,
        "hard_nonclaims":[
            "PUBLIC_CHARTQA_PRESERVATION_DOES_NOT_PROVE_CHARTOGRAPHY_GE_89",
            "PUBLIC_CHARTQA_PRESERVATION_DOES_NOT_PROVE_FULL_H100_TERMINAL_CAPABILITY"
        ],
        "h100_credit_delta":0,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
    }
    json.dump(out,open(args.output,"w"),indent=2,sort_keys=True)
    print(json.dumps({
        "status":out["status"],
        "fp32_accuracy":fp32["accuracy"],
        "packed_accuracy":packed["accuracy"],
        "agreement":agreement,
        "bundle_bytes":bundle_bytes,
        "byte_pass":byte_pass,
        "capability_pass":capability_pass,
        "pass":passed,
    },indent=2,sort_keys=True))


if __name__=="__main__":
    main()
