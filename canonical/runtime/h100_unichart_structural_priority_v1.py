"""Structural-priority UniChart H100 packer.

This candidate is frozen after the coarse/error-first candidates failed on the
public development slice, but before this candidate is evaluated. It does not
use prompts, labels, benchmark predictions, or benchmark correctness.

Policy:
- start from source-only W3/W4 reconstruction-error ranking,
- FORCE W4 for structurally sensitive storages:
  * tied token embedding / LM head,
  * decoder positional embeddings,
  * relative-position bias tables,
  * LayerNorm/norm parameters,
  * 1-D tensors and biases,
  * encoder embedding stem tensors,
- allocate the remaining W4 budget by source-only SSE(W3)-SSE(W4),
- keep I64 lossless,
- keep the complete counted bundle <=100,000,000 bytes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from canonical.runtime.h100_unichart_chartqa_bin_packer_v1 import (
    parse_checkpoint_metadata,
)
from canonical.runtime.h100_unichart_error_first_knapsack_v1 import (
    _bitmap_get,
    _layout,
    _pack_group,
    score_source_groups,
)
from canonical.runtime.h100_unichart_lowbit_packer_v1 import (
    GROUP_SIZE,
    H100_BUDGET_BYTES,
    MAGIC,
    PackerError,
    _sha256,
)

SCHEMA="PROJECT_BRAIN_H100_UNICHART_STRUCTURAL_PRIORITY_RESULT_V1"
PACKED_SCHEMA="PROJECT_BRAIN_H100_UNICHART_ERROR_FIRST_PACKED_CHECKPOINT_V1"


def _shape_by_name(parsed: dict[str,Any]) -> dict[str,list[int]]:
    return {row["name"]:list(row["shape"]) for row in parsed["tensor_rows"]}


def structural_class(aliases: list[str], shapes: dict[str,list[int]]) -> str | None:
    lower=[a.lower() for a in aliases]
    if any("decoder.lm_head.weight" in x or "decoder.model.decoder.embed_tokens.weight" in x for x in lower):
        return "TOKEN_EMBEDDING_LM_HEAD"
    if any("embed_positions.weight" in x for x in lower):
        return "POSITIONAL_EMBEDDING"
    if any("relative_position_bias_table" in x for x in lower):
        return "RELATIVE_POSITION_BIAS"
    if any(
        ("layernorm" in x) or ("layer_norm" in x) or (".norm." in x) or x.endswith(".norm.weight") or x.endswith(".norm.bias")
        for x in lower
    ):
        return "NORM"
    if any(x.endswith(".bias") for x in lower):
        return "BIAS"
    if any(len(shapes.get(a,[])) <= 1 for a in aliases):
        return "ONE_DIMENSIONAL"
    if any(x.startswith("encoder.embeddings.") for x in lower):
        return "ENCODER_EMBEDDING_STEM"
    return None


def forced_group_ids(parsed: dict[str,Any]) -> tuple[set[int],dict[str,int]]:
    shapes=_shape_by_name(parsed)
    forced:set[int]=set()
    counts:dict[str,int]={}
    gidx=0
    for storage in parsed["storages"]:
        if storage["dtype"]!="F32":
            continue
        groups=math.ceil(int(storage["numel"])/GROUP_SIZE)
        cls=structural_class(list(storage["aliases"]),shapes)
        if cls is not None:
            forced.update(range(gidx,gidx+groups))
            counts[cls]=counts.get(cls,0)+groups
        gidx+=groups
    return forced,counts


def choose_structural_priority(
    parsed: dict[str,Any],
    ranked_scores: list[tuple[float,str,int,int]],
    *,
    source_sha256: str,
    ancillary_bytes: int,
) -> tuple[set[int],dict[str,Any],int,dict[str,int]]:
    forced,class_counts=forced_group_ids(parsed)
    optional=[row[3] for row in ranked_scores if row[3] not in forced]
    total_groups=len(ranked_scores)

    def size_for(k:int):
        selected=forced | set(optional[:k])
        manifest,packed_size=_layout(
            parsed,
            selected,
            source_sha256=source_sha256,
            total_f32_groups=total_groups,
        )
        return packed_size+ancillary_bytes,selected,manifest,packed_size

    base_complete,base_selected,base_manifest,base_packed=size_for(0)
    if base_complete>H100_BUDGET_BYTES:
        raise PackerError(
            f"FORCED_STRUCTURAL_SET_EXCEEDS_H100:{base_complete}>{H100_BUDGET_BYTES}"
        )

    lo,hi=0,len(optional)
    best=(base_selected,base_manifest,base_packed,base_complete,0)
    while lo<=hi:
        mid=(lo+hi)//2
        complete,selected,manifest,packed=size_for(mid)
        if complete<=H100_BUDGET_BYTES:
            best=(selected,manifest,packed,complete,mid)
            lo=mid+1
        else:
            hi=mid-1

    selected,manifest,packed,complete,k=best
    manifest["selection_policy"]="STRUCTURAL_FORCED_W4_THEN_SOURCE_ONLY_DESC_SSE3_MINUS_SSE4"
    manifest["structural_forced_group_count"]=len(forced)
    manifest["structural_forced_class_counts"]=class_counts
    manifest["optional_error_ranked_w4_group_count"]=k
    manifest["precision_bitmap_b64"]=base64.b64encode(
        bytes(_bitmap_bytes(total_groups,selected))
    ).decode("ascii")
    # Recompute exact manifest/layout because manifest content length changed.
    # The byte payload layout is unchanged; the counted manifest is re-bound below.
    return selected,manifest,complete,class_counts


def _bitmap_bytes(total:int,selected:set[int]) -> bytearray:
    out=bytearray((total+7)//8)
    for idx in selected:
        out[idx//8] |= 1 << (idx%8)
    return out


def _build_manifest_and_size(
    parsed: dict[str,Any],
    selected:set[int],
    *,
    source_sha256:str,
    ancillary_bytes:int,
    class_counts:dict[str,int],
    optional_count:int,
) -> tuple[dict[str,Any],int]:
    total_groups=sum(
        math.ceil(int(s["numel"])/GROUP_SIZE)
        for s in parsed["storages"] if s["dtype"]=="F32"
    )
    manifest,packed=_layout(
        parsed,selected,source_sha256=source_sha256,total_f32_groups=total_groups
    )
    manifest["selection_policy"]="STRUCTURAL_FORCED_W4_THEN_SOURCE_ONLY_DESC_SSE3_MINUS_SSE4"
    manifest["structural_forced_group_count"]=sum(class_counts.values())
    manifest["structural_forced_class_counts"]=class_counts
    manifest["optional_error_ranked_w4_group_count"]=optional_count
    manifest["precision_bitmap_b64"]=base64.b64encode(
        bytes(_bitmap_bytes(total_groups,selected))
    ).decode("ascii")
    manifest_bytes=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode("utf-8")
    # _layout's returned size included its old manifest. Derive payload end directly.
    payload_end=max(int(s["data_end"]) for s in manifest["storages"])
    packed_size=payload_end+len(manifest_bytes)
    return manifest,packed_size+ancillary_bytes


def build_structural_priority_checkpoint(
    source:Path,
    output:Path,
    *,
    expected_source_sha256:str,
    ancillary_bytes:int,
) -> dict[str,Any]:
    source=Path(source); output=Path(output)
    source_sha=_sha256(source)
    if source_sha!=expected_source_sha256:
        raise PackerError(f"SOURCE_SHA256_MISMATCH:{source_sha}!={expected_source_sha256}")
    parsed=parse_checkpoint_metadata(source)
    ranked,total_sse3,total_sse4,total_groups=score_source_groups(source,parsed)
    forced,class_counts=forced_group_ids(parsed)
    optional=[row[3] for row in ranked if row[3] not in forced]

    # Because adding one W4 group can alter counted bytes by remainder length,
    # solve by exact manifest-aware binary search.
    lo,hi=0,len(optional)
    best=None
    while lo<=hi:
        mid=(lo+hi)//2
        selected=forced | set(optional[:mid])
        manifest,complete=_build_manifest_and_size(
            parsed,selected,source_sha256=source_sha,
            ancillary_bytes=ancillary_bytes,class_counts=class_counts,
            optional_count=mid,
        )
        if complete<=H100_BUDGET_BYTES:
            best=(selected,manifest,complete,mid)
            lo=mid+1
        else:
            hi=mid-1
    if best is None:
        raise PackerError("STRUCTURAL_FORCED_SET_EXCEEDS_H100")
    selected,manifest,projected_complete,optional_count=best
    precision=base64.b64decode(manifest["precision_bitmap_b64"])

    manifest_storages={s["key"]:s for s in manifest["storages"]}
    with zipfile.ZipFile(source,"r") as z, output.open("wb+") as out:
        out.write(MAGIC); out.write(struct.pack("<Q",0))
        global_idx=0
        for storage in parsed["storages"]:
            expected=manifest_storages[storage["key"]]
            if out.tell()!=int(expected["data_start"]):
                raise PackerError("STRUCTURAL_LAYOUT_START_MISMATCH")
            with z.open(storage["entry"],"r") as src:
                if storage["dtype"]=="I64":
                    remaining=int(storage["bytes"])
                    while remaining:
                        chunk=src.read(min(1<<20,remaining))
                        if not chunk: raise PackerError("STRUCTURAL_I64_TRUNCATED")
                        out.write(chunk); remaining-=len(chunk)
                    if src.read(1): raise PackerError("STRUCTURAL_I64_TRAILING_BYTES")
                else:
                    remaining=int(storage["numel"])
                    while remaining:
                        n=min(GROUP_SIZE,remaining)
                        raw=src.read(n*4)
                        if len(raw)!=n*4: raise PackerError("STRUCTURAL_F32_TRUNCATED")
                        vals=np.frombuffer(raw,dtype="<f4")
                        bits=4 if _bitmap_get(precision,global_idx) else 3
                        out.write(_pack_group(vals,bits))
                        global_idx+=1; remaining-=n
                    if src.read(1): raise PackerError("STRUCTURAL_F32_TRAILING_BYTES")
            if out.tell()!=int(expected["data_end"]):
                raise PackerError("STRUCTURAL_LAYOUT_END_MISMATCH")

        manifest_bytes=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode("utf-8")
        manifest_offset=out.tell(); out.write(manifest_bytes); final_size=out.tell()
        out.seek(len(MAGIC)); out.write(struct.pack("<Q",len(manifest_bytes))); out.flush()

    complete=final_size+ancillary_bytes
    if complete>H100_BUDGET_BYTES:
        output.unlink(missing_ok=True)
        raise PackerError(f"COMPLETE_BUNDLE_EXCEEDS_H100:{complete}>{H100_BUDGET_BYTES}")
    if complete!=projected_complete:
        raise PackerError(f"PROJECTED_ACTUAL_SIZE_MISMATCH:{projected_complete}!={complete}")

    selected_benefit=sum(row[0] for row in ranked if row[3] in selected)
    return {
        "schema":SCHEMA,
        "status":"STRUCTURAL_PRIORITY_PACKED__PUBLIC_DEV_EVALUATION_PENDING__ZERO_H100_CREDIT",
        "source_sha256":source_sha,
        "output_sha256":_sha256(output),
        "output_bytes":final_size,
        "ancillary_bytes":ancillary_bytes,
        "complete_bundle_bytes":complete,
        "margin_bytes":H100_BUDGET_BYTES-complete,
        "total_f32_groups":total_groups,
        "selected_w4_groups":len(selected),
        "selected_w3_groups":total_groups-len(selected),
        "structural_forced_group_count":len(forced),
        "structural_forced_class_counts":class_counts,
        "optional_error_ranked_w4_group_count":optional_count,
        "precision_bitmap_sha256":hashlib.sha256(precision).hexdigest(),
        "aggregate_source_sse_all_w3":total_sse3,
        "aggregate_source_sse_all_w4":total_sse4,
        "aggregate_selected_sse_reduction_vs_all_w3":selected_benefit,
        "hard_nonclaims":[
            "PUBLIC_20_CASE_SLICE_IS_NOW_DEVELOPMENT_DATA_AFTER_PRIOR_CANDIDATE_OUTCOMES",
            "NO_FINAL_PRESERVATION_CLAIM_MAY_USE_THE_SAME_20_CASE_SLICE",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_FULL_H100_TERMINAL_CREDIT",
        ],
        "h100_credit_delta":0,
    }


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--expected-source-sha256",required=True)
    ap.add_argument("--ancillary-bytes",required=True,type=int)
    ap.add_argument("--result-json")
    args=ap.parse_args()
    result=build_structural_priority_checkpoint(
        Path(args.source),Path(args.output),
        expected_source_sha256=args.expected_source_sha256,
        ancillary_bytes=args.ancillary_bytes,
    )
    rendered=json.dumps(result,indent=2,sort_keys=True)
    if args.result_json:
        Path(args.result_json).write_text(rendered+"\n")
    print(rendered)


if __name__=="__main__":
    main()
