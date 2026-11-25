"""The law library: observables a repository's own API must satisfy, independent of any test.

Each law names *what it observes* and *why a violation is a defect*, and none of them may look at a
test file. They are checked around calls the repository's existing (green) suite makes, plus a few
probes the law manufactures itself. A law that cannot fire on a defect class is recorded as silent
rather than tuned until it fires: silent is a coverage fact, noise is a lie.

Vocabulary is universal on purpose. `encode`/`decode`, `dump`/`load`, `normalize`, `Error` classes and
generators mean the same thing in every Python code base, which is what lets a law transfer across
repositories without a per-repository rule.
"""

from __future__ import annotations

import ast
import re
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence

__all__ = [
    "PAIR_STEMS",
    "IDEMPOTENT_VERBS",
    "HEADER_TOKENS",
    "BUILTIN_ESCAPES",
    "Violation",
    "check_canonicality",
    "check_round_trip",
    "check_idempotence",
    "check_error_inconsistency",
    "classify_exception",
    "check_iterable_retyping",
    "static_assert_validation",
    "mutations_for",
    "package_error_classes",
    "StrippedList",
    "NoneReversed",
    "safe_equal",
]

# `encode`/`decode` style pairs: (forward stem, inverse stem).
PAIR_STEMS: tuple[tuple[str, str], ...] = (
    ("encode", "decode"),
    ("dumps", "loads"),
    ("dump", "load"),
    ("serialize", "deserialize"),
    ("to_json", "from_json"),
    ("to_bytes", "from_bytes"),
    ("pack", "unpack"),
    ("compress", "decompress"),
    ("freeze", "thaw"),
    ("format", "parse"),
    ("quote", "unquote"),
    ("escape", "unescape"),
    ("to_string", "from_string"),
)

IDEMPOTENT_VERBS = (
    "normalize", "canonicalize", "canon", "clean", "sanitize", "strip_", "trim", "ensure_",
    "simplify", "dedupe", "squash",
)

HEADER_TOKENS = ("header", "to_header", "www_auth", "authenticate", "format", "serialize", "to_str", "__str__")

# A builtin escaping a library that defines its own error hierarchy is an observable defect: the
# caller cannot write `except LibraryError`, which is the only reason the hierarchy exists.
BUILTIN_ESCAPES = (TypeError, ValueError, KeyError, IndexError)

_WS_MULTI = re.compile(r"  +")
_SPACE_BEFORE_COMMA = re.compile(r"\s+,")
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f]")


class Violation(dict):
    """Something the repository promised and did not deliver."""

    def __init__(self, law: str, where: str, detail: str, **extra: Any) -> None:
        super().__init__(law=law, where=where, detail=detail, **extra)


def safe_equal(left: Any, right: Any) -> bool | None:
    """Three-valued equality: `None` when the values cannot be compared meaningfully.

    Generators, file handles and other lazy objects are not comparable; treating "cannot compare" as
    "unequal" is how a law library fills up with false accusations.
    """
    if left is right:
        return True
    for value in (left, right):
        if hasattr(value, "__next__") or hasattr(value, "read") or type(value).__name__ in {"generator", "function"}:
            return None
    try:
        outcome = bool(left == right)
    except Exception:
        return None
    return outcome


def check_canonicality(name: str, result: Any) -> list[Violation]:
    """A string the API hands out as a header/token/serialized form must be whitespace-canonical.

    Trailing whitespace is not cosmetic in a protocol value: `Bearer realm="x", ` and `Bearer  token`
    are rejected by strict parsers, and the defect is invisible to a test that strips before comparing.
    """
    if not isinstance(result, str) or not result:
        return []
    lowered = name.lower()
    if not any(tok in lowered for tok in HEADER_TOKENS):
        return []
    out: list[Violation] = []
    if result != result.strip():
        out.append(Violation("string_canonicality", name, "leading or trailing whitespace", value=result[:120]))
    if _WS_MULTI.search(result):
        out.append(Violation("string_canonicality", name, "repeated whitespace", value=result[:120]))
    if _SPACE_BEFORE_COMMA.search(result):
        out.append(Violation("string_canonicality", name, "whitespace before a separator", value=result[:120]))
    if _CTRL.search(result):
        out.append(Violation("string_canonicality", name, "control byte in a presented string", value=result[:120]))
    return out


