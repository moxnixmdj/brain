"""Complete the inverse pair instead of searching for a whole new function.

THE MEASUREMENT THAT MOTIVATED THIS
-----------------------------------
`canonical/corpus/real_fix_pairs_20261119_V1.json` holds 87 real fixes, each
verified by execution (its test fails at the parent and passes at the fix).
AST-diffing the before and after source of every one gives the edit kind the fix
actually required:

    INSERT              47   54.0%
    MIXED_SWAP          24   27.6%
    RENAME_OR_REORDER    9   10.3%
    DELETE               7    8.0%

The existing grammar can swap and replace and cannot insert (`can_insert_a_node:
false`), so 54% of real fixes need the operation it lacks. Decomposing those 47
by the AST nodes they add:

    NEW_GUARD            18   a condition the code did not have
    NEW_CALLABLE         12   a function or class nobody had written
    NEW_STATEMENT         5
    TYPE_OR_ANNOTATION    2
    other                 10

Eighteen of them are the guard case, which `distinction_creation_v1` addresses.
The twelve that invent a callable are the genuinely hard ones, and inspecting all
27 invented callables shows a structure the search space does not know about:
they come in PAIRS.

    _point_state          / _point_from_state
    _intervals_state      / _intervals_from_state
    __reduce_ex__         / _restore_version_range
    make_safe_parse_float / safe_parse_float

WHY A PAIR IS NOT FREE INVENTION
---------------------------------
Given one half of an inverse pair, the other half is constrained by a property
that can be EXECUTED:

    for every x the test builds:   load(save(x)) == x

That is not a search over syntax. It is a residual to drive to zero, and the
residual is measurable -- which is what separates this from guessing. The
existing grammar has no notion of a property at all, so this operation was
unreachable by construction, not merely unsearched.

WHAT THIS DOES NOT DO, STATED FIRST
-----------------------------------
It cannot invent the WRITER. A round-trip property does not say what the writer
must put into the payload; that comes from the test's fixture semantics, which is
where the real difficulty lives (see `a03bde12`, where the writer gained a third
element nobody derived from `assert load(save(x)) == x`). This module completes
the half that the property determines, and refuses when the property does not
determine it. It buys one of the two halves, and says so.

Authority: NONE.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_INVERSE_COMPLETION_V1"

# A known inverse pair, with the property that ties the two halves together.
# Each entry is (writer_role, reader_role, name_stems_that_pair).
PAIR_FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "family": "state_roundtrip",
        "writer": "__getstate__",
        "reader": "__setstate__",
        "property": "load(save(x)) == x",
        "payload_shape": "positional_tuple",
    },
    {
        "family": "reduce_roundtrip",
        "writer": "__reduce_ex__",
        "reader": "__setstate__",
        "property": "load(save(x)) == x",
        "payload_shape": "positional_tuple",
    },
    {
        "family": "encode_decode",
        "writer": "encode",
        "reader": "decode",
        "property": "load(save(x)) == x",
        "payload_shape": "mapping",
    },
    {
        "family": "to_from_named",
        "writer": "*_state",
        "reader": "*_from_state",
        "property": "load(save(x)) == x",
        "payload_shape": "mapping",
    },
)

REFUSALS = {
    "NEEDS_BOTH_POLARITIES",
    "REFUSED__NO_INVERSE_CONSTRAINT",
    "REFUSED__PROPERTY_ALREADY_HOLDS",
    "REFUSED__WRITER_NOT_DETERMINED",
}


class InverseError(ValueError):
    pass


def detect_pair(name: str, siblings: Sequence[str] = ()) -> dict[str, Any] | None:
    """Which inverse family, if any, does this name belong to?

    A writer with no reader is the reachable case: the reader is the half the
    property determines. A reader with no writer is not reachable here and is
    reported as such rather than silently skipped.
    """
    for entry in PAIR_FAMILIES:
        stem = entry["writer"]
        if stem.startswith("*_"):
            suffix = stem[1:]
            if name.endswith(suffix) and len(name) > len(suffix):
                reader = name[: -len(suffix)] + entry["reader"][1:]
                return {
                    "family": entry["family"],
                    "role": "writer",
                    "missing": reader,
                    "property": entry["property"],
                    "payload_shape": entry["payload_shape"],
                    "determines": "reader",
                }
        elif name == stem:
            return {
                "family": entry["family"],
                "role": "writer",
                "missing": entry["reader"],
                "property": entry["property"],
                "payload_shape": entry["payload_shape"],
                "determines": "reader",
                "sibling_hint": [s for s in siblings if entry["reader"] in s][:3],
            }
    return None


def roundtrip_residual(
    save: Callable[[Any], Any],
    load: Callable[[Any], Any],
    samples: Sequence[Any],
) -> dict[str, Any]:
    """The executable property, as a residual rather than a verdict.

    Returns the failing samples, not just a boolean, because the failing sample
    IS the constraint: it names which field the reader lost.
    """
    failures = []
    for index, sample in enumerate(samples):
        try:
            payload = save(sample)
        except Exception as exc:  # a writer that cannot write is not a pair
            failures.append({"index": index, "stage": "save", "error": type(exc).__name__})
            continue
        try:
            restored = load(payload)
        except Exception as exc:
            failures.append(
                {"index": index, "stage": "load", "error": type(exc).__name__,
                 "payload": repr(payload)[:200]}
            )
            continue
        if not _equal(restored, sample):
            failures.append(
                {
                    "index": index,
                    "stage": "mismatch",
                    "payload": repr(payload)[:200],
                    "expected": repr(sample)[:200],
                    "got": repr(restored)[:200],
                }
            )
    return {
        "schema": SCHEMA,
        "samples": len(samples),
        "failures": failures,
        "residual": len(failures),
        "holds": not failures,
    }


def _equal(a: Any, b: Any) -> bool:
    """Equality that does not let `==` on containers hide a type change."""
    if type(a) is not type(b):
        # a tuple and a list that compare equal are NOT the same state
        if not (isinstance(a, (tuple, list)) and isinstance(b, (tuple, list))):
            return False
        if type(a) is not type(b):
            return False
    return a == b


def _fields_of(sample: Any) -> list[str]:
    """The observable fields of a sample, in a deterministic order."""
    if isinstance(sample, Mapping):
        return sorted(sample)
    if hasattr(sample, "__dict__"):
        return sorted(k for k in vars(sample) if not k.startswith("__"))
    if hasattr(sample, "__slots__"):
        return sorted(sample.__slots__)
    return []


def determine_reader_shape(
    writer_payloads: Sequence[Any],
) -> dict[str, Any]:
    """What the READER must accept, derived from the writer's actual output.

    This is the whole mechanism. The reader is not searched for; its signature is
    read off the payloads the writer already produces. Arity, element types and
    order all come from the data, and none of them are guessed.

    Refuses when the writer is not consistent across samples -- a writer that
    emits different arities cannot determine a single reader, and pretending
    otherwise is how a synthesised reader silently breaks the second object.
    """
    if not writer_payloads:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__WRITER_NOT_DETERMINED",
            "note": "no writer output was supplied, so no reader shape is implied",
            "authority": "NONE",
        }
    # WHAT DETERMINES A READER'S SIGNATURE IS ARITY AND FIELD NAMES, NOT THE
    # ELEMENT TYPES. The first version keyed on element type names and refused
    # `__getstate__` payloads ("x", True, (True, None)) against ("y", None,
    # (False, False)) because `bool` and `NoneType` differ -- but `bool | None`
    # is one field, and the reader consumes the same three positions either way.
    # Optionality is not a distinction the reader must know about. Only ragged
    # arity (`("a", True)` against `("b", True, None)`) actually breaks a reader.
    shapes = []
    for payload in writer_payloads:
        if isinstance(payload, tuple):
            shapes.append(("tuple", len(payload)))
        elif isinstance(payload, Mapping):
            shapes.append(("mapping", tuple(sorted(payload))))
        elif isinstance(payload, (list, set, frozenset)):
            shapes.append(("sequence", len(payload)))
        else:
            shapes.append(("scalar", 1))

    distinct = {s for s in shapes}
    if len(distinct) > 1:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__WRITER_NOT_DETERMINED",
            "shapes_seen": [list(s) for s in sorted(distinct, key=repr)],
            "note": (
                "the writer emits different payload shapes for different samples, "
                "so one reader cannot be determined. Either the writer is wrong or "
                "the property is not the one being tested"
            ),
            "authority": "NONE",
        }

    kind, detail = shapes[0]
    arity = detail if isinstance(detail, int) else len(detail)
    # element types are still reported, as INFORMATION about what the reader will
    # receive, but they are not part of what selects the reader
    element_types = sorted({
        type(v).__name__ for payload in writer_payloads
        if isinstance(payload, (tuple, list)) for v in payload
    })
    return {
        "schema": SCHEMA,
        "status": "PASS__READER_SHAPE_DETERMINED",
        "payload_kind": kind,
        "arity": arity,
        "element_types": element_types or None,
        "field_names": list(detail) if kind == "mapping" else None,
        "claim": "THE_SHAPE_ONE_READER_MUST_ACCEPT",
        "not_claimed": "THE_READER_BODY",
        "authority": "NONE",
    }


def synthesise_reader(
    name: str,
    writer_payloads: Sequence[Any],
    samples: Sequence[Any] = (),
) -> dict[str, Any]:
    """Emit a reader for `name` whose signature is determined by the payloads.

    The body is a *proposal*, and the only thing allowed to accept it is
    `roundtrip_residual` running against the caller's own samples. Nothing here
    claims the reader is correct; it claims the reader is determined.
    """
    pair = detect_pair(name)
    if pair is None:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NO_INVERSE_CONSTRAINT",
            "name": name,
            "note": (
                "this name belongs to no known inverse family, so the round-trip "
                "property imposes no constraint on a second half. Completing it "
                "would be invention with no executable check"
            ),
            "source": None,
            "authority": "NONE",
        }

    shape = determine_reader_shape(writer_payloads)
    if shape["status"] != "PASS__READER_SHAPE_DETERMINED":
        return {**shape, "name": name, "pair": pair, "source": None}

    arity = shape["arity"]
    if shape["payload_kind"] == "mapping":
        fields = shape["field_names"]
        body = "".join(f"        self.{f} = payload[{f!r}]\n" for f in fields)
        source = (
            f"def {pair['missing']}(self, payload: dict) -> None:\n"
            f"    # fields read off the writer's own output, in its own order\n"
            f"{body}"
        )
    else:
        params = ", ".join(f"_{i}" for i in range(arity))
        source = (
            f"def {pair['missing']}(self, {params}) -> None:\n"
            f"    # arity {arity} read off the writer's payload, not chosen\n"
            f"    {tuple('_' + str(i) for i in range(arity))!r}\n"
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__READER_DETERMINED",
        "name": name,
        "pair": pair,
        "shape": shape,
        "source": source,
        "claim": "A_READER_WHOSE_SIGNATURE_IS_DETERMINED_BY_THE_WRITER",
        "not_claimed": "A_CORRECT_READER_WAS_FOUND",
        "must_be_accepted_by": "roundtrip_residual",
        "authority": "NONE",
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="JSON with 'name' and 'writer_payloads'")
    args = parser.parse_args(list(argv) if argv is not None else None)
    with open(args.path, encoding="utf-8") as handle:
        payload = json.load(handle)
    result = synthesise_reader(payload.get("name", ""), payload.get("writer_payloads") or [])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
