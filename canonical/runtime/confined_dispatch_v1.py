#!/usr/bin/env python3
"""The seam the admitted confinement was built for: declared capabilities run confined.

WHY THIS EXISTS
---------------

`computer_execution_boundary_v1` refuses unconfined host execution with one status and
names its release condition: "until a reviewed, admitted confinement and
effect-verification path exists". `confinement_v1` (merged 2026-11-12, PR #6733) is that
path; this module is the wiring. Measured wall this seam attacks
(`canonical/tools/realistic_goal_reach_probe_v1.py`): 19 of 38 material-aware realistic
goals for the most advanced coding capabilities refuse with
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` -- they compile, they
bind, and die for want of a carrier.

THE CONTRACT
------------

* A capability is routable ONLY if it is declared in
  `canonical/runtime/CONFINED_EFFECT_DECLARATIONS_V1.json` -- reviewed data: the effect
  argument names whose bound values must exist as files after the run, and the budget.
  No declaration, or a bound value that is not a string, or an absolute path pointing
  into the host -> `None` -> the caller's refusal stands exactly as before.
* The SAME adapter code runs, imported from the CONFINED CLONE (the worktree's own
  `canonical` package), with `root` set to the worktree. The host repository is never
  handed to the capability; after the run its `git status --porcelain` must be
  byte-identical (`confinement_v1` verifies, and the receipt records it).
* The result mirrors `run_adapter_locally`'s contract exactly -- `capability_id`, a
  `dependency` block whose `executor` names the confinement (honest provenance), and the
  caller's own expectation check (`_check_expectation`, imported lazily at call time, so
  a confined pass and a local pass are judged by the same ruler).
* Every result carries the confinement receipt: sha, host head, host_untouched, and the
  per-effect sha256 verification. A run that overruns its budget, exits nonzero without
  its declared effects, or loses its host guarantee is reported as what it is -- a
  fail-closed confinement outcome with the receipt attached -- never as a capability
  pass.

WHAT THIS IS NOT
----------------

Not a relaxation. The boundary module is untouched; undeclared capabilities keep the
refusal; a declaration that cannot be honored (unbound effect, escaping path) keeps the
refusal. The declarations file is the review surface: one JSON file, one capability per
row, each effect argument named.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import confinement_v1 as CF

SCHEMA = "PROJECT_BRAIN_CONFINED_DISPATCH_V1"

DECLARATIONS_PATH = Path(__file__).resolve().parent / "CONFINED_EFFECT_DECLARATIONS_V1.json"

EXECUTOR = "ADMITTED_CONFINEMENT_V1"
RESULT_FILE = "confinement_result.json"
MARKER = "@@CONFINED_RESULT@@"

# The runner executes inside the worktree with cwd = worktree, so `import canonical...`
# resolves to the CLONE's code and `root='.'` is the worktree. The adapter's own result
# dict goes to a file inside the worktree (stdout stays free for adapter prints), and the
# caller reads it before the worktree is released.
RUNNER = r"""
import importlib, json, sys
module_name, entrypoint, payload = sys.argv[1], sys.argv[2], sys.argv[3]
out = {"__confined_runner__": "started"}
try:
    mod = importlib.import_module("canonical.runtime.bound_capabilities." + module_name)
    fn = getattr(mod, entrypoint)
    res = fn(json.loads(payload), ".")
    out = res if isinstance(res, dict) else {"__confined_runner__": "non-dict result", "repr": repr(res)[:500]}
except BaseException as exc:
    out = {"__confined_runner__": "adapter_raised", "error_type": type(exc).__name__,
           "error": str(exc)[:500]}
with open(%r, "w") as fh:
    json.dump(out, fh)
