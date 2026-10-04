from __future__ import annotations
from collections import Counter
from itertools import combinations

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as active15
from canonical.runtime import livebench_public_scope_union_v1 as scope

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_INTERACTION_TOPOLOGY_V1"

EXIST="keywords:existence"
FREQ="keywords:frequency"
FORB="keywords:forbidden_words"
LETTER="keywords:letter_frequency"
LANG="language:response_language"
PARA="length_constraints:number_paragraphs"
SENT="length_constraints:number_sentences"
NTH="length_constraints:nth_paragraph_first_word"
PLACE="detectable_content:number_placeholders"
BULLET="detectable_format:number_bullet_lists"
CONSTRAINED="detectable_format:constrained_response"
HIGHLIGHT="detectable_format:number_highlighted_sections"
SECTIONS="detectable_format:multiple_sections"
JSON_ID="detectable_format:json_format"
TITLE="detectable_format:title"
TWO="combination:two_responses"
REPEAT="combination:repeat_prompt"
END="startend:end_checker"
CAPFREQ="change_case:capital_word_frequency"
CAPITAL="change_case:english_capital"
LOWER="change_case:english_lowercase"
NO_COMMA="punctuation:no_comma"
QUOTE="startend:quotation"

EXTRA10=(
    FREQ,LETTER,LANG,PLACE,CONSTRAINED,HIGHLIGHT,
    CAPITAL,LOWER,CAPFREQ,NO_COMMA,
)
EXPECTED_BY_SIZE={1:25,2:203,3:1055,4:3750,5:9526}
EXPECTED_EXTRA_CARD={0:928,1:4317,2:5892,3:2906,4:495,5:21}
EXPECTED_OCC={
    FREQ:3690,LETTER:3938,LANG:809,PLACE:3938,CONSTRAINED:1,
    HIGHLIGHT:2858,CAPITAL:2490,LOWER:2490,CAPFREQ:2738,NO_COMMA:3952,
}


class TopologyError(RuntimeError):
    pass


def conflict_pairs():
    ids=tuple(scope.TABLE4_25)
    universe=set(ids)
    pairs=set()

    def add(a,*bs):
        for b in bs:
            if a!=b:
                pairs.add(frozenset((a,b)))

    add(LANG,SECTIONS,EXIST,FREQ,FORB,END,CAPITAL,LOWER)
    add(PARA,NTH,SENT)
    add(NTH,BULLET,HIGHLIGHT,SECTIONS)
    for x in ids:
        add(CONSTRAINED,x)
    for x in universe-{FORB,EXIST,JSON_ID}:
        add(JSON_ID,x)
    add(SECTIONS,HIGHLIGHT)
    for x in universe-{FORB,EXIST,LANG,TITLE,NO_COMMA,TWO}:
        add(TWO,x)
    for x in universe-{EXIST,TITLE,NO_COMMA,REPEAT}:
        add(REPEAT,x)
    add(CAPFREQ,LOWER,CAPITAL)
    add(LOWER,CAPITAL)
    add(QUOTE,TITLE)

    out=frozenset(pairs)
    if len(out)!=97:
        raise TopologyError("CONFLICT_PAIR_COUNT_DRIFT")
    return out


def compatible(row,pairs):
    return all(frozenset(p) not in pairs for p in combinations(row,2))


def structural_sets():
    ids=tuple(scope.TABLE4_25)
    pairs=conflict_pairs()
    return tuple(
        row
        for k in range(1,6)
        for row in combinations(ids,k)
        if compatible(row,pairs)
    )


def repeat_comma_forces_loss(prompt):
    return "," in str(prompt)


def case_section_forces_case_loss(case_id,splitter):
    if splitter not in ("Section","SECTION"):
        raise TopologyError("BAD_SPLITTER")
    if case_id==LOWER:
        return True
    if case_id==CAPITAL:
        return splitter=="Section"
    raise TopologyError("BAD_CASE_ID")


