"""A compiled callable cannot be read, but it can be asked.

THE WALL, AND WHAT IS ON THE OTHER SIDE OF IT.

§A148b measured it precisely: a source census cannot see compiled code, and most of the room that
matters for ordinary file work is compiled. Of six standard-library modules,

    json     5 python functions defined in source
    base64  27
    tarfile  9
    zipfile 15
    csv      0        <- csv.reader and csv.writer are builtins imported from _csv
    ...

The stdlib `csv` module defines **no python function at all**. `csv.reader` has no AST node, no
signature, and no docstring in any file the census opens.

But it is not silent. Asked directly, it answers:

    csv.reader.__module__  ->  '_csv'
    csv.reader.__doc__     ->  'csv_reader = reader(iterable [, dialect=\\'excel\\']\\n ...'
    inspect.signature(...) ->  ValueError  (unavailable for builtins)

The docstring carries a **usage line** -- the same artefact `cli_contract_inference` already reads off
a program's `--help`. `csv_reader = reader(iterable [, dialect='excel'] ... )` states the name, the
inputs, and which of them are optional. That is the contract, printed by the thing that has it.

WHY THIS IS NOT "TRUSTING THE DOCSTRING".

`room_census_v1`'s rule is that a census never admits anything: finding a callable is a hypothesis, and
only running it makes it a capability. This module keeps that rule exactly. It produces the SAME
candidate rows `room_census_v1` produces, from a different source, and they go to the same
`forge_and_record` that runs the function twice and tries to corrupt it. The docstring is a way to
NOTICE a callable, never a reason to believe one.

WHAT IT DOES NOT DO.

  * It does not import the target blindly: the caller names a module that is already importable, and
    importing is the only way to ask a compiled object anything at all.
  * It does not admit, score, or execute anything the census would not have.
  * It does not claim the docstring is true. `csv.reader`'s usage line is a claim; whether the call
    works is settled by running it.
"""
from __future__ import annotations

import importlib
import inspect
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVE_OBJECT_CENSUS_V1"

