"""Unknown-Domain hidden generator V5: structural IDs plus total string interface.

V4 makes evaluator-visible identifiers structurally distinct even under forced
_token collisions, but it still accepts arbitrary Python beacon strings before
passing them to legacy strict-UTF8 HMAC helpers. V5 preserves V4's evaluator
semantics and identifier construction while canonicalizing every accepted
Python string beacon and string evaluator secret before any legacy path.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as v4

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V5"
BEACON_CANONICALIZATION="UTF8_SURROGATEPASS_BYTES_TO_LOWER_HEX_WITH_V5_PREFIX"
SECRET_CANONICALIZATION="UTF8_SURROGATEPASS_FOR_STR__BYTES_IDENTITY"
STRING_DOMAIN_TOTALITY="TOTAL_FOR_GENUINE_RUNTIME_STR_BYTES_HIERARCHY__CLASS_SPOOF_REJECTED"
IDENTIFIER_TOTALITY="INHERITS_V4_STRUCTURAL_SLOT_ORDINAL_UNIQUENESS"


def _genuine_str(value: Any)->bool:
    # type(value) is the actual runtime class and cannot be spoofed by an
    # instance-level __class__ property. With built-in str as the second
    # argument, issubclass checks the real inheritance chain.
    return issubclass(type(value),str)


def _genuine_bytes(value: Any)->bool:
    return issubclass(type(value),bytes)


def _beacon_gate(beacon: Any)->str:
    if not _genuine_str(beacon) or len(str.strip(beacon))<16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    return beacon


def _canonical_beacon(beacon: Any)->str:
    text=_beacon_gate(beacon)
    raw=str.encode(text,"utf-8","surrogatepass")
    # surrogatepass is total over Python str code-point sequences; hex is a
    # byte-injective ASCII representation, so no legacy strict-UTF8 helper can
    # reject or collapse an accepted beacon after this point.
    return "UDIRV5-BEACON-HEX|"+raw.hex()


def _secret_bytes_total(secret: Any)->bytes:
    if _genuine_bytes(secret):
        # Base-descriptor full slicing materializes exact built-in bytes and
        # bypasses Python overrides on genuine bytes subclasses.
        out=bytes.__getitem__(secret,slice(None))
    elif _genuine_str(secret):
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
