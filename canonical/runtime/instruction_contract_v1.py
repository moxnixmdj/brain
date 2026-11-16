"""Compile an instruction into a checkable contract, so the verifier stops being missing.

The bottleneck, stated once
---------------------------
Every measurement in this repository hands the machine the judge: the page's own `raw_reward`,
the corpus's own test. In deployment neither exists. Four sessions of evidence and the 2026
literature agree that this is the term that multiplies all the others:

  * OSWorld 2.0 (arXiv:2606.29537): agents spend under 7% of their budget detecting their own
    errors; the failures are verification and state drift.
  * Veritas (arXiv:2611.13336): training-time and test-time self-improvement are gated by the
    same bottleneck, the verifier.
  * VerifierBench (arXiv:2610.28679): generated verifiers reject valid solutions far more
    reliably than they accept invalid ones -- the asymmetry runs the wrong way.
  * Who Verifies the Verifier? (arXiv:2610.11464): a self-evolved grader that passes everything
    trains skills just as well, so downstream score cannot certify a verifier.

`acceptance_clause_v1` already reads a DECLARED contract ("`tests_pass` must be true"). What was
missing is the step before it: a user's instruction in plain words, on a screen, has no declared
contract at all. This module writes one.

The one design decision that makes it possible
----------------------------------------------
For a page whose success value is hidden, the state after a correct action often looks exactly
like the state after a wrong one -- a press ends the episode either way. So a state-only oracle
cannot exist for those tasks, and pretending otherwise would be the "always-pass grader" above.
What CAN be written down is the predicate a person would apply:

    "Click on the \"No\" button."
        -> there is a press, and the element pressed shows "No", and nothing was pressed after.

That is a contract over (observation, action) pairs -- a trace -- and it is checkable with no
reward, no `done` flag and no model. It is also falsifiable in the strong sense: on a trace whose
outcome is known, it can be WRONG IN BOTH DIRECTIONS, and both directions are counted here.

The language (all of it, and it is small on purpose)
---------------------------------------------------
A contract is a conjunction of clauses. Each clause is one operator over the trace or the final
observation:

    CLICK_NAMED      a press on an element whose text/value/label is the named one, last press
    CLICK_ORDINAL    the n-th element of a kind (button / textbox / link / checkbox) was pressed
    CLICK_KIND       any element of a kind was pressed at all
    SELECT_SET       the named elements show as checked/selected at the end
    TYPE_VALUE       a value was typed, produced by `derived_value_v1` (rule recorded) or literal
    ORDER            the pressed elements' numbers are in the instructed order
    NUMBER_PREDICATE a typed number satisfies a stated property (even / odd / negative)

and a REFUSAL for everything else, named, with the missing observable or capability in the name:

    REFUSED__VISUAL_QUANTITY      needs pixels (blocks with no text, counted shapes)
    REFUSED__SPATIAL              drag/into/inside/center/position/angle -- needs geometry
    REFUSED__STYLE_NOT_OBSERVABLE underline/highlight/bold -- the observation has no style field
    REFUSED__CONTINUOUS           "keep hovered", "as many as possible" -- no end state
    REFUSED__FUZZY                "similar to", "best describes" -- no decidable predicate
    REFUSED__MULTI_APP            email/contacts/calendar -- state lives outside the observation

A refusal is not a failure of the compiler and is not hidden: it is the census of what an oracle
would need that this observation cannot supply, and it is the ranked work list.

What this is not
----------------
  * Not an opinion about success. It answers "did the instruction happen?", not "was the answer
    right?" -- for `simple-arithmetic` the contract can verify that `7` was typed, never that
    `7` was correct. That distinction is printed on every contract as `verifies`.
  * Not a model, not learned, not trained, no network, no reward. `K3 = 0`, `$0`.
  * Not complete: 130 real instructions were read to choose these operators, and the ones that
    do not fit are refused BY NAME rather than approximated (see the census in the receipt).
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import derived_value_v1 as derived
from canonical.runtime import observable_descriptor_v1 as descriptor

SCHEMA = "PROJECT_BRAIN_INSTRUCTION_CONTRACT_V1"

PASS = "PASS"
FAIL = "FAIL"
UNCHECKABLE = "UNCHECKABLE"

#: Refusals. Each names what an oracle would need and this observation cannot give.
VISUAL_QUANTITY = "REFUSED__VISUAL_QUANTITY_NEEDS_PIXELS"
#: The instruction quotes a name for a control that appears NOWHERE in the observation. Measured
#: on click-dialog ("clicking the \"x\""): the x is drawn by CSS, so no text, aria-label, title,
#: or id in the observation contains it. Guessing from an unrelated title would be a false
#: accept; the refusal is the truthful answer.
LABEL_NOT_ON_THE_PAGE = "REFUSED__LABEL_NOT_ON_THE_PAGE"
SPATIAL = "REFUSED__SPATIAL_NEEDS_GEOMETRY"
STYLE_NOT_OBSERVABLE = "REFUSED__STYLE_NOT_IN_OBSERVATION"
#: A description names a dimension this observation does not carry -- a colour on a page painted
#: by a stylesheet, a content that is an image. Distinct from SPATIAL, which used to swallow these
#: and thereby hid that the fix was an OBSERVATION, not a coordinate.
OBSERVABLE_ABSENT = "REFUSED__THE_DESCRIPTION_NEEDS_A_DIMENSION_THE_OBSERVATION_LACKS"
CONTINUOUS = "REFUSED__CONTINUOUS_NO_END_STATE"
#: Two instructions in one, joined by "and" ("Expand the section below and click submit"). The
#: refuse-everything reading is only honest if the piece that is undecidable is the whole
#: instruction; here it is not, so the decidable half is compiled and the other half is refused.
PART_LIST = "REFUSED__PART_OF_THE_INSTRUCTION_IS_NOT_OBSERVABLE"
FUZZY = "REFUSED__FUZZY_NO_DECIDABLE_PREDICATE"
MULTI_APP = "REFUSED__MULTI_APP_STATE_OUTSIDE_OBSERVATION"
NO_CLAUSE = "REFUSED__NO_CLAUSE_UNDERSTOOD"

_EDGE = ".,;:!?\"'()[]{}<>"
_QUOTED = re.compile(r'"([^"]+)"|(?<![A-Za-z0-9])\'([^\']+)\'(?![A-Za-z0-9])')
_ORDINAL = r"(1st|2nd|3rd|\d{1,2}th|#\s*\d{1,2})"
_ORDINAL_VALUE = {"1st": 1, "2nd": 2, "3rd": 3}


def plain(text: Any) -> str:
    """Lower-case words with edge punctuation dropped; used for every name comparison."""
    return " ".join(word.strip(_EDGE).lower() for word in str(text or "").split() if word.strip(_EDGE))


def quotes(utterance: str) -> list[str]:
    out: list[str] = []
    for match in _QUOTED.finditer(utterance or ""):
        value = match.group(1) if match.group(1) is not None else match.group(2)
        if value and value not in out:
            out.append(value)
    return out


def ordinal_of(word: str) -> int:
    if word in _ORDINAL_VALUE:
        return _ORDINAL_VALUE[word]
    return int(re.sub(r"\D", "", word) or 0)


def element_label(element: Mapping[str, Any]) -> str:
    """What a person would call this element by: its text, its value, or its accessible names."""
    for field in ("text", "value", "aria-label", "title", "alt", "placeholder", "name"):
        value = str(element.get(field) or "").strip()
        if value:
            return value
    return ""


# --------------------------------------------------------------------------- #
# refusals, decided before any clause is attempted
# --------------------------------------------------------------------------- #
_REFUSALS = (
    # MEASURED 2026-11-16: `drag`, `drop`, `inside`, `into the ... box`, `move the cube` and
    # `position` all used to refuse as SPATIAL. Geometry is NOT missing -- the bridge reports every
    # element's box and the pages present a finite set of addressable elements, so "drag the smaller
    # box into the larger box" is a set to move and a set to move it into. Each of those words is now
    # compiled, and what genuinely needs a continuous coordinate (a freehand line, an angle to
    # construct, a point read off a picture) is stated separately below.
    (re.compile(r"\b(center|centre|mid-?point|angle|draw|line that runs through|"
                r"color ?wheel|colou?r wheel|color ?picker)\b"),
     SPATIAL),
    (re.compile(r"\b(color ?wheel|color ?picker|colou?r wheel)\b"), SPATIAL),
    # "Click on the white colored box": the colour is not in the observation, only in pixels.
    # MEASURED 2026-11-16 and corrected the same day: this pattern used to refuse every
    # "coloured box" instruction as needing pixels. It does not. The bridge reports each element's
    # own fill, so "click on the black colored box" is decidable from the observation; refusing it
    # was a guess dressed as an honesty rule, and it is precisely the error this project's wall
    # diagnosis made when it filed three pages under "budget". The pattern is gone, not narrowed.
    (re.compile(r"\b(hover|keep (?:your|the) mouse|as many .* as possible|while it moves)\b"),
     CONTINUOUS),
    (re.compile(r"\b(underlined|bold|italic|highlight|style)\b"), STYLE_NOT_OBSERVABLE),
    (re.compile(r"\bhow many\b|\btotal number\b|\bcount\b"), VISUAL_QUANTITY),
    (re.compile(r"\b(similar to|best describes|correctly denotes|that best|feel)\b"), FUZZY),
    (re.compile(r"\b(email|message|contact book|calendar|event named|retweet|forward|reply)\b"),
     MULTI_APP),
)


def refusal_for(utterance: str) -> str | None:
    """The first refusal that applies, or None."""

    # A slider, spinner, or dropdown exposes its VALUE in the observation and the instruction
    # names it, so it is decidable (SET_CONTROL). Only colourwheels and free canvases need
    # pixels, and those are refused by the geometry patterns below.
    """The first refusal that applies, or None. Stated before parsing so a refusal cannot be
    lost by a later clause accidentally matching."""
    said = (utterance or "").lower()
    for pattern, code in _REFUSALS:
        if pattern.search(said):
            return code
    return None


# --------------------------------------------------------------------------- #
# the compile step
# --------------------------------------------------------------------------- #
def _kind_of(element: Mapping[str, Any]) -> str:
    tag = str(element.get("tag") or "").lower()
    kind = str(element.get("type") or "").lower()
    if element.get("can_type"):
        return "textbox"
    if tag == "button" or kind in ("submit", "button"):
        return "button"
    if tag == "a":
        return "link"
    if kind in ("checkbox", "radio"):
        return kind
    if tag == "option":
        return "option"
    return tag or "element"


def compile_contract(utterance: str, observation: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one instruction into a conjunction of checkable clauses, or a named refusal.

    Deterministic, no model, no reward. Every clause records its own provenance (the words of the
    instruction that produced it) so a wrong contract can be argued with, not just obeyed. The
    clauses are built in a fixed order, and a press clause records what the instruction required
    BEFORE it, so pressing Submit on a wrong selection or an empty field fails.
    """
    said = " ".join((utterance or "").split())
    low = said.lower()
    contract: dict[str, Any] = {
        "schema": SCHEMA, "instruction": said, "clauses": [], "refusal": None,
        "verifies": "THAT_THE_INSTRUCTION_HAPPENED_NOT_THAT_THE_ANSWER_WAS_RIGHT",
    }
    code = refusal_for(said)
    if code:
        split = _conjunction(said)
        if split:
            for half in split:
                if refusal_for(half) is None:
                    sub = compile_contract(half, observation)
                    if sub["clauses"]:
                        contract["clauses"] += sub["clauses"]
        if contract["clauses"]:
            contract["refusal"] = None
            contract["refused_part"] = code
            contract["verifies"] = (
                "THAT_THE_DECIDABLE_HALF_OF_THE_INSTRUCTION_HAPPENED_NOT_THAT_THE_WHOLE_DID")
        else:
            contract["refusal"] = code
        return contract

    # --------------------------------------------------------------------------------------- #
    # A DESCRIBED TARGET, before any named one. Measured 2026-11-16: 12 pages were refused as
    # "no clause understood" and every one of them described its target by an attribute the
    # observation already carries ("click on a black colored box", "click on a triangle",
    # "drag the smaller box", "all triangles into the black box"). The resolver is a version space
    # over those attributes, so a description that cannot be resolved is refused BY THE MISSING
    # DIMENSION, not as an unknown instruction.
    # --------------------------------------------------------------------------------------- #
    described = _described_action(said, observation)
    if described is not None:
        if described.get("unresolved"):
            contract["refusal"] = described["unresolved"]
            contract["refusal_detail"] = described.get("detail")
            return contract
        contract["clauses"] = [described["clause"]]
        return contract

    fields = [e for e in observation.get("elements") or [] if e.get("can_type")]
    named_set = _named_set(said)
    elements = observation.get("elements") or []

    # 1. what must be typed
    describes_value = bool(re.search(r"\b(starts? with|ends? with|contains?)\b", low))
    if fields and not describes_value and re.search(r"\b(?:enter|type|fill|input|put)\b", low):
        targets = _type_targets(said, observation, fields)
        if targets["value"] is not None:
            for index in targets["indices"]:
                contract["clauses"].append({
                    "operator": "TYPE_VALUE", "index": index, "value": targets["value"],
                    "rule": targets.get("rule"), "provenance": targets["provenance"]})
        elif targets["predicate"]:
            contract["clauses"].append({
                "operator": "NUMBER_PREDICATE", "indices": targets["indices"],
                "predicate": targets["predicate"], "provenance": targets["provenance"]})

    # 1b. a typed value described by a predicate instead of quoted outright:
    #     "Enter an item that starts with \"Sur\" and ends with \"ame\"."
    if fields and re.search(r"\b(starts? with|ends? with|contains?)\b", low):
        parts: list[tuple[str, str]] = []
        for pattern, word in ((r"\bstarts? with\s*\"([^\"]+)\"", "startswith"),
                              (r"\bends? with\s*\"([^\"]+)\"", "endswith"),
                              (r"\bcontains?\s*\"([^\"]+)\"", "contains")):
            for found in re.findall(pattern, said, re.IGNORECASE):
                parts.append((word, found))
        if parts:
            contract["clauses"].append({
                "operator": "TYPE_MATCHING", "index": int(fields[0]["index"]),
                "parts": [value for _kind, value in parts],
                "tests": [kind for kind, _value in parts],
                "provenance": " ".join(f"{kind} {value}" for kind, value in parts)})

    # 1c. several values, each tied to a field named by a nearby word. "Enter the username
    #     \"olin\" and the password \"ULZ\" into the text fields and press login." has TWO values
    #     and TWO fields; typing only the first is not the instruction.
    if len(fields) > 1:
        assignments: list[tuple[int, str]] = []
        for match in re.finditer(r"\b([a-z]{3,})\s*(?::|=|is)?\s*\"([^\"]+)\"", said, re.IGNORECASE):
            word, value = match.group(1).lower(), match.group(2)
            if word in _NOT_A_LABEL or word in _FIELD_STOPWORDS:
                continue
            target = _field_named(observation, word, exclude={i for i, _v in assignments})
            if target is not None:
                assignments.append((target, value))
        if len(assignments) > 1:
            contract["clauses"] = [clause for clause in contract["clauses"]
                                   if clause["operator"] != "TYPE_VALUE"]
            for index, value in assignments:
                contract["clauses"].append({
                    "operator": "TYPE_VALUE", "index": index, "value": value,
                    "provenance": f"field {index} = {value}"})

    # 2. what must be selected. ONE name is as checkable as three: "Select ULZC and click Submit".
    choosable = any(e.get("checked") is not None or e.get("selected") is not None
                    or str(e.get("type") or "").lower() in ("checkbox", "radio")
                    or str(e.get("tag") or "").lower() in ("option", "option-array")
                    for e in elements)
    if (named_set and re.search(r"\bselect\b", low) and choosable
            and not re.search(r"\b(all|every|slider|color|colour)\b", low)):
        contract["clauses"].append({
            "operator": "SELECT_SET", "names": named_set,
            "provenance": f"select {', '.join(named_set)}"})

    # 3. an ordered sequence of presses the instruction spells out
    sequence = _press_sequence(said, observation)
    if sequence:
        contract["clauses"].append({"operator": "PRESS_SEQUENCE", "labels": sequence,
                                    "provenance": f"press in order {sequence}"})

    # 4. the press the instruction names, carrying what had to be true before it
    pending = [clause for clause in contract["clauses"]
               if clause["operator"] in ("TYPE_VALUE", "NUMBER_PREDICATE", "SELECT_SET")]
    needs: dict[str, Any] = {}
    if pending:
        needs = {"kind": pending[0]["operator"], "reason": "WHAT_THE_INSTRUCTION_REQUIRED_FIRST"}
    for name, kind in _named_press_targets(said, observation):
        contract["clauses"].append({
            "operator": "CLICK_NAMED", "name": name, "kind": kind, "needs": needs,
            "provenance": f"press {name}" + (f" ({kind})" if kind else "")})

    # 4a. a menu path: "Select Xaviera>Laurie>Melinde" -- an ordered walk, decidable from the
    # clicks alone. Nothing about pixels or app state is needed.
    if ">" in said and re.search(r"\bselect\b", low):
        path = [part.strip() for part in said.split(">") if part.strip()]
        path = [path[0].split()[-1]] + path[1:] if path and " " in path[0] else path
        if len(path) >= 2:
            contract["clauses"].append({"operator": "PRESS_SEQUENCE", "labels": path,
                                        "provenance": ">".join(path)})

    # 4b. a control set to a named value: "Set the sliders to the combination [10,18,15]",
    # "Select 5 with the spinner". The value lives in the observation, so this is decidable.
    control_word = re.search(r"\b(sliders?|spinners?|dropdown)\b", low)
    if control_word:
        if re.search(r"\bslider", low):
            groups = re.findall(r"\[([^\]]+)\]", said)
            raw = groups[0].split(",") if groups else []
            if not raw:
                raw = re.findall(r"\d+(?:\.\d+)?", said)
            values = [float(token) for token in (part.strip() for part in raw) if token]
        else:
            # "Select 0 with the slider, click the 3rd checkbox, then hit Submit" names two
            # numbers: the slider value and the checkbox ordinal. Only the number the slider
            # clause owns belongs here.
            window = said[max(0, control_word.start() - 40):control_word.end() + 40]
            # "Select 5 with the slider, click the 3rd checkbox" names TWO numbers for two
            # different controls. Drop the ones that an ORDINAL already owns.
            ordinals = {match.group(1) for match in
                        re.finditer(r"(\d{1,2}(?:st|nd|rd|th))", said, re.IGNORECASE)}
            tokens = [token for token in re.findall(r"\d+(?:\.\d+)?", window)
                      if f"{token}th" not in ordinals and f"{token}rd" not in ordinals
                      and f"{token}st" not in ordinals and f"{token}nd" not in ordinals]
            values = [float(token) for token in tokens]
        if values:
            contract["clauses"].append({
                "operator": "SET_CONTROL", "control": control_word.group(1),
                "values": values, "provenance": control_word.group(0) + " " + str(values)})

    # 4b-1. READ_PAIR: "Enter the value of Language into the text field" -- the answer is the
    #     table cell NEXT TO the named cell. Both are in the observation, so this is decidable.
    pair = re.search(r"\bvalue of\s+(.+?)\s+into\b", said, re.IGNORECASE)
    if pair and fields:
        wanted_label = pair.group(1).strip().strip('"').strip()
        neighbour = _table_neighbour(elements, wanted_label)
        if neighbour is not None:
            # the precise reading owns the field: "Enter the value of Language" must not also
            # leave a TYPE_VALUE that types the LABEL ("Color") into it. Measured 2026-11-16.
            contract["clauses"] = [clause for clause in contract["clauses"]
                                   if not (clause["operator"] == "TYPE_VALUE"
                                           and int(clause.get("index", -1)) == int(fields[0]["index"]))]
            contract["clauses"].append({
                "operator": "READ_PAIR", "label": wanted_label, "answer_index": neighbour,
                "index": int(fields[0]["index"]),
                "provenance": f"value of {wanted_label}"})

    # 4b-2. RANK_PICK: "the greatest number" / "the smallest". The numbers are on the page, and
    #     the hidden container is the thing to press. Decidable, no pixels needed.
    rank = re.search(r"\b(greatest|largest|biggest|smallest|least|lowest|highest)\b", low)
    if rank:
        card = _rank_pick(elements, rank.group(1))
        if card is not None:
            contract["clauses"].append({
                "operator": "RANK_PICK", "rank": rank.group(1), "index": card,
                "provenance": rank.group(0)})

    # 4b-3. EXPAND: "Expand the section below" -- open every collapsed container, then continue.
    #     The state that matters is the press, and the press is on the page. Decidable.
    if re.search(r"\bexpand\b", low):
        collapsed = [int(e["index"]) for e in elements
                     if e.get("can_click")
                     and ("collapsed" in str(e.get("classes") or "")
                          or "ui-accordion-header" in str(e.get("classes") or ""))]
        if collapsed:
            contract["clauses"].append({"operator": "EXPAND", "indices": collapsed,
                                        "provenance": "expand the section"})

    # 4c. focus: "Focus into the textbox" -- the observation carries `focused`, so this is a
    # state predicate like any other, not a refusal.
    if re.search(r"\b(focus|focused|focus into|click into)\b", low):
        fields = [int(e["index"]) for e in elements if e.get("can_type")]
        if fields:
            contract["clauses"].append({"operator": "FOCUS", "indices": fields,
                                        "provenance": "focus into the textbox"})

    # 4d. a labelled mode the page's own labels cannot name because the control shows an icon:
    #     'Close the dialog box by clicking the "x"' -- the quoted span IS the label.
    for span in quotes(said):
        if not plain(span) or plain(span) in _NOT_A_LABEL:
            continue
        # A quoted span that is the VALUE to be typed is not a control name; the type clause
        # already owns it ("Enter \"Donovan\" into the text field"). A quoted span that is the
        # VALUE OF A MATCHER ("starts with \"Sur\"", "the link \"ut.\"") is owned by the
        # matcher clause / the find-and-press clause. Decided from the INSTRUCTION and from
        # whether the page shows it, never from the order clauses happen to be emitted in.
        if any(clause["operator"] in ("TYPE_VALUE", "NUMBER_PREDICATE")
               and plain(clause.get("value") or "") == plain(span)
               for clause in contract["clauses"]):
            continue
        if re.search(r"(?:(?:starts?|ends?) with|contains?)\s*[\"\u201c]"
                     + re.escape(span), said, re.IGNORECASE):
            continue
        shown_anywhere = plain(" ".join(str(e.get(field) or "") for e in elements
                                       for field in ("text", "aria-label", "title", "alt", "id",
                                                     "name", "classes", "value")))
        # WHOLE-WORD match. A substring test is not evidence of naming: "x" occurs inside
        # "ui-icon-closethick", and accepting that would be guessing a symbol convention.
        deferred = bool(re.search(r"\b(find|switch between the tabs|expand)\b", low))
        # A quoted span that names a control the page shows is already handled by the named-press
        # clause above; a label clause for the same words would judge one press twice.
        if re.search(r"(?<![a-z0-9])" + re.escape(plain(span)) + r"(?![a-z0-9])",
                     shown_anywhere) is None and not deferred:
            # the page never names this control anywhere in what it can be observed to show
            contract["clauses"] = []
            contract["refusal"] = LABEL_NOT_ON_THE_PAGE
            return contract
        already_named = any(clause["operator"] == "CLICK_NAMED"
                            and plain(clause.get("name") or "") == plain(span)
                            for clause in contract["clauses"])
        if deferred and re.search(r"(?<![a-z0-9])" + re.escape(plain(span)) + r"(?![a-z0-9])",
                                  shown_anywhere) is None:
            # The label is not on the page yet and the instruction says so ("find and click").
            # The clause is deferred: it must surface somewhere in the trace, and then be pressed.
            contract["clauses"].append({"operator": "LABEL_ON_TRACE", "label": span,
                                        "provenance": f"find and press {span}"})
            continue
        if not already_named and not any(clause["operator"] == "CLICK_LABELLED"
                                         for clause in contract["clauses"]):
            contract["clauses"].append({
                "operator": "CLICK_LABELLED", "labels": [span],
                # an icon button shows no text, so the label can also live in aria-label,
                # title, or a class the page uses for the icon ("ui-dialog-titlebar-close")
                "also_match": ["aria-label", "title", "classes", "id", "alt"],
                "provenance": f"press {span}"})

    # 5. a press on an element the page itself labels with a word of the instruction
    if re.search(r"\b(?:click|press|push|hit|tap)\b", low) and not any(
            clause["operator"] in ("CLICK_NAMED", "PRESS_SEQUENCE") for clause in contract["clauses"]):
        labels = _labels_in_instruction(said, observation)
        if labels:
            contract["clauses"].append({"operator": "CLICK_LABELLED", "labels": labels,
                                        "provenance": f"press {labels}"})

    # 6. an ordinal press: "click the 3rd checkbox", "Click on Tab #1"
    # "Click on Tab #1" puts the number after a '#', so the ordinal and the kind are separated by
    # punctuation rather than by a space. Measured 2026-11-16 as a regression to UNCHECKABLE.
    ordinal_pattern = (
        r"\b(?:click|check|select|press)\s+(?:on\s+)?(?:the\s+)?"
        r"(?:(?P<o>" + _ORDINAL + r")\s+(?P<k>checkbox|radio button|textbox|"
        r"button|input textbox|text box|input|link|tab)\b"
        r"|(?P<k2>checkbox|radio button|textbox|button|input textbox|text box|"
        r"input|link|tab)\s*#?\s*(?P<o2>" + _ORDINAL + r"))")
    # A labelled press and an ordinal press CAN both be meant ("click the 3rd checkbox"); the
    # earlier suppression of the ordinal was too broad and dropped a real requirement.
    already_labelled = [plain(label) for clause in contract["clauses"]
                        if clause["operator"] == "CLICK_LABELLED" for label in clause["labels"]]
    for match in re.finditer(ordinal_pattern, low):
        kind_word = match.group("k") or match.group("k2")
        if already_labelled and any(plain(kind_word) in label for label in already_labelled):
            continue
        ordinal_word = match.group("o") or match.group("o2")
        contract["clauses"].append({
            "operator": "CLICK_ORDINAL", "ordinal": ordinal_of(ordinal_word),
            "kind": {"input textbox": "textbox", "input": "textbox", "text box": "textbox",
                     "textbox": "textbox", "radio button": "radio", "button": "button",
                     "checkbox": "checkbox", "link": "link", "tab": "tab"}[kind_word],
            "provenance": match.group(0)})

    # "find and click the 3rd search result": the control is described, not named. What IS
    # decidable is the ordinal -- the third thing pressed after the search. An ordinal with no
    # kind word is therefore kept as ORDINAL_PRESS, judged on position in the trace.
    for match in re.finditer(r"\b(?:click|press|hit|select|choose)\s+(?:on\s+)?(?:the\s+)?"
                             + _ORDINAL + r"\b(?!\s*(?:checkbox|radio|textbox|button|link|tab))",
                             low):
        if any(clause["operator"] in ("CLICK_ORDINAL", "PRESS_SEQUENCE")
               for clause in contract["clauses"]):
            continue
        contract["clauses"].append({
            "operator": "ORDINAL_PRESS", "ordinal": ordinal_of(match.group(1)),
            "provenance": match.group(0)})

    # 7. an order over the numbers of the elements pressed
    if re.search(r"\b(ascending|increasing order|from (?:smallest|lowest)|starting with the lowest)\b", low):
        numeric = [int(e["index"]) for e in elements
                   if e.get("can_click") and re.fullmatch(r"-?\d+", plain(element_label(e)))]
        if numeric:
            numeric.sort(key=lambda index: float(plain(element_label(
                next(e for e in elements if int(e["index"]) == index)))))
            by_index = {int(e["index"]): plain(element_label(e)) for e in elements}
            contract["clauses"].append({
                "operator": "PRESS_SEQUENCE_BY_INDEX", "indices": numeric,
                # a frozen INDEX is not an action: pages rewrite themselves mid-episode and the
                # same index then names a different element. The labels are what stays true.
                "labels": [by_index[index] for index in numeric],
                "provenance": "ascending order"})
            contract["clauses"] = [c for c in contract["clauses"]
                                   if c["operator"] not in ("ORDER", "CLICK_LABELLED")]
        else:
            contract["clauses"].append({"operator": "ORDER", "direction": "ascending",
                                        "provenance": "ascending order"})
    elif re.search(r"\b(descending|decreasing|starting with the (?:highest|largest))\b", low):
        contract["clauses"].append({"operator": "ORDER", "direction": "descending",
                                    "provenance": "descending order"})

    if not contract["clauses"]:
        contract["refusal"] = NO_CLAUSE
    return contract


