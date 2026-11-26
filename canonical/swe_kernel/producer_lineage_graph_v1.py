#!/usr/bin/env python3
"""Interprocedural guarded causal data-flow & producer-lineage graph.

THE PROBLEM (measured, `the_value_that_was_rejected_had_a_producer_v1.py`):
in 82% of value failures the defective producer has **already returned** by the
time the assertion fires.  A stack trace therefore names the *consumer* and is
structurally blind to the cause.  Localisation that follows the traceback
arrests the wrong function.

THE TWO HALVES:

**Static (`ProducerLineageGraph`)** -- extends `IncrementalSemanticGraph`'s file
discovery with a def-use graph over the Guarded Meaning IR.  Every SSA
definition and every call site becomes a node/edge, and a ``return`` in a
callee is connected to the caller's use of that call.  So the edge
``callee.return -> caller.local`` exists *before anything runs*, which is what
lets a value be traced backward across function and file boundaries.

**Dynamic (`ReturnLineageTracer`)** -- a `sys.settrace` hook that records every
``return`` event with the returned object's ``id()``.  When a later assertion
rejects a value, the producer is found by identity, not by walking a stack that
has already unwound.  ``explain(value)`` answers "who made this?" for a frame
that no longer exists.

Both halves are read-only: no subprocess, no disk write, no network, no model.
Authority: NONE.
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import pathlib
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from canonical.swe_kernel import guarded_meaning_ir_v1 as mir

SCHEMA = "PROJECT_BRAIN_PRODUCER_LINEAGE_GRAPH_V1"

_TRACE_LOCAL = threading.local()
_THIS_FILE = str(pathlib.Path(__file__).resolve())
#: modules whose frames are never producers for our purposes
_NOISE_MODULES = frozenset({"_pytest", "pytest", "pluggy", "py", "unittest"})

# --------------------------------------------------------------------------- #
# 1. Static graph
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProducerNode:
    key: str
    file: str
    function: str
    name: str
    term: mir.Term
    guards: tuple[str, ...] = ()
    region: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"key": self.key, "file": self.file, "function": self.function,
                "name": self.name, "term": str(self.term), "guards": list(self.guards)}


@dataclass(frozen=True)
class LineageEdge:
    src: str
    dst: str
    kind: str      # defines | uses | calls | returns | guards | raises
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _free_vars(t: Any, out: set[str] | None = None) -> set[str]:
    out = set() if out is None else out
    if isinstance(t, mir.Term):
        if t.op == "var" and t.args:
            out.add(str(t.args[0]))
        elif t.op != "lambda":
            for a in t.args:
                _free_vars(a, out)
    return out


class ProducerLineageGraph:
    """Def-use + call/return + guard graph over one or more ``MirModule``s."""

    def __init__(self, mods: Mapping[str, mir.MirModule]) -> None:
        self.mods = dict(mods)
        self.nodes: dict[str, ProducerNode] = {}
        self.edges: list[LineageEdge] = []
        self._by_func: dict[str, list[ProducerNode]] = {}
        self._by_name: dict[str, list[ProducerNode]] = {}
        self._callers: dict[str, set[str]] = {}
        self._returns: dict[str, set[str]] = {}
        self._ret_of: dict[str, str] = {}
        self._defs_of: dict[tuple[str, str], list[ProducerNode]] = {}
        self._build()

    # -- construction ----------------------------------------------------- #
    def _node_key(self, file: str, function: str, name: str, term: mir.Term) -> str:
        h = hashlib.sha256(str(term).encode("utf-8", errors="replace")).hexdigest()[:10]
        return f"{file}::{function}::{name}#{h}"

    def _build(self) -> None:
        # ---- 1. one node per function's return value ----
        for fname, mod in self.mods.items():
            for qname, meta in mod.functions.items():
                value = meta.get("value")
                if value is None:
                    continue
                ret_key = f"{fname}::{qname}::<ret>"
                self.nodes[ret_key] = ProducerNode(
                    ret_key, fname, qname, "<ret>", value, (), str(meta.get("region") or ""))
                self._by_func.setdefault(qname, []).append(self.nodes[ret_key])
                self._ret_of[qname] = ret_key
                # a parameter IS a definition of the callee's binding, so it must
                # be addressable in the lineage query
                for pname in (meta.get("params") or []):
                    pterm = mir.var(str(pname))
                    pkey = self._node_key(fname, qname, str(pname), pterm)
                    pnode = ProducerNode(pkey, fname, qname, str(pname), pterm, (), "")
                    self.nodes[pkey] = pnode
                    self._by_func.setdefault(qname, []).append(pnode)
                    self._defs_of.setdefault((qname, str(pname)), []).append(pnode)
        # ---- 2. one node per SSA definition ----
        for fname, mod in self.mods.items():
            for d in mod.defs:
                key = self._node_key(fname, d.function, d.name, d.term)
                node = ProducerNode(key, fname, d.function, d.name, d.term, d.guards, d.region)
                self.nodes[key] = node
                self._by_func.setdefault(d.function, []).append(node)
                self._by_name.setdefault(d.name, []).append(node)
                self._defs_of.setdefault((d.function, d.name), []).append(node)
                # a definition *uses* every free variable of its term
                for fv in sorted(_free_vars(d.term)):
                    for producer in self._by_name.get(fv, ()):
                        if producer.function == d.function:
                            self.edges.append(LineageEdge(producer.key, key, "uses", fv))
        # ---- 3. call -> return, argument -> parameter, return -> local ----
        for fname, mod in self.mods.items():
            for c in mod.calls:
                self._callers.setdefault(c.callee, set()).add(c.function)
                self._returns.setdefault(c.callee, set()).add(c.function)
                ret_key = self._ret_of.get(c.callee)
                if ret_key is None:
                    continue
                self.edges.append(
                    LineageEdge(f"{fname}::{c.function}::CALL#{c.callee}", ret_key,
                                "calls", c.callee))
                params = (mod.functions.get(c.callee) or {}).get("params") or []
                for i, arg in enumerate(c.args):
                    if arg.op == "var" and arg.args and i < len(params):
                        pname = str(params[i])
                        self.edges.append(
                            LineageEdge(f"{fname}::{c.function}::{arg.args[0]}",
                                        f"{fname}::{c.callee}::{pname}", "arg", pname))
        for fname, mod in self.mods.items():
            for d in mod.defs:
                t = d.term
                if isinstance(t, mir.Term) and t.op == "call" and t.args:
                    fn = t.args[0]
                    callee = str(fn.args[0]) if isinstance(fn, mir.Term) and fn.op == "var" else None
                    ret_key = self._ret_of.get(callee or "")
                    if ret_key is None:
                        continue
                    # the call's value is produced by the callee's return, and is
                    # consumed here -- this edge exists before anything runs
                    self.edges.append(
                        LineageEdge(ret_key, self._node_key(fname, d.function, d.name, t),
                                    "returns", str(callee)))

    # -- queries ---------------------------------------------------------- #
    def functions(self) -> list[str]:
        return sorted(self._by_func)

    def definitions_of(self, function: str, name: str) -> list[ProducerNode]:
        return list(self._defs_of.get((function, name), ()))

    def callers_of(self, callee: str) -> list[str]:
        return sorted(self._callers.get(callee, ()))

    def producers_of(self, function: str, name: str) -> list[ProducerNode]:
        """Definitions of ``name`` in ``function``, newest last."""
        return self.definitions_of(function, name)

    def lineage(self, function: str, name: str, *, max_depth: int = 8) -> dict[str, Any]:
        """Backward slice: every producer that can reach ``function::name``.

        Follows ``uses`` edges backward, crosses ``calls``/``returns`` edges into
        callees, and records the branch guards on each hop -- so the answer is a
        *guarded causal chain*, not a bag of names.
        """
        start = self.definitions_of(function, name)
        if not start:
            return {"schema": SCHEMA, "found": False, "reason": "NO_SUCH_DEFINITION",
                    "function": function, "name": name, "chain": []}
        preds: dict[str, list[tuple[LineageEdge, ProducerNode]]] = {}
        for e in self.edges:
            preds.setdefault(e.dst, []).append((e, self.nodes.get(e.src)))
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        frontier = [(n, 0, None) for n in start]
        while frontier:
            node, depth, via = frontier.pop(0)
            if node.key in seen or depth > max_depth:
                continue
            seen.add(node.key)
            row: dict[str, Any] = {"depth": depth, **node.as_dict()}
            if via:
                row["via"] = via
            chain.append(row)
            for e, src in preds.get(node.key, ()):
                if src is not None and src.key not in seen:
                    frontier.append((src, depth + 1, e.kind))
        return {
            "schema": SCHEMA, "found": True, "function": function, "name": name,
            "chain": chain,
            "guards": sorted({g for row in chain for g in row.get("guards") or ()}),
            # every hop is a producer, including a callee's return value
            "producers": [row["key"] for row in chain if row.get("key")],
        }

    def trace_value(self, function: str, name: str, *, max_depth: int = 8) -> dict[str, Any]:
        """Alias of :meth:`lineage` with the naming used by the repair probes."""
        return self.lineage(function, name, max_depth=max_depth)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "files": sorted(self.mods),
            "functions": self.functions(),
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "edge_kinds": sorted({e.kind for e in self.edges}),
        }


# --------------------------------------------------------------------------- #
# 2. Dynamic return-producer tracing
# --------------------------------------------------------------------------- #


@dataclass
class ProducerEvent:
    """One ``return`` observed at runtime, with the object it produced."""

    kind: str                 # return | exception
    function: str
    filename: str
    lineno: int
    value: Any
    value_id: int
    repr: str
    callers: tuple[str, ...] = ()
    frame_locals: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "function": self.function, "filename": self.filename,
                "lineno": self.lineno, "value_id": self.value_id, "repr": self.repr,
                "callers": list(self.callers), "frame_locals": dict(self.frame_locals)}


class ReturnLineageTracer:
    """``sys.settrace`` recorder for return values, usable as a context manager.

    Records ``id(value)`` for every returned object, so a value rejected later
    can be traced to the frame that produced it **even though that frame has
    already returned**.  The tracer never mutates the traced program: it only
    reads ``frame.f_locals`` and stores references.
    """

    def __init__(self, *, max_events: int = 20000, keep_values: bool = True) -> None:
        self.events: list[ProducerEvent] = []
        self.by_id: dict[int, list[int]] = {}
        self._max = int(max_events)
        self._keep = bool(keep_values)
        self._stack: list[str] = []
        self._prev: Any = None
        self._active = False

    # -- context manager -------------------------------------------------- #
    def __enter__(self) -> "ReturnLineageTracer":
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    def start(self) -> None:
        if self._active:
            return
        self._prev = sys.gettrace()
        self._active = True
        _TRACE_LOCAL.tracer = self
        sys.settrace(self._trace)

    def stop(self) -> None:
        if not self._active:
            return
        sys.settrace(self._prev)
        self._prev = None
        self._active = False
        if getattr(_TRACE_LOCAL, "tracer", None) is self:
            _TRACE_LOCAL.tracer = None

    # -- the hook --------------------------------------------------------- #
    def _trace(self, frame: Any, event: str, arg: Any) -> Any:
        if not self._active:
            return None
        if str(frame.f_code.co_filename) == _THIS_FILE:
            return None          # never trace the tracer
        mod_name = str(frame.f_globals.get("__name__", ""))
        if mod_name.split(".")[0] in _NOISE_MODULES:
            # test-framework frames can *return the very object* a rejected
            # assertion message carried (pytest's format_explanation does);
            # recording them would name a fake producer
            return None
        if event == "call":
            name = frame.f_code.co_name
            self._stack.append(name)
            return self._trace
        if event == "return":
            if self._stack:
                self._stack.pop()
            if len(self.events) < self._max:
                self._record("return", frame, arg)
            return self._trace
        if event == "exception":
            if len(self.events) < self._max:
                self._record("exception", frame, arg[1] if isinstance(arg, tuple) else arg)
            return self._trace
        return self._trace

    def _record(self, kind: str, frame: Any, value: Any) -> None:
        try:
            vid = id(value)
        except Exception:  # noqa: BLE001
            return
        callers = tuple(self._stack[-6:])
        loc: dict[str, str] = {}
        try:
            for k, v in list(frame.f_locals.items())[:16]:
                loc[str(k)] = _short_repr(v)
        except Exception:  # noqa: BLE001
            pass
        ev = ProducerEvent(
            kind=kind,
            function=str(frame.f_code.co_name),
            filename=str(frame.f_code.co_filename),
            lineno=int(frame.f_lineno),
            value=value if self._keep else None,
            value_id=vid,
            repr=_short_repr(value),
            callers=callers,
            frame_locals=loc,
        )
        self.events.append(ev)
        self.by_id.setdefault(vid, []).append(len(self.events) - 1)

    # -- queries ---------------------------------------------------------- #
    def producers_of(self, value: Any) -> list[ProducerEvent]:
        return [self.events[i] for i in self.by_id.get(id(value), ())]

    def last_producer(self, value: Any) -> ProducerEvent | None:
        idxs = self.by_id.get(id(value))
        return self.events[idxs[-1]] if idxs else None

    def explain(self, value: Any) -> dict[str, Any]:
        """Who produced ``value``?  Answers for a frame that already returned.

        Identity (``id()``) is authoritative.  A test framework that rewrites
        assertions can destroy it -- pytest replaces ``assert x == y, obj`` with
        a *formatted string* -- so there is a labelled ``repr`` fallback.  The
        receipt always says which one matched, so a repr match is never passed
        off as an identity match.
        """
        evs = self.producers_of(value)
        matched_by = "identity"
        if not evs:
            target = _short_repr(value)
            bare = target.strip("\"'")
            evs = [e for e in self.events
                   if e.kind == "return"
                   and (e.repr == target or bare in e.repr or e.repr in bare)]
            matched_by = "repr"
        if not evs:
            return {"schema": SCHEMA, "found": False, "reason": "NO_RECORDED_PRODUCER",
                    "repr": _short_repr(value), "events_seen": len(self.events),
                    "all_producers": []}
        last = evs[-1]
        return {
            "schema": SCHEMA, "found": True, "matched_by": matched_by,
            "producer": last.as_dict(),
            "all_producers": [e.as_dict() for e in evs],
            "returned_before_rejection": True,
            "note": ("the producer frame has already returned; a stack trace at the "
                     "assertion site cannot name it, identity can"),
        }

    def summary(self) -> dict[str, Any]:
        kinds: dict[str, int] = {}
        for e in self.events:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        return {"schema": SCHEMA, "events": len(self.events), "kinds": kinds,
                "distinct_values": len(self.by_id)}


def _short_repr(v: Any, limit: int = 160) -> str:
    try:
        s = repr(v)
    except Exception:  # noqa: BLE001
        s = f"<unrepresentable {type(v).__name__}>"
    return s if len(s) <= limit else s[: limit - 3] + "..."


# --------------------------------------------------------------------------- #
# 3. Whole-workspace construction (extends IncrementalSemanticGraph discovery)
# --------------------------------------------------------------------------- #

_POLYGLOT = {".py", ".c", ".h", ".cpp", ".cc", ".hpp", ".hh", ".js", ".jsx",
             ".mjs", ".cjs", ".ts", ".tsx"}


def build_lineage_graph(root: str | pathlib.Path, *, scope: str = ".",
                        max_files: int = 400) -> ProducerLineageGraph:
    """Discover sources with ``IncrementalSemanticGraph`` then lower + link them."""
    from canonical.swe_kernel.incremental_semantic_graph_v1 import IncrementalSemanticGraph

    g = IncrementalSemanticGraph(pathlib.Path(root).resolve())
    mods: dict[str, mir.MirModule] = {}
    for _abs, rel, _mt, _sz, _sha in g._discover_files(scope)[:max_files]:
        if pathlib.Path(rel).suffix.lower() not in _POLYGLOT:
            continue
        try:
            mods[rel] = mir.lower_file(_abs)
        except Exception:  # noqa: BLE001 - an unparsable file must not stop the graph
            continue
    return ProducerLineageGraph(mods)


def build_lineage_graph_from_sources(sources: Mapping[str, str]) -> ProducerLineageGraph:
    return ProducerLineageGraph(mir.lower_sources(sources))


# --------------------------------------------------------------------------- #
# 4. One-call diagnostics
# --------------------------------------------------------------------------- #


def trace_and_explain(fn: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Run ``fn``; if it raises, name the producer of the offending value.

    The rejection value is taken from the exception message when it carries one
    (``assert x == y`` style), else from the exception args.  The result always
    reports the recorded producer chain, never a guess.
    """
    failure: BaseException | None = None
    value: Any = None
    with ReturnLineageTracer() as tr:
        try:
            value = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - the failure IS the result
            failure = exc
    # tracing is OFF here: inspecting the exception must not manufacture a
    # bogus "producer" out of this function's own return
    if failure is not None:
        return {
            "schema": SCHEMA, "raised": True, "exception": type(failure).__name__,
            "message": str(failure)[:400],
            "trace": tr.summary(),
            "explain": tr.explain(_exc_value(failure)),
            "events": [e.as_dict() for e in tr.events[-12:]],
        }
    return {
        "schema": SCHEMA, "raised": False, "value_repr": _short_repr(value),
        "trace": tr.summary(),
        "explain": tr.explain(value),
        "events": [e.as_dict() for e in tr.events[-12:]],
    }


