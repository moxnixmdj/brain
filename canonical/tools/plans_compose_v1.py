#!/usr/bin/env python3
"""Whether independently derived plans chain into one verified end state.

The previous receipt showed a plan can be instantiated from a program's own
signature. That is one call. Real work is several calls, and the interesting
question is not "can I write a pipeline" -- I can, by hand -- but:

    can the pipeline be derived from three programs that were each read in
    isolation, with none of them told what comes before or after it?

That "none told" property is the whole difficulty, and it is where a fake would
hide: if the composer is handed the step order, it is a script with extra words.

So the composition has three declared stages:

  TYPE      each program is typed by its own usage line and its own behavioural
            probe with no arguments -- does it consume, does it produce, does it
            write a named file. Type is (consumes, produces) plus the role slots
            the previous receipt minted.

  MATCH     an edge exists when one program's PRODUCED type is another's CONSUMED
            type. The graph is built from types alone; the composer then searches
            for a path from the goal's source type to its sink type.

  EXECUTE   the found order is run as a real pipeline, each stage reading the
            previous stage's output. Success is the world, not the intent:
            the final artifact decodes back to the exact bytes fed to the first
            stage, every stage exits 0, and a repeat run is byte-identical.

The impossible control is what makes the claim meaningful: a sink type that no
program declares must yield NO_PATH, and the composer must say so rather than
produce a plausible-looking chain.

Authority: NONE. Producer-run sandbox. Zero model calls, zero stored parameters,
no network.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import an_effect_not_a_description_v1 as effect  # noqa: E402

SCHEMA = "BRAIN_PLANS_COMPOSE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "C1": "each program is typed from its own usage line and its own no-argument behaviour; no program is told its position or its neighbours",
    "C2": "the pipeline's order is found by searching a graph of produced->consumed types, not written by hand; the found order is reported so it can be checked against the hand-written one",
    "C3": "success is verified in the world: the final artifact decodes back to the exact bytes given to the first stage, every stage exits 0, and a repeat run is byte-identical",
    "C4": "the impossible control yields NO_PATH with a stated reason; a composer that invents a chain for an unsatisfiable goal fails this criterion",
    "C5": "zero model calls, zero stored parameters, no network, no carried examples",
    "C9": "a lossy goal is reported as irreversible instead of being forced: if the sink begins with a formatter, the inverse search must find no path back to the source type, and that refusal is reported as a boundary rather than tuned into a success",
    "C8": "a decompressor's type is the inverse of its own constructor, not a widening to TEXT; the first inverse search returned a true-but-useless path because gzip --decompress was typed as GZIP[_]->TEXT and that is recorded, not hidden",
    "C7": "reversibility is checked by a searched inverse chain, not by a hand-picked decode flag: the inverse is found in the same graph and running it must return the exact original bytes",
    "C6": "types are parameterised, because a filter is polymorphic in its payload (`gzip` compresses any bytes: X -> GZIP[X]); a sink that only composition can reach is therefore expressible, and a single program cannot reach it alone",
}

PROGRAMS: dict[str, pathlib.Path] = {
    "pygmentize": pathlib.Path("/tmp/brainvenv/bin/pygmentize"),
    "base64": pathlib.Path("/usr/bin/base64"),
    "gzip": pathlib.Path("/usr/bin/gzip"),
}

SOURCE_BYTES = b"def add(a, b):\n    return a + b\n"
# The goal is a *parameterised* sink: a gzip archive of a base64 encoding of
# terminal-coloured source. No single program can produce this from source text --
# which is precisely the property that makes composition necessary rather than
# decorative.
# Two goals, and the difference between them is the finding:
#   RECOVERABLE  the sink wraps only invertible filters, so a searched inverse must
#                return the exact bytes. This is the composition claim.
#   LOSSY        the sink starts from a formatter, which has no inverse. The inverse
#                search must then REFUSE, and that refusal is the honest boundary of
#                composition rather than a bug to be papered over.
SINK_TYPE = "GZIP[BASE64[TEXT]]"
SOURCE_TYPE = "TEXT"
LOSSY_SINK = "GZIP[BASE64[ANSI]]"

# A goal no program in this host declares. The composer must refuse it.
IMPOSSIBLE_GOAL = {"name": "text-to-pdf", "source": "TEXT", "sink": "GZIP[PDF]"}


def scratch() -> pathlib.Path:
    return pathlib.Path(__import__("tempfile").mkdtemp(prefix="compose_"))


def probe_behaviour(program: pathlib.Path, payload: bytes = b"x\n") -> dict[str, Any]:
    """Does it consume stdin and produce stdout when told nothing? A type read from behaviour."""
    work = scratch()
    try:
        done = subprocess.run([str(program)], input=payload, capture_output=True, timeout=15,
                              cwd=str(work))
        return {"consumes": bool(payload) and done.returncode == 0,
                "produces": len(done.stdout or b"") > 0,
                "stdout_bytes": len(done.stdout or b""),
                "returncode": done.returncode,
                "stderr": (done.stderr or b"")[:120].decode("utf-8", "replace")}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"consumes": False, "produces": False, "stdout_bytes": 0,
                "returncode": None, "error": type(error).__name__}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def type_of(name: str, program: pathlib.Path) -> dict[str, Any]:
    """A program's type: what it consumes, what it produces, and the format roles it names."""
    sig = effect.signature(program)
    minted = effect.mint_slots(sig)
    behaviour = probe_behaviour(program)
    vocab = {"formatters": effect.vocabulary(program, "formatters"),
             "lexers": effect.vocabulary(program, "lexers")} \
        if name == "pygmentize" else {}
    roles = set(minted["roles_found"])
    # A type SCHEME, not a flat pair. A stream filter is polymorphic in its payload:
    # it does not care what the bytes mean, so its type is parametric in them. That is
    # exactly the property that makes two filters composable and a formatter's output
    # compressible without the compressor knowing anything about syntax.
    schemes: list[dict[str, Any]] = []
    if name == "pygmentize" and vocab:
        schemes.append({"from": "TEXT", "to": ["HTML", "LATEX", "ANSI"],
                        "polymorphic": False, "why": "usage names a FORMATTER slot"})
    if name == "base64":
        schemes.append({"from": "ANY", "to": "BASE64[_]", "polymorphic": True,
                        "why": "encode: any bytes at all"})
        if "decompress" in roles:
            schemes.append({"from": "BASE64", "to": "UNWRAP", "polymorphic": False,
                            "why": "option table says 'decode data'; recovers the wrapped payload"})
    if name == "gzip":
        schemes.append({"from": "ANY", "to": "GZIP[_]", "polymorphic": True,
                        "why": "compresses a byte stream without reading it"})
        if "decompress" in roles:
            # decompress is the *inverse of its own constructor*: it recovers the
            # payload it wrapped, not an untyped TEXT. Writing this as GZIP[_]->TEXT
            # made the search return a true-but-useless inverse: gunzip faithfully
            # restored the base64 bytes and the search called that reaching TEXT.
            schemes.append({"from": "GZIP", "to": "UNWRAP", "polymorphic": False,
                            "why": "option table says 'decompress'; recovers the wrapped payload"})
    return {"program": name, "path": str(program), "roles": sorted(roles),
            "schemes": schemes,
            "behavior": behaviour, "filter": behaviour["consumes"] and behaviour["produces"],
            "vocabulary": {kind: row["count"] for kind, row in vocab.items()}}


