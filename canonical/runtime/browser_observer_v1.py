"""A page is judged in its own words, and only before the reload that erases them.

THE PROBLEM THIS SOLVES, measured 2026-11-23 against a real HeadlessChrome:

    op FILL        -> PASS
    op FILL        -> PASS
    op CLICK_TEXT  -> PASS
    page text      -> "Record manager Name Amount Save record"      <- the effect is NOT there

Every operation reported PASS and the click's own handler had run. Two separate defects produced that
result and only one of them was in the click:

1. THE INDEX CARRIED ONLY CONTROLS. `snapshot()` selected `a,button,input,textarea,select,[role=...]`, so a
   `<div>` a handler writes into was never reported. The act succeeded and its consequence was invisible.
   A browser that can act and cannot see what it did is a blind actuator, and §A95 already established that
   a loop confirming on an unseen consequence is worse than no loop at all.

2. RE-NAVIGATING TO OBSERVE DESTROYS THE STATE BEING OBSERVED. `browser_v1.state(url)` navigates and then
   reports, so using it as the read step reloads the page and throws away exactly the form state the act
   produced. Judged that way, a *successful* act reports `effect_present: False`.

So this module separates the three things that were being confused:

    observe   the page as it currently IS -- rendered text plus controls, no navigation
    act       perform operations and report what each returned
    judge     ask the same page, WITHOUT reloading, whether the effect the goal named is now present

It also states the thing `PASS` cannot: `PASS` means the driver completed an operation. It is not evidence
that the world changed. Only the page's own text is evidence of that.

Authority NONE. No model is consulted; the expectation is a string the caller or the goal supplied.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_BROWSER_OBSERVER_V1"

#: An op that only reads. Everything else is assumed to attempt a change, so the observer does not need a
#: table of every verb the driver might grow.
_READ_OPS = frozenset({"NAVIGATE", "WAIT", "SCROLL"})


def regions_of(seen: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The containers on a page, as `observe` reported them, innermost last.

    A region is what a person would point at: a landmark, a section under a heading, a list, anything
    labelled. `label` is the name they would use and `text` is what it holds. Keeping both is what makes
    membership answerable -- `Done` holding `fix login` is a statement about containment, which word order
    can imitate and cannot establish.
    """
    return list(seen.get("regions") or [])


def _smallest_region_holding(regions: Sequence[Mapping[str, Any]],
                            text: str) -> Mapping[str, Any] | None:
    """The innermost **NAMED** region whose text contains `text`.

    TWO CORRECTIONS IN ONE FUNCTION, and the first version got both wrong.

    1. INNERMOST, because every ancestor of a region also contains its text: the page's words contain
       everything, so the outermost match is always the whole page and says nothing about where anything is.
    2. NAMED, because the innermost match at all is the thing ITSELF -- a card `<div>` holding `fix login`
       has that exact text, is the smallest match, and carries no label. Measured 2026-11-23: that returned
       an empty label for both `was_in` and `now_in`, so a placement judge reported "not confirmed" on a
       page where the move had plainly happened. **A thing cannot be its own container**, and the container
       is the nearest ancestor a person could NAME -- which is exactly what `label` records.
    """
    matches = [r for r in regions
               if text and text in str(r.get("text") or "") and str(r.get("label") or "").strip()
               and str(r.get("text") or "").strip() != str(text).strip()]
    if not matches:
        return None
    return min(matches, key=lambda r: (len(str(r.get("text") or "")), -int(r.get("depth") or 0)))