_DROP_WORDS = re.compile(r"\b(drag|drop|move)\b", re.IGNORECASE)
_INTO_WORDS = re.compile(r"\b(into|inside|in the|to)\b", re.IGNORECASE)

#: The words a description can hang on. If an instruction contains none of them, the resolver has
#: nothing to read and must not be consulted -- otherwise every instruction becomes "describable".
_DESCRIPTOR_CUES = frozenset(
    set(descriptor.COLOUR_WORDS) | set(descriptor.SHAPE_TAGS) | set(descriptor.SIZE_WORDS)
    | set(descriptor.ALIGN_WORDS) | {"colored", "coloured", "color", "colour"}
)


def _described_action(instruction: str, observation: Mapping[str, Any]) -> dict[str, Any] | None:
    """Compile a target that is DESCRIBED rather than named, or refuse by the missing dimension.

    Returns None when the instruction carries no description cue at all -- the resolver must only
    ever be consulted when the words are about an observable dimension.
    """
    low = instruction.lower()
    words = set(re.findall(r"[a-z]+", low))
    # A QUOTED NAME IS A NAME, NOT A DESCRIPTION. "Click the button ... labeled "OK"" describes its
    # subject by an exact string the page shows; handing that to the descriptor resolver deletes the
    # one piece of evidence that identifies it (measured 2026-11-16: click-dialog-2 went from solved
    # to refused because "ok" was read as a size/shape word). The named path already handles quotes.
    if quotes(instruction):
        return None
    if _DROP_WORDS.search(low):
        # A drag names TWO things and either of them may be the described one: "drag ALL BLUE
        # SHAPES into the left box" describes both, "drag the smaller box into the larger box"
        # describes only the target. Gating on the source's cues refused the second case.
        return _described_drag(instruction, observation)
    if not (words & _DESCRIPTOR_CUES):
        return None

    described = descriptor.describe(instruction, observation)
    if described.outcome == descriptor.RESOLVED:
        return {"clause": {"operator": "CLICK_LABELLED", "index": described.subject,
                           "rule": "DESCRIBED_BY_" + "+".join(
                               p["dimension"].upper() for p in described.predicates),
                           "provenance": instruction,
                           "predicates": described.predicates}}
    if described.outcome == descriptor.NOTHING:
        return {"unresolved": LABEL_NOT_ON_THE_PAGE, "detail": described.as_dict()}
    if described.outcome == descriptor.ABSENT:
        return {"unresolved": OBSERVABLE_ABSENT, "detail": described.as_dict()}
    return {"unresolved": OBSERVABLE_ABSENT, "detail": described.as_dict()}


