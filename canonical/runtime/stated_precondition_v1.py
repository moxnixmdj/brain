"""Turn ONE located refusal into ONE fact, and keep it -- the generalisation the mission asked for.

WHAT THE OWNER ASKED. "Saving his exact experience must be in a very sufficient way, not just saving the
exact experience in a dumb way. Maybe we should do generalization." And: "what he doesn't know, he should
get it instantly ... I don't know what he should exactly save, what is not, and what we should generalize
and what is not."

THE ANSWER THIS FILE ARGUES, AND WHY IT IS NOT A GUESS. Do not save the action. Save the CONDITION the
environment stated, and nothing else. `ledgerctl record add --name alpha.beta --amount 12.50` is an
action that will never be worth repeating; `amount_must_be_whole` is true of every record, in every
database, forever. The action is the experience. The condition is the knowledge.

WHY THIS IS NOT WHAT `applicability_v1` ALREADY DOES. That module learns a requirement by ELIMINATION over
outcomes: a conjunction of facts survives if it is consistent with every success and every failure. Its
own docstring is explicit that with no failure it returns UNDETERMINED, because "necessity is only refuted
by failure". That is correct for what it does, and it CANNOT do this job -- measured 2026-11-23:

    evidence = [({'has_record:alpha'}, FAILED), ({'has_record:alpha','amount_whole:12.50'}, PASSED)]
    learn(evidence) -> AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS, 2 survivors

Two facts appeared together in the success and nothing distinguishes them, so elimination honestly refuses
to pick. But the environment DID distinguish them: it printed `AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50`. That
string names the fact that was missing and the value that was wrong. Elimination would throw away the only
thing the environment told us, then report that it cannot tell -- and the mission's whole premise is that
the environment is a better knowledge source than the documentation.

So a STATED requirement is not evidence to be eliminated against. It is a statement to be believed,
tested, and recorded with its provenance. The two coexist: a statement bootstraps a plan, elimination
refines it later once a failure contradicts it.

WHAT MAKES A REFUSAL A STATEMENT RATHER THAN A COMPLAINT -- and this is the whole discipline:

    AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50     a FACT + the VALUE that broke it   -> generalises
    PATH_OUTSIDE_REPOSITORY:<path>          a FACT + the VALUE that broke it   -> generalises
    NO_RECORDS_IN:alpha                     a FACT + the VALUE that was missing -> generalises
    TEST_PATHS_REQUIRED                     a KIND, no value                    -> cannot locate, refused
    TEST_ROOT_MISSING                       a KIND, no value                    -> cannot locate, refused
    SUITE_FAILED_AFTER_MOVE: Start dir...   prose, not a code:value            -> refused

The first three teach a predicate over a value: "a record whose amount has a decimal point is refused".
The last three teach only that SOMETHING was missing, and a requirement built from them would be a guess
wearing a fact's clothes. This module refuses them and says so -- that is the difference between learning
and confabulating, and it is the same rule A87 applied when it refused to invent ":test_paths".

HOW A FACT IS SPELLED. `code` says what the environment demands; `value` says what it demands it of. The
fact is `<code>:<value>`, lowercased and with the value normalised, so that the SAME rule stated by a
different program, or by the same program on a different input, lands in the same place:

    AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50  ->  amount_must_be_a_whole_number:12.50
    AMOUNT_MUST_BE_A_WHOLE_NUMBER:3.75   ->  amount_must_be_a_whole_number:3.75

Two values, one rule. The rule is the `code`; the value is the instance. A predicate that asks
"is this value whole?" is derived by comparing the value in the fact with a value the caller offers.

THE TEST THAT MAKES IT KNOWLEDGE RATHER THAN A LOG LINE: after one refusal, the same rule must REFUSE A
VALUE IT HAS NEVER SEEN -- `7.25`, not `12.50`. If it only remembers `12.50` it is a cache; if it refuses
`7.25` it has learned what "whole number" means, from one experience, with no model and no retraining.
That is the difference the mission turns on, and it is measurable.

WHAT THIS FILE REFUSES TO DO:
  * invent a value the refusal did not carry (no `:test_paths`);
  * record a claim as knowledge before a run contradicted it and a later run satisfied it;
  * keep the raw action. There is deliberately no field for it: an action is not knowledge.

Authority NONE. Pure function of what the environment printed. Zero model calls, $0.
"""
from __future__ import annotations