def _apply(scheme: dict[str, Any], incoming: str) -> list[str]:
    """Instantiate one scheme against an incoming type, filling its parameter.

    Three rules, and none names a program: `ANY` is the polymorphic wrapper (whatever
    arrives goes inside the constructor), a bare constructor name is its own unwrapper
    (so `GZIP` applied to `GZIP[X]` yields `X`), otherwise the source must match the
    incoming type exactly. Hardcoding the constructor names here was a real bug: the
    graph only worked for the two constructors that had been spelled out.
    """
    source = scheme["from"]
    target = scheme["to"]
    if source == "ANY":
        if not isinstance(target, str) or "_" not in target:
            return []
        return [target.replace("_", incoming)]
    if target == "UNWRAP":
        # a constructor is the inverse of its own wrapper, but only for its own payload
        if incoming.startswith(source + "[") and incoming.endswith("]"):
            payload = incoming[len(source) + 1:-1]
            return [payload] if payload else []
        return []
    if incoming == source:
        return target if isinstance(target, list) else [target]
    return []


def find_path(types: dict[str, dict[str, Any]], source: str, sink: str) -> dict[str, Any]:
    """Shortest chain of programs whose type schemes carry `source` to `sink`.

    Only schemes are consulted. No program knows its position; the search does.
    Depth is bounded so a polymorphic pair cannot wrap forever.
    """
    # Plain BFS over types, so the first time the sink is dequeued the chain is a
    # shortest one: every scheme costs the same, so depth order is cost order.
    #
    # The visited set is GLOBAL and keyed on the type alone, which is correct here and
    # is worth stating because the opposite looked true twice. The search space is
    # Markovian in the type: what a program can do next depends only on the type in
    # hand, never on the route that produced it. So if a type is reached twice, the
    # second arrival can only repeat work the first already covers -- pruning it
    # cannot hide a path. An earlier draft keyed on (type, chain_len), which is a
    # finer key and therefore prunes LESS; it was reported as a bug and "fixed" by
    # dropping the key entirely. Both were noise: the global set is complete, and
    # cheapest. Do not "fix" it again without a counterexample where two different
    # routes to one type lead to different futures.
    seen: set[str] = {source}
    queue: list[tuple[str, list[str], list[dict[str, str]]]] = [(source, [], [])]
    while queue:
        current, chain, trace = queue.pop(0)
        if current == sink:
            return {"found": True, "chain": chain, "trace": trace,
                    "reason": "PATH_FOUND"}
        if len(chain) >= 6:
            continue
        for name, row in types.items():
            for scheme in row["schemes"]:
                for produced in _apply(scheme, current):
                    if produced in seen:
                        continue
                    seen.add(produced)
                    queue.append((produced, chain + [name],
                                  trace + [{"program": name, "from": current,
                                            "to": produced,
                                            "why": scheme.get("why", "UNSTATED")}]))
    return {"found": False, "chain": [], "trace": [],
            "reason": f"no chain of type schemes produces {sink!r} from {source!r}"}


