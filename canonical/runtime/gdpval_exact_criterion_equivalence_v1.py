"""Exact GDPval rubric criterion equivalence compiler.

This compiler performs only byte/string identity compression over already-bound
GDPval rubric records. It never infers semantic equivalence from paraphrases.

Two rubric items enter the same exact-text class iff their criterion strings are
exactly equal. Score, task, occupation, and other context remain attached as
occurrence metadata, so exact text identity cannot silently imply equal score,
equal threshold, equal owner-pairwise effect, or whole-task equivalence.

Purpose: convert N rubric occurrences into a smaller set of exact shared
acceptance-text obligations before any semantic interpretation is attempted.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_GDPVAL_EXACT_CRITERION_EQUIVALENCE_V1"

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha_text(text:str)->str:
    return "sha256:"+sha256(text.encode("utf-8")).hexdigest()

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "semantic_equivalence_claimed":False,"task_closure_authority":False,
        "u_deletion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def compile_classes(rows:Sequence[Mapping[str,Any]], *, source_revision:str)->dict[str,Any]:
    if not isinstance(source_revision,str) or not source_revision.strip():
        return _fail("SOURCE_REVISION_REQUIRED")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        return _fail("ROWS_SEQUENCE_REQUIRED")

    groups:dict[str,list[dict[str,Any]]]=defaultdict(list)
    seen_items:set[str]=set()
    task_ids:set[str]=set()
    occurrence_count=0

    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return _fail("ROW_NOT_MAPPING",row_index=i)
        task_id=row.get("task_id")
        if not isinstance(task_id,str) or not task_id.strip():
            return _fail("TASK_ID_REQUIRED",row_index=i)
        task_id=task_id.strip()
        task_ids.add(task_id)
        rubric=row.get("rubric")
        if isinstance(rubric,str):
            try: rubric=json.loads(rubric)
            except json.JSONDecodeError:
                return _fail("RUBRIC_JSON_INVALID",task_id=task_id)
        if not isinstance(rubric,Sequence) or isinstance(rubric,(str,bytes)):
            return _fail("RUBRIC_SEQUENCE_REQUIRED",task_id=task_id)

        for j,item in enumerate(rubric):
            if not isinstance(item,Mapping):
                return _fail("RUBRIC_ITEM_NOT_MAPPING",task_id=task_id,item_index=j)
            item_id=item.get("rubric_item_id")
            criterion=item.get("criterion")
            if not isinstance(item_id,str) or not item_id.strip():
                return _fail("RUBRIC_ITEM_ID_REQUIRED",task_id=task_id,item_index=j)
            item_id=item_id.strip()
            if item_id in seen_items:
                return _fail("RUBRIC_ITEM_ID_DUPLICATE",rubric_item_id=item_id)
            seen_items.add(item_id)
            if not isinstance(criterion,str) or not criterion.strip():
                return _fail("CRITERION_REQUIRED",rubric_item_id=item_id)

            key=_sha_text(criterion)
            groups[key].append({
                "task_id":task_id,
                "rubric_item_id":item_id,
                "criterion_index":j,
                "score":item.get("score"),
                "criterion_sha256":key,
            })
            occurrence_count+=1

    classes=[]
    for digest,occ in groups.items():
        # All strings in the class are identical by construction. We store the
        # text exactly once. Context-sensitive fields remain occurrence-local.
        first_id=occ[0]["rubric_item_id"]
        text=None
        for row in rows:
            rubric=row.get("rubric")
            if isinstance(rubric,str): rubric=json.loads(rubric)
            for item in rubric:
                if item.get("rubric_item_id")==first_id:
                    text=item.get("criterion"); break
            if text is not None: break
        score_values=sorted({str(x["score"]) for x in occ})
        classes.append({
            "class_id":"EXACT_CRITERION::"+digest[7:],
            "criterion_sha256":digest,
            "criterion":text,
            "occurrence_count":len(occ),
            "task_count":len({x["task_id"] for x in occ}),
            "score_values":score_values,
            "score_context_invariant":len(score_values)==1,
            "occurrences":sorted(occ,key=lambda x:(x["task_id"],x["rubric_item_id"])),
        })

    classes.sort(key=lambda x:(-x["occurrence_count"],x["criterion_sha256"]))
    repeated=[x for x in classes if x["occurrence_count"]>1]
    repeated_occurrences=sum(x["occurrence_count"] for x in repeated)
    savings=sum(x["occurrence_count"]-1 for x in repeated)

    manifest_body={
        "source_revision":source_revision,
        "occurrence_count":occurrence_count,
        "classes":[
            {
                "class_id":x["class_id"],
                "criterion_sha256":x["criterion_sha256"],
                "occurrence_ids":[o["rubric_item_id"] for o in x["occurrences"]],
            }
            for x in classes
        ],
    }

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__EXACT_CRITERION_TEXT_EQUIVALENCE_COMPILED",
        "source_revision":source_revision,
        "task_count":len(task_ids),
        "criterion_occurrence_count":occurrence_count,
        "exact_text_class_count":len(classes),
        "repeated_class_count":len(repeated),
        "repeated_occurrence_count":repeated_occurrences,
        "exact_text_compression_savings":savings,
        "classes":classes,
        "manifest_sha256":"sha256:"+sha256(_canon(manifest_body).encode("utf-8")).hexdigest(),
        "equivalence_basis":"EXACT_CRITERION_STRING_IDENTITY_ONLY",
        "semantic_equivalence_claimed":False,
        "context_specific_threshold_equivalence_claimed":False,
        "owner_pairwise_effect_equivalence_claimed":False,
        "task_closure_authority":False,
        "u_deletion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"EXACT_TEXT_REUSE_ONLY__REPEATED_CLASS_MAY_SHARE_ONE_SEMANTIC_OR_ADEQUACY_LAW_ONLY_AFTER_THAT_LAW_IS_SEPARATELY_PROVED_SCOPE_SOUND_FOR_THE_OCCURRENCES_IT_CLAIMS",
    }
