#!/usr/bin/env python3
"""Repo-native component mining + dual-program splicing (zero-model, zero-network).

WHY THIS EXISTS
---------------
Measured on this tree (witness_inversion_v1 + REACH_OF_THE_GRAMMAR):
75.2% of real SWE-bench fix pieces are rebuilt by no operator any other
task's fixes ever produced; with every other task as experience coverage
is 18.7%. A fixed mutation grammar cannot name a fix that calls an
internal helper defined three files away. Witness inversion alone
selects a value the artifact already contains; it cannot create a
distinction the artifact does not have (0/16 on the real corpus, all
refusals correct).

This module attacks REACH from the other side: harvest the repository's
own vocabulary (functions, methods, classes, constants, exceptions)
via the incremental semantic graph, type-annotate it from live call
sites, and compose patches from those real components. When two
candidates each pass a different test slice, splice them behind a
separating guard synthesized by evaluation, not enumeration.

DISCIPLINE (same as witness_inversion_v1)
-----------------------------------------
- Proposal is untrusted; the real test has the last word.
- No candidate accepted -> REFUSE with reason, stays in denominator.
- Evaluation happens on live values; anything needing a model of the
  program is refused rather than guessed.
- Admission gate runs BEFORE persistence: >=1 unseen defective program
  repaired, >=1 already-correct program preserved, zero broken.
  Otherwise REFUSE and store nothing.
- Parallel rollouts use os.fork Copy-On-Write realities; the parent
  scores by residual reduction (failing-test count), keeps the winner,
  discards the rest. No imagined futures.

Authority: NONE. Producer-run sandbox measurement. Model calls 0.
Network calls 0 at decision time. Incremental spend $0.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_REPO_NATIVE_MINING_V1"

# ---------------------------------------------------------------------------
# 1. Vocabulary mining (repo-native, zero grammar)
# ---------------------------------------------------------------------------


def mine_vocabulary(root: pathlib.Path, scope: str = ".") -> dict[str, Any]:
    """Extract every function/method/class/constant/exception in the repo.

    Uses IncrementalSemanticGraph (content-addressed, 0.35s warm on
    2,292 files). Returns a plain dict; no model, no network.
    """
    from canonical.swe_kernel.incremental_semantic_graph_v1 import (
        IncrementalSemanticGraph,
    )

    graph = IncrementalSemanticGraph(pathlib.Path(root))
    summaries = graph.load_summaries(scope)
    functions: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    constants: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    call_sites: list[dict[str, Any]] = []
    for rel, info in summaries.items():
        mod = info.get("module", "")
        for d in info.get("definitions") or []:
            entry = {
                "name": d.get("name"),
                "qualname": d.get("qualname"),
                "kind": d.get("kind"),
                "module": mod,
                "rel_path": rel,
                "signature": d.get("signature", ""),
                "line": d.get("line"),
            }
            kind = d.get("kind")
            if kind in ("function", "async_function"):
                functions.append(entry)
            elif kind == "method":
                methods.append(entry)
            elif kind == "class":
                classes.append(entry)
                # Exception classes: name ends with Error/Exception
                nm = str(d.get("name") or "")
                if nm.endswith("Error") or nm.endswith("Exception"):
                    exceptions.append(entry)
            elif kind == "constant":
                constants.append(entry)
        for c in info.get("calls") or []:
            call_sites.append(
                {
                    "caller": c.get("caller"),
                    "callee": c.get("callee"),
                    "qualifier": c.get("qualifier", ""),
                    "rel_path": rel,
                    "line": c.get("line"),
                }
            )
    # Deduplicate by qualname+module
    def _dedup(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        out: list[dict[str, Any]] = []
        for r in rows:
            k = (str(r.get("qualname")), str(r.get("module")))
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
        return sorted(out, key=lambda r: (str(r.get("module")), str(r.get("qualname"))))

    vocab = {
        "schema": SCHEMA,
        "root": str(pathlib.Path(root).resolve()),
        "scope": scope,
        "functions": _dedup(functions),
        "methods": _dedup(methods),
        "classes": _dedup(classes),
        "constants": _dedup(constants),
        "exceptions": _dedup(exceptions),
        "call_sites": call_sites,
        "counts": {
            "functions": len(_dedup(functions)),
            "methods": len(_dedup(methods)),
            "classes": len(_dedup(classes)),
            "constants": len(_dedup(constants)),
            "exceptions": len(_dedup(exceptions)),
            "call_sites": len(call_sites),
        },
    }
    return vocab


def infer_transition_types(vocab: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Type-annotate mined components from live call sites (APIphany-style).

    Each transition is Input Semantic Type -> Output Semantic Type.
    Types are inferred from call-site arity and observed argument shapes
    in the summaries (literal kinds at call sites are not in summaries,
    so we infer arity + caller context; unknown stays UNKNOWN, never
    guessed). No model involved.
    """
    call_sites = list(vocab.get("call_sites") or [])
    # Count callers per callee name
    by_callee: dict[str, list[dict[str, Any]]] = {}
    for cs in call_sites:
        by_callee.setdefault(str(cs.get("callee")), []).append(cs)
    transitions: list[dict[str, Any]] = []
    for group in ("functions", "methods"):
        for entry in vocab.get(group) or []:
            name = str(entry.get("name"))
            sig = str(entry.get("signature") or "")
            # Arity from signature: count top-level commas inside parens
            arity = _arity_from_signature(sig)
            sites = by_callee.get(name, [])
            transitions.append(
                {
                    "name": name,
                    "qualname": entry.get("qualname"),
                    "module": entry.get("module"),
                    "rel_path": entry.get("rel_path"),
                    "arity": arity,
                    "input_type": f"ARGS_{arity}" if arity is not None else "ARGS_UNKNOWN",
                    "output_type": "UNKNOWN",
                    "call_site_count": len(sites),
                    "callers": sorted({str(s.get("caller")) for s in sites})[:8],
                }
            )
    return sorted(transitions, key=lambda t: (str(t["module"]), str(t["qualname"])))


