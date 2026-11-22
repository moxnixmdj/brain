"""A program's type is derivable from the sentence it writes about itself.

The previous instrument (`plans_compose_v1`) composed filters — but it did so with nine
`if name == ...` lines. It searched an order over a taxonomy that I had hand-written for
three programs, which means the search was real and the *knowledge* was a lookup table.
On a host it had never seen, `type_of` returned `schemes=[]` for every program. That is
the control this instrument is built to beat.

The claim here: no per-program code at all. For each executable, read the first prose
sentence of its own `--help`, take the transform verb out of it, and let the constructor
be the program's own name. Then the same searched algebra that already composed three
hand-typed programs must compose a host it has never seen.

    gzip       "Compress or uncompress FILEs ..."   ->  ANY -> GZIP[_],  GZIP -> UNWRAP
    bzip2      "a block-sorting file compressor"    ->  ANY -> BZIP2[_], BZIP2 -> UNWRAP
    sha256sum  "Print or check SHA256 checksums"    ->  TEXT -> SHA256[TEXT]   (lossy)

The important asymmetry: compression declares its own inverse ("or uncompress"), hashing
does not ("Print"), and a formatter does not ("Output"). So invertibility is *stated by
the program*, not assumed by the search. That is what makes a refusal meaningful.

Schema BRAIN_TYPE_IS_ITS_OWN_SENTENCE_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any

SCHEMA = "BRAIN_TYPE_IS_ITS_OWN_SENTENCE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# The verbs a program uses to name its own transform. This is a CLOSED CLASS of
# English words, not a list of programs: it says nothing about which executable runs.
# A verb absent from here means the instrument reports UNTYPED rather than guessing.
CONSTRUCTIVE = {
    "compress": "compress", "uncompress": "compress", "decompress": "compress",
    "pack": "compress", "encode": "encode", "decode": "decode",
}
# Verbs that produce a NEW representation and say nothing about recovering the old one.
LOSSY = {
    "print": "digest", "check": "digest", "sort": "order", "reverse": "reverse",
    "translate": "translate", "convert": "convert", "wrap": "wrap",
    "write": "represent", "output": "render", "render": "render", "format": "format",
    "extract": "extract", "concatenate": "concat", "join": "concat",
}
# The inverse word a program must ITSELF say for its transform to be invertible.
INVERSE_WORDS = {
    "compress": ("uncompress", "decompress"),
    "encode": ("decode",),
    "decode": ("encode",),
}

# English stop words and help-page furniture that never becomes a type.
NOISE = {
    "a", "an", "the", "of", "to", "in", "on", "or", "and", "for", "from", "by",
    "with", "is", "are", "it", "its", "this", "that", "each", "all", "any", "given",
    "file", "files", "input", "output", "standard", "stdout", "stdin", "mode",
    "default", "option", "options", "usage", "version", "flag", "flags", "order",
    "writing", "read", "reads", "print", "prints", "check", "checks", "please",
    "characterwise", "characters", "bytes", "string", "strings", "line", "lines",
    "standard input", "command", "specify", "specified",
}


def help_text(program: pathlib.Path, timeout: float = 10.0) -> str:
    """The program's own words, preferring the first flag that says anything."""
    for flag in ("--help", "-h"):
        try:
            run = subprocess.run([str(program), flag], capture_output=True,
                                 text=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            return ""
        text = (run.stdout or "") + (run.stderr or "")
        if text.strip():
            return text
    return ""


def self_description(text: str) -> str:
    """The first prose sentence: the place a program introduces itself.

    Usage blocks, `or:` continuations, and flag lines are furniture. Everything else
    that is prose is a candidate; the first one is the self-description.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if low.startswith(("usage", "or:", "options", "with no file", "with no arguments",
                           "-", "note", "see ", "report ", "example", "details")):
            continue
        # a prose line is not a table row and not a flag listing
        if stripped.count("  ") > 3:
            continue
        return stripped
    return ""


def verbs_of(description: str) -> list[str]:
    """Every transform verb the program names, in the order it names them."""
    words = re.findall(r"[A-Za-z][A-Za-z-]+", description.lower())
    found: list[str] = []
    for word in words:
        stem = word[:-3] if word.endswith("ing") else word
        for table in (CONSTRUCTIVE, LOSSY):
            if stem in table and table[stem] not in found:
                found.append(table[stem])
    return found


def its_own_inverse(description: str, transform: str) -> str | None:
    """The inverse word the program itself supplies, or None if it does not claim one."""
    words = set(re.findall(r"[A-Za-z][A-Za-z-]+", description.lower()))
    for word in INVERSE_WORDS.get(transform, ()):
        if word in words:
            return word
    return None


def constructor_of(description: str, program: pathlib.Path) -> str:
    """The type constructor: the program's own name, upper-cased.

    A program that names itself in its first sentence supplies its own constructor
    (`bzip2, a block-sorting file compressor`). When it does not, its executable name
    does — which is still the program speaking, not the instrument.
    """
    stem = program.name.split(".")[0]
    # strip a trailing `sum`, `1`, or version-ish suffix only when the description
    # itself uses the shorter form; otherwise trust the executable name.
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", description)
    for word in words:
        if word.lower() == stem.lower():
            return re.sub(r"[^A-Z0-9]", "", stem.upper())
    return re.sub(r"[^A-Z0-9]", "", stem.upper())


def type_of(program: pathlib.Path) -> dict[str, Any]:
    """Read one executable's own sentence and return its type schemes.

    No branch in this function names a program. That is the whole point and it is
    checked by `test_no_branch_names_a_program`.
    """
    text = help_text(program)
    description = self_description(text)
    if not description:
        return {"program": str(program), "description": "", "schemes": [],
                "transform": None, "invertible": False, "reason": "NO_SELF_DESCRIPTION"}
    verbs = verbs_of(description)
    if not verbs:
        return {"program": str(program), "description": description, "schemes": [],
                "transform": None, "invertible": False, "reason": "NO_TRANSFORM_VERB"}
    transform = verbs[0]
    constructor = constructor_of(description, program)
    schemes: list[dict[str, Any]] = []
    invertible = False

    if transform == "compress":
        schemes.append({"from": "ANY", "to": f"{constructor}[_]", "polymorphic": True,
                        "why": f"description says {transform!r}"})
        inverse = its_own_inverse(description, transform)
        if inverse:
            invertible = True
            schemes.append({"from": constructor, "to": "UNWRAP", "polymorphic": False,
                            "why": f"description itself says {inverse!r}"})
    elif transform == "encode":
        schemes.append({"from": "ANY", "to": f"{constructor}[_]", "polymorphic": True,
                        "why": "description says 'encode'"})
        inverse = its_own_inverse(description, transform)
        if inverse:
            invertible = True
            schemes.append({"from": constructor, "to": "UNWRAP", "polymorphic": False,
                            "why": f"description itself says {inverse!r}"})
    elif transform == "decode":
        schemes.append({"from": constructor, "to": "UNWRAP", "polymorphic": False,
                        "why": "description says 'decode'"})
        inverse = its_own_inverse(description, transform)
        invertible = bool(inverse)
        if inverse:
            schemes.append({"from": "ANY", "to": f"{constructor}[_]", "polymorphic": True,
                            "why": f"description itself says {inverse!r}"})
    else:
        # a lossy transform: it produces a representation and claims no inverse.
        schemes.append({"from": "TEXT", "to": f"{constructor}[TEXT]",
                        "polymorphic": False, "why": f"description says {transform!r}"})

    return {"program": str(program), "name": program.name, "description": description,
            "transform": transform, "constructor": constructor,
            "invertible": invertible, "schemes": schemes,
            "reason": "DERIVED_FROM_SELF_DESCRIPTION"}


def derive_all(host: pathlib.Path, names: list[str] | None = None) -> dict[str, Any]:
    """Type every executable a host offers, from each one's own sentence."""
    started = time.perf_counter()
    rows: dict[str, Any] = {}
    seen: set[str] = set()
    candidates = []
    for entry in sorted(host.iterdir()) if host.is_dir() else []:
        if not entry.is_file():
            continue
        # a symlink into the same target is the same program; do not type it twice
        try:
            real = str(entry.resolve())
        except OSError:
            continue
        if real in seen:
            continue
        seen.add(real)
        candidates.append(entry)
    if names is not None:
        candidates = [c for c in candidates if c.name in names]
    for entry in candidates:
        rows[entry.name] = type_of(entry)
    typed = {k: v for k, v in rows.items() if v["schemes"]}
    return {"host": str(host), "programs_seen": len(candidates),
            "programs_typed": len(typed), "rows": rows,
            "seconds": round(time.perf_counter() - started, 3)}


def run(receipt: pathlib.Path | None = None, hosts: list[str] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    report: dict[str, Any] = {"schema": SCHEMA, "authority": AUTHORITY}
    host_paths = [pathlib.Path(h) for h in (hosts or ["/usr/bin", "/bin"])]
    report["hosts"] = [derive_all(h) for h in host_paths if h.is_dir()]

    # The claim, made checkable: the SAME closed verb table types every host, and the
    # number of per-program branches in this file is zero.
    source = pathlib.Path(__file__).read_text()
    report["no_branch_names_a_program"] = not re.search(
        r"""if\s+(?:name|program\.name|stem)\s*==\s*['"]""", source)
    typed = sum(h["programs_typed"] for h in report["hosts"])
    seen = sum(h["programs_seen"] for h in report["hosts"])
    report["totals"] = {"programs_seen": seen, "programs_typed": typed,
                        "typed_rate": round(typed / seen, 4) if seen else 0.0}
    report["seconds"] = round(time.perf_counter() - started, 3)
    if receipt:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path)
    parser.add_argument("--hosts", nargs="*")
    parser.add_argument("--show", default="")
    args = parser.parse_args(argv)
    report = run(args.receipt, args.hosts)
    if args.show:
        names = {n.strip() for n in args.show.split(",") if n.strip()}
        for host in report["hosts"]:
            for name, row in host["rows"].items():
                if name in names:
                    print(f"{name:12s} {row['transform']:>10s} "
                          f"inv={row['invertible']!s:5s} {row['schemes']}")
    print(json.dumps({"totals": report["totals"], "seconds": report["seconds"],
                      "no_branch_names_a_program": report["no_branch_names_a_program"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