import json
import pathlib
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_STATED_PRECONDITION_V1"

#: Where learned conditions live. Outside the weights, editable by hand, removable without retraining --
#: the §2 boundary made concrete. A fact added here changes behaviour on the next call; a fact deleted
#: here removes it. No parameter is touched, because there are no parameters: this IS the knowledge.
STORE = pathlib.Path("canonical/runtime/state/stated_preconditions_v1.json")

#: `CODE:value` -- a refusal that located its own subject. The code is the demand; the value is what the
#: demand was about. Uppercase codes only, at least 4 characters. SEARCHED, not anchored: a refusal is
#: often wrapped by the exception that carried it (`RuntimeError: MODULE_NOT_FOUND:file_survey`), and the
#: statement is still in there. A CamelCase exception name cannot match -- `RuntimeError` is `R` followed
#: by lowercase, and the class requires four or more uppercase characters -- so the wrapper is skipped
#: and the code it wraps is found.
_LOCATED = re.compile(r"([A-Z][A-Z0-9_]{3,}):(\S[^\s:]*)")

#: A value that is one token and looks like a name, number or path. A refusal whose "value" is a whole
#: sentence is prose, and prose is not a predicate -- `SUITE_FAILED_AFTER_MOVE: Start directory is not
#: importable` must not become a fact called `suite_failed_after_move`.
_VALUE = re.compile(r"^[A-Za-z0-9_./\\-]{1,64}$")


def parse(refusal: str) -> dict[str, Any] | None:
    """Read one refusal. Return the condition it states, or None when it states none.

    None is not a failure of this function; it is its most important answer. Most refusals in this
    tree -- 1,029 of 1,588 measured in A87b -- carry no subject, and a learner that guessed one would
    be inventing the very knowledge it claims to have acquired.
    """
    text = str(refusal or "").strip()
    # a refusal may be `CODE:value` or `ExceptionType:CODE:value`; take the LAST `<CODE>:<value>` whose
    # code is uppercase, because a Python exception name is CamelCase and cannot match `_LOCATED`.
    for line in reversed(text.splitlines()):
        found = list(_LOCATED.finditer(line))
        if not found:
            continue
        # the LAST located code on the line is the most specific: `WRAPPER:INNER:value` names INNER.
        match = found[-1]
        code = match.group(1)
        value = match.group(2)
        if not _VALUE.match(value):
            # a code whose "value" is prose states a KIND and not an instance -- it cannot be located
            return None
        return {"code": code, "value": value, "fact": "%s:%s" % (code.lower(), value.lower())}
    return None


