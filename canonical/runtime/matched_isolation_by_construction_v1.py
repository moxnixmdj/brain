from __future__ import annotations
from typing import Any,Mapping

REQ=(
"fresh_private_namespace_per_case",
"read_only_content_addressed_case_input",
"identical_brain_and_future_comparator_initial_input",
"private_writable_scratch_only",
"no_shared_writable_mount_or_device",
"no_undeclared_inherited_fd",
"no_host_network",
"no_external_material_broker_effects",
"no_durable_persistence_channel",
"no_prior_case_result_or_mutable_state_input",
"namespace_destroyed_after_case",
"no_result_dependent_case_generation",
"no_result_dependent_runtime_mutation",
)

def compile_isolation_by_construction(doc:Mapping[str,Any])->dict[str,Any]:
    missing=[k for k in REQ if doc.get(k) is not True]
    if missing:
        return {"status":"FAIL_CLOSED","pass":False,"missing":missing,"matched_isolation_implied":False}
    ids=doc.get("case_ids")
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):
        return {"status":"FAIL_CLOSED","pass":False,"missing":["UNIQUE_NONEMPTY_CASE_IDS"],"matched_isolation_implied":False}
    namespaces=doc.get("namespace_ids")
    if not isinstance(namespaces,list) or len(namespaces)!=len(ids) or len(namespaces)!=len(set(namespaces)):
        return {"status":"FAIL_CLOSED","pass":False,"missing":["UNIQUE_NAMESPACE_PER_CASE"],"matched_isolation_implied":False}
    return {
      "status":"PASS__MATCHED_CASE_ISOLATION_BY_CONSTRUCTION",
      "pass":True,
      "case_count":len(ids),
      "matched_isolation_implied":True,
      "residual_only_comparator_counterfactual_preserved":True,
      "external_mutable_service_reset_receipts_required":False,
      "per_case_reset_equivalence_receipts_required":False,
      "reason":"NO_CROSS_CASE_MUTABLE_CARRIER_EXISTS_AND_EACH_CASE_STARTS_IN_A_FRESH_PRIVATE_NAMESPACE_FROM_CONTENT_ADDRESSED_READ_ONLY_INPUT",
      "execution_authority":False,"fresh_reality_authority":False,"promotion_authority":False,
      "terminal_credit_delta":0
    }
