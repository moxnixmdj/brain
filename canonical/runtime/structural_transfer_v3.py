from typing import Any, Iterable, Mapping, Sequence

RELATIONS={"EXACT","PROVEN_STRONGER"}
SURFACE={"LABEL_MATCH","IDENTIFIER_MATCH","NAME_SIMILARITY"}

class StructuralTransferError(ValueError):
    pass

def _receipt(receipt:Mapping[str,Any])->str:
    rid=str(receipt.get("receipt_id") or "").strip()
    if not rid:
        raise StructuralTransferError("RECEIPT_ID_REQUIRED")
    if receipt.get("independent_verified") is not True:
        raise StructuralTransferError("RECEIPT_NOT_INDEPENDENT")
    if receipt.get("exact_byte_bound") is not True:
        raise StructuralTransferError("RECEIPT_NOT_EXACT_BYTE_BOUND")
    if receipt.get("conclusion")!="success":
        raise StructuralTransferError("RECEIPT_NOT_SUCCESS")
    return rid

def admit(mapping:Mapping[str,Any])->dict[str,Any]:
    src=str(mapping.get("source_primitive") or "").strip()
    tgt=str(mapping.get("target_primitive") or "").strip()
    rel=str(mapping.get("relation") or "").strip()
    basis=str(mapping.get("mapping_basis") or "").strip()
    if not src or not tgt:
        raise StructuralTransferError("TRANSFER_PRIMITIVE_REQUIRED")
    if rel not in RELATIONS:
        raise StructuralTransferError("TRANSFER_RELATION_NOT_PROVED")
    if not basis or basis in SURFACE:
        raise StructuralTransferError("SURFACE_ONLY_TRANSFER_FORBIDDEN")
    rec=mapping.get("verification_receipt")
    if not isinstance(rec,Mapping):
        raise StructuralTransferError("TRANSFER_RECEIPT_REQUIRED")
    prov=[str(x).strip() for x in mapping.get("provenance_chain",[]) if str(x).strip()]
    if not prov:
        raise StructuralTransferError("TRANSFER_PROVENANCE_REQUIRED")
    return {
        "source_primitive":src,
        "target_primitive":tgt,
        "relation":rel,
        "mapping_basis":basis,
        "receipt_id":_receipt(rec),
        "provenance_chain":prov,
        "transfer_admitted":True,
    }

def apply(*,verified_facts:Iterable[Any],mappings:Sequence[Mapping[str,Any]])->dict[str,Any]:
    facts={str(x).strip() for x in verified_facts if str(x).strip()}
    admitted=[]
    for raw in mappings:
        m=admit(raw)
        if m["source_primitive"] not in facts:
            raise StructuralTransferError("TRANSFER_SOURCE_NOT_VERIFIED:"+m["source_primitive"])
        facts.add(m["target_primitive"])
        admitted.append(m)
    return {"verified_facts":sorted(facts),"admitted_transfer_mappings":admitted}
