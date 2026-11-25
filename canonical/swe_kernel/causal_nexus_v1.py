#!/usr/bin/env python3
"""Causal Nexus: expected-value abduction, single-site counterfactual blame, lens synthesis,
statement-level tree-rewrite morphisms, negative-space invariants, and boundary invariance fuzzing.

THE FIVE MOVES, AND THE MEASURED WALL EACH ONE REMOVES
------------------------------------------------------
The 2026-11-24 blind run (`AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V1.json`)
repaired 8 of 13 unseen OSS commits and left five open. The open five were not open for want of
candidates; they were open for want of a *value*:

  click@05f6fd0   `get_help_record` produced `None`, the test wanted `('SRC', '')`
  click@fc518e4   interrupt handling during abort reporting
  click@c53d373   prompt/abort interaction
  pyjwt@af8181c   "Invalid crypto padding" on a padded segment
  cJSON@9d1b229   allocator-guard memory defect under ASan

Every one of those failures *publishes the value it wanted* in its own assertion line, and none of
them lies inside any fixed mutation grammar. That is the whole thesis of this module. A test failure
is not just a signal that a site is wrong; it is a partially specified specification of what the
program must produce.

1. EXPECTED-VALUE ABDUCTION (`extract_value_obligations`).
   pytest prints `assert <actual> == <expected>`. The right-hand side is a witness of the missing
   value. We parse it, accept only self-contained literals (no names, no calls, no attribute access,
   so nothing can be laundered in), and treat it as the *goal residual* for the rest of the pipeline.

2. SINGLE-SITE COUNTERFACTUAL BLAME (`angelic_nexus_blame`).
   For each suspect site we *force* the expected literal at that site in an isolated `os.link` CoW
   clone in `/dev/shm` and re-run only the failing tests. A site whose forced value makes every
   failing test pass is a proven causal nexus for that failure: not a suspicion score, not a
   heuristic ranking, one executed counterfactual. This is Angelic Debugging (ICSE 2011) generalized
   from boolean conditions to arbitrary expressions, and it is cheap because the run is a few
   hundred milliseconds in a clone rather than a search over programs.

3. NEXUS REPAIR SYNTHESIS (`synthesize_nexus_repairs`).
   The witness says *which value* is missing; the synthesis step says *which expression owes it*.
   Candidate families are the ones that are total, one-line, and general:
       (orig or E)                falsy-to-default fallback
       (E if not orig else orig)  same, spelled as a conditional
       (E if orig is None else orig)  nullity fallback
       orig.translate(TABLE)      codec / byte-table lens (see 4)
   A bare literal is never emitted, so the repair cannot be a test-literal launder; the fallback
   only fires where the original produced a falsy value.

4. BIDIRECTIONAL LENS / TRANSDUCER INFERENCE (`infer_transducer`, `lens_expression`).
   When the observed and wanted values are strings or bytes of equal length, the missing mechanism
   is a per-position mapping, not a program. `infer_transducer` fits the minimal consistent
   `char -> char` table and `lens_expression` compiles it into `str.translate` / `bytes.translate`,
   which is invertible by construction when the table is a bijection, and is reported as
   non-invertible when it is not. That one table cracks a whole class of codec, escaping, and
   control-byte bugs that forward enumeration cannot reach.

5. STATEMENT-LEVEL TREE-REWRITE MORPHISMS (`SkillStoreV2`) AND NEGATIVE-SPACE INVARIANTS
   (`NegativeInvariantStore`).
   The 2026-11-24 ablation's own finding: multi-statement fixes do not crystallize, so
   `learned_skill_id` stayed `None`. Expression-level anti-unification cannot represent
   "delete a guard and wrap the tuple element in a fallback", because that is a *tree* difference,
   not an expression difference. `SkillStoreV2` anti-unifies statement lists into a shared pattern
   plus two substitutions, stores the pair as an inspectable JSON morphism with provenance and a
   staleness fingerprint, and applies it to a different file by matching the pattern and
   instantiating the replacement. Every morphism is `O(1)`-deletable and carries `refutations`, so a
   law that ever produces a regression is permanently narrowed instead of silently retried.
   `NegativeInvariantStore` is the complement: a refuted patch shape becomes a first-class invariant
   that filters the search space *before* compilation, so a dead end is paid for once and never again.

6. BOUNDARY INVARIANCE FUZZING (`differential_boundary_scan`).
   Before a patch is accepted we re-execute the before/after functions over a boundary corpus
   (`None, 0, -0.0, '', b'', [], (), {}, 0-length, 1-char, huge, control bytes`) and require that
   every divergence is one the obligation predicted. This is what stops "green suite, broken
   contract" acceptance: the divergence set must be a subset of the inputs where the original was
   falsy or null.

WHAT IS NOT CLAIMED
-------------------
* A forced value that passes is a fact about the failure, not a proof about the program. Acceptance
  always comes from the project's own suite, run on a clean clone with the answer key absent.
* `infer_transducer` reports `None` when the pairs are inconsistent; it never guesses.
* Statement-level morphisms are Python-only in this version. The C/C++/JS path still uses the
  expression-level UIR laws; that limitation is measured and reported, not papered over.
* No world facts are stored. Every entry is a *rewrite*, with the witness instance retained so it can
  be replayed, refuted, or deleted.

Authority: NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Network calls: 0. Parameters: 0.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
from dataclasses import dataclass, field
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import textwrap
import time
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import semantic_causal_engine_v1 as scm  # noqa: E402

SCHEMA = "BRAIN_CAUSAL_NEXUS_V1"
SKILL_STORE_SCHEMA = "BRAIN_TREE_REWRITE_MORPHISM_STORE_V1"
INVARIANT_STORE_SCHEMA = "BRAIN_NEGATIVE_INVARIANT_STORE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

MAX_LITERAL_CHARS = 240
MAX_LITERAL_NODES = 24


# ================================================================================================== #
# 1. Expected-value abduction: the failing assertion's own right-hand side is the goal residual.
# ================================================================================================== #

@dataclass(frozen=True)
class ValueObligation:
    """One `actual == expected` pair published by a failing test, with the node it came from."""
    node_id: str
    actual_text: str
    expected_text: str
    expected_value: Any
    op: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "actual_text": self.actual_text,
            "expected_text": self.expected_text,
            "expected_repr": repr(self.expected_value)[:MAX_LITERAL_CHARS],
            "op": self.op,
        }


_ASSERT_RE = re.compile(
    r"(?:AssertionError|assert)\s*:?\s*(?P<left>.+?)\s*(?P<op>==|!=|\bis\b|\bis not\b)\s*(?P<right>.+?)\s*$"
)
_DIFF_RE = re.compile(r"^(?P<left>.+?)\s*(?P<op>==|!=)\s*(?P<right>.+)$")


def _literal_value(text: str) -> Any:
    """Parse `text` only if it is a self-contained literal; refuse names, calls, attributes.

    Refusing non-literals is the anti-laundering gate: a name would let the test's own variables
    enter the repair, and a call would let the test's own helpers become program text.
    """
    t = text.strip()
    if not t or len(t) > MAX_LITERAL_CHARS:
        return _REFUSED
    if t in {"True", "False", "None", "Ellipsis"}:
        return {"True": True, "False": False, "None": None, "Ellipsis": Ellipsis}[t]
    if t.count("(") + t.count("[") + t.count("{") > MAX_LITERAL_NODES:
        return _REFUSED
    try:
        node = ast.parse(t, mode="eval").body
    except SyntaxError:
        return _REFUSED
    allowed = (
        ast.Constant, ast.Tuple, ast.List, ast.Set, ast.Dict, ast.UnaryOp, ast.USub, ast.UAdd,
        ast.Load, ast.expr_context,
    )
    for sub in ast.walk(node):
        if not isinstance(sub, allowed):
            return _REFUSED
        if isinstance(sub, ast.Constant) and isinstance(sub.value, (bytes, str)) and len(sub.value) > 4096:
            return _REFUSED
    try:
        return ast.literal_eval(node)
    except Exception:
        return _REFUSED


class _Refused:
    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return "<REFUSED>"


_REFUSED = _Refused()


def _current_test_node(lines: Sequence[str], idx: int) -> str:
    """Walk upward for the nearest `tests/...::test_...` marker that pytest prints."""
    for j in range(min(idx, len(lines) - 1), -1, -1):
        line = lines[j]
        m = re.search(r"((?:[\w./-]+/)?tests?/[\w./-]+\.py)::([\w\[\]\-.]+)", line)
        if m:
            return f"{m.group(1)}::{m.group(2)}"
        m2 = re.search(r"^_+ ([\w\[\]\-.]+) _+$", line.strip())
        if m2:
            return m2.group(1)
    return ""


def extract_value_obligations(failure_text: str, *, limit: int = 24) -> list[ValueObligation]:
    """Mine `(actual, expected)` pairs from a failing pytest transcript.

    Only the *expected* side is trusted, and only when it is a literal. `actual` is retained as
    evidence because it is what the current program produces at that point.
    """
    out: list[ValueObligation] = []
    seen: set[tuple[str, str]] = set()
    lines = failure_text.splitlines()
    for i, raw in enumerate(lines):
        line = raw.strip()
        if len(line) > 400 or "==" not in line and "!=" not in line and " is " not in line:
            continue
        if line.startswith(("#", ">>>", "...", "PASSED")) or ("assert" not in line and "!=" not in line):
            continue
        m = _ASSERT_RE.search(line) or _DIFF_RE.search(line.split("AssertionError:")[-1].strip())
        if not m:
            continue
        left = re.sub(r"^assert\s+", "", m.group("left").strip()).strip().rstrip(",")
        right = m.group("right").strip().rstrip(",")
        op = " ".join(m.group("op").split())
        if not right:
            continue
        val = _literal_value(right)
        if val is _REFUSED:
            val_l = _literal_value(left)
            if val_l is _REFUSED:
                continue
            left, right, val = right, left, val_l
        if val is _REFUSED or val is None:
            # `None` as the *expected* value carries no goal residual (it is what a missing
            # implementation already produces); only non-None expectations specify anything.
            continue
        node_for_key = _current_test_node(lines, i)
        # Two renderings of the same assertion (traceback line and summary line) are ONE obligation.
        # Support for a data-shaped value must therefore be counted over distinct test nodes, or a
        # single failing test would appear to corroborate itself.
        key = (node_for_key or left[:60], repr(val)[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(
            ValueObligation(
                node_id=_current_test_node(lines, i),
                actual_text=left[:200],
                expected_text=right[:200],
                expected_value=val,
                op=op,
            )
        )
        if len(out) >= limit:
            break
    return out


def literal_source(value: Any) -> str:
    """Emit a value as Python source, refusing anything that is not a literal."""
    src = repr(value)
    if len(src) > MAX_LITERAL_CHARS:
        raise ValueError("literal too large to emit")
    if _literal_value(src) is _REFUSED:
        raise ValueError("value is not a literal")
    return src


# ================================================================================================== #
# 2. Single-site counterfactual blame: force the expected value, see whether the failures close.
# ================================================================================================== #

@dataclass(frozen=True)
class NexusWitness:
    """A site + forced value that provably closes every failing test on its own."""
    site: scm.CausalSite
    forced_source: str
    forced_value_repr: str
    remaining_failures: int
    elapsed_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "rel_path": self.site.rel_path,
            "func_name": self.site.func_name,
            "kind": self.site.kind,
            "start_line": self.site.start_line,
            "site_text": self.site.source_text[:200],
            "forced_source": self.forced_source[:200],
            "forced_value_repr": self.forced_value_repr[:200],
            "remaining_failures": self.remaining_failures,
            "elapsed_ms": self.elapsed_ms,
        }


_FORCED_KINDS = ("return_expr", "guard", "assign_rhs")


def _forced_site_source(site: scm.CausalSite, value_src: str) -> str | None:
    """Rewrite one site so its value is a literal, in a form valid at that site's grammar position."""
    if site.kind == "guard":
        # The guard's *value* is its truthiness; forcing the expected literal is meaningful only
        # for booleans, which the expression-level path already covers.
        return None
    if site.kind == "return_expr":
        return value_src
    if site.kind == "assign_rhs":
        return value_src
    return None


