#!/usr/bin/env python3
"""Three more real machines, in the shape the tree already uses. Nothing else lives here.

WHY THIS FILE EXISTS
--------------------
`canonical/tools/instant_learning_in_a_new_environment_v1.py` already builds four real machines
(FILESYSTEM, GIT, TARBALL, SQLITE) with their own readers, and it is REUSED here, never rebuilt.
What it was not built for is the question this round asks: it exposes one goal shape per answer
(`PERSIST` / `REMOVE` / `REPLACE`) over a *set* of contents, so a goal is always one action deep
and a content is always the thing named.

Two consequences matter, and both are needed to test a slot-only template:

  1. **Order.** A one-deep set has no order to move, so `ORDER` can never be the frame a goal is
     about. `LIST` below has order, and `SORT` in `the_vocabulary_is_the_artifact_v1` has it too.
  2. **A role nobody wrote.** Every previous round bound the goal's literal to the content the
     probes were named after (`probe_new_content`), so an agent could pass by recognising the
     probe. `LIST` can be given a goal about a content **no atom of any machine ever writes**,
     so recognising the probe cannot help.

So: three machines in the same shape -- `read()`, `reset()`, atoms with opaque identifiers --
and no planner, no learner, no store. Those exist; a second copy would be a second thing to be
wrong.

WHAT IS REAL, AND WHAT IS NOT
-----------------------------
Real: `git`, `tar`, `gzip`, `sort`, `sh` over real directories. Every reading is the tool's own
output, never a log this code wrote for itself. Not real: no display exists in this sandbox, so
none of this is a GUI, and the instrument does not imply otherwise.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
from typing import Any, Callable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import instant_learning_in_a_new_environment_v1 as base  # noqa: E402

Machine = base.Machine
Atom = base.Atom
_run = base._run
_write_via_sh = base._write_via_sh

ALPHA = "alpha_one"
BETA = "beta_two"
GAMMA = "gamma_three"
DELTA = "delta_four"
#: a content no atom of any machine ever writes. A goal about it cannot be solved by
#: recognising a probe; only by carrying a relation that names no literal.
UNSEEN = "a_content_no_probe_ever_wrote"


def build_git2(root: pathlib.Path) -> Machine:
    """Commit history: the ORDER of the messages is a relation; `--amend` moves identity only."""

    def git(*argv: str) -> dict[str, Any]:
        return _run(("git", *argv), cwd=root)

    def reset() -> None:
        if (root / ".git").is_dir():
            shutil.rmtree(root / ".git")
        git("init", "-q")
        git("config", "user.email", "brain@example.invalid")
        git("config", "user.name", "brain")
        git("commit", "-q", "--allow-empty", "-m", ALPHA)
        git("commit", "-q", "--allow-empty", "-m", BETA)
        git("commit", "-q", "--allow-empty", "-m", GAMMA)

    def read() -> list[tuple[str, str]]:
        rows = []
        for line in git("log", "--format=%H%x09%s")["stdout"].splitlines():
            if "\t" in line:
                sha, message = line.split("\t", 1)
                rows.append((sha, message))
        return rows

    return Machine("GIT2", root, (
        Atom("G2_A1", ((("git", "commit", "--allow-empty", "-m", "{content}"), None),)),
        Atom("G2_A2", ((("git", "reset", "--hard", "HEAD~1"), None),)),
        Atom("G2_A3", ((("git", "commit", "--amend", "--allow-empty", "-m", "{content}"), None),)),
        Atom("G2_A4", ((("git", "log", "--oneline", "-n", "1"), None),)),
    ), read, reset)


def build_archive2(root: pathlib.Path) -> Machine:
    """Archive members: the member NAME is the identity, the member body is the content."""

    archive = root / "pack.tar"

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        for name, content in (("m_one", ALPHA), ("m_two", BETA), ("m_three", GAMMA)):
            (root / name).write_text(content, encoding="utf-8")
        _run(("tar", "-cf", str(archive), "m_one", "m_two", "m_three"), cwd=root)
        for name in ("m_one", "m_two", "m_three"):
            (root / name).unlink()

    def read() -> list[tuple[str, str]]:
        rows = []
        for name in _run(("tar", "-tf", str(archive)), cwd=root)["stdout"].split():
            body = _run(("tar", "-xOf", str(archive), name), cwd=root)
            rows.append((name, body["stdout"].strip()))
        return rows

    return Machine("ARCHIVE2", root, (
        Atom("AR_A1", ((_write_via_sh("{content}", "{name}"), None),
                       (("tar", "-rf", str(archive), "{name}"), None),
                       (("rm", "-f", "{name}"), None))),
        Atom("AR_A2", ((("tar", "--delete", "-f", str(archive), "{name}"), None),)),
        Atom("AR_A3", ((("tar", "-tf", str(archive)), None),)),
        Atom("AR_A4", ((("gzip", "-k", "-f", str(archive)), None),)),
    ), read, reset)


def build_list(root: pathlib.Path) -> Machine:
    """One text file read line by line. `sort` and `tac` move ORDER and nothing else; `LS_A5`
    appends a content no other machine holds, so a goal can be about a role nobody wrote."""

    lines = root / "lines.txt"

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        lines.write_text(f"{GAMMA}\n{ALPHA}\n{DELTA}\n{BETA}\n", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        if not lines.exists():
            return []
        return [(str(number), line) for number, line in
                enumerate(lines.read_text(encoding="utf-8", errors="replace").splitlines())]

    return Machine("LIST", root, (
        Atom("LS_A1", ((("sh", "-c", "sort -o lines.txt lines.txt"), None),)),
        Atom("LS_A2", ((("sh", "-c", "tac lines.txt > t && mv t lines.txt"), None),)),
        Atom("LS_A3", ((("sh", "-c", "head -n 2 lines.txt > t && mv t lines.txt"), None),)),
        Atom("LS_A4", ((("sh", "-c", "wc -l < lines.txt > /dev/null"), None),)),
        Atom("LS_A5", ((("sh", "-c", "printf '%s\\n' 'a_content_no_probe_ever_wrote' "
                                    ">> lines.txt"), None),)),
        # A decoy with a real effect the goal cannot want: appending a duplicate leaves the
        # multiset, the pairing and the cardinality of *distinct* contents... changed, but leaves
        # the goal "the last line is beta_two" false. It exists so that "some frame moved" is not
        # the same as "this atom achieves what the user accepted".
        Atom("LS_A6", ((("sh", "-c", "printf '%s\\n' 'gamma_three' >> lines.txt"), None),)),
        # max-length atom, so a sort that happened to move a frame still has to be *aimed*
        Atom("LS_A7", ((("sh", "-c", "cat lines.txt lines.txt > t && mv t lines.txt"), None),)),
    ), read, reset)




def build_journal(root: pathlib.Path) -> Machine:
    """Append-only log: `echo >> journal`. Appending is the ONLY verb this machine has, and two of
    its atoms append the SAME bytes, so changing the reading and moving the goal's frame stop
    being the same question. That is the machine the frame-blind control needs in order to lose
    for a real reason instead of a missing one."""

    journal = root / "journal.txt"

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        journal.write_text(f"{ALPHA}\n{BETA}\n{GAMMA}\n", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        if not journal.exists():
            return []
        return [(str(number), line) for number, line in
                enumerate(journal.read_text(encoding="utf-8", errors="replace").splitlines())]

    return Machine("JOURNAL", root, (
        Atom("JN_A1", ((("sh", "-c", "printf '%s\\n' 'alpha_one' >> journal.txt"), None),)),
        Atom("JN_A2", ((("sh", "-c", "printf '%s\\n' 'zulu_nine' >> journal.txt"), None),)),
        Atom("JN_A3", ((("sh", "-c", "printf '%s\\n' 'alpha_one' >> journal.txt"), None),)),
        Atom("JN_A4", ((("sh", "-c", "wc -l < journal.txt > /dev/null"), None),)),
    ), read, reset)


def build_vault(root: pathlib.Path) -> Machine:
    """Gzip a file, but two atoms compress different files with the SAME command shape, so the
    gzip timestamp is irrelevant and the gzip byte-identity of the corpus under 1.12.0-3 vs
    1.12.0-3 means 6 of 10 pair members still are."""

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        (root / "a.txt").write_text(ALPHA + "\n", encoding="utf-8")
        (root / "b.txt").write_text(BETA + "\n", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        rows = []
        for path in sorted(root.iterdir()):
            if path.is_file():
                rows.append((path.name, path.read_text(errors="replace").strip()[:40]))
        return rows

    return Machine("VAULT", root, (
        Atom("VT_A1", ((("gzip", "-k", "-f", "a.txt"), None),)),
        Atom("VAULT_A2", ((("gzip", "-k", "-f", "b.txt"), None),)),
        Atom("VAULT_A3", ((("sh", "-c", "gzip -d -f a.txt.gz 2>/dev/null || true"), None),)),
        Atom("VAULT_A4", ((("sh", "-c", "ls -1"), None),)),
    ), read, reset)


def build_scrambled(root: pathlib.Path) -> Machine:
    """A machine whose atom ROLES are deliberately permuted: the counterpart of the others.

    `A_CONTAST_IS_A_PROBE` rests on resolving an experiment by role -- `GIT_A4` means nothing on VAULT,
    but `A4` does, because every machine in this family fills slot A4 with the same kind of atom. If
    its 95.3% portability came from that convention rather than from the procedure itself, a machine
    that permutes its roles will collapse it.

    Here the atoms do the family's work in a PERMUTED order. It exists to falsify the round's own
    claim, so it is built to be as uncooperative as possible while remaining a real machine.
    """

    lines = root / "scrambled.txt"

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        lines.write_text("\n".join((ALPHA, BETA, GAMMA)) + "\n", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        if not lines.exists():
            return []
        body = lines.read_text(encoding="utf-8").splitlines()
        return [(str(index), content) for index, content in enumerate(body)]

    def write(*lines_to_write: str) -> dict[str, Any]:
        return _write_via_sh(str(lines), *lines_to_write)

    return Machine("SCRAMBLED", root, (
        # the roles are shifted by two: what is A3 elsewhere is A1 here, and so on
        Atom("SC_A1", ((("sort", "-o", str(lines), str(lines)), None),)),
        Atom("SC_A2", ((("tac", str(lines)), None), (("sort", "-o", str(lines)), None))),
        Atom("SC_A3", (((f"sh", "-c", f"printf '%s\\n' {DELTA} >> {lines}"), None),)),
        Atom("SC_A4", ((("head", "-n", "-1", str(lines)), None),
                       (("sort", "-o", str(lines)), None))),
    ), read, reset)


NEW_MACHINES: dict[str, Callable[[pathlib.Path], Machine]] = {
    "GIT2": build_git2,
    "ARCHIVE2": build_archive2,
    "LIST": build_list,
    "JOURNAL": build_journal,
    "VAULT": build_vault,
    # a deliberate counterpart: its roles do not line up with the rest of the family, so it is the
    # control for any claim that rests on role correspondence
    "SCRAMBLED": build_scrambled,
}
REUSED_MACHINES = dict(base.MACHINES)


def all_machines() -> dict[str, Callable[[pathlib.Path], Machine]]:
    merged = dict(REUSED_MACHINES)
    merged.update(NEW_MACHINES)
    return merged


def cell_args(state: Sequence[tuple[str, str]], state_class: str) -> dict[str, str]:
    """One cell of the (atom, state class) table.

    `TARGET_ABSENT`  the content named is one nobody holds, so the atom has to create it
    `TARGET_EXISTS`  the content named is already held, so the atom has to move or replace it

    The identity handed to `{name}` is read out of the reading, because an identity this code
    invented could not be used by a machine whose ids are hashes.
    """
    holder = next((ident for ident, content in state if content == ALPHA), None)
    if state_class == "TARGET_EXISTS" and holder:
        return {"content": ALPHA, "old": BETA, "name": holder, "target": BETA + "_copy"}
    return {"content": GAMMA, "old": ALPHA, "name": BETA + "_fresh", "target": GAMMA + "_copy"}


if __name__ == "__main__":  # a smoke test, not a measurement: the instrument is the measurement
    import tempfile

    for name, build in sorted(all_machines().items()):
        with tempfile.TemporaryDirectory() as room_dir:
            machine = build(pathlib.Path(room_dir))
            machine.reset()
            before = machine.read()
            print(f"{name:10s} rows={len(before)} first={before[0][1][:24]!r}")
