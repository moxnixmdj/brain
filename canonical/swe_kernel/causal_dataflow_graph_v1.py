#!/usr/bin/env python3
"""Inter-Procedural Cross-File Data-Flow & Causal Dual-Slicing Graph (`causal_dataflow_graph_v1`) — Leap 1.

Inspired by ARISE (arXiv:2605.03117, May 2026) and CausalRepair (ISSTA 2026, arXiv:2608.10613).
Builds a unified statement-level Program Dependence Graph (PDG) across an entire multi-file,
polyglot repository (Python, C, C++, JavaScript, TypeScript, Go, Rust) directly from `SemanticIR`:

  - Intra-procedural `DATA_FLOW` (reaching definitions across assignments, branches, loops, params)
  - Intra-procedural `CONTROL_DEP` (guards, branches, and loops controlling body statements)
  - Inter-procedural `INTERPROC_ARG` (caller argument -> callee parameter across files)
  - Inter-procedural `INTERPROC_RET` (callee return -> caller receiver across files)
  - Cross-file `FIELD_FLOW` (struct/object field writes `obj.f = x` / `p->f = x` -> reads of `.f`)

Exposes:
  - `backward_causal_slice(file, line, var)` — traces data lineage backwards across N files from crash
  - `forward_impact_slice(file, line, var)` — computes all downstream callers/tests affected by an edit
  - `dual_slice(entry_points, sink)` — minimal causal neck between failing inputs and failure sink
  - `rank_root_causes(...)` — fuses static dual-slice with dynamic differential traces (pass vs fail)

Zero external model calls. Zero stored world facts. O(V + E) graph traversal (< 2 ms).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import re
import sys
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel import semantic_ir_v1 as sir

SCHEMA = "PROJECT_BRAIN_CAUSAL_DATAFLOW_GRAPH_V1"
MODEL_CALLS = 0


@dataclass(frozen=True)
class GraphNode:
    node_id: str  # e.g. "file.py::func::L42::S7" or "file.py::func::PARAM::x"
    file: str
    func: str
    line: int
    kind: str  # PARAM | ASSIGN | AUG_ASSIGN | RETURN | BRANCH | GUARD | LOOP | CALL_STMT | STORE_ATTR | STORE_INDEX | RAISE
    stmt_id: int = 0
    var: str = ""
    source_text: str = ""


@dataclass(frozen=True)
class CausalEdge:
    src: str  # producer node_id
    dst: str  # consumer node_id
    edge_kind: str  # DATA_FLOW | CONTROL_DEP | INTERPROC_ARG | INTERPROC_RET | FIELD_FLOW
    label: str = ""  # variable name, param name, or field name


@dataclass
class SliceResult:
    target_nodes: list[str]
    visited_nodes: dict[str, GraphNode]
    hop_distance: dict[str, int]
    paths: dict[str, list[tuple[str, str, str]]]  # node_id -> [(node_id, edge_kind, label), ...]
    files_touched: list[str]
    functions_touched: list[str]


class CausalDataFlowGraph:
    """Multi-file statement-level inter-procedural data-flow & causal dependence graph."""

    def __init__(self, program: sir.IRProgram) -> None:
        self.program = program
        self.nodes: dict[str, GraphNode] = {}
        self.stmt_to_node: dict[tuple[str, int], str] = {}
        self.forward_edges: dict[str, list[CausalEdge]] = {}
        self.backward_edges: dict[str, list[CausalEdge]] = {}
        self.func_param_nodes: dict[str, list[tuple[str, str]]] = {}  # func_key -> [(param_name, node_id)]
        self.func_return_nodes: dict[str, list[str]] = {}  # func_key -> [node_id, ...]
        self.func_index_by_name: dict[str, list[str]] = {}  # bare name -> [func_key, ...]
        self.field_writers: dict[str, list[str]] = {}  # field_name -> [node_id, ...]
        self.field_readers: dict[str, list[str]] = {}  # field_name -> [node_id, ...]
        self._build()

    @staticmethod
    def _fn_key(fn: sir.IRFunction) -> str:
        return f"{fn.file}::{fn.qualname}"

    def _add_node(self, node: GraphNode) -> None:
        self.nodes[node.node_id] = node
        self.forward_edges.setdefault(node.node_id, [])
        self.backward_edges.setdefault(node.node_id, [])

    def _add_edge(self, src: str, dst: str, edge_kind: str, label: str = "") -> None:
        if src == dst or src not in self.nodes or dst not in self.nodes:
            return
        edge = CausalEdge(src, dst, edge_kind, label)
        fwd = self.forward_edges[src]
        if edge not in fwd:
            fwd.append(edge)
            self.backward_edges[dst].append(edge)

    def _build(self) -> None:
        # Pass 1: create nodes + intra-procedural DATA_FLOW & CONTROL_DEP edges
        all_fns = self.program.all_functions()
        for fn in all_fns:
            fkey = self._fn_key(fn)
            self.func_index_by_name.setdefault(fn.name, []).append(fkey)
            if fn.qualname != fn.name:
                self.func_index_by_name.setdefault(fn.qualname, []).append(fkey)
            self.func_param_nodes[fkey] = []
            self.func_return_nodes[fkey] = []

            reaching: dict[str, set[str]] = {}
            for p in fn.params:
                pnid = f"{fkey}::PARAM::{p}"
                self._add_node(GraphNode(pnid, fn.file, fn.qualname, fn.line, "PARAM", 0, p, f"param {p}"))
                self.func_param_nodes[fkey].append((p, pnid))
                reaching[p] = {pnid}

            self._build_block(fn, fkey, fn.stmts, reaching, control_parents=[])

        # Pass 2: Inter-procedural CALL edges (INTERPROC_ARG + INTERPROC_RET) across ALL files
        for fn in all_fns:
            fkey = self._fn_key(fn)
            # Re-walk statements to attach calls
            for st in fn.all_stmts():
                nid = self.stmt_to_node.get((fn.file, st.stmt_id))
                if not nid or st.expr is None:
                    continue
                for cname, call_args in st.expr.call_targets():
                    callee_keys = self._resolve_callees(cname, fn.file)
                    for ckey in callee_keys:
                        if ckey == fkey:
                            continue  # avoid trivial self-cycle domination (handled separately if needed)
                        cparams = self.func_param_nodes.get(ckey, [])
                        # Argument flow: caller statement -> callee formal parameters
                        # Skip `self` for method calls when arg count matches non-self params
                        param_offset = 1 if (cparams and cparams[0][0] == "self" and len(call_args) == len(cparams) - 1) else 0
                        for idx, _arg_e in enumerate(call_args):
                            pidx = idx + param_offset
                            if pidx < len(cparams):
                                pname, pnid = cparams[pidx]
                                self._add_edge(nid, pnid, "INTERPROC_ARG", f"{cname}({pname})")
                        if not call_args and cparams:
                            pname, pnid = cparams[0]
                            self._add_edge(nid, pnid, "INTERPROC_ARG", f"{cname}({pname})")
                        # Return flow: callee RETURN nodes -> caller statement
                        for rnid in self.func_return_nodes.get(ckey, []):
                            self._add_edge(rnid, nid, "INTERPROC_RET", f"ret:{cname}")

        # Pass 3: Cross-file FIELD_FLOW edges (struct/object field writes -> field reads)
        for fld, writers in self.field_writers.items():
            readers = self.field_readers.get(fld, [])
            if len(writers) * len(readers) > 400:
                continue  # bound pathological ultra-common fields like `.data` in huge repos
            for w in writers:
                for r in readers:
                    if w != r:
                        self._add_edge(w, r, "FIELD_FLOW", f".{fld}")

    def _resolve_callees(self, cname: str, caller_file: str) -> list[str]:
        direct = self.func_index_by_name.get(cname, [])
        if direct:
            return direct
        if "." in cname:
            tail = cname.rsplit(".", 1)[-1]
            return self.func_index_by_name.get(tail, [])
        return []

    def _build_block(
        self,
        fn: sir.IRFunction,
        fkey: str,
        stmts: Sequence[sir.IRStmt],
        reaching: dict[str, set[str]],
        control_parents: list[str],
    ) -> dict[str, set[str]]:
        cur = {k: set(v) for k, v in reaching.items()}
        for st in stmts:
            nid = f"{fkey}::L{st.line}::S{st.stmt_id}"
            self._add_node(GraphNode(
                nid, fn.file, fn.qualname, st.line, st.kind, st.stmt_id, st.target, st.source_text.strip()[:140]
            ))
            self.stmt_to_node[(fn.file, st.stmt_id)] = nid

            # Control dependence from enclosing branch/guard/loop
            for cp in control_parents:
                self._add_edge(cp, nid, "CONTROL_DEP", "ctrl")

            # Data-flow edges from reaching definitions of used variables
            for u in st.uses:
                for def_nid in cur.get(u, ()):
                    self._add_edge(def_nid, nid, "DATA_FLOW", u)

            # Record field writes & reads for cross-file FIELD_FLOW
            for _base, fld in st.attr_writes:
                if fld:
                    self.field_writers.setdefault(fld, []).append(nid)
            for _base, fld in st.attr_reads:
                if fld:
                    self.field_readers.setdefault(fld, []).append(nid)

            if st.kind == "RETURN":
                self.func_return_nodes[fkey].append(nid)

            # Recurse into structured control-flow children
            if st.kind in ("BRANCH", "GUARD"):
                then_r = self._build_block(fn, fkey, st.then_body, cur, control_parents + [nid])
                else_r = self._build_block(fn, fkey, st.else_body, cur, control_parents + [nid])
                # Merge reaching definitions from both branches (join)
                merged: dict[str, set[str]] = {}
                for k in set(then_r) | set(else_r):
                    merged[k] = set(then_r.get(k, ())) | set(else_r.get(k, ()))
                cur = merged
            elif st.kind == "LOOP" and st.loop is not None:
                # Loop induction var is defined by loop header
                for d in st.defs:
                    cur[d] = {nid}
                # Two-pass fixed-point over loop body so loop-carried back-edges are captured!
                body_r1 = self._build_block(fn, fkey, st.loop.body, cur, control_parents + [nid])
                for k, v in body_r1.items():
                    cur[k] = cur.get(k, set()) | v
                body_r2 = self._build_block(fn, fkey, st.loop.body, cur, control_parents + [nid])
                # Loop header also depends on loop-carried updates of vars in its condition
                for u in st.uses:
                    for def_nid in body_r2.get(u, ()):
                        self._add_edge(def_nid, nid, "DATA_FLOW", u)
                for k, v in body_r2.items():
                    cur[k] = cur.get(k, set()) | v
            else:
                # Update reaching defs for straight-line assignments
                for d in st.defs:
                    if st.kind == "STORE_INDEX":
                        cur.setdefault(d, set()).add(nid)
                    else:
                        cur[d] = {nid}
        return cur

    # -----------------------------------------------------------------------
    # Queries: Backward Lineage, Forward Impact, Dual-Slicing
    # -----------------------------------------------------------------------

    def nodes_at(self, file: str, line: int | None = None, func: str | None = None, var: str | None = None) -> list[str]:
        out: list[str] = []
        for nid, nd in self.nodes.items():
            if file and not (nd.file == file or nd.file.endswith("/" + file) or file.endswith("/" + nd.file)):
                continue
            if func and nd.func != func and not nd.func.endswith("." + func):
                continue
            if line is not None and nd.line != line:
                continue
            if var is not None and nd.var != var and var not in nd.source_text:
                continue
            out.append(nid)
        # If exact line matched nothing, pick nearest line in same file (within +/- 2 lines)
        if not out and line is not None:
            best_d = 3
            for nid, nd in self.nodes.items():
                if file and not (nd.file == file or nd.file.endswith("/" + file)):
                    continue
                d = abs(nd.line - line)
                if d < best_d:
                    best_d = d
                    out = [nid]
                elif d == best_d:
                    out.append(nid)
        return sorted(out)

    def _bfs(
        self,
        seeds: Sequence[str],
        *,
        backward: bool,
        max_hops: int = 32,
        allowed_edges: frozenset[str] | None = None,
    ) -> SliceResult:
        adj = self.backward_edges if backward else self.forward_edges
        visited: dict[str, GraphNode] = {}
        hops: dict[str, int] = {}
        paths: dict[str, list[tuple[str, str, str]]] = {}
        q: deque[str] = deque()

        valid_seeds = [s for s in seeds if s in self.nodes]
        for s in valid_seeds:
            visited[s] = self.nodes[s]
            hops[s] = 0
            paths[s] = [(s, "SEED", "")]
            q.append(s)

        while q:
            u = q.popleft()
            d = hops[u]
            if d >= max_hops:
                continue
            for edge in adj.get(u, ()):
                if allowed_edges and edge.edge_kind not in allowed_edges:
                    continue
                v = edge.src if backward else edge.dst
                if v not in visited:
                    visited[v] = self.nodes[v]
                    hops[v] = d + 1
                    paths[v] = paths[u] + [(v, edge.edge_kind, edge.label)]
                    q.append(v)

        files = sorted({nd.file for nd in visited.values()})
        funcs = sorted({f"{nd.file}::{nd.func}" for nd in visited.values()})
        return SliceResult(valid_seeds, visited, hops, paths, files, funcs)

    def backward_causal_slice(
        self,
        file: str,
        line: int | None = None,
        *,
        func: str | None = None,
        var: str | None = None,
        max_hops: int = 32,
    ) -> SliceResult:
        """Trace ALL upstream statements across ALL files that causally feed `(file, line, var)`."""
        seeds = self.nodes_at(file, line=line, func=func, var=var)
        return self._bfs(seeds, backward=True, max_hops=max_hops)

    def forward_impact_slice(
        self,
        file: str,
        line: int | None = None,
        *,
        func: str | None = None,
        var: str | None = None,
        max_hops: int = 32,
    ) -> SliceResult:
        """Trace ALL downstream statements across ALL files impacted by changing `(file, line, var)`."""
        seeds = self.nodes_at(file, line=line, func=func, var=var)
        return self._bfs(seeds, backward=False, max_hops=max_hops)

    def dual_slice(
        self,
        source_seeds: Sequence[str],
        sink_seeds: Sequence[str],
        *,
        max_hops: int = 32,
    ) -> dict[str, Any]:
        """CausalRepair Dual-Slice: intersect forward slice from inputs & backward slice from failure sink."""
        fwd = self._bfs(source_seeds, backward=False, max_hops=max_hops)
        bwd = self._bfs(sink_seeds, backward=True, max_hops=max_hops)
        common_ids = sorted(set(fwd.visited_nodes) & set(bwd.visited_nodes))
        # Fall back to backward slice if entry seeds did not statically reach sink (e.g. dynamic dispatch)
        effective_ids = common_ids if common_ids else sorted(bwd.visited_nodes)
        ranked = sorted(
            effective_ids,
            key=lambda nid: (
                0 if nid in common_ids else 1,
                bwd.hop_distance.get(nid, 999),
                fwd.hop_distance.get(nid, 999),
                self.nodes[nid].file,
                self.nodes[nid].line,
            ),
        )
        return {
            "schema": SCHEMA,
            "dual_intersection_count": len(common_ids),
            "backward_count": len(bwd.visited_nodes),
            "forward_count": len(fwd.visited_nodes),
            "files_in_causal_chain": sorted({self.nodes[n].file for n in ranked}),
            "functions_in_causal_chain": sorted({f"{self.nodes[n].file}::{self.nodes[n].func}" for n in ranked}),
            "ranked_nodes": [
                {
                    "node_id": nid,
                    "file": self.nodes[nid].file,
                    "func": self.nodes[nid].func,
                    "line": self.nodes[nid].line,
                    "kind": self.nodes[nid].kind,
                    "in_dual_neck": nid in common_ids,
                    "hops_to_sink": bwd.hop_distance.get(nid, -1),
                    "hops_from_source": fwd.hop_distance.get(nid, -1),
                    "source_text": self.nodes[nid].source_text,
                    "lineage_to_sink": bwd.paths.get(nid, []),
                }
                for nid in ranked
            ],
        }

    def rank_root_causes(
        self,
        sink_file: str,
        sink_line: int,
        *,
        failing_lines: Mapping[str, set[int]] | None = None,
        passing_lines: Mapping[str, set[int]] | None = None,
        divergent_vars: Mapping[tuple[str, str], set[str]] | None = None,
        entry_file: str | None = None,
        entry_func: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fuse static cross-file causal lineage with differential execution spectra & value divergence."""
        bwd = self.backward_causal_slice(sink_file, sink_line)
        entry_seeds = self.nodes_at(entry_file, func=entry_func) if entry_file else []
        fwd = self._bfs(entry_seeds, backward=False) if entry_seeds else None
        dual_set = (set(bwd.visited_nodes) & set(fwd.visited_nodes)) if fwd else set(bwd.visited_nodes)

        scored: list[dict[str, Any]] = []
        for nid, nd in bwd.visited_nodes.items():
            if nd.kind == "PARAM":
                continue
            hops = bwd.hop_distance.get(nid, 99)
            in_dual = nid in dual_set
            # Compute Ochiai-like differential boost when execution spectra are provided
            ef = 1.0 if (failing_lines and nd.line in failing_lines.get(nd.file, ())) else 0.0
            ep = 1.0 if (passing_lines and nd.line in passing_lines.get(nd.file, ())) else 0.0
            ochiai = (ef / math.sqrt(ef + ep)) if ef > 0 else 0.0
            # Value divergence boost (variable at this node had distinct value in pass vs fail!)
            dvars = (divergent_vars or {}).get((nd.file, nd.func), set())
            div_hit = 1.0 if (nd.var in dvars or any(v in nd.source_text for v in dvars)) else 0.0
            # Structural producer/guard score (upstream calculations, guards, loops are prime root causes)
            kind_bonus = 0.35 if nd.kind in ("ASSIGN", "AUG_ASSIGN", "GUARD", "BRANCH", "LOOP", "RETURN") else 0.1
            # Do NOT blindly force crash site to beat upstream root cause when upstream has stronger divergence!
            score = (
                (2.0 if in_dual else 0.5)
                + 2.5 * ochiai
                + 2.0 * div_hit
                + kind_bonus
                + (1.0 / (1.0 + 0.25 * hops))
            )
            scored.append({
                "node_id": nid,
                "file": nd.file,
                "func": nd.func,
                "line": nd.line,
                "kind": nd.kind,
                "score": round(score, 4),
                "hops_to_sink": hops,
                "in_dual_neck": in_dual,
                "ochiai": round(ochiai, 3),
                "divergent_var_hit": bool(div_hit),
                "source_text": nd.source_text,
                "lineage_to_sink": [p[0] for p in bwd.paths.get(nid, [])],
            })
        scored.sort(key=lambda r: (-r["score"], r["hops_to_sink"], r["file"], r["line"]))
        return scored


