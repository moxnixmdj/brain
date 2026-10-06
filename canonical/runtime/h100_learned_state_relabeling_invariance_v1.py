from __future__ import annotations
import base64, hashlib

class RelabelingInvariantError(ValueError): pass

def embed_bytes_as_deterministic_literal(payload:bytes)->str:
    if not isinstance(payload,(bytes,bytearray)) or len(payload)==0:
        raise RelabelingInvariantError("PAYLOAD_INVALID")
    return base64.b85encode(bytes(payload)).decode("ascii")

def recover_embedded_literal(literal:str)->bytes:
    if not isinstance(literal,str) or not literal:
        raise RelabelingInvariantError("LITERAL_INVALID")
    return base64.b85decode(literal.encode("ascii"))

def behavior_preserving_relabel(payload:bytes)->dict:
    literal=embed_bytes_as_deterministic_literal(payload)
    recovered=recover_embedded_literal(literal)
    return {
        "payload_sha256":hashlib.sha256(bytes(payload)).hexdigest(),
        "recovered_sha256":hashlib.sha256(recovered).hexdigest(),
        "behavioral_state_bytes_identical":recovered==bytes(payload),
        "original_learned_bytes":len(payload),
        "relabelled_accounted_learned_bytes":0,
        "deterministic_literal_bytes":len(literal.encode("ascii")),
        "deduction":"LEARNED_BYTE_COUNT_CAN_DROP_TO_ZERO_BY_REPRESENTATION_RELABELING_IF_CAPABILITY_BEARING_DETERMINISTIC_CONSTANTS_ARE_UNCHARGED"
    }

def invariant_accounting_bits(*,learned_bytes:int,deterministic_capability_bytes:int)->int:
    if min(learned_bytes,deterministic_capability_bytes)<0:
        raise RelabelingInvariantError("NEGATIVE_BYTES")
    return 8*(learned_bytes+deterministic_capability_bytes)
