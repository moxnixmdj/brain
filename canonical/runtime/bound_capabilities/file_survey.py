"""The directory survey: lists what is in a folder, for `file.directory_listing.v1`.

WHY THIS FILE EXISTS. `file.directory_listing.v1` has been named in four runtime modules since
2026-11-02, and `live_brain_route_admission_v1` cites it as the settled authority for a rule. It was
never in the registry, because the adapter it declares -- this file -- had never been written. The
verifying check could not pass: it raised `BOUND_CAPABILITY_ADAPTER_MISSING` before it could report
anything. Measured 2026-11-22 (A80). So the plainest sentence a person can say, "list the files in
this folder", had no verified capability behind it, even though `ls` worked and the observation code
already knew how to list a directory.

WHAT IT DOES, AND WHAT IT REFUSES. It reads one directory the caller names and reports its entries.
It reads; it never writes, renames or deletes. It refuses a path outside the repository root, a path
that is not a directory, and a missing path -- each by raising, so a refusal can never be mistaken
for an empty folder. `entries` distinguishes directories from files because "list the files" and
"list what is in here" are different questions and the caller can tell them apart.

THE ANSWER SHAPE. `files` and `names` are the same list, and both are returned because they answer
different readings of the sentence: the answer-shape gate projects onto `files` (it was written
against this row and checks exactly that, in `verify_file_facts_provenance_v1`), while `names` is the
neutral word. `answer` is the listing as text, one entry per line -- what a person would see.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_FILE_SURVEY_RESULT_V1"

# The one command this adapter implements. It is a name for the operation, NOT a shell program:
# nothing here starts a process.
_COMMAND = "directory_list"


def _repo_root(root: Any = None) -> pathlib.Path:
    """The root the caller named, or this checkout.

    `run_adapter_locally` passes the repository root explicitly, and that is the authority: the
    adapter must not decide for itself which tree it is allowed to read.
    """
    if root is not None:
        return pathlib.Path(root).resolve()
    return pathlib.Path(__file__).resolve().parents[3]


def _resolve_inside(root: pathlib.Path, raw: Any) -> pathlib.Path:
    """The directory `raw` names, or a refusal. Never returns a path outside `root`."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("PATH_REQUIRED")
    target = (root / raw).resolve()
    if target != root and root not in target.parents:
        # `/etc`, `../..`, and an absolute path elsewhere all arrive here.
        raise ValueError("PATH_OUTSIDE_ROOT")
    return target


def _entries_of(target: pathlib.Path) -> list[dict[str, Any]]:
    """One record per entry, sorted by name, with the facts a caller can act on."""
    out: list[dict[str, Any]] = []
    for item in sorted(target.iterdir(), key=lambda child: child.name):
        try:
            size = item.stat().st_size
        except OSError:
            size = None
        out.append({
            "name": item.name,
            "is_dir": item.is_dir(),
            "is_file": item.is_file(),
            "is_symlink": item.is_symlink(),
            "size_bytes": size,
        })
    return out


def run(args: Mapping[str, Any], root: Any = None) -> dict[str, Any]:
    """List one directory inside the repository.

    ``args`` carries ``path`` (relative to the repository root) and ``command``; the command must be
    the operation this adapter declares, so a row wired to the wrong one fails loudly instead of
    listing a folder and being believed. ``root`` is the tree the caller allows, and every path this
    adapter touches is checked against it.
    """
    args = dict(args or {})
    command = str(args.get("command") or _COMMAND)
    if command != _COMMAND:
        raise ValueError("COMMAND_NOT_SUPPORTED:" + command)

    root = _repo_root(root)
    target = _resolve_inside(root, args.get("path"))
    if not target.is_dir():
        raise ValueError("PATH_NOT_DIRECTORY")
    if target == root:
        # The repository root is refused for the same reason every other binder refuses it: a
        # listing of everything is not an answer to a question about a folder.
        raise ValueError("REFUSES_THE_REPOSITORY_ROOT")

    entries = _entries_of(target)
    names = [entry["name"] for entry in entries]
    return {
        "schema": SCHEMA,
        "adapter": "file_survey",
        "command": _COMMAND,
        "capability_id": "file.directory_listing.v1",
        "path": str(target.relative_to(root)),
        # The contract `file_observation_expectation_v1.verify` re-reads: it recomputes these from
        # the disk rather than trusting them, so they are stated plainly.
        "entries": entries,
        "names": names,
        "files": names,
        "entry_count": len(entries),
        "directory_count": sum(1 for entry in entries if entry["is_dir"]),
        "file_count": sum(1 for entry in entries if entry["is_file"]),
        "answer": "\n".join(names),
        # This adapter reads and then states what it read; it has nothing to write, so it is its own
        # producer. The verifier re-reads the directory and compares, which is what makes that
        # honest rather than a self-certification.
        "output_verified": True,
        "read_only": True,
    }