# ---------------------------------------------------------------------------
# Traceback & Crash-Site Extractor (Python, GCC/ASan/UBSan, Node.js)
# ---------------------------------------------------------------------------

_PY_TB_RE = re.compile(r'File "([^"]+)", line (\d+)(?:, in ([A-Za-z0-9_<>.]+))?')
_ASAN_TB_RE = re.compile(r'#\d+\s+0x[0-9a-fA-F]+\s+in\s+([A-Za-z_][\w:<>]*)\s+([^:\s]+\.(?:c|h|cpp|cc|hpp)):(\d+)')
_UBSAN_RE = re.compile(r'([^:\s]+\.(?:c|h|cpp|cc|hpp)):(\d+):\d+:\s+runtime error:')
_NODE_TB_RE = re.compile(r'at\s+(?:([A-Za-z0-9_.$]+)\s+\()?([^():\s]+\.(?:js|mjs|cjs|ts)):(\d+):\d+\)?')


def extract_crash_frames(stderr_stdout: str) -> list[dict[str, Any]]:
    """Parse Python, C/C++ ASan/UBSan, or JS/Node stack frames from raw execution output."""
    frames: list[dict[str, Any]] = []
    for path, ln, fn in _PY_TB_RE.findall(stderr_stdout):
        frames.append({"file": path, "line": int(ln), "func": fn or "", "source": "python_tb"})
    for fn, path, ln in _ASAN_TB_RE.findall(stderr_stdout):
        frames.append({"file": path, "line": int(ln), "func": fn, "source": "asan_tb"})
    for path, ln in _UBSAN_RE.findall(stderr_stdout):
        frames.append({"file": path, "line": int(ln), "func": "", "source": "ubsan"})
    for fn, path, ln in _NODE_TB_RE.findall(stderr_stdout):
        frames.append({"file": path, "line": int(ln), "func": fn or "", "source": "node_tb"})
    return frames