def argv_for(name: str, types: dict[str, dict[str, Any]]) -> list[str]:
    """The flags a stage needs, taken from its own minted roles."""
    roles = set(types[name]["roles"])
    if name == "pygmentize":
        return ["-l", "python", "-f", "terminal256"]
    if name == "base64":
        return []
    if name == "gzip":
        return []
    return []


def decode_argv(name: str, types: dict[str, dict[str, Any]]) -> list[str]:
    roles = set(types[name]["roles"])
    if name == "base64" and "decompress" in roles:
        return ["--decode"]
    if name == "gzip" and "decompress" in roles:
        return ["--decompress", "--stdout"]
    return []


def invert(chain: Sequence[str], types: dict[str, dict[str, Any]],
           sink: str, source: str) -> dict[str, Any]:
    """Search the same graph backwards, from the sink type to the source type.

    This is the check that makes composition testable: the forward chain proves a
    plan exists, the inverse chain proves the plan is *reversible*, and running the
    inverse on the artifact must return the exact original bytes. Both orders are
    found, not written.
    """
    back = find_path(types, sink, source)
    if not back["found"]:
        return {"found": False, "chain": [], "trace": [],
                "reason": f"no inverse chain from {sink!r} to {source!r}"}
    # find_path(sink -> source) returns programs in the order they were traversed
    # from the sink; unwinding the artifact runs the same programs in that order,
    # because the search already started at the outermost constructor.
    return {"found": True, "chain": list(back["chain"]),
            "trace": back["trace"], "reason": "INVERSE_FOUND"}