# From a usage line: the first identifier is the callable, the parenthesised part is the contract.
_USAGE = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*=\s*([A-Za-z_][\w.]*)\s*\((.*)$", re.S)
# '[optional]' vs required, as the docs themselves write it
_OPTIONAL = re.compile(r"\[(.*?)\]", re.S)
_TOKEN = re.compile(r"[A-Za-z_][\w]*")


def _first_line(doc: str) -> str:
    """The usage line, spanning wrapped lines but stopping at the balanced close.

    A compiled callable's docstring usually opens with its own usage, wrapped:
        csv_writer = csv.writer(fileobj [, dialect='excel']
                                [optional keyword args])
        for row in sequence: ...
    The call ends at the parenthesis that balances the first `(`; everything after it is prose about
    the call, not part of it. Scanning to the first newline cut the contract in half, and scanning to
    the last parenthesis swallowed the following example and turned its words into parameters.
    """
    text = (doc or "").strip()
    if not text or "(" not in text:
        return text.split("\n")[0].strip()
    # a usage line BEGINS with the call; prose begins with words and merely contains a parenthesis
    if not _USAGE.match(_strip_display_names(text.split("\n")[0])):
        return ""
    head, rest = text.split("(", 1)
    depth, buf = 1, []
    for ch in rest:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                buf.append(ch)
                return (head + "(" + "".join(buf)).strip()
        buf.append(ch)
    return text.split("\n")[0].strip()


def _strip_display_names(text: str) -> str:
    """`csv.writer(...)` is how the docs SHOW the call; `writer(...)` is what you write."""
    return re.sub(r"\bcsv\.(?=[A-Za-z_])", "", text)


def _params_from_usage(usage: str) -> tuple[list[str], list[str]]:
    """Required and optional parameter names, as the usage line spells them."""
    # ONLY A USAGE LINE HAS A CONTRACT IN IT. Prose that happens to contain parentheses does not.
    # Measured 2026-11-23: `json.dump`'s PROSE -- "Serialize ``obj`` as a JSON formatted stream to
    # ``fp`` (a ``.write()``-supporting file-like object)" -- was being parsed as a usage line and
    # produced `obj, fp, skipkeys, ...` from the wrong sentence entirely. It looked right, which is
    # worse than looking wrong: the signature path was being silently duplicated by an accident.
    # A real usage line starts with an identifier and an `=`, or is the identifier and `(`.
    candidate = _strip_display_names(usage or "").strip()
    m = _USAGE.match(candidate)
    if not m and re.match(r"^[A-Za-z_][\w]*\s*\(", candidate):
        # `reader(iterable [, dialect=...])` -- bare-name form, still a usage line
        head, rest = candidate.split("(", 1)
        m = _USAGE.match(head.strip() + " = " + head.strip() + "(" + rest)
    if not m:
        return [], []
    inside = m.group(3) or ""
    # THE BRACKETS ARE THE DOCUMENTATION'S WAY OF SAYING "OPTIONAL", AND THEY ARE ALSO NOISE.
    # `[optional keyword args]` is a note, not four parameters. What is inside brackets is optional;
    # what is outside is required. Remove the entire bracketed span from the required side, and take
    # only identifier-shaped names from the optional side -- never the words "optional"/"keyword".
    optional_text = " ".join(_OPTIONAL.findall(inside))
    required_text = _OPTIONAL.sub(" ", inside)
    def names(text):
        out = []
        for tok in _TOKEN.findall(text):
            low = tok.lower()
            if low in ("dialect", "excel", "delimiter", "fmtparams", "none", "true", "false",
                       "optional", "keyword", "args", "and"):
                continue
            if tok not in out:
                out.append(tok)
        return out
    return names(required_text), names(optional_text)


def _summary(doc: str, usage: str) -> str:
    """What the callable says it is for, in its own words.

    TWO KINDS OF DOCSTRING, AND THEY MUST NOT BE CONFUSED.

    A compiled callable opens with a USAGE LINE (`csv_writer = csv.writer(fileobj [, dialect=...])`)
    and the prose, if any, follows it. A python callable opens with PROSE (`Serialize obj as a JSON
    formatted stream to fp`). Subtracting a usage line that is not there mangled the second kind:
    `json.dump` described itself as "dump ." because the first line was stripped as if it were a
    header. Detect which kind this is before deciding what to remove.
    """
    text = (doc or "").strip()
    if not text:
        return ""
    looks_like_usage = bool(usage) and "(" in usage and _USAGE.match(_strip_display_names(usage))
    rest = text.replace(usage, "", 1).strip() if looks_like_usage else text
    rest = re.split(r"\n\s*\n", rest, maxsplit=1)[0]
    rest = rest.replace("``", "").replace("`", "")
    return " ".join(rest.split())[:300]


def census_module(module_name: str, public_only: bool = True,
                  limit: int = 400) -> dict:
    """Ask a live module what it can do, and describe each callable as it describes itself.

    Deterministic order (sorted by name) so two runs of the same environment agree.
    """
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return {"schema": SCHEMA, "module": module_name, "status": "NOT_IMPORTABLE",
                "reason": type(exc).__name__, "functions": [], "note": str(exc)[:200]}
    rows = []
    for name in sorted(dir(module)):
        if public_only and name.startswith("_"):
            continue
        try:
            value = getattr(module, name)
        except Exception:
            continue
        # A CLASS IS A TEMPLATE, NOT A CALLABLE A PERSON ASKS FOR BY NAME. Offering a constructor as
        # a thing to invoke puts it in the same list as functions, and DictReader(path) does not read
        # a csv -- it needs a file OBJECT. Functions and methods only.
        if inspect.isclass(value) or not callable(value):
            continue
        doc = inspect.getdoc(value) or ""
        usage = _first_line(doc)
        required, optional = _params_from_usage(usage)
        params = required + optional
        # A REAL SIGNATURE BEATS A PARSED DOCSTRING, WHEN THERE IS ONE.
        # Every pure-python callable reports `inspect.signature` exactly; only compiled ones do not.
        # Reading the signature where it exists and falling back to the usage line where it does not
        # means the same census answers correctly across both kinds of callable, which is the point
        # of crossing the wall rather than building a second pipeline for the other side.
        sig = ""
        sig_required: list[str] = []
        sig_optional: list[str] = []
        try:
            _s = inspect.signature(value)
            sig = str(_s)
            for pname, parm in _s.parameters.items():
                if pname in ("self", "cls"):
                    continue
                if parm.kind in (parm.VAR_POSITIONAL, parm.VAR_KEYWORD):
                    continue
                if parm.default is inspect.Parameter.empty:
                    sig_required.append(pname)
                else:
                    sig_optional.append(pname)
        except Exception:
            sig = ""
        # ONE PATH OR THE OTHER, NEVER A BLEND.
        # A real signature is the contract; the docstring's usage line is the fallback. Merging them
        # -- which the first version did, appending signature names to the docstring's lists before
        # deciding which to believe -- meant the fallback was never actually exercised and a mutant
        # deleting the signature path changed nothing. A guard that cannot be observed is decoration.
        if sig_required or sig_optional:
            required, optional = sig_required, sig_optional
            params = sig_required + sig_optional
        else:
            params = required + optional
        # WHERE THE TRUTH CAME FROM MATTERS. A compiled callable was read from its own docstring;
        # a python one could have been read from source, and the source census does that better.
        origin = getattr(value, "__module__", "") or ""
        rows.append({
            "function": name,
            "call": name,
            "owner": "",
            "origin": origin,
            "is_compiled": not inspect.isfunction(value) and not inspect.isclass(value),
            "doc": _summary(doc, usage),
            "usage": usage[:300],
            "signature": sig[:200],
            "params": params,
            "required": required,
            "optional": optional,
            "text": " ".join(x for x in (name.replace("_", " "), _summary(doc, usage)) if x)[:600],
        })
        if len(rows) >= limit:
            break
    return {
        "schema": SCHEMA,
        "module": module_name,
        "status": "ASKED",
        "functions": rows,
        "compiled": sum(1 for r in rows if r["is_compiled"]),
        "note": ("Read by asking the live objects, not by reading source. A callable found here is "
                 "still a CANDIDATE: only `forge_and_record`, which runs it twice and tries to "
                 "corrupt it, can make it a capability."),
    }


def bridge_to_room(module_name: str, **kwargs) -> dict:
    """A live census in the shape `room_census_v1` produces, so the same tools can consume it.

    This is the whole point of the module: the rest of the pipeline should not care whether a
    callable was found in a file or asked of a running object. Same rows, same ranking, same forge,
    same verification.
    """
    asked = census_module(module_name, **kwargs)
    return {
        "schema": "PROJECT_BRAIN_ROOM_CENSUS_V1",
        "root": "<live:%s>" % module_name,
        "status": "SURVEYED" if asked["status"] == "ASKED" else asked["status"],
        "functions": asked["functions"],
        "files_read": 0,
        "asked_live": True,
        "compiled": asked.get("compiled", 0),
        "note": asked.get("note"),
    }
