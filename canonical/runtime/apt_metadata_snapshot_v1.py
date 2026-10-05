from __future__ import annotations

import hashlib
import os
import pathlib
import struct
from collections.abc import Iterable, Iterator
from typing import Any

SCHEMA="PROJECT_BRAIN_APT_METADATA_SNAPSHOT_V1"
LZ4_MAGIC=0x184D2204
XXH32_PRIME1=0x9E3779B1
XXH32_PRIME2=0x85EBCA77
XXH32_PRIME3=0xC2B2AE3D
XXH32_PRIME4=0x27D4EB2F
XXH32_PRIME5=0x165667B1


class AptSnapshotError(RuntimeError):
    pass


def _rotl32(x:int,r:int)->int:
    return ((x << r) | (x >> (32-r))) & 0xFFFFFFFF


def xxh32(data:bytes, seed:int=0)->int:
    data=bytes(data)
    n=len(data)
    i=0
    if n>=16:
        v1=(seed+XXH32_PRIME1+XXH32_PRIME2)&0xFFFFFFFF
        v2=(seed+XXH32_PRIME2)&0xFFFFFFFF
        v3=seed&0xFFFFFFFF
        v4=(seed-XXH32_PRIME1)&0xFFFFFFFF
        limit=n-16
        while i<=limit:
            for which in range(4):
                lane=int.from_bytes(data[i:i+4],"little"); i+=4
                if which==0:
                    v1=(v1+lane*XXH32_PRIME2)&0xFFFFFFFF
                    v1=(_rotl32(v1,13)*XXH32_PRIME1)&0xFFFFFFFF
                elif which==1:
                    v2=(v2+lane*XXH32_PRIME2)&0xFFFFFFFF
                    v2=(_rotl32(v2,13)*XXH32_PRIME1)&0xFFFFFFFF
                elif which==2:
                    v3=(v3+lane*XXH32_PRIME2)&0xFFFFFFFF
                    v3=(_rotl32(v3,13)*XXH32_PRIME1)&0xFFFFFFFF
                else:
                    v4=(v4+lane*XXH32_PRIME2)&0xFFFFFFFF
                    v4=(_rotl32(v4,13)*XXH32_PRIME1)&0xFFFFFFFF
        h=(_rotl32(v1,1)+_rotl32(v2,7)+_rotl32(v3,12)+_rotl32(v4,18))&0xFFFFFFFF
    else:
        h=(seed+XXH32_PRIME5)&0xFFFFFFFF
    h=(h+n)&0xFFFFFFFF
    while i+4<=n:
        lane=int.from_bytes(data[i:i+4],"little"); i+=4
        h=(h+lane*XXH32_PRIME3)&0xFFFFFFFF
        h=(_rotl32(h,17)*XXH32_PRIME4)&0xFFFFFFFF
    while i<n:
        h=(h+data[i]*XXH32_PRIME5)&0xFFFFFFFF
        h=(_rotl32(h,11)*XXH32_PRIME1)&0xFFFFFFFF
        i+=1
    h ^= h >> 15
    h=(h*XXH32_PRIME2)&0xFFFFFFFF
    h ^= h >> 13
    h=(h*XXH32_PRIME3)&0xFFFFFFFF
    h ^= h >> 16
    return h & 0xFFFFFFFF


def _read_len(block:bytes, i:int, base:int)->tuple[int,int]:
    length=base
    if base==15:
        while True:
            if i>=len(block):
                raise AptSnapshotError("LZ4_LENGTH_TRUNCATED")
            b=block[i]; i+=1
            length+=b
            if b!=255:
                break
    return length,i


def _decode_block(block:bytes, dictionary:bytes=b"")->bytes:
    out=bytearray(dictionary[-65536:])
    base=len(out)
    i=0
    while i<len(block):
        token=block[i]; i+=1
        lit,i=_read_len(block,i,token>>4)
        if i+lit>len(block):
            raise AptSnapshotError("LZ4_LITERAL_TRUNCATED")
        out.extend(block[i:i+lit]); i+=lit
        if i==len(block):
            break
        if i+2>len(block):
            raise AptSnapshotError("LZ4_OFFSET_TRUNCATED")
        offset=block[i] | (block[i+1]<<8); i+=2
        if offset<=0 or offset>len(out):
            raise AptSnapshotError("LZ4_OFFSET_INVALID")
        mlen,i=_read_len(block,i,token&0x0F)
        mlen+=4
        src=len(out)-offset
        if src<0:
            raise AptSnapshotError("LZ4_MATCH_SOURCE_INVALID")
        if mlen<=offset:
            out.extend(out[src:src+mlen])
        else:
            pattern=bytes(out[src:src+offset])
            if len(pattern)!=offset:
                raise AptSnapshotError("LZ4_MATCH_SOURCE_INVALID")
            repeats=(mlen+offset-1)//offset
            out.extend((pattern*repeats)[:mlen])
    return bytes(out[base:])