def angelic_nexus_blame(
    project_root: pathlib.Path | str,
    sites: Sequence[scm.CausalSite],
    failure_text: str,
    focused_cmd: Sequence[str],
    *,
    obligations: Sequence[ValueObligation] | None = None,
    max_sites: int = 10,
    per_probe_timeout_s: float = 8.0,
) -> list[NexusWitness]:
    """Prove causal sites one executed counterfactual at a time.

    Each probe forces one literal at one site in its own CoW clone and runs only the failing
    tests. Cost is `O(sites x obligations)` subprocess runs of the *focused* suite, which is
    the cheapest complete experiment available: no candidate program is synthesized here.
    """
    root = pathlib.Path(project_root).resolve()
    obls = list(obligations if obligations is not None else extract_value_obligations(failure_text))
    if not obls:
        return []
    raw_cache: dict[str, bytes] = {}

    def _raw(rel: str) -> bytes:
        if rel not in raw_cache:
            raw_cache[rel] = (root / rel).read_bytes()
        return raw_cache[rel]

    witnesses: list[NexusWitness] = []
    probed = 0
    for site in sites[:max_sites]:
        if site.kind not in _FORCED_KINDS or site.language not in ("python", "javascript", "typescript"):
            continue
        for obl in obls[:6]:
            forced = _forced_site_source(site, _safe_emit(site, obl.expected_value))
            if forced is None:
                continue
            probed += 1
            t0 = time.perf_counter_ns()
            orig = _raw(site.rel_path)
            patched = scm._apply_site_patch(orig, site, forced)  # noqa: SLF001
            if not scm._syntactically_valid(patched, site.language, orig):  # noqa: SLF001
                continue
            ok, _rc, out = scm._run_suite_in_scratch(  # noqa: SLF001
                root, focused_cmd, {site.rel_path: patched}, timeout_s=per_probe_timeout_s
            )
            if ok:
                witnesses.append(
                    NexusWitness(
                        site=site,
                        forced_source=forced,
                        forced_value_repr=repr(obl.expected_value)[:MAX_LITERAL_CHARS],
                        remaining_failures=0,
                        elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                    )
                )
                return witnesses  # one proven nexus is enough; never keep spending
            if probed >= 24:
                return witnesses
    return witnesses


def _safe_emit(site: scm.CausalSite, value: Any) -> str:
    try:
        return literal_source(value)
    except ValueError:
        return repr(value)[:MAX_LITERAL_CHARS]


