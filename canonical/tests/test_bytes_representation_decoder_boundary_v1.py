from canonical.runtime.bytes_representation_decoder_boundary_v1 import compressed_sizes,roundtrip,account,RepresentationAccountingError

RAW=(b"abc123"*1000)+bytes(range(256))*5

def test_all_codecs_roundtrip_exact():
    for c in ("zlib9","gzip9","bz2_9","lzma_xz_9","lzma_alone_9"):
        out=roundtrip(c,RAW)
        assert out["roundtrip_exact"] is True
        assert out["raw_sha256"]==out["restored_sha256"]

def test_compression_is_representation_not_free_decoder():
    s=compressed_sizes(RAW)
    assert min(v for k,v in s.items() if k!="raw") < s["raw"]
    external=account(payload_bytes=4000,brain_owned_decoder_bytes=0,decoder_is_fixed_external_substrate=True)
    assert external["brain_owned_persistent_payload_bytes"]==4000
    assert external["external_substrate_dependency_present"] is True
    owned=account(payload_bytes=4000,brain_owned_decoder_bytes=900,decoder_is_fixed_external_substrate=False)
    assert owned["self_contained_brain_owned_description_bytes"]==4900

def test_fail_closed_double_classification():
    try: account(payload_bytes=1,brain_owned_decoder_bytes=1,decoder_is_fixed_external_substrate=True)
    except RepresentationAccountingError as e: assert str(e)=="EXTERNAL_DECODER_CANNOT_ALSO_BE_BRAIN_OWNED"
    else: raise AssertionError("expected fail closed")