def _predicate(code: str, seen: str) -> dict[str, Any] | None:
    """The rule `code` states about a value, derived from the ONE value it was stated about.

    A code is not a name to be looked up in a table -- that would be the knowledge house in miniature.
    It is a sentence in a small spelling convention, and reading it is derivation: `MUST_BE_A_WHOLE_NUMBER`
    says the value must be whole, so `whole` is the property to test and the property is decidable.

    Returns None when the code does not name a decidable property. That is a refusal, not a gap: a rule
    this function cannot read is a rule it will not pretend to know.
    """
    lowered = code.lower()
    tokens = set(lowered.split("_"))
    # Property names the convention can express. Each is derived from the code's own words, not from a
    # list of tools: `must_be_a_whole_number` -> whole; `must_not_exist` -> fresh; `already_taken` ->
    # unique. A code that names none of these is not readable here.
    if "whole" in tokens and "number" in tokens:
        return {"property": "whole", "test": "is_whole", "because": code}
    if tokens & {"already", "taken", "exists", "duplicate"}:
        return {"property": "unique", "test": "is_absent", "because": code}
    # `MODULE_NOT_FOUND:<name>` demands that the thing exist. The code's last token says it.
    if "not" in tokens and "found" in tokens:
        return {"property": "present", "test": "is_present", "because": code}
    if tokens & {"missing", "required", "absent", "not_found"}:
        return {"property": "present", "test": "is_present", "because": code}
    # `NO_RECORDS_IN:<prefix>` says the prefix holds nothing, so the fact it demands is that the prefix
    # EXISTS. Read from the code's own words: `no ... in X` is a statement about X's contents.
    if "no" in tokens or "empty" in tokens:
        return {"property": "present", "test": "is_present", "because": code}
    if tokens & {"outside", "escape", "escapes", "escaped", "traversal", "beneath", "contained"}:
        return {"property": "inside", "test": "is_inside", "because": code}
    # `SOURCE_ROOT_NOT_DIRECTORY`, `NOT_A_FILE`, `NOT_A_DIR` -- the value must be the kind of thing the
    # program can use. The kind is in the code, so it is read and not guessed.
    if "directory" in tokens or tokens & {"dir", "folder"}:
        return {"property": "directory", "test": "is_a_directory", "because": code}
    if tokens & {"file", "filepath", "filename"}:
        return {"property": "file", "test": "is_a_file", "because": code}
    if tokens & {"object", "mapping", "dict"}:
        return {"property": "object", "test": "is_an_object", "because": code}
    # `NEW_NAME_COLLIDES`, `COLLISION`, `CONFLICT` -- the same demand as `already taken`.
    if tokens & {"collides", "collision", "collisions", "conflict", "conflicts"}:
        return {"property": "unique", "test": "is_absent", "because": code}
    return None


def _whole(value: Any) -> bool:
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return False
    return number == int(number)


def is_satisfied(predicate: Mapping[str, Any], value: Any, universe: Iterable[Any] = ()) -> bool:
    """Would the environment accept `value`, given what it stated about a DIFFERENT value?

    `universe` is what exists, for `is_absent`/`is_present`. It is passed by the caller rather than
    stored here: a fact about the world that arrived with the refusal is knowledge; a copy of the world
    is a stale cache, and this project has already been burned by caching an environment.
    """
    test = str(predicate.get("test") or "")
    if test == "is_whole":
        return _whole(value)
    if test == "is_absent":
        return str(value).lower() not in {str(u).lower() for u in universe}
    if test == "is_present":
        return str(value).lower() in {str(u).lower() for u in universe}
    if test == "is_inside":
        root = str(predicate.get("universe") or "")
        return str(value).startswith(root) if root else True
    # THE KIND TESTS NEED THE WORLD, so they are answers the caller must supply rather than facts this
    # module assumes. `universe` carries them: a directory test asks whether the value is among the
    # directories the caller observed. Absent that, the honest answer is "unknown", never "fine".
    if test == "is_a_directory":
        return str(value) in {str(u) for u in universe}
    if test == "is_a_file":
        return str(value) in {str(u) for u in universe}
    if test == "is_an_object":
        return isinstance(value, Mapping) or (isinstance(value, str) and value.strip().startswith("{"))
    return False


def _load(store: pathlib.Path | None = None) -> dict[str, Any]:
    path = pathlib.Path(store) if store else STORE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": SCHEMA, "conditions": {}}
    if not isinstance(data, dict):
        return {"schema": SCHEMA, "conditions": {}}
    data.setdefault("conditions", {})
    return data


