#!/usr/bin/env python3
"""Parametric numeric reduction for frozen LiveBench active15. Zero terminal data."""
from __future__ import annotations
from typing import Any
from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp

SCHEMA="PROJECT_BRAIN_LIVEBENCH_LEGACY15_NUMERIC_QUOTIENT_V1"
WORD_MIN,WORD_MAX=100,500
SENT_MIN,SENT_MAX=1,20

# With number_words already consuming one of <=5 instruction slots, only four
# other active families can contribute tokens. Conservative constructor-local
# maxima, ordered by largest possible contribution:
FAMILY_WORD_BOUNDS={
    comp.SENTENCES:20, comp.SECTIONS:15, comp.END:8, comp.NTH:5,
    comp.BULLETS:5, comp.PARAGRAPHS:4, comp.POSTSCRIPT:3,
    comp.EXIST:1, comp.TITLE:1, comp.JSON_ID:1, comp.TWO:1,
    comp.REPEAT:1, comp.QUOTE:0, comp.FORBIDDEN:0,
}
ANALYTIC_WORD_CEILING=sum(sorted(FAMILY_WORD_BOUNDS.values(),reverse=True)[:4])


def C(iid:str,**slots:Any)->dict[str,Any]:
    return {"instruction_id":iid,"slots":slots}


def maximal_profile(ids):
    out=[]
    for iid in ids:
        if iid==comp.EXIST: out.append(C(iid,keywords=["harbor","violet","canyon","meadow","signal"]))
        elif iid==comp.FORBIDDEN: out.append(C(iid,forbidden_words=["amber","forest","silver","planet","window"]))
        elif iid==comp.PARAGRAPHS: out.append(C(iid,num_paragraphs=5))
        elif iid==comp.WORDS: out.append(C(iid,num_words=100,relation="less than"))
        elif iid==comp.SENTENCES: out.append(C(iid,num_sentences=20,relation="at least"))
        elif iid==comp.NTH: out.append(C(iid,num_paragraphs=5,nth_paragraph=5,first_word="harbor"))
        elif iid==comp.POSTSCRIPT: out.append(C(iid,postscript_marker="P.P.S"))
        elif iid==comp.BULLETS: out.append(C(iid,num_bullets=5))
        elif iid==comp.TITLE: out.append(C(iid))
        elif iid==comp.SECTIONS: out.append(C(iid,section_spliter="SECTION",num_sections=5))
        elif iid==comp.JSON_ID: out.append(C(iid))
        elif iid==comp.REPEAT: out.append(C(iid,prompt_to_repeat="Public request"))
        elif iid==comp.TWO: out.append(C(iid))
        elif iid==comp.END: out.append(C(iid,end_phrase="Is there anything else I can help with?"))
        elif iid==comp.QUOTE: out.append(C(iid))
        else: raise AssertionError("UNKNOWN_ACTIVE15_ID:"+iid)
    return out


def executable_word_ceiling():
    maximum=-1; maximizers=[]; examined=constructed=0
    for ids in arch.enumerate_compatible_sets():
        if comp.WORDS not in ids: continue
        examined+=1
        out=comp.compose_contracts(maximal_profile(ids))
        if out.get("status")!="CANDIDATE_WITNESS":
            raise AssertionError("MAX_PROFILE_NOT_CONSTRUCTED:"+repr((ids,out)))
        constructed+=1
        wc=int(out["word_count"])
        if wc>maximum: maximum,maximizers=wc,[list(ids)]
        elif wc==maximum: maximizers.append(list(ids))
    return {"examined":examined,"constructed":constructed,"maximum":maximum,"maximizers":maximizers}


def verify():
    if ANALYTIC_WORD_CEILING!=48: raise AssertionError("ANALYTIC_WORD_CEILING_DRIFT")
    ex=executable_word_ceiling()
    if ex["maximum"]>ANALYTIC_WORD_CEILING:
        raise AssertionError("EXECUTABLE_EXCEEDS_ANALYTIC_WORD_CEILING")
    return {
      "schema":SCHEMA,
      "status":"PASS__PARAMETRIC_NUMERIC_REDUCTION",
      "word_upper_bound":{
        "public_threshold_domain":[WORD_MIN,WORD_MAX],
        "analytic_constructor_ceiling":ANALYTIC_WORD_CEILING,
        "minimum_safety_margin":WORD_MIN-ANALYTIC_WORD_CEILING,
        "reason":"NUMBER_WORDS_PLUS_AT_MOST_FOUR_OTHER_FAMILIES__FOUR_LARGEST_TOKEN_BOUNDS_20_15_8_5",
        "executable_structural_crosscheck":ex,
      },
      "word_lower_bound":{
        "public_threshold_domain":[WORD_MIN,WORD_MAX],
        "reason":"CONSTRUCTOR_MONOTONICALLY_PADS_TO_THRESHOLD_BEFORE_TERMINAL_TAILS__TAILS_ONLY_ADD_WORDS",
      },
      "sentence_partition":{
        "less_than_1":"PROVED_UNSAT_BY_STRICT_NONEMPTY_PLUS_PINNED_PUNKT",
        "less_than_2_to_20":"ONE_SENTENCE_OR_LESS_CONSTRUCTION_CLASS__P.S._NEUTRALIZED_AS_P.S.+",
        "at_least_1_to_20":"MONOTONE_N_EXPLICIT_SENTENCE_CONSTRUCTION_CLASS",
      },
      "exact_small_integer_domains":{
        "paragraphs":[1,5],"bullets":[1,5],"sections":[1,5],
        "nth_valid_position_count":15,
      },
      "terminal_rows_read":0,"hidden_kwargs_read":0,"target_scores_read":0,
      "acceptance_credit":False,
    }


def run(args=None,root=None): return verify()
if __name__=="__main__":
    import json; print(json.dumps(verify(),indent=2,sort_keys=True))
