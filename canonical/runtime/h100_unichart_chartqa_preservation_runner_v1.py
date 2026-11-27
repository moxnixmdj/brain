from __future__ import annotations

import argparse
import gc
import json
import math
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderConfig, VisionEncoderDecoderModel

from canonical.runtime.h100_unichart_chartqa_bin_packer_v1 import (
    parse_checkpoint_metadata,
)
from canonical.runtime.h100_unichart_lowbit_packer_v1 import MAGIC

MODEL_ID="ahmed-masry/unichart-chartqa-960"
MODEL_REVISION="e5eb1e52c1d775e0f3febaddc7fc3559e80cb989"
EXPECTED_SOURCE_SHA256="4407db60801a20bcf254946acfee6727491ef1739ad7b4d3abbf87b7c75e7229"
PACKED_SCHEMA="PROJECT_BRAIN_H100_UNICHART_CHARTQA_PACKED_CHECKPOINT_V1"
H100_BUDGET_BYTES=100_000_000


class PreservationError(ValueError):
    pass


def relaxed_correct(gold: str, pred: str) -> bool:
    g=gold.strip()
    p=pred.strip()
    def number(x: str):
        x=x.strip().strip("%").strip().replace(",","")
        try:
            return float(x)
        except ValueError:
            return None
    gf=number(g)
    pf=number(p)
    if gf is not None and pf is not None:
        if gf==0.0:
            return pf==0.0
        return abs(pf-gf)/abs(gf) <= 0.05
    return p.lower()==g.lower()


def _copy_aliases(state: dict[str, torch.Tensor], aliases: list[str], flat: torch.Tensor) -> None:
    first=aliases[0]
    target=state[first].reshape(-1)
    if target.numel()!=flat.numel():
        raise PreservationError(f"TARGET_NUMEL_MISMATCH:{first}")
    target.copy_(flat.to(dtype=target.dtype))
    for alias in aliases[1:]:
        other=state[alias].reshape(-1)
        if other.numel()!=target.numel():
            raise PreservationError(f"ALIAS_NUMEL_MISMATCH:{alias}")
        if other.data_ptr()!=target.data_ptr():
            other.copy_(target)


def load_fp32_donor(model: VisionEncoderDecoderModel, source: Path) -> dict[str, Any]:
    parsed=parse_checkpoint_metadata(source)
    state=model.state_dict()
    names={r["name"] for r in parsed["tensor_rows"]}
    if names != set(state):
        raise PreservationError(
            f"FP32_STATE_KEY_MISMATCH:missing={sorted(set(state)-names)[:3]}:"
            f"extra={sorted(names-set(state))[:3]}"
        )
    with torch.no_grad(), zipfile.ZipFile(source,"r") as z:
        for storage in parsed["storages"]:
            raw=z.read(storage["entry"])
            if storage["dtype"]=="F32":
                arr=np.frombuffer(raw,dtype="<f4").copy()
                flat=torch.from_numpy(arr)
            elif storage["dtype"]=="I64":
                arr=np.frombuffer(raw,dtype="<i8").copy()
                flat=torch.from_numpy(arr)
            else:
                raise PreservationError("FP32_DTYPE_UNEXPECTED")
            _copy_aliases(state,storage["aliases"],flat)
    return {
        "tensor_count":parsed["tensor_count"],
        "storage_count":parsed["storage_count"],
        "alias_storage_count":parsed["alias_storage_count"],
    }