def _arity_from_signature(sig: str) -> int | None:
    m = re.search(r"\((.*)\)", sig, re.DOTALL)
    if not m:
        return None
    inner = m.group(1).strip()
    if not inner:
        return 0
    # Split on commas at depth 0 (ignore defaults with commas in brackets roughly)
    depth = 0
    count = 1
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count


def vocabulary_for_expression(
    vocab: Mapping[str, Any],
    *,
    exclude_names: Sequence[str] = (),
    limit: int = 24,
) -> list[str]:
    """Names the synthesizer may use: mined callables, shortest first.

    This is the dynamic alphabet that replaces a fixed grammar. It
    expands to fit any codebase automatically.
    """
    excl = set(exclude_names)
    names: list[str] = []
    for group in ("functions", "methods"):
        for entry in vocab.get(group) or []:
            nm = str(entry.get("name"))
            if nm and nm not in excl and nm not in names:
                names.append(nm)
    # Prefer names already called somewhere (live vocabulary), then short
    called = {str(cs.get("callee")) for cs in vocab.get("call_sites") or []}
    names.sort(key=lambda n: (n not in called, len(n), n))
    return names[:limit]


# ---------------------------------------------------------------------------
# 2. Dual-program splicing (counterexample-partitioned merge)
# ---------------------------------------------------------------------------


