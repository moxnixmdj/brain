"""Unknown-Domain hidden generator V5: structural IDs plus total string interface.

V4 makes evaluator-visible identifiers structurally distinct even under forced
_token collisions. V5 preserves V4 evaluator semantics while canonicalizing the
exact built-in str/bytes domain emitted by the frozen production launcher before
any legacy strict-UTF8 HMAC path. The gate intentionally rejects Python objects
that merely spoof isinstance membership through __class__.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as v4

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V5"
BEACON_CANONICALIZATION="UTF8_SURROGATEPASS_BYTES_TO_LOWER_HEX_WITH_V5_PREFIX"
SECRET_CANONICALIZATION="UTF8_SURROGATEPASS_FOR_STR__BYTES_IDENTITY"
STRING_DOMAIN_TOTALITY="TOTAL_FOR_FROZEN_PRODUCTION_LAUNCHER_EXACT_BUILTIN_STR_BYTES_DOMAIN"
IDENTIFIER_TOTALITY="INHERITS_V4_STRUCTURAL_SLOT_ORDINAL_UNIQUENESS"


def _beacon_gate(beacon: Any)->str:
    # The frozen production launcher constructs the beacon as an exact built-in
    # str. Do not widen that reachable domain with spoofable isinstance semantics.
    if type(beacon) is not str or len(str.strip(beacon))<16:
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
    # The frozen production launcher constructs the evaluator secret with
    # secrets.token_bytes(32), which is exact built-in bytes. Exact built-in str
    # remains accepted for deterministic nonproduction qualification fixtures.
    # Reject proxy/subclass widening instead of pretending isinstance defines the
    # production domain.
    if type(secret) is bytes:
        out=secret
    elif type(secret) is str:
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
