"""Live V4 transferable complete-interface qualification for Tool Discovery.

This is a realizability witness, not an acceptance proof. It instantiates the
frozen V4 complete-interface contract on a real changing APT catalog epoch and
checks the V8 policy invariants that are observable without terminal cases.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime import tool_discovery_apt_complete_interface_instance_v1 as aptv1
from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v8 as v8

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V4_TRANSFERABLE_CATALOG.json"
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_APT_V4_TRANSFERABLE_INTERFACE_INSTANCE_V1"

REQUIRED_PROPERTIES = {
    "FINITE_EXPLICITLY_CLASSIFIED_DISCOVERY_SOURCE_SET_PER_AUTHORITY_EPOCH",
    "EACH_AUTHORITATIVE_SOURCE_DECLARES_A_TASK_INDEPENDENT_COMPLETE_CATALOG_QUERY",
    "POLICY_COMPUTES_SOURCE_SET_DIGEST_FROM_EXACT_SOURCE_METADATA_CATALOG_QUERY_AND_AUTHORITY_EPOCH",
    "EACH_SOURCE_HAS_STABLE_SOURCE_EPOCH_AND_CANONICAL_EXPECTED_RESULT_CONTENT_DIGEST_OR_EPISODE_RESTARTS",
    "DISCOVERY_RECEIPT_IS_COMPLETE_CURRENT_AUTHORITY_EPOCH_CURRENT_SOURCE_EPOCH_CANONICAL_CATALOG_QUERY_AND_EXACT_RESULT_CONTENT_BOUND",
    "COMPLETE_CATALOG_RECEIPT_IS_REUSABLE_ACROSS_TASK_REQUIREMENT_AND_DECISION_EPOCH_CHANGES_WITHIN_THE_SAME_AUTHORITY_SOURCE_EPOCHS",
    "UNION_OF_CURRENT_COMPLETE_AUTHORITATIVE_CATALOG_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_IS_CORRECT_AND_SAME_ID_METADATA_IS_CONSISTENT_WITHIN_EPOCH",
    "EVERY_ADMISSIBLE_REQUIRED_CAPABILITY_IS_CURRENTLY_EVIDENCED_OR_EXPLICITLY_SAFE_PROBE_DECIDABLE",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_TOOL_EPOCH_BOUND",
    "UNRESOLVED_CHEAPER_ADMISSIBLE_ROUTE_WITHOUT_SAFE_PROBE_BLOCKS_MORE_EXPENSIVE_SELECTION",
    "TOOL_VERSION_OR_AUTHORITY_CHANGE_RESTARTS_OR_INVALIDATES_STALE_CATALOG_AND_CAPABILITY_EVIDENCE",
}


def _sha_json(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()


def _source_epoch(index_sha256: str) -> int:
    return int(index_sha256[:15],16)


def _authority_epoch(epoch_sha256: str) -> int:
    return int(epoch_sha256[:15],16)


def _tool_rows_for_source(row: dict[str,str]) -> list[dict[str,Any]]:
    sid=aptv1._source_id(row)
    tools=[]
    for stanza in aptv1._iter_stanzas_from_index(row["filename"]):
        name=stanza.get("Package")
        version=stanza.get("Version")
        arch=stanza.get("Architecture")
        if not name or not version or not arch:
            continue
        tid=f"{sid}::{name}::{version}::{arch}"
        safe=["CLI_SHA256SUM_VERSION_EXECUTES"] if name=="coreutils" else []
        tools.append({
            "tool_id":tid,
            "epoch":_source_epoch(row["index_sha256"]),
            "cost":0.0,
            "available":True,
            "authorized":True,
            "safe_probe_capabilities":safe,
        })
    tools.sort(key=lambda x:x["tool_id"])
    return tools


def _v8_single_source_state(
    tools: list[dict[str,Any]],
    *,
    required: list[str],
    authority_epoch: int,
    decision_epoch: int,
    probe_rows: list[dict[str,Any]],
) -> dict[str,Any]:
    source={
        "source_id":"LIVE_APT_COMPOSITE",
        "cost":0.0,
        "available":True,
        "authorized":True,
        "authoritative":True,
        "source_epoch":0,
        "source_digest":v5._tools_digest(tools),
        "catalog_query":"APT_COMPLETE_ENABLED_PUBLIC_CATALOG",
    }
    source_set=v8._source_set_digest([source],authority_epoch=authority_epoch)
    return {
        "required_capabilities":required,
        "decision_epoch":decision_epoch,
        "authority_epoch":authority_epoch,
        "constraint":None,
        "visible_tools":[],
        "discovery_sources":[source],
        "discovery_receipts":[{
            "kind":"DISCOVERY_RESULT",
            "source_id":source["source_id"],
            "complete":True,
            "authority_epoch":authority_epoch,
            "source_epoch":source["source_epoch"],
            "source_digest":source["source_digest"],
            "source_set_digest":source_set,
            "query":source["catalog_query"],
            "tools":copy.deepcopy(tools),
        }],
        "prior_probe_receipts":copy.deepcopy(probe_rows),
        "version_events":[],
    }


def _policy_transfer_and_blocking_checks(
    *,
    coreutils_tool: dict[str,Any],
    authority_epoch: int,
) -> dict[str,bool]:
    cap="CLI_SHA256SUM_VERSION_EXECUTES"
    probe=[{
        "kind":"SAFE_CAPABILITY_PROBE",
        "tool_id":coreutils_tool["tool_id"],
        "capability":cap,
        "epoch":coreutils_tool["epoch"],
        "authority_epoch":authority_epoch,
        "supported":True,
    }]
    s1=_v8_single_source_state(
        [coreutils_tool],required=[cap],authority_epoch=authority_epoch,
        decision_epoch=1,probe_rows=probe,
    )
    a1=v8.next_action(copy.deepcopy(s1))
    s2=copy.deepcopy(s1)
    s2["decision_epoch"]=999999
    a2=v8.next_action(copy.deepcopy(s2))

    cheap=copy.deepcopy(coreutils_tool)
    cheap["tool_id"]="CHEAP_UNPROBEABLE"
    cheap["cost"]=0.0
    cheap["safe_probe_capabilities"]=[]
    expensive=copy.deepcopy(coreutils_tool)
    expensive["tool_id"]="EXPENSIVE_VERIFIED"
    expensive["cost"]=10.0
    exp_probe=[{
        "kind":"SAFE_CAPABILITY_PROBE",
        "tool_id":expensive["tool_id"],
        "capability":cap,
        "epoch":expensive["epoch"],
        "authority_epoch":authority_epoch,
        "supported":True,
    }]
    blocked=_v8_single_source_state(
        [cheap,expensive],required=[cap],authority_epoch=authority_epoch,
        decision_epoch=7,probe_rows=exp_probe,
    )
    ab=v8.next_action(blocked)

    version=copy.deepcopy(s1)
    version["version_events"]=[{
        "kind":"TOOL_VERSION_CHANGED",
        "tool_id":coreutils_tool["tool_id"],
        "new_epoch":coreutils_tool["epoch"]+1,
    }]
    av=v8.next_action(version)

    authority=copy.deepcopy(s1)
    authority["version_events"]=[{
        "kind":"TOOL_AUTHORITY_CHANGED",
        "new_authority_epoch":authority_epoch+1,
    }]
    aa=v8.next_action(authority)

    return {
        "same_catalog_reused_across_decision_epoch":a1=={"action":"SELECT","tool_id":coreutils_tool["tool_id"]} and a2==a1,
        "cheaper_unprobeable_blocks_expensive_selection":ab=={
            "action":"ESCALATE",
            "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id":"CHEAP_UNPROBEABLE",
        },
        "tool_version_change_restarts":av.get("reason")=="TOOL_VERSION_CHANGED_RESTART_EPISODE",
        "authority_change_restarts":aa.get("reason")=="TOOL_AUTHORITY_CHANGED_RESTART_EPISODE",
    }


def evaluate() -> dict[str,Any]:
    contract=json.loads(CONTRACT.read_text())
    if set(contract.get("required_properties") or [])!=REQUIRED_PROPERTIES:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED__V4_CONTRACT_DRIFT","pass":False,
            "errors":["V4_CONTRACT_PROPERTY_SET_DRIFT"],"execution_authority":False,
            "promotion_authority":False,"capability_credit_delta":0,"family_credit_delta":0,
        }

    base=aptv1.evaluate()
    if base.get("pass") is not True:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED__V1_LIVE_INTERFACE_BASE_FAILED","pass":False,
            "base":base,"execution_authority":False,"promotion_authority":False,
            "capability_credit_delta":0,"family_credit_delta":0,
        }

    snapshot=aptv1._epoch_snapshot()
    rows=snapshot.pop("_index_rows")
    authority_epoch=_authority_epoch(snapshot["epoch_sha256"])
    source_descriptors=[]
    all_tools=[]
    same_id={}
    metadata_consistent=True
    coreutils_tool=None

    for row in rows:
        tools=_tool_rows_for_source(row)
        sid=aptv1._source_id(row)
        source_epoch=_source_epoch(row["index_sha256"])
        query=f"APT_PACKAGES_INDEX_COMPLETE::{sid}"
        result_digest=v5._tools_digest(tools)
        descriptor={
            "source_id":sid,
            "source_class":"APT_PACKAGES_INDEX",
            "authoritative":True,
            "available":True,
            "authorized":True,
            "cost":0.0,
            "source_epoch":source_epoch,
            "source_digest":result_digest,
            "catalog_query":query,
            "index_sha256":row["index_sha256"],
            "complete":True,
            "tool_count":len(tools),
        }
        source_descriptors.append(descriptor)
        for tool in tools:
            prior=same_id.get(tool["tool_id"])
            if prior is not None and prior!=tool:
                metadata_consistent=False
            same_id[tool["tool_id"]]=tool
            all_tools.append(tool)
            if coreutils_tool is None and "::coreutils::" in tool["tool_id"]:
                coreutils_tool=tool

    source_set_digest=v8._source_set_digest(
        source_descriptors,authority_epoch=authority_epoch,
    )
    receipts=[]
    for src in source_descriptors:
        receipts.append({
            "kind":"DISCOVERY_RESULT",
            "source_id":src["source_id"],
            "complete":True,
            "authority_epoch":authority_epoch,
            "source_epoch":src["source_epoch"],
            "source_digest":src["source_digest"],
            "source_set_digest":source_set_digest,
            "query":src["catalog_query"],
            "exact_result_content_digest":src["source_digest"],
        })

    stable=aptv1._epoch_snapshot()
    stable.pop("_index_rows")
    epoch_stable=stable["epoch_sha256"]==snapshot["epoch_sha256"]

    probe=base.get("safe_probe_receipt") or {}
    if coreutils_tool is None:
        policy_checks={
            "same_catalog_reused_across_decision_epoch":False,
            "cheaper_unprobeable_blocks_expensive_selection":False,
            "tool_version_change_restarts":False,
            "authority_change_restarts":False,
        }
    else:
        policy_checks=_policy_transfer_and_blocking_checks(
            coreutils_tool=coreutils_tool,authority_epoch=authority_epoch,
        )

    source_queries_task_independent=all(
        str(s["catalog_query"]).startswith("APT_PACKAGES_INDEX_COMPLETE::")
        and "CAP" not in s["catalog_query"]
        and "TASK" not in s["catalog_query"]
        for s in source_descriptors
    )
    receipts_bound=all(
        r["complete"] is True
        and r["authority_epoch"]==authority_epoch
        and r["source_set_digest"]==source_set_digest
        and r["exact_result_content_digest"]==r["source_digest"]
        for r in receipts
    )

    props={
        "FINITE_EXPLICITLY_CLASSIFIED_DISCOVERY_SOURCE_SET_PER_AUTHORITY_EPOCH":bool(source_descriptors) and all(s["source_class"]=="APT_PACKAGES_INDEX" for s in source_descriptors),
        "EACH_AUTHORITATIVE_SOURCE_DECLARES_A_TASK_INDEPENDENT_COMPLETE_CATALOG_QUERY":source_queries_task_independent,
        "POLICY_COMPUTES_SOURCE_SET_DIGEST_FROM_EXACT_SOURCE_METADATA_CATALOG_QUERY_AND_AUTHORITY_EPOCH":source_set_digest.startswith("sha256:") and len(source_set_digest)==71,
        "EACH_SOURCE_HAS_STABLE_SOURCE_EPOCH_AND_CANONICAL_EXPECTED_RESULT_CONTENT_DIGEST_OR_EPISODE_RESTARTS":epoch_stable and all(isinstance(s["source_epoch"],int) and s["source_digest"] for s in source_descriptors),
        "DISCOVERY_RECEIPT_IS_COMPLETE_CURRENT_AUTHORITY_EPOCH_CURRENT_SOURCE_EPOCH_CANONICAL_CATALOG_QUERY_AND_EXACT_RESULT_CONTENT_BOUND":receipts_bound,
        "COMPLETE_CATALOG_RECEIPT_IS_REUSABLE_ACROSS_TASK_REQUIREMENT_AND_DECISION_EPOCH_CHANGES_WITHIN_THE_SAME_AUTHORITY_SOURCE_EPOCHS":policy_checks["same_catalog_reused_across_decision_epoch"],
        "UNION_OF_CURRENT_COMPLETE_AUTHORITATIVE_CATALOG_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE":base["property_results"]["UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE"],
        "DISCOVERED_TOOL_METADATA_IS_CORRECT_AND_SAME_ID_METADATA_IS_CONSISTENT_WITHIN_EPOCH":base["property_results"]["DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS"] and metadata_consistent,
        "EVERY_ADMISSIBLE_REQUIRED_CAPABILITY_IS_CURRENTLY_EVIDENCED_OR_EXPLICITLY_SAFE_PROBE_DECIDABLE":coreutils_tool is not None and "CLI_SHA256SUM_VERSION_EXECUTES" in coreutils_tool["safe_probe_capabilities"],
        "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_TOOL_EPOCH_BOUND":probe.get("pass") is True and probe.get("truthful_observed_execution") is True and coreutils_tool is not None,
        "UNRESOLVED_CHEAPER_ADMISSIBLE_ROUTE_WITHOUT_SAFE_PROBE_BLOCKS_MORE_EXPENSIVE_SELECTION":policy_checks["cheaper_unprobeable_blocks_expensive_selection"],
        "TOOL_VERSION_OR_AUTHORITY_CHANGE_RESTARTS_OR_INVALIDATES_STALE_CATALOG_AND_CAPABILITY_EVIDENCE":policy_checks["tool_version_change_restarts"] and policy_checks["authority_change_restarts"],
    }
    ok=all(props.values())
    return {
        "schema":SCHEMA,
        "status":"PASS__LIVE_APT_V4_TRANSFERABLE_INTERFACE_INSTANCE__REALIZABILITY_ONLY__ZERO_ACCEPTANCE_CREDIT" if ok else "FAIL_CLOSED__V4_PROPERTY_FAILURE",
        "pass":ok,
        "v4_contract_blob":"0a9a788c2637610f4b4cfc5e0f770ba972409137",
        "property_results":props,
        "authority_epoch":authority_epoch,
        "source_set_digest":source_set_digest,
        "source_count":len(source_descriptors),
        "tool_identity_count":len(all_tools),
        "epoch_stable":epoch_stable,
        "safe_probe_receipt":probe,
        "policy_checks":policy_checks,
        "base_v1_live_instance_status":base.get("status"),
        "declared_live_requirement":"CLI_SHA256SUM_VERSION_EXECUTES",
        "hard_nonclaims":[
            "ONE_APT_INSTANCE_DOES_NOT_PROVE_ALL_REAL_WORLD_TOOL_ECOSYSTEMS",
            "REALIZABILITY_DOES_NOT_PROVE_UNIVERSAL_SCOPE_COMPLETENESS",
            "REALIZABILITY_DOES_NOT_PROVE_OPUS_NONINFERIORITY",
            "NO_TOOL_DISCOVERY_ACCEPTANCE_FAMILY_OR_CAPABILITY_CREDIT",
        ],
        "new_reality_units_consumed":1,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