def _pair_for(name: str) -> tuple[str, str] | None:
    base = name.split(".")[-1]
    for forward, inverse in PAIR_STEMS:
        if base == forward or base.startswith(forward + "_") or base.endswith("_" + forward):
            return forward, inverse
        if base == inverse or base.startswith(inverse + "_") or base.endswith("_" + inverse):
            return None  # only the forward direction is exercised
    return None


def check_round_trip(name: str, args: Sequence[Any], result: Any, inverse: Callable[[Any], Any] | None) -> list[Violation]:
    """`decode(encode(x)) == x`: an emitter and parser that disagree are not inverse functions."""
    if inverse is None or not args:
        return []
    if _pair_for(name) is None:
        return []
    if isinstance(result, (bytes, str, bytearray, memoryview)):
        try:
            back = inverse(result)
        except Exception as exc:  # the inverse refusing its own product is itself the defect
            return [Violation("round_trip", name, f"inverse raised {type(exc).__name__}: {exc}")]
        verdict = safe_equal(back, args[0])
        if verdict is False:
            return [Violation("round_trip", name, "inverse product differs from the input",
                              got=repr(back)[:80], expected=repr(args[0])[:80])]
    return []


def check_idempotence(name: str, fn: Callable[..., Any], args: Sequence[Any], result: Any) -> list[Violation]:
    """`f(f(x)) == f(x)` for anything named like a normalizer."""
    base = name.split(".")[-1].lower()
    if not any(base.startswith(v) or v in base for v in IDEMPOTENT_VERBS):
        return []
    if not args or result is None:
        return []
    try:
        again = fn(result)
    except Exception as exc:
        return [Violation("idempotence", name, f"second application raised {type(exc).__name__}")]
    verdict = safe_equal(again, result)
    if verdict is False:
        return [Violation("idempotence", name, "not idempotent", once=repr(result)[:60], twice=repr(again)[:60])]
    return []


def package_error_classes(module_name: str, cache: dict[str, tuple[type, ...]] | None = None) -> tuple[type, ...]:
    """Every exception class the *package* defines, found by scanning already-imported modules."""
    root = module_name.split(".")[0]
    if cache is not None and root in cache:
        return cache[root]
    found: list[type] = []
    for mod_name, module in list(sys.modules.items()):
        if not mod_name.startswith(root) or module is None:
            continue
        for attr in vars(module).values():
            if isinstance(attr, type) and issubclass(attr, BaseException):
                if attr.__module__.split(".")[0] == root and attr not in found:
                    found.append(attr)
    result = tuple(found)
    if cache is not None:
        cache[root] = result
    return result


def classify_exception(exc_type: type, errors: tuple[type, ...]) -> str:
    """`library` / `builtin` / `other` — where an exception sits relative to the library's hierarchy."""
    if errors and issubclass(exc_type, errors):
        return "library"
    if issubclass(exc_type, BUILTIN_ESCAPES):
        return "builtin"
    return "other"


def check_error_inconsistency(
    name: str,
    module_name: str,
    outcomes: Sequence[tuple[str, type | None]],
    *,
    errors: tuple[type, ...],
) -> list[Violation]:
    """The *same* function must not answer malformed input sometimes with its own error, sometimes
    with a bare builtin.

    The weaker law ("a builtin escaped a library that defines errors") was measured and rejected: it
    fired identically on buggy and fixed trees on six of six commits, because plenty of functions
    legitimately raise `TypeError` and a package-wide error class says nothing about them. What is
    actually an observable defect is the *inconsistency*: `exp="x"` raising `PyJWTError` while
    `exp=None` raises `TypeError` means a caller cannot write one `except` clause.
    """
    if not errors:
        return []
    families = {classify_exception(t, errors) for _label, t in outcomes if t is not None}
    if "library" in families and "builtin" in families:
        detail = ", ".join(f"{label}={t.__name__ if t else 'ok'}" for label, t in outcomes if t is not None)
        return [Violation("error_discipline", name, f"mixed exception families: {detail}", module=module_name)]
    return []