def read_packed_manifest(path: Path) -> dict[str, Any]:
    path=Path(path)
    size=path.stat().st_size
    with path.open("rb") as f:
        magic=f.read(len(MAGIC))
        if magic!=MAGIC:
            raise PreservationError("PACKED_MAGIC_MISMATCH")
        raw=f.read(8)
        if len(raw)!=8:
            raise PreservationError("PACKED_MANIFEST_LENGTH_TRUNCATED")
        mlen=struct.unpack("<Q",raw)[0]
        if mlen<=0 or mlen>=size:
            raise PreservationError("PACKED_MANIFEST_LENGTH_INVALID")
        f.seek(size-mlen)
        manifest=json.loads(f.read(mlen).decode("utf-8"))
    if manifest.get("schema")!=PACKED_SCHEMA:
        raise PreservationError("PACKED_SCHEMA_MISMATCH")
    if manifest.get("source_sha256")!=EXPECTED_SOURCE_SHA256:
        raise PreservationError("PACKED_SOURCE_LINEAGE_MISMATCH")
    return manifest


def _decode_full_group_block(raw: np.ndarray, bits: int) -> tuple[np.ndarray,np.ndarray]:
    meta=np.ascontiguousarray(raw[:,:4]).view("<f2").reshape(-1,2).astype(np.float32)
    packed=np.ascontiguousarray(raw[:,4:])
    n=raw.shape[0]
    if bits==4:
        q=np.empty((n,256),dtype=np.uint8)
        q[:,0::2]=packed & 0x0F
        q[:,1::2]=packed >> 4
    elif bits==3:
        b=np.unpackbits(packed,axis=1,bitorder="little").reshape(n,256,3)
        q=(b[:,:,0] + (b[:,:,1]<<1) + (b[:,:,2]<<2)).astype(np.uint8)
    else:
        raise PreservationError(f"PACKED_BITS_INVALID:{bits}")
    vals=meta[:,1,None] + meta[:,0,None]*q.astype(np.float32)
    return vals,meta


def _decode_remainder(blob: np.ndarray, count: int, bits: int) -> np.ndarray:
    if len(blob)<4:
        raise PreservationError("PACKED_REMAINDER_TRUNCATED")
    meta=np.frombuffer(np.ascontiguousarray(blob[:4]).tobytes(),dtype="<f2").astype(np.float32)
    packed=np.ascontiguousarray(blob[4:])
    bits_arr=np.unpackbits(packed,bitorder="little")[:count*bits].reshape(count,bits)
    weights=(1<<np.arange(bits,dtype=np.uint8))
    q=(bits_arr*weights).sum(axis=1).astype(np.float32)
    return meta[1] + meta[0]*q


def load_packed_donor(model: VisionEncoderDecoderModel, packed_path: Path) -> dict[str, Any]:
    manifest=read_packed_manifest(packed_path)
    state=model.state_dict()
    alias_rows={x["name"]:x for x in manifest["tensor_aliases"]}
    if set(alias_rows)!=set(state):
        raise PreservationError(
            f"PACKED_STATE_KEY_MISMATCH:missing={sorted(set(state)-set(alias_rows))[:3]}:"
            f"extra={sorted(set(alias_rows)-set(state))[:3]}"
        )
    mm=np.memmap(packed_path,dtype=np.uint8,mode="r")
    with torch.no_grad():
        for storage in manifest["storages"]:
            aliases=storage["aliases"]
            first=aliases[0]
            target=state[first].reshape(-1)
            numel=int(storage["numel"])
            if target.numel()!=numel:
                raise PreservationError(f"PACKED_TARGET_NUMEL_MISMATCH:{first}")
            start=int(storage["data_start"])
            end=int(storage["data_end"])
            if storage["dtype"]=="I64":
                arr=np.frombuffer(
                    np.ascontiguousarray(mm[start:end]).tobytes(),
                    dtype="<i8",
                ).copy()
                _copy_aliases(state,aliases,torch.from_numpy(arr))
                continue
            bits=int(storage["bits"])
            row_bytes=4 + math.ceil(256*bits/8)
            full,rem=divmod(numel,256)
            pos=start
            written=0
            chunk_groups=512
            while written//256 < full:
                g0=written//256
                n=min(chunk_groups,full-g0)
                nbytes=n*row_bytes
                block=np.asarray(mm[pos:pos+nbytes]).reshape(n,row_bytes)
                vals,_=_decode_full_group_block(block,bits)
                flat=torch.from_numpy(vals.reshape(-1))
                target[written:written+n*256].copy_(flat.to(dtype=target.dtype))
                written += n*256
                pos += nbytes
            if rem:
                rbytes=4+math.ceil(rem*bits/8)
                vals=_decode_remainder(np.asarray(mm[pos:pos+rbytes]),rem,bits)
                target[written:written+rem].copy_(torch.from_numpy(vals).to(dtype=target.dtype))
                written += rem
                pos += rbytes
            if written!=numel or pos!=end:
                raise PreservationError(
                    f"PACKED_STORAGE_BOUNDARY_MISMATCH:{first}:{written}/{numel}:{pos}/{end}"
                )
            for alias in aliases[1:]:
                other=state[alias].reshape(-1)
                if other.data_ptr()!=target.data_ptr():
                    other.copy_(target)
    return {
        "tensor_count":manifest["tensor_count"],
        "storage_count":manifest["storage_count"],
        "packed_bytes":Path(packed_path).stat().st_size,
    }


