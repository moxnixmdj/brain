from __future__ import annotations
import argparse, base64, hashlib, json, math, struct
from pathlib import Path
import numpy as np
import torch

from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import (
    MAGIC, EXPECTED_SOURCE_SHA256, PreservationError, _copy_aliases,
    _decode_full_group_block, _decode_remainder, make_model_and_processor,
    load_fp32_donor, answer_case, relaxed_correct,
)

PACKED_SCHEMA='PROJECT_BRAIN_H100_UNICHART_STRUCTURAL_SAFEGUARD_PACKED_V1'
H100_BUDGET_BYTES=100_000_000

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b=f.read(1<<20)
            if not b: break
            h.update(b)
    return h.hexdigest()

def read_manifest(path:Path,expected_packed_sha:str):
    if sha256(path)!=expected_packed_sha:
        raise PreservationError('STRUCTURAL_PACKED_SHA_MISMATCH')
    size=path.stat().st_size
    with path.open('rb') as f:
        if f.read(len(MAGIC))!=MAGIC: raise PreservationError('STRUCTURAL_MAGIC_MISMATCH')
        raw=f.read(8)
        if len(raw)!=8: raise PreservationError('STRUCTURAL_MLEN_TRUNCATED')
        mlen=struct.unpack('<Q',raw)[0]
        if mlen<=0 or mlen>=size: raise PreservationError('STRUCTURAL_MLEN_INVALID')
        f.seek(size-mlen); m=json.loads(f.read(mlen).decode('utf8'))
    if m.get('schema')!=PACKED_SCHEMA: raise PreservationError('STRUCTURAL_SCHEMA_MISMATCH')
    if m.get('source_sha256')!=EXPECTED_SOURCE_SHA256: raise PreservationError('STRUCTURAL_SOURCE_MISMATCH')
    bitmap=base64.b64decode(m['candidate_precision_bitmap_b64'])
    if hashlib.sha256(bitmap).hexdigest()!=m['candidate_precision_bitmap_sha256']:
        raise PreservationError('STRUCTURAL_BITMAP_SHA_MISMATCH')
    return m,bitmap

