#!/usr/bin/env python3
"""Does a row declare that it computes a stated command's answer, in process?

Two gates refuse a capability when the sentence states a settled command line
and the capability has no command slot:

* `live_brain_route_admission_v1.route_admission`, rule
  ``NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND``;
* `capability_selection_retrieval_v1.admit`, reason
  ``BINDING_REFUSED:NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND``.

Both exist for the same reason and that reason is sound: a capability chosen for
lexical overlap that cannot run the command answers nothing the sentence asked
for.  But a row can honestly answer a command's *question* without running it --
`file.line_count.v1` returns the number `wc -l` prints, from the same bytes, in
process.  Refusing that row for want of a command slot tells the caller a
sandbox is missing when the machine has the answer.

So the exemption is a DECLARATION, not a policy: the row names the command line
it computes, in the registry, and this module decides whether the sentence's own
argv is that command.  A row that declares nothing is refused exactly as before,
which is what keeps the blast radius at zero for the other rows.

Matching is positional and token-exact:

* the program name is never a placeholder, so a template cannot match a
  different program;
* a token that is ONLY a placeholder (``${path}``) is one of the row's own
  operands and may match any one token, in the declared position;
* a token that is a LITERAL followed by a placeholder (``$a ${line}``) matches a
  stated token that begins with that literal, so a row can declare that it
  computes one subcommand of a program without claiming the whole program.  The
  remainder must be non-empty: the literal alone is not an operand;
* every other token must equal the stated token, so a different flag or a
  different operand order does not match;
* the lengths must agree, so no prefix match across operands is possible.

The literal-prefix form exists because `file.line.appended.v1` appends a stated
line with ``sed -i '$a <line>'``: the value is part of the command line, and a
bare ``$``-placeholder at that position would have declared that the row computes
ANY ``sed -i`` -- including a substitution it does not perform.  A declaration
that is wider than the behaviour is a lie with a receipt.

The declaration is a claim about behaviour, and a claim is only worth what its
check is: `verify_file_facts_provenance_v1` compares the rows' answers against
the real `wc` and `stat` on a world it constructs, and records agreement.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

#: Registry key holding the declaration.
FIELD = "computes_command"


def _token_matches(expected: str, actual: str) -> bool:
    """One positional token of a declaration against the sentence's own.

    See the module docstring: exact literal, whole placeholder, or literal-then-
    placeholder.  Anything else is not this row's command.
    """
    if not expected:
        return False
    cut = expected.find("${")
    if cut < 0:
        return expected == actual
    if cut == 0:
        return True           # a whole placeholder takes any one operand
    prefix = expected[:cut]
    return actual.startswith(prefix) and len(actual) > len(prefix)


def matched_template(entry: Mapping[str, Any], argv: Any) -> Mapping[str, Any] | None:
    """Return the declaration (plus what matched) when this row computes ``argv``."""
    declaration = entry.get(FIELD)
    if not isinstance(declaration, Mapping):
        return None
    if not isinstance(argv, (list, tuple)) or isinstance(argv, str):
        return None
    stated = [str(token) for token in argv]
    templates = declaration.get("argvs")
    if not isinstance(templates, (list, tuple)):
        templates = [declaration.get("argv")]
    for raw in templates:
        if not isinstance(raw, (list, tuple)) or not raw:
            continue
        template = [str(token) for token in raw]
        if len(template) != len(stated):
            continue
        if not template[0] or template[0].startswith("$"):
            continue
        if all(_token_matches(expected, actual)
               for expected, actual in zip(template, stated)):
            return {**dict(declaration), "matched_argv": stated, "template": template}
    return None


def states_the_command_this_row_computes(goal: str, entry: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Convenience: extract the sentence's settled argv, then match it.

    Returns None both when the sentence states no single command and when the
    row does not declare it.  Callers use None to keep their existing refusal,
    which is why this returns evidence rather than a boolean.
    """
    try:
        from canonical.runtime import composer_route_v1 as composer_route
        argv: Sequence[str] | None = composer_route.extract_argv(str(goal or ""))
    except Exception:  # noqa: BLE001 - an unreadable sentence states nothing
        return None
    if argv is None:
        return None
    return matched_template(entry, argv)


__all__ = ["FIELD", "matched_template", "states_the_command_this_row_computes"]
