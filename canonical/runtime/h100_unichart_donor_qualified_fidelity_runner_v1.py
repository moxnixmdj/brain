from __future__ import annotations
import argparse, json
from pathlib import Path
from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import make_model_and_processor, answer_case, relaxed_correct
from canonical.runtime.h100_unichart_structural_holdout_runner_v1 import load_structural

EXPECTED_PACKED_SHA="89d0dfe759920047c8668d398b0811efad962f0194f36f3858bedf290af3d429"
EXPECTED_COMPLETE_BYTES=99_999_997
REQUIRED_CORRECT=19
REQUIRED_AGREEMENTS=17

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--selection",required=True)
    ap.add_argument("--image-dir",required=True)
    ap.add_argument("--packed-source",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    sel=json.load(open(a.selection))
    cases=sel["cases"]
    if sel.get("packed_subject_was_run_during_selection") is not False or len(cases)!=20:
        raise RuntimeError("SELECTION_INVALID")
    for c in cases:
        if not relaxed_correct(c["label"],c["fp32_prediction"]):
            raise RuntimeError("DONOR_SELECTED_CASE_NOT_CORRECT:"+c["id"])

    model,proc=make_model_and_processor()
    load=load_structural(model,Path(a.packed_source),EXPECTED_PACKED_SHA)
    complete=load["packed_bytes"]+5_313_202
    if complete!=EXPECTED_COMPLETE_BYTES:
        raise RuntimeError("COMPLETE_BUNDLE_MISMATCH")

    rows=[]; correct=0; agreements=0; status="INCONCLUSIVE"
    for i,c in enumerate(cases,1):
        pred=answer_case(model,proc,Path(a.image_dir)/c["imgname"],c["query"])
        ok=relaxed_correct(c["label"],pred)
        agree=pred==c["fp32_prediction"]
        correct+=int(ok); agreements+=int(agree)
        row={"index":i,"id":c["id"],"split":c["split"],"label":c["label"],"fp32_prediction":c["fp32_prediction"],"packed_prediction":pred,"relaxed_correct":ok,"exact_agreement":agree}
        rows.append(row)
        print(json.dumps(row),flush=True)
        rem=20-i
        if correct+rem<REQUIRED_CORRECT or agreements+rem<REQUIRED_AGREEMENTS:
            status="FAIL__DONOR_QUALIFIED_FIDELITY_GATE_MATHEMATICALLY_IMPOSSIBLE"
            break
        if correct>=REQUIRED_CORRECT and agreements>=REQUIRED_AGREEMENTS:
            status="PASS__DONOR_QUALIFIED_FIDELITY_GATE_MATHEMATICALLY_SECURED"
            break
    out={"schema":"PROJECT_BRAIN_H100_UNICHART_DONOR_QUALIFIED_FIDELITY_RESULT_V1","status":status,"pass":status.startswith("PASS__"),"selected_case_count":20,"evaluated_cases":len(rows),"required_packed_correct":REQUIRED_CORRECT,"required_exact_agreements":REQUIRED_AGREEMENTS,"packed_correct_so_far":correct,"exact_agreements_so_far":agreements,"max_possible_packed_correct":correct+(20-len(rows)),"max_possible_exact_agreements":agreements+(20-len(rows)),"packed_sha256":EXPECTED_PACKED_SHA,"complete_bundle_bytes":complete,"h100_budget_bytes":100_000_000,"byte_pass":complete<=100_000_000,"load":load,"rows":rows,"hard_nonclaims":["DONOR_QUALIFIED_FIDELITY_IS_NOT_FULL_CHARTQA_ACCURACY","NO_CHARTOGRAPHY_THRESHOLD_CREDIT","NO_FULL_H100_TERMINAL_CREDIT"],"h100_credit_delta":0}
    json.dump(out,open(a.output,"w"),indent=2,sort_keys=True)
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
