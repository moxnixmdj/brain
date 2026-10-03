from typing import Any, Iterable, Mapping, Sequence

RELATIONS={"EXACT","PROVEN_STRONGER"}
BASES={"STRUCTURAL_EQUIVALENCE","CAUSAL_ISOMORPHISM","FORMAL_REDUCTION","PROTOCOL_EQUIVALENCE"}

class StructuralTransferError(ValueError):
    pass

def _receipt(receipt:Mapping[str,Any],*,source:str,target:str,relation:str,basis:str)->str:
    rid=str(receipt.get("receipt_id") or "").strip()
    if not rid:
        raise StructuralTransferError("RECEIPT_ID_REQUIRED")
    if receipt.get("independent_verified") is not True:
        raise StructuralTransferError("RECEIPT_NOT_INDEPENDENT")
    if receipt.get("exact_byte_bound") is not True:
        raise StructuralTransferError("RECEIPT_NOT_EXACT_BYTE_BOUND")
    if receipt.get("conclusion")!="success":
        raise StructuralTransferError("RECEIPT_NOT_SUCCESS")
    bound={
        "source_primitive":str(receipt.get("source_primitive") or "").strip(),
        "target_primitive":str(receipt.get("target_primitive") or "").strip(),
        "relation":str(receipt.get("relation") or "").strip(),
        "mapping_basis":str(receipt.get("mapping_basis") or "").strip(),
    }
    expected={
        "source_primitive":source,
        "target_primitive":target,
        "relation":relation,
        "mapping_basis":basis,
    }
    if bound!=expected:
        raise StructuralTransferError("RECEIPT_MAPPING_BINDING_MISMATCH")
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
    if basis not in BASES:
        raise StructuralTransferError("TRANSFER_MAPPING_BASIS_NOT_ADMISSIBLE")
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
        "receipt_id":_receipt(rec,source=src,target=tgt,relation=rel,basis=basis),
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