def judge_placement(browser: Any, operations: Sequence[Mapping[str, Any]],
                    thing: str, container: str) -> dict[str, Any]:
    """Judge a goal whose success is a RELATIONSHIP: `thing` must end up inside `container`.

    WHY TEXT WAS NOT ENOUGH. Measured 2026-11-23 on a board holding two identical cards: moving one from
    Todo to Done changes no word and can change no word order, so every judge in §A105 is blind to it. The
    question a person asks -- *is the card in Done* -- is about containment, and containment has to be read
    from structure or it cannot be read at all.

    The verdict requires the relationship to be TRUE AFTER and FALSE BEFORE: a card already in Done is not
    evidence that the act moved it there, exactly as §A105 refuses to confirm a value that was already on
    the page.

    Refuses rather than guesses when the container cannot be found -- a placement judge that cannot locate
    the destination has no question to ask, and inventing one would confirm whatever the page happened to
    look like.
    """
    before = observe(browser)
    if not before.get("ok"):
        return {"schema": SCHEMA, "judged": False, "why": before.get("why") or "THE_PAGE_COULD_NOT_BE_READ"}
    if not regions_of(before):
        return {"schema": SCHEMA, "judged": False,
                "why": "THE_PAGE_REPORTS_NO_REGIONS", "detail": "this driver cannot answer membership"}
    if not any(str(container) == str(r.get("label") or "") for r in regions_of(before)):
        return {"schema": SCHEMA, "judged": False, "why": "THE_CONTAINER_NAMED_IS_NOT_ON_THE_PAGE",
                "container": container,
                "labels": [r.get("label") for r in regions_of(before)][:20]}

    outcomes = run(browser, operations)
    after = observe(browser)

    def where(seen: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return _smallest_region_holding(regions_of(seen), str(thing))

    was, now = where(before), where(after)
    inside_before = bool(was) and str(was.get("label") or "") == str(container)
    inside_now = bool(now) and str(now.get("label") or "") == str(container)
    if inside_now and not inside_before:
        verdict = "PLACEMENT_CONFIRMED"
    elif inside_now and inside_before:
        verdict = "THE_THING_WAS_ALREADY_THERE"
    else:
        verdict = "PLACEMENT_NOT_CONFIRMED"
    return {"schema": SCHEMA, "judged": True, "verdict": verdict,
            "thing": str(thing)[:200], "container": str(container)[:120],
            "was_in": (was or {}).get("label") if was else None,
            "now_in": (now or {}).get("label") if now else None,
            "operations": outcomes,
            "ops_all_passed": all(o.get("status") == "PASS" for o in outcomes)}


def observe(browser: Any, *, max_text: int = 8000) -> dict[str, Any]:
    """The page as it is, with no navigation.

    `rendered_text` is the sense a person uses: the words on the page. `elements` is the sense a person uses
    to act: the things that can be pressed or typed into. Neither alone is enough -- a click needs elements
    and a consequence needs text -- and reporting both is what makes an effect judgeable at all.
    """
    snapshot = browser.snapshot()
    pages = snapshot.get("pages") or []
    if not pages:
        return {"schema": SCHEMA, "ok": False, "why": "NO_PAGE_IS_OPEN"}
    page = pages[0]
    elements = page.get("elements") or []
    text = str(page.get("text") or "")
    if not text:
        # an older driver does not report rendered text; fall back to the words on its controls so a
        # caller is never made worse by this module, and say which sense was used
        text = re.sub(r"\s+", " ", " ".join(
            (element.get("text") or "") + " " + (element.get("aria") or "") + " " +
            (element.get("placeholder") or "") for element in elements)).strip()
        sense = "ELEMENT_WORDS_ONLY"
    else:
        sense = "RENDERED_TEXT"
    return {"schema": SCHEMA, "ok": True, "url": page.get("url") or "",
            "title": page.get("title") or "", "text": text[:max_text],
            "elements": elements, "regions": page.get("regions") or [], "sense": sense,
            "page_count": snapshot.get("page_count", len(pages))}


def run(browser: Any, operations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Perform the operations, reporting what each returned -- and never claiming more than that."""
    outcomes: list[dict[str, Any]] = []
    for operation in operations:
        try:
            result = browser.act(operation)
        except Exception as exc:  # a driver raising is an outcome, not a crash of the loop
            outcomes.append({"type": operation.get("type"), "status": "RAISED",
                             "error": "%s: %s" % (type(exc).__name__, str(exc)[:200])})
            continue
        outcomes.append({"type": operation.get("type"), "status": result.get("status"),
                         "detail": {key: value for key, value in result.items()
                                    if key not in ("schema", "status")}})
    return outcomes


#: The words a goal uses to name a value rather than to describe an action. Quoted spans are the primary
#: source and are read first; these patterns catch the unquoted case. Closed class, and it is about GRAMMAR
#: (this word introduces a value) not about any program or page.
#: A word that introduces a value, and the value itself.
#:
#: `amount`, `value`, `text` and `label` are NOT here any more, and that correction matters. Measured
#: 2026-11-23: `save a record named alpha with amount 4` yielded `['alpha', 'amount']` -- the word `amount`
#: captured AS the value and the real value `4` never extracted. A judge fed that would have confirmed a page
#: containing the word "amount" while the amount itself was wrong, which is worse than refusing: it is a
#: false confirmation wearing the costume of a real one.
#:
#: They were in the list because they appear where a value goes (`amount 4`). But they are NOUNS naming the
#: field, not prepositions introducing the value, and a closed class of introductions must contain only the
#: latter. `with amount 4` is caught by `with`, which is why the removal costs nothing.
_VALUE_INTRO = re.compile(
    r"\b(?:named|called|titled|as|to|into|for|describing|described|labelled|labeled)\s+"
    r"(?P<value>[^\s,;.\"']+)", re.I)

#: Words that NAME a field rather than being one of its values.
_NOT_A_VALUE = frozenset({
    "the", "a", "an", "this", "that", "and", "with", "for", "to", "in", "on", "of", "it",
    "amount", "value", "qty", "quantity", "count", "number", "size", "price",
    "name", "title", "label", "text", "sku", "id", "key", "record", "row", "item",
})

#: A field word followed by a bare value -- `with amount 4`, `qty 8`. The field word is skipped and the
#: token after it is the value. Kept separate from the introductions above because it needs the extra token:
#: `with amount` alone states no value at all, and taking `amount` as the value is the false confirmation
#: this project already caught once.
_FIELD_THEN_VALUE = re.compile(
    r"\b(?:amount|value|qty|quantity|count|number|size|price|name|title|label|text)\s+"
    r"(?P<value>\d+(?:\.\d+)?|[^\s,;.\"']{1,40})", re.I)


def stated_values(goal: str) -> list[str]:
    """The values a goal states, in the order it states them -- the load-bearing part of a request.

    WHY THIS AND NOT THE GOAL'S SENTENCE. Measured 2026-11-23: the goal `save a record named "alpha" with
    amount "4"` has NO verbatim substring in common with the page that fulfils it (`saved alpha = 4`). A
    judge that looked for the goal's words would refuse a page that had done exactly what was asked.

    What a person checks is not whether the page repeats their sentence. It is whether THEIR VALUES landed.
    The quoted spans are the goal's own statement of what those values are, which is why they are read
    first; nothing is inferred and nothing is invented.

    This is the same extraction `mechanism_act_v1._stated_values` performs on a CLI request, applied to a
    page. It does not know what `save` means, and it does not need to: it knows which words the request
    said were the values, and asks the page whether they arrived.
    """
    quoted = [a or b for a, b in re.findall(r'"([^"]*)"|\u201c([^\u201d]*)\u201d', str(goal))]
    if quoted:
        return quoted
    found: list[str] = []
    for pattern in (_VALUE_INTRO, _FIELD_THEN_VALUE):
        for match in pattern.finditer(str(goal)):
            candidate = match.group("value").strip()
            # a FIELD NOUN IS NOT A VALUE. `set qty 8 for sku B2` yielded `['sku','8']` -- `sku` captured
            # as a value because it follows `for`. It names a field, exactly like `amount` did before.
            # A value that is one of these words would be a page/field literally called "sku", which is
            # not worth a false confirmation to support.
            if candidate.lower() in _NOT_A_VALUE or not candidate:
                continue
            if candidate not in found:
                found.append(candidate)
    return found


def judge(browser: Any, operations: Sequence[Mapping[str, Any]],
          expectation: str, *, values: Sequence[str] = ()) -> dict[str, Any]:
    """Act, then ask the page -- WITHOUT reloading -- whether the goal's own words are now on it.

    `before` and `after` are the page's rendered text. The verdict is `EFFECT_CONFIRMED` only when the
    expectation is present in the text after the operations AND was not present before them: an effect that
    was already there is not evidence that the act produced it.

    `PASS` is reported but never trusted. Every operation can succeed and the page can be unchanged; that is
    the failure this module exists to make visible, and it is `EFFECT_ABSENT` with the operations' own
    statuses beside it so the two facts cannot be confused for one another.
    """
    before = observe(browser)
    if not before.get("ok"):
        return {"schema": SCHEMA, "judged": False, "why": before.get("why") or "THE_PAGE_COULD_NOT_BE_READ"}
    outcomes = run(browser, operations)
    after = observe(browser)
    if not after.get("ok"):
        return {"schema": SCHEMA, "judged": False, "why": after.get("why") or "THE_PAGE_COULD_NOT_BE_READ",
                "operations": outcomes}

    wanted = str(expectation or "")
    # THE VERBATIM EXPECTATION IS ONE WAY TO ASK; THE GOAL'S VALUES ARE THE OTHER AND OFTEN THE ONLY ONE.
    # With `values`, the question becomes "did every value the request stated arrive on the page" -- which
    # a page can answer even when it shares no wording with the goal.
    stated = [str(v) for v in values if str(v)]
    if not wanted.strip() and not stated:
        return {"schema": SCHEMA, "judged": False, "operations": outcomes,
                "why": "THE_GOAL_STATES_NOTHING_TO_LOOK_FOR"}
    before_text, after_text = before["text"], after["text"]
    if stated:
        present_now = all(value in after_text for value in stated)
        present_before = all(value in before_text for value in stated)
        wanted = " AND ".join(stated)
    else:
        present_now = wanted in after_text
        present_before = wanted in before_text
    if present_now and not present_before:
        verdict = "EFFECT_CONFIRMED"
    elif present_now and present_before:
        verdict = "THE_EFFECT_WAS_ALREADY_THERE"
    else:
        verdict = "EFFECT_ABSENT"
    return {"schema": SCHEMA, "judged": True, "verdict": verdict,
            "looked_for": wanted[:200], "values": stated,
            "missing_after": [v for v in stated if v not in after_text],
            "before": before_text[:400], "after": after_text[:400],
            "operations": outcomes,
            "ops_all_passed": all(o.get("status") == "PASS" for o in outcomes),
            "sense": before.get("sense")}


def main(argv: Sequence[str] | None = None) -> int:
    """`python -m canonical.runtime.browser_observer_v1 <url> <text-to-look-for>` -- a live check."""
    import json
    import sys

    from . import browser_v1

    arguments = list(argv if argv is not None else sys.argv[1:])
    if len(arguments) < 2:
        print(json.dumps({"schema": SCHEMA,
                          "usage": "browser_observer_v1 <url> <text-to-look-for>"}, indent=1))
        return 0
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": arguments[0]})
    print(json.dumps(judge(browser, [], arguments[1]), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
