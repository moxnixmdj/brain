"""Finite concrete-to-abstract policy cover lift with constructive counterexamples.

This kernel closes one specific gap in the existing finite symbolic cover replay:
it verifies that a declared abstraction is total over a declared concrete Boolean
scope, derives each abstract predicate mechanically from concrete formulas, and
checks that at least one adequate abstract policy region covers every concrete
valuation.

It deliberately does NOT claim the declared concrete scope equals real S_TRACE
or the Opus-relevant world. That outer scope-fidelity proof remains separate.
"""
from __future__ import annotations

from hashlib import sha256
import itertools
import json
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_FINITE_ABSTRACTION_COVER_LIFT_V1"
SPEC_SCHEMA = "PROJECT_BRAIN_FINITE_ABSTRACTION_COVER_SPEC_V1"
MAX_CONCRETE_VARIABLES = 16
MAX_ABSTRACT_VARIABLES = 16
MAX_ROUTES = 64
MAX_FORMULA_UNITS = 4096
MAX_EVALUATION_WORK_UNITS = 4_000_000
_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}$")
TOP_FIELDS = frozenset({
    "schema","scope_id","concrete_variables","concrete_scope_cnf",
    "abstract_predicates","routes"
})
ABSTRACT_FIELDS = frozenset({"name","definition_cnf"})
ROUTE_FIELDS = frozenset({"route_id","admission_cnf","adequacy_cnf"})


def _fail(reason: str, **more: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "declared_concrete_scope_covered": False,
        "abstraction_total_over_declared_scope": False,
        "real_target_scope_completeness_verified": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **more,
    }


def _check_cnf(value: Any, variables: set[str], budget: list[int]):
    if not isinstance(value, list):
        raise ValueError("CNF_MUST_BE_ARRAY")
    out=[]
    budget[0]+=1
    for clause in value:
        budget[0]+=1
        if budget[0] > MAX_FORMULA_UNITS:
            raise ValueError("CNF_BUDGET_EXCEEDED")
        if not isinstance(clause, list):
            raise ValueError("CNF_CLAUSE_MUST_BE_ARRAY")
        row=[]
        for lit in clause:
            budget[0]+=1
            if budget[0] > MAX_FORMULA_UNITS:
                raise ValueError("CNF_BUDGET_EXCEEDED")
            if not isinstance(lit,str) or not lit:
                raise ValueError("CNF_LITERAL_INVALID")
            name=lit[1:] if lit.startswith("!") else lit
            if name not in variables:
                raise ValueError("CNF_UNKNOWN_LITERAL")
            row.append(lit)
        out.append(tuple(row))
    return tuple(out)


def _holds(cnf, values: Mapping[str,bool]) -> bool:
    return all(any(
        (not values[lit[1:]]) if lit.startswith("!") else values[lit]
        for lit in clause
    ) for clause in cnf)