# ================================================================================================== #
# 3. Lens / transducer inference and compilation
# ================================================================================================== #

@dataclass(frozen=True)
class TransducerFit:
    """A minimal consistent mapping between observed and wanted values.

    `mode == "position"` is a per-character transliteration (equal-length pairs, compiled to
    `str.translate` / `bytes.translate`). `mode == "token"` is a multi-character substitution
    table (unequal lengths, compiled to a longest-first `.replace` chain). Both are *invertible or
    explicitly reported as not*, and both are fit from observations only -- never guessed.
    """
    table: tuple[tuple[str, str], ...]
    alphabet: str
    invertible: bool
    coverage: int
    mode: str = "position"

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": [[a, b] for a, b in self.table],
            "alphabet": self.alphabet,
            "invertible": self.invertible,
            "coverage": self.coverage,
            "mode": self.mode,
        }


def _as_text_pair(observed: Any, wanted: Any) -> tuple[str, str, str] | None:
    if isinstance(observed, bytes) and isinstance(wanted, bytes):
        return observed.decode("latin-1"), wanted.decode("latin-1"), "bytes"
    if isinstance(observed, str) and isinstance(wanted, str):
        return observed, wanted, "str"
    return None


def infer_transducer(pairs: Iterable[tuple[Any, Any]]) -> TransducerFit | None:
    """Fit the minimal consistent table that maps every observed value onto its wanted value.

    Refuses when the pairs disagree, when nothing differs, or when the values are not strings/bytes.
    """
    items = list(pairs)
    if not items:
        return None
    parsed = [_as_text_pair(o, w) for o, w in items]
    if any(p is None for p in parsed):
        return None
    parsed = [p for p in parsed if p is not None]  # type: ignore[misc]
    identity = all(o == w for o, w, _ in parsed)
    if identity:
        return None

    if all(len(o) == len(w) for o, w, _ in parsed):
        mapping: dict[str, str] = {}
        alphabet: set[str] = set()
        for o, w, _ in parsed:
            for a, b in zip(o, w):
                alphabet.add(a)
                if a in mapping and mapping[a] != b:
                    return None
                mapping[a] = b
        return TransducerFit(
            table=tuple(sorted(mapping.items())),
            alphabet="".join(sorted(alphabet)),
            invertible=len(set(mapping.values())) == len(mapping),
            coverage=len(parsed),
            mode="position",
        )

    # Token mode: whole-value substitutions. Consistent by construction (one entry per observed
    # value); ambiguity across overlapping observations is resolved longest-first and reported.
    table: dict[str, str] = {}
    for o, w, _ in parsed:
        if o in table and table[o] != w:
            return None
        if o:
            table[o] = w
    if not table:
        return None
    ordered = sorted(table.items(), key=lambda kv: (-len(kv[0]), kv[0]))
    invertible = len({b for _, b in ordered}) == len(ordered)
    return TransducerFit(
        table=tuple(ordered),
        alphabet="".join(sorted({c for o, _w, _k in parsed for c in o})),
        invertible=invertible,
        coverage=len(parsed),
        mode="token",
    )


def _encode_literal(text: str, value_kind: str) -> str:
    return repr(text.encode("latin-1")) if value_kind == "bytes" else repr(text)


def lens_expression(var_name: str, fit: TransducerFit, *, value_kind: str = "str") -> str:
    """Compile a fitted table into one self-contained stdlib expression (no helper, no import)."""
    if fit.mode == "position":
        if value_kind == "bytes":
            items = ", ".join(
                f"{a.encode('latin-1')!r}: {b.encode('latin-1')!r}" for a, b in fit.table
            )
            return f"{var_name}.translate({{{items}}})"
        items = ", ".join(f"{ord(a)}: {ord(b)}" for a, b in fit.table)
        return f"{var_name}.translate({{{items}}})"
    expr = var_name
    for a, b in fit.table:
        expr = f"{expr}.replace({_encode_literal(a, value_kind)}, {_encode_literal(b, value_kind)})"
    return f"({expr})"


def invert_lens(fit: TransducerFit, var_name: str = "v", *, value_kind: str = "str") -> str | None:
    """The backward half of the lens, or `None` when the table is not invertible."""
    if not fit.invertible:
        return None
    backward = TransducerFit(
        table=tuple((b, a) for a, b in fit.table),
        alphabet=fit.alphabet,
        invertible=True,
        coverage=fit.coverage,
        mode=fit.mode,
    )
    return lens_expression(var_name, backward, value_kind=value_kind)


# ================================================================================================== #
# 4. Nexus repair synthesis: which expression owes the proven value?
# ================================================================================================== #

_FALLBACK_TEMPLATES = (
    ("NEXUS_FALSY_FALLBACK", "({orig} or {exp})"),
    ("NEXUS_CONDITIONAL_FALLBACK", "({exp} if not {orig} else {orig})"),
    ("NEXUS_NULLITY_FALLBACK", "({exp} if {orig} is None else {orig})"),
)


_CANONICAL_SCALARS = (0, 1, -1, True, False, 0.0, -1.0)


def is_canonical_default(value: Any) -> bool:
    """True for absence/identity values that carry no test-specific data.

    `()`, `''`, `b''`, `[]`, `{}`, `set()`, `0`, `1`, `-1`, `0.0`, `True`, `False` and shallow
    containers of those are the values a *total function* returns when it has nothing: they are
    part of the language's surface, not part of the test's data. Anything else (a metavar such as
    `'SRC'`, a one-character flag, a payload, a fixture id) is test data; the only way it may enter
    a repair is through `frame_substituted_source`, which proves the site itself produced it.
    """
    if value is None:
        return True
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)) and value in _CANONICAL_SCALARS:
        return True
    if isinstance(value, (str, bytes)) and value in ("", b""):
        return True
    if isinstance(value, (tuple, list, set, frozenset)):
        return all(is_canonical_default(v) for v in value)
    if isinstance(value, dict):
        return all(is_canonical_default(v) for v in value.values())
    return False


def data_literal_gate(value: Any, *, supporting_obligations: int = 1) -> tuple[bool, str]:
    """Admission test for a forced value as a *repair source* (not as evidence).

    Two independent tests demanding the same value at the same site is a specification; one test
    demanding a data-shaped value is indistinguishable from overfitting and is refused. The refusal
    is reported, not hidden, and the caller falls through to ordinary synthesis.
    """
    if is_canonical_default(value):
        return True, "CANONICAL_DEFAULT"
    if supporting_obligations >= 2:
        return True, f"REPEATED_OBLIGATION_x{supporting_obligations}"
    return False, "REFUSED__TEST_VALUE_LAUNDERING_GUARD"


