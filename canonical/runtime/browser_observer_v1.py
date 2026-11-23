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
            "elements": elements, "sense": sense,
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


def judge(browser: Any, operations: Sequence[Mapping[str, Any]],
          expectation: str) -> dict[str, Any]:
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
    if not wanted.strip():
        return {"schema": SCHEMA, "judged": False, "operations": outcomes,
                "why": "THE_GOAL_STATES_NOTHING_TO_LOOK_FOR"}
    before_text, after_text = before["text"], after["text"]
    present_now = wanted in after_text
    present_before = wanted in before_text
    if present_now and not present_before:
        verdict = "EFFECT_CONFIRMED"
    elif present_now and present_before:
        verdict = "THE_EFFECT_WAS_ALREADY_THERE"
    else:
        verdict = "EFFECT_ABSENT"
    return {"schema": SCHEMA, "judged": True, "verdict": verdict,
            "looked_for": wanted[:200],
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