def verify(spec_reference: Mapping[str, Any], *, repo_root: str|Path,
           expected_scope_id: str) -> dict[str, Any]:
    try:
        if not isinstance(expected_scope_id,str) or not expected_scope_id:
            return _fail("EXPECTED_SCOPE_REQUIRED")
        bound=resolve_receipt_bytes(spec_reference, repo_root=repo_root)
        spec=bound["document"]
        if spec.get("schema") != SPEC_SCHEMA:
            return _fail("SPEC_SCHEMA_INVALID")
        if spec.get("scope_id") != expected_scope_id:
            return _fail("SPEC_SCOPE_MISMATCH")
        if set(spec) != TOP_FIELDS:
            return _fail("SPEC_FIELDS_INVALID")
        if any(k in spec for k in (
            "u_empty_authorized","global_scope_complete","terminal_authority",
            "opus55_equivalent","selected_cover_complete_authorized"
        )):
            return _fail("GLOBAL_AUTHORITY_CLAIM_FORBIDDEN")

        concrete=spec["concrete_variables"]
        if (not isinstance(concrete,list) or not concrete or
            len(concrete)>MAX_CONCRETE_VARIABLES or len(set(concrete))!=len(concrete) or
            any(not isinstance(v,str) or not _IDENT.fullmatch(v) for v in concrete)):
            return _fail("CONCRETE_VARIABLES_INVALID")
        cset=set(concrete)
        budget=[0]
        concrete_scope=_check_cnf(spec["concrete_scope_cnf"], cset, budget)

        abstract_rows=spec["abstract_predicates"]
        if (not isinstance(abstract_rows,list) or not abstract_rows or
            len(abstract_rows)>MAX_ABSTRACT_VARIABLES):
            return _fail("ABSTRACT_PREDICATES_INVALID")
        abstract_names=[]
        abstract_defs=[]
        for row in abstract_rows:
            if not isinstance(row,dict) or set(row)!=ABSTRACT_FIELDS:
                return _fail("ABSTRACT_PREDICATE_FIELDS_INVALID")
            name=row["name"]
            if (not isinstance(name,str) or not _IDENT.fullmatch(name) or name in abstract_names):
                return _fail("ABSTRACT_PREDICATE_NAME_INVALID")
            abstract_names.append(name)
            abstract_defs.append(_check_cnf(row["definition_cnf"], cset, budget))
        aset=set(abstract_names)

        routes=spec["routes"]
        if not isinstance(routes,list) or not 1<=len(routes)<=MAX_ROUTES:
            return _fail("ROUTES_INVALID_OR_TOO_MANY")
        compiled=[]
        ids=set()
        for row in routes:
            if not isinstance(row,dict) or set(row)!=ROUTE_FIELDS:
                return _fail("ROUTE_FIELDS_INVALID")
            rid=row["route_id"]
            if not isinstance(rid,str) or not rid or rid in ids:
                return _fail("ROUTE_ID_INVALID")
            ids.add(rid)
            compiled.append((
                rid,
                _check_cnf(row["admission_cnf"], aset, budget),
                _check_cnf(row["adequacy_cnf"], aset, budget),
            ))

        estimated=(1 << len(concrete))*budget[0]
        if estimated>MAX_EVALUATION_WORK_UNITS:
            return _fail("EVALUATION_WORK_BUDGET_EXCEEDED",
                         estimated_work_units=estimated,
                         max_work_units=MAX_EVALUATION_WORK_UNITS)

        checked=0
        for bits in itertools.product((False,True), repeat=len(concrete)):
            cval=dict(zip(concrete,bits))
            if not _holds(concrete_scope,cval):
                continue
            checked+=1
            aval={name:_holds(defn,cval)
                  for name,defn in zip(abstract_names,abstract_defs)}
            admitted=[]
            for rid,admission,adequacy in compiled:
                if _holds(admission,aval):
                    admitted.append(rid)
                    if _holds(adequacy,aval):
                        break
            else:
                if admitted:
                    return _fail(
                        "ADMITTED_BUT_NO_ADEQUATE_ROUTE",
                        scope_id=expected_scope_id,
                        failing_concrete_valuation=cval,
                        derived_abstract_valuation=aval,
                        admitting_route_ids=admitted,
                        spec_git_blob_sha=bound["git_blob_sha"],
                    )
                return _fail(
                    "UNCOVERED_CONCRETE_VALUATION",
                    scope_id=expected_scope_id,
                    failing_concrete_valuation=cval,
                    derived_abstract_valuation=aval,
                    spec_git_blob_sha=bound["git_blob_sha"],
                )

        if checked==0:
            return _fail("EMPTY_DECLARED_SCOPE_NOT_CREDITABLE")
        return {
            "schema":SCHEMA,
            "pass":True,
            "status":"PASS__DECLARED_CONCRETE_SCOPE_LIFTED_TO_ADEQUATE_ABSTRACT_COVER",
            "scope_id":expected_scope_id,
            "spec_git_blob_sha":bound["git_blob_sha"],
            "spec_byte_sha256":bound["byte_sha256"],
            "concrete_variable_count":len(concrete),
            "abstract_predicate_count":len(abstract_names),
            "route_count":len(compiled),
            "scoped_concrete_valuations_checked":checked,
            "total_concrete_valuations":1 << len(concrete),
            "bounded_evaluation_work_units":estimated,
            "abstraction_total_over_declared_scope":True,
            "declared_concrete_scope_covered":True,
            "constructive_counterexample_on_failure":True,
            "real_target_scope_completeness_verified":False,
            "u_empty_authorized":False,
            "abc_closed_authorized":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
            "boundary":"PROVES_ONLY_PINNED_DECLARED_CONCRETE_SCOPE_TO_ABSTRACT_POLICY_COVER__OUTER_S_TRACE_FIDELITY_AND_PRODUCTION_ROUTE_ADEQUACY_REQUIRE_SEPARATE_AUTHENTICATION",
        }
    except Exception as exc:
        return _fail("SPEC_BINDING_OR_REPLAY_INVALID",
                     exception_type=type(exc).__name__, detail=str(exc)[:200])