def synthesize_nexus_repairs(
    site: scm.CausalSite,
    witness: NexusWitness,
    *,
    observed_value: Any = _REFUSED,
    cpg: scm.ProjectCPG | None = None,
    supporting_obligations: int = 1,
    frame_exprs: Mapping[str, Any] | None = None,
    prefer_names: Sequence[str] = (),
) -> list[tuple[str, str, str]]:
    """Turn a proven nexus into candidate expressions that *produce* the missing value.

    Every candidate keeps the original site expression and adds the fallback, so the repair can
    only fire where the original was falsy. That property is what makes the boundary invariance
    check meaningful, and it is what stops a bare test literal from ever being shipped.
    """
    orig = site.source_text.strip()
    if not orig or site.kind not in ("return_expr", "assign_rhs"):
        return []
    exp_src = witness.forced_source
    if not exp_src or _literal_value(exp_src) is _REFUSED:
        return []
    expected_value = witness_expected(witness)
    admitted, _reason = data_literal_gate(expected_value, supporting_obligations=supporting_obligations)
    frame_src: str | None = None
    if frame_exprs:
        # Provenance beats permission: when every non-default component of the wanted value is
        # produced by an expression the site's own scope evaluates, no test data enters the program
        # text and the laundering gate does not apply.
        frame_src, _frame_reason = frame_substituted_source(
            expected_value, frame_exprs, prefer_names=prefer_names,
        )
    if not admitted and frame_src is None:
        return []
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    if frame_src is not None:
        for tag, tpl in _FALLBACK_TEMPLATES:
            cand = tpl.format(orig=orig, exp=frame_src)
            try:
                ast.parse(cand, mode="eval")
            except SyntaxError:
                continue
            if cand not in seen:
                seen.add(cand)
                out.append(("NEXUS_FRAME_SUBSTITUTED_FALLBACK", cand, ""))
        out = out[:3]  # provenance-based candidates first; they are the only ones that generalise

    for tag, tpl in _FALLBACK_TEMPLATES:
        if not admitted:
            break
        cand = tpl.format(orig=orig, exp=exp_src)
        try:
            ast.parse(cand, mode="eval")
        except SyntaxError:
            continue
        if cand not in seen:
            seen.add(cand)
            out.append((tag, cand, ""))

    if observed_value is not _REFUSED:
        fit = infer_transducer([(observed_value, witness_expected(witness))])
        if fit is not None:
            kind = "bytes" if isinstance(observed_value, bytes) else "str"
            var = _sole_name(orig)
            if var is not None:
                out.append(("NEXUS_LENS_TRANSLATE", lens_expression(var, fit, value_kind=kind), ""))

    if cpg is not None:
        for helper, (rel, mod, arity) in list(cpg.pure_helpers.items())[:8]:
            if arity != 1 or helper == site.func_name:
                continue
            cand = f"({helper}({orig}) or {exp_src})"
            try:
                ast.parse(cand, mode="eval")
            except SyntaxError:
                continue
            imp = f"from {mod} import {helper}" if rel != site.rel_path else ""
            if cand not in seen:
                seen.add(cand)
                out.append(("NEXUS_HELPER_FALLBACK", cand, imp))
    return out


def witness_expected(witness: NexusWitness) -> Any:
    """Recover the literal a witness forced (it was emitted by `literal_source`, so it round-trips)."""
    val = _literal_value(witness.forced_source)
    return val if val is not _REFUSED else witness.forced_source


def _sole_name(expr_text: str) -> str | None:
    """Return the single bare variable an expression is, if it is exactly one."""
    try:
        node = ast.parse(expr_text.strip(), mode="eval").body
    except SyntaxError:
        return None
    if isinstance(node, ast.Name):
        return node.id
    return None


# ================================================================================================== #
# 5. Statement-level tree-rewrite morphisms (L2) — the multi-statement crystallization gap
# ================================================================================================== #

def _dump(node: Any) -> str:
    if isinstance(node, ast.AST):
        return ast.dump(node, annotate_fields=True, include_attributes=False)
    return repr(node)


_BUILTIN_NAMES = frozenset(dir(__import__("builtins")))
_KEEP_NAMES = frozenset({"self", "cls", "__class__", "__name__", "True", "False", "None"})


