"""Unknown-Domain hidden generator V5: structural IDs plus total reachable string interface.

V4 makes evaluator-visible identifiers structurally distinct even under forced
_token collisions. V5 canonicalizes every genuine runtime str beacon and every
genuine runtime str/bytes evaluator secret before any legacy strict-UTF8 path.

Important: Python isinstance() is deliberately not the authority for this
boundary. Arbitrary proxy objects can spoof __class__ and make isinstance(proxy,
str/bytes) true without carrying the corresponding C-level payload. The frozen
production evaluator supplies textual/byte material, not arbitrary user objects,
so the load-bearing domain is the genuine runtime type hierarchy.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as v4

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V5"
BEACON_CANONICALIZATION="UTF8_SURROGATEPASS_BYTES_TO_LOWER_HEX_WITH_V5_PREFIX"
SECRET_CANONICALIZATION="UTF8_SURROGATEPASS_FOR_STR__BYTES_IDENTITY"
STRING_DOMAIN_TOTALITY="TOTAL_FOR_GENUINE_RUNTIME_STR_HIERARCHY__ISINSTANCE_CLASS_SPOOF_PROXIES_REJECTED"
IDENTIFIER_TOTALITY="INHERITS_V4_STRUCTURAL_SLOT_ORDINAL_UNIQUENESS"
RUNTIME_TYPE_GATE="TYPE_OBJECT_MRO_MEMBERSHIP_VIA_TYPE_BASE_DESCRIPTOR"


def _is_genuine_runtime_instance(value: Any, base: type)->bool:
    """True exactly when the actual runtime class inherits from base.

    type(value) cannot be spoofed by an instance __class__ property. Reading the
    class MRO through type.__getattribute__ also bypasses user metaclass attribute
    hooks. For built-in bases str and bytes, membership therefore captures the
    genuine runtime hierarchy while retaining real subclasses.
    """
    actual_type=type(value)
    try:
        mro=type.__getattribute__(actual_type,"__mro__")
    except (TypeError, AttributeError):
        return False
    return base in mro


def _beacon_gate(beacon: Any)->str:
    if not _is_genuine_runtime_instance(beacon,str):
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    if len(str.strip(beacon))<16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    return beacon


def _canonical_beacon(beacon: Any)->str:
    text=_beacon_gate(beacon)
    raw=str.encode(text,"utf-8","surrogatepass")
    return "UDIRV5-BEACON-HEX|"+raw.hex()


def _secret_bytes_total(secret: Any)->bytes:
    if _is_genuine_runtime_instance(secret,bytes):
        # Base descriptor on a full slice reads the inherited immutable payload,
        # bypassing Python-level bytes subclass hooks and returning exact bytes.
        out=bytes.__getitem__(secret,slice(None))
    elif _is_genuine_runtime_instance(secret,str):
        out=str.encode(secret,"utf-8","surrogatepass")
    else:
        raise v1.UnknownDomainGeneratorError("EVALUATOR_SECRET_INVALID")
    if len(out)<32:
        raise v1.UnknownDomainGeneratorError("EVALUATOR_SECRET_TOO_SHORT")
    return out


def _generate(*,beacon:str,evaluator_secret:Any,namespace:str):
    canonical_beacon=_canonical_beacon(beacon)
    secret=_secret_bytes_total(evaluator_secret)
    out=v4._generate(
        beacon=canonical_beacon,
        evaluator_secret=secret,
        namespace=namespace,
    )
    out["schema"]=SCHEMA
    out["beacon_canonicalization"]=BEACON_CANONICALIZATION
    out["secret_canonicalization"]=SECRET_CANONICALIZATION
    out["string_domain_totality"]=STRING_DOMAIN_TOTALITY
    out["identifier_totality"]=IDENTIFIER_TOTALITY
    out["runtime_type_gate"]=RUNTIME_TYPE_GATE
    return out


def generate_production_population(*,beacon:str,evaluator_secret:Any,authority:Mapping[str,Any]):
    v1._production_authorized(authority)
    out=_generate(
        beacon=beacon,
        evaluator_secret=evaluator_secret,
        namespace="UDIR5",
    )
    out["authority_claim_id"]=str(authority["one_use_claim_id"])
    out["production"]=True
    return out


def generate_qualification_fixture_population(*,beacon:str):
    out=_generate(
        beacon=beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-V5-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY5",
    )
    out["production"]=False
    out["hard_nonclaim"]="QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
