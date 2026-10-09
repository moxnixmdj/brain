"""UVCK V2 domain challenge registry V1.

Compiles previously discovered assurance failure classes into the fixed V2
primitive vocabulary. This registry is intentionally non-authoritative: it
proves representability of challenge obligations, not that the corresponding
domain obligations are already solved.

A challenge that cannot be represented with the fixed primitive set is a
candidate architectural primitive gap. A representable challenge remains an
ordinary residual for existing synthesis/verification machinery.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from canonical.runtime import assurance_closure_compiler_v1 as closure

SCHEMA="PROJECT_BRAIN_ASSURANCE_DOMAIN_CHALLENGE_REGISTRY_V1"

CHALLENGES={
    "EPISTEMIC_SNAPSHOT_CONSISTENCY":{
        "origin":"V1.52",
        "description":"individually true observations can compose into a nonexistent Frankenstate",
        "primitives":["CLAIM","OBLIGATION","EVIDENCE","DEPENDENCY","EPOCH","MONITOR"],
    },
    "ADVERSARIAL_OBSERVATION_RECONSTRUCTION":{
        "origin":"V1.53",
        "description":"authenticated observations can still be faulty, replayed, correlated, or adversarial",
        "primitives":["CLAIM","OBLIGATION","EVIDENCE","DEFEATER","ASSUMPTION","MONITOR"],
    },
    "ACTIVE_CHALLENGE_RESPONSE_ATTESTATION":{
        "origin":"V1.54",
        "description":"passive observation histories can be synthetically replayed without live coupling",
        "primitives":["OBLIGATION","EVIDENCE","EFFECT","RESOURCE","AUTHORITY","MONITOR"],
    },
    "TARGET_BOUND_ANTI_RELAY":{
        "origin":"V1.55",
        "description":"fresh valid responses can originate from the wrong genuine target",
        "primitives":["CLAIM","OBLIGATION","EVIDENCE","DEPENDENCY","AUTHORITY","EPOCH"],
    },
    "CHECK_TO_EFFECT_TEMPORAL_CLOSURE":{
        "origin":"V1.56",
        "description":"a checked precondition can become false before semantic commit",
        "primitives":["ASSUMPTION","OBLIGATION","MONITOR","EPOCH","TRANSITION","EFFECT"],
    },
    "END_TO_END_SCHEDULABILITY":{
        "origin":"V1.57",
        "description":"assurance plus execution may miss the semantic deadline despite local correctness",
        "primitives":["OBLIGATION","RESOURCE","DEPENDENCY","MONITOR","EFFECT"],
    },
    "TRUSTED_TIME_REFERENCE":{
        "origin":"V1.58",
        "description":"leases and deadlines can be unsound when their clocks are wrong or incomparable",
        "primitives":["ASSUMPTION","EVIDENCE","EPOCH","MONITOR","DEPENDENCY"],
    },
    "RESOURCE_SUPPLY_EXHAUSTION":{
        "origin":"V1.59",
        "description":"timing and recovery proofs can fail when CPU, storage, network, energy, or quotas exhaust",
        "primitives":["RESOURCE","OBLIGATION","MONITOR","ASSUMPTION","EFFECT"],
    },
    "PROGRESS_DEADLOCK_LIVELOCK":{
        "origin":"V1.60",
        "description":"resources can exist while waits, retries, or handoffs fail to make root progress",
        "primitives":["OBLIGATION","DEPENDENCY","RESOURCE","TRANSITION","MONITOR"],
    },
    "DISTRIBUTED_COORDINATION_FENCING":{
        "origin":"V1.61",
        "description":"partitions and stale leaders can create conflicting authority or unsafe progress",
        "primitives":["AUTHORITY","EPOCH","TRANSITION","OBLIGATION","EFFECT"],
    },
    "SEMANTIC_EFFECT_EXACTLY_ONCE":{
        "origin":"V1.62",
        "description":"internal commit cannot prove an external effect occurred exactly once",
        "primitives":["EFFECT","OBLIGATION","EVIDENCE","EPOCH","TRANSITION"],
    },
    "SEMANTIC_ISOLATION_COMPENSATION":{
        "origin":"V1.63",
        "description":"individually correct effects can interleave or compensate into a globally wrong state",
        "primitives":["EFFECT","DEPENDENCY","OBLIGATION","TRANSITION","RESOURCE"],
    },
    "EXTERNAL_PUBLICATION_FINALITY":{
        "origin":"V1.64",
        "description":"tentative state can escape to an uncontrolled observer before it is semantically final",
        "primitives":["EFFECT","CLAIM","DEPENDENCY","OBLIGATION","EPOCH"],
    },
    "COMMUNICATION_RECIPIENT_UPTAKE":{
        "origin":"V1.65",
        "description":"sent, delivered, accessed, understood, and acted-on are distinct obligations",
        "primitives":["OBLIGATION","EVIDENCE","DEPENDENCY","MONITOR","EFFECT"],
    },
    "ATOMIC_OBLIGATION_HANDOFF":{
        "origin":"V1.66",
        "description":"communication does not itself transfer responsibility for a live obligation",
        "primitives":["OBLIGATION","AUTHORITY","RESOURCE","TRANSITION","EPOCH","DEPENDENCY"],
    },
    "RESPONSIBILITY_SUCCESSION_CONTINUITY":{
        "origin":"V1.67",
        "description":"a valid current owner can disappear before a safe successor becomes active",
        "primitives":["OBLIGATION","AUTHORITY","RESOURCE","EPOCH","TRANSITION","MONITOR"],
    },
}


def challenge_ids()->list[str]:
    return sorted(CHALLENGES)


def validate_registry()->dict[str,Any]:
    errors=[]
    used=set()
    for challenge_id,row in CHALLENGES.items():
        if not isinstance(challenge_id,str) or not challenge_id:
            errors.append("CHALLENGE_ID_INVALID")
            continue
        primitives=row.get("primitives")
        if not isinstance(primitives,list) or not primitives:
            errors.append("PRIMITIVES_REQUIRED:"+challenge_id)
            continue
        unknown=sorted(set(primitives)-closure.PRIMITIVE_TYPES)
        if unknown:
            errors.append("UNKNOWN_PRIMITIVES:"+challenge_id+":"+",".join(unknown))
        used.update(primitives)
        if not str(row.get("origin") or "").startswith("V1."):
            errors.append("ORIGIN_INVALID:"+challenge_id)
        if not str(row.get("description") or "").strip():
            errors.append("DESCRIPTION_REQUIRED:"+challenge_id)
    return {
        "schema":SCHEMA,
        "pass":not errors,
        "status":"PASS__ALL_DOMAIN_CHALLENGES_REPRESENTABLE" if not errors else "FAIL_CLOSED",
        "challenge_count":len(CHALLENGES),
        "used_primitive_types":sorted(used),
        "unused_primitive_types":sorted(closure.PRIMITIVE_TYPES-used),
        "errors":errors,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def graph_for(challenge_id:str)->dict[str,Any]:
    if challenge_id not in CHALLENGES:
        raise KeyError(challenge_id)
    row=CHALLENGES[challenge_id]
    obligation_id="obligation:"+challenge_id
    return {
        "schema":closure.GRAPH_SCHEMA,
        "root_ids":["root:"+challenge_id],
        "nodes":[
            {
                "id":"root:"+challenge_id,
                "type":"CLAIM",
                "status":"SUPPORTED",
                "depends_on":[obligation_id],
                "defeated_by":[],
                "claim":"DOMAIN_CHALLENGE_CLOSED",
            },
            {
                "id":obligation_id,
                "type":"OBLIGATION",
                "status":"OPEN",
                "challenge_id":challenge_id,
                "origin":row["origin"],
                "description":row["description"],
                "required_primitive_types":deepcopy(row["primitives"]),
            },
        ],
    }


def evaluate_challenge(challenge_id:str)->dict[str,Any]:
    graph=graph_for(challenge_id)
    out=closure.evaluate(graph)
    return {
        "schema":SCHEMA,
        "challenge_id":challenge_id,
        "origin":CHALLENGES[challenge_id]["origin"],
        "compiler_status":out.get("status"),
        "representable":out.get("existing_kernel_expressive") is True,
        "ordinary_residual":out.get("status")=="OPEN__ASSURANCE_RESIDUAL",
        "new_primitive_required":out.get("new_primitive_required") is True,
        "open_residual_ids":deepcopy(out.get("open_residual_ids") or []),
        "terminal_authority":False,
    }


def evaluate_all()->dict[str,Any]:
    registry=validate_registry()
    rows=[evaluate_challenge(cid) for cid in challenge_ids()]
    bad=[
        row for row in rows
        if not row["representable"]
        or not row["ordinary_residual"]
        or row["new_primitive_required"]
    ]
    return {
        "schema":SCHEMA,
        "pass":registry["pass"] and not bad,
        "status":"PASS__DOMAIN_CHALLENGES_COMPILE_TO_EXISTING_KERNEL_RESIDUALS" if registry["pass"] and not bad else "FAIL_CLOSED",
        "challenge_count":len(rows),
        "compiled_count":len(rows)-len(bad),
        "failed_challenge_ids":[row["challenge_id"] for row in bad],
        "rows":rows,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