def verify():
    if len(scope.TABLE4_25)!=25:
        raise TopologyError("UNION25_DRIFT")
    if set(scope.TABLE4_25)-set(active15.ACTIVE_IDS)!=set(EXTRA10):
        raise TopologyError("EXTRA10_DRIFT")

    rows=structural_sets()
    by_size=Counter(map(len,rows))
    if dict(sorted(by_size.items()))!=EXPECTED_BY_SIZE:
        raise TopologyError("SIZE_DISTRIBUTION_DRIFT")
    if len(rows)!=14559:
        raise TopologyError("TOTAL_DRIFT")

    active=set(active15.ACTIVE_IDS)
    extra=set(EXTRA10)
    active_only=tuple(r for r in rows if set(r)<=active)
    with_extra=tuple(r for r in rows if set(r)&extra)
    if len(active_only)!=928 or len(with_extra)!=13631:
        raise TopologyError("ACTIVE_EXTRA_PARTITION_DRIFT")

    by_extra=Counter(len(set(r)&extra) for r in rows)
    if dict(sorted(by_extra.items()))!=EXPECTED_EXTRA_CARD:
        raise TopologyError("EXTRA_CARDINALITY_DRIFT")

    extra_subsets={tuple(sorted(set(r)&extra)) for r in with_extra}
    if len(extra_subsets)!=156:
        raise TopologyError("EXTRA_SUBSET_COUNT_DRIFT")

    occ={x:sum(x in r for r in rows) for x in EXTRA10}
    if occ!=EXPECTED_OCC:
        raise TopologyError("EXTRA_OCCURRENCE_DRIFT")

    constrained=tuple(r for r in rows if CONSTRAINED in r)
    if constrained!=((CONSTRAINED,),):
        raise TopologyError("CONSTRAINED_NOT_SINGLETON")

    json_rows=tuple(r for r in rows if JSON_ID in r)
    if len(json_rows)!=4 or any(set(r)&extra for r in json_rows):
        raise TopologyError("JSON_BRANCH_DRIFT")

    repeat_rows=tuple(r for r in rows if REPEAT in r)
    if len(repeat_rows)!=8:
        raise TopologyError("REPEAT_BRANCH_DRIFT")
    if any(not set(r)<={REPEAT,EXIST,TITLE,NO_COMMA} for r in repeat_rows):
        raise TopologyError("REPEAT_ISOLATION_DRIFT")
    repeat_comma_rows=tuple(r for r in repeat_rows if NO_COMMA in r)
    if len(repeat_comma_rows)!=4:
        raise TopologyError("REPEAT_COMMA_COUNT_DRIFT")

    lower_sections=sum(LOWER in r and SECTIONS in r for r in rows)
    capital_sections=sum(CAPITAL in r and SECTIONS in r for r in rows)
    if (lower_sections,capital_sections)!=(444,444):
        raise TopologyError("CASE_SECTION_COUNT_DRIFT")

    repeat_truth={
        "no_comma":repeat_comma_forces_loss("alpha beta"),
        "comma":repeat_comma_forces_loss("alpha, beta"),
    }
    case_truth={
        LOWER:{s:case_section_forces_case_loss(LOWER,s) for s in ("Section","SECTION")},
        CAPITAL:{s:case_section_forces_case_loss(CAPITAL,s) for s in ("Section","SECTION")},
    }
    if repeat_truth!={"no_comma":False,"comma":True}:
        raise TopologyError("REPEAT_TRUTH_DRIFT")
    if case_truth!={
        LOWER:{"Section":True,"SECTION":True},
        CAPITAL:{"Section":True,"SECTION":False},
    }:
        raise TopologyError("CASE_TRUTH_DRIFT")

    return {
        "schema":SCHEMA,
        "status":"PASS__UNION25_TOPOLOGY_REDUCED",
        "structural":{
            "families":25,
            "conflict_pairs":97,
            "sets":14559,
            "by_size":dict(sorted(by_size.items())),
            "active15_only":len(active_only),
            "with_extra":len(with_extra),
            "extra_cardinality":dict(sorted(by_extra.items())),
            "extra_subsets":len(extra_subsets),
            "extra_occurrences":occ,
            "constrained_sets":len(constrained),
            "json_sets":len(json_rows),
            "repeat_sets":len(repeat_rows),
            "repeat_no_comma_sets":len(repeat_comma_rows),
        },
        "new_loss_coordinates":{
            "repeat_prompt_no_comma":{
                "state_bit":"prompt_contains_comma",
                "forced_loss":repeat_truth,
            },
            "case_multiple_sections":{
                "lowercase_section_structures":lower_sections,
                "capital_section_structures":capital_sections,
                "forced_case_loss_if_section_passes":case_truth,
            },
        },
        "next":"REDUCE_EXTRA10_FREQUENCY_LETTER_CAPITALWORD_LANGUAGE_INTERACTIONS",
        "credit_delta":0,
    }


def run(args=None,root=None):
    return verify()


if __name__=="__main__":
    import json
    print(json.dumps(verify(),indent=2,sort_keys=True))