def _exc_value(exc: BaseException) -> Any:
    args = getattr(exc, "args", ())
    for a in args:
        if not isinstance(a, str):
            return a
    return args[0] if args else exc


def explain_assertion(source: str, *, filename: str = "<probe>") -> dict[str, Any]:
    """Compile ``source`` (which must raise) and explain the offending value."""
    code = compile(source, filename, "exec")
    ns: dict[str, Any] = {"__name__": "__lineage_probe__"}
    failure: BaseException | None = None
    with ReturnLineageTracer() as tr:
        try:
            exec(code, ns)  # noqa: S102 - caller-supplied probe source, by contract
        except Exception as exc:  # noqa: BLE001
            failure = exc
    if failure is not None:
        return {"schema": SCHEMA, "raised": True, "exception": type(failure).__name__,
                "message": str(failure)[:400], "trace": tr.summary(),
                "explain": tr.explain(_exc_value(failure))}
    return {"schema": SCHEMA, "raised": False, "trace": tr.summary()}


__all__ = [
    "SCHEMA", "ProducerNode", "LineageEdge", "ProducerLineageGraph",
    "ProducerEvent", "ReturnLineageTracer", "build_lineage_graph",
    "build_lineage_graph_from_sources", "trace_and_explain", "explain_assertion",
]


