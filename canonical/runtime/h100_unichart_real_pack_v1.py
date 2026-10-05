from __future__ import annotations

import argparse,hashlib,json,math,shutil,struct,tempfile
from pathlib import Path
from typing import Any
import numpy as np
from canonical.runtime.h100_unichart_safetensors_header_audit_v1 import parse_header_blob

H100_BUDGET_BYTES=100_000_000
GROUP_SIZE=256
EXPECTED_SOURCE_BYTES=809_095_376
EXPECTED_SOURCE_SHA256="2faf9ef1ac62a290ea58c80e9e2454db4e3613579e7cb6167cb934a03c09664e"
EXPECTED_SOURCE_MANIFEST_SHA256="8b32480b8f7981f3c8413941e522034f3779bef1187374f2ca836bc29af314c5"
ANCILLARY_EXPECTED={
 ".gitattributes":1477,"README.md":4909,"added_tokens.json":235,"config.json":4941,
 "generation_config.json":186,"preprocessor_config.json":420,
 "sentencepiece.bpe.model":1296245,"special_tokens_map.json":355,
 "tokenizer.json":4008718,"tokenizer_config.json":510,
}

class PackError(ValueError): pass

def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
 return h.hexdigest()

def _read_header(source:Path):
 with source.open("rb") as f:
  first=f.read(8)
  if len(first)!=8: raise PackError("SOURCE_HEADER_PREFIX_TRUNCATED")
  n=struct.unpack("<Q",first)[0]
  if n<=0 or n>16_000_000: raise PackError("SOURCE_HEADER_LENGTH_INVALID")
  rest=f.read(n)
  if len(rest)!=n: raise PackError("SOURCE_HEADER_TRUNCATED")
 blob=first+rest
 return parse_header_blob(blob,expected_file_size=source.stat().st_size)

def _sensitive_f32(name:str,numel:int)->bool:
 low=name.lower()
 return numel<=4096 or name.endswith(".bias") or "layernorm" in low or "layer_norm" in low or name.endswith("relative_position_bias_table") or name.endswith("relative_position_bias_table.weight")

def _policy(name:str,dtype:str,numel:int):
 if dtype=="I64": return "RAW_I64",None
 if dtype!="F32": raise PackError("UNSUPPORTED_SOURCE_DTYPE:"+dtype)
 if _sensitive_f32(name,numel): return "RAW_F32",None
 if name.startswith("encoder."): return "GROUPWISE_ASYM",4
 if name.startswith("decoder."): return "GROUPWISE_ASYM",3
 raise PackError("TENSOR_PREFIX_UNCLASSIFIED:"+name)

def _pack_full_groups(q:np.ndarray,bits:int)->bytes:
 flat=np.asarray(q,dtype=np.uint8).reshape(-1)
 if bits==4:
  if flat.size%2: raise PackError("W4_ALIGNMENT")
  a=flat.astype(np.uint16).reshape(-1,2)
  return (a[:,0] | (a[:,1]<<4)).astype(np.uint8).tobytes()
 if bits==3:
  if flat.size%8: raise PackError("W3_ALIGNMENT")
  a=flat.astype(np.uint32).reshape(-1,8)
  v=a[:,0]|(a[:,1]<<3)|(a[:,2]<<6)|(a[:,3]<<9)|(a[:,4]<<12)|(a[:,5]<<15)|(a[:,6]<<18)|(a[:,7]<<21)
  out=np.empty((len(v),3),dtype=np.uint8)
  out[:,0]=(v&255).astype(np.uint8); out[:,1]=((v>>8)&255).astype(np.uint8); out[:,2]=((v>>16)&255).astype(np.uint8)
  return out.tobytes()
 raise PackError("BITS_UNSUPPORTED")

def _pack_tail(q:np.ndarray,bits:int)->bytes:
 acc=0; nbits=0; out=bytearray()
 for raw in np.asarray(q,dtype=np.uint8).reshape(-1).tolist():
  v=int(raw); acc|=v<<nbits; nbits+=bits
  while nbits>=8:
   out.append(acc&255); acc>>=8; nbits-=8
 if nbits: out.append(acc&255)
 return bytes(out)

def _quantize(mat:np.ndarray,bits:int):
 mat=np.asarray(mat,dtype=np.float32)
 if not np.isfinite(mat).all(): raise PackError("SOURCE_NONFINITE_WEIGHT")
 levels=(1<<bits)-1
 mins=mat.min(axis=1); maxs=mat.max(axis=1)
 off16=mins.astype(np.float16); off32=off16.astype(np.float32)
 sc16=((maxs-off32)/float(levels)).astype(np.float16)
 bad=(sc16==0)&(maxs!=mins)
 if bad.any(): sc16[bad]=np.nextafter(np.float16(0),np.float16(1))
 if not np.isfinite(off16.astype(np.float32)).all() or not np.isfinite(sc16.astype(np.float32)).all(): raise PackError("QUANT_METADATA_NONFINITE")
 sc32=sc16.astype(np.float32); safe=np.where(sc32==0,np.float32(1),sc32)
 q=np.rint((mat-off32[:,None])/safe[:,None]); q=np.clip(q,0,levels).astype(np.uint8)
 q=np.where((sc32==0)[:,None],0,q).astype(np.uint8)
 recon=off32[:,None]+sc32[:,None]*q.astype(np.float32)
 diff=mat.astype(np.float64)-recon.astype(np.float64)
 return off16.astype("<f2"),sc16.astype("<f2"),q,float(np.sum(diff*diff,dtype=np.float64)),float(np.max(np.abs(diff)))

