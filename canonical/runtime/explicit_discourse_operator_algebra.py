"""Deterministic discourse-operator algebra for explicit structured references.

This owns only operator semantics once upstream evidence has already identified
constituents. It intentionally does not discover arbitrary noun phrases or infer
world knowledge.

Owned operators:
- former/latter over an explicit ordered pair,
- respectively over two explicit equal-length ordered lists,
- explicit "too" ellipsis by predicate reuse with a replacement subject,
- demonstrative event reference over a unique explicit candidate.

Any arity mismatch, duplicate identity, missing predicate, or ambiguous candidate
set fails closed.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping, Sequence

SCHEMA="BRAIN_EXPLICIT_DISCOURSE_OPERATOR_ALGEBRA_V1"


def _fail(error:str, **extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":error,"terminal_authority":False,**extra}


def resolve_former_latter(ordered_pair:Sequence[str], reference:str)->dict[str,Any]:
    if not isinstance(ordered_pair,Sequence) or isinstance(ordered_pair,(str,bytes)):
        return _fail("PAIR_NOT_SEQUENCE")
    ids=list(ordered_pair)
    if len(ids)!=2 or any(not isinstance(x,str) or not x for x in ids):
        return _fail("PAIR_ARITY_OR_ID_INVALID")
    if ids[0]==ids[1]:
        return _fail("PAIR_IDENTITIES_NOT_DISTINCT")
    ref=str(reference).strip().lower()
    if ref=="former":
        target=ids[0]
    elif ref=="latter":
        target=ids[1]
    else:
        return _fail("REFERENCE_NOT_FORMER_OR_LATTER")
    return {
        "schema":SCHEMA,"status":"RESOLVED","operator":"FORMER_LATTER",
        "reference":ref,"target_id":target,"ordered_pair":ids,
        "terminal_authority":False,
    }


def resolve_respectively(left_ids:Sequence[str], right_values:Sequence[Any])->dict[str,Any]:
    if any(isinstance(x,(str,bytes)) for x in (left_ids,right_values)):
        return _fail("RESPECTIVELY_INPUT_NOT_LISTLIKE")
    try:
        left=list(left_ids); right=list(right_values)
    except TypeError:
        return _fail("RESPECTIVELY_INPUT_NOT_LISTLIKE")
    if not left or len(left)!=len(right):
        return _fail("RESPECTIVELY_ARITY_MISMATCH",left_count=len(left),right_count=len(right))
    if any(not isinstance(x,str) or not x for x in left):
        return _fail("RESPECTIVELY_LEFT_ID_INVALID")
    if len(set(left))!=len(left):
        return _fail("RESPECTIVELY_LEFT_IDS_NOT_DISTINCT")
    return {
        "schema":SCHEMA,"status":"RESOLVED","operator":"RESPECTIVELY",
        "bindings":[{"left_id":lid,"right_value":rv} for lid,rv in zip(left,right)],
        "terminal_authority":False,
    }


def resolve_too_ellipsis(
    prior_predicate:Mapping[str,Any],
    new_subject_id:str,
    *,
    marker:str="too",
)->dict[str,Any]:
    if str(marker).strip().lower() not in {"too","also","as well"}:
        return _fail("ELLIPSIS_MARKER_UNSUPPORTED")
    if not isinstance(prior_predicate,Mapping):
        return _fail("PRIOR_PREDICATE_NOT_OBJECT")
    operator=prior_predicate.get("operator")
    if not isinstance(operator,str) or not operator:
        return _fail("PRIOR_PREDICATE_OPERATOR_MISSING")
    if not isinstance(new_subject_id,str) or not new_subject_id:
        return _fail("NEW_SUBJECT_ID_INVALID")
    inherited=deepcopy(dict(prior_predicate))
    inherited["subject_id"]=new_subject_id
    inherited["inherited_by_explicit_ellipsis"]=True
    inherited["ellipsis_marker"]=str(marker).strip().lower()
    return {
        "schema":SCHEMA,"status":"RESOLVED","operator":"EXPLICIT_TOO_ELLIPSIS",
        "predicate":inherited,"terminal_authority":False,
    }


def resolve_demonstrative_event(
    candidate_event_ids:Sequence[str],
    phrase:str,
)->dict[str,Any]:
    allowed={"this validation","this operation","this action","this step","that validation","that operation","that action","that step"}
    p=" ".join(str(phrase).strip().lower().split())
    if p not in allowed:
        return _fail("DEMONSTRATIVE_EVENT_PHRASE_UNSUPPORTED")
    if isinstance(candidate_event_ids,(str,bytes)):
        return _fail("EVENT_CANDIDATES_NOT_SEQUENCE")
    ids=list(candidate_event_ids)
    if any(not isinstance(x,str) or not x for x in ids):
        return _fail("EVENT_CANDIDATE_ID_INVALID")
    uniq=list(dict.fromkeys(ids))
    if len(uniq)!=1:
        return _fail("EVENT_REFERENCE_NOT_UNIQUE",candidate_ids=uniq)
    return {
        "schema":SCHEMA,"status":"RESOLVED","operator":"DEMONSTRATIVE_EVENT",
        "phrase":p,"target_event_id":uniq[0],"terminal_authority":False,
    }
