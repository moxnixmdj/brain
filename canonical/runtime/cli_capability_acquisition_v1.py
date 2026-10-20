#!/usr/bin/env python3
"""Close the loop on learning a program: infer it, then prove it works.

cli_contract_inference returns CANDIDATE_REQUIRES_EFFECT_VERIFICATION. That is
the honest status for something nobody has run. The codec acquisition path in
this repository does close its loop -- it probes the real thing in a fresh
subprocess and requires observed["ok"] is True before trusting the contract.
The CLI path never did, so an inferred contract was a guess with good manners.

This runs it. Infer, substitute real inputs, execute, and check the EFFECT:

  - the output file exists and is non-empty
  - its leading bytes match the magic the contract claims (output_prefix_hex)
  - or, for a text format, it decodes as UTF-8

Only then is the contract bankable. A program whose help text advertises PNG
and emits a zero-byte file is not learned; it is believed.

When the first attempt fails it does not stop at one try. Help text lists
several output flags; each is a hypothesis about how to drive the program, and
the way to choose between hypotheses is to run them. That is not a fixed
sequence -- it is the machine testing its own guesses against reality, which is
the only thing that separates learning from pattern matching.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import tempfile

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CLI_CAPABILITY_ACQUIRED_V1"

PASS = "PASS__CLI_CAPABILITY_ACQUIRED"
NO_CONTRACT = "OPEN__CLI_CAPABILITY_NO_CONTRACT"
NOT_VERIFIED = "OPEN__CLI_CAPABILITY_EFFECT_NOT_VERIFIED"
UNRUNNABLE = "OPEN__CLI_CAPABILITY_NOT_RUNNABLE"

_PLACEHOLDER = re.compile(r"\$\{input\.([A-Za-z0-9_.]+)\}")

# plausible values for the inputs a contract declares
_SAMPLES: dict[str, Any] = {
    "text": "brain-acquisition-probe-1234",
    "data": "brain-acquisition-probe-1234",
    "input": "brain-acquisition-probe-1234",
    "output_path": None,   # filled per attempt
    "output": None,
}

_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".csv", ".tsv", ".json",
                  ".html", ".htm", ".xml"}


def _candidate_output_flags(help_text: str) -> list[str]:
    """Every flag the program's own help suggests for naming an output.

    The first one that works is the answer; the rest are hypotheses the machine
    is entitled to hold until it has run them.
    """
    flags: list[str] = []
    for m in re.finditer(r"(-{1,2}[A-Za-z0-9][\w-]*)\s*(?:[= ]\s*)?(FILE|OUTPUT|OUTFILE|PATH|TARGET)?",
                         help_text):
        flag = m.group(1)
        kind = (m.group(2) or "").upper()
        line_start = help_text.rfind("\n", 0, m.start()) + 1
        line_end = help_text.find("\n", m.end())
        line = help_text[line_start: line_end if line_end > 0 else len(help_text)]
        if not re.search(r"output|write|save|out\s*file|\bto\b", line, re.I):
            continue
        if kind or re.search(r"output|outfile", line, re.I):
            if flag not in flags:
                flags.append(flag)
    return flags


def _substitute(template: list[str], values: Mapping[str, Any]) -> list[str]:
    out = []
    for tok in template:
        def repl(m: re.Match[str]) -> str:
            return str(values.get(m.group(1), ""))
        out.append(_PLACEHOLDER.sub(repl, str(tok)))
    return out


def _verify(path: pathlib.Path, contract: Mapping[str, Any]) -> tuple[bool, str]:
    """Did the program actually produce what the contract claims?"""
    if not path.exists():
        return False, "OUTPUT_MISSING"
    raw = path.read_bytes()
    if not raw:
        return False, "OUTPUT_EMPTY"
    magic = contract.get("output_prefix_hex")
    if magic:
        try:
            want = bytes.fromhex(str(magic))
        except ValueError:
            return False, "MAGIC_UNPARSEABLE"
        if not raw.startswith(want):
            return False, "MAGIC_MISMATCH"
        return True, ""
    if contract.get("output_text_utf8") or path.suffix.lower() in _TEXT_SUFFIXES:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return False, "TEXT_NOT_UTF8"
        return True, ""
    return False, "NO_VERIFIABLE_OUTPUT_SPEC"


def acquire(probe: Mapping[str, Any], goal: str, *,
            extra_output_flags: list[str] | None = None,
            timeout_s: float | None = None,
            sample_text: str = "brain-acquisition-probe-1234") -> dict[str, Any]:
    """Infer how to use this program, then prove it by running it."""
    from canonical.runtime import cli_contract_inference as ci

    try:
        contract = ci.infer_contract(probe, goal)
        route = "help_text"
    except ci.ContractInferenceFailure as exc:
        # Reading its help failed. That is not the same as the program being
        # unlearnable -- it is sitting right there and can be run. Fall back to
        # driving it and watching what happens, which needs no documentation.
        contract = None
        route = "empirical"
        infer_error = str(exc)

    if contract is None:
        # A goal that never says what it wants produced gives us nothing to
        # check an effect against, so any program that prints anything would
        # "work" -- ls would be learned as a capability. That is the same
        # failure mode the help path already refuses as
        # CLI_OUTPUT_FORMAT_UNVERIFIABLE, and it is refused here too.
        want_suffix = _requested_suffix(goal)
        if not want_suffix:
            out = {"schema": SCHEMA, "status": NO_CONTRACT,
                   "reason": "NO_OUTPUT_FORMAT_IN_GOAL_CANNOT_VERIFY_EFFECT",
                   "verified": False, "attempts": [], "tried_empirically": False}
            _note_gaps(out, goal)
            return out
        try:
            from canonical.runtime import empirical_cli_probe_v1 as emp
            exe_guess = ""
            for e in (probe.get("executables") or []):
                exe_guess = str(e.get("executable") or "")
                if exe_guess:
                    break
            observed = emp.probe(exe_guess, goal, suffix=want_suffix)
        except Exception:
            observed = None
        if observed is None or observed.get("status") != emp.PASS:
            out = {"schema": SCHEMA, "status": NO_CONTRACT,
                   "reason": infer_error, "verified": False, "attempts": [],
                   "tried_empirically": True}
            _note_gaps(out, goal)
            return out
        return {**observed, "schema": SCHEMA, "status": PASS,
                "verified": True, "route": route,
                "evidence": {**(observed.get("evidence") or {}),
                             "authority": observed.get("authority"),
                             "inferred_from": "observed_effect_no_help_text",
                             "attempts": []}}

    exe = str(contract.get("executable") or "")
    if not shutil.which(exe) and not pathlib.Path(exe).is_file():
        return {"schema": SCHEMA, "status": UNRUNNABLE,
                "reason": "EXECUTABLE_NOT_FOUND:" + exe,
                "contract": contract, "verified": False, "attempts": []}

    help_text = ""
    for e in (probe.get("executables") or []):
        for att in (e.get("help_attempts") or []):
            help_text += str(att.get("text") or "")

    attempts: list[dict[str, Any]] = []
    flags = list(extra_output_flags or [])
    for f in _candidate_output_flags(help_text):
        if f not in flags:
            flags.append(f)
    if not flags:
        flags = [None]   # run the template exactly as inferred

    for flag in flags:
        with tempfile.TemporaryDirectory(prefix="brain-cli-acq-") as td:
            out = pathlib.Path(td) / ("probe" + (contract.get("requested_suffix")
                                                 or ".out"))
            values = {"text": sample_text, "data": sample_text,
                      "input": sample_text,
                      "output_path": str(out), "output": str(out)}
            argv = _substitute(contract.get("argv_template") or [exe], values)
            # The contract carries the full path in "executable" but puts only
            # the BASENAME in argv -- which runs only if the program happens to
            # be on PATH. A program the machine just met is not on PATH; that
            # is the whole situation. Use the path we actually resolved.
            if argv and pathlib.Path(argv[0]).name == pathlib.Path(exe).name \
                    and argv[0] != exe:
                argv[0] = exe
            if flag is not None and flag not in argv:
                # swap in the alternative output flag before the output path
                try:
                    pos = argv.index(str(out))
                except ValueError:
                    continue
                argv = argv[:max(0, pos - 1)] + [flag, str(out)] + argv[pos + 1:]

            try:
                proc = subprocess.run(argv, capture_output=True,
                                      timeout=float(timeout_s
                                                    or contract.get("timeout_s")
                                                    or 60))
                code = proc.returncode
            except subprocess.TimeoutExpired:
                attempts.append({"argv": argv, "outcome": "TIMEOUT"})
                continue
            except OSError as exc:
                attempts.append({"argv": argv, "outcome": "OS_ERROR:" + type(exc).__name__})
                continue

            ok, why = _verify(out, contract)
            attempts.append({"argv": argv, "returncode": code,
                             "outcome": "VERIFIED" if ok else why})
            if ok:
                result = {
                    "schema": SCHEMA,
                    "status": PASS,
                    "verified": True,
                    "route": route,
                    "executable": exe,
                    "argv_template": contract.get("argv_template"),
                    "required_inputs": contract.get("required_inputs"),
                    "output_flag": flag,
                    "output_prefix_hex": contract.get("output_prefix_hex"),
                    "output_text_utf8": contract.get("output_text_utf8"),
                    "evidence": {
                        "returncode": code,
                        "output_bytes": out.stat().st_size,
                        "verified_against": ("magic"
                                             if contract.get("output_prefix_hex")
                                             else "text"),
                        "attempts": attempts,
                        # a probe file proves the program runs, not that it is
                        # correct for real work; it stays a candidate for that
                        "authority": "EFFECT_VERIFIED_NOT_SEMANTICALLY_PROVEN",
                    },
                }
                _remember(result, goal)
                return result

    failed = {"schema": SCHEMA, "status": NOT_VERIFIED, "verified": False,
              "executable": exe, "contract": contract, "attempts": attempts}
    _note_gaps(failed, goal)
    return failed


def _requested_suffix(goal: str) -> str:
    """The OUTPUT extension the goal asks for, so the effect can be checked.

    Taking the first extension in the sentence measures the INPUT. For
    "compress notes.txt into notes.txt.gz" that is .txt -- a file which
    already existed before anything was learned. Verifying against it
    declares success for producing a file that was there all along, and a
    gap gets closed by doing nothing. The output is the TARGET: what follows
    into/to/as, or failing that the last extension named.
    """
    text = str(goal or "")
    target = re.search(
        r"\b(?:into|to|as|named|called|output|produce|producing)\s+"
        r"[\"']?([^\s\"']+\.([A-Za-z0-9]{1,6}))\b", text, re.I)
    if target:
        return "." + target.group(2)
    # the other way round: "create notes.txt.tar containing notes.txt" makes
    # the output the thing being built and the input the thing named after
    source = re.search(r"\b(?:containing|from|using|with)\s+", text, re.I)
    if source:
        head = re.findall(r"(\.[A-Za-z0-9]{1,6})\b", text[:source.start()])
        if head:
            return head[-1]
    found = re.findall(r"(\.[A-Za-z0-9]{1,6})\b", text)
    return found[-1] if found else ""


def _remember(result: Mapping[str, Any], goal: str) -> None:
    """File what was learned where it can be found again, and record the gaps.

    Learning that is not remembered is not learning, it is a transaction. The
    two systems this feeds are the ones that decide what matters, so neither is
    allowed to break acquisition -- a memory failure must not cost a capability.
    """
    try:
        from canonical.runtime import associative_memory_v1 as mem
        mem.remember(
            f"{result.get('executable')} {' '.join(result.get('argv_template') or [])}",
            kind="acquired_capability",
            tags=["cli", str(result.get("executable") or "")],
        )
    except Exception:
        pass


def _note_gaps(result: Mapping[str, Any], goal: str) -> None:
    """A failure is the machine finding out what it does not know."""
    try:
        from canonical.runtime import ignorance_ledger_v1 as led
        for attempt in result.get("attempts") or []:
            outcome = str(attempt.get("outcome") or "")
            if outcome in ("VERIFIED", "TIMEOUT"):
                continue
            led.note(outcome or "UNKNOWN_ACQUISITION_FAILURE",
                     why=f"{result.get('executable')}: {goal}", cost=1.0)
    except Exception:
        pass


def to_registry_entry(acquired: Mapping[str, Any], capability_id: str) -> dict[str, Any] | None:
    """Shape a verified acquisition as a capability the machine can invoke."""
    if acquired.get("status") != PASS or not acquired.get("verified"):
        return None
    return {
        "id": capability_id,
        "adapter_module": "cli_command",
        "action_template": {
            "type": "invoke_capability",
            "args": {
                "capability_id": capability_id,
                "argv": acquired["argv_template"],
                "output_path": "${input.output_path}",
                "timeout_s": 60,
            },
            "expect": {"field": "output_verified", "type": "field_equals",
                       "value": True},
        },
        "acquisition": {
            "schema": SCHEMA,
            "authority": acquired["evidence"]["authority"],
            "output_prefix_hex": acquired.get("output_prefix_hex"),
        },
    }


def _dump_like(original: str, doc: Mapping[str, Any]) -> str:
    """Reserialize in the file's own style, so registering does not reformat it.

    Writing json.dumps(indent=1, sort_keys=True) into a registry that is kept at
    indent=2 rewrites every line of the source of truth to add one capability:
    5,666 insertions and 5,641 deletions for a single entry, which makes the
    change unreviewable and buries anything else that happened.
    """
    for kwargs in ({"indent": 2}, {"indent": 2, "sort_keys": True},
                   {"indent": 1, "sort_keys": True}, {"indent": 4}):
        try:
            out = json.dumps(doc, **kwargs)
        except (TypeError, ValueError):
            continue
        if out == original or out + "\n" == original:
            return out
    return json.dumps(doc, indent=2)


def register(acquired: Mapping[str, Any], capability_id: str, *,
             registry_path: str | None = None,
             overwrite: bool = False) -> dict[str, Any]:
    """Make a verified acquisition invocable -- the last mile of learning.

    Until it is in the registry, a learned capability is a souvenir: bankable,
    inspectable, and unreachable. Nothing can call it. Registering is what lets
    the machine actually use the thing it just taught itself.

    Refuses by default rather than overwrite. A capability that already exists
    was proven by whatever means it was proven; replacing it with something
    learned from one probe run -- which the evidence above explicitly labels
    EFFECT_VERIFIED_NOT_SEMANTICALLY_PROVEN -- would trade a known quantity for
    a plausible one. Growth must not be able to destroy what already worked.
    """
    from canonical.runtime import capability_type_surface_v1 as ts

    path = pathlib.Path(registry_path or ts.REGISTRY)
    entry = to_registry_entry(acquired, capability_id)
    if entry is None:
        return {"registered": False,
                "reason": "NOT_VERIFIED_ONLY_VERIFIED_ACQUISITIONS_ARE_REGISTERED"}

    try:
        original = path.read_text(encoding="utf-8")
        doc = json.loads(original)
    except (OSError, ValueError) as exc:
        return {"registered": False, "reason": "REGISTRY_UNREADABLE:" + type(exc).__name__}

    caps = doc.get("capabilities")
    if not isinstance(caps, dict):
        return {"registered": False, "reason": "REGISTRY_SHAPE_UNRECOGNISED"}

    if capability_id in caps and not overwrite:
        return {"registered": False, "reason": "CAPABILITY_ALREADY_EXISTS",
                "capability_id": capability_id}

    caps[capability_id] = entry
    # write atomically: a half-written registry is worse than an unchanged one
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(_dump_like(original, doc), encoding="utf-8")
    tmp.replace(path)
    return {"registered": True, "capability_id": capability_id,
            "count": len(caps)}