def _copy_range(source:Path,out,offset:int,n:int):
 with source.open("rb") as f:
  f.seek(offset); remaining=n
  while remaining:
   b=f.read(min(8*1024*1024,remaining))
   if not b: raise PackError("SOURCE_RANGE_TRUNCATED")
   out.write(b); remaining-=len(b)

def pack(source:str|Path,ancillary_dir:str|Path,output_dir:str|Path)->dict[str,Any]:
 source=Path(source); ancillary_dir=Path(ancillary_dir); output_dir=Path(output_dir)
 if source.stat().st_size!=EXPECTED_SOURCE_BYTES: raise PackError("SOURCE_SIZE_MISMATCH")
 if sha256_file(source)!=EXPECTED_SOURCE_SHA256: raise PackError("SOURCE_SHA256_MISMATCH")
 census=_read_header(source)
 if census["tensor_manifest_sha256"]!=EXPECTED_SOURCE_MANIFEST_SHA256: raise PackError("SOURCE_MANIFEST_MISMATCH")
 rows=sorted(census["tensors"],key=lambda r:(r["data_start"],r["name"]))
 payload_base=8+census["header_length_bytes"]
 if output_dir.exists(): shutil.rmtree(output_dir)
 output_dir.mkdir(parents=True); aout=output_dir/"ancillary"; aout.mkdir()

 ancillary_bytes=0; ancillary_receipt=[]
 for name,size in ANCILLARY_EXPECTED.items():
  src=ancillary_dir/name
  if not src.is_file() or src.stat().st_size!=size: raise PackError("ANCILLARY_SIZE_MISMATCH:"+name)
  dst=aout/name; shutil.copyfile(src,dst); ancillary_bytes+=size
  ancillary_receipt.append({"name":name,"bytes":size,"sha256":sha256_file(dst)})

 weights=output_dir/"weights.pbq"; records=[]
 source_f32=source_i64=raw_f32_bytes=raw_i64_bytes=quantized=packed_bytes=meta_bytes=0
 sse=0.0; err_n=0; maxerr=0.0
 with weights.open("wb") as out:
  out.write(b"PBH100Q1")
  for row in rows:
   name=row["name"]; dtype=row["dtype"]; n=int(row["numel"]); rep,bits=_policy(name,dtype,n)
   rec={"name":name,"shape":row["shape"],"source_dtype":dtype,"numel":n,"representation":rep,"packed_block_start":out.tell()}
   src_off=payload_base+int(row["data_start"])
   if rep=="RAW_I64":
    source_i64+=n; raw_i64_bytes+=int(row["payload_bytes"]); _copy_range(source,out,src_off,int(row["payload_bytes"])); rec["raw_bytes"]=int(row["payload_bytes"])
   elif rep=="RAW_F32":
    source_f32+=n; raw_f32_bytes+=int(row["payload_bytes"]); _copy_range(source,out,src_off,int(row["payload_bytes"])); rec["raw_bytes"]=int(row["payload_bytes"])
   else:
    source_f32+=n; quantized+=n; groups=(n+GROUP_SIZE-1)//GROUP_SIZE
    view=np.memmap(source,mode="r",dtype="<f4",offset=src_off,shape=(n,))
    offs=[]; scales=[]; local_sse=0.0; local_max=0.0; local_packed=0
    with tempfile.SpooledTemporaryFile(max_size=8*1024*1024) as spool:
     full=n//GROUP_SIZE; g=0
     while g<full:
      take=min(4096,full-g); start=g*GROUP_SIZE; stop=(g+take)*GROUP_SIZE
      o,s,q,se,ma=_quantize(np.asarray(view[start:stop],dtype=np.float32).reshape(take,GROUP_SIZE),bits)
      offs.append(o); scales.append(s); b=_pack_full_groups(q,bits); spool.write(b)
      local_packed+=len(b); local_sse+=se; local_max=max(local_max,ma); g+=take
     rem=n-full*GROUP_SIZE
     if rem:
      o,s,q,se,ma=_quantize(np.asarray(view[full*GROUP_SIZE:n],dtype=np.float32).reshape(1,rem),bits)
      offs.append(o); scales.append(s); b=_pack_tail(q,bits); spool.write(b)
      local_packed+=len(b); local_sse+=se; local_max=max(local_max,ma)
     oa=np.concatenate(offs).astype("<f2",copy=False); sa=np.concatenate(scales).astype("<f2",copy=False)
     if len(oa)!=groups: raise PackError("GROUP_COUNT_MISMATCH:"+name)
     mstart=out.tell(); out.write(oa.tobytes()); out.write(sa.tobytes()); mend=out.tell()
     spool.seek(0); pstart=out.tell(); shutil.copyfileobj(spool,out,length=8*1024*1024); pend=out.tell()
    expected=(n*bits+7)//8
    if local_packed!=expected or pend-pstart!=expected: raise PackError("PACKED_BYTES_MISMATCH:"+name)
    if mend-mstart!=groups*4: raise PackError("META_BYTES_MISMATCH:"+name)
    packed_bytes+=expected; meta_bytes+=groups*4; sse+=local_sse; err_n+=n; maxerr=max(maxerr,local_max)
    rec.update({"bits":bits,"group_size":GROUP_SIZE,"group_count":groups,"metadata_start":mstart,"metadata_end":mend,"packed_values_start":pstart,"packed_values_end":pend,"quantization_sse":local_sse,"quantization_max_abs_error":local_max})
    del view
   rec["packed_block_end"]=out.tell(); records.append(rec)

 manifest={
  "schema":"PROJECT_BRAIN_UNICHART_H100_PACK_V1",
  "source":{"revision":"baa206a05372f8c49778313abb7091e1d0c8e474","safetensors_sha256":EXPECTED_SOURCE_SHA256,"tensor_manifest_sha256":EXPECTED_SOURCE_MANIFEST_SHA256},
  "policy":{"group_size":GROUP_SIZE,"encoder_large":"W4","decoder_large":"W3","sensitive_f32":"RAW_F32","i64":"RAW_I64"},
  "counts":{"tensor_count":len(records),"source_f32_elements":source_f32,"source_i64_elements":source_i64,"quantized_f32_elements":quantized,"raw_f32_bytes":raw_f32_bytes,"raw_i64_bytes":raw_i64_bytes,"packed_value_bytes":packed_bytes,"quant_metadata_bytes":meta_bytes,"ancillary_bytes":ancillary_bytes},
  "quantization_error":{"rmse":math.sqrt(sse/err_n) if err_n else 0.0,"global_max_abs_error":maxerr,"note":"WEIGHT_RECONSTRUCTION_ONLY_NOT_CAPABILITY_EVIDENCE"},
  "weights_sha256":sha256_file(weights),"ancillary":ancillary_receipt,"tensors":records
 }
 mp=output_dir/"manifest.json"; mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
 files=sorted(p for p in output_dir.rglob("*") if p.is_file()); package_bytes=sum(p.stat().st_size for p in files)
 if package_bytes>H100_BUDGET_BYTES: raise PackError(f"H100_PACKAGE_BUDGET_EXCEEDED:{package_bytes}")
 return {
  "schema":"PROJECT_BRAIN_H100_UNICHART_REAL_PACK_OUTPUT_V1",
  "status":"PASS__REAL_PACKED_SUBJECT_UNDER_100MB__CAPABILITY_PRESERVATION_UNPROVED",
  "package_bytes":package_bytes,"h100_budget_bytes":H100_BUDGET_BYTES,"margin_bytes":H100_BUDGET_BYTES-package_bytes,
  "weights_file_bytes":weights.stat().st_size,"weights_sha256":sha256_file(weights),
  "manifest_bytes":mp.stat().st_size,"manifest_sha256":sha256_file(mp),"ancillary_bytes":ancillary_bytes,
  "source_f32_elements":source_f32,"source_i64_elements":source_i64,"quantized_f32_elements":quantized,
  "raw_f32_bytes":raw_f32_bytes,"raw_i64_bytes":raw_i64_bytes,"packed_value_bytes":packed_bytes,"quant_metadata_bytes":meta_bytes,
  "quantization_rmse":manifest["quantization_error"]["rmse"],"quantization_global_max_abs_error":maxerr,
  "package_files":[{"path":str(p.relative_to(output_dir)),"bytes":p.stat().st_size,"sha256":sha256_file(p)} for p in files],
  "h100_credit_delta":0,"acceptance_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
  "hard_nonclaims":["REAL_PACKED_BYTES_DO_NOT_PROVE_CAPABILITY_PRESERVATION","NO_CHARTOGRAPHY_THRESHOLD_CREDIT","NO_H100_TERMINAL_CREDIT"]
 }

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--source",required=True); ap.add_argument("--ancillary-dir",required=True); ap.add_argument("--output-dir",required=True); a=ap.parse_args()
 print(json.dumps(pack(a.source,a.ancillary_dir,a.output_dir),indent=2,sort_keys=True))
if __name__=="__main__": main()
