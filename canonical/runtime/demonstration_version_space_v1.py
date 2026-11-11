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
  a position is: the n-th from the start or the end; the n-th where n is a number in the
      instruction; or the one NEAREST, in the page tree, to an element the instruction names
      ("the trash icon in the row of the sender it mentions").
  a slot is a rule for cutting a piece out of the instruction: the k-th quoted span, the text
      between two given tokens (or the start / the end), the k-th number;
  typed text is a slot (optionally upper- or lower-cased), a copy of a field of a described
      element, or a constant.
  A program is a fixed sequence of steps. There are no loops, no conditions, no arithmetic
  and no search at run time. A task that needs any of those is outside this language and
  fails here; that is a boundary, reported as one, not a defect to paper over.

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

STRUCTURE_FIELDS = ("tag", "type", "id", "classes", "role", "name", "placeholder", "for", "title")
CONTENT_FIELDS = ("text", "full_text", "value")
RELATIONS = ("self", "parent", "prev", "next", "label")
MAX_CONTENT_LENGTH = 80
MAX_HYPOTHESES_PER_STEP = 6000

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
        else:
            wanted = key[3] if kind == "equals" else key[2]
        hits = set()
        if wanted is not None:
            for index in range(len(self.elements)):
                other = self.neighbour(index, relation)
                if other is None:
                    continue
                if kind == "has_class":
                    if wanted in self.field(other, "classes").split():
                        hits.add(index)
                else:
                    value = self.field(other, key[2])
                    if kind == "slot" and key[4] == "fold":
                        value = value.lower()
                    if value == wanted:
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
            for name in ("tag", "type"):          # "click on a textarea": the instruction names the KIND
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
    if by_place:
        rank = 3
    elif bound:
        rank = 0
    elif quotes_content:
        rank = 2
    else:
        rank = 1
    bound_tests = [t for t in tests if _is_bound(t)]
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
    return (rank, reach, slot_rank, -len(tests), -on_self, crowd, repr(description))


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
        return (2, 0, repr(expression))
    return (3, 0, repr(expression))


# --------------------------------------------------------------------------- #
# the skill: what still fits every success
# --------------------------------------------------------------------------- #
def _parse(action: str) -> tuple[str, int, str]:
    kind, _, rest = str(action).partition("@")
    if kind == "click":
        return "click", int(rest), ""
    index, _, text = rest.partition("=")
    return "type", int(index), text


