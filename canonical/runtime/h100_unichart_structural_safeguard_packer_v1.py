from __future__ import annotations
import argparse, base64, hashlib, json, math, struct, zipfile
from pathlib import Path
from typing import Any
import numpy as np
from canonical.runtime.h100_unichart_chartqa_bin_packer_v1 import parse_checkpoint_metadata
from canonical.runtime.h100_unichart_lowbit_packer_v1 import GROUP_SIZE,H100_BUDGET_BYTES,MAGIC,PackerError,_sha256,quantize_group
from canonical.runtime.h100_unichart_error_first_knapsack_v1 import _sse_rows

SCHEMA='PROJECT_BRAIN_H100_UNICHART_STRUCTURAL_SAFEGUARD_RESULT_V1'
PACKED_SCHEMA='PROJECT_BRAIN_H100_UNICHART_STRUCTURAL_SAFEGUARD_PACKED_V1'

def mode_for(storage):
    if storage['dtype']=='I64': return 'I64'
    names=[x.lower() for x in storage['aliases']]
    first=names[0]
    # Small numerically sensitive affine state.
    if any(('layernorm' in n or 'layer_norm' in n or '.norm.' in n or n.endswith('.bias')) for n in names):
        return 'FP16'
    # Shared token/output embedding is directly exposed to generation.
    if any(('lm_head.weight' in n or 'embed_tokens.weight' in n) for n in names):
        return 'W4_FORCED'
    if any('embed_positions.weight' in n for n in names):
        return 'W4_FORCED'
    if any('relative_position_bias_table' in n for n in names):
        return 'W4_FORCED'
    return 'CANDIDATE'

def group_payload(n,bits): return 4+math.ceil(n*bits/8)

def score_candidates(source,parsed,*,chunk_groups:int=4096):
    ranked=[]; gid=0
    with zipfile.ZipFile(source,'r') as z:
        for s in parsed['storages']:
            mode=mode_for(s)
            if s['dtype']!='F32':
                continue
            remaining=int(s['numel']); local=0
            with z.open(s['entry'],'r') as src:
                while remaining:
                    groups=min(chunk_groups,math.ceil(remaining/GROUP_SIZE))
                    want=min(remaining,groups*GROUP_SIZE)
                    raw=src.read(want*4)
                    if len(raw)!=want*4:
                        raise PackerError('SOURCE_TRUNCATED')
                    vals=np.frombuffer(raw,dtype='<f4')
                    full,rem=divmod(want,GROUP_SIZE)
                    pos=0
                    if full:
                        mat=vals[:full*GROUP_SIZE].reshape(full,GROUP_SIZE)
                        if mode=='CANDIDATE':
                            s3=_sse_rows(mat,3); s4=_sse_rows(mat,4)
                            for j in range(full):
                                ranked.append((float(s3[j]-s4[j]),s['aliases'][0],local,gid))
                                local+=1; gid+=1
                        else:
                            local+=full
                        pos=full*GROUP_SIZE
                    if rem:
                        if mode=='CANDIDATE':
                            mat=vals[pos:].reshape(1,rem)
                            s3=_sse_rows(mat,3); s4=_sse_rows(mat,4)
                            ranked.append((float(s3[0]-s4[0]),s['aliases'][0],local,gid))
                            gid+=1
                        local+=1
                    remaining-=want
                if src.read(1):
                    raise PackerError('SOURCE_TRAILING_BYTES')
    ranked.sort(key=lambda r:(-r[0],r[1],r[2]))
    return ranked

