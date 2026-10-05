from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import StoppingCriteria, StoppingCriteriaList

from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import (
    H100_BUDGET_BYTES,
    load_fp32_donor,
    load_packed_donor,
    make_model_and_processor,
    answer_case,
)


class ImpossibleAgreementStop(StoppingCriteria):
    def __init__(self, tokenizer, target: str, prompt_len: int):
        self.tokenizer=tokenizer
        self.target=target
        self.prompt_len=prompt_len
        removable={tokenizer.eos_token,tokenizer.pad_token,None}
        self.nonremovable_specials={
            x for x in tokenizer.all_special_tokens
            if x not in removable
        }
        self.proven=False
        self.trigger_tokens: list[list[str]]=[]

    def __call__(self,input_ids,scores,**kwargs):
        impossible=[]
        triggers=[]
        for row in input_ids:
            ids=row[self.prompt_len:].tolist()
            toks=self.tokenizer.convert_ids_to_tokens(ids)
            bad=[
                tok for tok in toks
                if tok in self.nonremovable_specials
                and tok not in self.target
            ]
            impossible.append(bool(bad))
            triggers.append(bad)
        if impossible and all(impossible):
            self.proven=True
            self.trigger_tokens=triggers
            return True
        return False


def certify_case_mismatch(model,processor,image_path: Path,question: str,target: str) -> dict[str,Any]:
    image=Image.open(image_path).convert("RGB")
    pixel_values=processor(image,return_tensors="pt").pixel_values
    prompt=f"<chartqa> {question} <s_answer>"
    decoder_input_ids=processor.tokenizer(
        prompt,add_special_tokens=False,return_tensors="pt"
    ).input_ids
    stop=ImpossibleAgreementStop(
        processor.tokenizer,target,decoder_input_ids.shape[1]
    )
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
            stopping_criteria=StoppingCriteriaList([stop]),
        )
    if stop.proven:
        return {
            "mismatch_proven":True,
            "proof":"ALL_LIVE_BEAMS_CONTAIN_NONREMOVABLE_SPECIAL_TOKEN_ABSENT_FROM_FP32_TARGET",
            "trigger_tokens":stop.trigger_tokens,
            "packed_final_prediction":None,
        }
    seq=processor.batch_decode(outputs)[0]
    if processor.tokenizer.eos_token:
        seq=seq.replace(processor.tokenizer.eos_token,"")
    if processor.tokenizer.pad_token:
        seq=seq.replace(processor.tokenizer.pad_token,"")
    pred=seq.split("<s_answer>")[-1].strip()
    return {
        "mismatch_proven":pred!=target,
        "proof":"FULL_GENERATION_EXACT_STRING_COMPARISON",
        "trigger_tokens":[],
        "packed_final_prediction":pred,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preexposure",required=True)
    ap.add_argument("--image-dir",required=True)
    ap.add_argument("--fp32-source",required=True)
    ap.add_argument("--packed-source",required=True)
    ap.add_argument("--runtime-assets",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--max-prefix",type=int,default=20)
    args=ap.parse_args()

    pre=json.load(open(args.preexposure))
    assets=json.load(open(args.runtime_assets))
    cases=pre["population"]["cases"][:args.max_prefix]

    model,processor=make_model_and_processor()
    fp32_load=load_fp32_donor(model,Path(args.fp32_source))
    fp32_predictions=[]
    for case in cases:
        pred=answer_case(model,processor,Path(args.image_dir)/case["imgname"],case["query"])
        fp32_predictions.append(pred)
        print(json.dumps({"phase":"fp32","id":case["id"],"prediction":pred}),flush=True)
    del model
    gc.collect()

    model,processor=make_model_and_processor()
    packed_load=load_packed_donor(model,Path(args.packed_source))
    rows=[]
    mismatches=0
    for case,target in zip(cases,fp32_predictions):
        cert=certify_case_mismatch(
            model,processor,Path(args.image_dir)/case["imgname"],case["query"],target
        )
        cert.update({"id":case["id"],"fp32_prediction":target})
        rows.append(cert)
        mismatches += int(cert["mismatch_proven"])
        print(json.dumps({
            "phase":"packed_certificate",
            "id":case["id"],
            "mismatch_proven":cert["mismatch_proven"],
            "proof":cert["proof"],
        }),flush=True)
        if mismatches>=4:
            break

    bundle_bytes=Path(args.packed_source).stat().st_size+int(assets["ancillary_total_bytes"])
    impossible=mismatches>=4
    out={
        "schema":"PROJECT_BRAIN_H100_UNICHART_COARSE_GATE_FUTILITY_CERTIFICATE_V1",
        "status":"PASS__COARSE_20_CASE_GATE_MATHEMATICALLY_IMPOSSIBLE" if impossible else "OPEN__INSUFFICIENT_MISMATCHES",
        "mismatches_proven":mismatches,
        "cases_examined":len(rows),
        "minimum_mismatches_for_impossibility":4,
        "maximum_possible_full_20_agreements":20-mismatches if impossible else None,
        "frozen_agreement_minimum":0.85,
        "rows":rows,
        "bundle_bytes":bundle_bytes,
        "byte_pass":bundle_bytes<=H100_BUDGET_BYTES,
        "fp32_load":fp32_load,
        "packed_load":packed_load,
        "hard_nonclaims":[
            "THIS_CERTIFIES_ONLY_THE_COARSE_W4_ENCODER_W3_DECODER_GATE",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "h100_credit_delta":0,
    }
    json.dump(out,open(args.output,"w"),indent=2,sort_keys=True)
    print(json.dumps({
        "status":out["status"],
        "mismatches_proven":mismatches,
        "cases_examined":len(rows),
        "bundle_bytes":bundle_bytes,
    },indent=2,sort_keys=True))


if __name__=="__main__":
    main()
