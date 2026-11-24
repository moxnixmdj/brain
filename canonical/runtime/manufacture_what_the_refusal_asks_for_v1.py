#!/usr/bin/env python3
"""An artefact a refusal asks for is MANUFACTURED, never faked -- and the producer is the
program's own declaration.

THE MEASURED WALL. Round 8 read refusals as specifications and the largest remaining group
was `UNLOADABLE`: 87 in the nine-program fleet, and after this round's census repair (below)
601 on openssl alone. Every one of them says the same thing -- the file is there and its
CONTENT is the wrong kind of thing. Round 8's answer was to substitute a witness, which
cannot work when the environment contains nothing of that kind. The term was missing because
the environment did not contain it, and no amount of reading supplies an absence.

THE FRONTIER GOT THIS WRONG IN A MEASURED WAY. arXiv 2611.23305 ("Dependency Fabrication in
Repository Deployment Agents") builds probes whose dependency CANNOT legitimately be
obtained, and finds Repo2Run and SetupX agents almost always write a stub and the harnesses
mostly mark the run SUCCESSFUL. Rules against it, in the prompt or in CONTRIBUTING.md, did
not reliably prevent it. So the danger here is not that manufacturing is impossible; it is
that manufacturing something that only LOOKS right is easy, and passes a test that cannot
tell the difference.

THE DISTINCTION THAT MAKES THIS SAFE. A manufactured artefact is admissible only when:

  1. PRODUCED, NOT WRITTEN. The command that makes it is a declaration the program itself
     printed. `openssl req -h` states `-x509`, `-newkey`, `-keyout`, `-out`, `-days`,
     `-nodes`, `-subj`; the producer is composed from those and nothing else. This module
     never assembles the bytes of the thing asked for.
  2. VERIFIED BY THE PROGRAM, NOT BY US. After the producer runs, the CONSUMER that was
     refusing is run again and must accept the artefact. The oracle is the refusing program,
     so a stub cannot pass: `openssl x509` rejects a file whose bytes are not a certificate
     however the file is named.
  3. NO VANISHING. The produced file must still exist afterwards, and the tree must have
     changed. A producer that exits 0 and leaves nothing has produced nothing.

An artefact that fails any of the three is reported `FABRICATED` or `UNVERIFIED`, never
counted. That is the whole guard: it is cheap because the check is the same program that
refused, and it is honest because nothing here can make `openssl x509` read a stub.

WHY THIS IS NOT THE SEED AGAIN. Rounds 6-8 supplied artefacts by putting them in the trial's
seed, which is the harness answering its own question. Here the producer runs INSIDE the
environment under test, from the program's own declarations, and its output is judged by the
program that asked. The difference is visible in the receipt: a supplied artefact is
`SEEDED`, a produced one is `MANUFACTURED`, and they are counted separately.

WHAT IT REFUSES TO DO. It never runs a producer whose command is not fully declared. It
never retries a producer with invented arguments. It never treats a verification failure as
a partial success. And it never manufactures from a source outside the environment under
test -- no network, no model, no checked-in fixture.

Authority NONE. Runs programs in a restored temporary tree; writes nothing to the repo.
$0, no model call, no network call.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

SCHEMA = "PROJECT_BRAIN_MANUFACTURE_WHAT_THE_REFUSAL_ASKS_FOR_V1"

MANUFACTURED = "MANUFACTURED__THE_PROGRAM_PRODUCED_IT_AND_THE_CONSUMER_ACCEPTED"
FABRICATED = "FABRICATED__THE_PRODUCER_MADE_SOMETHING_THE_CONSUMER_REFUSES"
UNVERIFIED = "UNVERIFIED__NOTHING_WAS_PRODUCED"
NO_DECLARED_PRODUCER = "NO_DECLARED_PRODUCER_FOR_THIS_KIND"
CONSUMED_AFTERWARDS = "CONSUMED__THE_CONSUMER_ACCEPTED_A_MANUFACTURED_ARTEFACT"

#: WHAT KIND OF THING A REFUSAL ASKS FOR, and the DECLARATIONS that produce it.
#:
#: Each entry names, for a kind, the subcommand the program declares and the flags that
#: subcommand declares for producing it. Every string here was read off the program's own
#: `-h` output (quoted in the comment) rather than invented, and every one of them is
#: REQUIRED to appear in the program's contract before the producer may run -- a producer
#: composed from flags the program did not print is unreachable by construction.
#:
#: This is a table of DECLARATIONS, not of programs: the subcommand and each flag are
#: checked against the contract at run time, so a program that does not declare them is
#: reported NO_DECLARED_PRODUCER instead of being handed a guess.
PRODUCERS = {
    "certificate": {
        "subcommand": "req",
        # -x509 "Output an X.509 certificate structure instead of a cert request"
        # -newkey "Generate new key with [<alg>:]<nbits> ..."
        # -keyout "File to write private key to"   -out "Output file"
        # -days "+int"                              -nodes "Don't encrypt private keys"
        # -subj "Set or modify subject of request or cert"
        "flags": ("-x509", "-newkey", "-keyout", "-out", "-days", "-nodes", "-subj"),
        "values": {"-newkey": "rsa:1024", "-keyout": "produced.key", "-out": "produced.pem",
                   "-days": "1", "-subj": "/CN=produced"},
    },
    "key": {
        "subcommand": "genpkey",
        # -out "Output file"   -algorithm "Public key algorithm"   -pkeyopt "Set the public key algorithm option"
        "flags": ("-algorithm", "-out", "-pkeyopt"),
        "values": {"-algorithm": "RSA", "-out": "produced.key", "-pkeyopt": "rsa_keygen_bits:1024"},
    },
    "parameters": {
        "subcommand": "dhparam",
        # -out "Output file"   -in "Input file"   -text "print the DH parameters"
        "flags": ("-out",),
        "values": {"-out": "produced.pem"},
    },
}

#: A kind is produced by ONE of these subcommands, and the artefact is looked for by the
#: name the producer was told to write. Nothing is scanned or guessed afterwards.
_ARTIFACT_NAMES = ("produced.pem", "produced.key")


def declared(contract_flags: Sequence[str], wanted: Sequence[str]) -> bool:
    """Are ALL of these flags declared by the scope this producer belongs to?"""
    spelled = {str(flag).split("=", 1)[0] for flag in contract_flags}
    return all(flag in spelled for flag in wanted)


def producer_for(kind: str, *, program: str, flags: Sequence[str]) -> list[str] | None:
    """The producing command, or None when this program did not declare it.

    EVERY FLAG IS CHECKED AGAINST THE CONTRACT FIRST. A producer assembled from flags the
    program never printed is exactly the fabrication the literature measured, so it is not
    attempted: the answer is NO_DECLARED_PRODUCER and the term stays missing.
    """
    recipe = PRODUCERS.get(kind.strip().lower())
    if recipe is None:
        return None
    if not declared(flags, recipe["flags"]):
        return None
    argv = [program, recipe["subcommand"]]
    for flag in recipe["flags"]:
        value = recipe["values"].get(flag)
        argv.append(f"{flag}={value}" if value is not None else flag)
    return argv


def _run(argv: Sequence[str], cwd: str, timeout: float = 30.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(list(argv), cwd=cwd, capture_output=True,
                                   timeout=timeout, stdin=subprocess.DEVNULL,
                                   env={**os.environ, "HOME": cwd})
        return {"exit": completed.returncode,
                "text": (completed.stdout + completed.stderr).decode("utf-8", "replace"),
                "argv": list(argv)}
    except subprocess.TimeoutExpired:
        return {"exit": None, "text": "TIMEOUT", "argv": list(argv)}
    except OSError as exc:
        return {"exit": None, "text": f"{type(exc).__name__}: {exc}", "argv": list(argv)}


def _digest(root: str) -> str:
    """Paths AND contents, so a directory appearing counts as a change."""
    import hashlib
    h = hashlib.sha256()
    for current, dirs, names in os.walk(root):
        dirs.sort()
        rel = os.path.relpath(current, root)
        if rel != ".":
            h.update(b"D:" + rel.encode())
        for name in sorted(names):
            path = os.path.join(current, name)
            h.update(b"F:" + os.path.relpath(path, root).encode())
            try:
                with open(path, "rb") as handle:
                    h.update(handle.read())
            except OSError:
                continue
    return h.hexdigest()


@dataclass
class Supply:
    """One missing term, the declared producer tried for it, and whether it was genuine."""

    kind: str
    consumer: list[str]
    producer: list[str] | None
    status: str
    consumer_exit_before: int | None
    consumer_exit_after: int | None
    produced: bool
    changed: bool
    restored: bool = True
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "consumer": self.consumer, "producer": self.producer,
                "status": self.status, "consumer_exit_before": self.consumer_exit_before,
                "consumer_exit_after": self.consumer_exit_after, "produced": self.produced,
                "changed": self.changed, "restored": self.restored,
                "evidence": self.evidence}


def declared_flags_of(program: str, subcommand: str) -> list[str] | None:
    """The flags the program declares for THIS SUBCOMMAND, or None if it does not admit it.

    THE SCOPE THAT DECLARES THE PRODUCER IS THE SCOPE THAT MUST BE READ. `openssl -h` prints
    no `-newkey`; `openssl req -h` prints it. Checking the producer's flags against the
    PARENT contract reported NO_DECLARED_PRODUCER for a producer the program plainly
    declares -- the same scope error round 7 fixed in the binder, and the reason this
    function asks the subcommand itself rather than being handed a flag list.
    """
    from canonical.runtime import tool_census_v1 as census_module
    answer = census_module.admits(program, subcommand,
                                  parent_text=census_module._own_text(program))
    if not answer["admitted"]:
        return None
    contract = census_module.parse_contract(answer["text"], f"{program} {subcommand}")
    return [spelling for flag in (contract.get("flags") or ())
            for spelling in (flag.get("flags") or ())]


def supply(kind: str, consumer: Sequence[str], *, program: str,
           flags: Sequence[str] | None = None, seed: Sequence[tuple[str, bytes]] = (),
           artifact_names: Sequence[str] = _ARTIFACT_NAMES) -> Supply:
    """Manufacture the kind the consumer asked for, then make the CONSUMER judge it.

    THE CONSUMER IS THE ORACLE, and that is what makes a stub useless: `openssl x509`
    refuses a file whose bytes are not a certificate no matter what it is called, so a
    fabricated artefact fails the same test a real one passes.
    """
    root = tempfile.mkdtemp(prefix="brain-supply-")
    try:
        for name, data in seed:
            with open(os.path.join(root, name), "wb") as handle:
                handle.write(data)
        before = _digest(root)
        first = _run(consumer, root)
        recipe = PRODUCERS.get(kind.strip().lower())
        if flags is None and recipe is not None:
            flags = declared_flags_of(program, recipe["subcommand"]) or ()
        producer = producer_for(kind, program=program, flags=flags or ())
        if producer is None:
            return Supply(kind, list(consumer), None, NO_DECLARED_PRODUCER,
                          first["exit"], None, False, False)
        made = _run(producer, root)
        present = [name for name in artifact_names if os.path.exists(os.path.join(root, name))]
        changed = _digest(root) != before
        if not present:
            return Supply(kind, list(consumer), producer, UNVERIFIED, first["exit"], None,
                          False, changed, evidence={"producer_exit": made["exit"],
                                                    "producer_said": made["text"][:200]})
        # THE CONSUMER MUST ACCEPT IT. Run exactly the command that refused.
        second = _run(consumer, root)
        accepted = second["exit"] == 0
        status = (MANUFACTURED if accepted else FABRICATED)
        survived = all(os.path.exists(os.path.join(root, name)) for name in present)
        if accepted and not survived:
            status = UNVERIFIED
        return Supply(kind, list(consumer), producer, status, first["exit"],
                      second["exit"], True, changed,
                      evidence={"producer_exit": made["exit"],
                                "artifacts": present,
                                "consumer_said": second["text"][:200],
                                "artifacts_survived": survived})
    finally:
        shutil.rmtree(root, ignore_errors=True)


def supply_many(requests: Sequence[dict[str, Any]], *, program: str,
                flags: Sequence[str] | None = None,
                seed: Sequence[tuple[str, bytes]] = ()) -> dict[str, Any]:
    """The supply pass over `{kind, consumer}` requests, with its own accounting."""
    rows = [supply(str(item["kind"]), item["consumer"], program=program, flags=flags,
                   seed=seed) for item in requests]
    kinds: dict[str, int] = {}
    for row in rows:
        if row.status == MANUFACTURED:
            kinds[row.kind] = kinds.get(row.kind, 0) + 1
    return {"schema": SCHEMA, "rows": [r.as_dict() for r in rows],
            "requested": len(rows),
            "manufactured": sum(1 for r in rows if r.status == MANUFACTURED),
            "fabricated": sum(1 for r in rows if r.status == FABRICATED),
            "unverified": sum(1 for r in rows if r.status == UNVERIFIED),
            "no_producer": sum(1 for r in rows if r.status == NO_DECLARED_PRODUCER),
            "by_kind": kinds,
            "all_restored": all(r.restored for r in rows),
            "model_calls": 0, "network_calls": 0, "parameters": 0}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from canonical.runtime import tool_census_v1 as census_module
    from canonical.runtime import a_refusal_is_a_specification_v1 as refusal_module

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", default="openssl")
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    program = args.program
    contract = census_module.parse_contract(census_module._own_text(program), program)
    census = census_module.census(program, depth=2, max_ops=80)
    bound = [census_module.bind(op, contract=contract) for op in census["operations"]]
    committed = census_module.commit_check_many(
        bound, seed=census_module.trial_seeds(), preparation="PLAIN")
    refused = [row for row in committed["rows"] if row["verdict"] == "FAILED_NO_EFFECT"]

    # The kinds the refusals ask for, read from their own sentences.
    wanted: dict[str, dict[str, Any]] = {}
    for row in refused:
        clause = refusal_module.read_refusal(row.get("said") or "")
        if clause is None:
            continue
        if clause.form not in (refusal_module.UNLOADABLE, refusal_module.WITNESS):
            continue
        kind = clause.token.strip().lower()
        if kind not in wanted:
            wanted[kind] = {"kind": kind, "consumer": row["invoked_as"]}

    flags = [spelling for flag in (contract.get("flags") or ())
             for spelling in (flag.get("flags") or ())]
    result = supply_many(list(wanted.values()), program=program, flags=flags,
                         seed=census_module.trial_seeds())
    out = {"schema": SCHEMA, "program": program,
           "operations": len(bound), "doors": committed["counts"].get("CHANGES", 0),
           "refused": len(refused),
           "kinds_asked_for": sorted(wanted), **{k: v for k, v in result.items()
                                                 if k != "schema"},
           "seconds": round(time.perf_counter() - started, 2)}
    if args.receipt:
        with open(args.receipt, "w", encoding="utf-8") as handle:
            json.dump(out, handle, indent=2)
            handle.write("\n")
        print("wrote", args.receipt)
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