def _direction_drag(instruction: str, observation: Mapping[str, Any],
                    direction: str) -> dict[str, Any] | None:
    """ "Drag the item down ...": one element moves along an axis by the page's own amount."""
    lead = re.search(r"\b(drag|drop|move)\b", instruction.lower())
    source_text = instruction[lead.end():] if lead else instruction
    source_text = re.split(r"\b(up|down|then|and)\b", source_text, maxsplit=1)[0]
    items = descriptor.describe(source_text, observation)
    if items.outcome not in (descriptor.RESOLVED, descriptor.RESOLVED_SET) or not items.members:
        # "the item" names no observable dimension: the page shows exactly one thing that is not a
        # control, and that is a count, not a description.
        movable = [int(e["index"]) for e in observation.get("elements") or []
                   if (e.get("can_click") or e.get("can_type"))
                   and descriptor.area(e) > 0
                   and str(e.get("tag") or "").lower() not in ("button", "input")
                   and str(e.get("text") or "").strip().lower() not in ("submit", "ok", "done")]
        if len(movable) != 1:
            return {"unresolved": OBSERVABLE_ABSENT, "detail": items.as_dict()}
        members = movable
    else:
        members = items.members
    return {"clause": {"operator": "MOVE_DIRECTION", "members": members,
                       "direction": direction, "provenance": instruction}}


