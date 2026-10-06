"""Lossless representation/decoder byte accounting.

A smaller serialized payload is a legitimate persistent-storage saving only when
the decoder boundary is explicit. For a self-contained Brain-owned description,
count payload + Brain-owned decoder. If the decoder is a fixed external substrate,
report payload bytes as Brain-owned persistent bytes but retain the decoder as an
explicit substrate dependency.
"""
from __future__ import annotations
import bz2,gzip,lzma,zlib,hashlib

class RepresentationAccountingError(ValueError): pass

def compressed_sizes(raw: bytes)->dict[str,int]:
    if not isinstance(raw,(bytes,bytearray)) or not raw:
        raise RepresentationAccountingError("RAW_BYTES_REQUIRED")
    b=bytes(raw)
    return {
      "raw":len(b),
      "zlib9":len(zlib.compress(b,9)),
      "gzip9":len(gzip.compress(b,compresslevel=9,mtime=0)),
      "bz2_9":len(bz2.compress(b,compresslevel=9)),
      "lzma_xz_9":len(lzma.compress(b,format=lzma.FORMAT_XZ,preset=9)),
      "lzma_alone_9":len(lzma.compress(b,format=lzma.FORMAT_ALONE,preset=9)),
    }

def roundtrip(codec:str, raw:bytes)->dict[str,object]:
    b=bytes(raw)
    if codec=="zlib9": payload=zlib.compress(b,9); restored=zlib.decompress(payload)
    elif codec=="gzip9": payload=gzip.compress(b,compresslevel=9,mtime=0); restored=gzip.decompress(payload)
    elif codec=="bz2_9": payload=bz2.compress(b,compresslevel=9); restored=bz2.decompress(payload)
    elif codec=="lzma_xz_9": payload=lzma.compress(b,format=lzma.FORMAT_XZ,preset=9); restored=lzma.decompress(payload,format=lzma.FORMAT_XZ)
    elif codec=="lzma_alone_9": payload=lzma.compress(b,format=lzma.FORMAT_ALONE,preset=9); restored=lzma.decompress(payload,format=lzma.FORMAT_ALONE)
    else: raise RepresentationAccountingError("CODEC_UNKNOWN")
    return {
      "codec":codec,"payload_bytes":len(payload),"roundtrip_exact":restored==b,
      "raw_sha256":hashlib.sha256(b).hexdigest(),
      "restored_sha256":hashlib.sha256(restored).hexdigest(),
    }

def account(*,payload_bytes:int,brain_owned_decoder_bytes:int,decoder_is_fixed_external_substrate:bool)->dict[str,object]:
    for v,n in ((payload_bytes,"PAYLOAD_BYTES"),(brain_owned_decoder_bytes,"DECODER_BYTES")):
        if not isinstance(v,int) or isinstance(v,bool) or v<0: raise RepresentationAccountingError(n+"_INVALID")
    if not isinstance(decoder_is_fixed_external_substrate,bool):
        raise RepresentationAccountingError("SUBSTRATE_FLAG_INVALID")
    if decoder_is_fixed_external_substrate and brain_owned_decoder_bytes!=0:
        raise RepresentationAccountingError("EXTERNAL_DECODER_CANNOT_ALSO_BE_BRAIN_OWNED")
    self_contained=payload_bytes+brain_owned_decoder_bytes
    return {
      "brain_owned_persistent_payload_bytes":payload_bytes,
      "brain_owned_decoder_bytes":brain_owned_decoder_bytes,
      "self_contained_brain_owned_description_bytes":self_contained,
      "decoder_is_fixed_external_substrate":decoder_is_fixed_external_substrate,
      "external_substrate_dependency_present":decoder_is_fixed_external_substrate,
    }