class NoneReversed:
    """An iterable whose optional `__reversed__` protocol is present but set to `None`.

    That is the distinction Python actually makes and `hasattr` erases: the attribute exists, so
    `hasattr` is True, but `reversed()` fails because the protocol is *absent by value*.
    Measured need: `more_itertools.last()` used `hasattr(iterable, '__reversed__')`, so an object with
    `__reversed__ = None` fell into the `reversed()` branch and returned the default instead of its
    element. A list subclass never shows this, because `Sequence` short-circuits the check first.
    """

    __reversed__ = None  # type: ignore[assignment]

    def __init__(self, items: Iterable[Any]) -> None:
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)


class StrippedList(list):
    """A list with its optional protocols removed: no `__reversed__`, no `__len__`."""

    __reversed__ = None  # type: ignore[assignment]

    def __len__(self) -> int:  # type: ignore[override]
        raise TypeError("object of type 'StrippedList' has no len()")


def _iterable_variants(value: Any) -> list[tuple[str, Any]]:
    """Bounded retypings of one argument.

    Bounded because the argument may be infinite: `more_itertools` ships `count`, `repeat`, `cycle`, and
    materializing one of those in a variant killed the whole run (exit -9, OOM). Sixty-four elements is
    far past every threshold a correctness question turns on, and an argument that does not fit is left
    alone rather than guessed at.
    """
    from itertools import islice

    # A string is a container of characters, not a container: retyping it as an iterator of characters
    # is not the same value in a different container, and `substrings_indexes(str, indexes)` duly raised
    # `TypeError` on all three variants on the healthy tree. Only genuine collections are retyped.
    if isinstance(value, (str, bytes, bytearray, dict)):
        return []
    try:
        items = list(islice(iter(value), 65))
    except Exception:
        return []
    if len(items) > 64:
        return []
    out: list[tuple[str, Any]] = [("iterator", iter(items)), ("none_reversed", NoneReversed(items))]
    if isinstance(value, list):
        out.append(("stripped", StrippedList(items)))
    return out


def _outcome(thunk: Callable[[], Any]) -> tuple[str, Any]:
    """Return the observable outcome of a call: a value or an exception *type*.

    Comparing against "did it raise" alone is not a law: many suites call a function on an empty input
    precisely to assert that it raises, so every retyped variant raises too and the law fires on the
    healthy tree. Measured on more-itertools: `last([])` is tested for `ValueError`, and a raise-only
    form reported three violations on both the buggy and the fixed commit.
    """
    try:
        return ("ok", thunk())
    except Exception as exc:  # noqa: BLE001 - the type is the observable
        return ("raise", type(exc))


_COMPARABLE = (str, bytes, bytearray, int, float, complex, bool, type(None), tuple, list, dict, set, frozenset)


def _not_comparable(value: Any) -> bool:
    """True when a result cannot be compared across two calls.

    A generator is the case that matters: `distinct_permutations(list)` returns a live generator whose
    repr differs every call, so identity-based equality reports a violation on the healthy tree. A lazy
    result is "the same answer" when both calls are lazy — its contents were never evaluated.
    """
    if isinstance(value, _COMPARABLE) and not isinstance(value, (tuple, list)):
        return False
    if isinstance(value, (tuple, list)):
        # A result is only as comparable as its leaves: `spy()` returns a tuple holding a live `_tee`,
        # which never compares equal, and that was reported as a violation on the healthy tree.
        return any(_not_comparable(item) for item in value)
    return True


