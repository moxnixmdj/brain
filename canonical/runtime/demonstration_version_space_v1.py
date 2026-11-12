"""One success is a single point. A skill is whatever still fits every success seen so far.

Why this file exists
--------------------
A recorded success says WHAT was clicked and typed on one page under one instruction. It does
not say WHY that element and that text. "The third button", "the button labelled No", "the
button whose label is the quoted word in the instruction" and "the button with id b7" all
describe the same click, and they part company on the very next page. Replaying the record
picks the first reading silently. `causal_trace_to_skill_compiler_v1` picks another one
silently: a literal shared by the instruction and a step becomes a parameter, everything else
stays a constant. Either may be right; from one success neither can be known to be.

So this module does not pick. For every step it writes down EVERY description (from a small,
stated language) that selects the element that was acted on, and every expression that
produces the text that was typed. Each further success strikes out the ones that would have
done something else there. What is left, in a fixed order of preference, is the skill; when
the first surviving description does not apply to a page, the next one is used.

The language (all of it)
------------------------
  an element is described by one or two tests, optionally followed by a position among the
  elements passing them:
      a property of the element or of its parent / previous sibling / next sibling / label
      equals a constant (tag, type, id, classes, a single class, role, name, placeholder,
      for, title; or its text, full text, value);
      or equals a SLOT of the instruction (its text, full text or value; for the element
      itself also its tag or type: "click on a textarea");
      or, for the element's own text, STARTS or ENDS with a quoted piece of the instruction
      ("an item that starts with "Af" and ends with "tan"");
  a position is: the n-th from the start or the end; the n-th where n is a number in the
      instruction; or the one NEAREST, in the page tree, to an element the instruction names
      ("the trash icon in the row of the sender it mentions").
  a slot is a rule for cutting a piece out of the instruction: the k-th quoted span, the text
      between two given tokens (or the start / the end), the k-th number;
  typed text is a slot (optionally upper- or lower-cased), a copy of a field of a described
      element (which may itself be found through the instruction: "the cell next to the word
      it names"), or a constant.
  A program is a sequence of steps, and a step is one of three things:
      act on ONE described element;
      press EVERY element of one kind that the instruction mentions, in the order of the page
      (zero, one or twelve of them: the same step);
      and a step whose target a success found only AFTER the press before it is remembered
      with that purpose: when the target is not on a new page, elements of the same kind as
      the one pressed before are pressed, each at most once, until it is (or a fixed number
      of presses is used up).
  There are no conditions inside a program, no arithmetic, no counting and no comparison. A
  task that needs any of those is outside this language and fails here; that is a boundary,
  reported as one, not a defect to paper over.

  One task may need several programs (`SkillSet`): a success that no single program explains
  together with the earlier ones starts a program of its own, and on a new page the program
  whose instructions most resemble the new instruction acts. Without this, a second success
  that contradicts the first leaves nothing standing and practice makes the skill worse --
  which is what was measured before it was added.

Preference order (a prior, stated because with one example it decides everything)
--------------------------------------------------------------------------------
  1. descriptions tied to the instruction (a coincidence between instruction and page is
     the least likely thing to be an accident);
  2. descriptions made only of structure (tag, id, class, role ...);
  3. descriptions that quote page content as a constant;
  4. descriptions that rely on position.
  Inside a class: more tests first (the narrower claim is tried before the broader one),
  then fewer matches on the pages seen.

No model, no randomness, no network, no I/O.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_DEMONSTRATION_VERSION_SPACE_V1"

STRUCTURE_FIELDS = ("tag", "type", "id", "classes", "role", "name", "placeholder", "for", "title", "colour")
CONTENT_FIELDS = ("text", "full_text", "value")
RELATIONS = ("self", "parent", "prev", "next", "label")
MAX_CONTENT_LENGTH = 80
MAX_HYPOTHESES_PER_STEP = 6000
MAX_BOUND_COPY_SOURCES = 24      # how many instruction-tied descriptions of a copied element are kept
MAX_REVEAL_PRESSES = 12          # how many elements one step may press while looking for its target
SET_STEP = "click_all"           # the step kind "press every element of one kind the instruction mentions"
WAIT_STEP = "wait"               # the step kind "let time go by": it is done at no element
AT_AN_ELEMENT = ("click", "hover", "grab", "drop", "triple")     # steps that are one thing done at one element
WITH_A_WORD = ("type", "nudge", WAIT_STEP)                       # steps that carry a word: text, a direction, seconds
NUDGE_WORDS = ("up", "down", "left", "right")
NOWHERE: tuple[Any, ...] = ((), None)                            # stands where a step has no element to describe

_TOKEN = re.compile(r"\w+(?:[-'./:@]\w+)*|[^\w\s]")
_QUOTED = re.compile(r'"([^"]+)"|(?<![A-Za-z0-9])\'([^\']+)\'(?![A-Za-z0-9])')
_NUMBER = re.compile(r"(?<![\w.])-?\d+")


# --------------------------------------------------------------------------- #
# slots: rules for cutting a piece out of an instruction
# --------------------------------------------------------------------------- #
def tokenize(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(text or "")]


def quoted_spans(text: str) -> list[str]:
    return [m.group(1) if m.group(1) is not None else m.group(2) for m in _QUOTED.finditer(text or "")]


def numbers(text: str) -> list[str]:
    return _NUMBER.findall(text or "")


def extract(slot: Sequence[Any], instruction: str) -> str | None:
    """Apply a slot rule to an instruction. None when the rule finds nothing to cut."""
    kind = slot[0]
    if kind == "quoted":
        spans = quoted_spans(instruction)
        return spans[slot[1]] if slot[1] < len(spans) else None
    if kind == "number":
        found = numbers(instruction)
        return found[slot[1]] if slot[1] < len(found) else None
    if kind == "between":
        left, right = slot[1], slot[2]
        tokens = tokenize(instruction)
        start_char, start_token = 0, 0
        if left is not None:
            for position, (token, _, end) in enumerate(tokens):
                if token == left:
                    start_char, start_token = end, position + 1
                    break
            else:
                return None
        end_char = len(instruction or "")
        if right is not None:
            for token, begin, _ in tokens[start_token:]:
                if token == right and begin >= start_char:
                    end_char = begin
                    break
            else:
                return None
        piece = (instruction or "")[start_char:end_char].strip()
        return piece or None
    raise ValueError("SLOT_KIND_UNKNOWN")


def slots_returning(instruction: str, wanted: str, *, fold_case: bool = False) -> list[tuple[Any, ...]]:
    """Every slot rule that cuts exactly `wanted` out of `instruction`."""
    if not wanted or not instruction:
        return []
    same = (lambda a, b: a.lower() == b.lower()) if fold_case else (lambda a, b: a == b)
    out: list[tuple[Any, ...]] = []
    for k, span in enumerate(quoted_spans(instruction)):
        if same(span, wanted):
            out.append(("quoted", k))
    tokens = tokenize(instruction)
    haystack = instruction.lower() if fold_case else instruction
    needle = wanted.lower() if fold_case else wanted
    begin = haystack.find(needle)
    while begin >= 0:
        end = begin + len(needle)
        before = [t for t, _, e in tokens if e <= begin]
        after = [t for t, s, _ in tokens if s >= end]
        rule = ("between", before[-1] if before else None, after[0] if after else None)
        # a rule only ever cuts whole tokens, so applying it back is also the check that the
        # occurrence sits on token boundaries and that the neighbours identify it
        got = extract(rule, instruction)
        if got is not None and same(got, wanted) and rule not in out:
            out.append(rule)
        begin = haystack.find(needle, begin + 1)
    for k, number in enumerate(numbers(instruction)):
        if number == wanted:
            out.append(("number", k))
    return out


def mentioned_in(instruction: str, value: str) -> bool:
    """Does the instruction contain exactly this text, starting and ending on token boundaries?
    Asked without any slot rule: the fourth item of a list is mentioned as much as the first,
    though no "between this word and that" cuts it out."""
    if not value or not instruction:
        return False
    tokens = tokenize(instruction)
    starts = {begin for _, begin, _ in tokens}
    ends = {end for _, _, end in tokens}
    begin = instruction.find(value)
    while begin >= 0:
        if begin in starts and begin + len(value) in ends:
            return True
        begin = instruction.find(value, begin + 1)
    return False


# --------------------------------------------------------------------------- #
# a page, indexed once
# --------------------------------------------------------------------------- #
class Page:
    def __init__(self, observation: Mapping[str, Any]) -> None:
        self.instruction = str(observation.get("utterance") or "")
        self.elements: list[Mapping[str, Any]] = list(observation.get("elements") or [])
        siblings: dict[int, list[int]] = {}
        for index, element in enumerate(self.elements):
            siblings.setdefault(int(element.get("parent", -1)), []).append(index)
        self._prev: dict[int, int] = {}
        self._next: dict[int, int] = {}
        for group in siblings.values():
            for a, b in zip(group, group[1:]):
                self._next[a] = b
                self._prev[b] = a
        by_id = {str(e.get("id")): i for i, e in enumerate(self.elements) if e.get("id")}
        self._label: dict[int, int] = {}
        for index, element in enumerate(self.elements):
            target = by_id.get(str(element.get("for") or ""))
            if element.get("tag") == "label" and target is not None:
                self._label.setdefault(target, index)
        self._slot_cache: dict[tuple[Any, ...], str | None] = {}
        self._atom_cache: dict[tuple[Any, ...], frozenset[int]] = {}
        self._chain: list[tuple[int, ...]] = []
        for index, element in enumerate(self.elements):
            parent = int(element.get("parent", -1))
            above = self._chain[parent] if 0 <= parent < index else ()
            self._chain.append(above + (index,))
        self._anchor_specs: list[tuple[Any, ...]] | None = None

    def closeness(self, a: int, b: int) -> int:
        """How deep in the page tree two elements still share a container (larger = closer)."""
        shared = 0
        for x, y in zip(self._chain[a], self._chain[b]):
            if x != y:
                break
            shared += 1
        return shared

    def anchor_specs(self) -> list[tuple[Any, ...]]:
        """Every (field, slot rule, mode) under which some element on this page is NAMED by the
        instruction: its text is exactly a piece the rule cuts out of the instruction."""
        if self._anchor_specs is None:
            found: dict[tuple[Any, ...], None] = {}
            for index in range(len(self.elements)):
                for name in ("text", "full_text"):
                    value = self.field(index, name)
                    if not value or len(value) > MAX_CONTENT_LENGTH:
                        continue
                    if name == "full_text" and value == self.field(index, "text"):
                        continue
                    exact = slots_returning(self.instruction, value)
                    for rule in exact:
                        found.setdefault((name, rule, "exact"), None)
                    if not exact:
                        for rule in slots_returning(self.instruction, value, fold_case=True):
                            found.setdefault((name, rule, "fold"), None)
            self._anchor_specs = list(found)
        return self._anchor_specs

    def field(self, index: int, name: str) -> str:
        element = self.elements[index]
        if name == "full_text":
            return str(element.get("full_text") or element.get("text") or "")
        return str(element.get(name) or "")

    def neighbour(self, index: int, relation: str) -> int | None:
        if relation == "self":
            return index
        if relation == "parent":
            parent = int(self.elements[index].get("parent", -1))
            return parent if parent >= 0 else None
        if relation == "prev":
            return self._prev.get(index)
        if relation == "next":
            return self._next.get(index)
        if relation == "label":
            return self._label.get(index)
        raise ValueError("RELATION_UNKNOWN")

    def slot(self, rule: Sequence[Any]) -> str | None:
        key = tuple(rule)
        if key not in self._slot_cache:
            self._slot_cache[key] = extract(key, self.instruction)
        return self._slot_cache[key]

    def passing(self, test: Sequence[Any]) -> frozenset[int]:
        """Indices of the elements for which one test holds."""
        key = tuple(test)
        cached = self._atom_cache.get(key)
        if cached is not None:
            return cached
        kind, relation = key[0], key[1]
        wanted: str | None
        if kind == "slot":
            wanted = self.slot(key[3])
            if wanted is not None and key[4] == "fold":
                wanted = wanted.lower()
        elif kind == "mentioned":
            wanted = ""
        else:
            wanted = key[3] if kind == "equals" else key[2]
        mode = key[4] if kind == "slot" else None
        hits = set()
        if wanted is not None:
            for index in range(len(self.elements)):
                other = self.neighbour(index, relation)
                if other is None:
                    continue
                if kind == "has_class":
                    if wanted in self.field(other, "classes").split():
                        hits.add(index)
                elif kind == "mentioned":
                    value = self.field(other, key[2])
                    if len(value) <= MAX_CONTENT_LENGTH and mentioned_in(self.instruction, value):
                        hits.add(index)
                else:
                    value = self.field(other, key[2])
                    if mode == "fold":
                        value = value.lower()
                    if mode == "prefix":
                        if value.startswith(wanted):
                            hits.add(index)
                    elif mode == "suffix":
                        if value.endswith(wanted):
                            hits.add(index)
                    elif value == wanted:
                        hits.add(index)
        result = frozenset(hits)
        self._atom_cache[key] = result
        return result


# --------------------------------------------------------------------------- #
# descriptions of an element
# --------------------------------------------------------------------------- #
def tests_true_of(page: Page, index: int) -> list[tuple[Any, ...]]:
    """Every single test in the language that holds for this element on this page."""
    out: list[tuple[Any, ...]] = []
    for relation in RELATIONS:
        other = page.neighbour(index, relation)
        if other is None:
            continue
        for name in (STRUCTURE_FIELDS if relation == "self" else ("tag",)):
            value = page.field(other, name)
            if value:
                out.append(("equals", relation, name, value))
        if relation == "self":
            classes = page.field(other, "classes").split()
            if len(classes) > 1:
                out += [("has_class", relation, c) for c in classes]
            for name in ("tag", "type", "colour"):    # "click on a textarea", "the red box": the instruction names the KIND
                value = page.field(other, name)
                if value:
                    out += [("slot", relation, name, rule, "exact")
                            for rule in slots_returning(page.instruction, value)]
        for name in CONTENT_FIELDS:
            value = page.field(other, name)
            if not value or len(value) > MAX_CONTENT_LENGTH:
                continue
            if name == "full_text" and value == page.field(other, "text"):
                continue
            out.append(("equals", relation, name, value))
            exact = slots_returning(page.instruction, value)
            out += [("slot", relation, name, rule, "exact") for rule in exact]
            if not exact:
                out += [("slot", relation, name, rule, "fold")
                        for rule in slots_returning(page.instruction, value, fold_case=True)]
            if relation == "self" and name == "text":
                # "starts with "Af"", "the "Block" button" on a button that reads "Block @ann": only
                # pieces the instruction itself puts in quotes, and only when they are not the whole text
                for k, span in enumerate(quoted_spans(page.instruction)):
                    if len(span) >= 2 and span != value:
                        if value.startswith(span):
                            out.append(("slot", relation, name, ("quoted", k), "prefix"))
                        if value.endswith(span):
                            out.append(("slot", relation, name, ("quoted", k), "suffix"))
    return list(dict.fromkeys(out))


def _is_bound(test: Sequence[Any]) -> bool:
    return test[0] == "slot"


def _is_content_constant(test: Sequence[Any]) -> bool:
    return test[0] == "equals" and test[2] in CONTENT_FIELDS


def matches(description: Sequence[Any], page: Page) -> list[int]:
    """The elements a description selects on a page, in document order."""
    tests, position = description
    chosen: frozenset[int] | None = None
    for test in tests:
        passing = page.passing(test)
        chosen = passing if chosen is None else (chosen & passing)
        if not chosen:
            return []
    ordered = sorted(chosen or ())
    if position is None:
        return ordered
    kind = position[0]
    if kind == "nth":
        return [ordered[position[1]]] if position[1] < len(ordered) else []
    if kind == "nth_from_end":
        return [ordered[-1 - position[1]]] if position[1] < len(ordered) else []
    if kind == "nth_slot":
        value = page.slot(position[1])
        if value is None or not value.lstrip("-").isdigit():
            return []
        n = int(value) - 1
        return [ordered[n]] if 0 <= n < len(ordered) else []
    if kind == "nearest":
        # among the elements passing the tests, the one that shares the deepest container with
        # an element the instruction names: "the trash icon in the row of the sender it mentions"
        anchors = page.passing(("slot", "self", position[1], position[2], position[3]))
        if not anchors:
            return []
        best, best_score = None, -1
        for candidate in ordered:
            score = max(page.closeness(candidate, anchor) for anchor in anchors)
            if score > best_score:
                best, best_score = candidate, score
        return [] if best is None else [best]
    raise ValueError("POSITION_KIND_UNKNOWN")


def pick(description: Sequence[Any], page: Page) -> int | None:
    found = matches(description, page)
    return found[0] if found else None


def descriptions_of(page: Page, index: int) -> list[tuple[Any, ...]]:
    """Every description in the language whose FIRST match on this page is this element."""
    tests = tests_true_of(page, index)
    groups: list[tuple[tuple[Any, ...], ...]] = [(t,) for t in tests]
    for a in range(len(tests)):
        for b in range(a + 1, len(tests)):
            groups.append((tests[a], tests[b]))
    out: list[tuple[Any, ...]] = []
    for group in groups:
        selected = matches((group, None), page)
        if index not in selected:
            continue
        if selected[0] == index:
            out.append((group, None))
        if len(selected) > 1:
            place = selected.index(index)
            out.append((group, ("nth", place)))
            out.append((group, ("nth_from_end", len(selected) - 1 - place)))
            for k, number in enumerate(numbers(page.instruction)):
                if number == str(place + 1):
                    out.append((group, ("nth_slot", ("number", k))))
            for name, rule, mode in page.anchor_specs():
                near = (group, ("nearest", name, rule, mode))
                if matches(near, page) == [index]:
                    out.append(near)
        if len(out) >= MAX_HYPOTHESES_PER_STEP:
            break
    return out


def preference(description: Sequence[Any], pages: Sequence[Page]) -> tuple[Any, ...]:
    tests, position = description
    kind = position[0] if position is not None else None
    bound = any(_is_bound(t) for t in tests) or kind in ("nth_slot", "nearest")
    by_place = kind in ("nth", "nth_from_end")
    quotes_content = any(_is_content_constant(t) for t in tests)
    bound_tests = [t for t in tests if _is_bound(t)]
    # "is the piece" says more than "begins with the piece": a part can match by accident where the whole cannot
    loose = 1 if any(t[4] in ("prefix", "suffix") for t in bound_tests) else 0
    if by_place:
        rank = 3
    elif bound and not (loose and quotes_content):
        rank = 0
    elif quotes_content:
        # also: "reads exactly Alxeo and begins with the quoted piece" -- the constant does the choosing, and
        # on a page that happens to hold the same text the loose half lets it through
        rank = 2
    else:
        rank = 1
    # A tie between the instruction and the element itself explains more than a tie with what
    # stands right next to it, and that more than "whatever is nearest to the thing it names".
    if any(t[1] == "self" for t in bound_tests) or kind == "nth_slot":
        reach = 0
    elif bound_tests:
        reach = 1
    elif kind == "nearest":
        reach = 2
    else:
        reach = 0
    slot_kinds = [t[3][0] for t in bound_tests] + ([position[2][0]] if kind == "nearest" else [])
    slot_rank = 0 if "quoted" in slot_kinds else (1 if slot_kinds else 2)
    on_self = sum(1 for t in tests if t[1] == "self")
    crowd = sum(max(0, len(matches((tests, None), p)) - 1) for p in pages)
    return (rank, reach, loose, slot_rank, -len(tests), -on_self, crowd, repr(description))


# --------------------------------------------------------------------------- #
# expressions for typed text
# --------------------------------------------------------------------------- #
_TRANSFORMS = {"same": lambda s: s, "upper": str.upper, "lower": str.lower}


def expressions_for(page: Page, typed: str) -> list[tuple[Any, ...]]:
    out: list[tuple[Any, ...]] = []
    for rule in slots_returning(page.instruction, typed):
        out.append(("slot", rule, "same"))
    for transform in ("upper", "lower"):
        for token, begin, end in tokenize(page.instruction):
            if token != typed and _TRANSFORMS[transform](token) == typed:
                for rule in slots_returning(page.instruction, token):
                    out.append(("slot", rule, transform))
    for index in range(len(page.elements)):
        for name in ("value", "text", "full_text"):
            if page.field(index, name) == typed:
                for test in tests_true_of(page, index):
                    if test[1] == "self" and test[0] in ("equals", "has_class") and not _is_content_constant(test):
                        if pick(((test,), None), page) == index:
                            out.append(("copy", ((test,), None), name))
                # "the value of Language": the element copied from is the one the instruction leads to
                tied = [d for d in descriptions_of(page, index)
                        if d[1] is None and any(_is_bound(t) for t in d[0])
                        and not any(_is_content_constant(t) for t in d[0])]
                tied.sort(key=lambda d: preference(d, [page]))
                for description in tied[:MAX_BOUND_COPY_SOURCES]:
                    out.append(("copy", description, name))
    out.append(("constant", typed))
    return list(dict.fromkeys(out))


def evaluate(expression: Sequence[Any], page: Page) -> str | None:
    kind = expression[0]
    if kind == "constant":
        return expression[1]
    if kind == "slot":
        value = page.slot(expression[1])
        return None if value is None else _TRANSFORMS[expression[2]](value)
    if kind == "copy":
        source = pick(expression[1], page)
        if source is None:
            return None
        return page.field(source, expression[2]) or None
    raise ValueError("EXPRESSION_KIND_UNKNOWN")


def expression_preference(expression: Sequence[Any]) -> tuple[Any, ...]:
    kind = expression[0]
    if kind == "slot":
        return (0 if expression[2] == "same" else 1, 0 if expression[1][0] == "quoted" else 1, repr(expression))
    if kind == "copy":
        tied = any(_is_bound(t) for t in expression[1][0])
        return (2, 0 if tied else 1, repr(expression))
    return (3, 0, repr(expression))


def _parse(action: str) -> tuple[str, int, str]:
    """(kind, element, word). `wait=3` is done at no element (-1); `click@4` carries no word."""
    whole = str(action)
    if whole.startswith(WAIT_STEP + "="):
        return WAIT_STEP, -1, whole[len(WAIT_STEP) + 1:]
    kind, _, rest = whole.partition("@")
    if kind in AT_AN_ELEMENT:
        return kind, int(rest), ""
    if kind not in WITH_A_WORD:
        raise ValueError("ACTION_KIND_UNKNOWN")
    index, _, text = rest.partition("=")
    return kind, int(index), text


def _word_fits(kind: str, word: str) -> bool:
    """Can this word be carried by a step of this kind? Any text can be typed; a nudge goes one
    of four ways; a wait lasts a whole number of seconds."""
    if kind == "nudge":
        return word in NUDGE_WORDS
    if kind == WAIT_STEP:
        return word.isdigit() and int(word) > 0
    return True


# --------------------------------------------------------------------------- #
# steps that are more than "act on one element"
# --------------------------------------------------------------------------- #
def _same_element(first: Page, later: Page, index: int) -> bool:
    """Is element `index` of a later page the element that had this number on the first one?"""
    return (len(first.elements) == len(later.elements) and 0 <= index < len(first.elements)
            and all(first.field(index, name) == later.field(index, name) for name in ("tag", "id", "text", "full_text")))


def set_descriptions(page: Page, indices: Sequence[int]) -> list[tuple[Any, ...]]:
    """Every description "all the elements of this kind that the instruction mentions" that
    selects EXACTLY these elements on this page -- none of them left out and no other let in."""
    wanted = sorted(set(int(i) for i in indices))
    if not wanted:
        return []
    shared = []
    for name in ("tag", "type", "classes"):
        values = {page.field(index, name) for index in wanted}
        if len(values) == 1 and next(iter(values)):
            shared.append(("equals", "self", name, next(iter(values))))
    if not shared or shared[0][2] != "tag":
        return []
    out: list[tuple[Any, ...]] = []
    for relation in RELATIONS:
        for name in CONTENT_FIELDS:
            mention = ("mentioned", relation, name)
            if not set(wanted) <= page.passing(mention):
                continue
            for tests in ((shared[0], mention), tuple(shared) + (mention,)):
                description = (tests, None)
                if description not in out and matches(description, page) == wanted:
                    out.append(description)
    return out


def _roll(parsed: Sequence[tuple[Page, str, int, str]]) -> list[tuple[str, Page, Any, str]]:
    """Rewrite a recorded success: a run of two or more presses that went, in the order of the
    page, through exactly the elements of one kind the instruction mentions becomes ONE step,
    "press every one of them". A single press stays a single press: one example of one element
    does not say "all"."""
    out: list[tuple[str, Page, Any, str]] = []
    position = 0
    while position < len(parsed):
        page, kind, index, text = parsed[position]
        if kind == "click":
            last = position
            while (last + 1 < len(parsed) and parsed[last + 1][1] == "click"
                   and parsed[last + 1][2] > parsed[last][2]
                   and _same_element(page, parsed[last + 1][0], parsed[last + 1][2])):
                last += 1
            rolled = False
            for end in range(last, position, -1):
                indices = [parsed[k][2] for k in range(position, end + 1)]
                if set_descriptions(page, indices):
                    out.append((SET_STEP, page, tuple(indices), ""))
                    position, rolled = end + 1, True
                    break
            if rolled:
                continue
        out.append((kind, page, index, text))
        position += 1
    return out


def page_order(trace: Sequence[tuple[Mapping[str, Any], str]]) -> list[str] | None:
    """The same actions with every run that pressed exactly the mentioned elements of one kind
    put in the order of the page, or None when that changes nothing. This is a QUESTION for the
    page ("would it also have paid in this order?"), not a fact: whoever calls this has to do
    the reordered actions on a fresh page and keep them only if the page pays again."""
    parsed = [(Page(observation), *_parse(action)) for observation, action in trace]
    actions = [str(action) for _, action in trace]
    changed = False
    position = 0
    while position < len(parsed):
        page, kind, _, _ = parsed[position]
        step = 1
        if kind == "click":
            last = position
            while (last + 1 < len(parsed) and parsed[last + 1][1] == "click"
                   and _same_element(page, parsed[last + 1][0], parsed[last + 1][2])):
                last += 1
            for end in range(last, position, -1):
                indices = [parsed[k][2] for k in range(position, end + 1)]
                if len(set(indices)) == len(indices) and set_descriptions(page, indices):
                    if sorted(indices) != indices:
                        actions[position:end + 1] = [f"click@{index}" for index in sorted(indices)]
                        changed = True
                    step = end + 1 - position
                    break
        position += step
    return actions if changed else None


def family_of(page: Page, index: int) -> tuple[Any, ...] | None:
    """The elements of the same kind as this one: same tag, same classes. None when it has no
    class to be told by. (It may be the only one of its kind on this page and one of five on
    the next.)"""
    tag, classes = page.field(index, "tag"), page.field(index, "classes")
    if not tag or not classes:
        return None
    return ((("equals", "self", "tag", tag), ("equals", "self", "classes", classes)), None)


def signature(page: Page, index: int) -> tuple[Any, ...]:
    """What an element is known by after the page has changed around it: what it is and says,
    and which one of several such it is."""
    def what(i: int) -> tuple[str, ...]:
        return tuple(page.field(i, name) for name in ("tag", "id", "text", "full_text"))
    mine = what(index)
    return mine + (sum(1 for other in range(index) if what(other) == mine),)


# --------------------------------------------------------------------------- #
# the skill: what still fits every success
# --------------------------------------------------------------------------- #
class VersionSpaceSkill:
    """Per step: the descriptions (and typed-text expressions) consistent with every success."""

    def __init__(self) -> None:
        self.kinds: list[str] = []
        self._examples: list[list[tuple[Page, Any, str]]] = []
        self._targets: list[list[tuple[Any, ...]]] = []
        self._ranks: list[list[int]] = []
        self._texts: list[list[tuple[Any, ...]]] = []
        self._reveal: list[tuple[Any, ...] | None] = []
        self._slot_rules: list[tuple[Any, ...]] | None = None
        self._own_fixed: list[frozenset[str]] | None = None
        self.rejected_examples = 0

    @property
    def examples(self) -> int:
        return len(self._examples)

    def _align(self, parsed: Sequence[tuple[Page, str, int, str]]) -> list[tuple[Page, Any, str]] | None:
        """Read a recorded success as a run of THIS program: every "press all of them" step takes
        as many presses as its description selects on that page (none, when it selects none) and
        they must be exactly those, in the order of the page. None when it is not such a run."""
        out: list[tuple[Page, Any, str]] = []
        position = 0
        for step, kind in enumerate(self.kinds):
            if kind == SET_STEP:
                if position >= len(parsed):
                    return None
                page = parsed[position][0]
                taken: tuple[int, ...] | None = None
                for description in self._targets[step]:
                    expected = matches(description, page)
                    run = []
                    while (len(run) < len(expected) and position + len(run) < len(parsed)
                           and parsed[position + len(run)][1] == "click"
                           and parsed[position + len(run)][2] == expected[len(run)]
                           and _same_element(page, parsed[position + len(run)][0], expected[len(run)])):
                        run.append(expected[len(run)])
                    if run == expected:
                        taken = tuple(run)
                        break
                if taken is None:
                    return None
                out.append((page, taken, ""))
                position += len(taken)
            else:
                if position >= len(parsed) or parsed[position][1] != kind:
                    return None
                out.append((parsed[position][0], parsed[position][2], parsed[position][3]))
                position += 1
        return out if position == len(parsed) else None

    def add_success(self, trace: Sequence[tuple[Mapping[str, Any], str]]) -> bool:
        """Take one more verified success. False -- and nothing changes -- when no single
        program in the language accounts for it together with the successes already held:
        it has another shape (other kinds of step in another order), or some step would be
        left with no description, or no expression for its typed text, that fits them all."""
        parsed = [(Page(observation), *_parse(action)) for observation, action in trace]
        if not parsed:
            return False
        if self._examples:
            aligned = self._align(parsed)
            if aligned is None:
                self.rejected_examples += 1
                return False
            kinds = list(self.kinds)
        else:
            rolled = _roll(parsed)
            kinds = [kind for kind, _, _, _ in rolled]
            aligned = [(page, payload, text) for _, page, payload, text in rolled]
        examples = self._examples + [aligned]
        targets, ranks, texts, reveal = self._fit(kinds, examples)
        unexplained = any(not t for t in targets) or any(
            kind in WITH_A_WORD and not x for kind, x in zip(kinds, texts))
        if unexplained and self._examples:
            self.rejected_examples += 1
            return False
        self.kinds = kinds
        self._examples = examples
        self._targets, self._ranks, self._texts, self._reveal = targets, ranks, texts, reveal
        self._slot_rules = None
        self._own_fixed = None
        return True

    def instructions(self) -> list[str]:
        return [example[0][0].instruction for example in self._examples]

    def slot_rules(self) -> list[tuple[Any, ...]]:
        """Every slot rule some surviving description or text expression reads the instruction through."""
        if self._slot_rules is None:
            rules: dict[tuple[Any, ...], None] = {}

            def read(description: Sequence[Any]) -> None:
                tests, position = description
                for test in tests:
                    if _is_bound(test):
                        rules.setdefault(tuple(test[3]), None)
                if position is not None and position[0] == "nth_slot":
                    rules.setdefault(tuple(position[1]), None)
                if position is not None and position[0] == "nearest":
                    rules.setdefault(tuple(position[2]), None)

            for descriptions in self._targets:
                for description in descriptions:
                    read(description)
            for expressions in self._texts:
                for expression in expressions:
                    if expression[0] == "slot":
                        rules.setdefault(tuple(expression[1]), None)
                    if expression[0] == "copy":
                        read(expression[1])
            self._slot_rules = list(rules)
        return self._slot_rules

    def mentions_read(self, page: Page) -> frozenset[str]:
        """The tokens of this page's instruction that a "press all of them" step of this program
        reads as the names of the elements it presses."""
        found: set[str] = set()
        for step, kind in enumerate(self.kinds):
            if kind != SET_STEP or not self._targets[step]:
                continue
            description = self._targets[step][0]
            mention = next(test for test in description[0] if test[0] == "mentioned")
            for index in matches(description, page):
                other = page.neighbour(index, mention[1])
                if other is not None:
                    found |= _token_set(page.field(other, mention[2]))
        return frozenset(found)

    def fixed(self, instruction: str, page: Page | None = None) -> frozenset[str]:
        """The tokens of an instruction this program does NOT read as values."""
        rest = fixed_tokens(instruction, self.slot_rules())
        return rest - self.mentions_read(page) if page is not None else rest

    def own_fixed(self) -> list[frozenset[str]]:
        if self._own_fixed is None:
            out = []
            for example in self._examples:
                rest = set(fixed_tokens(example[0][0].instruction, self.slot_rules()))
                for step, kind in enumerate(self.kinds):
                    if kind == SET_STEP:
                        rest -= self.mentions_read(example[step][0])
                out.append(frozenset(rest))
            self._own_fixed = out
        return self._own_fixed

    @staticmethod
    def _fit(kinds: Sequence[str], examples: Sequence[Sequence[tuple[Page, Any, str]]]
             ) -> tuple[list[list[tuple[Any, ...]]], list[list[int]], list[list[tuple[Any, ...]]],
                        list[tuple[Any, ...] | None]]:
        targets, ranks, texts = [], [], []
        for step, kind in enumerate(kinds):
            seen = [example[step] for example in examples]
            pages = [page for page, _, _ in seen]
            if kind == SET_STEP:
                pool: dict[tuple[Any, ...], None] = {}
                for page, indices, _ in seen:
                    for description in set_descriptions(page, indices):
                        pool.setdefault(description, None)
                kept = [d for d in pool if all(matches(d, page) == list(indices) for page, indices, _ in seen)]
                targets.append(kept)
                ranks.append([0] * len(kept))
                texts.append([])
                continue
            if kind == WAIT_STEP:
                targets.append([NOWHERE])
                ranks.append([0])
            else:
                candidates: dict[tuple[Any, ...], None] = {}
                for page, index, _ in seen:
                    for description in descriptions_of(page, index):
                        candidates.setdefault(description, None)
                kept = [d for d in candidates if all(pick(d, page) == index for page, index, _ in seen)]
                kept.sort(key=lambda d: preference(d, pages))
                targets.append(kept)
                ranks.append([preference(d, pages)[0] for d in kept])
            if kind in WITH_A_WORD:
                pool = {}
                for page, _, typed in seen:
                    for expression in expressions_for(page, typed):
                        pool.setdefault(expression, None)
                fitting = [x for x in pool if all(evaluate(x, page) == typed for page, _, typed in seen)]
                fitting.sort(key=expression_preference)
                texts.append(fitting)
            else:
                texts.append([])
        # A purpose, read off the record: in some success the element this step looks for was not
        # to be found before the press that came just before it, and was there after. That press
        # brought it out, and any element of the same kind may have to be pressed for that on
        # another page. (A success in which it was there all along, and the press was made anyway,
        # does not take the purpose away: it shows a press that was not needed, nothing more.)
        reveal: list[tuple[Any, ...] | None] = [None] * len(kinds)
        for step in range(1, len(kinds)):
            if kinds[step] in (SET_STEP, WAIT_STEP) or kinds[step - 1] != "click" or not targets[step]:
                continue
            first = targets[step][0]
            brought_out = [example for example in examples if pick(first, example[step - 1][0]) is None]
            families = {family_of(example[step - 1][0], example[step - 1][1]) for example in brought_out}
            if len(families) == 1 and None not in families:
                reveal[step] = next(iter(families))
        return targets, ranks, texts, reveal

    def _target(self, step: int, page: Page, *, strong_only: bool = False) -> int | None:
        """The element this step acts on here. `strong_only`: found by a description of the
        best kind that survived (tied to the instruction, when one such survived), not by a
        weaker one tried for want of anything better."""
        ranks = self._ranks[step]
        for description, rank in zip(self._targets[step], ranks):
            if strong_only and rank != ranks[0]:
                break
            target = pick(description, page)
            if target is not None:
                return target
        return None

    def _action(self, step: int, page: Page, *, strong_only: bool = False) -> str | None:
        kind = self.kinds[step]
        if kind == SET_STEP:
            for description in self._targets[step][:1]:
                for target in matches(description, page):
                    if page.elements[target].get("can_click"):
                        return f"click@{target}"
            return None
        if kind == WAIT_STEP:
            for expression in self._texts[step]:
                text = evaluate(expression, page)
                if text is not None and _word_fits(kind, text):
                    return f"{WAIT_STEP}={text}"
            return None
        target = self._target(step, page, strong_only=strong_only)
        if target is None:
            return None
        element = page.elements[target]
        if not element.get("can_type" if kind == "type" else "can_click"):
            return None
        if kind in AT_AN_ELEMENT:
            return f"{kind}@{target}"
        for expression in self._texts[step]:
            text = evaluate(expression, page)
            if text is not None and _word_fits(kind, text):
                return f"{kind}@{target}={text}"
        return None

    def act(self, step: int, observation: Mapping[str, Any]) -> str | None:
        """The action for this step on this page, taken by itself: the first surviving
        description that selects something here. None when the program is over or nothing that
        survived applies. (A whole episode is run by `Execution`, which also remembers.)"""
        if step >= len(self.kinds):
            return None
        return self._action(step, Page(observation))

    def begins(self, page: Page) -> int:
        """Can this program start on this page? 2: its first step finds its element by a
        description of the best kind that survived; 1: only by a weaker one; 0: not at all. A
        "press all of them" step that finds nothing to press is passed over, as it is in a run."""
        for step, kind in enumerate(self.kinds):
            if kind == SET_STEP:
                if self._action(step, page) is not None:
                    return 2
                continue
            if self._action(step, page, strong_only=True) is not None:
                return 2
            return 1 if self._action(step, page) is not None else 0
        return 0

    def describe(self) -> dict[str, Any]:
        steps = []
        for step, kind in enumerate(self.kinds):
            entry: dict[str, Any] = {"kind": kind, "descriptions_left": len(self._targets[step]),
                                     "first": repr(self._targets[step][0]) if self._targets[step] else None}
            if kind in WITH_A_WORD:
                entry["text_expressions_left"] = len(self._texts[step])
                entry["first_text"] = repr(self._texts[step][0]) if self._texts[step] else None
            if self._reveal[step] is not None:
                entry["target_is_brought_out_by_pressing"] = repr(self._reveal[step])
            steps.append(entry)
        return {"schema": SCHEMA, "examples": self.examples, "rejected_examples": self.rejected_examples,
                "steps": steps}


class Execution:
    """One run of one program in one episode. It remembers what a step number cannot: which of
    the mentioned elements were already pressed, and what was already pressed in looking for a
    target that is not on the page."""

    def __init__(self, skill: VersionSpaceSkill) -> None:
        self.skill = skill
        self.step = 0
        self.actions = 0
        self.searched = 0                    # presses made only to bring a target out
        self._pressed: set[tuple[Any, ...]] = set()
        self._pressed_in_set: set[tuple[Any, ...]] = set()
        self._looked_for = 0

    def _next_of_set(self, step: int, page: Page) -> int | None:
        for description in self.skill._targets[step][:1]:
            for target in matches(description, page):
                mark = signature(page, target)
                if mark in self._pressed_in_set or not page.elements[target].get("can_click"):
                    continue
                self._pressed_in_set.add(mark)
                return target
        return None

    def _bring_out(self, step: int, page: Page) -> int | None:
        family = self.skill._reveal[step]
        if family is None or self._looked_for >= MAX_REVEAL_PRESSES:
            return None
        for candidate in matches(family, page):
            mark = signature(page, candidate)
            if mark in self._pressed or not page.elements[candidate].get("can_click"):
                continue
            self._looked_for += 1
            return candidate
        return None

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        skill, page = self.skill, Page(observation)
        while self.step < len(skill.kinds):
            step = self.step
            if skill.kinds[step] == SET_STEP:
                target = self._next_of_set(step, page)
                if target is None:
                    self._pressed_in_set = set()
                    self.step += 1
                    continue
                self.actions += 1
                return f"click@{target}"
            action = skill._action(step, page, strong_only=True)
            if action is None:
                candidate = self._bring_out(step, page)
                if candidate is not None:
                    self._pressed.add(signature(page, candidate))
                    self.actions += 1
                    self.searched += 1
                    return f"click@{candidate}"
                action = skill._action(step, page)
            self.step += 1
            self._looked_for = 0
            if action is None:
                return None
            if action.startswith("click@"):
                self._pressed.add(signature(page, int(action[6:])))
            self.actions += 1
            return action
        return None


def _token_set(text: str) -> frozenset[str]:
    return frozenset(token for token, _, _ in tokenize(text))


def fixed_tokens(instruction: str, slot_rules: Sequence[Sequence[Any]]) -> frozenset[str]:
    """The tokens of an instruction that the given slot rules do NOT account for."""
    variable: set[str] = set()
    for rule in slot_rules:
        value = extract(rule, instruction)
        if value:
            variable |= _token_set(value)
    return _token_set(instruction) - variable


def mismatch(skill: "VersionSpaceSkill", instruction: str, page: Page | None = None) -> int:
    """How far a new instruction is from the ones this program was learned from, counting
    only what the program does not read as a value. A different quoted word costs nothing
    (the program reads it through a slot), nor do other names in a list the program goes
    through (given the page, it reads them as the elements it presses); a different fixed
    word does."""
    new = skill.fixed(instruction, page)
    return min((len(new ^ known) for known in skill.own_fixed()), default=len(new))


def evidence(skill: "VersionSpaceSkill", instruction: str, page: Page | None = None) -> tuple[int, int]:
    """(for, against) that an instruction is of the kind this program was learned from.

    For: the fixed WORDS it shares with one of the program's own instructions -- words the
    program does not read as values. Against: fixed tokens only one of the two has. Among
    the program's own instructions the most favourable one is taken.

    `mismatch` alone (the "against" half) is enough inside one task, where every program was
    learned from the same kind of sentence. Across tasks it is not: a program whose slot
    swallows its whole instruction ("Go." read as "<the button's name>.") leaves no fixed word,
    so nothing can ever differ and it would sit at distance zero from every page there is.
    What it lacks is evidence FOR, and that is what is counted here.
    """
    new = skill.fixed(instruction, page)
    best: tuple[int, int] | None = None
    for old in skill.own_fixed():
        shared = sum(1 for token in new & old if token[:1].isalnum())
        against = len(new ^ old)
        if best is None or (shared - against, -against) > (best[0] - best[1], -best[1]):
            best = (shared, against)
    return best if best is not None else (0, len(new))


class SkillSet:
    """Several programs for one task, because one task can present itself in several ways.

    A success that fits no single program together with the ones already held is not
    evidence that nothing was learned; it is evidence of a second way ("type it in UPPER
    case" / "type it in lower case"). It starts a program of its own. On a new page the
    program whose own instructions differ least from the new one -- in the words it does not
    read as values -- is the one that acts; among equals, one whose first step finds its
    element on this page goes before one whose first step does not, and then the one with
    more successes behind it. The language still has no conditions INSIDE a program; this is
    a choice BETWEEN programs, made once, from the instruction and the first page.
    """

    def __init__(self) -> None:
        self.skills: list[VersionSpaceSkill] = []

    @property
    def examples(self) -> int:
        return sum(skill.examples for skill in self.skills)

    def _ordered(self, instruction: str, page: Page | None = None) -> list[VersionSpaceSkill]:
        scored = [(mismatch(skill, instruction, page), 0 if page is None else -skill.begins(page),
                   -skill.examples, position, skill)
                  for position, skill in enumerate(self.skills)]
        scored.sort(key=lambda item: item[:4])
        return [skill for _, _, _, _, skill in scored]

    def add_success(self, trace: Sequence[tuple[Mapping[str, Any], str]]) -> str:
        """'refined' when an existing program took it, 'new_way' when it started its own."""
        if not trace:
            return "empty"
        instruction = str(trace[0][0].get("utterance") or "")
        for skill in self._ordered(instruction, Page(trace[0][0])):
            if skill.add_success(trace):
                return "refined"
        fresh = VersionSpaceSkill()
        fresh.add_success(trace)
        self.skills.append(fresh)
        return "new_way"

    def choose(self, instruction: str, observation: Mapping[str, Any] | None = None) -> VersionSpaceSkill | None:
        page = None if observation is None else Page(observation)
        ordered = self._ordered(instruction, page)
        return ordered[0] if ordered else None

    def start(self, observation: Mapping[str, Any]) -> Execution | None:
        """A run of the program that fits this page best, or None when nothing is held."""
        skill = self.choose(str(observation.get("utterance") or ""), observation)
        return None if skill is None else Execution(skill)

    def describe(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "programs": len(self.skills), "examples": self.examples,
                "per_program": [skill.describe() for skill in self.skills]}


# --------------------------------------------------------------------------- #
# practice: more successes, each one checked by the environment
# --------------------------------------------------------------------------- #
class VersionSpaceArm:
    name = "version_space"

    def __init__(self, skills: SkillSet, learning: Mapping[str, Any]) -> None:
        self.skills = skills
        self.learning = dict(learning)
        self._run: Execution | None = None
        self._asked = 0
        self.refused = False
        self.searched = 0                    # presses made, over all episodes, only to bring a target out

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        self._run = self.skills.start(observation)
        self._asked = 0
        self.refused = False

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        before = 0 if self._run is None else self._run.searched
        action = None if self._run is None else self._run.next_action(observation)
        if self._run is not None:
            self.searched += self._run.searched - before
        if action is None and self._asked == 0:
            self.refused = True
        self._asked += 1
        return action


# --------------------------------------------------------------------------- #
# one memory for everything learned
# --------------------------------------------------------------------------- #
class SkillLibrary:
    """Every program learned anywhere, in one memory, and nothing that says which task a page is.

    A skill kept per task and handed back with the task's name answers a question nobody asks
    twice: "what did I learn HERE?". A memory has to answer the other one: "I have never been
    told what this page is -- what do I know that fits it?". The answer here uses nothing but
    the page: programs are tried in the order of the evidence that the page's instruction is
    of their kind (`evidence`: shared fixed words minus differing ones), and the first whose
    opening step can be taken on this page acts.

    `without` leaves out everything learned in the named places. That is how first sight is
    measured: a page is met with the memory of every OTHER place and nothing of its own.
    """

    def __init__(self) -> None:
        self.entries: list[tuple[str, int, VersionSpaceSkill]] = []      # (where learned, its place there, the program)

    def add(self, origin: str, skills: SkillSet) -> None:
        if any(held == str(origin) for held, _, _ in self.entries):
            raise ValueError("ORIGIN_ALREADY_HELD")
        for place, skill in enumerate(skills.skills):
            self.entries.append((str(origin), place, skill))

    def origins(self) -> list[str]:
        return sorted({origin for origin, _, _ in self.entries})

    def ranked(self, instruction: str, *, without: Sequence[str] = (),
               observation: Mapping[str, Any] | None = None) -> list[tuple[int, str, VersionSpaceSkill]]:
        """(evidence for minus against, where learned, program), best supported first; ties go
        to less against, then to more successes behind the program, then to a fixed order so
        that the same memory always answers alike."""
        left_out = set(without)
        page = None if observation is None else Page(observation)
        rows = []
        for origin, place, skill in self.entries:
            if origin in left_out:
                continue
            supports, against = evidence(skill, instruction, page)
            rows.append((against - supports, against, -skill.examples, origin, place, skill))
        rows.sort(key=lambda row: row[:5])
        return [(-row[0], row[3], row[5]) for row in rows]

    def choose(self, observation: Mapping[str, Any], *, without: Sequence[str] = (),
               look: int = 12) -> tuple[str | None, VersionSpaceSkill | None]:
        """Where the acting program was learned, and the program. (None, None): nothing among
        the `look` nearest can even begin on this page, and the honest move is to do nothing."""
        instruction = str(observation.get("utterance") or "")
        page = Page(observation)
        ranked = self.ranked(instruction, without=without, observation=observation)[:max(1, int(look))]
        for _, origin, skill in ranked:
            if skill.begins(page) > 0:
                return origin, skill
        return None, None


class LibraryArm:
    """One agent with one memory. It is given a page, never the name of the task."""
    name = "library"

    def __init__(self, library: SkillLibrary, *, without: Sequence[str] = ()) -> None:
        self.library = library
        self.without = tuple(without)
        self.chosen_from: dict[str, int] = {}          # where the acting program had been learned -> episodes
        self._run: Execution | None = None
        self._asked = 0
        self.refused = False
        self.searched = 0                              # presses made, over all episodes, only to bring a target out

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        origin, skill = self.library.choose(observation, without=self.without)
        key = origin if origin is not None else "NOTHING_HELD_BEGINS_HERE"
        self.chosen_from[key] = self.chosen_from.get(key, 0) + 1
        self._run = None if skill is None else Execution(skill)
        self._asked = 0
        self.refused = False

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        before = 0 if self._run is None else self._run.searched
        action = None if self._run is None else self._run.next_action(observation)
        if self._run is not None:
            self.searched += self._run.searched - before
        if action is None and self._asked == 0:
            self.refused = True
        self._asked += 1
        return action


def build_arm(*, bridge: Any, task: str, trace: Sequence[tuple[Mapping[str, Any], str]],
              practice_seeds: Sequence[int], action_budget: int, tier: int, tool: Any,
              search: str = "blind") -> VersionSpaceArm:
    """Start from one success. On each practice instance try what is held; if the page says
    no, find a success there by exploration and take that. Either way the only thing ever
    added is a trace the page itself rewarded.

    One question is put to the page a success came from: where the success pressed exactly
    the elements of one kind that the instruction mentions, but not in the order of the page,
    the same presses are made in the order of the page on a fresh copy of that page. If it
    pays again, that is the success kept (the order did not matter, and "press every one of
    them" can be read off it); if it does not, the order did matter and nothing is changed.
    """
    log = {"own_success": 0, "found_by_search": 0, "new_ways": 0, "no_success": 0,
           "search_actions": 0, "practice_instances": len(list(practice_seeds)),
           "order_questions": 0, "order_questions_answered_yes": 0, "order_question_actions": 0,
           "own_success_with_looking": 0}

    def settled(found: Sequence[tuple[Mapping[str, Any], str]], seed: int) -> Sequence[tuple[Mapping[str, Any], str]]:
        reordered = page_order(found)
        if reordered is None:
            return found
        again = tool.replay_on_fresh_page(bridge, task, seed, reordered)
        log["order_questions"] += 1
        log["order_question_actions"] += len(again["trace"]) + 1
        if again["reproduced"]:
            log["order_questions_answered_yes"] += 1
            return again["trace"]
        return found

    skills = SkillSet()
    skills.add_success(settled(trace, tool.DEMO_SEED))
    for seed in practice_seeds:
        if not bridge.load(task).get("ok"):
            break
        observation = bridge.reset(seed)
        run = skills.start(observation)
        attempt: list[tuple[Mapping[str, Any], str]] = []
        while run is not None and not observation.get("done") and len(attempt) < tool.MAX_EPISODE_STEPS:
            action = run.next_action(observation)
            if action is None:
                break
            attempt.append((observation, action))
            observation = bridge.act(tool.parse_action(action))
        if tool.succeeded(observation):
            log["own_success"] += 1
            if run is not None and run.searched:
                # the program found its own way there by looking; the record of the looking is
                # not a new way of doing the task and is not kept as one
                log["own_success_with_looking"] += 1
            elif skills.add_success(attempt) == "new_way":
                log["new_ways"] += 1
            continue
        shown = tool.demonstrate(bridge, task, seed, action_budget=action_budget, search=search)
        log["search_actions"] += int((shown["acquisition"] or {}).get("budget_spent") or 0)
        if shown["trace"] is None:
            log["no_success"] += 1
            continue
        log["found_by_search"] += 1
        if skills.add_success(settled(shown["trace"], seed)) == "new_way":
            log["new_ways"] += 1
    log["skills"] = skills.describe()
    return VersionSpaceArm(skills, log)
