#!/usr/bin/env python3
"""Visible-constraint interval normalization for legacy LiveBench IFEval.

This module does not recover hidden kwargs. It compiles visible natural-language
count constraints into integer acceptance intervals, then proves whether a
visible constraint is sufficient for a scorer-side constraint.

Core rule:
    satisfying visible interval V guarantees hidden/scorer interval H iff V ⊆ H.

That correctly handles equivalent off-by-one paraphrases such as
"at most 150 words" -> count <= 150 -> scorer "less than 151",
and stronger visible constraints such as >=400 implying scorer >=336.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_DOMINANCE_COMPILER_V1"

_NUMBER_WORDS = {
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,
    "eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,
    "fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,
    "nineteen":19,"twenty":20,"thirty":30,"forty":40,"fifty":50,
    "sixty":60,"seventy":70,"eighty":80,"ninety":90,
}
_NUM = r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)"

@dataclass(frozen=True)
class IntegerInterval:
    lower: int = 0
    upper: int | None = None
    provenance: str = ""

    def validate(self) -> None:
        if self.lower < 0:
            raise ValueError("NEGATIVE_LOWER_BOUND")
        if self.upper is not None and self.upper < self.lower:
            raise ValueError("EMPTY_INTERVAL")

    def subset_of(self, other: "IntegerInterval") -> bool:
        self.validate(); other.validate()
        lower_ok = self.lower >= other.lower
        upper_ok = other.upper is None or (self.upper is not None and self.upper <= other.upper)
        return lower_ok and upper_ok

    def equivalent_to(self, other: "IntegerInterval") -> bool:
        self.validate(); other.validate()
        return self.lower == other.lower and self.upper == other.upper

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _n(text: str) -> int:
    t=text.strip().lower()
    if t.isdigit(): return int(t)
    if t in _NUMBER_WORDS: return _NUMBER_WORDS[t]
    raise ValueError("UNSUPPORTED_NUMBER_TOKEN")

def scorer_interval(relation: str, threshold: int) -> IntegerInterval:
    relation=str(relation).strip().lower()
    threshold=int(threshold)
    if threshold < 0: raise ValueError("NEGATIVE_THRESHOLD")
    if relation == "at least":
        return IntegerInterval(lower=threshold, upper=None, provenance=f"SCORER_GE_{threshold}")
    if relation == "less than":
        return IntegerInterval(lower=0, upper=threshold-1, provenance=f"SCORER_LT_{threshold}")
    if relation == "exactly":
        return IntegerInterval(lower=threshold, upper=threshold, provenance=f"SCORER_EQ_{threshold}")
    raise ValueError("UNSUPPORTED_SCORER_RELATION")

# Quantity-specific nouns. Deliberately narrow: fail closed rather than bind a
# number from unrelated task content.
_QUANTITY_NOUNS = {
    "words": r"(?:words?|word count)",
    "sentences": r"(?:sentences?)",
    "capital_words": r"(?:words?\s+(?:with\s+)?(?:all\s+)?capital\s+letters|all[- ]caps\s+words?|capitalized\s+words?)",
    "bullets": r"(?:bullet(?:\s+points?)?|bullets?)",
    "placeholders": r"(?:placeholders?)",
    "highlights": r"(?:highlighted\s+(?:sections?|parts?|text\s+sections?)|sections?\s+(?:should\s+be\s+)?highlighted)",
    "sections": r"(?:sections?)",
    "paragraphs": r"(?:paragraphs?)",
}

def _interval_from_relation(rel: str, n: int, provenance: str) -> IntegerInterval:
    rel=rel.upper()
    if rel=="GE": return IntegerInterval(n,None,provenance)
    if rel=="GT": return IntegerInterval(n+1,None,provenance)
    if rel=="LE": return IntegerInterval(0,n,provenance)
    if rel=="LT": return IntegerInterval(0,n-1,provenance)
    if rel=="EQ": return IntegerInterval(n,n,provenance)
    raise ValueError("UNKNOWN_RELATION")

def _candidate_patterns(noun: str) -> list[tuple[str,str]]:
    # Each regex has one named group n and maps directly to an integer relation.
    return [
      (rf"\bat\s+least\s+(?P<n>{_NUM})\s+{noun}\b", "GE"),
      (rf"\b(?P<n>{_NUM})\s*(?:\+|or\s+more)\s+{noun}\b", "GE"),
      (rf"\bmore\s+than\s+(?P<n>{_NUM})\s+{noun}\b", "GT"),
      (rf"\bover\s+(?P<n>{_NUM})\s+{noun}\b", "GT"),
      (rf"\bless\s+than\s+(?P<n>{_NUM})\s+{noun}\b", "LT"),
      (rf"\bfewer\s+than\s+(?P<n>{_NUM})\s+{noun}\b", "LT"),
      (rf"\bunder\s+(?P<n>{_NUM})\s+{noun}\b", "LT"),
      (rf"\bat\s+most\s+(?P<n>{_NUM})\s+{noun}\b", "LE"),
      (rf"\bno\s+more\s+than\s+(?P<n>{_NUM})\s+{noun}\b", "LE"),
      (rf"\b(?P<n>{_NUM})\s+or\s+fewer\s+{noun}\b", "LE"),
      (rf"\bexactly\s+(?P<n>{_NUM})\s+{noun}\b", "EQ"),
      (rf"\b(?P<n>{_NUM})\s+{noun}\s+exactly\b", "EQ"),
    ]

def parse_visible_intervals(text: str, quantity: str) -> dict[str, Any]:
    text=str(text or "")
    noun=_QUANTITY_NOUNS.get(quantity)
    if noun is None:
        raise ValueError("UNSUPPORTED_QUANTITY")
    hits=[]
    occupied=[]
    for pat,rel in _candidate_patterns(noun):
        for m in re.finditer(pat,text,flags=re.IGNORECASE):
            span=m.span()
            if any(not (span[1] <= a or span[0] >= b) for a,b in occupied):
                continue
            n=_n(m.group("n"))
            iv=_interval_from_relation(rel,n,f"VISIBLE_{rel}_{n}")
            if iv.upper is not None and iv.upper < 0:
                continue
            hits.append({
              "start":span[0],"end":span[1],"matched_text":m.group(0),
              "relation":rel,"number":n,"interval":iv.to_dict(),
            })
            occupied.append(span)
    hits.sort(key=lambda x:(x["start"],x["end"]))
    intervals=[IntegerInterval(**h["interval"]) for h in hits]
    if not intervals:
        return {"schema":SCHEMA,"status":"NO_MATCH","quantity":quantity,"matches":[],"intersection":None}
    lo=max(x.lower for x in intervals)
    finite=[x.upper for x in intervals if x.upper is not None]
    hi=min(finite) if finite else None
    if hi is not None and hi < lo:
        return {
          "schema":SCHEMA,"status":"CONTRADICTION","quantity":quantity,
          "matches":hits,"intersection":{"lower":lo,"upper":hi},
        }
    return {
      "schema":SCHEMA,"status":"PASS","quantity":quantity,"matches":hits,
      "intersection":IntegerInterval(lo,hi,"VISIBLE_INTERSECTION").to_dict(),
    }

def prove_visible_implies_scorer(
    text: str,
    quantity: str,
    scorer_relation: str,
    scorer_threshold: int,
) -> dict[str, Any]:
    parsed=parse_visible_intervals(text,quantity)
    hidden=scorer_interval(scorer_relation,scorer_threshold)
    if parsed["status"]!="PASS":
        return {
          "schema":SCHEMA,"status":"UNPROVED","quantity":quantity,
          "visible":parsed,"scorer":hidden.to_dict(),
          "visible_implies_scorer":False,"equivalent":False,
        }
    v=IntegerInterval(**parsed["intersection"])
    implies=v.subset_of(hidden)
    return {
      "schema":SCHEMA,
      "status":"PROVED" if implies else "UNPROVED",
      "quantity":quantity,
      "visible":parsed,
      "scorer":hidden.to_dict(),
      "visible_implies_scorer":implies,
      "equivalent":v.equivalent_to(hidden),
      "strictly_stronger_visible":implies and not v.equivalent_to(hidden),
      "proof_rule":"VISIBLE_ACCEPTANCE_INTERVAL_SUBSET_OF_SCORER_ACCEPTANCE_INTERVAL",
      "hidden_kwargs_required_at_runtime":False,
    }

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args=args or {}
    if "scorer_relation" in args:
        return prove_visible_implies_scorer(
          str(args.get("text") or args.get("prompt") or ""),
          str(args["quantity"]),
          str(args["scorer_relation"]),
          int(args["scorer_threshold"]),
        )
    return parse_visible_intervals(
      str(args.get("text") or args.get("prompt") or ""),
      str(args["quantity"]),
    )

if __name__=="__main__":
    import argparse,json
    ap=argparse.ArgumentParser()
    ap.add_argument("quantity")
    ap.add_argument("text")
    ap.add_argument("--scorer-relation")
    ap.add_argument("--scorer-threshold",type=int)
    ns=ap.parse_args()
    if ns.scorer_relation is not None:
        out=prove_visible_implies_scorer(ns.text,ns.quantity,ns.scorer_relation,ns.scorer_threshold)
    else:
        out=parse_visible_intervals(ns.text,ns.quantity)
    print(json.dumps(out,indent=2,sort_keys=True))