class _AlphaRenamer(ast.NodeTransformer):
    """Rename every non-builtin identifier to a positional placeholder, consistently per body.

    This is the identifier abstraction §9.2 asks for: `record`, `rec`, and `arg` become the same
    placeholder when they occupy the same role, so a morphism learned in one file applies to a
    differently named file. Builtins and `self`/`cls` are kept concrete so the template still
    means what it says.
    """

    def __init__(self, prefix: str, mapping: dict[str, str] | None = None,
                 keep: frozenset[str] = frozenset()) -> None:
        self.prefix = prefix
        self.mapping: dict[str, str] = dict(mapping or {})
        self.keep = keep
        self.created: list[tuple[str, str]] = []

    def _name_for(self, orig: str) -> str:
        if orig in _KEEP_NAMES or orig in self.keep or orig.startswith(("__b", "__a", "__n")):
            return orig
        if orig not in self.mapping:
            new = f"{self.prefix}{len(self.mapping)}"
            self.mapping[orig] = new
            self.created.append((new, orig))
        return self.mapping[orig]

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        return ast.copy_location(ast.Name(id=self._name_for(node.id), ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.AST:  # noqa: N802
        node.arg = self._name_for(node.arg)
        return node


def _called_builtins(bodies: Sequence[Sequence[ast.stmt]]) -> frozenset[str]:
    """Builtin names that are actually *called* stay concrete; every other name is a variable."""
    called: set[str] = set()
    for body in bodies:
        for st in body:
            for sub in ast.walk(st):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in _BUILTIN_NAMES:
                    called.add(sub.func.id)
    return frozenset(called)


def _alpha_rename(body: Sequence[ast.stmt], prefix: str, mapping: dict[str, str] | None = None,
                  keep: frozenset[str] = frozenset()
                  ) -> tuple[list[ast.stmt], dict[str, str], dict[str, str]]:
    ren = _AlphaRenamer(prefix, mapping, keep)
    out = [ren.visit(copy.deepcopy(st)) for st in body]
    return out, ren.mapping, {new: orig for new, orig in ren.created}


def _restore_names(node: Any, restore: Mapping[str, str]) -> Any:
    """Map after-side-only placeholders back to the concrete vocabulary the repo already has."""
    if not restore:
        return node
    if isinstance(node, list):
        return [_restore_names(x, restore) for x in node]
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in restore:
            sub.id = restore[sub.id]
        elif isinstance(sub, ast.arg) and sub.arg in restore:
            sub.arg = restore[sub.arg]
    return node


def _au(a: Any, b: Any, holes: dict[str, tuple[Any, Any]]) -> dict[str, Any]:
    """Plotkin anti-unification over AST *statements and expressions*.

    Differing subtrees of the same shape become holes that remember both sides; differing
    subtrees of different shape become a single hole holding the whole subtree on each side.
    """
    if isinstance(a, ast.AST) and isinstance(b, ast.AST) and type(a) is type(b) and a._fields == b._fields:
        fields: dict[str, Any] = {}
        for f in a._fields:
            fields[f] = _au(getattr(a, f, None), getattr(b, f, None), holes)
        return {"T": type(a).__name__, "F": fields}
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return {"L": [_au(x, y, holes) for x, y in zip(a, b)]}
    if isinstance(a, ast.AST) and isinstance(b, ast.AST) and type(a) is type(b) and _dump(a) == _dump(b):
        return {"T": type(a).__name__, "F": {f: _au(getattr(a, f, None), getattr(b, f, None), holes) for f in a._fields}}
    if a == b and not isinstance(a, ast.AST) and not isinstance(b, ast.AST):
        return {"V": a}
    if a is None and b is None:
        return {"V": None}
    name = f"?{len(holes)}"
    holes[name] = (a, b)
    return {"H": name}


def _au_replace(node: dict[str, Any], use_after: bool) -> dict[str, Any]:
    """Expand every hole into the before-side or after-side half of the learned pair."""
    if "H" in node:
        return {"H": node["H"]}
    if "L" in node:
        return {"L": [_au_replace(x, use_after) for x in node["L"]]}
    if "V" in node:
        return {"V": node["V"]}
    return {"T": node["T"], "F": {k: _au_replace(v, use_after) for k, v in node["F"].items()}}


def _tree_match(
    pat: dict[str, Any],
    node: Any,
    binding: dict[str, Any],
    before_dumps: Mapping[str, str] | None = None,
) -> bool:
    """Match a pattern against a node, binding holes.

    A hole is two-sided: the node must reproduce the *before* half of the learned pair exactly
    (after alpha-renaming), so a pattern can never silently generalise over the part of the witness
    that was supposed to stay fixed. That constraint is what makes `return 7` refuse a morphism
    learned from `return None`.
    """
    if "H" in pat:
        name = pat["H"]
        expected = (before_dumps or {}).get(name)
        if expected is not None and _dump(node) != expected:
            return False
        if name in binding:
            return _dump(binding[name]) == _dump(node)
        binding[name] = node
        return True
    if "L" in pat:
        if not isinstance(node, list) or len(node) != len(pat["L"]):
            return False
        return all(_tree_match(p, n, binding, before_dumps) for p, n in zip(pat["L"], node))
    if "V" in pat:
        return not isinstance(node, ast.AST) and pat["V"] == node
    if not isinstance(node, ast.AST) or type(node).__name__ != pat["T"]:
        return False
    return all(_tree_match(pat["F"][f], getattr(node, f, None), binding, before_dumps) for f in pat["F"])


def _tree_build(pat: dict[str, Any], binding: Mapping[str, Any]) -> Any:
    if "H" in pat:
        return copy.deepcopy(binding[pat["H"]])
    if "L" in pat:
        return [_tree_build(p, binding) for p in pat["L"]]
    if "V" in pat:
        return pat["V"]
    node = _AST_BY_NAME[pat["T"]]()
    for f, sub in pat["F"].items():
        setattr(node, f, _tree_build(sub, binding))
    return ast.fix_missing_locations(node)


_AST_BY_NAME: dict[str, type] = {
    name: obj for name, obj in vars(ast).items()
    if isinstance(obj, type) and issubclass(obj, ast.AST)
}


@dataclass
class TreeRewriteMorphism:
    """A verified, inspectable statement/expression rewrite with typed holes and provenance."""
    morphism_id: str
    diagnostic_class: str
    pattern: dict[str, Any]        # shared anti-unified shape (holes as {"H": name})
    replacement: dict[str, Any]     # after-side shape; holes substituted at apply time
    hole_count: int
    language: str
    origin: str                     # repo/commit identifier supplied by the caller
    created_at: float = field(default_factory=time.time)
    verified_transfers: int = 0
    refutations: int = 0
    witness_before: str = ""
    witness_after: str = ""
    name_restore: dict[str, str] = field(default_factory=dict)
    hole_before_dumps: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "TreeRewriteMorphism":
        return TreeRewriteMorphism(
            morphism_id=str(d["morphism_id"]),
            diagnostic_class=str(d.get("diagnostic_class") or "general"),
            pattern=dict(d["pattern"]),
            replacement=dict(d["replacement"]),
            hole_count=int(d.get("hole_count") or 0),
            language=str(d.get("language") or "python"),
            origin=str(d.get("origin") or ""),
            created_at=float(d.get("created_at") or 0.0),
            verified_transfers=int(d.get("verified_transfers") or 0),
            refutations=int(d.get("refutations") or 0),
            witness_before=str(d.get("witness_before") or ""),
            witness_after=str(d.get("witness_after") or ""),
            name_restore=dict(d.get("name_restore") or {}),
            hole_before_dumps=dict(d.get("hole_before_dumps") or {}),
        )


class SkillStoreV2:
    """External, JSON, `O(1)`-editable store of statement-level tree-rewrite morphisms.

    Admission (§9.2): a morphism must be *verified* (the caller only calls `learn` after the full
    suite passed), *prediction-error-bearing* (before != after), *compressible* (at least one hole,
    at most `MAX_STATEMENTS` top-level statements), and carry provenance. Staleness is a fingerprint
    comparison, not a guess.
    """

    MAX_STATEMENTS = 12
    MAX_HOLES = 24

    def __init__(self, path: pathlib.Path | str | None = None) -> None:
        default_p = ROOT / "canonical" / "astra_runtime" / "tmp" / "tree_rewrite_morphism_store_v1.json"
        self.path = pathlib.Path(path) if path else default_p
        self.morphisms: dict[str, TreeRewriteMorphism] = {}
        self.refusal_counts: dict[str, int] = {}
        if self.path.is_file():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, Mapping) and raw.get("schema") == SKILL_STORE_SCHEMA:
                for item in raw.get("morphisms") or []:
                    m = TreeRewriteMorphism.from_dict(item)
                    self.morphisms[m.morphism_id] = m
                self.refusal_counts = dict(raw.get("refusal_counts") or {})
        except Exception:
            self.morphisms = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SKILL_STORE_SCHEMA,
            "authority": AUTHORITY,
            "morphism_count": len(self.morphisms),
            "refusal_counts": self.refusal_counts,
            "morphisms": [m.to_dict() for m in sorted(self.morphisms.values(), key=lambda x: x.morphism_id)],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    # -- admission --------------------------------------------------------------------------- #
    def learn(
        self,
        before_src: str,
        after_src: str,
        *,
        origin: str,
        diagnostic_class: str = "general",
        language: str = "python",
    ) -> TreeRewriteMorphism | None:
        """Crystallize a verified before/after pair into a statement-level morphism."""
        if language != "python":
            self.refusal_counts["NON_PYTHON_STATEMENT_LEVEL"] = self.refusal_counts.get("NON_PYTHON_STATEMENT_LEVEL", 0) + 1
            return None
        try:
            b_body = ast.parse(textwrap.dedent(before_src)).body
            a_body = ast.parse(textwrap.dedent(after_src)).body
        except SyntaxError:
            self.refusal_counts["UNPARSABLE"] = self.refusal_counts.get("UNPARSABLE", 0) + 1
            return None
        if _dump(b_body[0]) == _dump(a_body[0]) and len(b_body) == len(a_body) and all(
            _dump(x) == _dump(y) for x, y in zip(b_body, a_body)
        ):
            self.refusal_counts["NO_PREDICTION_ERROR"] = self.refusal_counts.get("NO_PREDICTION_ERROR", 0) + 1
            return None
        if max(len(b_body), len(a_body)) > self.MAX_STATEMENTS:
            self.refusal_counts["TOO_LARGE"] = self.refusal_counts.get("TOO_LARGE", 0) + 1
            return None

        keep = _called_builtins([b_body, a_body])
        b_alpha, fwd, _ = _alpha_rename(b_body, "__b", keep=keep)
        a_map = {orig: new_name.replace("__b", "__a", 1) for orig, new_name in fwd.items()}
        a_alpha, _, created_after = _alpha_rename(a_body, "__n", mapping=a_map, keep=keep)

        holes: dict[str, tuple[Any, Any]] = {}
        pat = _au(b_alpha, a_alpha, holes)
        if not holes or len(holes) > self.MAX_HOLES:
            self.refusal_counts["DEGENERATE_OR_HUGE"] = self.refusal_counts.get("DEGENERATE_OR_HUGE", 0) + 1
            return None
        def _alpha_pair(bv: Any, av: Any) -> bool:
            # `_au` descends into `Name.id`, so the alpha pair usually arrives as two *strings*;
            # it can also arrive as two `Name` nodes when the whole node differed first.
            if isinstance(bv, str) and isinstance(av, str):
                return av == bv.replace("__b", "__a", 1)
            if isinstance(bv, ast.Name) and isinstance(av, ast.Name):
                return av.id == bv.id.replace("__b", "__a", 1)
            return False

        alpha_holes = frozenset(name for name, (bv, av) in holes.items() if _alpha_pair(bv, av))
        rep = _after_view(pat, holes, alpha_holes)

        hole_before = {name: _dump(bv) for name, (bv, _av) in holes.items()}
        blob = json.dumps(
            {"pat": pat, "rep": rep, "r": created_after, "hb": hole_before},
            sort_keys=True, separators=(",", ":"),
        )
        mid = "trm_" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
        existing = self.morphisms.get(mid)
        if existing is not None:
            if origin and origin not in existing.origin:
                existing.origin = f"{existing.origin},{origin}" if existing.origin else origin
            self.save()
            return existing
        m = TreeRewriteMorphism(
            morphism_id=mid,
            diagnostic_class=diagnostic_class,
            pattern=pat,
            replacement=rep,
            hole_count=len(holes),
            language=language,
            origin=origin,
            witness_before=textwrap.dedent(before_src)[:600],
            witness_after=textwrap.dedent(after_src)[:600],
            name_restore=dict(created_after),
            hole_before_dumps=hole_before,
        )
        self.morphisms[mid] = m
        self.save()
        return m

    # -- application ------------------------------------------------------------------------- #
    def propose(self, source_text: str, *, limit: int = 8) -> list[tuple[TreeRewriteMorphism, str]]:
        """Rewrite `source_text` (a function or module body) with every matching morphism."""
        try:
            body = ast.parse(textwrap.dedent(source_text)).body
        except SyntaxError:
            return []
        body, _, tgt_names = _alpha_rename(body, "__b", keep=_called_builtins([body]))
        proposals: list[tuple[TreeRewriteMorphism, str]] = []
        for m in sorted(self.morphisms.values(), key=lambda x: (x.verified_transfers - x.refutations, x.created_at), reverse=True):
            if m.refutations > m.verified_transfers:
                continue
            binding: dict[str, Any] = {}
            if not _tree_match(m.pattern, body, binding, m.hole_before_dumps):
                continue
            # Alpha correspondence: the k-th distinct witness name plays the role of the k-th
            # distinct target name. If the target has fewer names than the witness used, the
            # morphism cannot be instantiated and is refused rather than guessed.
            restore = dict(m.name_restore)
            for placeholder, orig in tgt_names.items():
                restore[placeholder] = orig
                restore[placeholder.replace("__b", "__a", 1)] = orig
            if any(k not in restore for k in _placeholders_in(m.replacement)):
                continue
            try:
                new_body = _restore_names(_tree_build(m.replacement, binding), restore)
                new_src = ast.unparse(ast.Module(body=new_body, type_ignores=[]))
            except Exception:
                continue
            if new_src.strip() and new_src.strip() != textwrap.dedent(source_text).strip():
                proposals.append((m, new_src))
            if len(proposals) >= limit:
                break
        return proposals

    def mark_transfer(self, morphism_id: str) -> None:
        m = self.morphisms.get(morphism_id)
        if m is not None:
            m.verified_transfers += 1
            self.save()

    def mark_refutation(self, morphism_id: str) -> None:
        m = self.morphisms.get(morphism_id)
        if m is not None:
            m.refutations += 1
            self.save()

    def remove(self, morphism_id: str) -> bool:
        """`O(1)` removal: the store is a dict, so deletion needs no rebuild or retraining."""
        removed = self.morphisms.pop(morphism_id, None) is not None
        if removed:
            self.save()
        return removed

    def stale(self, morphism_id: str, current_source: str) -> bool:
        """Staleness probe: does the recorded witness still parse and still differ?"""
        m = self.morphisms.get(morphism_id)
        if m is None:
            return True
        try:
            ast.parse(m.witness_before)
            ast.parse(m.witness_after)
        except SyntaxError:
            return True
        return _dump(ast.parse(m.witness_before).body) == _dump(ast.parse(m.witness_after).body)


def _placeholders_in(node: Any) -> set[str]:
    """Every `__aK`/`__bK` placeholder an encoded replacement tree mentions."""
    out: set[str] = set()
    if isinstance(node, Mapping):
        for v in node.values():
            out |= _placeholders_in(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            out |= _placeholders_in(v)
    elif isinstance(node, str) and (node.startswith("__a") or node.startswith("__b")) and node[3:].isdigit():
        out.add(node)
    return out


def _after_view(
    pat: dict[str, Any],
    holes: Mapping[str, tuple[Any, Any]],
    alpha_holes: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Build the replacement tree from the shared pattern.

    A hole whose two sides are the *same identifier* up to alpha-renaming stays a hole, so at
    application time it is filled with the new file's own name instead of the witness file's.
    Every other hole expands to its after-side half, which is the concrete new vocabulary.
    """
    if "H" in pat:
        name = pat["H"]
        if name in alpha_holes:
            return {"H": name}
        return _au(holes[name][1], holes[name][1], {})
    if "L" in pat:
        return {"L": [_after_view(x, holes, alpha_holes) for x in pat["L"]]}
    if "V" in pat:
        return {"V": pat["V"]}
    return {"T": pat["T"], "F": {k: _after_view(v, holes, alpha_holes) for k, v in pat["F"].items()}}


# ================================================================================================== #
# 6. Negative-space invariants (L3): a refuted shape is a permanent filter, not a retry.
# ================================================================================================== #

@dataclass
class NegativeInvariant:
    """An executed refutation: this candidate shape, at this site kind, broke this test."""
    invariant_id: str
    site_kind: str
    mechanism_tag: str
    features: dict[str, Any]
    witness_node: str
    origin: str
    created_at: float = field(default_factory=time.time)
    blocked_hits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "NegativeInvariant":
        return NegativeInvariant(
            invariant_id=str(d["invariant_id"]),
            site_kind=str(d.get("site_kind") or ""),
            mechanism_tag=str(d.get("mechanism_tag") or ""),
            features=dict(d.get("features") or {}),
            witness_node=str(d.get("witness_node") or ""),
            origin=str(d.get("origin") or ""),
            created_at=float(d.get("created_at") or 0.0),
            blocked_hits=int(d.get("blocked_hits") or 0),
        )


def candidate_features(site: scm.CausalSite, candidate_code: str) -> dict[str, Any]:
    """Cheap structural signature of a candidate, computed without running anything."""
    orig = site.source_text
    return {
        "site_kind": site.kind,
        "drops_none_guard": bool(re.search(r"\bis\s+(not\s+)?None\b", orig)) and not re.search(
            r"\bis\s+(not\s+)?None\b", candidate_code
        ),
        "adds_or_default": " or " in candidate_code and " or " not in orig,
        "negates_condition": candidate_code.strip().startswith("not ") and not orig.strip().startswith("not "),
        "shrinks_length": len(candidate_code.strip()) < max(4, len(orig.strip()) // 2),
        "introduces_call": bool(re.search(r"\w+\(", candidate_code)) and not re.search(r"\w+\(", orig),
    }


class NegativeInvariantStore:
    """External JSON store of L3 negative invariants; `O(1)` add, delete, and membership test."""

    def __init__(self, path: pathlib.Path | str | None = None) -> None:
        default_p = ROOT / "canonical" / "astra_runtime" / "tmp" / "negative_invariant_store_v1.json"
        self.path = pathlib.Path(path) if path else default_p
        self.invariants: dict[str, NegativeInvariant] = {}
        self._feature_index: dict[tuple[str, str], list[str]] = {}
        if self.path.is_file():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, Mapping) and raw.get("schema") == INVARIANT_STORE_SCHEMA:
                for item in raw.get("invariants") or []:
                    inv = NegativeInvariant.from_dict(item)
                    self.invariants[inv.invariant_id] = inv
                self._reindex()
        except Exception:
            self.invariants = {}
            self._feature_index = {}

    def _reindex(self) -> None:
        self._feature_index = {}
        for inv in self.invariants.values():
            self._feature_index.setdefault((inv.site_kind, inv.mechanism_tag), []).append(inv.invariant_id)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": INVARIANT_STORE_SCHEMA,
            "authority": AUTHORITY,
            "invariant_count": len(self.invariants),
            "invariants": [inv.to_dict() for inv in sorted(self.invariants.values(), key=lambda x: x.invariant_id)],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def record(
        self,
        site_kind: str,
        mechanism_tag: str,
        features: Mapping[str, Any],
        witness_node: str,
        *,
        origin: str = "",
    ) -> NegativeInvariant:
        active = {k: v for k, v in features.items() if v}
        blob = json.dumps({"k": site_kind, "t": mechanism_tag, "f": active}, sort_keys=True, separators=(",", ":"))
        iid = "ninv_" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
        inv = self.invariants.get(iid)
        if inv is None:
            inv = NegativeInvariant(
                invariant_id=iid,
                site_kind=site_kind,
                mechanism_tag=mechanism_tag,
                features=active,
                witness_node=witness_node,
                origin=origin,
            )
            self.invariants[iid] = inv
            self._feature_index.setdefault((site_kind, mechanism_tag), []).append(iid)
            self.save()
        return inv

    def refuted(self, site_kind: str, mechanism_tag: str, features: Mapping[str, Any]) -> NegativeInvariant | None:
        """Microsecond membership test: is this candidate shape already known to fail?"""
        active = {k for k, v in features.items() if v}
        for iid in self._feature_index.get((site_kind, mechanism_tag), ()):
            inv = self.invariants[iid]
            if set(inv.features) and set(inv.features).issubset(active):
                inv.blocked_hits += 1
                return inv
        return None

    def remove(self, invariant_id: str) -> bool:
        inv = self.invariants.pop(invariant_id, None)
        if inv is None:
            return False
        self._reindex()
        self.save()
        return True


# ================================================================================================== #
# 7. Boundary invariance fuzzing: the divergence set must be the one the obligation predicted.
# ================================================================================================== #

BOUNDARY_CORPUS: tuple[Any, ...] = (
    None, True, False, 0, 1, -1, 0.0, -0.0, "", " ", "a", "0", b"", b"\x00", b"\x04", b"\x1a",
    [], [0], (), (0,), {}, {"a": 0}, set(), 255, 256, -256, 2**31, -(2**31), 2**63,
    "\x00", "\x04\x1a", "None", "0.0", "-0.0", float("inf"), float("nan"), 10**30,
)


def _safe_call(fn: Any, args: Sequence[Any]) -> tuple[bool, Any]:
    try:
        return True, fn(*args)
    except Exception as exc:  # noqa: BLE001 - the exception *is* the observation
        return False, f"{type(exc).__name__}:{exc}"[:120]


@dataclass(frozen=True)
class Divergence:
    args: tuple[Any, ...]
    before: str
    after: str
    predicted: bool

    def to_dict(self) -> dict[str, Any]:
        return {"args": repr(self.args)[:120], "before": self.before[:120], "after": self.after[:120],
                "predicted": self.predicted}


def differential_boundary_scan(
    before_fn: Any,
    after_fn: Any,
    *,
    arity: int = 1,
    corpus: Sequence[Any] = BOUNDARY_CORPUS,
    max_cases: int = 256,
) -> list[Divergence]:
    """Execute both versions over a boundary corpus and classify every divergence.

    A divergence is `predicted` when the original produced a falsy/None result on that input and
    the fallback therefore legitimately fired. Any other divergence is an unpredicted change of
    behaviour, and the caller must refuse the patch.
    """
    out: list[Divergence] = []
    cases = 0
    combos: Iterable[tuple[Any, ...]]
    if arity <= 1:
        combos = ((v,) for v in corpus)
    elif arity == 2:
        combos = ((a, b) for a in corpus for b in corpus)
    else:
        combos = ((a,) * arity for a in corpus)
    for args in combos:
        if cases >= max_cases:
            break
        cases += 1
        ok_b, vb = _safe_call(before_fn, args)
        ok_a, va = _safe_call(after_fn, args)
        if ok_b != ok_a or repr(vb) != repr(va) and not _nan_equal(vb, va):
            predicted = ok_b and (not vb or vb is None)
            out.append(Divergence(args=args, before=repr(vb), after=repr(va), predicted=bool(predicted)))
    return out


def _nan_equal(a: Any, b: Any) -> bool:
    try:
        return a != a and b != b  # noqa: PLR0124 - NaN identity on purpose
    except Exception:
        return False


def patch_invariance_verdict(divergences: Sequence[Divergence]) -> tuple[bool, str]:
    """Accept only when every observed divergence is one the obligation predicted."""
    unpredicted = [d for d in divergences if not d.predicted]
    if unpredicted:
        return False, f"UNPREDICTED_DIVERGENCE:{len(unpredicted)}"
    if not divergences:
        return True, "NO_OBSERVABLE_CHANGE_IN_BOUNDARY_CORPUS"
    return True, f"PREDICTED_FALLBACK_DIVERGENCE:{len(divergences)}"


__all__ = [
    "BOUNDARY_CORPUS",
    "Divergence",
    "NegativeInvariant",
    "NegativeInvariantStore",
    "NexusWitness",
    "SkillStoreV2",
    "TransducerFit",
    "TreeRewriteMorphism",
    "ValueObligation",
    "angelic_nexus_blame",
    "candidate_features",
    "differential_boundary_scan",
    "derive_frame_expressions",
    "extract_value_obligations",
    "frame_substituted_source",
    "data_literal_gate",
    "infer_transducer",
    "is_canonical_default",
    "invert_lens",
    "lens_expression",
    "literal_source",
    "patch_invariance_verdict",
    "synthesize_nexus_repairs",
]


# ================================================================================================== #
# 8. Frame provenance: where did the expected value come from?
#
# The laundering gate refuses a test's own data as repair material -- correctly. But click@05f6fd0 shows
# exactly why that is not the end of the story: the value `('SRC', '')` is not *data*, it is
# `(self.make_metavar(ctx), '')` -- a value the enclosing object computes for itself. The test publishes
# the value; the frame holds the provenance. This section recovers that provenance mechanically.
#
# The recorder runs the instrumented site once in a `/dev/shm` clone and, for every object in scope,
# records the primitive-valued attributes and the primitive results of calling its own public methods
# on the primitive locals. Nothing is looked up in a table of known libraries: the candidate expressions
# are built from the object's own `dir()` and the repo's own call sites, then kept only if they
# reproduce the wanted component exactly.
# ================================================================================================== #

_DERIVE_RT = '''
import json, os
_LOG = os.environ.get("BRAIN_DERIVE_LOG", "")
_PRI = (int, float, str, bool, list, tuple, dict, type(None))


def _rec(expr, value):
    if not _LOG:
        return
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"expr": expr, "value": value}, default=repr) + "\\n")
    except Exception:
        pass


def _derive(val, loc):
    budget = 24
    for name, obj in list(loc.items()):
        if isinstance(obj, _PRI) or budget <= 0:
            continue
        prim_locals = [(k, v) for k, v in loc.items() if isinstance(v, _PRI) and not k.startswith("__")]
        obj_locals = [(k, v) for k, v in loc.items() if not isinstance(v, _PRI) and not k.startswith("__")]
        for attr in dir(obj):
            if budget <= 0:
                return val
            if attr.startswith("_"):
                continue
            budget -= 1
            try:
                member = getattr(obj, attr)
            except Exception:
                continue
            if isinstance(member, _PRI):
                _rec(f"{name}.{attr}", member)
                if isinstance(member, (str, bytes)):
                    for meth in ("upper", "lower", "strip"):
                        try:
                            produced = getattr(member, meth)()
                        except Exception:
                            continue
                        if isinstance(produced, _PRI) and produced != member:
                            _rec(f"{name}.{attr}.{meth}()", produced)
            elif callable(member):
                bound = False
                for argname, argval in prim_locals[:3]:
                    try:
                        produced = member(argval)
                    except Exception:
                        continue
                    if isinstance(produced, _PRI):
                        _rec(f"{name}.{attr}({argname})", produced)
                        bound = True
                        break
                if not bound:
                    # Object locals are legal arguments too -- the metavar of an argument is a
                    # function of its *context*, which is an object and not a primitive.
                    for oname, oval in obj_locals[:2]:
                        if oval is obj:
                            continue
                        try:
                            produced = member(oval)
                        except Exception:
                            continue
                        if isinstance(produced, _PRI):
                            _rec(f"{name}.{attr}({oname})", produced)
                            bound = True
                            break
                if not bound:
                    try:
                        produced = member()
                    except Exception:
                        continue
                    if isinstance(produced, _PRI):
                        _rec(f"{name}.{attr}()", produced)
    return val
'''

_HOOK_NAME = "__brain_derive__"


def derive_frame_expressions(
    project_root: pathlib.Path | str,
    site: "scm.CausalSite",
    focused_cmd: Sequence[str],
    *,
    timeout_s: float = 8.0,
) -> dict[str, Any]:
    """Return `{expression_text: value}` for every in-scope expression that produced a primitive.

    The probe is read-only with respect to the real tree: it runs in a fresh `os.link` clone in
    `/dev/shm` with a bytecode prefix in that clone, exactly like every other verification here.
    """
    if site.language != "python" or site.kind not in _FORCED_KINDS:
        return {}
    root = pathlib.Path(project_root).resolve()
    orig = (root / site.rel_path).read_bytes()
    wrapped = (
        f"__import__('_brain_derive_rt')._derive("
        f"__import__('_brain_derive_rt')._hook(({site.source_text}), locals()), locals())"
    )
    patched = scm._apply_site_patch(orig, site, wrapped)  # noqa: SLF001
    if not scm._syntactically_valid(patched, "python", orig):  # noqa: SLF001
        return {}
    rt = _DERIVE_RT.encode("utf-8") + b"\n\ndef _hook(val, loc):\n    return val\n"
    with tempfile.TemporaryDirectory(prefix="brain-derive-", dir=str(scm._shm_root())) as td:  # noqa: SLF001
        log = pathlib.Path(td) / "derived.jsonl"
        prev = os.environ.get("BRAIN_DERIVE_LOG")
        os.environ["BRAIN_DERIVE_LOG"] = str(log)
        try:
            scm._run_suite_in_scratch(  # noqa: SLF001
                root, focused_cmd,
                {site.rel_path: patched, "_brain_derive_rt.py": rt},
                timeout_s=timeout_s,
            )
        finally:
            if prev is None:
                os.environ.pop("BRAIN_DERIVE_LOG", None)
            else:
                os.environ["BRAIN_DERIVE_LOG"] = prev
        if not log.is_file():
            return {}
        out: dict[str, Any] = {}
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            expr = str(rec.get("expr") or "")
            if expr and expr not in out:
                out[expr] = rec.get("value")
        return out


def _component_source(
    component: Any,
    frame_exprs: Mapping[str, Any],
    prefer_names: Sequence[str] = (),
) -> str | None:
    """Emit the provenance expression for one leaf of the expected value, or `None`.

    Ranking prefers an expression that calls something the *repository itself* defines
    (`self.make_metavar(ctx)`) over one that calls a builtin (`self.name.upper()`). Both are proven by
    the frame, but the repo's own vocabulary is the one that means what the program means.
    """
    if is_canonical_default(component):
        return repr(component)
    matches = [expr for expr, val in frame_exprs.items()
               if type(val) is type(component) and val == component]
    if not matches:
        return None
    preferred = [e for e in matches if any(f"{name}(" in e for name in prefer_names)]
    if preferred:
        matches = preferred
    matches.sort(key=lambda e: (e.count("("), len(e)))
    return matches[0]


def frame_substituted_source(
    expected: Any,
    frame_exprs: Mapping[str, Any],
    *,
    prefer_names: Sequence[str] = (),
) -> tuple[str | None, str]:
    """Rebuild the expected value out of the frame's own expressions.

    Every non-default component must be reproduced by an expression the site's own scope evaluates.
    If even one is unmatched the whole substitution is refused: a partial rebuild would re-introduce
    the test's data through the back door.
    """
    if not frame_exprs:
        return None, "NO_FRAME_EVIDENCE"
    if isinstance(expected, tuple):
        parts = [_component_source(el, frame_exprs, prefer_names) for el in expected]
        if any(p is None for p in parts):
            return None, "COMPONENT_NOT_IN_FRAME"
        body = ", ".join(parts)
        if len(parts) == 1:
            body += ","
        return f"({body})", "FRAME_SUBSTITUTED"
    if isinstance(expected, list):
        parts = [_component_source(el, frame_exprs, prefer_names) for el in expected]
        if any(p is None for p in parts):
            return None, "COMPONENT_NOT_IN_FRAME"
        return "[" + ", ".join(parts) + "]", "FRAME_SUBSTITUTED"
    if isinstance(expected, dict):
        pairs = []
        for key, val in expected.items():
            ksrc = _component_source(key, frame_exprs, prefer_names)
            vsrc = _component_source(val, frame_exprs, prefer_names)
            if ksrc is None or vsrc is None:
                return None, "COMPONENT_NOT_IN_FRAME"
            pairs.append(f"{ksrc}: {vsrc}")
        return "{" + ", ".join(pairs) + "}", "FRAME_SUBSTITUTED"
    src = _component_source(expected, frame_exprs, prefer_names)
    if src is None:
        return None, "COMPONENT_NOT_IN_FRAME"
    return src, "FRAME_SUBSTITUTED"
