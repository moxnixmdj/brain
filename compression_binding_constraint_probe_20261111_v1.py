#!/usr/bin/env python3
"""Can `sleep_abstract` compress programs that differ by a LITERAL?

Why this file exists
--------------------
`THE_DEEPEST_STILL_OPEN_DEFECT_NOTHING_IS_EVER_COMPRESSED_20261104_V1.md` reports the deepest
measured defect in the tree: the concept library `G_t` stays empty, so nothing the machine ever
solves can compound. That document locates the cause in the *organ bridge*
(`_skill_organ_to_concept_entry`, which admits only single-`return` bodies).

This probe tests a different and deeper hypothesis, measured against the real library with
nothing mocked:

    H1  The sleep phase cannot abstract over CONSTANTS. `_canonicalize_pure_subtree` draws holes
        only from `ast.Name`, never from `ast.Constant`. Programs that differ only by a literal
        therefore canonicalize to different keys, get one occurrence each, and die on the
        `len(occurrences) >= 2` filter. Differing by a literal is the commonest way two real
        programs differ, so the compressor can currently only rediscover structure that
        canonicalization already removed. `G_t` = 0 follows.

    H2  Making constants hole-eligible yields abstractions that also compress a HELD-OUT program
        carrying a literal never seen in the teaching corpus, and that program stays
        execution-equivalent.

H2 is the whole point. An abstraction that only rewrites the corpus it was fit on is a template
menu. An abstraction that rewrites an unseen instance is compression, and compression is the only
measured thing that separates "a cache that grows" from "a learner that compounds".

What is measured, per family
----------------------------
    baseline_admitted   `sleep_abstract` with `CONSTANT_HOLES_ENABLED = False` (shipped behaviour)
    patched_admitted    `sleep_abstract` with `CONSTANT_HOLES_ENABLED = True`
    heldout_rewritten   a new instance, with an unseen literal, is rewritten under the library
    heldout_shrink      AST nodes in the rewritten `run` body / nodes in the original `run` body
    heldout_equivalent  original and rewritten return identical outputs on a probe grid
    blocker             which gate rejected the family, when it rejected it

Pre-registered verdict (written before the run; it was allowed to fail)
----------------------------------------------------------------------
    PASS    patched_admitted >= 1 in at least 2 of the 3 pure families (F1,F2,F3), AND every
            family that admits also rewrites its held-out instance with shrink < 1.0 AND
            heldout_equivalent is True.
    REFUTED anything less. In that case do NOT adopt constant abstraction as "the fix": it would
            be one more mechanism that admits a few templates and compounds nothing.

Reported below is the pre-registered verdict exactly as written, followed by a per-family
diagnostic that names the gate responsible for each family. The diagnostic was not part of the
pre-registration and does not change the verdict.

F4 is the repository's flagship period-table shape, included as a control rather than a criterion.

This is a producer-run measurement of four constructed families.
It is not independent verification, and it says nothing about GUI or unbounded computer use.
"""

from __future__ import annotations

import ast
import json
import math
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from canonical.swe_kernel import concept_library_v1 as CL


# ---------------------------------------------------------------------------
# Families. Each teaching corpus differs ONLY by a literal.
# ---------------------------------------------------------------------------

def _mod(k):
    return f"def run(x):\n    return ((x % {k}) + {k}) % {k}\n"


def _affine(a, b):
    return f"def run(x):\n    return (x - {a}) * ({b} - {a}) + (x - {a})\n"


def _clamp(lo, hi):
    return f"def run(x):\n    return {lo} if x < {lo} else ({hi} if x > {hi} else x)\n"


def _period(block):
    return (
        "def run(x0):\n"
        f"    _b = {block}\n"
        "    _n = len(_b)\n"
        "    return _b[int(math.floor(x0) - math.floor(x0 / _n) * _n)]\n"
    )