def load_structural(model,path:Path,expected_packed_sha:str):
    m,bitmap=read_manifest(path,expected_packed_sha)
    state=model.state_dict()
    alias_rows={x['name']:x for x in m['tensor_aliases']}
    if set(alias_rows)!=set(state): raise PreservationError('STRUCTURAL_STATE_KEY_MISMATCH')
    mm=np.memmap(path,dtype=np.uint8,mode='r')
    def cbit(i:int)->int:
        return 1 if bitmap[i//8]&(1<<(i%8)) else 0
    with torch.no_grad():
        for s in m['storages']:
            aliases=s['aliases']; first=aliases[0]; target=state[first].reshape(-1)
            numel=int(s['numel']); start=int(s['data_start']); end=int(s['data_end']); mode=s['mode']
            if target.numel()!=numel: raise PreservationError('STRUCTURAL_TARGET_NUMEL_MISMATCH')
            if mode=='I64':
                arr=np.frombuffer(np.ascontiguousarray(mm[start:end]).tobytes(),dtype='<i8').copy()
                _copy_aliases(state,aliases,torch.from_numpy(arr)); continue
            if mode=='FP16':
                arr=np.frombuffer(np.ascontiguousarray(mm[start:end]).tobytes(),dtype='<f2').astype(np.float32)
                if arr.size!=numel: raise PreservationError('STRUCTURAL_FP16_NUMEL_MISMATCH')
                _copy_aliases(state,aliases,torch.from_numpy(arr)); continue

            full,rem=divmod(numel,256); pos=start; written=0
            cand_start=s.get('candidate_group_start')
            for g in range(full):
                if mode=='W4_FORCED': bits=4
                elif mode=='CANDIDATE': bits=4 if cbit(int(cand_start)+g) else 3
                else: raise PreservationError('STRUCTURAL_MODE_INVALID')
                rowbytes=4+math.ceil(256*bits/8)
                block=np.asarray(mm[pos:pos+rowbytes]).reshape(1,rowbytes)
                vals,_=_decode_full_group_block(block,bits)
                target[written:written+256].copy_(torch.from_numpy(vals.reshape(-1)).to(dtype=target.dtype))
                pos+=rowbytes; written+=256
            if rem:
                g=full
                if mode=='W4_FORCED': bits=4
                else: bits=4 if cbit(int(cand_start)+g) else 3
                rbytes=4+math.ceil(rem*bits/8)
                vals=_decode_remainder(np.asarray(mm[pos:pos+rbytes]),rem,bits)
                target[written:written+rem].copy_(torch.from_numpy(vals).to(dtype=target.dtype))
                pos+=rbytes; written+=rem
            if pos!=end or written!=numel: raise PreservationError('STRUCTURAL_BOUNDARY_MISMATCH')
            for alias in aliases[1:]:
                other=state[alias].reshape(-1)
                if other.data_ptr()!=target.data_ptr(): other.copy_(target)
    return {'packed_bytes':path.stat().st_size,
            'selected_candidate_w4_groups':int(m['selected_candidate_w4_groups']),
            'candidate_group_count':int(m['candidate_group_count'])}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--holdout',required=True)
    ap.add_argument('--image-dir',required=True)
    ap.add_argument('--fp32-source',required=True)
    ap.add_argument('--packed-source',required=True)
    ap.add_argument('--packed-sha256',required=True)
    ap.add_argument('--runtime-assets',required=True)
    ap.add_argument('--output',required=True)
    a=ap.parse_args()
    hold=json.load(open(a.holdout)); cases=hold['cases']
    if len(cases)!=20: raise PreservationError('HOLDOUT_COUNT_MUST_BE_20')
    assets=json.load(open(a.runtime_assets))

    model,proc=make_model_and_processor()
    fp32_load=load_fp32_donor(model,Path(a.fp32_source))
    fp32_rows=[]; fp32_correct=0
    for c in cases:
        pred=answer_case(model,proc,Path(a.image_dir)/c['imgname'],c['query'])
        ok=relaxed_correct(c['label'],pred); fp32_correct+=int(ok)
        fp32_rows.append({'id':c['id'],'prediction':pred,'relaxed_correct':ok})
        print(json.dumps({'phase':'FP32','id':c['id'],'prediction':pred,'correct':ok}),flush=True)
    if fp32_correct<10:
        out={'schema':'PROJECT_BRAIN_H100_UNICHART_STRUCTURAL_HOLDOUT_RESULT_V1',
             'status':'INVALID_DONOR_BASELINE_BELOW_50_PERCENT','fp32_correct':fp32_correct,
             'fp32_accuracy':fp32_correct/20,'h100_credit_delta':0}
        json.dump(out,open(a.output,'w'),indent=2,sort_keys=True); print(json.dumps(out,indent=2)); return
    del model
    model,proc=make_model_and_processor()
    load=load_structural(model,Path(a.packed_source),a.packed_sha256)
    complete=load['packed_bytes']+int(assets['ancillary_total_bytes'])
    if complete>H100_BUDGET_BYTES: raise PreservationError('STRUCTURAL_COMPLETE_BUNDLE_OVER_H100')

    required_correct=fp32_correct-1
    required_agreements=17
    rows=[]; correct=0; agreements=0; status='INCONCLUSIVE'
    fpref={r['id']:r['prediction'] for r in fp32_rows}
    for i,c in enumerate(cases,1):
        pred=answer_case(model,proc,Path(a.image_dir)/c['imgname'],c['query'])
        ok=relaxed_correct(c['label'],pred); agree=(pred==fpref[c['id']])
        correct+=int(ok); agreements+=int(agree)
        row={'index':i,'id':c['id'],'label':c['label'],'fp32_prediction':fpref[c['id']],
             'packed_prediction':pred,'relaxed_correct':ok,'agreement':agree}
        rows.append(row); print(json.dumps({'phase':'PACKED',**row}),flush=True)
        rem=20-i
        if correct+rem<required_correct or agreements+rem<required_agreements:
            status='FAIL__HOLDOUT_GATE_MATHEMATICALLY_IMPOSSIBLE'; break
        if correct>=required_correct and agreements>=required_agreements:
            status='PASS__HOLDOUT_GATE_MATHEMATICALLY_SECURED'; break
    passed=status.startswith('PASS__')
    out={'schema':'PROJECT_BRAIN_H100_UNICHART_STRUCTURAL_HOLDOUT_RESULT_V1','status':status,
         'pass':passed,'evaluated_packed_cases':len(rows),'fp32_correct':fp32_correct,'fp32_accuracy':fp32_correct/20,
         'required_packed_correct':required_correct,'required_agreements':required_agreements,
         'packed_correct_so_far':correct,'agreements_so_far':agreements,
         'max_possible_packed_correct':correct+(20-len(rows)),
         'max_possible_agreements':agreements+(20-len(rows)),
         'complete_bundle_bytes':complete,'byte_pass':complete<=H100_BUDGET_BYTES,
         'packed_sha256':a.packed_sha256,'load':load,'fp32_rows':fp32_rows,'packed_rows':rows,
         'hard_nonclaims':['THIS_IS_PUBLIC_NONTERMINAL_CHARTQA_HOLDOUT_ONLY','NO_CHARTOGRAPHY_THRESHOLD_CREDIT','NO_FULL_H100_TERMINAL_CREDIT'],
         'h100_credit_delta':0}
    json.dump(out,open(a.output,'w'),indent=2,sort_keys=True); print(json.dumps(out,indent=2,sort_keys=True))

if __name__=='__main__': main()