def check_iterable_retyping(name: str, fn: Callable[..., Any], args: Sequence[Any]) -> list[Violation]:
    """The same elements in a different iterable must give the same answer.

    A generator is a list; a list with `__reversed__` set to None is still a sequence of the same
    items. A function that depends on the *container* rather than the *contents* has smuggled a
    protocol it never declared — `last(seq)` falling over when `__reversed__` is None is exactly that.

    Differential, not absolute: the baseline call on the suite's own argument is the reference, so a
    function that is *supposed* to raise on this input stays silent.
    """
    if len(args) != 1:
        return []
    baseline = _outcome(lambda: fn(args[0]))
    out: list[Violation] = []
    for label, variant in _iterable_variants(args[0]):
        got = _outcome(lambda: fn(variant))
        if got[0] == baseline[0] == "raise":
            if got[1] is baseline[1]:
                continue
        elif got[0] == baseline[0] == "ok":
            if _not_comparable(got[1]) or _not_comparable(baseline[1]) or safe_equal(got[1], baseline[1]):
                continue
        if got[0] == "raise":
            detail = f"{label} form raised {got[1].__name__}: {_exc_text(label, fn, variant)}"
        else:
            detail = f"{label} form returned {got[1]!r} where {args[0]!r} returned {baseline[1]!r}"
        out.append(Violation("iterable_retyping", name, detail))
    return out


def _exc_text(label: str, fn: Callable[..., Any], variant: Any) -> str:
    try:
        fn(variant)
    except Exception as exc:  # noqa: BLE001
        return str(exc)
    return ""