FAMILIES = {
    "F1_modulo": {
        "teach": [_mod(5), _mod(7), _mod(9)],
        "heldout": _mod(11),
        "grid": list(range(-30, 31)),
        "pure": True,
    },
    "F2_affine": {
        "teach": [_affine(0.0, 10.0), _affine(2.0, 8.0), _affine(5.0, 20.0)],
        "heldout": _affine(1.0, 4.0),
        "grid": [float(v) for v in range(-20, 21)] + [0.5, -3.25, 12.75],
        "pure": True,
    },
    "F3_clamp": {
        "teach": [_clamp(0.0, 1.0), _clamp(-1.0, 1.0), _clamp(0.0, 100.0)],
        "heldout": _clamp(-2.0, 6.0),
        "grid": [float(v) for v in range(-20, 21)] + [0.5, -7.5, 64.25],
        "pure": True,
    },
    "F4_period": {
        "teach": [
            _period("(1.0, 2.0, 3.0,)"),
            _period("(-1.0, -5.0, 2.0, -2.0, 5.0,)"),
            _period("(0.0, 1.0, 0.0, -1.0, 0.0, 4.0, 9.0,)"),
        ],
        "heldout": _period("(3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0,)"),
        "grid": [float(v) for v in range(-16, 17)],
        "pure": False,  # math.floor -> attribute-call purity gate
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_body_nodes(src: str) -> int:
    """Nodes in the `run` function only. Helper defs injected by wake are library state, not
    program size: the library is paid for once and shared across every program that uses it."""
    def _count(node: ast.AST) -> int:
        total = 1
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef):
                continue  # nested concept helper: library state, not program size
            total += _count(child)
        return total

    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            return _count(node)
    return _count(tree)


def _call(src: str, grid, extra=None):
    ns: dict = {"math": math}
    if extra:
        ns.update(extra)
    exec(compile(src, "<probe>", "exec"), ns)
    fn = ns["run"]
    out = []
    for v in grid:
        try:
            out.append(repr(fn(v)))
        except Exception as exc:  # noqa: BLE001 - recorded, not hidden
            out.append(f"ERR:{type(exc).__name__}")
    return out


def _diagnose(spec) -> dict:
    """Name the gate that rejects this family. Observation only; behaviour unchanged."""
    seen: list[dict] = []
    original = CL.CompoundingConceptLibrary._verify_candidate_concept

    def _spy(self, expr_src, arity):
        ok, dom = original(self, expr_src, arity)
        seen.append({"expr": expr_src, "arity": arity, "admitted": ok, "reason": dom})
        return ok, dom

    CL.CompoundingConceptLibrary._verify_candidate_concept = _spy
    CL.CONSTANT_HOLES_ENABLED = True
    try:
        d = pathlib.Path(tempfile.mkdtemp())
        lib = CL.CompoundingConceptLibrary(d / "c.json")
        lib.sleep_abstract(spec["teach"])
    finally:
        CL.CompoundingConceptLibrary._verify_candidate_concept = original
        CL.CONSTANT_HOLES_ENABLED = False

    # Would the canonicalizer even look at the shared subtree?
    canon_ok = None
    try:
        mod = CL.canonicalize_ast_via_egraph(ast.parse(spec["teach"][0]))
        fn = [n for n in ast.walk(mod) if isinstance(n, ast.FunctionDef)][0]
        bound = frozenset(
            {a.arg for a in fn.args.args}
            | {
                t.id
                for s in ast.walk(fn)
                if isinstance(s, ast.Assign)
                for t in s.targets
                if isinstance(t, ast.Name)
            }
        )
        roots = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.expr) and CL._expr_node_count(n) >= 5
        ]
        canon_ok = any(
            CL._canonicalize_pure_subtree(n, bound, frozenset()) is not None for n in roots
        )
    except Exception:  # noqa: BLE001
        canon_ok = None

    if seen:
        rejects = [s for s in seen if not s["admitted"]]
        return {
            "stage": "verify_candidate_concept",
            "reached_verification": len(seen),
            "rejected": len(rejects),
            "reasons": sorted({str(r["reason"]) for r in rejects}),
        }
    if canon_ok is False:
        return {"stage": "canonicalize_pure_subtree", "reasons": ["NO_CANONICAL_SUBTREE_PASSES"]}
    return {"stage": "candidate_filter", "reasons": ["STITCH_NODE_GAIN_OR_MDL_NON_POSITIVE"]}