def layout(parsed,selected,source_sha):
    cursor=len(MAGIC)+8; cand_gid=0; stor=[]
    for s in parsed['storages']:
        start=cursor; mode=mode_for(s); groups=0; cand_start=cand_gid
        if mode=='I64':
            cursor += int(s['bytes'])
        elif mode=='FP16':
            cursor += int(s['numel'])*2
        else:
            rem=int(s['numel'])
            while rem:
                n=min(GROUP_SIZE,rem)
                if mode=='W4_FORCED': bits=4
                else:
                    bits=4 if cand_gid in selected else 3
                    cand_gid+=1
                cursor+=group_payload(n,bits); groups+=1; rem-=n
        stor.append({'key':s['key'],'dtype':s['dtype'],'numel':s['numel'],'aliases':s['aliases'],
                     'mode':mode,'groups':groups,
                     'candidate_group_start':cand_start if mode=='CANDIDATE' else None,
                     'data_start':start,'data_end':cursor})
    precision=bytearray((cand_gid+7)//8)
    for idx in selected:
        if idx<0 or idx>=cand_gid:
            raise PackerError('CANDIDATE_BITMAP_INDEX_OUT_OF_RANGE')
        precision[idx//8] |= 1 << (idx%8)
    precision_bytes=bytes(precision)
    manifest={'schema':PACKED_SCHEMA,'source_sha256':source_sha,'group_size':GROUP_SIZE,
              'policy':'FP16_NORM_BIAS__W4_TOKEN_POSITION_RELPOS__SOURCE_SSE_KNAPSACK_REMAINDER',
              'selected_candidate_w4_groups':len(selected),'candidate_group_count':cand_gid,
              'candidate_precision_bitmap_b64':base64.b64encode(precision_bytes).decode('ascii'),
              'candidate_precision_bitmap_sha256':hashlib.sha256(precision_bytes).hexdigest(),
              'storages':stor,
              'tensor_count':parsed['tensor_count'],'storage_count':parsed['storage_count'],
              'tensor_aliases':[{'name':r['name'],'storage_key':r['storage_key'],'shape':r['shape'],
                                 'stride':r['stride'],'dtype':r['storage_dtype']} for r in parsed['tensor_rows']]}
    mb=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    return manifest,cursor+len(mb),len(mb)

def choose(source,parsed,ancillary):
    sha=_sha256(source); ranked=score_candidates(source,parsed); ids=[r[3] for r in ranked]
    lo,hi=0,len(ids); best=None
    while lo<=hi:
        mid=(lo+hi)//2; sel=set(ids[:mid]); m,p,mb=layout(parsed,sel,sha); complete=p+ancillary
        if complete<=H100_BUDGET_BYTES:
            best=(sel,m,p,complete,mb,ranked); lo=mid+1
        else: hi=mid-1
    if best is None: raise PackerError('NO_FEASIBLE_LAYOUT')
    return best

def pack_group(vals,bits):
    meta,codes=quantize_group(vals.astype(np.float32).tolist(),bits); return meta+codes

def build(source,output,expected_sha,ancillary):
    source=Path(source); output=Path(output)
    if _sha256(source)!=expected_sha: raise PackerError('SOURCE_SHA_MISMATCH')
    parsed=parse_checkpoint_metadata(source)
    selected,manifest,projected,complete,manifest_bytes,ranked=choose(source,parsed,ancillary)
    with zipfile.ZipFile(source,'r') as z, output.open('wb+') as out:
        out.write(MAGIC); out.write(struct.pack('<Q',0))
        cand_gid=0
        for s,ms in zip(parsed['storages'],manifest['storages']):
            if out.tell()!=ms['data_start']: raise PackerError('LAYOUT_START')
            mode=mode_for(s)
            with z.open(s['entry'],'r') as src:
                if mode=='I64':
                    raw=src.read()
                    if len(raw)!=int(s['bytes']): raise PackerError('I64_TRUNC')
                    out.write(raw)
                elif mode=='FP16':
                    raw=src.read()
                    vals=np.frombuffer(raw,dtype='<f4')
                    if not np.isfinite(vals).all(): raise PackerError('NONFINITE')
                    out.write(vals.astype('<f2').tobytes())
                else:
                    rem=int(s['numel'])
                    while rem:
                        n=min(GROUP_SIZE,rem); raw=src.read(n*4)
                        if len(raw)!=n*4: raise PackerError('F32_TRUNC')
                        vals=np.frombuffer(raw,dtype='<f4')
                        if mode=='W4_FORCED': bits=4
                        else:
                            bits=4 if cand_gid in selected else 3; cand_gid+=1
                        out.write(pack_group(vals,bits)); rem-=n
            if out.tell()!=ms['data_end']: raise PackerError('LAYOUT_END')
        mb=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
        mo=out.tell(); out.write(mb); final=out.tell(); out.seek(len(MAGIC)); out.write(struct.pack('<Q',len(mb))); out.flush()
    if final!=projected: raise PackerError(f'PROJECTED_MISMATCH:{final}!={projected}')
    if final+ancillary>H100_BUDGET_BYTES: raise PackerError('BUDGET_EXCEEDED')
    counts={}
    for s in manifest['storages']: counts[s['mode']]=counts.get(s['mode'],0)+int(s['numel'])
    return {'schema':SCHEMA,'status':'PACKED__POST_FAILURE_STRUCTURAL_CANDIDATE__HOLDOUT_UNTESTED',
            'source_sha256':expected_sha,'output_sha256':_sha256(output),'output_bytes':final,
            'ancillary_bytes':ancillary,'complete_bundle_bytes':final+ancillary,
            'margin_bytes':H100_BUDGET_BYTES-final-ancillary,'selected_candidate_w4_groups':len(selected),
            'candidate_groups_total':len(ranked),'mode_numel':counts,'manifest_bytes':len(mb),
            'hard_nonclaims':['POLICY_WAS_DESIGNED_AFTER_PRIOR_20_CASE_FAILURES','PRIOR_20_CASES_ARE_DEVELOPMENT_ONLY','NO_HOLDOUT_CAPABILITY_CREDIT','NO_FULL_H100_TERMINAL_CREDIT']}

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); ap.add_argument('--output',required=True)
    ap.add_argument('--expected-source-sha256',required=True); ap.add_argument('--ancillary-bytes',type=int,required=True); ap.add_argument('--result-json')
    a=ap.parse_args(); r=build(Path(a.source),Path(a.output),a.expected_source_sha256,a.ancillary_bytes)
    if a.result_json: Path(a.result_json).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps(r,indent=2,sort_keys=True))