class VersionSpaceSkill:
    """Per step: the descriptions (and typed-text expressions) consistent with every success."""

    def __init__(self) -> None:
        self.kinds: list[str] = []
        self._examples: list[list[tuple[Page, int, str]]] = []
        self._targets: list[list[tuple[Any, ...]]] = []
        self._texts: list[list[tuple[Any, ...]]] = []
        self._slot_rules: list[tuple[Any, ...]] | None = None
        self.rejected_examples = 0

    @property
    def examples(self) -> int:
        return len(self._examples)

    def add_success(self, trace: Sequence[tuple[Mapping[str, Any], str]]) -> bool:
        """Take one more verified success. False -- and nothing changes -- when no single
        program in the language accounts for it together with the successes already held:
        it has another shape (other length, other kinds of step), or some step would be left
        with no description, or no expression for its typed text, that fits them all."""
        parsed = [(Page(observation), *_parse(action)) for observation, action in trace]
        kinds = [kind for _, kind, _, _ in parsed]
        if not parsed:
            return False
        if self._examples and kinds != self.kinds:
            self.rejected_examples += 1
            return False
        examples = self._examples + [[(page, index, text) for page, _, index, text in parsed]]
        targets, texts = self._fit(kinds, examples)
        unexplained = any(not t for t in targets) or any(
            kind == "type" and not x for kind, x in zip(kinds, texts))
        if unexplained and self._examples:
            self.rejected_examples += 1
            return False
        self.kinds = kinds
        self._examples = examples
        self._targets, self._texts = targets, texts
        self._slot_rules = None
        return True

    def instructions(self) -> list[str]:
        return [example[0][0].instruction for example in self._examples]

    def slot_rules(self) -> list[tuple[Any, ...]]:
        """Every slot rule some surviving description or text expression reads the instruction through."""
        if self._slot_rules is None:
            rules: dict[tuple[Any, ...], None] = {}
            for descriptions in self._targets:
                for tests, position in descriptions:
                    for test in tests:
                        if _is_bound(test):
                            rules.setdefault(tuple(test[3]), None)
                    if position is not None and position[0] == "nth_slot":
                        rules.setdefault(tuple(position[1]), None)
                    if position is not None and position[0] == "nearest":
                        rules.setdefault(tuple(position[2]), None)
            for expressions in self._texts:
                for expression in expressions:
                    if expression[0] == "slot":
                        rules.setdefault(tuple(expression[1]), None)
            self._slot_rules = list(rules)
        return self._slot_rules

    @staticmethod
    def _fit(kinds: Sequence[str], examples: Sequence[Sequence[tuple[Page, int, str]]]
             ) -> tuple[list[list[tuple[Any, ...]]], list[list[tuple[Any, ...]]]]:
        targets, texts = [], []
        for step, kind in enumerate(kinds):
            seen = [example[step] for example in examples]
            pages = [page for page, _, _ in seen]
            candidates: dict[tuple[Any, ...], None] = {}
            for page, index, _ in seen:
                for description in descriptions_of(page, index):
                    candidates.setdefault(description, None)
            kept = [d for d in candidates if all(pick(d, page) == index for page, index, _ in seen)]
            kept.sort(key=lambda d: preference(d, pages))
            targets.append(kept)
            if kind == "type":
                pool: dict[tuple[Any, ...], None] = {}
                for page, _, typed in seen:
                    for expression in expressions_for(page, typed):
                        pool.setdefault(expression, None)
                fitting = [x for x in pool if all(evaluate(x, page) == typed for page, _, typed in seen)]
                fitting.sort(key=expression_preference)
                texts.append(fitting)
            else:
                texts.append([])
        return targets, texts

    def act(self, step: int, observation: Mapping[str, Any]) -> str | None:
        """The action for this step on this page: the first surviving description that selects
        something here. None when the program is over or nothing that survived applies."""
        if step >= len(self.kinds):
            return None
        page = Page(observation)
        target = None
        for description in self._targets[step]:
            target = pick(description, page)
            if target is not None:
                break
        if target is None:
            return None
        element = page.elements[target]
        if self.kinds[step] == "click":
            return f"click@{target}" if element.get("can_click") else None
        if not element.get("can_type"):
            return None
        for expression in self._texts[step]:
            text = evaluate(expression, page)
            if text is not None:
                return f"type@{target}={text}"
        return None

    def describe(self) -> dict[str, Any]:
        steps = []
        for step, kind in enumerate(self.kinds):
            entry: dict[str, Any] = {"kind": kind, "descriptions_left": len(self._targets[step]),
                                     "first": repr(self._targets[step][0]) if self._targets[step] else None}
            if kind == "type":
                entry["text_expressions_left"] = len(self._texts[step])
                entry["first_text"] = repr(self._texts[step][0]) if self._texts[step] else None
            steps.append(entry)
        return {"schema": SCHEMA, "examples": self.examples, "rejected_examples": self.rejected_examples,
                "steps": steps}


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


def mismatch(skill: "VersionSpaceSkill", instruction: str) -> int:
    """How far a new instruction is from the ones this program was learned from, counting
    only what the program's own slots do not explain. A different quoted word costs nothing
    (the program reads it through a slot); a different fixed word does."""
    rules = skill.slot_rules()
    new = fixed_tokens(instruction, rules)
    return min((len(new ^ fixed_tokens(known, rules)) for known in skill.instructions()), default=len(new))


