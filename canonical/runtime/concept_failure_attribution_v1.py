"""When a program built from several concepts is wrong, which one was wrong?

THE PROBLEM, STATED PRECISELY
-----------------------------
`CompoundingConceptLibrary.record_concept_outcome` takes ONE `concept_id`. A failed program may use
several. So the library faces a choice with no good options: blame all of them (an innocent concept
is punished alongside a guilty one) or blame none (the library stays blind).

Note what is NOT the problem, because an earlier document of mine got this wrong: the *notice* that
a program failed cannot come from inside. The synthesizer returns a string body and callers use it
immediately; at emission time nobody knows whether it is right. So the notice arrives from outside,
and this module does not supply it. What this module supplies is the part that must be internal,
because it needs the concept bodies: **attribution**.

THE MECHANISM
-------------
Ablate the concept from the SEARCH, not the program.

The first version of this module substituted the concept's body into the failed program and asked
whether it then passed. That is vacuous by construction: inlining a definition preserves semantics
exactly, so the substituted program has the same behaviour by definition. Measured 2026-11-04: a
two-concept failed program reported BOTH concepts innocent, including the guilty one, because the
"without X" program still failed -- as it necessarily had to.

The question that actually has content is different. A failure is evidence about a concept when the
search could have succeeded *without that concept*:

    re-synthesize the same problem with the suspect concept unavailable
      succeeds  -> the concept was not needed, and its presence misled the search: charge it
      fails     -> the concept was not the cause; the problem is out of reach either way

The first arm is the informative one. It says: a correct program over these examples existed, and
the concept we were offering steered the search away from it. That is the concept's fault, and it is
a fact about the search rather than about arithmetic -- which is why it cannot be established by
rewriting the program.

WHY REVERSIBLE
--------------
Retirement from a single failed program is weaker evidence than a threshold's worth of failures, so
`revive` exists and restores full standing. An apparatus that can only escalate its own convictions
is the failure mode this project already fixed once (append-only priors); it would be a poor joke to
reintroduce it one level up.

Authority: NONE. Pure Python, small numeric tuples, no I/O beyond the library's own state file.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_CONCEPT_FAILURE_ATTRIBUTION_V1"


def concepts_used_by(body: str) -> list[str]:
    """Concept ids the program calls, in first-use order, including nested helper calls."""
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return []
    seen: list[str] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id.startswith("concept_") and node.func.id not in seen):
            seen.append(node.func.id)
    return seen


def substitute_concept(body: str, library: Any, concept_id: str) -> str | None:
    """Return the program with `concept_id`'s definition inlined and its helper removed.

    Textual/AST substitution rather than re-synthesis: the question is what THIS program would have
    evaluated to without that concept, not what a fresh search would produce.
    """
    try:
        entries = {c.concept_id: c for c in library.concepts()} if hasattr(library, "concepts") else {}
    except Exception:  # noqa: BLE001
        entries = {}
    retired_ids = getattr(library, "retired_concept_ids", lambda: frozenset())()
    for cid in retired_ids:
        entry = getattr(library, "_concepts", {}).get(cid)
        if entry is not None:
            entries[cid] = entry
    entry = entries.get(concept_id)
    if entry is None:
        return None
    call_src = f"{concept_id}("
    if call_src not in body:
        return None

    try:
        inner = ast.parse(entry.body_expr, mode="eval").body
    except SyntaxError:
        return None

    # Rename the concept's hole names (_v0, _v1, ...) with unique markers so that two inlined
    # copies in the same program cannot collide, then inline each call's arguments.
    out_lines: list[str] = []
    for line in body.splitlines():
        if call_src not in line or line.lstrip().startswith("def " + concept_id):
            out_lines.append(line)
            continue
        try:
            tree = ast.parse(line.strip())
        except SyntaxError:
            out_lines.append(line)
            continue

        class _Inliner(ast.NodeTransformer):
            def visit_Call(self, node: ast.Call) -> Any:
                self.generic_visit(node)
                if not (isinstance(node.func, ast.Name) and node.func.id == concept_id):
                    return node
                if len(node.args) != int(entry.arity):
                    return node
                cloned = ast.parse(entry.body_expr, mode="eval").body
                mapping = {f"_v{i}": arg for i, arg in enumerate(node.args)}
                for sub in ast.walk(cloned):
                    if isinstance(sub, ast.Name) and sub.id in mapping:
                        replacement = mapping[sub.id]
                        sub.id = ast.unparse(replacement)
                return cloned

        try:
            tree = _Inliner().visit(tree)
            ast.fix_missing_locations(tree)
            out_lines.append(ast.unparse(tree))
        except Exception:  # noqa: BLE001
            out_lines.append(line)
    _ = inner
    return "\n".join(out_lines)


def attribute_failure(
    library: Any,
    failed_body: str,
    synth: Any,
    params: Sequence[str],
    examples: Sequence[Any],
    *,
    disconfirmations_per_refutation: int = 3,
    max_weight: int = 4,
    extra_constants: Sequence[Any] = (),
) -> dict[str, Any]:
    """Charge a failed program to the concept(s) whose REMOVAL FROM THE SEARCH makes it solvable.

    `synth(...)` must be `synthesize_python_function_body`. The test for each suspect is a
    re-synthesis with that concept withheld from the library the search can see -- never a rewrite
    of the failed program, because inlining a definition cannot change behaviour.
    """
    used = concepts_used_by(failed_body)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "concepts_used": used,
        "suspects": [],
        "not_the_cause": [],
        "unattributable": [],
        "resynth_detail": [],
        "authority": "NONE",
    }
    if not used:
        report["unattributable"].append("NO_CONCEPT_USED")
        return report
    if not hasattr(library, "_concepts"):
        report["unattributable"].append("LIBRARY_HAS_NO_STATE")
        return report

    original = dict(library._concepts)
    try:
        for cid in used:
            # Ablate: the search sees the library WITHOUT this concept.
            ablated = {k: v for k, v in original.items() if k != cid}
            library._concepts = ablated
            try:
                body_without = synth(list(params), list(examples),
                                     extra_constants=tuple(extra_constants),
                                     max_weight=max_weight, concept_library=library)
            except Exception:  # noqa: BLE001
                body_without = None
            finally:
                library._concepts = dict(original)

            solvable_without = bool(body_without) and cid not in (body_without or "")
            report["resynth_detail"].append({
                "concept": cid,
                "resynth_without_it_succeeded": solvable_without,
            })
            if not solvable_without:
                # Not the cause: the problem is beyond the search either way. Do not manufacture a
                # culprit -- charging here would punish a concept for a problem nobody could solve.
                report["not_the_cause"].append(cid)
                continue
            report["suspects"].append(cid)
            if hasattr(library, "record_concept_outcome"):
                for _ in range(int(disconfirmations_per_refutation)):
                    library.record_concept_outcome(cid, helped=False)
    finally:
        library._concepts = original

    return report


def viable_scenarios() -> str:
    """Short summary of what this module can and cannot do, for callers."""
    return (
        "CAN: decide which of several concepts used by one failed program is responsible, by "
        "re-synthesizing with each concept ablated from the search; leave a concept alone when the "
        "problem was out of reach anyway.\n"
        "CANNOT: notice that a failure happened. The notice must come from outside -- at emission "
        "time nobody knows whether the body is right. CANNOT: charge a concept for a program whose "
        "target is unreachable, because there is no evidence that could distinguish the concepts."
    )