def _described_drag(instruction: str, observation: Mapping[str, Any]) -> dict[str, Any] | None:
    """Drag a described set into a described or evidenced target.

    The clause records the two descriptors rather than two indices: WHERE a thing is must not be
    learned as an index, because the pages here renumber their elements between observations.
    """
    low = instruction.lower()
    # "drag X down then press Submit" has no destination element at all: the words are a DIRECTION
    # and the page's own box moves. Measured 2026-11-16 on drag-single-shape / drag-circle.
    direction = re.search(r"\b(up|down)\b", low)
    into = _INTO_WORDS.search(low)
    if into is None:
        if direction is not None:
            return _direction_drag(instruction, observation, direction.group(1))
        return None
    source_text = instruction[:into.start()]
    target_text = instruction[into.end():]
    # the direction word belongs to the action, not to the thing being moved
    for mark in (direction, re.search(r"\b(then|and)\b", source_text)):
        if mark is not None and mark.start() > 0:
            source_text = source_text[:mark.start()]
            break

    items = descriptor.describe(source_text, observation)
    if items.outcome not in (descriptor.RESOLVED, descriptor.RESOLVED_SET) or not items.members:
        return {"unresolved": OBSERVABLE_ABSENT, "detail": items.as_dict()}
    members = items.members

    # The target pool EXCLUDES the moved set: "drag the smaller box into the larger box" is only a
    # comparison when the smaller one is not competing for the word "larger".
    # A thing cannot be dragged INTO the container it is already in. The ancestors of the moved
    # elements are therefore not candidates, which is what keeps the page frame (480x210) from
    # winning "the larger box" on every drag page -- measured 2026-11-16, and it beat the real
    # 58x58 target by a factor of thirty before this rule existed.
    elements = list(observation.get("elements") or [])
    by_index = {int(e["index"]): e for e in elements}
    ancestors = {int(e["index"]) for e in elements
                 if any(descriptor._contained(by_index[m], e) for m in members if m in by_index)}
    pool = [int(e["index"]) for e in elements
            if int(e["index"]) not in members and int(e["index"]) not in ancestors]
    target = descriptor.describe(target_text, observation, pool=pool)
    if target.outcome == descriptor.NOTHING:
        return {"unresolved": OBSERVABLE_ABSENT,
                "detail": {"items": items.as_dict(), "target": target.as_dict()}}
    if target.outcome in (descriptor.NOTHING, descriptor.AMBIGUOUS) and target.missing_dimensions:
        # A description the page cannot answer ("the BLACK box", where the bin carries no fill at
        # all) falls back to the page's own asymmetry -- but only when that asymmetry is unique,
        # and the refusal reason is replaced by what was actually used. A fallback is never allowed
        # to look like a resolution.
        found = descriptor.container_of(observation, inner=members[0] if len(members) == 1 else None)
        if found["outcome"] == descriptor.RESOLVED:
            return {"clause": {"operator": "DRAG_DESCRIBED", "members": members,
                               "target": found["target"],
                               "target_evidence": "PAGE_ASYMMETRY__" + str(found["evidence"]),
                               "unresolved_words": target.residual_words,
                               "rule": "DESCRIBED_BY_" + "+".join(
                                   p["dimension"].upper() for p in items.predicates),
                               "provenance": instruction, "predicates": items.predicates}}
    if target.outcome == descriptor.NOTHING and set(target.residual_words) >= (set(descriptor.SIZE_WORDS)):
        # the only rival was the element being moved, so the comparison is made against it
        target = descriptor.describe(target_text, observation)
    if target.outcome == descriptor.RESOLVED:
        target_index = target.subject
        evidence = "DESCRIBED_TARGET"
    else:
        found = descriptor.container_of(observation)
        if found["outcome"] != descriptor.RESOLVED:
            return {"unresolved": OBSERVABLE_ABSENT,
                    "detail": {"items": items.as_dict(), "target": target.as_dict(),
                               "container": found}}
        target_index = found["target"]
        evidence = found["evidence"]

    return {"clause": {"operator": "DRAG_DESCRIBED", "members": members,
                       "target": target_index, "target_evidence": evidence,
                       "rule": "DESCRIBED_BY_" + "+".join(
                           p["dimension"].upper() for p in items.predicates),
                       "provenance": instruction, "predicates": items.predicates}}


def _conjunction(instruction: str) -> list[str]:
    """"Expand the section below and click submit." -> ["Expand the section below", "click submit"]

    Only an "and"/"then" that joins two INSTRUCTIONS is split. A split that leaves a fragment
    without a verb is not a split, so nothing is invented.
    """
    if re.search(r"\bthen\b", instruction, re.IGNORECASE):
        parts = re.split(r"\bthen\b", instruction, flags=re.IGNORECASE)
    else:
        parts = re.split(r"\band\b", instruction, flags=re.IGNORECASE)
    parts = [part.strip(" ,.") for part in parts if part.strip(" ,.")]
    verbs = re.compile(r"\b(expand|click|press|hit|enter|type|select|choose|pick|submit|fill|"
                       r"find|focus|open|close|set|check)\b", re.IGNORECASE)
    if len(parts) < 2 or not all(verbs.search(part) for part in parts):
        return []
    return parts


def _press_sequence(instruction: str, observation: Mapping[str, Any]) -> list[str]:
    """"Click button ONE, then click button TWO" -> ['ONE', 'TWO'] when the page shows them."""
    if not re.search(r"\bthen\b|\bafter that\b", instruction, re.IGNORECASE):
        return []
    shown = _element_label_set(observation)
    parts = re.split(r"\bthen\b|,|\bafter that\b", instruction, flags=re.IGNORECASE)
    # a path segment is short and names a control ("ONE", "Zoom In"); a segment with a sentence's
    # worth of words is a new instruction, and joining the two into one ordered requirement was a
    # measured false reject ("press Search, then click the 3rd result" -> OUT_OF_ORDER).
    if any(len(part.split()) > 4 for part in parts):
        return []
    found: list[str] = []
    for part in parts:
        best = None
        for word in part.split():
            key = plain(word)
            if key and key in shown and key not in _NOT_A_LABEL and key not in [plain(x) for x in found]:
                if best is None or len(key) > len(plain(best)):
                    best = word.strip(_EDGE)
        if best:
            found.append(best)
    return found if len(found) >= 2 else []


#: Words that appear in an instruction but do not name a control. Deliberately short: a word the
#: page actually shows on a control is a label whether or not it is on this list, and the
#: intersection with the page's own labels is what decides.
_NOT_A_LABEL = frozenset("""
a an the this that these those it its to into from below above
and or then press click hit tap push find go name named labeled labelled which
button buttons link links tab tabs item items box boxes field fields textbox
text input area section sections dialog menu pie list option
""".split())


#: Words that can precede a quoted value without naming a field.
_FIELD_STOPWORDS = frozenset("an item enter type value name".split())


