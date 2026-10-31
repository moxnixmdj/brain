"""A capability may not write its report over the file it was asked to read.

Measured 2026-10-29 on `main` e2d7981, 60 human software-engineering sentences
through ``live_brain_route_admission_v1.solve``:

    "Fix the ZeroDivisionError in <repo>/app/utils.py."
      -> FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN
      -> app/utils.py is now a tree-sitter parse report (14 lines of source lost)
    "Who last changed the function line_total in <repo>/app/service.py?"
      -> FAIL_CLOSED__NAMED_SOURCE_UNPARSEABLE
      -> app/service.py is now a symbol-index report (358 lines of JSON)

Both are deterministic (3/3).  The trigger is not the sentence: it is the ABSENCE
of a stated destination.  Every software-engineering row declares

    "output_path": "${input.output_path}", "source_root": "${input.source_root}"

so when the goal names no place to put a report, the binder has exactly one
stated path in hand -- the source -- and binds the report to it.  The adapter
then writes, verifies its own artifact, and reports success.

The repository already states the rule in the other direction ("a path the
sentence names as a DESTINATION is never a candidate SOURCE",
``goal_compiler._path_named_after_output_verb``).  This module is the dual, at
the one place every local adapter invocation passes through
(``live_brain_route_admission_v1.run_adapter_locally``), so it covers the door,
the composer, and every composed step without editing 125 registry rows or the
per-adapter ``_safe_output`` copies.

What may still write over a source: a capability that IS a source transformer.
``python.refactor.rename_parameter.v1`` exists to change the file it names, and
the check below reads that from the capability's own id rather than assuming it.
Nothing is invented: the vocabulary is the registry's own effect vocabulary,
already used as an admission gate by ``swe_typed_plan_v1._effect_consistent``.

Authority: NONE.  Credit: 0.  Model dependency: 0.  Incremental spend: $0.
"""
from __future__ import annotations

import pathlib
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_WRITE_AUTHORITY_V1"

# Slots whose value names where a result is put.  ``output_path`` is the one the
# software-engineering rows declare; the others are the same role under the
# spelling other rows use, so the rule is not keyed on one schema.
OUTPUT_SLOTS: tuple[str, ...] = (
    "output_path", "output", "out", "dest", "destination", "report_path", "result_path",
)

# Slots known to name something the capability will READ.  A directory here
# contains the files as well, which is how ``source_root`` admits ``utils.py``
# without naming it.
#
# This tuple is documentation, not the gate.  Measured on main 88bb18bb: it was
# the gate, and it was written from the rows someone happened to read, so it
# admitted nothing that a row spelled differently.  ``changed_paths`` is how
# ``code.impact.tree_sitter.testselect.v1`` states the files it analyses, and it
# is not here -- so the one destination the binder had in hand was the file it
# was asked to analyse, and a 272-byte Python module became a 1076-byte JSON
# impact report.  Across all 125 rows there are 122 argument names this list
# cannot name in advance (``diff_path`` x9, ``anchor_path`` x4, ``index_path``
# x3, ``worktree_path`` x4, ``json_path`` x11, ...).  Enumerating them is a race
# the guard always loses, so the rule no longer enumerates them: every argument
# that is not a destination is an input.  That is strictly fewer conditions than
# the list it replaces.
SOURCE_SLOTS: tuple[str, ...] = (
    "source_root", "source_path", "source", "input_path", "input", "module",
    "repo_path", "file_path", "test_paths", "test_path", "path",
)


def _input_values(args: Mapping[str, Any]) -> list[tuple[str, Any]]:
    """Every argument that is not a destination, read from the action itself.

    A destination slot is skipped because it is the thing being written; every
    other value is offered to the path test, which ignores anything that is not
    a single-line path-shaped string.  Nothing is guessed about what a slot is
    for -- the role is decided by whether it is written, not by its name.
    """
    values: list[tuple[str, Any]] = []
    for slot, value in args.items():
        if str(slot) in OUTPUT_SLOTS:
            continue
        if isinstance(value, (list, tuple, set)):
            values.extend((str(slot), item) for item in value)
        else:
            values.append((str(slot), value))
    return values

# Suffixes that are somebody's source.  A report is never written with one of
# these names by accident; when it is, the file it replaces is code.
SOURCE_SUFFIXES: tuple[str, ...] = (
    ".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs", ".go",
    ".java", ".kt", ".c", ".h", ".cc", ".cpp", ".hpp", ".rb", ".php", ".cs",
    ".swift", ".scala", ".sh", ".bash", ".pl", ".lua", ".ex", ".exs", ".sql",
)

# A capability whose own id says it transforms source may replace the file it
# names.  Read from the id, never asserted about particular rows.
_TRANSFORMERS: tuple[str, ...] = (
    "edit", "repair", "refactor", "rename", "patch", "apply", "fix", "rewrite",
    "transform", "migrate", "format", "generate", "scaffold", "synthes",
)


class WriteAuthorityViolation(RuntimeError):
    """The action was refused before it could destroy a file it was given."""


def _as_path(root: pathlib.Path, value: Any) -> pathlib.Path | None:
    if not isinstance(value, str) or not value.strip() or "\n" in value:
        return None
    raw = value.strip()
    candidate = pathlib.Path(raw)
    resolved = (root / candidate if not candidate.is_absolute() else candidate).resolve()
    return resolved