def static_assert_validation(source: str, module_name: str = "") -> list[Violation]:
    """A public function must not validate its arguments with `assert`.

    `assert` is not validation in a library: under `python -O` it is not code. Measured need: pluggy's
    `unregister()` checked "one of name or plugin" and "plugin is not registered" with `assert`, so
    `pm.unregister()` returned `None` under `-O` instead of raising. That defect is invisible to every
    runtime law — the suite never runs with `-O`, and the assertion is silent when it *passes*.

    The rule is narrow on purpose: an `assert` that mentions a parameter of a public function. An
    internal invariant about a local is left alone.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        params = {a.arg for a in list(node.args.args) + list(node.args.kwonlyargs) + list(node.args.posonlyargs)}
        if not params:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Assert):
                continue
            mentioned = {
                sub.id for sub in ast.walk(inner.test) if isinstance(sub, ast.Name)
            } & params
            if mentioned:
                out.append(Violation(
                    "assert_validation",
                    f"{node.name} (line {inner.lineno})",
                    f"argument validation by assert on {sorted(mentioned)} disappears under python -O",
                    module=module_name,
                ))
    return out


def mutations_for(args: Sequence[Any], *, budget: int = 4) -> list[tuple[int, str, Any]]:
    """Boundary re-typings of an argument, used to test error discipline and total-ness."""
    out: list[tuple[int, str, Any]] = []
    for idx, value in enumerate(args):
        if len(out) >= budget:
            break
        if isinstance(value, str):
            out.append((idx, "int", 7))
        elif isinstance(value, bool):
            out.append((idx, "str", "yes"))
        elif isinstance(value, (int, float)):
            out.append((idx, "str", "not-a-number"))
        elif isinstance(value, (list, tuple)):
            out.append((idx, "none", None))
        elif isinstance(value, Mapping):
            out.append((idx, "list", []))
        elif value is None:
            out.append((idx, "str", "none"))
    return out

def _document_variants(text: str) -> list[tuple[str, str]]:
    """Mutate the claims of a dot-separated base64url document (`header.payload.signature`).

    The content of a token is attacker-controlled, so a parser's contract is that content it cannot
    interpret is answered with the package's own error. The mutation is the smallest one that changes a
    *value* while leaving the document well-formed: one claim at a time replaced with a wrong-typed value.
    """
    import base64
    import json

    parts = text.split(".")
    if len(parts) != 3:
        return []
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return []
    if not isinstance(claims, dict) or not claims:
        return []
    out: list[tuple[str, str]] = []
    for key, _ in claims.items():
        for value in ([1], None):
            mutated = dict(claims)
            mutated[key] = value
            body = base64.urlsafe_b64encode(json.dumps(mutated).encode()).rstrip(b"=").decode()
            out.append((f"{key}={value!r}", ".".join([parts[0], body, parts[2]])))
    return out[:12]


def _escape_site(exc: BaseException, package: str) -> str:
    """The innermost frame of the package in which a leaked exception was raised."""
    import os
    import traceback

    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return ""
    if not package:
        # No package hint (a law run outside a known tree): the innermost frame is still the site.
        frame = frames[-1]
        return f"{frame.name} ({os.path.basename(frame.filename)}:{frame.lineno})"
    best = ""
    for frame in frames:
        if f"{os.sep}{package}{os.sep}" in frame.filename:
            best = f"{frame.name} ({os.path.basename(frame.filename)}:{frame.lineno})"
    return best


def check_document_retyping(
    name: str,
    fn: Callable[..., Any],
    args: Sequence[Any],
    error_classes: Sequence[type],
    package: str = "",
) -> list[Violation]:
    """A wrong-typed value inside a document must not leak a builtin exception out of the parser.

    Measured need: `pyjwt` decoded `{"exp": [1]}` and `int([1])` raised `TypeError`, which the handler —
    `except ValueError` — did not catch, so `jwt.decode()` leaked `TypeError` for an attacker-controlled
    claim while every other malformed claim raised `DecodeError`. Applications catching `PyJWTError` (the
    documented contract) crashed. The witness is a *value inside the argument*, which is why every law
    that mutates the arguments themselves (V17's `error_discipline`) could not name this site.
    """
    if not args or not isinstance(args[0], str):
        return []
    out: list[Violation] = []
    for label, document in _document_variants(args[0]):
        new_args = (document,) + tuple(args[1:])
        try:
            fn(*new_args)
        except Exception as exc:  # noqa: BLE001 - the family is the observable
            if error_classes and isinstance(exc, tuple(error_classes)):
                continue
            out.append(Violation(
                "document_retyping",
                name,
                f"{label} raised {type(exc).__name__} at {_escape_site(exc, package) or 'unknown site'}: {exc}",
            ))
    return out

def check_content_retyping(
    name: str,
    recall: Callable[[Any], Any],
    encode: Callable[[Any], Any],
    result: Any,
    error_classes: Sequence[type],
    package: str = "",
) -> list[Violation]:
    """Values *inside* a parsed document are attacker-controlled too — including after re-encoding.

    Mutating the serialized text is not enough for a signed document: changing the payload invalidates the
    signature, so the parser rejects it before it ever reads the claim (`InvalidSignatureError`, measured).
    The parser's own inverse — `encode` next to `decode` — puts the mutation back into a *valid* document,
    which is the only form in which the defect is reachable.

    The two callables are supplied by the caller, not derived here: the parser's keyword arguments
    (`algorithms=["HS256"]`) are part of the call, and slicing the positional arguments alone dropped them,
    so the re-invocation raised "algorithms required" — a member of the package family — and the law saw
    nothing. A closure over the *whole* call is the only faithful replay.
    """
    from collections.abc import Mapping

    if not isinstance(result, Mapping):
        return []
    out: list[Violation] = []
    for claim in list(result)[:6]:
        # `inf` is the value that separates the families: `int(float("inf"))` raises `OverflowError`, not
        # `TypeError`. Measured on pyjwt: broadening to `(ValueError, TypeError)` cleared 9 of the 12 hidden
        # cases and still failed the three `inf` ones, because no mutation had ever produced `OverflowError`.
        for value in ([1], None, float("inf")):
            mutated = dict(result)
            mutated[claim] = value
            try:
                document = encode(mutated)
            except Exception:
                continue
            if not isinstance(document, (str, bytes)):
                continue
            try:
                recall(document)
            except Exception as exc:  # noqa: BLE001 - the family is the observable
                if error_classes and isinstance(exc, tuple(error_classes)):
                    continue
                out.append(Violation(
                    "content_retyping",
                    name,
                    f"{claim}={value!r} raised {type(exc).__name__} at "
                    f"{_escape_site(exc, package) or 'unknown site'}: {exc}",
                ))
    return out
