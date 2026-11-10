"""Induce a PREDICATE from ONE demonstration. No model. No second example.

THE CLAIM THIS TESTS. In r88 I said a demonstration gives you procedure, never semantics,
because "the shortest one" cannot be named in text. That was half right and half lazy.

What a demonstration actually gives you is MORE than a replay. Watch someone pick one
ticket out of four and the DOM will tell you WHY, if you look at the right place:

    <span class="time-duration" data-duration="7200000">2h 0m</span>
    <button class="buy-ticket" data-price="340">Book for $340</button>

The chosen element differs from the others in exactly one direction on exactly one
quantity. Recover (quantity, direction) and you have the PREDICATE, not the choice. It
then applies to any instance of that task, with different numbers, without another demo.

This is hypothesis selection over observed data -- induction -- and it needs no model
because the hypothesis space is tiny and the data is exact. It is the mechanism that
turns "learned once" into "learned permanently", which is the whole thesis.

THE HONEST LIMIT, built in: if more than one (quantity, direction) explains the choice,
the induction REFUSES rather than picking. A rule that cannot be distinguished from its
rival is a guess, and a guess wearing a rule's clothing is exactly what r68 forbids.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def numeric_profile(element: Mapping[str, Any], dom: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    """Every numeric quantity this element exposes, as a dict of name -> value."""
    out: dict[str, float] = {}
    for k, v in (element.get("attrs") or {}).items():
        if k.startswith("data-"):
            m = _NUM.fullmatch(str(v).strip())
            if m:
                out[k[5:]] = float(m.group(0))
    text = str(element.get("text") or "")
    # "2h 0m" / "$340" / "12:30" -- named by the element's own class when possible
    for cls in str(element.get("cls") or "").split():
        if "duration" in cls:
            h = re.search(r"(\d+)\s*h", text); mnt = re.search(r"(\d+)\s*m", text)
            if h or mnt:
                out.setdefault("duration_text",
                               int(h.group(1)) * 3600 + int(mnt.group(1)) * 60 if h and mnt
                               else (int(h.group(1)) * 3600 if h else int(mnt.group(1)) * 60))
    money = re.search(r"\$(\d+(?:\.\d+)?)", text)
    if money:
        out.setdefault("price_text", float(money.group(1)))

    # MEASURED FAILURE (r105). find-greatest renders the number the goal is ABOUT as the
    # card's bare visible text: <div class="card">2</div>. numeric_profile read data-*
    # attributes, $money and duration text -- and NOT a bare numeral -- so the three cards
    # profiled as {'index': 0}, {'index': 1}, {'index': 2}: their POSITION, not their value.
    # Every chosen card then produced NO_RULE, and the inducer was reported as failing to
    # reason while it had never been shown the quantity. This is r91 in a second place:
    # the extractor, not the reasoner.
    bare = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*", text)
    if bare:
        out.setdefault("text_number", float(bare.group(1)))
    return out


def induce(chosen: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]],
           dom: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Which (quantity, direction) uniquely explains why `chosen` was picked?"""
    key = lambda e: (str(e.get("id") or ""), str(e.get("text") or ""))
    chosen_key = key(chosen)
    prof_c = numeric_profile(chosen, dom)
    others = [e for e in candidates if key(e) != chosen_key]
    if not others:
        return {"status": "NO_CONTRAST", "why": "only one candidate; nothing to compare"}
    prof_o = [numeric_profile(e, dom) for e in others]

    shared = [q for q in prof_c if all(q in p for p in prof_o)]
    rules = []
    for q in shared:
        v = prof_c[q]
        vals = [p[q] for p in prof_o]
        if all(v < x for x in vals):
            rules.append({"quantity": q, "direction": "min", "chosen": v, "others": vals})
        elif all(v > x for x in vals):
            rules.append({"quantity": q, "direction": "max", "chosen": v, "others": vals})

    # MEASURED FAILURE (r89). `data-price` and the "$340" in the button text are the SAME
    # quantity under two names, so a single choice produced two "rival" rules and the
    # induction refused. Dedupe on the VALUES, not the names: two quantities that rank the
    # candidates identically are one quantity as far as this decision is concerned.
    seen: dict[tuple, dict] = {}
    for r in rules:
        sig = (r["direction"], tuple(round(x, 6) for x in [r["chosen"], *r["others"]]))
        seen.setdefault(sig, r)
    rules = list(seen.values())

    if not rules:
        return {"status": "NO_RULE", "why": "no single quantity orders the choice",
                "considered": shared}
    if len(rules) > 1:
        # Refuse: two rival rules fit equally. Distinguishing them needs a second demo.
        return {"status": "AMBIGUOUS", "rules": rules,
                "why": f"{len(rules)} rival rules fit; a second demonstration would separate them",
                "asks_for": "one more example"}
    r = rules[0]
    return {"status": "INDUCED", "rule": r,
            "statement": f"pick the element with the {r['direction']}imum {r['quantity']}"}


def apply_rule(rule: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]],
               dom: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any] | None:
    """Apply an induced rule to a NEW instance. Returns the element to act on, or None."""
    q, d = rule["quantity"], rule["direction"]
    scored = []
    for e in candidates:
        p = numeric_profile(e, dom)
        if q in p:
            scored.append((p[q], e))
    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=(d == "max"))
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None          # a tie is not a decision
    return scored[0][1]


def induce_from_two(obs: Sequence[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]]) -> dict[str, Any]:
    """Resolve ambiguity with a SECOND demonstration instead of guessing.

    A single observation often cannot separate "shortest duration" from "cheapest cost":
    on a random instance the shortest flight is frequently also the cheapest. One more
    demonstration on a DIFFERENT instance separates them, because the two quantities no
    longer co-vary. That is the whole value of a second example, and it is exactly what the
    AMBIGUOUS verdict asks for.

    Refuses if the observations cannot be reconciled -- two demos that imply contradictory
    rules are not evidence, they are a mistake.
    """
    per = [induce(chosen, cands) for chosen, cands in obs]
    induced = [r for r in per if r["status"] == "INDUCED"]
    rules = {(r["rule"]["quantity"], r["rule"]["direction"]) for r in induced}
    if len(rules) == 1:
        q, d = rules.pop()
        return {"status": "INDUCED", "demos": len(obs),
                "rule": {"quantity": q, "direction": d},
                "statement": f"pick the element with the {d}imum {q}",
                "resolved_by": "the demonstrations agree"}
    if len(rules) > 1:
        return {"status": "CONTRADICTORY", "rules": sorted(rules),
                "why": "the demonstrations imply different rules"}
    return {"status": "AMBIGUOUS", "why": "no demonstration separated the rival rules",
            "per_demo": [p["status"] for p in per]}