def _inside(child: pathlib.Path, parent: pathlib.Path) -> bool:
    return child == parent or parent in child.parents


def is_source_transformer(capability_id: str) -> bool:
    low = str(capability_id or "").lower()
    return any(token in low for token in _TRANSFORMERS)


def declares_no_source_write_authority(entry: Mapping[str, Any] | None) -> bool:
    """Does the row's OWN declaration say it will not write the source it was given?

    ``is_source_transformer`` above reads the id, and an id is a name: ``python.patch.search.
    test_guided.ast.v1`` contains "patch" and is therefore "a transformer", while its own registry
    row says, verbatim, *"Candidate-only: source bytes are restored after every trial and before
    return; no source write or promotion authority"*.  It is a PROPOSER.  When such a row is the
    terminal answer to "repair <src> so that <test> passes", the machine reports a verified
    candidate and the file is untouched -- measured 2026-10-31, the last FALSE row on the
    capability matrix.  The declaration decides, never the name.
    """
    text = " ".join(str(x) for x in ((entry or {}).get("limitations") or [])).lower()
    return ("no source write" in text or "no write or promotion" in text
            or "source bytes are restored" in text)


def cannot_perform_the_stated_change(goal: str, entry: Mapping[str, Any] | None,
                                     capability_id: str = "") -> str | None:
    """A reason when the sentence promises a change this row declares it cannot make.

    Both halves are read, never assumed: the sentence through the door's own reader of imperatives
    (``sentence_promises_a_change`` -- a question about a change is not a promise to make one), and
    the row through its own ``limitations``.  A plan for a question, and a reader for a question,
    are untouched.  Returned as a token so every caller refuses in the same words.
    """
    if not declares_no_source_write_authority(entry):
        return None
    from canonical.runtime import live_brain_route_admission_v1 as _door
    if not _door.sentence_promises_a_change(goal):
        return None
    return ("CANDIDATE_ONLY_ROW_DECLARES_NO_SOURCE_WRITE_AUTHORITY:"
            + str(capability_id or (entry or {}).get("capability_id")
                  or (entry or {}).get("id") or "UNNAMED"))


def violation(root: pathlib.Path, args: Mapping[str, Any], capability_id: str) -> str | None:
    """Return a refusal reason when this action would overwrite a file it reads.

    Four conditions, each READ from the action rather than assumed:
      1. some slot names a destination (``output_path`` and friends);
      2. that destination already exists -- a new file cannot destroy anything;
      3. it is source, by suffix, and / or it sits inside a path the action also
         hands the capability (a directory contains its files, which is how
         ``source_root`` admits ``utils.py`` without naming it) -- and "a path
         the action also hands the capability" is now READ as *every argument
         that is not a destination*, never from a list of slot names;
      4. the capability's own id does not say it transforms source.

    Anything else returns None, so every route that worked before this runs
    byte for byte as it did.
    """
    root = pathlib.Path(root).resolve()
    if is_source_transformer(capability_id):
        return None
    destinations: list[tuple[str, pathlib.Path]] = []
    for slot in OUTPUT_SLOTS:
        p = _as_path(root, args.get(slot))
        if p is not None:
            destinations.append((slot, p))
    if not destinations:
        return None
    sources: list[tuple[str, pathlib.Path]] = []
    for slot, item in _input_values(args):
        p = _as_path(root, item)
        if p is not None:
            sources.append((slot, p))
    for dest_slot, dest in destinations:
        if not dest.is_file():
            continue
        if dest.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        for source_slot, source in sources:
            if source == dest or (source.is_dir() and _inside(dest, source)):
                return ":".join((
                    "OUTPUT_OVERWRITES_A_STATED_SOURCE",
                    "%s=%s" % (dest_slot, dest.relative_to(root) if _inside(dest, root) else dest),
                    "read_as=%s" % source_slot,
                    "capability=%s" % str(capability_id or ""),
                ))
    return None


def check(root: pathlib.Path, args: Mapping[str, Any], capability_id: str) -> None:
    """Raise ``WriteAuthorityViolation`` when the action would destroy its own input."""
    reason = violation(root, args, capability_id)
    if reason:
        raise WriteAuthorityViolation(reason)


def check_report(root: pathlib.Path, destination: Any, inputs: Any) -> None:
    """Protect explicit report roles, even when the producer edits source.

    Unlike ``check``, this API is called only where the adapter KNOWS it writes
    a report, not transformed source. Compare filesystem identity as well as
    resolved names: hard links can share bytes without sharing a pathname.
    This preflight is not a lock or an OS sandbox; concurrent path replacement
    still requires isolated, owned workspaces.
    """
    root = pathlib.Path(root).resolve()
    dest = _as_path(root, str(destination))
    if dest is None:
        raise WriteAuthorityViolation("REPORT_DESTINATION_INVALID")
    for raw in inputs:
        source = _as_path(root, str(raw))
        if source is None:
            continue
        try:
            aliases = dest == source or (dest.exists() and source.exists()
                                         and dest.samefile(source))
        except OSError as exc:
            raise WriteAuthorityViolation("REPORT_IDENTITY_UNREADABLE") from exc
        if aliases:
            raise WriteAuthorityViolation("REPORT_OVERWRITES_INPUT:" + str(source))