def decompress_lz4_frame(raw:bytes, *, max_output_bytes:int=1_500_000_000)->bytes:
    raw=bytes(raw)
    if len(raw)<7:
        raise AptSnapshotError("LZ4_FRAME_TOO_SHORT")
    if int.from_bytes(raw[:4],"little")!=LZ4_MAGIC:
        raise AptSnapshotError("LZ4_MAGIC_INVALID")
    pos=4
    flg=raw[pos]; bd=raw[pos+1]; pos+=2
    if (flg>>6)!=1 or (flg & 0x02):
        raise AptSnapshotError("LZ4_FRAME_FLAGS_INVALID")
    independent=bool(flg & 0x20)
    block_checksum=bool(flg & 0x10)
    content_size_flag=bool(flg & 0x08)
    content_checksum=bool(flg & 0x04)
    dict_id_flag=bool(flg & 0x01)
    descriptor=bytearray([flg,bd])
    declared_size=None
    if content_size_flag:
        if pos+8>len(raw): raise AptSnapshotError("LZ4_CONTENT_SIZE_TRUNCATED")
        declared_size=int.from_bytes(raw[pos:pos+8],"little")
        descriptor.extend(raw[pos:pos+8]); pos+=8
    if dict_id_flag:
        if pos+4>len(raw): raise AptSnapshotError("LZ4_DICT_ID_TRUNCATED")
        descriptor.extend(raw[pos:pos+4]); pos+=4
    if pos>=len(raw): raise AptSnapshotError("LZ4_HEADER_CHECKSUM_MISSING")
    hc=raw[pos]; pos+=1
    if ((xxh32(bytes(descriptor))>>8)&0xFF)!=hc:
        raise AptSnapshotError("LZ4_HEADER_CHECKSUM_MISMATCH")

    out=bytearray()
    while True:
        if pos+4>len(raw): raise AptSnapshotError("LZ4_BLOCK_HEADER_TRUNCATED")
        size_word=int.from_bytes(raw[pos:pos+4],"little"); pos+=4
        if size_word==0:
            break
        uncompressed=bool(size_word & 0x80000000)
        size=size_word & 0x7FFFFFFF
        if size<=0 or pos+size>len(raw):
            raise AptSnapshotError("LZ4_BLOCK_SIZE_INVALID")
        payload=raw[pos:pos+size]; pos+=size
        if block_checksum:
            if pos+4>len(raw): raise AptSnapshotError("LZ4_BLOCK_CHECKSUM_TRUNCATED")
            expected=int.from_bytes(raw[pos:pos+4],"little"); pos+=4
            if xxh32(payload)!=expected:
                raise AptSnapshotError("LZ4_BLOCK_CHECKSUM_MISMATCH")
        if uncompressed:
            chunk=payload
        else:
            chunk=_decode_block(payload,b"" if independent else bytes(out[-65536:]))
        out.extend(chunk)
        if len(out)>max_output_bytes:
            raise AptSnapshotError("LZ4_OUTPUT_LIMIT_EXCEEDED")

    if content_checksum:
        if pos+4>len(raw): raise AptSnapshotError("LZ4_CONTENT_CHECKSUM_TRUNCATED")
        expected=int.from_bytes(raw[pos:pos+4],"little"); pos+=4
        if xxh32(bytes(out))!=expected:
            raise AptSnapshotError("LZ4_CONTENT_CHECKSUM_MISMATCH")
    if declared_size is not None and len(out)!=declared_size:
        raise AptSnapshotError("LZ4_CONTENT_SIZE_MISMATCH")
    if pos!=len(raw):
        raise AptSnapshotError("LZ4_TRAILING_BYTES")
    return bytes(out)