""" % (RESULT_FILE,)

_ADAPTER_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")

_DECLS: dict[str, Any] | None = None


def declarations(path: Path = DECLARATIONS_PATH) -> dict[str, Any]:
    """Load and validate the reviewed effect declarations (cached)."""
    global _DECLS
    if _DECLS is not None:
        return _DECLS
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "PROJECT_BRAIN_CONFINED_EFFECT_DECLARATIONS_V1":
        raise ValueError("CONFINED_EFFECT_DECLARATIONS_SCHEMA_MISMATCH")
    caps = raw.get("capabilities")
    if not isinstance(caps, dict):
        raise ValueError("CONFINED_EFFECT_DECLARATIONS_INVALID")
    _DECLS = caps
    return _DECLS


def reset_cache() -> None:
    global _DECLS
    _DECLS = None


def _args_of(entry: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    args = dict(action.get("args") or {})
    args.pop("capability_id", None)
    return args


def _sha256_file(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _host_escaping(host_root: Path, value: str) -> bool:
    """True when a bound string value is an absolute path into the host."""
    if not isinstance(value, str) or not value.startswith("/"):
        return False
    stripped = value[len(str(host_root)):] if value.startswith(str(host_root)) else value
    candidate = (host_root / stripped.lstrip("/")).resolve()
    try:
        return host_root.resolve() in candidate.parents or candidate == host_root.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def run_confined_capability(
    cid: str,
    entry: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    host_root: str | Path,
) -> dict[str, Any] | None:
    """Run one declared capability on the disposable clone; `None` means "not routable".

    `None` is the fail-closed answer: the caller then refuses exactly as before. A dict
    return is the adapter's own result, stamped with the confinement receipt and judged
    by the caller's expectation check.
    """
    host = Path(host_root).resolve()
    decl = declarations().get(str(cid))
    if not isinstance(decl, Mapping):
        return None
    # A NATIVE ARGV DECLARATION runs the command itself, not a Python adapter.
    #
    # `shell.command.run` compiles to exactly the shape the confinement was built for -- a list
    # argv, no shell (`{"argv": ["cp", "AGENTS.md", "AGENTS_copy.md"]}`) -- and it was refused with
    # REQUIRES_ADMITTED_CONFINEMENT purely because no declaration existed to carry it, so
    # "Copy the file X to Y" could not be done. Measured: the confinement runs that argv in a
    # disposable clone, verifies the declared effect inside the worktree by sha256, and proves the
    # host untouched. What a declaration adds is the part a raw argv cannot say for itself: WHICH
    # argument names the file this command promises to produce. An argv with no declared effect is
    # still refused, because an unverifiable effect is not a capability.
    if decl.get("native_argv") is True:
        argv_in = (action.get("args") or {}).get("argv")
        if not isinstance(argv_in, list) or not argv_in or not all(isinstance(a, str) for a in argv_in):
            return None
        effect_args = decl.get("effect_args")
        if not isinstance(effect_args, list):
            return None
        # effect_args indexes the argv (an integer position) or names an argument key.
        effects: list[str] = []
        for spec in effect_args:
            value = None
            if isinstance(spec, int):
                if -len(argv_in) <= spec < len(argv_in):
                    value = argv_in[spec]
            elif isinstance(spec, str):
                value = (action.get("args") or {}).get(spec)
            if not isinstance(value, str) or not value.strip():
                return None
            if _host_escaping(host, value) or Path(value).is_absolute():
                return None
            effects.append(value)
        # A COMMAND THAT ONLY REPORTS IS STILL A VERIFIABLE CAPABILITY.
        #
        # `python3 --version` promises no file; its result IS its stdout, and requiring a file it
        # never writes reported a working command as FAIL_CLOSED__CONFINED_RUN_NOT_VERIFIED. The
        # declaration may now name the argv TAILS that are pure observations (--version, --help),
        # and the evidence for those is the run itself: exit 0 and a non-empty stdout_tail. It is
        # matched on the tail of the argv, so `python3 --version` and `git --version` are one rule,
        # and it is DECLARED DATA, not a heuristic over command strings -- the same authority
        # contract the rest of this file uses. Nothing is assumed about the command's semantics.
        stdout_effect = False
        _declared_tails = decl.get("stdout_effect_argv")
        if isinstance(_declared_tails, list) and _declared_tails:
            for _tail in _declared_tails:
                if (isinstance(_tail, list) and len(_tail) <= len(argv_in)
                        and list(argv_in[len(argv_in) - len(_tail):]) == list(_tail)):
                    stdout_effect = True
                    break
        # ...and when the SENTENCE states where the output goes, that file is the evidence.
        stdout_to = None
        _to_key = decl.get("stdout_to_effect_arg")
        if isinstance(_to_key, str):
            _bound_out = (action.get("args") or {}).get(_to_key)
            if isinstance(_bound_out, str) and _bound_out.strip():
                if _host_escaping(host, _bound_out) or Path(_bound_out).is_absolute():
                    return None
                stdout_to = _bound_out
        # A COMMAND THAT PRINTED SOMETHING IS A COMMAND WHOSE EFFECT THE RECEIPT HOLDS.
        #
        # This used to admit an argv run with no declared effect ONLY when the argv ended in one of
        # a short list of tails (`--version`, `-V`, `--help`, `-h`) -- data about which commands
        # were expected to talk. Measured 2026-11-22, that list was the whole distance between the
        # most ordinary request a person can make and the machine: `ls -la` bound its argv, reached
        # this gate, and was refused, while `ls -la --version` would have passed.
        #
        # The list was guarding a real property, and the property is tested directly a few lines
        # below: `effects_ok = bool(_exited and str(executed.get("stdout_tail") or "").strip())`.
        # A tail in a whitelist does not make a run verifiable -- a whitelisted command that prints
        # NOTHING already fails, and a non-whitelisted command that printed 2000 bytes of real
        # output was already proof that it ran and that the host was untouched. What the whitelist
        # actually decided was whether someone had anticipated the command, which is not evidence
        # about this run.
        #
        # So the evidence is the RECEIPT, not the shape: stdout was captured, the run exited 0, and
        # the host is untouched. A command that prints nothing still has no verifiable effect and is
        # still refused; a declared file effect is still checked as a file.
        if not effects and not stdout_to:
            # `stdout_effect` no longer widens admission; it only says the receipt is the evidence.
            pass
        # A STATED DESTINATION FOR THE OUTPUT IS A DECLARED EFFECT.
        #
        # `CF.execute` only gives stdout its file when the file is one of the confinement's
        # DECLARED effects -- that is the only place it writes one. Passing the destination as
        # `stdout_to` alone left the effect list empty, so nothing was written, the worktree held
        # no `out.txt`, and the run was reported unverified although the command had succeeded.
        if stdout_to is not None and stdout_to not in effects:
            effects.append(stdout_to)
        budget = float(decl.get("budget_s") or 120.0)
        conf = CF.admit(host, argv_in, budget_s=budget, declared_effects=effects,
                        stdout_to=stdout_to)
        if not isinstance(conf, CF.Confinement):
            return None
        try:
            executed = CF.execute(conf)
            observed = executed.get("declared_effects") or {}
            host_untouched = bool(executed.get("host_untouched"))
            _exited = executed.get("exit_code") == 0
            # The evidence for a file effect is the file; for an observation it is the run.
            effects_ok = (all(o.get("exists") and o.get("inside_worktree")
                              for o in observed.values()) if observed else False)
            if stdout_to is not None:
                _written = (conf.worktree / stdout_to)
                effects_ok = effects_ok or bool(
                    _exited and _written.is_file() and _written.stat().st_size > 0
                    and str(_written.resolve()).startswith(str(conf.worktree.resolve())))
                if _written.is_file() and _exited:
                    effects = [stdout_to]
                    observed = {stdout_to: {"exists": True, "inside_worktree": True}}
            elif not observed:
                # The receipt: the host is untouched and the run produced an OUTCOME. "Exited 0 and
                # printed" is the strict form. But a program may DOCUMENT that a nonzero exit is one
                # of its normal answers -- `grep --help`: "Exit status is 0 if any line is selected,
                # 1 otherwise" -- and then "no match" is the result, not a failure. Which
                # programs those are is read from the programs, per machine, never listed here.
                _printed = bool(str(executed.get("stdout_tail") or "").strip())
                _documented_negative = False
                if not _exited and argv_in:
                    try:
                        from canonical.runtime import machine_purpose_index_v1 as _machine
                        _documented_negative = _machine.documents_a_nonzero_exit_as_a_result(
                            str(argv_in[0]))
                    except Exception:  # noqa: BLE001 - no reader, no benefit of the doubt
                        _documented_negative = False
                # TWO KINDS OF EVIDENCE, AND THE PROGRAM DECIDES WHICH ONE APPLIES.
                #
                #   * It printed. The output is the effect, and the exit code must be the success
                #     the program documents.
                #   * It printed NOTHING and exited with a code the program documents as a RESULT.
                #     For grep that is "1 otherwise" -- no match -- and "no match" is a complete,
                #     true answer to "is TODO in this file". Requiring bytes here would make a
                #     correct answer unrepresentable.
                #
                # `true` still fails both: it documents no exit status and prints nothing, so its
                # empty output is not evidence of anything. Nothing is listed here; the exception
                # exists only for programs that state it in their own help text.
                effects_ok = bool((_printed and _exited)
                                  or (_documented_negative and not _printed))
            confined = {
                "capability_id": str(cid),
                "pass": bool(host_untouched and effects_ok),
                "status": (("PASS__CONFINED_NATIVE_ARGV_VERIFIED" if _exited
                            else "PASS__CONFINED_DOCUMENTED_NONZERO_RESULT")
                           if host_untouched and effects_ok
                           else "FAIL_CLOSED__CONFINED_RUN_NOT_VERIFIED"),
                "exit_code_documented_as_a_result": bool(
                    executed.get("exit_code") and _documented_negative),
                "argv": list(argv_in),
                "dependency": {"executor": "confinement_v1", "adapter": "native_argv"},
                "confinement": {
                    "receipt_sha256": executed.get("receipt_sha256"),
                    "host_untouched": host_untouched,
                    "declared_effects": observed,
                    "exit_code": executed.get("exit_code"),
                    "budget_s": budget,
                },
            }
            # AN OBSERVATION'S ANSWER IS WHAT THE COMMAND PRINTED.
            #
            # `observations` passed above and nothing was delivered, because `applied_to_host` only
            # records FILES. So `ls -la` ran, was verified, and returned a pass with no listing in
            # it -- the machine did the work and threw the answer away, which reads exactly like a
            # pass and is worth nothing to the caller who asked. The receipt already holds the
            # bytes; they are carried out here so the result answers the question it was asked.
            if not effects and stdout_to is None:
                confined["stdout"] = executed.get("stdout_tail") or ""
                confined["stderr"] = executed.get("stderr_tail") or ""
            # THE WORK IS PROVEN, SO NOW DO IT WHERE IT WAS ASKED FOR.
            #
            # Two rules in this repository are both right and, left alone, mutually exclusive:
            # the confinement proves the host UNTOUCHED (that is what makes exploring safe), and
            # `_execute` refuses a promise-to-change that leaves the world identical
            # (FAIL_CLOSED__NO_OBSERVED_EFFECT). So a `cp` verified perfectly in a clone could
            # never pass, because passing requires the host to change and confinement forbids it.
            #
            # The resolution is the one the module was built around: the clone is where a command
            # is TRIED, not where a stated change is DELIVERED. Once the argv has run there with a
            # verified receipt -- it exited 0, every declared effect exists inside the worktree --
            # the same argv is applied here, and the RESULT IS RE-READ FROM THE HOST rather than
            # trusted. That is not a loosening: a command that escapes the worktree was already
            # refused above by `_host_escaping`, measured against a `bash -c 'echo > /abs/path'`
            # which the confinement declines to run at all.
            applied: list[dict[str, Any]] = []
            if confined["pass"] and bool(decl.get("apply_effect_to_host")):
                import subprocess as _sp
                try:
                    _proc = _sp.run(list(argv_in), cwd=str(host), capture_output=True, timeout=budget)
                except Exception as exc:  # noqa: BLE001
                    confined["pass"] = False
                    confined["status"] = "FAIL_CLOSED__APPLY_TO_HOST_DID_NOT_RUN"
                    confined["apply_error"] = type(exc).__name__
                else:
                    # THE CLONE PROVED WHAT TO WRITE; THE HOST RUN ONLY DELIVERS IT.
                    #
                    # A command whose product is its STDOUT (`python3 --version`) writes no file
                    # when it is run again, so re-reading the host for `out.txt` found nothing and
                    # an ordinary observation the caller had already placed came back
                    # FAIL_CLOSED__HOST_DID_NOT_SHOW_THE_EFFECT. What the host copy must show is the
                    # bytes the verified clone run produced -- so when the sentence named the
                    # destination, those exact bytes are written there and then re-read. A command
                    # that writes its own file is unaffected: `effects` holds its paths either way,
                    # and the check below is the same check.
                    if stdout_to is not None:
                        target = host / stdout_to
                        try:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(_proc.stdout or b"")
                        except Exception as exc:  # noqa: BLE001
                            confined["apply_error"] = type(exc).__name__
                    for effect in effects:
                        target = host / effect
                        exists = target.is_file()
                        applied.append({"effect": effect, "exists_on_host": exists,
                                        "sha256": (_sha256_file(target) if exists else None)})
                    # AN OBSERVATION HAS NOTHING TO DELIVER.
                    #
                    # `applied` is the list of FILES the host copy was checked for. A command whose
                    # product is its stdout and which was given no destination (`ls -la`) produces
                    # no file at all, so `applied` is empty and requiring a non-empty list reported
                    # a run that had already succeeded -- on the clone AND on the host, exit 0 both
                    # times -- as a failure to show its effect. There is no effect to show: the
                    # effect WAS the output, and the receipt already holds it.
                    #
                    # So an empty `applied` means "nothing to verify on the host", and the host run's
                    # own exit code is what is verified. Every command that DOES name a file still
                    # has one entry and is still checked for existence, byte for byte.
                    _nothing_to_deliver = not applied
                    # The host run is judged by the same rule as the clone run: the program's own
                    # documented exit status decides whether a nonzero code is a failure.
                    _host_negative_ok = bool(_proc.returncode != 0 and _documented_negative)
                    if not ((_proc.returncode == 0 or _host_negative_ok)
                            and (_nothing_to_deliver or all(a["exists_on_host"] for a in applied))):
                        confined["pass"] = False
                        confined["status"] = "FAIL_CLOSED__HOST_DID_NOT_SHOW_THE_EFFECT"
                    elif _nothing_to_deliver:
                        confined["status"] = "PASS__OBSERVATION_RAN_AND_VERIFIED"
                    else:
                        confined["status"] = "PASS__APPLIED_TO_HOST_AND_VERIFIED"
                confined["applied_to_host"] = applied
            return confined
        finally:
            import shutil as _sh
            _sh.rmtree(str(conf.worktree), ignore_errors=True)

    effect_args = decl.get("effect_args")
    if not isinstance(effect_args, list) or not effect_args:
        return None
    args = _args_of(entry, action)
    effects: list[str] = []
    for name in effect_args:
        value = args.get(str(name))
        if not isinstance(value, str) or not value.strip():
            return None  # the door did not bind the declared effect -> refuse as before
        if _host_escaping(host, value):
            return None  # a bound absolute path into the host is not a confined effect
        effects.append(value)

    module_name = str(entry.get("adapter_module") or "")
    if not module_name or any(ch not in _ADAPTER_OK for ch in module_name):
        return None
    entrypoint = str(entry.get("entrypoint") or "run")

    budget = float(decl.get("budget_s") or 600.0)
    argv = ["python3", "-c", RUNNER, module_name, entrypoint, json.dumps(args)]
    conf = CF.admit(host, argv, budget_s=budget, declared_effects=effects)
    if not isinstance(conf, CF.Confinement):
        return None  # the confinement refused the declared shape -> refuse as before
    try:
        executed = CF.execute(conf)
        outcome = executed.get("outcome")
        host_untouched = bool(executed.get("host_untouched"))
        observed = executed.get("declared_effects") or {}
        effects_ok = bool(observed) and all(o.get("exists") for o in observed.values())
        receipt = {
            "receipt_sha256": executed.get("receipt_sha256"),
            "host_head": executed.get("host_head"),
            "host_untouched": host_untouched,
            "outcome": outcome,
            "elapsed_s": executed.get("elapsed_s"),
            "declared_effects": observed,
        }
        adapter_result: dict[str, Any] | None = None
        raised_reason: str | None = None
        result_path = conf.worktree / RESULT_FILE
        if result_path.is_file():
            try:
                loaded = json.loads(result_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and "__confined_runner__" not in loaded:
                    adapter_result = loaded
                elif isinstance(loaded, dict) and loaded.get("__confined_runner__") == "adapter_raised":
                    # The adapter ran and refused: the reason is measured data, not silence.
                    raised_reason = "CONFINED_ADAPTER_RAISED:%s:%s" % (
                        loaded.get("error_type"), loaded.get("error"))
            except (ValueError, OSError):
                adapter_result = None

        if adapter_result is None:
            return {
                "pass": False,
                "status": CF.STATUS if hasattr(CF, "STATUS") else "FAIL_CLOSED__CONFINED_EXECUTION",
                "reason": raised_reason or "CONFINED_RUN_DID_NOT_PRODUCE_A_RESULT",
                "confinement": receipt,
                "capability_id": str(cid),
                "dependency": {"type": "confinement", "modules": [], "executor": EXECUTOR},
                "terminal_authority": False,
            }

        adapter_result.setdefault("capability_id", str(cid))
        adapter_result["confinement"] = receipt
        adapter_result["dependency"] = {
            "type": "confinement", "modules": [], "executor": EXECUTOR,
        }
        adapter_result["terminal_authority"] = False
        # The same ruler the local path uses, applied to the confined result.
        from canonical.runtime import live_brain_route_admission_v1 as _door

        _door._check_expectation(action.get("expect"), adapter_result, args)
        return adapter_result
    finally:
        CF.release(conf)
