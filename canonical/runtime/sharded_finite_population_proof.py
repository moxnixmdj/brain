"""Deterministic post-freeze sampling for sharded finite benchmark proofs.

The population is a frozen list of opaque case IDs. Case content is neither required
nor accepted. A public seed is mixed with the frozen population commitment and each
case ID; the n lowest hashes form a uniform random sample without replacement when
the seed is unpredictable before candidate freeze.

Execution policy:
- one selected case per fresh zero-cost runner job;
- no replacement or resampling;
- infrastructure, resource, harness, oracle, timeout, or candidate failures all count
  as case failures unless the entire scorer identity is invalidated;
- exact finite-population lower bound is computed after all selected cases terminate.

This makes heterogeneous per-case resource failures conservative rather than a source
of selection bias.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime.finite_population_proof import evaluate_binary_population

SCHEMA="BRAIN_SHARDED_FINITE_POPULATION_PROOF_V1"


def _canon(x: Any) -> bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()


def population_commitment(case_ids: Sequence[str]) -> str:
    if not isinstance(case_ids, Sequence) or isinstance(case_ids,(str,bytes)) or not case_ids:
        raise ValueError("case_ids must be a nonempty sequence")
    ids=[str(x) for x in case_ids]
    if any(not x for x in ids) or len(ids)!=len(set(ids)):
        raise ValueError("case IDs must be unique nonempty strings")
    return hashlib.sha256(_canon(sorted(ids))).hexdigest()


def select_case_ids(case_ids: Sequence[str], sample_size: int, seed: str) -> list[str]:
    ids=[str(x) for x in case_ids]
    commit=population_commitment(ids)
    if not isinstance(sample_size,int) or isinstance(sample_size,bool) or not 1<=sample_size<=len(ids):
        raise ValueError("invalid sample_size")
    if not isinstance(seed,str) or not seed:
        raise ValueError("seed must be nonempty string")
    ranked=[]
    for cid in ids:
        h=hashlib.sha256((SCHEMA+"\0"+commit+"\0"+seed+"\0"+cid).encode()).hexdigest()
        ranked.append((h,cid))
    ranked.sort()
    return [cid for _,cid in ranked[:sample_size]]


def compile_execution_manifest(
    *,
    case_ids: Sequence[str],
    sample_size: int,
    seed: str,
    candidate_commit: str,
    harness_commit: str,
    scorer_commit: str,
    runner_label: str,
    timeout_minutes: int,
) -> dict[str,Any]:
    if not all(isinstance(x,str) and x for x in (candidate_commit,harness_commit,scorer_commit,runner_label)):
        raise ValueError("commit and runner bindings must be nonempty strings")
    if not isinstance(timeout_minutes,int) or isinstance(timeout_minutes,bool) or timeout_minutes<=0:
        raise ValueError("timeout_minutes must be positive")
    commit=population_commitment(case_ids)
    selected=select_case_ids(case_ids,sample_size,seed)
    return {
      "schema":SCHEMA,
      "status":"FROZEN_EXECUTION_MANIFEST",
      "population_size":len(case_ids),
      "population_commitment":commit,
      "sample_size":sample_size,
      "seed":seed,
      "candidate_commit":candidate_commit,
      "harness_commit":harness_commit,
      "scorer_commit":scorer_commit,
      "runner_label":runner_label,
      "timeout_minutes_per_case":timeout_minutes,
      "selected_case_ids":selected,
      "job_policy":"ONE_SELECTED_CASE_PER_FRESH_JOB",
      "case_failure_policy":"ANY_CANDIDATE_INFRASTRUCTURE_RESOURCE_TIMEOUT_HARNESS_OR_ORACLE_FAILURE_COUNTS_AS_FAILURE__NO_REPLACEMENT",
      "scorer_invalidation_policy":"ONLY_PROVEN_GLOBAL_SCORER_IDENTITY_OR_SEMANTIC_INVALIDATION_INVALIDATES_WAVE__CASE_LOCAL_FAILURE_COUNTS_AS_FAILURE",
      "replacement_allowed":False,
    }


def score_results(
    manifest: Mapping[str,Any],
    case_results: Sequence[Mapping[str,Any]],
    *,
    threshold_rate: float,
    alpha: float=0.05,
) -> dict[str,Any]:
    if manifest.get("schema")!=SCHEMA or manifest.get("status")!="FROZEN_EXECUTION_MANIFEST":
        raise ValueError("invalid manifest")
    selected=list(manifest.get("selected_case_ids") or [])
    by_id={}
    for row in case_results:
        if not isinstance(row,Mapping):
            raise ValueError("case result invalid")
        cid=row.get("case_id")
        if not isinstance(cid,str) or cid in by_id:
            raise ValueError("duplicate or invalid case result")
        by_id[cid]=row
    if set(by_id)!=set(selected):
        raise ValueError("result case IDs must exactly match frozen sample")
    invalidators=[
        cid for cid in selected
        if by_id[cid].get("scorer_invalidated") is True
    ]
    if invalidators:
        return {
          "schema":"BRAIN_SHARDED_FINITE_POPULATION_VERDICT_V1",
          "status":"INVALID_SCORER",
          "population_commitment":manifest["population_commitment"],
          "invalidating_case_ids":sorted(invalidators),
          "pass_terminal_rate_lower_bound":False,
          "rule":"GLOBAL_SCORER_IDENTITY_OR_SEMANTIC_INVALIDATION_INVALIDATES_WAVE__IT_IS_NOT_COUNTED_AS_A_CASE_FAILURE",
        }

    successes=0
    normalized=[]
    for cid in selected:
        row=by_id[cid]
        # Only an explicit machine-oracle pass counts. Every case-local execution
        # problem is conservatively a failure; global scorer invalidation was handled above.
        passed=row.get("oracle_pass") is True
        successes += int(passed)
        normalized.append({
          "case_id":cid,
          "pass":passed,
          "failure_class":None if passed else str(row.get("failure_class") or "UNSPECIFIED_FAILURE"),
        })
    proof=evaluate_binary_population(
      population_size=int(manifest["population_size"]),
      sample_size=len(selected),
      sample_successes=successes,
      threshold_rate=threshold_rate,
      alpha=alpha,
    )
    return {
      "schema":"BRAIN_SHARDED_FINITE_POPULATION_VERDICT_V1",
      "status":proof["status"],
      "population_commitment":manifest["population_commitment"],
      "sample_size":len(selected),
      "successes":successes,
      "failures":len(selected)-successes,
      "case_results":normalized,
      "finite_population_proof":proof,
      "pass_terminal_rate_lower_bound":proof["pass_lower_bound"],
    }