def iter_lz4_frame_chunks(raw:bytes, *, max_output_bytes:int=1_500_000_000)->Iterator[bytes]:
    raw=bytes(raw)
    if len(raw)<7 or int.from_bytes(raw[:4],"little")!=LZ4_MAGIC:
        raise AptSnapshotError("LZ4_MAGIC_INVALID")
    pos=4
    flg=raw[pos]; bd=raw[pos+1]; pos+=2
    if (flg>>6)!=1 or (flg & 0x02):
        raise AptSnapshotError("LZ4_FRAME_FLAGS_INVALID")
    independent=bool(flg & 0x20)
    block_checksum=bool(flg & 0x10)
    content_size_flag=bool(flg & 0x08)
    content_checksum=bool(flg & 0x04)
    dict_id_flag=bool(flg & 0x01)
    if content_checksum:
        yield decompress_lz4_frame(raw,max_output_bytes=max_output_bytes)
        return
    descriptor=bytearray([flg,bd])
    declared_size=None
    if content_size_flag:
        if pos+8>len(raw): raise AptSnapshotError("LZ4_CONTENT_SIZE_TRUNCATED")
        declared_size=int.from_bytes(raw[pos:pos+8],"little")
        descriptor.extend(raw[pos:pos+8]); pos+=8
    if dict_id_flag:
        if pos+4>len(raw): raise AptSnapshotError("LZ4_DICT_ID_TRUNCATED")
        descriptor.extend(raw[pos:pos+4]); pos+=4
    if pos>=len(raw): raise AptSnapshotError("LZ4_HEADER_CHECKSUM_MISSING")
    hc=raw[pos]; pos+=1
    if ((xxh32(bytes(descriptor))>>8)&0xFF)!=hc:
        raise AptSnapshotError("LZ4_HEADER_CHECKSUM_MISMATCH")
    history=b""
    total=0
    while True:
        if pos+4>len(raw): raise AptSnapshotError("LZ4_BLOCK_HEADER_TRUNCATED")
        size_word=int.from_bytes(raw[pos:pos+4],"little"); pos+=4
        if size_word==0:
            break
        uncompressed=bool(size_word & 0x80000000)
        size=size_word & 0x7FFFFFFF
        if size<=0 or pos+size>len(raw):
            raise AptSnapshotError("LZ4_BLOCK_SIZE_INVALID")
        payload=raw[pos:pos+size]; pos+=size
        if block_checksum:
            if pos+4>len(raw): raise AptSnapshotError("LZ4_BLOCK_CHECKSUM_TRUNCATED")
            expected=int.from_bytes(raw[pos:pos+4],"little"); pos+=4
            if xxh32(payload)!=expected:
                raise AptSnapshotError("LZ4_BLOCK_CHECKSUM_MISMATCH")
        chunk=payload if uncompressed else _decode_block(payload,b"" if independent else history)
        total+=len(chunk)
        if total>max_output_bytes:
            raise AptSnapshotError("LZ4_OUTPUT_LIMIT_EXCEEDED")
        history=(history+chunk)[-65536:]
        yield chunk
    if declared_size is not None and total!=declared_size:
        raise AptSnapshotError("LZ4_CONTENT_SIZE_MISMATCH")
    if pos!=len(raw):
        raise AptSnapshotError("LZ4_TRAILING_BYTES")


def iter_apt_index_lines(
    path:str|os.PathLike[str],
    *,
    max_output_bytes:int=1_500_000_000,
)->Iterator[str]:
    p=pathlib.Path(path)
    name=p.name.lower()
    pending=b""
    if name.endswith(".lz4"):
        chunks=iter_lz4_frame_chunks(p.read_bytes(),max_output_bytes=max_output_bytes)
        for chunk in chunks:
            pending+=chunk
            parts=pending.split(b"\n")
            pending=parts.pop()
            for line in parts:
                yield line.decode("utf-8","replace")
    else:
        raw=read_apt_index(p,max_output_bytes=max_output_bytes)
        for line in raw.splitlines():
            yield line.decode("utf-8","replace")
    if pending:
        yield pending.decode("utf-8","replace")


def read_apt_index(path:str|os.PathLike[str], *, max_output_bytes:int=1_500_000_000)->bytes:
    p=pathlib.Path(path)
    raw=p.read_bytes()
    name=p.name.lower()
    if name.endswith(".lz4"):
        return decompress_lz4_frame(raw,max_output_bytes=max_output_bytes)
    if name.endswith(".gz"):
        import gzip
        out=gzip.decompress(raw)
    elif name.endswith(".xz"):
        import lzma
        out=lzma.decompress(raw)
    else:
        out=raw
    if len(out)>max_output_bytes:
        raise AptSnapshotError("APT_INDEX_OUTPUT_LIMIT_EXCEEDED")
    return out


def parse_deb822_records(text:str)->list[dict[str,str]]:
    records=[]
    current:dict[str,str]={}
    last=None
    for raw in str(text or "").splitlines()+[""]:
        if not raw.strip():
            if current:
                records.append(current)
            current={}
            last=None
            continue
        if raw[:1].isspace() and last:
            current[last]=current.get(last,"")+"\n"+raw[1:]
            continue
        if ":" not in raw:
            continue
        key,value=raw.split(":",1)
        last=key.strip()
        current[last]=value.lstrip()
    return records