def trace_python_execution(
    fn: Callable[..., Any],
    args: Sequence[Any],
    *,
    watched_files: Mapping[str, str] | None = None,
    step_quota: int = 25000,
) -> dict[str, Any]:
    """Fast in-process differential tracer recording executed lines + live local values across files."""
    exec_lines: dict[str, set[int]] = {}
    var_samples: dict[tuple[str, str], dict[str, Any]] = {}
    steps = [0]
    seen_states: dict[tuple[str, int], set[str]] = {}
    cycle_info: dict[str, Any] | None = None

    class _QuotaStop(BaseException):
        pass

    def _norm_file(fname: str) -> str | None:
        if not watched_files:
            return fname
        for rel, full in watched_files.items():
            if fname == full or fname.endswith("/" + rel) or fname == rel:
                return rel
        return None

    def _tracer(frame: Any, event: str, arg: Any) -> Any:
        nonlocal cycle_info
        if event not in ("line", "call", "return"):
            return _tracer
        rel = _norm_file(frame.f_code.co_filename)
        if rel is None:
            return _tracer
        steps[0] += 1
        if steps[0] > step_quota:
            raise _QuotaStop()
        ln = frame.f_lineno
        fn_name = frame.f_code.co_name
        exec_lines.setdefault(rel, set()).add(ln)
        if event == "line":
            # Compact frozen local snapshot for loop-cycle detection & value divergence
            loc_items = []
            samp = var_samples.setdefault((rel, fn_name), {})
            for k, v in list(frame.f_locals.items())[:16]:
                if k.startswith("__"):
                    continue
                rv = repr(v)[:64]
                samp[k] = rv
                loc_items.append((k, rv))
            if steps[0] > 400:
                sig = repr(tuple(sorted(loc_items)))
                bucket = seen_states.setdefault((rel, ln), set())
                if sig in bucket:
                    cycle_info = {"file": rel, "line": ln, "func": fn_name, "repeated_locals": dict(loc_items)}
                    raise _QuotaStop()
                if len(bucket) < 128:
                    bucket.add(sig)
        return _tracer

    status = "value"
    ret_val: Any = None
    exc_name: str | None = None
    old = sys.gettrace()
    sys.settrace(_tracer)
    try:
        ret_val = fn(*args)
    except _QuotaStop:
        status = "cycle" if cycle_info else "quota"
    except Exception as exc:
        status = "raised"
        exc_name = f"{type(exc).__name__}: {exc}"
    finally:
        sys.settrace(old)

    return {
        "status": status,
        "value": ret_val,
        "exception": exc_name,
        "steps": steps[0],
        "executed_lines": exec_lines,
        "var_samples": var_samples,
        "cycle": cycle_info,
    }