def _field_named(observation: Mapping[str, Any], word: str, *, exclude: set[int]) -> int | None:
    """The field the page associates with `word` (in its id, label, placeholder, or name)."""
    elements = observation.get("elements") or []
    for element in elements:
        if not element.get("can_type") or int(element["index"]) in exclude:
            continue
        blob = plain(" ".join(str(element.get(field) or "")
                              for field in ("id", "name", "placeholder", "aria-label", "title")))
        if word in blob:
            return int(element["index"])
    for element in elements:
        if plain(element.get("tag")) == "label" and word in plain(element.get("text")):
            parent = int(element.get("parent", -1))
            for other in elements:
                if other.get("can_type") and int(other.get("parent", -2)) == parent:
                    if int(other["index"]) not in exclude:
                        return int(other["index"])
    return None


def _table_neighbour(elements: Sequence[Mapping[str, Any]], label: str) -> int | None:
    """The cell's partner: the element after the one that shows `label` in the same row."""
    key = plain(label)
    ordered = sorted(elements, key=lambda e: int(e.get("index", 0)))
    for position, element in enumerate(ordered):
        if plain(element_label(element)) != key:
            continue
        for later in ordered[position + 1:position + 3]:
            text = plain(element_label(later))
            if text and text != key:
                return int(later["index"])
    return None


def _rank_pick(elements: Sequence[Mapping[str, Any]], rank: str) -> int | None:
    """Which pressable container holds the extreme number the instruction asks for."""
    best: tuple[float, int] | None = None
    for element in elements:
        if not element.get("can_click"):
            continue
        numbers = re.findall(r"-?\d+(?:\.\d+)?", str(element.get("full_text")
                                                      or element_label(element) or ""))
        if not numbers:
            continue
        for token in numbers:
            value = float(token)
            if best is None:
                best = (value, int(element["index"]))
            elif rank in ("greatest", "largest", "biggest", "highest") and value > best[0]:
                best = (value, int(element["index"]))
            elif rank in ("smallest", "least", "lowest") and value < best[0]:
                best = (value, int(element["index"]))
    return None if best is None else best[1]


def _element_label_set(observation: Mapping[str, Any]) -> dict[str, list[int]]:
    """Every string the page shows on an element, as label -> indices."""
    out: dict[str, list[int]] = {}
    for element in observation.get("elements") or []:
        for field in ("text", "value", "aria-label", "title", "alt", "id", "name"):
            value = plain(element.get(field))
            if value and len(value) <= 60:
                out.setdefault(value, []).append(int(element["index"]))
    return out


def _labels_in_instruction(instruction: str, observation: Mapping[str, Any]) -> list[str]:
    """Words or quoted spans of the instruction that the PAGE shows on a control.

    The page is the authority on what a control is called, so this is an intersection, not a
    guess. A quoted span is matched exactly and first (the strongest signal); then any word of
    the instruction that is a whole label on the page, longest first, so "button ONE" resolves
    to the control that shows "ONE" rather than to the word "button".
    """
    shown = _element_label_set(observation)
    out: list[str] = []
    for span in quotes(instruction):
        key = plain(span)
        if key in shown and span not in out:
            out.append(span)
    candidates: list[tuple[int, str]] = []
    # quoted phrases are ONE token, and the words of a quoted phrase are never re-scanned
    # separately: the quote already said exactly what it meant.
    unquoted = instruction
    for span in quotes(instruction):
        unquoted = unquoted.replace(f'"{span}"', " ").replace(f"\u201c{span}\u201d", " ")
    # a label that names a FIELD the instruction wanted filled is not a control to press
    field_names = {plain(e.get(field)) for e in observation.get("elements") or []
                   if e.get("can_type")
                   for field in ("id", "name", "placeholder", "aria-label", "title")}
    for word in unquoted.split():
        key = plain(word)
        if not key or key in _NOT_A_LABEL or key in field_names:
            continue
        if key in shown and re.search(r"\b(?:click|press|push|hit|tap|find)\b",
                                      instruction, re.IGNORECASE):
            candidates.append((len(key), word.strip(_EDGE)))
    # a label the page shows that spans several words ("Tab #1", "Long Beach, CA")
    said = plain(instruction)
    for label in shown:
        if len(label.split()) > 1 and label in said and label not in [plain(x) for x in out]:
            candidates.append((len(label), label))
    for length, word in sorted(candidates, reverse=True):
        if plain(word) not in [plain(existing) for existing in out]:
            out.append(word)
    return out


def _named_set(instruction: str) -> list[str]:
    """The comma/and separated names in `Select A, B and C ...`."""
    match = re.search(r"\bselect\s+(.+?)(?:\s+from\b|\s+and\s+(?:click|press|submit)|\s+then\b|\.|$)",
                      instruction, re.IGNORECASE)
    if not match:
        return []
    body = match.group(1)
    parts = re.split(r",\s*|\s+and\s+", body)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) <= 40]