def apt_index_target_files(
    lists_dir:str|os.PathLike[str]="/var/lib/apt/lists",
    *,
    identifier:str|None=None,
    language:str|None=None,
)->list[str]:
    root=pathlib.Path(lists_dir)
    if not root.is_dir():
        return []
    out=[]
    for p in sorted(root.iterdir(),key=lambda x:x.name):
        if not p.is_file() or p.name=="lock":
            continue
        n=p.name
        ok=True
        if identifier:
            if identifier=="Translations":
                ok="_i18n_Translation-" in n
            elif identifier.startswith("Contents"):
                ok="_Contents-" in n
            elif identifier=="Packages":
                ok="_binary-" in n and "_Packages" in n
            else:
                ok=False
        if ok and language:
            ok=("_Translation-"+str(language)) in n
        if ok:
            out.append(str(p))
    return out


def package_records(
    lists_dir:str|os.PathLike[str]="/var/lib/apt/lists",
    *,
    max_total_output_bytes:int=1_500_000_000,
)->list[dict[str,str]]:
    total=0
    out=[]
    files=apt_index_target_files(lists_dir,identifier="Packages")
    for path in files:
        raw=read_apt_index(path,max_output_bytes=max_total_output_bytes-total)
        total+=len(raw)
        if total>max_total_output_bytes:
            raise AptSnapshotError("PACKAGE_INDEX_TOTAL_OUTPUT_LIMIT_EXCEEDED")
        out.extend(parse_deb822_records(raw.decode("utf-8","replace")))
    return out


def translation_records(
    lists_dir:str|os.PathLike[str]="/var/lib/apt/lists",
    *,
    language:str="en",
    max_total_output_bytes:int=1_500_000_000,
)->list[dict[str,str]]:
    total=0
    out=[]
    files=apt_index_target_files(lists_dir,identifier="Translations",language=language)
    for path in files:
        raw=read_apt_index(path,max_output_bytes=max_total_output_bytes-total)
        total+=len(raw)
        if total>max_total_output_bytes:
            raise AptSnapshotError("TRANSLATION_INDEX_TOTAL_OUTPUT_LIMIT_EXCEEDED")
        out.extend(parse_deb822_records(raw.decode("utf-8","replace")))
    return out


def executable_owners(
    lists_dir:str|os.PathLike[str]="/var/lib/apt/lists",
    *,
    max_total_output_bytes:int=1_500_000_000,
)->dict[str,list[str]]:
    owners:dict[str,list[str]]={}
    total=0
    files=apt_index_target_files(lists_dir,identifier="Contents")
    for path in files:
        compressed_bytes=pathlib.Path(path).stat().st_size
        total+=compressed_bytes
        if total>max_total_output_bytes:
            raise AptSnapshotError("CONTENTS_COMPRESSED_INPUT_LIMIT_EXCEEDED")
        for line in iter_apt_index_lines(path,max_output_bytes=max_total_output_bytes):
            if not line:
                continue
            try:
                filename,raw_owners=line.rsplit(None,1)
            except ValueError:
                continue
            normalized=filename.lstrip("/")
            if not normalized.startswith("usr/bin/"):
                continue
            executable="/"+normalized
            for raw_owner in raw_owners.split(","):
                owner=raw_owner.strip().rsplit("/",1)[-1].split(":",1)[0]
                if not owner:
                    continue
                bucket=owners.setdefault(owner,[])
                if executable not in bucket:
                    bucket.append(executable)
    return owners


def installed_version(
    package:str,
    status_path:str|os.PathLike[str]="/var/lib/dpkg/status",
)->str|None:
    package=str(package or "").strip()
    if not package or any(ch.isspace() for ch in package):
        raise AptSnapshotError("PACKAGE_NAME_INVALID")
    records=parse_deb822_records(pathlib.Path(status_path).read_text(encoding="utf-8",errors="replace"))
    matches=[]
    for rec in records:
        if rec.get("Package")!=package:
            continue
        if rec.get("Status")!="install ok installed":
            continue
        v=str(rec.get("Version") or "").strip()
        if v:
            matches.append(v)
    uniq=sorted(set(matches))
    if not uniq:
        return None
    if len(uniq)!=1:
        raise AptSnapshotError("MULTIPLE_INSTALLED_VERSIONS:"+package)
    return uniq[0]


def snapshot_manifest(
    lists_dir:str|os.PathLike[str]="/var/lib/apt/lists",
    status_path:str|os.PathLike[str]="/var/lib/dpkg/status",
)->dict[str,Any]:
    files=[]
    root=pathlib.Path(lists_dir)
    for p in sorted(root.iterdir(),key=lambda x:x.name):
        if p.is_file() and p.name!="lock":
            raw=p.read_bytes()
            files.append({"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
    status=pathlib.Path(status_path)
    sraw=status.read_bytes()
    return {
        "schema":SCHEMA,
        "lists_dir":str(root),
        "list_file_count":len(files),
        "list_files":files,
        "status_path":str(status),
        "status_bytes":len(sraw),
        "status_sha256":hashlib.sha256(sraw).hexdigest(),
    }