def synthesize_separating_guard(
    states_t1: Sequence[Mapping[str, Any]],
    states_t2: Sequence[Mapping[str, Any]],
    *,
    max_candidates: int = 64,
) -> str | None:
    """Find a boolean guard separating T1 states from T2 states by evaluation.

    Candidates are comparisons over shared locals (==, !=, <, <=, >, >=,
    truthiness, len comparisons). The guard must hold on ALL T1 states
    and on NO T2 states (or vice versa). Returns the guard source or
    None (refuse). Synthesizing a 3-token guard is exponentially easier
    than synthesizing a 40-line function.
    """
    if not states_t1 or not states_t2:
        return None
    keys = sorted(set(states_t1[0].keys()) & set(states_t2[0].keys()))
    # Only scalar locals (int/str/bool/None) are eligible
    candidates: list[str] = []
    for k in keys:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
            continue
        candidates.append(f"{k}")
        candidates.append(f"not {k}")
        candidates.append(f"len({k}) > 0")
        candidates.append(f"len({k}) == 0")
        for op in ("==", "!=", "<", "<=", ">", ">="):
            candidates.append(f"{k} {op} 0")
            candidates.append(f"{k} {op} 1")
        # String equality against observed values (bounded)
        vals: set[str] = set()
        for s in list(states_t1) + list(states_t2):
            v = s.get(k)
            if isinstance(v, str) and len(v) <= 32:
                vals.add(v)
        for v in sorted(vals)[:4]:
            candidates.append(f"{k} == {v!r}")
            candidates.append(f"{k} != {v!r}")
    candidates = candidates[:max_candidates]
    for guard in candidates:
        try:
            tree = ast.parse(guard, mode="eval")
        except SyntaxError:
            continue
        if _eval_guard(tree, states_t1, expect=True) and not _eval_guard(tree, states_t2, expect=True):
            return guard
        # Negation also acceptable (swap T1/T2 meaning is symmetric for splice)
        neg = f"not ({guard})"
        try:
            ntree = ast.parse(neg, mode="eval")
        except SyntaxError:
            continue
        if _eval_guard(ntree, states_t1, expect=True) and not _eval_guard(ntree, states_t2, expect=True):
            return neg
    return None


def _eval_guard(tree: ast.Expression, states: Sequence[Mapping[str, Any]], *, expect: bool) -> bool:
    for st in states:
        try:
            val = _eval_node(tree.body, dict(st))
        except Exception:
            return False
        if bool(val) is not expect:
            return False
    return True


