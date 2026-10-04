from __future__ import annotations
from collections import Counter

from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_union25_extension_kernel_v1 as ext

SCHEMA="PROJECT_BRAIN_LIVEBENCH_UNION25_CASE_SECTION_INTERACTION_V1"
ARCHETYPES_BLOB="8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a"
EXTENSION_BLOB="d92256d2ebca72e67289e5861fcf8d005a026c0b"
PUBLIC_SPLITTERS=("Section","SECTION")


def forced_case_failure(case_id, splitter):
    if splitter not in PUBLIC_SPLITTERS:
        raise ValueError("UNKNOWN_SPLITTER")
    if case_id==u.ENGLISH_LOWERCASE:
        return True
    if case_id==u.ENGLISH_CAPITAL:
        return splitter=="Section"
    raise ValueError("UNKNOWN_CASE_ID")


def _hard_signature(ids):
    s=set(ids)
    return tuple(i for i in u.ALL_IDS if i in s and i in ext.HARD_EXTRA)


def verify():
    ext.verify()
    rows=u.enumerate_compatible_sets()

    lower_rows=[r for r in rows if u.ENGLISH_LOWERCASE in r and u.SECTIONS in r]
    capital_rows=[r for r in rows if u.ENGLISH_CAPITAL in r and u.SECTIONS in r]
    if len(lower_rows)!=444 or len(capital_rows)!=444:
        raise AssertionError("CASE_SECTION_STRUCTURE_COUNT_DRIFT")

    lower_hard=Counter(_hard_signature(r) for r in lower_rows)
    capital_hard=Counter(_hard_signature(r) for r in capital_rows)
    expected_lower={
        (u.ENGLISH_LOWERCASE,):277,
        (u.KEYWORD_FREQUENCY,u.ENGLISH_LOWERCASE):77,
        (u.LETTER_FREQUENCY,u.ENGLISH_LOWERCASE):77,
        (u.KEYWORD_FREQUENCY,u.LETTER_FREQUENCY,u.ENGLISH_LOWERCASE):13,
    }
    expected_capital={
        (u.ENGLISH_CAPITAL,):277,
        (u.KEYWORD_FREQUENCY,u.ENGLISH_CAPITAL):77,
        (u.LETTER_FREQUENCY,u.ENGLISH_CAPITAL):77,
        (u.KEYWORD_FREQUENCY,u.LETTER_FREQUENCY,u.ENGLISH_CAPITAL):13,
    }
    if dict(lower_hard)!=expected_lower:
        raise AssertionError("LOWER_HARD_SIGNATURE_DRIFT")
    if dict(capital_hard)!=expected_capital:
        raise AssertionError("CAPITAL_HARD_SIGNATURE_DRIFT")

    truth={
        u.ENGLISH_LOWERCASE:{
            s:forced_case_failure(u.ENGLISH_LOWERCASE,s) for s in PUBLIC_SPLITTERS
        },
        u.ENGLISH_CAPITAL:{
            s:forced_case_failure(u.ENGLISH_CAPITAL,s) for s in PUBLIC_SPLITTERS
        },
    }
    expected_truth={
        u.ENGLISH_LOWERCASE:{"Section":True,"SECTION":True},
        u.ENGLISH_CAPITAL:{"Section":True,"SECTION":False},
    }
    if truth!=expected_truth:
        raise AssertionError("CASE_SECTION_TRUTH_DRIFT")

    return {
        "schema":SCHEMA,
        "status":"PASS__CASE_SECTION_MANDATORY_INTERACTION_IDENTIFIED",
        "structural_exposure":{
            "lowercase_plus_sections_sets":len(lower_rows),
            "capital_plus_sections_sets":len(capital_rows),
            "affected_hard_signatures_each":4,
            "lowercase_hard_signature_counts":{
                "|".join(k):v for k,v in sorted(lower_hard.items())
            },
            "capital_hard_signature_counts":{
                "|".join(k):v for k,v in sorted(capital_hard.items())
            },
        },
        "slot_quotient":{
            "section_splitters":list(PUBLIC_SPLITTERS),
            "forced_case_checker_failure_if_section_checker_passes":truth,
        },
        "proof":{
            "section_checker":"A passing section checker requires at least one exact case-sensitive splitter occurrence.",
            "lowercase_checker":"The lowercase checker first requires str.islower(); either public splitter contains uppercase cased letters.",
            "capital_checker":"The capital checker first requires str.isupper(); the mixed-case splitter Section contains lowercase cased letters.",
            "consequence":"The active15 minimum-cut basis is incomplete on these union25 structures and must add this slot-dependent case/section coordinate."
        },
        "next":"INCORPORATE_CASE_SECTION_COORDINATE_IN_UNION25_POINTWISE_PLANNER_AND_VERIFY_EXACT_CHECKERS",
        "credit_delta":0,
    }


def run(args=None,root=None):
    return verify()


if __name__=="__main__":
    import json
    print(json.dumps(verify(),indent=2,sort_keys=True))