def _save(data: Mapping[str, Any], store: pathlib.Path | None = None) -> None:
    path = pathlib.Path(store) if store else STORE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def learn(refusal: str, *, at: str = "", store: pathlib.Path | None = None) -> dict[str, Any]:
    """Learn the condition ONE refusal states. Returns the record, or why nothing was learned.

    `at` is WHICH capability or program refused. It is stored as provenance, and it is deliberately NOT
    part of the key: the condition is about the value, not about who complained. A rule learned from one
    program must be offered to another -- that is what makes it generalisation rather than a per-tool
    patch, and it is exactly the mistake `macro_v1` documents five times (an environment-specific
    pathology turned into a global ban).

    What IS keyed is the CODE: one rule, one entry, however many values demonstrate it. Two programs that
    both demand a whole number converge on one condition instead of two.
    """
    stated = parse(refusal)
    if stated is None:
        return {"schema": SCHEMA, "learned": False, "why": "REFUSAL_DOES_NOT_LOCATE_ITS_SUBJECT",
                "refusal": str(refusal)[:200]}
    predicate = _predicate(stated["code"], stated["value"])
    if predicate is None:
        return {"schema": SCHEMA, "learned": False, "why": "CODE_NAMES_NO_DECIDABLE_PROPERTY",
                "code": stated["code"], "value": stated["value"]}
    data = _load(store)
    key = stated["code"].lower()
    entry = data["conditions"].get(key) or {
        "code": stated["code"], "predicate": predicate, "values": [], "seen_at": [],
        "refusals": 0,
    }
    if stated["value"].lower() not in [v.lower() for v in entry["values"]]:
        entry["values"].append(stated["value"])
    if at and at not in entry["seen_at"]:
        entry["seen_at"].append(at)
    entry["refusals"] = int(entry.get("refusals") or 0) + 1
    entry["predicate"] = predicate
    data["conditions"][key] = entry
    _save(data, store)
    return {"schema": SCHEMA, "learned": True, "key": key, "fact": stated["fact"],
            "predicate": predicate, "values": list(entry["values"]), "seen_at": list(entry["seen_at"]),
            "one_rule_many_values": len(entry["values"]) > 1}


def conditions(store: pathlib.Path | None = None) -> dict[str, Any]:
    """Everything learned, for inspection and for hand editing. This is the knowledge store."""
    return _load(store)["conditions"]


def would_refuse(value: Any, *, code: str, universe: Iterable[Any] = (),
                 store: pathlib.Path | None = None) -> dict[str, Any]:
    """Ask the learned rule about a value it has NEVER seen. This is the generalisation test.

    `code` is the rule's name, not a program's: the caller asks `AMOUNT_MUST_BE_A_WHOLE_NUMBER` and gets
    an answer about `7.25` although the only value ever observed was `12.50`.
    """
    entry = conditions(store).get(str(code).lower())
    if not entry:
        return {"schema": SCHEMA, "known": False, "code": code}
    predicate = entry.get("predicate") or {}
    satisfied = is_satisfied(predicate, value, universe)
    return {"schema": SCHEMA, "known": True, "code": code, "value": value,
            "satisfied": satisfied, "refuse": not satisfied,
            "property": predicate.get("property"),
            "seen_values": list(entry.get("values") or []),
            "value_never_seen": str(value).lower() not in [v.lower() for v in entry.get("values") or []]}


def forget(code: str, *, store: pathlib.Path | None = None) -> bool:
    """Remove a rule without retraining anything. The §2 test, executable."""
    data = _load(store)
    key = str(code).lower()
    if key not in data["conditions"]:
        return False
    del data["conditions"][key]
    _save(data, store)
    return True


def main(argv: Sequence[str] | None = None) -> int:
    """Learn from refusals given on stdin or as arguments; print the store."""
    import sys
    arguments = list(argv if argv is not None else sys.argv[1:])
    for refusal in arguments:
        print(json.dumps(learn(refusal), sort_keys=True))
    if not arguments:
        print(json.dumps({"schema": SCHEMA, "conditions": conditions()}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