class SkillSet:
    """Several programs for one task, because one task can present itself in several ways.

    A success that fits no single program together with the ones already held is not
    evidence that nothing was learned; it is evidence of a second way ("type it in UPPER
    case" / "type it in lower case"). It starts a program of its own. On a new page the
    program whose own instructions differ least from the new one -- in the words its slots
    do not account for -- is the one that acts; a tie goes to the program with more
    successes behind it. The language still has no conditions INSIDE a program; this is a
    choice BETWEEN programs, made once, from the instruction alone.
    """

    def __init__(self) -> None:
        self.skills: list[VersionSpaceSkill] = []

    @property
    def examples(self) -> int:
        return sum(skill.examples for skill in self.skills)

    def _ordered(self, instruction: str) -> list[VersionSpaceSkill]:
        scored = [(mismatch(skill, instruction), -skill.examples, position, skill)
                  for position, skill in enumerate(self.skills)]
        scored.sort(key=lambda item: item[:3])
        return [skill for _, _, _, skill in scored]

    def add_success(self, trace: Sequence[tuple[Mapping[str, Any], str]]) -> str:
        """'refined' when an existing program took it, 'new_way' when it started its own."""
        if not trace:
            return "empty"
        instruction = str(trace[0][0].get("utterance") or "")
        for skill in self._ordered(instruction):
            if skill.add_success(trace):
                return "refined"
        fresh = VersionSpaceSkill()
        fresh.add_success(trace)
        self.skills.append(fresh)
        return "new_way"

    def choose(self, instruction: str) -> VersionSpaceSkill | None:
        ordered = self._ordered(instruction)
        return ordered[0] if ordered else None

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
        self._skill: VersionSpaceSkill | None = None
        self._step = 0
        self.refused = False

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        self._skill = self.skills.choose(str(observation.get("utterance") or ""))
        self._step = 0
        self.refused = False

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        action = None if self._skill is None else self._skill.act(self._step, observation)
        if action is None and self._step == 0:
            self.refused = True
        self._step += 1
        return action


def build_arm(*, bridge: Any, task: str, trace: Sequence[tuple[Mapping[str, Any], str]],
              practice_seeds: Sequence[int], action_budget: int, tier: int, tool: Any,
              search: str = "blind") -> VersionSpaceArm:
    """Start from one success. On each practice instance try what is held; if the page says
    no, find a success there by exploration and take that. Either way the only thing ever
    added is a trace the page itself rewarded."""
    skills = SkillSet()
    skills.add_success(trace)
    log = {"own_success": 0, "found_by_search": 0, "new_ways": 0, "no_success": 0,
           "search_actions": 0, "practice_instances": len(list(practice_seeds))}
    for seed in practice_seeds:
        if not bridge.load(task).get("ok"):
            break
        observation = bridge.reset(seed)
        skill = skills.choose(str(observation.get("utterance") or ""))
        attempt: list[tuple[Mapping[str, Any], str]] = []
        while skill is not None and not observation.get("done") and len(attempt) < tool.MAX_EPISODE_STEPS:
            action = skill.act(len(attempt), observation)
            if action is None:
                break
            attempt.append((observation, action))
            observation = bridge.act(tool.parse_action(action))
        if tool.succeeded(observation):
            if skills.add_success(attempt) == "new_way":
                log["new_ways"] += 1
            log["own_success"] += 1
            continue
        shown = tool.demonstrate(bridge, task, seed, action_budget=action_budget, search=search)
        log["search_actions"] += int((shown["acquisition"] or {}).get("budget_spent") or 0)
        if shown["trace"] is None:
            log["no_success"] += 1
            continue
        log["found_by_search"] += 1
        if skills.add_success(shown["trace"]) == "new_way":
            log["new_ways"] += 1
    log["skills"] = skills.describe()
    return VersionSpaceArm(skills, log)