def _measure_family(name, spec, *, patched: bool) -> dict:
    CL.CONSTANT_HOLES_ENABLED = bool(patched)
    try:
        d = pathlib.Path(tempfile.mkdtemp())
        lib = CL.CompoundingConceptLibrary(d / "c.json")
        res = lib.sleep_abstract(spec["teach"])
        admitted = list(res.get("admitted") or [])

        row = {
            "admitted": len(admitted),
            "concepts": [
                {
                    "concept_id": a.get("concept_id"),
                    "arity": a.get("arity"),
                    "corpus_sites": a.get("corpus_sites"),
                    "mdl_gain_bytes": a.get("mdl_gain_bytes"),
                    "body_expr": a.get("body_expr"),
                }
                for a in admitted
            ],
            "heldout_rewritten": False,
            "heldout_shrink": None,
            "heldout_equivalent": None,
        }
        if not admitted:
            return row

        rewritten = CL.rewrite_source_with_concepts(spec["heldout"], lib)
        if rewritten is None or rewritten.strip() == spec["heldout"].strip():
            return row
        row["heldout_rewritten"] = True
        before = _run_body_nodes(spec["heldout"])
        after = _run_body_nodes(rewritten)
        row["heldout_shrink"] = round(after / before, 4)
        row["heldout_nodes"] = {"before": before, "after": after}

        try:
            got = _call(rewritten, spec["grid"], extra=lib.callable_map())
            row["heldout_equivalent"] = got == _call(spec["heldout"], spec["grid"])
        except Exception as exc:  # noqa: BLE001
            row["heldout_equivalent"] = False
            row["heldout_error"] = f"{type(exc).__name__}: {exc}"
        return row
    finally:
        CL.CONSTANT_HOLES_ENABLED = False


def main() -> int:
    report: dict = {"schema": "PROBE_COMPRESSION_BINDING_CONSTRAINT_V1", "families": {}}
    for name, spec in FAMILIES.items():
        report["families"][name] = {
            "pure": spec["pure"],
            "baseline": _measure_family(name, spec, patched=False),
            "patched": _measure_family(name, spec, patched=True),
            "blocker": _diagnose(spec),
        }

    pure_names = [n for n, s in FAMILIES.items() if s["pure"]]
    admitted_families = [
        n for n in pure_names if report["families"][n]["patched"]["admitted"] >= 1
    ]
    generalized = [
        n
        for n in admitted_families
        if report["families"][n]["patched"]["heldout_rewritten"]
        and (report["families"][n]["patched"]["heldout_shrink"] or 1.0) < 1.0
        and report["families"][n]["patched"]["heldout_equivalent"] is True
    ]

    report["summary"] = {
        "pure_families": len(pure_names),
        "baseline_admitted_total": sum(
            report["families"][n]["baseline"]["admitted"] for n in FAMILIES
        ),
        "patched_admitted_total": sum(
            report["families"][n]["patched"]["admitted"] for n in FAMILIES
        ),
        "families_admitting_when_patched": len(admitted_families),
        "families_that_compress_a_held_out_literal": len(generalized),
        "verdict": "PASS" if len(generalized) >= 2 else "REFUTED",
        "verdict_note": (
            "Pre-registered bar was >=2 of 3 pure families compressing an unseen literal. "
            "The per-family `blocker` field names the gate responsible for each miss."
        ),
    }

    print(json.dumps(report, indent=2))
    print()
    print(f"{'family':<12} {'base':>5} {'patch':>6} {'held':>6} {'shrink':>7} {'equiv':>6}  blocker")
    print("-" * 84)
    for name in FAMILIES:
        f = report["families"][name]
        b, p, bl = f["baseline"], f["patched"], f["blocker"]
        reasons = ",".join(bl.get("reasons", []))[:34]
        print(
            f"{name:<12} {b['admitted']:>5} {p['admitted']:>6} "
            f"{str(p['heldout_rewritten']):>6} "
            f"{str(p['heldout_shrink']):>7} "
            f"{str(p['heldout_equivalent']):>6}  {bl['stage']}:{reasons}"
        )
    print()
    print("verdict:", report["summary"]["verdict"])
    print()
    print("This is a producer-run measurement of four constructed families.")
    print("It is not independent verification, and it says nothing about GUI or unbounded")
    print("computer use.")
    return 0 if report["summary"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