def make_model_and_processor():
    cfg=VisionEncoderDecoderConfig.from_pretrained(MODEL_ID,revision=MODEL_REVISION)
    proc=DonutProcessor.from_pretrained(MODEL_ID,revision=MODEL_REVISION)
    model=VisionEncoderDecoderModel(config=cfg)
    model.eval()
    return model,proc


def answer_case(model,processor,image_path: Path,question: str) -> str:
    image=Image.open(image_path).convert("RGB")
    pixel_values=processor(image,return_tensors="pt").pixel_values
    prompt=f"<chartqa> {question} <s_answer>"
    decoder_input_ids=processor.tokenizer(
        prompt,
        add_special_tokens=False,
        return_tensors="pt",
    ).input_ids
    unk=processor.tokenizer.unk_token_id
    with torch.inference_mode():
        outputs=model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=4,
            bad_words_ids=[[unk]] if unk is not None else None,
        )
    seq=processor.batch_decode(outputs)[0]
    if processor.tokenizer.eos_token:
        seq=seq.replace(processor.tokenizer.eos_token,"")
    if processor.tokenizer.pad_token:
        seq=seq.replace(processor.tokenizer.pad_token,"")
    return seq.split("<s_answer>")[-1].strip()


def evaluate_subject(model,processor,cases: list[dict[str,Any]],image_dir: Path) -> dict[str,Any]:
    rows=[]
    for case in cases:
        pred=answer_case(model,processor,image_dir/case["imgname"],case["query"])
        ok=relaxed_correct(case["label"],pred)
        rows.append({
            "id":case["id"],
            "imgname":case["imgname"],
            "query":case["query"],
            "label":case["label"],
            "prediction":pred,
            "relaxed_correct":ok,
        })
        print(json.dumps({"id":case["id"],"prediction":pred,"correct":ok}),flush=True)
    accuracy=sum(int(x["relaxed_correct"]) for x in rows)/len(rows)
    return {"accuracy":accuracy,"correct":sum(int(x["relaxed_correct"]) for x in rows),"total":len(rows),"rows":rows}


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
    packed_load=load_packed_donor(model,Path(args.packed_source))
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
        "schema":"PROJECT_BRAIN_H100_UNICHART_CHARTQA_PRESERVATION_RESULT_V1",
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
        "environment":{
            "python":"3.11.16",
            "torch":"2.0.1+cpu",
            "transformers":"4.28.1",
            "numpy":"1.26.4",
        },
        "hard_nonclaims":[
            "PUBLIC_CHARTQA_PRESERVATION_DOES_NOT_PROVE_CHARTOGRAPHY_GE_89",
            "PUBLIC_CHARTQA_PRESERVATION_DOES_NOT_PROVE_FULL_H100_TERMINAL_CAPABILITY",
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