def _eval_node(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not bool(_eval_node(node.operand, env))
    if isinstance(node, ast.BoolOp):
        vals = [_eval_node(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in vals)
        if isinstance(node.op, ast.Or):
            return any(bool(v) for v in vals)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval_node(comp, env)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            else:
                raise ValueError("unsupported compare")
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
        if len(node.args) != 1:
            raise ValueError("len arity")
        return len(_eval_node(node.args[0], env))
    raise ValueError(f"unsupported guard node {type(node).__name__}")


def splice_programs(prog_p1: str, prog_p2: str, guard: str) -> str:
    """Splice two programs behind a separating guard.

    prog_p1/prog_p2 are single return expressions (as in witness
    inversion). The result is a single expression valid in the same
    site: `(P1 if (guard) else P2)`.
    """
    return f"({prog_p1} if ({guard}) else {prog_p2})"


def splice_statements(stmt_p1: str, stmt_p2: str, guard: str) -> str:
    """Splice two statement bodies (for multi-line functions)."""
    return f"if {guard}:\n    {stmt_p1}\nelse:\n    {stmt_p2}"


# ---------------------------------------------------------------------------
# 3. Checker-has-last-word verification (real test, always restore)
# ---------------------------------------------------------------------------


def _env(repo: pathlib.Path) -> dict[str, str]:
    return {
        "PYTHONPATH": ":".join([str(repo), str(repo / "src"), str(repo / "tests")]),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(repo),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def verify_with_real_test(
    repo: pathlib.Path,
    command: Sequence[str],
    file_path: pathlib.Path,
    original: str,
    candidate_source: str,
    timeout: float = 60.0,
) -> bool:
    """Accept only on the real test. Always restore. Never a proposal."""
    try:
        file_path.write_text(candidate_source, encoding="utf-8")
        for stale in repo.rglob("__pycache__"):
            shutil.rmtree(stale, ignore_errors=True)
        try:
            done = subprocess.run(
                list(command),
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_env(repo),
            )
        except subprocess.TimeoutExpired:
            return False
        return done.returncode == 0
    finally:
        file_path.write_text(original, encoding="utf-8")


# ---------------------------------------------------------------------------
# 4. Admission gate (before persistence, on held-out victims)
# ---------------------------------------------------------------------------


def admit_patch(
    *,
    candidate_source: str,
    defective_repo: pathlib.Path,
    defective_file: pathlib.Path,
    defective_original: str,
    defective_command: Sequence[str],
    correct_repo: pathlib.Path,
    correct_file: pathlib.Path,
    correct_original: str,
    correct_command: Sequence[str],
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Gate: repair >=1 unseen defective program, preserve >=1 correct one.

    Returns {"verdict": "ADMIT"|"REFUSE", "reason": ...}. On REFUSE the
    caller must store nothing. This is the verifier-before-persistence
    bottleneck: without it, permanence stores the wrong reading forever.
    """
    repaired = verify_with_real_test(
        defective_repo, defective_command, defective_file, defective_original, candidate_source, timeout
    )
    if not repaired:
        return {"verdict": "REFUSE", "reason": "ADMISSION_REJECT:DID_NOT_REPAIR_DEFECTIVE_VICTIM"}
    preserved = verify_with_real_test(
        correct_repo, correct_command, correct_file, correct_original, candidate_source, timeout
    )
    if not preserved:
        return {"verdict": "REFUSE", "reason": "ADMISSION_REJECT:BROKE_CORRECT_PROGRAM"}
    return {"verdict": "ADMIT", "reason": "ADMIT:REPAIRED_VICTIM_AND_PRESERVED_CORRECT"}


# ---------------------------------------------------------------------------
# 5. Parallel CoW speculative rollouts (exact futures, not imagined)
# ---------------------------------------------------------------------------


def parallel_cow_rollouts(
    candidates: Sequence[dict[str, Any]],
    *,
    score_fn: Any | None = None,
) -> dict[str, Any]:
    """Fork N CoW realities, score by residual reduction, keep winner.

    Each candidate is {"id": str, "apply": callable()->int residual}.
    The parent forks; each child runs its candidate and reports its
    residual over a pipe; the parent keeps the lowest residual and
    discards the rest at zero cost. If score_fn is None, candidates
    must carry "residual" directly (for tests without forking).

    Returns {"winner": id|None, "residuals": {id: residual}, "fork_ms": float}.
    Fail-closed: no winner -> winner None.
    """
    if not candidates:
        return {"winner": None, "residuals": {}, "fork_ms": 0.0}
    if score_fn is None:
        residuals = {str(c["id"]): int(c["residual"]) for c in candidates}
        winner = min(residuals, key=lambda k: residuals[k]) if residuals else None
        return {"winner": winner, "residuals": residuals, "fork_ms": 0.0}
    # Real fork path (Linux CoW). Each child runs apply() and writes residual.
    t0 = time.perf_counter()
    pipes: list[tuple[str, int, int]] = []  # (id, read_fd, pid)
    for cand in candidates:
        rfd, wfd = os.pipe()
        pid = os.fork()
        if pid == 0:
            # Child: run candidate, report residual, exit.
            os.close(rfd)
            try:
                residual = int(cand["apply"]())
            except Exception:
                residual = 10**9
            try:
                os.write(wfd, str(residual).encode("ascii"))
            except OSError:
                pass
            os.close(wfd)
            os._exit(0)
        os.close(wfd)
        pipes.append((str(cand["id"]), rfd, pid))
    residuals: dict[str, int] = {}
    for cid, rfd, pid in pipes:
        data = b""
        while True:
            chunk = os.read(rfd, 64)
            if not chunk:
                break
            data += chunk
        os.close(rfd)
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        try:
            residuals[cid] = int(data.decode("ascii").strip() or "1000000000")
        except ValueError:
            residuals[cid] = 10**9
    fork_ms = (time.perf_counter() - t0) * 1000.0
    winner = min(residuals, key=lambda k: residuals[k]) if residuals else None
    return {"winner": winner, "residuals": residuals, "fork_ms": fork_ms}


def state_fingerprint(root: pathlib.Path) -> str:
    """Hash of file bytes under root (for differential state tomography)."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts:
            h.update(str(p.relative_to(root)).encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()


def diff_states(before: str, after: str) -> bool:
    """True if state changed (Mealy-style transition observed)."""
    return before != after
