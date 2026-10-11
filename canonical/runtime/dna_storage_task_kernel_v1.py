"""Deterministic task-facing adapter for donor-free DNA storage capability."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any, Iterable

from canonical.runtime import dna_storage_codec_v1 as codec

SCHEMA = "PROJECT_BRAIN_DNA_STORAGE_TASK_KERNEL_V1"
MODEL_DEPENDENCY_COUNT = 0
NETWORK_DEPENDENCY_COUNT = 0
MAX_INPUT_FILES = 256
MAX_INPUT_BYTES = 8_000_000
DNA_SUFFIXES = {".dna", ".fa", ".fasta", ".fas", ".seq", ".fastq", ".fq"}


class DNAStorageTaskError(RuntimeError):
    pass


def _absolute_paths(text: str) -> list[str]:
    seen=set(); out=[]
    for raw in re.findall(r"/[A-Za-z0-9_.+@%=-]+(?:/[A-Za-z0-9_.+@%=-]+)*", str(text or "")):
        p=raw.rstrip(".,;:)]}")
        if p and p not in seen:
            seen.add(p); out.append(p)
    return out


def _under(path: str, root: str) -> bool:
    p=pathlib.PurePosixPath(path); r=pathlib.PurePosixPath(root)
    try:
        p.relative_to(r); return True
    except Exception:
        return False


def classify_contract(instruction: str, artifact_paths: Iterable[str]) -> dict[str, Any]:
    text=str(instruction or "")
    low=text.casefold()
    artifacts=[str(x) for x in artifact_paths if isinstance(x,str) and x.startswith("/")]
    family=bool(re.search(r"\bdna\b",low)) and any(k in low for k in ("storage","codec","oligo","sequence","encode","decode","recover"))
    explicit_encode=any(k in low for k in ("encode","encoding","to dna"))
    explicit_decode=any(k in low for k in ("decode","decoding","recover","reconstruct","restore","from dna"))
    explicit_implement=any(k in low for k in (
        "implement", "implementation", "write a codec", "build a dna",
        "develop a dna", "create a dna", "provide a dna",
    ))
    encode=sum(k in low for k in ("encode","encoding","store","to dna"))
    decode=sum(k in low for k in ("decode","decoding","recover","reconstruct","restore","from dna","reads"))
    implement=sum(k in low for k in ("implement","implementation","write a codec","codec.py","encoder","decoder"))
    if not family or not artifacts:
        mode=None
    elif explicit_implement:
        mode="implementation"
    elif implement >= 2 and not explicit_encode and not explicit_decode:
        mode="implementation"
    elif explicit_encode and explicit_decode:
        mode="roundtrip"
    elif encode > decode:
        mode="encode"
    elif decode > encode:
        mode="decode"
    elif implement:
        mode="implementation"
    else:
        mode=None
    paths=_absolute_paths(text)
    explicit_outputs=[]; explicit_inputs=[]
    for path in paths:
        pos=text.find(path)
        prefix=text[max(0,pos-48):pos].casefold() if pos>=0 else ""
        marked_input=bool(re.search(r"(?:from|source|input|reads?(?:\s+from)?)\s*$",prefix))
        under_artifact=any(_under(path,a) for a in artifacts)
        if marked_input:
            explicit_inputs.append(path)
            continue
        if not under_artifact:
            explicit_inputs.append(path)
            continue
        if any(path==artifact and _is_probably_directory(artifact) for artifact in artifacts):
            continue
        explicit_outputs.append(path)
    return {
        "schema":"PROJECT_BRAIN_DNA_STORAGE_CONTRACT_CLASSIFICATION_V1",
        "supported":mode is not None,
        "mode":mode,
        "family_evidence":family,
        "artifact_paths":artifacts,
        "explicit_output_paths":explicit_outputs,
        "explicit_input_paths":explicit_inputs,
        "model_dependency_count":0,
        "network_dependency_count":0,
        "terminal_authority":False,
    }


def _is_probably_directory(path: str) -> bool:
    p=pathlib.PurePosixPath(path)
    return p.suffix == "" or str(path).endswith("/")


def output_paths(contract: dict[str,Any]) -> list[str]:
    mode=contract.get("mode")
    explicit=list(contract.get("explicit_output_paths") or [])
    if explicit:
        return explicit[:16]
    artifacts=list(contract.get("artifact_paths") or [])
    if len(artifacts)!=1:
        raise DNAStorageTaskError("AMBIGUOUS_ARTIFACT_OUTPUTS")
    root=artifacts[0]
    if not _is_probably_directory(root):
        return [root]
    if mode=="encode": return [root.rstrip("/")+"/encoded.dna"]
    if mode=="decode": return [root.rstrip("/")+"/decoded.bin"]
    if mode=="implementation": return [root.rstrip("/")+"/dna_storage_codec.py"]
    if mode=="roundtrip": return [root.rstrip("/")+"/encoded.dna",root.rstrip("/")+"/decoded.bin"]
    raise DNAStorageTaskError("OUTPUT_MODE_UNSUPPORTED")


def _safe_file(path: pathlib.Path, output_roots: list[pathlib.Path]) -> bool:
    try:
        p=path.resolve()
        if not p.is_file() or p.stat().st_size<=0 or p.stat().st_size>MAX_INPUT_BYTES:
            return False
        for root in output_roots:
            rr=root.resolve()
            if p==rr or rr in p.parents:
                return False
        return True
    except Exception:
        return False


def discover_inputs(roots: Iterable[str], artifact_paths: Iterable[str]) -> list[pathlib.Path]:
    outputs=[pathlib.Path(x) for x in artifact_paths]
    seen=set(); found=[]
    for raw in roots:
        root=pathlib.Path(raw)
        if not root.exists(): continue
        it=[root] if root.is_file() else root.rglob("*")
        for p in it:
            if not _safe_file(p,outputs): continue
            key=str(p.resolve())
            if key in seen: continue
            seen.add(key); found.append(p.resolve())
            if len(found)>=MAX_INPUT_FILES: return sorted(found)
    return sorted(found)


def _read_oligos(path: pathlib.Path) -> list[str]:
    text=path.read_text(encoding="ascii",errors="ignore")
    stripped=text.strip()
    if path.suffix.lower()==".json" or stripped.startswith(("{","[")):
        try:
            value=json.loads(stripped)
        except Exception:
            value=None
        rows=None
        if isinstance(value,dict):
            rows=value.get("oligos") or value.get("sequences") or value.get("reads")
        elif isinstance(value,list):
            rows=value
        if isinstance(rows,list):
            return [str(x).strip().upper() for x in rows if isinstance(x,str) and str(x).strip()]
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    if lines and len(lines)%4==0 and all(lines[i].startswith("@") for i in range(0,len(lines),4)) and all(lines[i].startswith("+") for i in range(2,len(lines),4)):
        return [re.sub(r"\s+","",lines[i]).upper() for i in range(1,len(lines),4)]
    if any(x.startswith(">") for x in lines):
        records=[]; cur=[]
        for line in lines:
            if line.startswith(">"):
                if cur: records.append("".join(cur).upper()); cur=[]
            else: cur.append(re.sub(r"\s+","",line))
        if cur: records.append("".join(cur).upper())
        return [x for x in records if x]
    out=[]
    for line in lines:
        seq=re.sub(r"\s+","",line).upper()
        if seq and set(seq)<=set("ACGTN"):
            out.append(seq)
    return out


def _dna_score(path: pathlib.Path) -> float:
    if path.suffix.lower() in DNA_SUFFIXES: return 10.0
    if path.suffix.lower()==".json":
        try:
            reads=_read_oligos(path)
            if reads and all(set(x)<=set("ACGTN") for x in reads[:64]):
                return 10.0
        except Exception:
            pass
    try:
        sample=path.read_text(encoding="ascii",errors="ignore")[:20000]
    except Exception: return 0.0
    chars=[c for c in sample.upper() if not c.isspace() and c not in ">0123456789_-.:/ "]
    if not chars: return 0.0
    return sum(c in "ACGTN" for c in chars)/len(chars)


def _choose_input(files:list[pathlib.Path], mode:str, explicit:list[str]) -> pathlib.Path:
    explicit_existing=[pathlib.Path(p) for p in explicit if pathlib.Path(p).is_file()]
    pool=explicit_existing or files
    if not pool: raise DNAStorageTaskError("NO_INPUT_FILES")
    if mode=="decode":
        ranked=sorted(pool,key=lambda p:(-_dna_score(p),str(p)))
        if _dna_score(ranked[0])<0.90: raise DNAStorageTaskError("NO_DNA_INPUT_DETECTED")
        return ranked[0]
    ranked=sorted(pool,key=lambda p:(_dna_score(p)>=0.90,p.suffix.lower() in {".py",".sh"},str(p)))
    return ranked[0]


def _write_oligos(path:pathlib.Path, oligos:list[str]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    ext=path.suffix.lower()
    if ext==".json":
        path.write_text(json.dumps({"oligos":oligos},sort_keys=True)+"\n",encoding="utf-8")
    elif ext in {".fa",".fasta",".fas"}:
        with path.open("w",encoding="ascii") as fh:
            for i,seq in enumerate(oligos): fh.write(f">oligo_{i}\n{seq}\n")
    else:
        path.write_text("\n".join(oligos)+"\n",encoding="ascii")


def execute(payload:dict[str,Any]) -> dict[str,Any]:
    if not isinstance(payload,dict): raise DNAStorageTaskError("PAYLOAD_INVALID")
    instruction=str(payload.get("instruction") or "")
    artifacts=payload.get("artifacts") or []
    if not isinstance(artifacts,list) or any(not isinstance(x,str) for x in artifacts):
        raise DNAStorageTaskError("ARTIFACTS_INVALID")
    contract=classify_contract(instruction,artifacts)
    if not contract["supported"]: raise DNAStorageTaskError("CONTRACT_UNSUPPORTED")
    outs=[pathlib.Path(x) for x in output_paths(contract)]
    roots=payload.get("roots") or ["/root/data","/root","/data","/workspace"]
    if not isinstance(roots,list): raise DNAStorageTaskError("ROOTS_INVALID")
    files=discover_inputs(roots,artifacts)
    mode=contract["mode"]
    receipts=[]
    if mode=="implementation":
        source=pathlib.Path(codec.__file__).read_bytes()
        for out in outs:
            out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(source)
            receipts.append({"path":str(out),"sha256":hashlib.sha256(source).hexdigest(),"bytes":len(source)})
    elif mode=="encode":
        inp=_choose_input(files,mode,list(contract["explicit_input_paths"]))
        oligos=codec.encode_bytes(inp.read_bytes())
        for out in outs:
            _write_oligos(out,oligos)
            receipts.append({"path":str(out),"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size})
    elif mode=="decode":
        inp=_choose_input(files,mode,list(contract["explicit_input_paths"]))
        data=codec.decode_oligos(_read_oligos(inp))
        for out in outs:
            out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(data)
            receipts.append({"path":str(out),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)})
    elif mode=="roundtrip":
        inp=_choose_input(files,"encode",list(contract["explicit_input_paths"]))
        raw=inp.read_bytes(); oligos=codec.encode_bytes(raw); recovered=codec.decode_oligos(oligos)
        if recovered!=raw: raise DNAStorageTaskError("ROUNDTRIP_INTERNAL_MISMATCH")
        enc=next((p for p in outs if p.suffix.lower() in DNA_SUFFIXES|{".txt",".json"}),outs[0])
        dec=next((p for p in outs if p!=enc),None)
        _write_oligos(enc,oligos); receipts.append({"path":str(enc),"sha256":hashlib.sha256(enc.read_bytes()).hexdigest(),"bytes":enc.stat().st_size})
        if dec is not None:
            dec.parent.mkdir(parents=True,exist_ok=True); dec.write_bytes(recovered)
            receipts.append({"path":str(dec),"sha256":hashlib.sha256(recovered).hexdigest(),"bytes":len(recovered)})
    else:
        raise DNAStorageTaskError("MODE_UNSUPPORTED")
    return {
        "schema":SCHEMA,"status":"PASS__DNA_STORAGE_TASK_EXECUTED","mode":mode,
        "contract":contract,"input_file_count":len(files),"artifact_receipts":receipts,
        "model_dependency_count":0,"network_dependency_count":0,"terminal_authority":False,
    }


def main(argv=None) -> int:
    import sys
    argv=list(sys.argv[1:] if argv is None else argv)
    if len(argv)!=1:
        raise SystemExit("usage: dna_storage_task_kernel_v1.py REQUEST.json")
    payload=json.loads(pathlib.Path(argv[0]).read_text(encoding="utf-8"))
    result=execute(payload)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