def self_check() -> dict[str, Any]:
    """Two files, one returned value, one assertion downstream -- and one decoy.

    The module's claim is that the *producer* can be named from the consumer's failure. The decoy
    below recomputes the same expression inline: the terms are identical, the causal edge is not,
    and a graph that reported an edge there would be pointing at a function that never ran for that
    value. That is the whole difference between lineage and pattern matching.
    """
    import json as _json

    failures: list[str] = []

    def check(label: str, ok: bool) -> None:
        if not ok:
            failures.append(label)

    linked = {
        "a.py": "def produce(x):\n    return x * 2 + 1\n",
        "b.py": "from a import produce\n\ndef consume(x):\n    v = produce(x)\n"
                "    assert v > 10\n    return v\n",
    }
    graph = build_lineage_graph_from_sources(linked)
    cross_file = [
        edge for edge in graph.edges
        if edge.kind == "returns" and edge.src.split("::")[0] != edge.dst.split("::")[0]
    ]
    check("cross-file return edge is recorded", len(cross_file) == 1)
    check("the edge starts at the producer's return",
          bool(cross_file) and cross_file[0].src.startswith("a.py::produce::"))
    check("the edge ends at the consumer's binding",
          bool(cross_file) and cross_file[0].dst.startswith("b.py::consume::v"))
    check("both endpoints exist as nodes",
          bool(cross_file) and cross_file[0].src in graph.nodes
          and cross_file[0].dst in graph.nodes)
    check("the caller->callee edge is recorded",
          any(edge.kind == "calls" and edge.detail == "produce" for edge in graph.edges))

    decoy = {"b.py": "def consume(x):\n    v = x * 2 + 1\n    assert v > 10\n    return v\n"}
    decoy_graph = build_lineage_graph_from_sources(decoy)
    check("negative control: an inline copy of the same expression earns no edge",
          decoy_graph.edges == [])
    check("negative control: the decoy still parses into nodes",
          len(decoy_graph.nodes) >= 2)

    payload = _json.loads(_json.dumps(graph.to_dict()))
    check("to_dict is JSON-serialisable and reports the return edge",
          "returns" in payload.get("edge_kinds", [])
          and payload.get("edges") == len(graph.edges))

    total = 8
    return {
        "schema": "BRAIN_PRODUCER_LINEAGE_GRAPH_V1_SELF_CHECK",
        "checks": total,
        "passed": total - len(failures),
        "failures": failures,
        "verdict": "SELF_CHECK_PASS" if not failures else "SELF_CHECK_FAIL",
    }