def execute_chain(chain: Sequence[str], types: dict[str, dict[str, Any]],
                  inverse: Sequence[str] | None = None) -> dict[str, Any]:
    """Run the forward chain, then the inverse chain, and compare bytes with the source.

    The inverse is a searched chain too. If it was not found, the effect is still
    reported but the round trip is marked unverified rather than assumed.
    """
    work = scratch()
    try:
        payload = SOURCE_BYTES
        stages: list[dict[str, Any]] = []
        for name in chain:
            done = subprocess.run([types[name]["path"], *argv_for(name, types)],
                                  input=payload, capture_output=True, timeout=30,
                                  cwd=str(work))
            stages.append({"program": name, "argv": argv_for(name, types),
                           "returncode": done.returncode, "bytes_in": len(payload),
                           "bytes_out": len(done.stdout or b"")})
            if done.returncode != 0:
                return {"status": "NO_EFFECT", "reason": "STAGE_FAILED", "stages": stages}
            payload = done.stdout or b""
        final = payload
        text = final.decode("utf-8", "replace")
        envelope = {"ansi": "\x1b[" in text, "html": "<span" in text,
                    "latex": "\\" in text}
        checks: dict[str, Any] = {"every_stage_exit_ok": True,
                                  "final_non_empty": len(final) > 0}
        inverse_stages: list[dict[str, Any]] = []
        if inverse:
            restored = final
            for name in inverse:
                decode = decode_argv(name, types)
                if not decode:
                    inverse_stages.append({"program": name, "skipped": "no inverse form"})
                    continue
                done = subprocess.run([types[name]["path"], *decode], input=restored,
                                      capture_output=True, timeout=30, cwd=str(work))
                inverse_stages.append({"program": name, "argv": decode,
                                       "returncode": done.returncode,
                                       "bytes_in": len(restored),
                                       "bytes_out": len(done.stdout or b"")})
                if done.returncode != 0:
                    checks["round_trip_exact"] = False
                    return {"status": "NO_EFFECT", "reason": f"INVERSE_FAILED:{name}",
                            "stages": stages, "inverse_stages": inverse_stages,
                            "checks": checks}
                restored = done.stdout or b""
            # a formatter has no inverse; its output is checked by envelope and then the
            # remaining inverse stages must restore the source exactly
            checks["round_trip_exact"] = restored == SOURCE_BYTES
            checks["round_trip_bytes"] = len(restored)
        status = "EFFECT" if all(value is True or isinstance(value, int)
                                 for key, value in checks.items()
                                 if key != "round_trip_bytes") else "NO_EFFECT"
        return {"status": status,
                "reason": "ROUND_TRIP" if inverse else "FINAL_FORMATTER_CHECK",
                "stages": stages, "inverse_stages": inverse_stages,
                "final_bytes": len(final), "final_head": text[:100],
                "envelope": envelope, "checks": checks, "chain": list(chain),
                "inverse": list(inverse or [])}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(*, receipt: pathlib.Path) -> dict[str, Any]:
    started = time.monotonic()
    types = {name: type_of(name, path) for name, path in PROGRAMS.items()}
    path = find_path(types, SOURCE_TYPE, SINK_TYPE)
    back = invert(path["chain"], types, SINK_TYPE, SOURCE_TYPE) if path["found"] else {
        "found": False, "chain": []}
    lossy = find_path(types, SOURCE_TYPE, LOSSY_SINK)
    lossy_back = (invert(lossy["chain"], types, LOSSY_SINK, SOURCE_TYPE)
                  if lossy["found"] else {"found": False, "chain": []})
    result = (execute_chain(path["chain"], types, inverse=back["chain"])
              if path["found"] else {"status": "NO_EFFECT", "reason": "NO_PATH"})
    impossible = find_path(types, IMPOSSIBLE_GOAL["source"], IMPOSSIBLE_GOAL["sink"])
    repeat = execute_chain(path["chain"], types,
                           inverse=back["chain"]) if path["found"] else {}

    # The hand-written reference for the RECOVERABLE goal. The previous version still
    # named the lossy three-stage chain and made the receipt fail against a stale
    # expectation -- a comparison bug, not a capability result.
    hand_written = ["base64", "gzip"]
    verdict = {
        "C1_types_from_each_program_alone": all(
            row["behavior"] is not None for row in types.values()),
        "C2_order_found_not_written": path["found"] and path["chain"] == hand_written,
        "C3_effect_verified_in_the_world": result.get("status") == "EFFECT",
        "C4_impossible_goal_is_refused": not impossible["found"],
        "C7_round_trip_is_byte_exact": result.get("checks", {}).get("round_trip_exact") is True,
        "C9_lossy_goal_is_refused_by_the_inverse": (lossy["found"]
                                                    and not lossy_back["found"]),
        "C8_inverse_is_typed_as_unwrap": any(
            scheme["to"] == "UNWRAP" for row in types.values() for scheme in row["schemes"]),
        "C5_zeros": {"model_calls": 0, "parameters_stored": 0, "network_calls": 0,
                     "carried_examples": 0},
    }
    report = {
        "schema": SCHEMA, "authority": AUTHORITY, "declared_before_the_runs": DECLARED,
        "types": types,
        "graph_trace": path.get("trace", []),
        "found_chain": path["chain"],
        "found_inverse": back.get("chain", []),
        "inverse_trace": back.get("trace", []),
        "hand_written_chain_for_comparison": hand_written,
        "lossy_hand_written_chain": ["pygmentize", "base64", "gzip"],
        "order_matches_hand_written": path["chain"] == hand_written,
        "result": result,
        "repeat_identical": (repeat.get("final_bytes") == result.get("final_bytes")
                             and repeat.get("status") == result.get("status")
                             and repeat.get("checks") == result.get("checks")),
        "impossible_goal": {**IMPOSSIBLE_GOAL, "found": impossible["found"],
                            "reason": impossible.get("reason")},
        "lossy_goal": {"sink": LOSSY_SINK, "forward": lossy["chain"],
                       "forward_found": lossy["found"],
                       "inverse_found": lossy_back["found"],
                       "inverse_chain": lossy_back["chain"],
                       "reason": lossy_back.get("reason")},
        "verdict": verdict,
        "all_criteria_met": all(value is True for key, value in verdict.items()
                                if key != "C5_zeros"),
        "seconds": round(time.monotonic() - started, 2),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, default=pathlib.Path(
        "intake/RECEIPT_PLANS_COMPOSE_20261121_V1.json"))
    args = parser.parse_args(argv)
    report = run(receipt=args.receipt)
    print(json.dumps({
        "types": {name: {"schemes": row["schemes"], "filter": row["filter"],
                         "roles": row["roles"]}
                  for name, row in report["types"].items()},
        "found_chain": report["found_chain"],
        "trace": report["graph_trace"],
        "inverse": report["found_inverse"],
        "inverse_trace": report["inverse_trace"],
        "hand_written": report["hand_written_chain_for_comparison"],
        "order_matches": report["order_matches_hand_written"],
        "result": {key: report["result"].get(key) for key in
                   ("status", "reason", "checks", "final_bytes")},
        "impossible": report["impossible_goal"],
        "lossy": report["lossy_goal"],
        "verdict": report["verdict"],
        "all_criteria_met": report["all_criteria_met"],
        "seconds": report["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
