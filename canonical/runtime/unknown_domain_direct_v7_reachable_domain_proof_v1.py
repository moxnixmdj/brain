"""Successor proof for the Unknown-Domain direct evaluator after class-spoof falsification.

This proof removes an accidental Python-object overquantification. The evaluator
needs genuine runtime str/bytes values. It does not need to accept arbitrary
objects whose instance __class__ property merely makes isinstance() lie.

The valid V6 transfer, identifier, and abstention lemmas are reused from their
exact frozen source. The invalid V6 isinstance-domain theorem is not reused.
No production or terminal case is generated here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as v6

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V7_REACHABLE_RUNTIME_DOMAIN_PROOF_V1"
STATUS="PASS__GENUINE_RUNTIME_TYPE_DOMAIN_TOTAL__CLASS_SPOOF_EXCLUDED__V6_TRANSFER_IDENTIFIER_ABSTENTION_LEMMAS_RETAINED"

EXPECTED_BLOBS={
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py":"34b5b78844cef95442c4a640c1ea24378d2fd48c",
    "canonical/tests/test_unknown_domain_direct_v5.py":"7270b90b9844d9806c0952887aaa328573d98710",
    "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py":"58d3a61f5e2cb24b4387ddd817b64f897f62fe06",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}


def _git_blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _root()->Path:
    return Path(__file__).resolve().parents[2]


def _verify_bindings(root:Path)->dict[str,str]:
    got={rel:_git_blob_sha(root/rel) for rel in EXPECTED_BLOBS}
    bad={rel:{"expected":EXPECTED_BLOBS[rel],"got":got[rel]}
         for rel in EXPECTED_BLOBS if got[rel]!=EXPECTED_BLOBS[rel]}
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:"+repr(bad))
    return got


class _RealAdversarialStr(str):
    @property
    def __class__(self):
        raise RuntimeError("INSTANCE_CLASS_HOOK_MUST_NOT_RUN")

    def strip(self,*args,**kwargs):
        raise RuntimeError("INSTANCE_STRIP_MUST_NOT_RUN")

    def encode(self,*args,**kwargs):
        raise RuntimeError("INSTANCE_ENCODE_MUST_NOT_RUN")


class _RealAdversarialBytes(bytes):
    @property
    def __class__(self):
        raise RuntimeError("INSTANCE_CLASS_HOOK_MUST_NOT_RUN")

    def __bytes__(self):
        raise RuntimeError("INSTANCE_BYTES_MUST_NOT_RUN")

    def __buffer__(self,*args,**kwargs):
        raise RuntimeError("INSTANCE_BUFFER_MUST_NOT_RUN")

    def __len__(self):
        raise RuntimeError("INSTANCE_LEN_MUST_NOT_RUN")

    def __getitem__(self,*args,**kwargs):
        raise RuntimeError("INSTANCE_GETITEM_MUST_NOT_RUN")


class _FakeStr:
    @property
    def __class__(self):
        return str


class _FakeBytes:
    @property
    def __class__(self):
        return bytes


def _expect_reject(fn,code:str)->None:
    try:
        fn()
    except Exception as exc:
        assert exc.__class__.__name__=="UnknownDomainGeneratorError"
        assert str(exc)==code
    else:
        raise AssertionError("EXPECTED_REJECTION:"+code)


def _runtime_domain_theorem()->dict[str,Any]:
    fake_str=_FakeStr()
    fake_bytes=_FakeBytes()
    assert isinstance(fake_str,str) is True
    assert isinstance(fake_bytes,bytes) is True
    assert g5._is_genuine_runtime_instance(fake_str,str) is False
    assert g5._is_genuine_runtime_instance(fake_bytes,bytes) is False
    _expect_reject(lambda:g5._canonical_beacon(fake_str),"POST_FREEZE_BEACON_INVALID")
    _expect_reject(lambda:g5._secret_bytes_total(fake_str),"EVALUATOR_SECRET_INVALID")
    _expect_reject(lambda:g5._secret_bytes_total(fake_bytes),"EVALUATOR_SECRET_INVALID")

    real_str=_RealAdversarialStr("A"*16+"\ud800")
    real_secret_str=_RealAdversarialStr("S"*31+"\udfff")
    real_bytes=_RealAdversarialBytes(b"B"*32)
    assert g5._is_genuine_runtime_instance(real_str,str) is True
    assert g5._is_genuine_runtime_instance(real_secret_str,str) is True
    assert g5._is_genuine_runtime_instance(real_bytes,bytes) is True
    assert g5._canonical_beacon(real_str).isascii()
    assert len(g5._secret_bytes_total(real_secret_str))>=32
    assert g5._secret_bytes_total(real_bytes)==b"B"*32

    seen=set()
    for cp in range(0xD800,0xE000):
        out=g5._canonical_beacon("A"*16+chr(cp))
        assert out.isascii()
        seen.add(out)
    assert len(seen)==0x800

    return {
        "runtime_type_gate":g5.RUNTIME_TYPE_GATE,
        "genuine_str_subclasses_retained":True,
        "genuine_bytes_subclasses_retained":True,
        "instance_class_spoof_str_rejected":True,
        "instance_class_spoof_bytes_rejected":True,
        "surrogate_codepoints_exhausted":2048,
        "beacon_domain":"GENUINE_RUNTIME_STR_HIERARCHY_WITH_BASE_STRIP_LENGTH_GE_16",
        "secret_domain":"GENUINE_RUNTIME_STR_OR_BYTES_HIERARCHY_WITH_CANONICAL_BYTE_LENGTH_GE_32",
        "isinstance_spoofable_object_domain_authoritative":False,
    }


def prove(root:Path|None=None)->dict[str,Any]:
    root=_root() if root is None else Path(root).resolve()
    bindings=_verify_bindings(root)
    runtime_domain=_runtime_domain_theorem()

    # Reuse only the exact V6 lemmas untouched by the falsified Python-object
    # boundary theorem. Do not call v6._string_totality() or v6.prove().
    identifiers=v6._identifier_totality()
    transfer=v6._transfer_theorem()
    abstention=v6._abstention_theorem()

    return {
        "schema":SCHEMA,
        "status":STATUS,
        "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs":bindings,
        "runtime_input_domain":runtime_domain,
        "identifier_totality_proof":identifiers,
        "transfer_proof":transfer,
        "abstention_proof":abstention,
        "falsified_v6_component_reused":False,
        "retained_v6_components":[
            "IDENTIFIER_TOTALITY",
            "TRANSFER_THEOREM",
            "ABSTENTION_THEOREM",
        ],
        "required_external_binding_before_acceptance":[
            "PRODUCTION_BEACON_ORIGIN_IS_GENUINE_RUNTIME_STR",
            "EVALUATOR_SECRET_ORIGIN_IS_GENUINE_RUNTIME_STR_OR_BYTES",
            "INDEPENDENT_CONTENT_BOUND_EXECUTION_OF_THIS_EXACT_PROOF_AND_TEST_SET",
        ],
        "hard_nonclaims":[
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_SOURCE_PROOF_ALONE",
            "NO CLAIM_THAT_ARBITRARY_ISINSTANCE_SPOOFABLE_OBJECTS_ARE_STRING_OR_BYTES_PAYLOADS",
            "NO PRODUCTION_OR TERMINAL CASE GENERATED_READ_OR_CONSUMED",
            "NO MYSTERYMECHANISM CREDIT",
        ],
        "accounting":{
            "incremental_spend_usd":0,
            "new_reality_units_consumed":0,
            "terminal_cases_consumed":0,
            "production_cases_generated":0,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        },
    }


if __name__=="__main__":
    import json
    print(json.dumps(prove(),indent=2,sort_keys=True,ensure_ascii=True))