def _type_targets(instruction: str, observation: Mapping[str, Any],
                  fields: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What must be typed, and where. The value comes from `derived_value_v1` when the
    instruction does not state it literally -- which is the whole point of having that algebra."""
    indices = [int(e["index"]) for e in fields]
    ordinal = re.search(r"\b(?:the\s+)?(?:the\s+)?" + _ORDINAL + r"\s+(?:text ?box|input)", instruction, re.IGNORECASE)
    if ordinal:
        n = ordinal_of(ordinal.group(1)) - 1
        if 0 <= n < len(indices):
            indices = [indices[n]]
    named_where = re.search(r"\binto (?:the )?(?:text ?field|textbox|text input|the input)\b",
                            instruction, re.IGNORECASE)
    if named_where and len(indices) > 1:
        indices = [indices[0]]
    if re.search(r"\bboth text fields\b", instruction, re.IGNORECASE):
        indices = indices[:2]

    if not re.search(r"\b(?:enter|type|fill|input|put)\b", instruction, re.IGNORECASE):
        return {"value": None, "indices": indices, "rule": None, "predicate": None,
                "provenance": None}      # nothing is being typed; a quote here names a press target
    quoted = quotes(instruction)
    if quoted:
        candidate = quoted[0]
        # A quote that is a press target ("press \"Search\"") names a control, not a value.
        if plain(candidate) in {plain(element_label(e)) for e in observation.get("elements") or []} \
                and re.search(r"\b(?:press|click|hit|tap)\s+(?:on\s+)?(?:the\s+)?[\"']", instruction,
                              re.IGNORECASE):
            quoted = []
        else:
            quoted = [candidate]
    if quoted:
        value = quoted[0]
        if re.search(r"\ball upper ?case\b|\buppercase\b", instruction, re.IGNORECASE):
            value = value.upper()
        elif re.search(r"\ball lower ?case\b|\blowercase\b", instruction, re.IGNORECASE):
            value = value.lower()
        # a clock or date value may need converting for the field's own type
        field_types = {str(e.get("type") or "").lower() for e in fields}
        if "time" in " ".join(field_types) or re.search(r"\b(time|pm|am)\b", instruction, re.IGNORECASE):
            converted, _ = derived.clock24(instruction)
            if converted:
                value = converted
        return {"value": value, "indices": indices, "rule": "LITERAL_FROM_INSTRUCTION",
                "predicate": None, "provenance": f"quoted {quoted[0]!r}"}

    # a literal that carries its own shape (a date, a number, a time) is a value even without
    # quotes -- "Enter 08/13/2018 as the date and hit submit".
    shaped = re.search(r"\b(\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4})\b", instruction)
    if shaped is None:
        shaped = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", instruction)
    if shaped:
        literal = shaped.group(1)
        # a time field will not take "1:13 PM". The conversion already exists in
        # derived_value_v1 and was simply not applied to the shaped-literal path -- measured
        # 2026-11-16 on enter-time, where "1:13" was typed and the page rejected it.
        if re.search(r":", literal) and re.search(r"\b(am|pm)\b", instruction, re.IGNORECASE):
            converted, _ = derived.clock24(instruction)
            if converted:
                literal = converted
        return {"value": literal, "indices": indices,
                "rule": "SHAPED_LITERAL_FROM_INSTRUCTION", "predicate": None,
                "provenance": f"literal {shaped.group(1)!r}"}

    # no literal: the value must be derived from the page (arithmetic, algebra, last word, ...)
    rows = derived.derivations(observation)
    if rows:
        best = rows[0]
        return {"value": best["value"], "indices": indices, "rule": best["rule"],
                "predicate": None, "provenance": best.get("witness") or best["rule"]}

    predicate = None
    if re.search(r"\beven number\b", instruction, re.IGNORECASE):
        predicate = "even"
    elif re.search(r"\bodd number\b", instruction, re.IGNORECASE):
        predicate = "odd"
    elif re.search(r"\bnegative number\b", instruction, re.IGNORECASE):
        predicate = "negative"
    if predicate:
        return {"value": None, "indices": indices, "rule": None, "predicate": predicate,
                "provenance": predicate}
    return {"value": None, "indices": indices, "rule": None, "predicate": None, "provenance": None}


def _named_press_targets(instruction: str, observation: Mapping[str, Any]
                         ) -> list[tuple[str, str | None]]:
    """Every press the instruction names, in order. A press is named by a quote beside a press
    verb, or by a built-in label ("submit", "login", "cancel") the page itself shows."""
    out: list[tuple[str, str | None]] = []
    label_pool = {(plain(element_label(e))): _kind_of(e)
                  for e in observation.get("elements") or [] if element_label(e)}
    press_words = r"(?:press|click|hit|tap|choose|select)"
    for match in re.finditer(press_words + r"\s+(?:on\s+)?(?:the\s+)?(?:\"([^\"]+)\"|'([^']+)')", instruction,
                             re.IGNORECASE):
        name = match.group(1) if match.group(1) is not None else match.group(2)
        if name and (plain(name), None) not in [(plain(n), k) for n, k in out]:
            out.append((name, label_pool.get(plain(name))))
    for word in ("submit", "login", "sign in", "cancel", "ok", "done"):
        if re.search(r"\b(?:press|click|hit|tap)\s+(?:the\s+)?(?:button\s+)?" + re.escape(word) + r"\b",
                     instruction, re.IGNORECASE):
            if word in label_pool and (plain(label_pool and word), None):
                if not any(plain(n) == word for n, _ in out):
                    out.append((word, "button"))
    return out


# --------------------------------------------------------------------------- #
# the check step
# --------------------------------------------------------------------------- #
def check_contract(contract: Mapping[str, Any], trace: Sequence[tuple[Mapping[str, Any], str]]
                   ) -> dict[str, Any]:
    """Judge a trace against a contract. Returns PASS, FAIL, or UNCHECKABLE with the reason.

    `trace` is [(observation before the action, action string), ...] -- exactly what the
    measurement tools already record. Nothing here reads a reward or a `done` flag.
    """
    if contract.get("refusal"):
        return {"verdict": UNCHECKABLE, "reason": contract["refusal"], "witness": []}
    clauses = contract.get("clauses") or []
    if not clauses:
        return {"verdict": UNCHECKABLE, "reason": NO_CLAUSE, "witness": []}
    # A press clause may depend on another clause's outcome; resolve those first so "pressed
    # Submit on a wrong selection" is judged with the selection's verdict in hand.
    prereq: dict[str, dict[str, Any]] = {}
    for clause in clauses:
        if clause["operator"] in ("SELECT_SET", "TYPE_VALUE", "NUMBER_PREDICATE"):
            prereq[clause["operator"]] = _check_clause(clause, trace)
    for clause in clauses:
        if clause["operator"] == "CLICK_NAMED" and clause.get("needs"):
            need = clause["needs"]
            outcome = prereq.get(need["kind"], {})
            clause = dict(clause)
            clause["needs"] = dict(need, satisfied=outcome.get("verdict") == PASS)
            prereq["_press"] = clause
    resolved = []
    for clause in clauses:
        if clause["operator"] == "CLICK_NAMED" and clause.get("needs"):
            clause = prereq.get("_press", clause)
        resolved.append(_check_clause(clause, trace))
    results = resolved
    failed = [r for r in results if r["verdict"] != PASS]
    verdict = PASS if not failed else FAIL
    return {"verdict": verdict, "reason": None,
            "witness": [r for r in (results if failed else results)],
            "clauses_passed": sum(1 for r in results if r["verdict"] == PASS),
            "clauses_total": len(results)}


def _final(trace: Sequence[tuple[Mapping[str, Any], str]]) -> Mapping[str, Any]:
    return trace[-1][0] if trace else {}


def _check_clause(clause: Mapping[str, Any], trace: Sequence[tuple[Mapping[str, Any], str]]
                  ) -> dict[str, Any]:
    operator = clause["operator"]
    if operator == "CLICK_NAMED":
        return _check_click_named(clause, trace)
    if operator == "PRESS_SEQUENCE_BY_INDEX":
        return _check_press_sequence_by_index(clause, trace)
    if operator == "READ_PAIR":
        return _check_read_pair(clause, trace)
    if operator == "RANK_PICK":
        return _check_rank_pick(clause, trace)
    if operator == "EXPAND":
        return _check_expand(clause, trace)
    if operator == "FOCUS":
        return _check_focus(clause, trace)
    if operator == "SET_CONTROL":
        return _check_set_control(clause, trace)
    if operator == "PRESS_SEQUENCE":
        return _check_press_sequence(clause, trace)
    if operator == "DRAG_DESCRIBED":
        return _check_drag_described(clause, trace)
    if operator == "MOVE_DIRECTION":
        return _check_move_direction(clause, trace)
    if operator == "CLICK_LABELLED":
        return _check_click_labelled(clause, trace)
    if operator == "CLICK_KIND":
        return _check_click_kind(clause, trace)
    if operator == "TYPE_MATCHING":
        return _check_type_matching(clause, trace)
    if operator == "LABEL_ON_TRACE":
        return _check_label_on_trace(clause, trace)
    if operator == "ORDINAL_PRESS":
        return _check_ordinal_press(clause, trace)
    if operator == "CLICK_ORDINAL":
        return _check_click_ordinal(clause, trace)
    if operator == "SELECT_SET":
        return _check_select_set(clause, trace)
    if operator == "TYPE_VALUE":
        return _check_type_value(clause, trace)
    if operator == "NUMBER_PREDICATE":
        return _check_number_predicate(clause, trace)
    if operator == "ORDER":
        return _check_order(clause, trace)
    return {"operator": operator, "verdict": UNCHECKABLE, "reason": "OPERATOR_NOT_IMPLEMENTED"}


def _presses(trace: Sequence[tuple[Mapping[str, Any], str]]):
    for observation, action in trace:
        text = str(action)
        kind, _, rest = text.partition("@")
        if kind in ("click", "triple", "drop"):
            index_text = rest.split("=")[0]
            if index_text.isdigit():
                yield observation, int(index_text)


def _check_click_named(clause, trace) -> dict[str, Any]:
    wanted = plain(clause["name"])
    hits = []
    for observation, index in _presses(trace):
        elements = observation.get("elements") or []
        if 0 <= index < len(elements):
            label = plain(element_label(elements[index]))
            if label and (label == wanted or wanted in label or label in wanted):
                hits.append(index)
    if not hits:
        return {"operator": "CLICK_NAMED", "verdict": FAIL, "reason": f"NEVER_PRESSED:{clause['name']}"}
    # If the instruction exists only to press this control ("press Submit" and nothing else that
    # must precede it), then a press alone is the task -- but if the instruction also names
    # things to select or values to type, choosing the wrong one and pressing Submit is exactly
    # the trace a wrong answer makes. Measured 2026-11-16 as a false accept on choose-list.
    if clause.get("needs") and not clause["needs"].get("satisfied"):
        return {"operator": "CLICK_NAMED", "verdict": FAIL,
                "reason": f"PRESSED_{clause['name'].upper()}_WITHOUT_{clause['needs']['reason']}"}
    # the named press must be the LAST press, so a correct press followed by a wrong one fails
    last = list(_presses(trace))[-1][1] if list(_presses(trace)) else None
    if clause.get("kind") is None and last is not None and last not in hits:
        return {"operator": "CLICK_NAMED", "verdict": FAIL,
                "reason": f"PRESSED_SOMETHING_ELSE_AFTER:{last}"}
    return {"operator": "CLICK_NAMED", "verdict": PASS, "witness": hits[-1]}


def _check_read_pair(clause, trace) -> dict[str, Any]:
    """"the value of X" -> the field holds the cell that sits beside X."""
    index = int(clause["index"])
    answer = None
    for observation, _action in trace:
        elements = observation.get("elements") or []
        partner = _table_neighbour(elements, clause["label"])
        if partner is None:
            continue
        answer = plain(element_label(elements[partner]))
        if index < len(elements) and plain(elements[index].get("value")) == answer:
            return {"operator": "READ_PAIR", "verdict": PASS, "witness": f"{clause['label']}={answer}"}
    if answer is None:
        return {"operator": "READ_PAIR", "verdict": FAIL, "reason": "THE_NAMED_CELL_IS_NOT_ON_THE_PAGE"}
    return {"operator": "READ_PAIR", "verdict": FAIL,
            "reason": f"FIELD_DOES_NOT_HOLD_THE_NEIGHBOUR:{answer}"}


def _check_rank_pick(clause, trace) -> dict[str, Any]:
    """The extreme card was pressed."""
    wanted = clause["index"]
    for observation, action in trace:
        match = re.fullmatch(r"(?:click|triple)@(\d+)", str(action or ""))
        if match and int(match.group(1)) == int(wanted):
            return {"operator": "RANK_PICK", "verdict": PASS, "witness": int(wanted)}
    return {"operator": "RANK_PICK", "verdict": FAIL,
            "reason": f"THE_{clause['rank'].upper()}_CARD_WAS_NEVER_PRESSED"}


def _check_drag_described(clause, trace) -> dict[str, Any]:
    """Every named member was grabbed and let go inside the target's box, by the boxes present.

    A drag is checked against GEOMETRY, not against an index: the page may renumber its elements
    between the observation the clause was written on and the observation the drop happened in.
    """
    final = _final(trace)
    elements = {int(e["index"]): e for e in final.get("elements") or []}
    target = int(clause.get("target") or -1)
    target_box = (elements.get(target) or {}).get("box")
    moved = []
    for observation, action in trace:
        text = str(action)
        if not text.startswith("drop@"):
            continue
        index = int(text.split("@")[1])
        element = (observation.get("elements") or [{}] * (index + 1))[index] \
            if index < len(observation.get("elements") or []) else {}
        if not isinstance(target_box, (list, tuple)) or len(target_box) != 4:
            continue
        if descriptor._contained(element, {"box": target_box}):
            moved.append(index)
    members = {int(m) for m in clause.get("members") or []}
    leftover = [m for m in members
                if m in elements and isinstance(target_box, (list, tuple)) and len(target_box) == 4
                and not descriptor._contained(elements[m], {"box": target_box})]
    verdict = PASS if not leftover else FAIL
    return {"clause": clause.get("operator"), "verdict": verdict,
            "why": "EVERY_NAMED_THING_ENDED_INSIDE_THE_TARGET" if verdict == PASS
            else "SOMETHING_NAMED_DID_NOT_END_INSIDE_THE_TARGET",
            "dropped_inside": moved, "not_inside": leftover}


def _check_move_direction(clause, trace) -> dict[str, Any]:
    """The named thing moved at least one box height in the stated direction."""
    first = (trace[0][0] if trace else {})
    final = _final(trace)
    before = {int(e["index"]): e for e in first.get("elements") or []}
    after = {int(e["index"]): e for e in final.get("elements") or []}
    direction = str(clause.get("direction") or "")
    moved = []
    for member in clause.get("members") or []:
        a, b = before.get(int(member)), after.get(int(member))
        if not a or not b:
            continue
        box_a, box_b = a.get("box"), b.get("box")
        if not (isinstance(box_a, (list, tuple)) and isinstance(box_b, (list, tuple))):
            continue
        delta = float(box_b[1]) - float(box_a[1])
        if (direction == "down" and delta > 0) or (direction == "up" and delta < 0):
            moved.append(int(member))
    named = [int(m) for m in clause.get("members") or []]
    verdict = PASS if named and len(moved) == len(named) else FAIL
    return {"clause": clause.get("operator"), "verdict": verdict, "moved": moved,
            "why": "EVERY_NAMED_THING_MOVED_THE_STATED_WAY" if verdict == PASS
            else "SOMETHING_NAMED_DID_NOT_MOVE_THE_STATED_WAY"}


def _check_press_sequence_by_index(clause, trace) -> dict[str, Any]:
    """The given elements were pressed, in exactly this order (ascending numbers, top to bottom)."""
    wanted = [int(index) for index in clause["indices"]]
    pressed: list[int] = []
    for observation, action in trace:
        match = re.fullmatch(r"(?:click|triple)@(\d+)", str(action or ""))
        if match:
            pressed.append(int(match.group(1)))
    hits = [index for index in pressed if index in wanted]
    if hits == wanted[:len(hits)] and len(hits) == len(wanted):
        return {"operator": "PRESS_SEQUENCE_BY_INDEX", "verdict": PASS, "witness": hits}
    return {"operator": "PRESS_SEQUENCE_BY_INDEX", "verdict": FAIL,
            "reason": f"PRESSED_{hits}_WANTED_{wanted}"}


def _contains_word(blob: str, word: str) -> bool:
    if not word:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", blob) is not None


def _check_expand(clause, trace) -> dict[str, Any]:
    """An element that was collapsed when the episode began has been pressed."""
    wanted = {int(index) for index in clause["indices"]}
    for observation, action in trace:
        match = re.fullmatch(r"(?:click|triple)@(\d+)", str(action or ""))
        if match and int(match.group(1)) in wanted:
            return {"operator": "EXPAND", "verdict": PASS, "witness": int(match.group(1))}
    return {"operator": "EXPAND", "verdict": FAIL, "reason": "NOTHING_WAS_EXPANDED"}


def _check_focus(clause, trace) -> dict[str, Any]:
    """One of the instruction's fields took the focus -- read from the state OR from the action.

    focus-text.html rewards *inside* its focus handler and calls `this.blur()` in the same
    breath, so the observation recorded after the success can never show `focused`. A contract
    that only read state would call a correct trace wrong. Pressing a field is the act of
    focusing it, so the press itself is admissible evidence -- and pressing anything else is not.
    """
    wanted = {int(index) for index in clause["indices"]}
    for observation, action in trace:
        elements = observation.get("elements") or []
        for element in elements:
            if int(element.get("index", -1)) in wanted and element.get("focused"):
                return {"operator": "FOCUS", "verdict": PASS,
                        "witness": f"STATE_FOCUSED:{int(element['index'])}"}
        match = (re.fullmatch(r"(?:click|triple|grab)@(\d+)", str(action or ""))
                 or re.fullmatch(r"type@(\d+)=.*", str(action or ""), re.DOTALL))
        if match and int(match.group(1)) in wanted:
            pressed = elements[int(match.group(1))] if int(match.group(1)) < len(elements) else {}
            if pressed.get("can_type"):
                return {"operator": "FOCUS", "verdict": PASS,
                        "witness": f"FOCUS_BY_PRESS:{int(match.group(1))}"}
    return {"operator": "FOCUS", "verdict": FAIL, "reason": "NO_FIELD_EVER_FOCUSED"}


def _check_set_control(clause, trace) -> dict[str, Any]:
    """A slider/spinner/select ends holding the value the instruction named.

    This is decided by reading the final observation, NOT by geometry: the earlier refusal of
    every slider page was wrong, and it excluded a whole family of instructions that are exactly
    as checkable as "type this text".
    """
    wanted = clause["values"]
    # MiniWoB++ spinners are plain <input> with no type attribute and the value in `value`; a
    # filter on type/tag alone found nothing and failed a correct trace. A control is any
    # element that CARRIES A NUMERIC VALUE and can be changed.
    final = _control_values(_final(trace))
    seen = [value for observation, _action in trace for value in _control_values(observation)]
    reached = final or seen
    if not reached:
        return {"operator": "SET_CONTROL", "verdict": FAIL, "reason": "NO_CONTROL_VALUE_OBSERVED"}
    if len(wanted) == 1:
        ok = any(abs(value - wanted[0]) < 1e-6 for value in reached)
        if ok:
            return {"operator": "SET_CONTROL", "verdict": PASS, "witness": reached}
        # a slider is dragged, so an intermediate landing is not the end state; only the final
        # observation of the last episode step counts
        return {"operator": "SET_CONTROL", "verdict": FAIL,
                "reason": f"WRONG_VALUE:{reached}_WANTED:{wanted}"}
    if len(reached) >= len(wanted):
        tail = reached[-len(wanted):]
        for index, want in enumerate(wanted):
            if abs(tail[index] - want) > 1e-6:
                return {"operator": "SET_CONTROL", "verdict": FAIL,
                        "reason": f"WRONG_VALUE_AT_{index}:{tail[index]}_WANTED:{want}"}
        return {"operator": "SET_CONTROL", "verdict": PASS, "witness": tail}
    return {"operator": "SET_CONTROL", "verdict": FAIL,
            "reason": f"ONLY_{len(reached)}_OF_{len(wanted)}_CONTROLS_OBSERVED"}


def _control_values(observation: Mapping[str, Any]) -> list[float]:
    """The numeric values the observation shows for settable controls.

    A jQuery slider has no input: its value is DISPLAYED in a separate element and changed by
    dragging or by the arrow keys. Reading only form controls found nothing (measured 2026-11-16
    on use-slider, whose only numeric element is a div showing "107").
    """
    out: list[float] = []
    for element in observation.get("elements") or []:
        displayed = re.findall(r"-?\d+(?:\.\d+)?", str(element.get("text") or ""))
        if displayed and (element.get("can_click") or element.get("can_type")):
            out.append(float(displayed[0]))
        tag = str(element.get("tag") or "").lower()
        kind = str(element.get("type") or "").lower()
        settable = (bool(element.get("can_type")) or bool(element.get("can_click"))
                    or tag in ("input", "select", "option", "option-array")
                    or kind in ("range", "slider", "spinner", "number", "select-one", "dropdown"))
        if not settable:
            continue
        for number in _numbers([element.get("value")]):
            out.append(number)
    return out


def _numbers(values: Sequence[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        for token in re.findall(r"-?\d+(?:\.\d+)?", str(value if value is not None else "")):
            out.append(float(token))
    return out


def _check_press_sequence(clause, trace) -> dict[str, Any]:
    """The named controls were pressed, and in the order the instruction gave.

    This is the clause a state-only oracle cannot express at all: the end state of "ONE then TWO"
    and of "TWO then ONE" is the same page.
    """
    wanted = [plain(label) for label in clause["labels"]]
    seen: list[str] = []
    for observation, index in _presses(trace):
        elements = observation.get("elements") or []
        if not 0 <= index < len(elements):
            continue
        label = plain(element_label(elements[index]))
        if label in wanted:
            seen.append(label)
    if seen != wanted[:len(seen)]:
        return {"operator": "PRESS_SEQUENCE", "verdict": FAIL,
                "reason": f"OUT_OF_ORDER:{seen}"}
    if len(seen) < len(wanted):
        return {"operator": "PRESS_SEQUENCE", "verdict": FAIL,
                "reason": f"MISSING_PRESSES:{wanted[len(seen):]}"}
    return {"operator": "PRESS_SEQUENCE", "verdict": PASS, "witness": seen}


def _check_click_labelled(clause, trace) -> dict[str, Any]:
    """One of the named labels was pressed, and it was the last press (so pressing the right
    control and then a wrong one fails, which is the case a state-only oracle cannot see)."""
    # A clause written by the DESCRIPTOR path carries one `index` and no label list: its subject
    # was identified by an attribute ("the black box"), not by a name, so it is checked by the
    # element it actually names rather than by text.
    if "labels" not in clause and clause.get("index") is not None:
        presses = list(_presses(trace))
        hit = [i for _, i in presses if i == int(clause["index"])]
        return {"operator": "CLICK_LABELLED", "verdict": PASS if hit else FAIL,
                "reason": "THE_DESCRIBED_ELEMENT_WAS_PRESSED" if hit
                else "THE_DESCRIBED_ELEMENT_WAS_NOT_PRESSED",
                "rule": clause.get("rule"), "pressed": hit}
    wanted = [plain(label) for label in clause["labels"]]
    presses = list(_presses(trace))
    hits = []
    for observation, index in presses:
        elements = observation.get("elements") or []
        if not 0 <= index < len(elements):
            continue
        label = plain(element_label(elements[index]))
        if label and any(label == w or label in w or w in label for w in wanted):
            hits.append(index)
    if not hits:
        return {"operator": "CLICK_LABELLED", "verdict": FAIL,
                "reason": f"NEVER_PRESSED_ANY_OF:{clause['labels']}"}
    # Pressing the right control and then something unrelated fails; but when the instruction
    # itself contains a later press ("... and press 'Search', then click the 3rd result") the
    # later press is accounted for by another clause, so it is not evidence against this one.
    accounted = set(int(index) for index in clause.get("accounted_after") or [])
    later = [index for _observation, index in presses[presses.index(min(
        ((p for p in presses if p[1] in hits)), key=lambda p: p[0], default=presses[-1])) + 1:]
        if index not in accounted and index not in hits]
    if later and not clause.get("allow_later"):
        return {"operator": "CLICK_LABELLED", "verdict": FAIL,
                "reason": f"PRESSED_SOMETHING_ELSE_AFTER:{later[-1]}"}
    return {"operator": "CLICK_LABELLED", "verdict": PASS, "witness": hits[-1]}


def _check_type_matching(clause, trace) -> dict[str, Any]:
    """The field's value satisfies every quoted constraint the instruction gave."""
    index = int(clause["index"])
    for test, part in zip(clause["tests"], clause["parts"]):
        wanted = plain(part)
        seen = []
        for observation, _action in trace:
            elements = observation.get("elements") or []
            if 0 <= index < len(elements):
                seen.append(plain(elements[index].get("value")))
        found = [value for value in seen if _satisfies(test, value, wanted)]
        if not found:
            return {"operator": "TYPE_MATCHING", "verdict": FAIL,
                    "reason": f"NO_TYPED_VALUE_{test.upper()}_{part}"}
    return {"operator": "TYPE_MATCHING", "verdict": PASS,
            "witness": f"SATISFIED_{clause['tests']}"}


def _satisfies(test: str, value: str, wanted: str) -> bool:
    if not value:
        return False
    if test == "startswith":
        return value.startswith(wanted)
    if test == "endswith":
        return value.endswith(wanted)
    return wanted in value


def _check_label_on_trace(clause, trace) -> dict[str, Any]:
    """A control the instruction told the agent to FIND: it appears, then it is pressed."""
    wanted = plain(clause["label"])
    appeared = False
    for observation, action in trace:
        elements = observation.get("elements") or []
        match = re.fullmatch(r"(?:click|triple)@(\d+)", str(action or ""))
        if match and int(match.group(1)) < len(elements):
            element = elements[int(match.group(1))]
            # WHOLE WORDS. A substring test made "ut" match "vulputate." and the wrong link was
            # pressed -- measured 2026-11-16 on click-tab-2-easy, a false accept waiting to be
            # recorded as a skill.
            blob = plain(" ".join(str(element.get(field) or "")
                                  for field in ("text", "full_text", "value",
                                                "aria-label", "title")))
            if wanted and _contains_word(blob, wanted):
                return {"operator": "LABEL_ON_TRACE", "verdict": PASS,
                        "witness": f"PRESSED_AFTER_FINDING:{int(match.group(1))}"}
        for element in elements:
            if wanted and wanted in plain(element_label(element) + " " +
                                          str(element.get("full_text") or "")):
                appeared = True
    outcome = "APPEARED_BUT_NEVER_PRESSED" if appeared else "NEVER_APPEARED"
    return {"operator": "LABEL_ON_TRACE", "verdict": FAIL, "reason": f"LABEL_{outcome}"}


def _check_ordinal_press(clause, trace) -> dict[str, Any]:
    """"the 3rd search result" -> the n-th pressable thing of its kind ON THE PAGE when pressed.

    My first attempt counted presses in sequence, which is not what the words say: the plan that
    the page scores as a success presses ONE result, the third one listed. The ordinal is a
    position among the candidates visible at the moment of the press, so it is decided exactly,
    from the observation, with no guessing about what a "result" is -- the pressed element's own
    tag supplies the kind.
    """
    n = int(clause["ordinal"])
    for observation, action in trace:
        match = re.fullmatch(r"(?:click|triple)@(\d+)", str(action or ""))
        if not match:
            continue
        index = int(match.group(1))
        elements = observation.get("elements") or []
        if not 0 <= index < len(elements):
            continue
        pressed = elements[index]
        same = [e for e in elements
                if str(e.get("tag")) == str(pressed.get("tag"))
                and (e.get("can_click") or e.get("can_type"))]
        if len(same) >= n and int(same[n - 1]["index"]) == index:
            return {"operator": "ORDINAL_PRESS", "verdict": PASS,
                    "witness": f"{n}_OF_{len(same)}_{pressed.get('tag')}@{index}"}
    return {"operator": "ORDINAL_PRESS", "verdict": FAIL,
            "reason": f"NO_PRESS_WAS_THE_{n}_TH_OF_ITS_KIND"}


def _check_click_kind(clause, trace) -> dict[str, Any]:
    for observation, index in _presses(trace):
        elements = observation.get("elements") or []
        if 0 <= index < len(elements) and _kind_of(elements[index]) in clause["kinds"]:
            return {"operator": "CLICK_KIND", "verdict": PASS, "witness": index}
    return {"operator": "CLICK_KIND", "verdict": FAIL, "reason": f"NO_{clause['kinds']}_PRESSED"}


def _check_click_ordinal(clause, trace) -> dict[str, Any]:
    kind, n = clause["kind"], int(clause["ordinal"])
    for observation, index in _presses(trace):
        elements = observation.get("elements") or []
        same = [e["index"] for e in elements if _kind_of(e) == kind]
        if 0 < n <= len(same) and same[n - 1] == index:
            return {"operator": "CLICK_ORDINAL", "verdict": PASS, "witness": index}
    return {"operator": "CLICK_ORDINAL", "verdict": FAIL,
            "reason": f"THE_{n}_TH_{kind.upper()}_WAS_NEVER_PRESSED"}


def _choosable(elements: Sequence[Mapping[str, Any]], index: int) -> list[int]:
    """The elements that carry the chosen state for the thing at `index`.

    A label shows the name; the checkbox it stands for is a different element (`for=`/id, a
    child, or the sibling that follows). Measured 2026-11-16: reading `checked` off the labelled
    element itself found nothing and produced a false reject on a correct trace.
    """
    out = [index]
    element = elements[index] if 0 <= index < len(elements) else {}
    ids = {str(e.get("id")): int(e["index"]) for e in elements if e.get("id")}
    target = ids.get(str(element.get("for") or ""))
    if target is not None:
        out.append(target)
    if index + 1 < len(elements):
        sibling = elements[index + 1]
        if str(sibling.get("type") or "").lower() in ("checkbox", "radio") or sibling.get("checked") is not None:
            out.append(int(sibling["index"]))
    for other in elements:
        if int(other.get("parent", -1)) == index:
            out.append(int(other["index"]))
    return out


def _chosen_labels(elements: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every label that stands for something currently checked or selected.

    The association runs in BOTH directions, because both occur: a checkbox that is a CHILD of
    its label (MiniWoB++), and a label that points at its input with `for=`/id. Measured
    2026-11-16: looking only sideways found nothing and rejected a correct trace.
    """
    by_index = {int(e["index"]): e for e in elements}
    labels: list[str] = []
    for element in elements:
        if not (element.get("checked") or element.get("selected")):
            continue
        candidates = [element]
        # ancestors: a checkbox inside <label>NAME</label> is named by the label above it
        cursor = int(element.get("parent", -1))
        depth = 0
        while cursor in by_index and depth < 4:
            candidates.append(by_index[cursor])
            cursor = int(by_index[cursor].get("parent", -1))
            depth += 1
        # children: a label that wraps the input
        candidates += [e for e in elements if int(e.get("parent", -1)) == int(element["index"])]
        # an explicit label[for=id]
        ids = {str(e.get("id")): int(e["index"]) for e in elements if e.get("id")}
        candidates += [e for e in elements
                       if str(e.get("for") or "") and ids.get(str(e.get("for"))) == int(element["index"])]
        for candidate in candidates:
            label = plain(element_label(candidate))
            if label and label not in labels and "." not in label and len(label) <= 40:
                labels.append(label)
    return labels


def _check_select_set(clause, trace) -> dict[str, Any]:
    """Every observation in the trace is inspected, not just the last.

    Measured 2026-11-16: a press on Submit ends the episode and the page replaces itself with a
    fresh look-alike, so the checked state is GONE from the final observation while the selection
    really happened. Reading only the last observation produced a false reject on a trace the
    page scored as a success.
    """
    wanted = [plain(n) for n in clause["names"]]
    shown: list[str] = []
    for observation, _action in trace:
        for label in _chosen_labels(observation.get("elements") or []):
            if label not in shown:
                shown.append(label)
    for label in _chosen_labels(_final(trace).get("elements") or []):
        if label not in shown:
            shown.append(label)
    missing = [name for name in wanted if not any(name == s or name in s or s in name for s in shown if s)]
    if missing:
        return {"operator": "SELECT_SET", "verdict": FAIL, "reason": f"NOT_SELECTED:{','.join(missing)}"}
    return {"operator": "SELECT_SET", "verdict": PASS, "witness": shown}


def _check_type_value(clause, trace) -> dict[str, Any]:
    wanted = str(clause["value"])
    for observation, action in trace:
        text = str(action)
        if not text.startswith("type@"):
            continue
        head, _, payload = text.partition("=")
        index = head[5:]
        if clause.get("index") is not None and index.isdigit() and int(index) != int(clause["index"]):
            continue
        if payload.strip() == wanted.strip():
            return {"operator": "TYPE_VALUE", "verdict": PASS, "witness": payload}
    return {"operator": "TYPE_VALUE", "verdict": FAIL, "reason": f"NEVER_TYPED:{wanted!r}"}


def _check_number_predicate(clause, trace) -> dict[str, Any]:
    predicate = clause["predicate"]
    for _observation, action in trace:
        text = str(action)
        if not text.startswith("type@"):
            continue
        _head, _, payload = text.partition("=")
        try:
            number = int(str(payload).strip())
        except ValueError:
            continue
        if predicate == "even" and number % 2 == 0:
            return {"operator": "NUMBER_PREDICATE", "verdict": PASS, "witness": number}
        if predicate == "odd" and number % 2 != 0:
            return {"operator": "NUMBER_PREDICATE", "verdict": PASS, "witness": number}
        if predicate == "negative" and number < 0:
            return {"operator": "NUMBER_PREDICATE", "verdict": PASS, "witness": number}
    return {"operator": "NUMBER_PREDICATE", "verdict": FAIL, "reason": f"NO_{predicate.upper()}_TYPED"}


def _check_order(clause, trace) -> dict[str, Any]:
    """The numbers on the elements pressed, read in press order, must be sorted."""
    numbers: list[float] = []
    for observation, index in _presses(trace):
        elements = observation.get("elements") or []
        if not 0 <= index < len(elements):
            continue
        label = element_label(elements[index])
        found = re.findall(r"-?\d+", label)
        if found:
            numbers.append(float(found[0]))
    if len(numbers) < 2:
        return {"operator": "ORDER", "verdict": UNCHECKABLE, "reason": "FEWER_THAN_TWO_NUMBERS_PRESSED"}
    ascending = numbers == sorted(numbers)
    good = ascending if clause["direction"] == "ascending" else numbers == sorted(numbers, reverse=True)
    return {"operator": "ORDER", "verdict": PASS if good else FAIL, "witness": numbers}
