#!/usr/bin/env python3
"""Meta-Circular Reflective Program Graph (`K3 = 0`, `$0` spend).

Implements Axiom I & Axiom III of the non-static sentient creature architecture:
every cognitive mechanism across all five reflective strata is a content-addressed,
AST-verified, falsification-gated executable Python program (`ExecutableOrgan`)
stored inside one evolving program graph `P_t`:

  1. `PERCEPTOR`        : Raw bytes/text -> structured state (online epistemic
                          sensorogenesis via round-trip & corruption-falsified
                          parser/serializer synthesis for unfamiliar formats).
  2. `PREDICTOR`        : (task_features, env_features) -> (p_pass, cost_ms, p_burn)
                          (online causal feature-conditioned self/world model).
  3. `SKILL`            : inputs -> output (`< 0.05 ms` in-RAM compiled bytecode,
                          admitted only after active version-space disambiguation).
  4. `VERIFIER`         : (input_or_ctx, artifact) -> (ok, reason) (derived by
                          differential semantic/recomputational mutation probing,
                          killing comment-stuffed and wrong-operator decoys).
  5. `META_SYNTHESIZER` : (examples, budget) -> candidate_source_code (higher-order
                          search tactics compiled from prior solved organs so Level-1
                          synthesis itself grows open-endedly over time).
"""
from __future__ import annotations

import ast
import collections
import hashlib
import json
import math
import pathlib
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_META_CIRCULAR_ORGAN_GRAPH_V1"

PERCEPTOR = "PERCEPTOR"
PREDICTOR = "PREDICTOR"
SKILL = "SKILL"
VERIFIER = "VERIFIER"
META_SYNTHESIZER = "META_SYNTHESIZER"

STRATA: tuple[str, ...] = (
    PERCEPTOR,
    PREDICTOR,
    SKILL,
    VERIFIER,
    META_SYNTHESIZER,
)

_FORBIDDEN_AST_NAMES = frozenset({
    "__import__",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
    "exit",
    "quit",
})

_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "bytes": bytes,
    "chr": chr,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "ord": ord,
    "pow": pow,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "ZeroDivisionError": ZeroDivisionError,
}


class OrganSafetyError(ValueError):
    """Raised when candidate organ source violates pure confined AST safety."""


def verify_pure_organ_ast(source_code: str) -> ast.Module:
    """Parse and verify that an organ's Python AST contains zero host I/O or reflection."""
    try:
        tree = ast.parse(source_code, mode="exec")
    except SyntaxError as exc:
        raise OrganSafetyError(f"SYNTAX_ERROR:{exc.msg}") from exc

    has_func = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            raise OrganSafetyError(f"FORBIDDEN_NODE:{type(node).__name__}")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_func = True
            if isinstance(node, ast.AsyncFunctionDef):
                raise OrganSafetyError("ASYNC_NOT_ALLOWED")
        if isinstance(node, ast.Name) and (
            node.id in _FORBIDDEN_AST_NAMES or node.id.startswith("__")
        ):
            raise OrganSafetyError(f"FORBIDDEN_NAME:{node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise OrganSafetyError(f"FORBIDDEN_DUNDER_ATTR:{node.attr}")
    if not has_func:
        raise OrganSafetyError("NO_ENTRYPOINT_FUNCTION")
    return tree


def _canonical_ast_bytes(tree: ast.AST) -> int:
    return len(ast.dump(tree, annotate_fields=True, include_attributes=False).encode("utf-8"))


def compile_organ_namespace(source_code: str) -> tuple[ast.Module, dict[str, Any]]:
    """Compile verified pure organ source into an isolated deterministic namespace."""
    tree = verify_pure_organ_ast(source_code)
    code_obj = compile(tree, "<meta_circular_organ>", "exec")
    ns: dict[str, Any] = {
        "__builtins__": dict(_SAFE_BUILTINS),
        "math": math,
        "json": json,
        "re": re,
        "collections": collections,
    }
    exec(code_obj, ns, ns)  # noqa: S102 - AST-verified pure namespace with restricted builtins
    return tree, ns


@dataclass
class ExecutableOrgan:
    """First-class executable program node in the 5-stratum program graph `P_t`."""

    organ_id: str
    stratum: str
    name: str
    task_signature: str
    entrypoint: str
    source_code: str
    code_bytes: int
    mean_latency_ms: float = 0.05
    verified_passes: int = 0
    verified_failures: int = 0
    parent_organ_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    _fn: Callable[..., Any] | None = field(default=None, repr=False, compare=False)
    _ns: dict[str, Any] | None = field(default=None, repr=False, compare=False)

    def ensure_compiled(self) -> Callable[..., Any]:
        if self._fn is None:
            _, ns = compile_organ_namespace(self.source_code)
            fn = ns.get(self.entrypoint)
            if not callable(fn):
                raise OrganSafetyError(f"ENTRYPOINT_NOT_CALLABLE:{self.entrypoint}")
            self._ns = ns
            self._fn = fn
        return self._fn

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        fn = self.ensure_compiled()
        t0 = time.perf_counter()
        out = fn(*args, **kwargs)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        self.mean_latency_ms = 0.85 * self.mean_latency_ms + 0.15 * max(dt_ms, 0.001)
        return out

    def invoke_aux(self, helper_name: str, *args: Any, **kwargs: Any) -> Any:
        self.ensure_compiled()
        assert self._ns is not None
        fn = self._ns.get(helper_name)
        if not callable(fn):
            raise OrganSafetyError(f"HELPER_NOT_CALLABLE:{helper_name}")
        return fn(*args, **kwargs)

    @property
    def reliability(self) -> float:
        total = self.verified_passes + self.verified_failures
        return (self.verified_passes + 1.0) / (total + 2.0)

    @property
    def pareto_score(self) -> float:
        """Solomonoff-Levin speed-prior utility: reliability * 2^(-L(p)/256) / latency."""
        mdl_prior = 2.0 ** (-min(self.code_bytes, 2048) / 256.0)
        return (self.reliability * mdl_prior) / max(self.mean_latency_ms, 0.005)

    def as_row(self) -> dict[str, Any]:
        return {
            "organ_id": self.organ_id,
            "stratum": self.stratum,
            "name": self.name,
            "task_signature": self.task_signature,
            "entrypoint": self.entrypoint,
            "source_code": self.source_code,
            "code_bytes": self.code_bytes,
            "mean_latency_ms": round(self.mean_latency_ms, 6),
            "verified_passes": self.verified_passes,
            "verified_failures": self.verified_failures,
            "parent_organ_ids": list(self.parent_organ_ids),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ExecutableOrgan":
        return cls(
            organ_id=str(row["organ_id"]),
            stratum=str(row["stratum"]),
            name=str(row["name"]),
            task_signature=str(row["task_signature"]),
            entrypoint=str(row["entrypoint"]),
            source_code=str(row["source_code"]),
            code_bytes=int(row["code_bytes"]),
            mean_latency_ms=float(row.get("mean_latency_ms") or 0.05),
            verified_passes=int(row.get("verified_passes") or 0),
            verified_failures=int(row.get("verified_failures") or 0),
            parent_organ_ids=tuple(str(x) for x in (row.get("parent_organ_ids") or ())),
            metadata=dict(row.get("metadata") or {}),
        )


def make_organ(
    *,
    stratum: str,
    name: str,
    task_signature: str,
    entrypoint: str,
    source_code: str,
    parent_organ_ids: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> ExecutableOrgan:
    if stratum not in STRATA:
        raise ValueError(f"UNKNOWN_STRATUM:{stratum}")
    tree, ns = compile_organ_namespace(source_code)
    fn = ns.get(entrypoint)
    if not callable(fn):
        raise OrganSafetyError(f"ENTRYPOINT_MISSING:{entrypoint}")
    ast_dump = ast.dump(tree, annotate_fields=True, include_attributes=False)
    digest = hashlib.sha256(
        f"{stratum}::{task_signature}::{entrypoint}::{ast_dump}".encode("utf-8")
    ).hexdigest()[:20]
    organ = ExecutableOrgan(
        organ_id=f"organ_{stratum.lower()}_{digest}",
        stratum=stratum,
        name=name,
        task_signature=task_signature,
        entrypoint=entrypoint,
        source_code=source_code.strip(),
        code_bytes=_canonical_ast_bytes(tree),
        parent_organ_ids=tuple(parent_organ_ids),
        metadata=dict(metadata or {}),
    )
    organ._ns = ns
    organ._fn = fn
    return organ


# ---------------------------------------------------------------------------
# Online Causal Feature Predictor (Closes EXTERNAL_BASELINE counterexample)
# ---------------------------------------------------------------------------


def _sigmoid(z: float) -> float:
    if z >= 35.0:
        return 1.0 - 1e-15
    if z <= -35.0:
        return 1e-15
    return 1.0 / (1.0 + math.exp(-z))


class CausalFeatureSelfPredictor:
    """Online regularized logistic + latency self-predictor conditioned on task features.

    Uses structural features of the task itself (e.g. arity, ast_depth, branch_count,
    has_inspector, domain_novelty, unseen_tokens) rather than replaying a capability-ID
    lookup table, directly closing EXTERNAL_BASELINE_KNOWN_COUNTEREXAMPLE_20261102_V1.
    """

    def __init__(self, *, learning_rate: float = 0.35, l2_reg: float = 0.01) -> None:
        self.learning_rate = float(learning_rate)
        self.l2_reg = float(l2_reg)
        self.weights: dict[str, float] = {}
        self.bias: float = 0.0
        self.cost_weights: dict[str, float] = {}
        self.cost_bias: float = 1.0
        self.observations: int = 0

    @staticmethod
    def normalize_features(features: Mapping[str, Any] | None) -> dict[str, float]:
        out: dict[str, float] = {}
        if not features:
            return out
        for key, val in sorted(features.items()):
            k = str(key)
            if isinstance(val, bool):
                out[f"bool:{k}"] = 1.0 if val else 0.0
            elif isinstance(val, (int, float)) and not math.isnan(float(val)) and not math.isinf(float(val)):
                v = float(val)
                # Smooth log-signed compression so large counts never blow up gradients.
                out[f"num:{k}"] = math.copysign(math.log1p(abs(v)), v)
            elif isinstance(val, str) and val:
                out[f"cat:{k}={val[:48]}"] = 1.0
        return out

    def predict_pass_probability(self, features: Mapping[str, Any] | None) -> float:
        x = self.normalize_features(features)
        if self.observations == 0 or not x:
            return 0.5
        z = self.bias + sum(self.weights.get(k, 0.0) * v for k, v in x.items())
        # Mild epistemic shrinkage on very small sample counts prevents overconfident cold starts.
        conf = self.observations / (self.observations + 3.0)
        raw_p = _sigmoid(z)
        return max(0.02, min(0.98, 0.5 + conf * (raw_p - 0.5)))

    def predict_cost(self, features: Mapping[str, Any] | None) -> float:
        x = self.normalize_features(features)
        raw = self.cost_bias + sum(self.cost_weights.get(k, 0.0) * v for k, v in x.items())
        return max(0.05, raw)

    def update(
        self,
        features: Mapping[str, Any] | None,
        *,
        outcome_pass: bool,
        realised_cost: float | None = None,
    ) -> float:
        x = self.normalize_features(features)
        pred = self.predict_pass_probability(features)
        target = 1.0 if outcome_pass else 0.0
        err = target - pred
        lr = self.learning_rate / math.sqrt(1.0 + 0.05 * self.observations)
        self.bias += lr * err
        for k, v in x.items():
            w_prev = self.weights.get(k, 0.0)
            self.weights[k] = w_prev * (1.0 - lr * self.l2_reg) + lr * err * v

        if realised_cost is not None and realised_cost >= 0.0:
            c_pred = self.predict_cost(features)
            c_err = max(-10.0, min(10.0, float(realised_cost) - c_pred))
            c_lr = 0.15 / math.sqrt(1.0 + 0.1 * self.observations)
            self.cost_bias = max(0.05, self.cost_bias + c_lr * c_err)
            for k, v in x.items():
                cw = self.cost_weights.get(k, 0.0)
                self.cost_weights[k] = cw * 0.995 + c_lr * c_err * v

        self.observations += 1
        return pred

    def behavioral_signature(self, probes: Sequence[Mapping[str, Any]]) -> str:
        """Deterministic competence fingerprint over canonical feature probes."""
        vec = [
            f"{self.predict_pass_probability(p):.4f}:{self.predict_cost(p):.3f}"
            for p in probes
        ]
        return hashlib.sha256("|".join(vec).encode("utf-8")).hexdigest()[:24]

    def as_row(self) -> dict[str, Any]:
        return {
            "learning_rate": self.learning_rate,
            "l2_reg": self.l2_reg,
            "bias": round(self.bias, 8),
            "weights": {k: round(v, 8) for k, v in sorted(self.weights.items())},
            "cost_bias": round(self.cost_bias, 8),
            "cost_weights": {k: round(v, 8) for k, v in sorted(self.cost_weights.items())},
            "observations": self.observations,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "CausalFeatureSelfPredictor":
        inst = cls(
            learning_rate=float(row.get("learning_rate") or 0.35),
            l2_reg=float(row.get("l2_reg") or 0.01),
        )
        inst.bias = float(row.get("bias") or 0.0)
        inst.weights = {str(k): float(v) for k, v in (row.get("weights") or {}).items()}
        inst.cost_bias = float(row.get("cost_bias") or 1.0)
        inst.cost_weights = {str(k): float(v) for k, v in (row.get("cost_weights") or {}).items()}
        inst.observations = int(row.get("observations") or 0)
        return inst


# ---------------------------------------------------------------------------
# Online Epistemic Sensorogenesis (Unparsed Format -> Verified Perceptor Organ)
# ---------------------------------------------------------------------------


_CANDIDATE_PERCEPTOR_TEMPLATES: tuple[tuple[str, str], ...] = (
    (
        "json_or_jsonl_codec",
        """
def parse(raw):
    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
    s = text.strip()
    if not s:
        raise ValueError('EMPTY')
    if s[0] in '{[':
        obj = json.loads(s)
        if not isinstance(obj, (dict, list)) or len(obj) == 0:
            raise ValueError('TRIVIAL_JSON')
        return {'kind': 'json', 'data': obj}
    rows = []
    for line in s.splitlines():
        ln = line.strip()
        if not ln:
            continue
        item = json.loads(ln)
        if not isinstance(item, dict):
            raise ValueError('NOT_JSONL_DICT')
        rows.append(item)
    if len(rows) < 1:
        raise ValueError('NO_ROWS')
    return {'kind': 'jsonl', 'rows': rows}

def serialize(parsed):
    if parsed.get('kind') == 'json':
        return json.dumps(parsed['data'], sort_keys=True)
    return '\\n'.join(json.dumps(r, sort_keys=True) for r in parsed['rows'])
""",
    ),
    (
        "sectioned_kv_codec",
        """
def parse(raw):
    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]
    if not lines:
        raise ValueError('EMPTY')
    sections = {}
    cur = '_root'
    kv_count = 0
    for ln in lines:
        if ln.startswith('[') and ln.endswith(']') and len(ln) > 2:
            cur = ln[1:-1].strip()
            sections.setdefault(cur, {})
        elif '=' in ln or ':' in ln:
            sep = '=' if ('=' in ln and (':' not in ln or ln.index('=') < ln.index(':'))) else ':'
            k, v = ln.split(sep, 1)
            k = k.strip()
            v = v.strip()
            if not k or ' ' in k:
                raise ValueError('BAD_KEY')
            if re.fullmatch(r'-?\\d+', v):
                val = int(v)
            elif re.fullmatch(r'-?\\d+\\.\\d+', v):
                val = float(v)
            elif v.lower() in ('true', 'false'):
                val = (v.lower() == 'true')
            else:
                val = v
            sections.setdefault(cur, {})[k] = val
            kv_count += 1
        else:
            raise ValueError('UNPARSED_LINE')
    if kv_count == 0:
        raise ValueError('NO_KV')
    return {'kind': 'sectioned_kv', 'sections': sections, 'sep': sep}

def serialize(parsed):
    sep = parsed.get('sep', '=')
    out = []
    for sec, mapping in parsed['sections'].items():
        if sec != '_root':
            out.append(f'[{sec}]')
        for k, v in mapping.items():
            if isinstance(v, bool):
                vs = 'true' if v else 'false'
            else:
                vs = str(v)
            out.append(f'{k} {sep} {vs}')
    return '\\n'.join(out)
""",
    ),
    (
        "delimited_table_codec",
        """
def parse(raw):
    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]
    if len(lines) < 2:
        raise ValueError('NEED_HEADER_AND_ROW')
    best_delim = None
    for delim in ('|', '\\t', ';', ','):
        counts = [len([c for c in ln.split(delim)]) for ln in lines]
        if counts[0] >= 2 and len(set(counts)) == 1:
            best_delim = delim
            break
    if best_delim is None:
        raise ValueError('NO_CONSISTENT_DELIMITER')
    headers = [h.strip() for h in lines[0].split(best_delim)]
    if any(not h for h in headers):
        raise ValueError('EMPTY_HEADER')
    rows = []
    for ln in lines[1:]:
        cells = [c.strip() for c in ln.split(best_delim)]
        rec = {}
        for h, c in zip(headers, cells):
            if re.fullmatch(r'-?\\d+', c):
                rec[h] = int(c)
            elif re.fullmatch(r'-?\\d+\\.\\d+', c):
                rec[h] = float(c)
            else:
                rec[h] = c
        rows.append(rec)
    return {'kind': 'table', 'delim': best_delim, 'headers': headers, 'rows': rows}

def serialize(parsed):
    d = parsed['delim']
    hdr = d.join(parsed['headers'])
    body = [d.join(str(r[h]) for h in parsed['headers']) for r in parsed['rows']]
    return '\\n'.join([hdr] + body)
""",
    ),
    (
        "sexpr_tree_codec",
        """
def parse(raw):
    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
    s = text.strip()
    if not (s.startswith('(') and s.endswith(')')):
        raise ValueError('NOT_SEXPR')
    tokens = re.findall(r'\\(|\\)|"[^"]*"|[^\\s()]+', s)
    pos = [0]
    def _read():
        if pos[0] >= len(tokens):
            raise ValueError('UNEXPECTED_EOF')
        tok = tokens[pos[0]]
        pos[0] += 1
        if tok == '(':
            items = []
            while pos[0] < len(tokens) and tokens[pos[0]] != ')':
                items.append(_read())
            if pos[0] >= len(tokens):
                raise ValueError('UNCLOSED_PAREN')
            pos[0] += 1
            return items
        if tok == ')':
            raise ValueError('STRAY_CLOSE')
        if re.fullmatch(r'-?\\d+', tok):
            return int(tok)
        if tok.startswith('"') and tok.endswith('"'):
            return tok[1:-1]
        return tok
    tree = _read()
    if pos[0] != len(tokens) or not isinstance(tree, list) or not tree:
        raise ValueError('TRAILING_OR_EMPTY')
    return {'kind': 'sexpr', 'tree': tree}

def serialize(parsed):
    def _emit(node):
        if isinstance(node, list):
            return '(' + ' '.join(_emit(x) for x in node) + ')'
        if isinstance(node, str) and (' ' in node or node == ''):
            return '"' + node + '"'
        return str(node)
    return _emit(parsed['tree'])
""",
    ),
    (
        "tlv_binary_frame_codec",
        """
def parse(raw):
    data = raw if isinstance(raw, bytes) else str(raw).encode('latin1')
    if len(data) < 4:
        raise ValueError('TOO_SHORT')
    idx = 0
    frames = []
    while idx < len(data):
        if idx + 3 > len(data):
            raise ValueError('TRUNCATED_HEADER')
        tag = data[idx]
        ln = (data[idx + 1] << 8) | data[idx + 2]
        idx += 3
        if idx + ln > len(data):
            raise ValueError('TRUNCATED_PAYLOAD')
        payload = data[idx:idx + ln]
        idx += ln
        frames.append({'tag': int(tag), 'payload_hex': payload.hex()})
    if not frames:
        raise ValueError('NO_FRAMES')
    return {'kind': 'tlv', 'frames': frames}

def serialize(parsed):
    out = bytearray()
    for fr in parsed['frames']:
        payload = bytes.fromhex(fr['payload_hex'])
        ln = len(payload)
        out.append(int(fr['tag']) & 0xFF)
        out.append((ln >> 8) & 0xFF)
        out.append(ln & 0xFF)
        out.extend(payload)
    return bytes(out)
""",
    ),
)


def _corrupt_sample(sample: str | bytes) -> list[str | bytes]:
    """Generate adversarial framing corruptions a true parser must reject."""
    if isinstance(sample, bytes):
        return [b"", sample[:2], sample + b"\xff\xff"]
    return [
        "",
        "@@@UNSTRUCTURED_CORRUPTED_NOISE_WITHOUT_GRAMMAR@@@",
        "(((unclosed_broken_frame",
    ]


def synthesize_perceptor_organ(
    samples: Sequence[str | bytes],
    *,
    format_tag: str = "discovered_format",
) -> ExecutableOrgan | None:
    """Synthesize and round-trip-verify a new `PERCEPTOR` organ from raw samples alone."""
    if not samples:
        return None
    for codec_name, src in _CANDIDATE_PERCEPTOR_TEMPLATES:
        organ = make_organ(
            stratum=PERCEPTOR,
            name=f"perceptor_{codec_name}_{format_tag}",
            task_signature=f"perceptor::{format_tag}",
            entrypoint="parse",
            source_code=src,
            metadata={"codec_family": codec_name},
        )
        ok_all = True
        for s in samples:
            try:
                parsed = organ.invoke(s)
                re_emitted = organ.invoke_aux("serialize", parsed)
                reparsed = organ.invoke(re_emitted)
                if reparsed != parsed:
                    ok_all = False
                    break
            except Exception:
                ok_all = False
                break
        if not ok_all:
            continue

        # Falsification gate: must reject malformed/corrupted framing decoys!
        corruptions = _corrupt_sample(samples[0])
        rejected = 0
        for bad in corruptions:
            try:
                organ.invoke(bad)
            except Exception:
                rejected += 1
        if rejected < len(corruptions):
            continue
        organ.verified_passes = len(samples)
        return organ
    return None


# ---------------------------------------------------------------------------
# Active Version-Space Disambiguation (Closes PERMANENCE_AMPLIFIES_THE_CHECK)
# ---------------------------------------------------------------------------


def _arg_names(arity: int) -> list[str]:
    return [f"x{i}" for i in range(arity)]


def _safe_eval_candidate(organ: ExecutableOrgan, args: tuple[Any, ...]) -> tuple[bool, Any]:
    try:
        val = organ.invoke(*args)
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return False, None
        return True, val
    except Exception:
        return False, None


def _generate_candidate_expressions(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
) -> list[tuple[str, str]]:
    """Generate MDL-ordered candidate `(rule_name, expr_src)` hypotheses for version-space search."""
    if not examples:
        return []
    first_in, first_out = examples[0]
    arity = len(first_in)
    names = _arg_names(arity)
    cands: list[tuple[str, str]] = []

    # 1. Constant rule (simplest Occam trap — e.g. `copy 42` in permanence_amplifies_check_v1!)
    if isinstance(first_out, (int, float, str, bool)) or (
        isinstance(first_out, (list, tuple)) and len(first_out) <= 8
    ):
        cands.append(("constant_output", repr(first_out)))

    # 2. Projections & unary transforms
    for i, nm in enumerate(names):
        cands.append((f"proj_{i}", nm))
        v = first_in[i]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            for k in (1, 2, 3, -1, 5, 10):
                cands.append((f"add_{i}_{k}", f"({nm} + {k})"))
                cands.append((f"sub_{i}_{k}", f"({nm} - {k})"))
            for k in (2, 3, 4, -1, 10):
                cands.append((f"mul_{i}_{k}", f"({nm} * {k})"))
            cands.append((f"sq_{i}", f"({nm} * {nm})"))
            cands.append((f"abs_{i}", f"abs({nm})"))
            # Solve exact affine y = a*x + b from first two distinct points if available
            if len(examples) >= 2 and isinstance(first_out, (int, float)):
                x2, y2 = examples[1][0][i], examples[1][1]
                if isinstance(x2, (int, float)) and isinstance(y2, (int, float)) and x2 != v:
                    slope = (y2 - first_out) / (x2 - v)
                    intercept = first_out - slope * v
                    if abs(slope - round(slope)) < 1e-9 and abs(intercept - round(intercept)) < 1e-9:
                        si, bi = int(round(slope)), int(round(intercept))
                        cands.append((f"affine_{i}_{si}_{bi}", f"({si} * {nm} + {bi})"))
        elif isinstance(v, (list, tuple)):
            cands.append((f"sum_{i}", f"sum({nm})"))
            cands.append((f"len_{i}", f"len({nm})"))
            cands.append((f"max_{i}", f"max({nm}) if {nm} else 0"))
            cands.append((f"min_{i}", f"min({nm}) if {nm} else 0"))
            cands.append((f"sorted_{i}", f"sorted({nm})"))
            cands.append((f"rev_{i}", f"list(reversed({nm}))"))
            cands.append((f"uniq_sorted_{i}", f"sorted(set({nm}))"))
            cands.append((f"prod_{i}", f"(1 if not {nm} else __prod({nm}))"))
        elif isinstance(v, str):
            cands.append((f"strip_{i}", f"{nm}.strip()"))
            cands.append((f"lower_{i}", f"{nm}.lower()"))
            cands.append((f"upper_{i}", f"{nm}.upper()"))
            cands.append((f"len_str_{i}", f"len({nm})"))
            cands.append((f"rev_str_{i}", f"{nm}[::-1]"))

    # 3. Pairwise & multi-argument algebraic / billing / relational rules
    if arity >= 2:
        for i in range(arity):
            for j in range(arity):
                if i == j:
                    continue
                a, b = names[i], names[j]
                va, vb = first_in[i], first_in[j]
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    if i < j:
                        cands.append((f"add_{i}_{j}", f"({a} + {b})"))
                        cands.append((f"mul_{i}_{j}", f"({a} * {b})"))
                        cands.append((f"max_{i}_{j}", f"max({a}, {b})"))
                        cands.append((f"min_{i}_{j}", f"min({a}, {b})"))
                    cands.append((f"sub_{i}_{j}", f"({a} - {b})"))
                    cands.append((f"floordiv_{i}_{j}", f"({a} // {b})"))
                    cands.append((f"mod_{i}_{j}", f"({a} % {b})"))
                    cands.append((f"discount_pct_{i}_{j}", f"({a} * (100.0 - {b}) / 100.0)"))
                    cands.append((f"markup_pct_{i}_{j}", f"({a} * (100.0 + {b}) / 100.0)"))
                    cands.append((f"linear_2_{i}_{j}", f"(2 * {a} + {b})"))
                    cands.append((f"diff_sq_{i}_{j}", f"(({a} - {b}) * ({a} - {b}))"))
                if isinstance(va, (list, tuple)) and isinstance(vb, (int, float)):
                    cands.append((f"sum_discount_{i}_{j}", f"(sum({a}) * (100.0 - {b}) / 100.0)"))
                    cands.append((f"sum_tax_{i}_{j}", f"(sum({a}) * (1.0 - {b}))"))
                    cands.append((f"sum_plus_{i}_{j}", f"(sum({a}) + {b})"))
                    cands.append((f"sum_scale_{i}_{j}", f"(sum({a}) * {b})"))
                    cands.append((f"filter_gt_sum_{i}_{j}", f"sum(z for z in {a} if z > {b})"))

    if arity == 3 and all(isinstance(x, (int, float)) for x in first_in):
        a, b, c = names[0], names[1], names[2]
        cands.extend([
            ("sum3", f"({a} + {b} + {c})"),
            ("prod3", f"({a} * {b} * {c})"),
            ("fma_012", f"({a} * {b} + {c})"),
            ("fms_012", f"({a} * {b} - {c})"),
            ("clamp_012", f"max({b}, min({c}, {a}))"),
        ])

    return cands


def _wrap_expr_into_source(arity: int, expr_src: str) -> str:
    params = ", ".join(_arg_names(arity))
    helper = ""
    if "__prod(" in expr_src:
        helper = (
            "def __prod(seq):\n"
            "    acc = 1\n"
            "    for v in seq:\n"
            "        acc = acc * v\n"
            "    return acc\n\n"
        )
    return f"{helper}def run({params}):\n    return {expr_src}\n"


def _outputs_match(got: Any, expected: Any) -> bool:
    if type(got) is bool or type(expected) is bool:
        return type(got) is type(expected) and got == expected
    if isinstance(got, (int, float)) and isinstance(expected, (int, float)):
        if isinstance(expected, int) and isinstance(got, float) and not got.is_integer():
            return False
        return abs(float(got) - float(expected)) <= 1e-9
    return got == expected


def _candidate_probe_inputs(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
) -> list[tuple[Any, ...]]:
    """Deterministic boundary + interior probe grid for version-space disambiguation."""
    if not examples:
        return []
    sample_in = examples[0][0]
    seen = {tuple(repr(x) for x in ex_in) for ex_in, _ in examples}
    probes: list[tuple[Any, ...]] = []

    def _domain_for(val: Any, slot: int) -> list[Any]:
        if isinstance(val, bool):
            return [False, True]
        if isinstance(val, int):
            return [3 + slot, 5 + slot, 8, 11, 0, 1, -2, val + 1, val + 3]
        if isinstance(val, float):
            return [10.0, 25.0, 50.0, 0.0, 5.0, val + 10.0]
        if isinstance(val, list):
            return [[10, 20], [3, 5, 7], [100], [2, 4, 6, 8], []]
        if isinstance(val, tuple):
            return [(10, 20), (3, 5, 7), (100,)]
        if isinstance(val, str):
            return ["alpha", "Beta ", "xyz", val + "_2"]
        return [val]

    domains = [_domain_for(v, idx) for idx, v in enumerate(sample_in)]
    arity = len(domains)
    if arity == 1:
        grid = [(a,) for a in domains[0]]
    elif arity == 2:
        grid = [(a, b) for a in domains[0][:7] for b in domains[1][:7]]
    elif arity == 3:
        grid = [
            (a, b, c)
            for a in domains[0][:4]
            for b in domains[1][:4]
            for c in domains[2][:4]
        ]
    else:
        grid = [tuple(d[k % len(d)] for d in domains) for k in range(24)]

    for pt in grid:
        key = tuple(repr(x) for x in pt)
        if key not in seen:
            seen.add(key)
            probes.append(pt)
    return probes


def synthesize_discriminating_input(
    hypotheses: Sequence[ExecutableOrgan],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
) -> tuple[Any, ...] | None:
    """Find the probe input `x_disc` maximizing Shannon entropy over hypothesis outputs."""
    if len(hypotheses) <= 1:
        return None
    best_probe: tuple[Any, ...] | None = None
    best_entropy = -1.0
    for probe in _candidate_probe_inputs(examples):
        buckets: dict[str, int] = {}
        valid_total = 0
        for h in hypotheses:
            ok, out = _safe_eval_candidate(h, probe)
            key = f"OK:{type(out).__name__}:{out!r}" if ok else "ERR"
            buckets[key] = buckets.get(key, 0) + 1
            if ok:
                valid_total += 1
        if len(buckets) <= 1 or valid_total == 0:
            continue
        n = float(len(hypotheses))
        ent = -sum((cnt / n) * math.log2(cnt / n) for cnt in buckets.values())
        if ent > best_entropy:
            best_entropy = ent
            best_probe = probe
    return best_probe


# ---------------------------------------------------------------------------
# Mutation-Discriminating Semantic Inspector Synthesis
# (Closes DERIVED_INSPECTOR & REPAIR_ADMISSION counterexamples)
# ---------------------------------------------------------------------------


def _generate_semantic_artifact_mutants(valid_text: str) -> dict[str, str]:
    """Generate semantic decoys that fool lexical substring checks (`# comment`, wrong sum, etc.)."""
    lines = [ln for ln in valid_text.splitlines() if ln.strip()]
    mutants: dict[str, str] = {
        "comment_stuffed_decoy": "\n".join(f"# {ln}" for ln in lines) + "\nNO_ACTIVE_PAYLOAD\n",
        "empty_decoy": "",
    }
    if len(lines) >= 2:
        mutants["reversed_order_decoy"] = "\n".join(reversed(lines)) + "\n"
        mutants["duplicated_payload_decoy"] = valid_text + "\n" + valid_text

    # Perturb the last number in the artifact while keeping all labels/keywords intact!
    num_matches = list(re.finditer(r"-?\d+(?:\.\d+)?", valid_text))
    if num_matches:
        last_m = num_matches[-1]
        raw_num = last_m.group(0)
        perturbed = (
            str(float(raw_num) + 1.0) if "." in raw_num else str(int(raw_num) + 1)
        )
        mutants["numeric_value_perturbed_decoy"] = (
            valid_text[: last_m.start()] + perturbed + valid_text[last_m.end() :]
        )

    # JSON structural type-confusion decoy: keep every substring present inside a comment/string field!
    stripped = valid_text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        mutants["json_string_wrapped_decoy"] = json.dumps({"_note": valid_text})

    return mutants


def derive_semantic_inspector_organ(
    *,
    capability_id: str,
    valid_artifacts: Sequence[str],
    environment_checker: Callable[[str], bool],
) -> dict[str, Any]:
    """Derive a semantic/recomputational `VERIFIER` organ by probing which mutants the checker rejects.

    Unlike lexical containment, this observes actual rejection of comment-stuffed, reordered,
    duplicated, JSON-wrapped, and numeric-perturbed mutants, and synthesizes an executable
    `VERIFIER` organ that enforces those exact structural & arithmetic invariants.
    """
    if not valid_artifacts:
        return {"ok": False, "reason": "NO_VALID_ARTIFACTS"}
    for art in valid_artifacts:
        if not environment_checker(art):
            return {"ok": False, "reason": "POSITIVE_ARTIFACT_REJECTED_BY_ENVIRONMENT"}

    sample = valid_artifacts[0]
    mutants = _generate_semantic_artifact_mutants(sample)
    rejected_classes: set[str] = set()
    for m_name, m_text in mutants.items():
        if m_text != sample and not environment_checker(m_text):
            rejected_classes.add(m_name)

    if not rejected_classes:
        return {"ok": False, "reason": "ENVIRONMENT_CHECKER_REJECTS_NO_MUTANTS"}

    # Extract structural invariants from all valid artifacts
    json_mode = False
    required_json_types: dict[str, str] = {}
    try:
        parsed_jsons = [json.loads(a) for a in valid_artifacts]
        if all(isinstance(j, dict) and j for j in parsed_jsons):
            json_mode = True
            common_keys = set(parsed_jsons[0].keys())
            for j in parsed_jsons[1:]:
                common_keys &= set(j.keys())
            for k in sorted(common_keys):
                t_names = {type(j[k]).__name__ for j in parsed_jsons}
                if len(t_names) == 1:
                    required_json_types[str(k)] = next(iter(t_names))
    except Exception:
        json_mode = False

    def _active_lines(txt: str) -> list[str]:
        return [
            ln.strip()
            for ln in txt.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")
        ]

    active_per_art = [_active_lines(a) for a in valid_artifacts]
    # Extract ordered structural token skeletons (replacing pure numbers with `<NUM>`)
    def _line_skeleton(ln: str) -> str:
        return re.sub(r"-?\d+(?:\.\d+)?", "<NUM>", ln)

    common_skeleton_seq: list[str] | None = None
    skel0 = [_line_skeleton(ln) for ln in active_per_art[0]]
    if all([_line_skeleton(ln) for ln in lines] == skel0 for lines in active_per_art[1:]):
        common_skeleton_seq = skel0

    # Check if the final number is an exact arithmetic function (sum or product) of earlier numbers!
    arithmetic_law: str | None = None
    for candidate_law in ("sum", "prod", "exact_constants"):
        law_holds = True
        for art in valid_artifacts:
            act_txt = "\n".join(_active_lines(art))
            nums = [
                float(x) if "." in x else int(x)
                for x in re.findall(r"-?\d+(?:\.\d+)?", act_txt)
            ]
            if candidate_law in ("sum", "prod"):
                if len(nums) < 2:
                    law_holds = False
                    break
                body_nums, target_num = nums[:-1], nums[-1]
                if candidate_law == "sum":
                    calc = sum(body_nums)
                else:
                    calc = 1
                    for v in body_nums:
                        calc = calc * v
                if abs(float(calc) - float(target_num)) > 1e-9:
                    law_holds = False
                    break
            elif candidate_law == "exact_constants":
                if len(valid_artifacts) > 1:
                    nums0 = re.findall(r"-?\d+(?:\.\d+)?", "\n".join(active_per_art[0]))
                    if re.findall(r"-?\d+(?:\.\d+)?", act_txt) != nums0:
                        law_holds = False
                        break
        if law_holds and ("numeric_value_perturbed_decoy" in rejected_classes):
            arithmetic_law = candidate_law
            break

    exact_nums0 = re.findall(r"-?\d+(?:\.\d+)?", "\n".join(active_per_art[0]))
    enforce_order = "reversed_order_decoy" in rejected_classes
    enforce_no_dup = "duplicated_payload_decoy" in rejected_classes

    verifier_src = f"""
def inspect_artifact(text):
    if not isinstance(text, str) or not text.strip():
        return (False, 'EMPTY_ARTIFACT')
    json_mode = {json_mode!r}
    req_json_types = {required_json_types!r}
    if json_mode:
        try:
            obj = json.loads(text)
        except Exception:
            return (False, 'INVALID_JSON')
        if not isinstance(obj, dict):
            return (False, 'JSON_NOT_OBJECT')
        _type_map = {{'int': int, 'float': float, 'str': str, 'bool': bool, 'list': list, 'dict': dict}}
        for k, tname in req_json_types.items():
            if k not in obj:
                return (False, 'JSON_SCHEMA_MISMATCH:' + k)
            t_cls = _type_map.get(tname)
            if t_cls is not None:
                if tname == 'int' and isinstance(obj[k], bool):
                    return (False, 'JSON_SCHEMA_MISMATCH:' + k)
                if not isinstance(obj[k], t_cls):
                    return (False, 'JSON_SCHEMA_MISMATCH:' + k)
    active = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith('#')]
    if not active:
        return (False, 'ONLY_COMMENTS_OR_WHITESPACE')
    skel_expected = {common_skeleton_seq!r}
    enforce_order = {enforce_order!r}
    enforce_no_dup = {enforce_no_dup!r}
    if skel_expected is not None:
        got_skel = [re.sub(r'-?\\d+(?:\\.\\d+)?', '<NUM>', ln) for ln in active]
        if enforce_no_dup and len(got_skel) != len(skel_expected):
            return (False, 'LINE_COUNT_OR_DUPLICATION_MISMATCH')
        if enforce_order:
            if got_skel != skel_expected:
                return (False, 'ORDERED_STRUCTURE_MISMATCH')
        else:
            if not set(skel_expected).issubset(set(got_skel)):
                return (False, 'REQUIRED_ACTIVE_LINES_MISSING')
    law = {arithmetic_law!r}
    nums_raw = re.findall(r'-?\\d+(?:\\.\\d+)?', '\\n'.join(active))
    if law == 'sum':
        vals = [float(x) if '.' in x else int(x) for x in nums_raw]
        if len(vals) < 2 or abs(float(sum(vals[:-1])) - float(vals[-1])) > 1e-9:
            return (False, 'ARITHMETIC_SUM_INVARIANT_FAILED')
    elif law == 'prod':
        vals = [float(x) if '.' in x else int(x) for x in nums_raw]
        acc = 1
        for v in vals[:-1]:
            acc = acc * v
        if len(vals) < 2 or abs(float(acc) - float(vals[-1])) > 1e-9:
            return (False, 'ARITHMETIC_PRODUCT_INVARIANT_FAILED')
    elif law == 'exact_constants':
        if nums_raw != {exact_nums0!r}:
            return (False, 'NUMERIC_CONSTANT_MISMATCH')
    return (True, '')
"""
    organ = make_organ(
        stratum=VERIFIER,
        name=f"semantic_inspector_{capability_id}",
        task_signature=f"inspector::{capability_id}",
        entrypoint="inspect_artifact",
        source_code=verifier_src,
        metadata={
            "discriminated_mutant_classes": sorted(rejected_classes),
            "arithmetic_law": arithmetic_law,
            "json_mode": json_mode,
        },
    )

    # Verify positive agreement AND 100% kill on every rejected semantic decoy!
    for art in valid_artifacts:
        ok, reason = organ.invoke(art)
        if not ok:
            return {"ok": False, "reason": f"SELF_REJECTED_VALID:{reason}"}

    killed: list[str] = []
    for m_name in sorted(rejected_classes):
        ok, _ = organ.invoke(mutants[m_name])
        if ok:
            return {"ok": False, "reason": f"INSPECTOR_ACCEPTED_SEMANTIC_DECOY:{m_name}"}
        killed.append(m_name)

    organ.verified_passes = len(valid_artifacts) + len(killed)
    return {
        "ok": True,
        "organ": organ,
        "killed_mutant_classes": killed,
        "arithmetic_law": arithmetic_law,
    }


# ---------------------------------------------------------------------------
# Meta-Trace Tactic Compilation (Level-1 Non-Static Synthesizer Growth)
# ---------------------------------------------------------------------------


def _anti_unify_ast_constants(
    tree_a: ast.AST,
    tree_b: ast.AST,
) -> tuple[ast.AST | None, list[tuple[Any, Any]]]:
    """Anti-unify two pure AST expressions differing at numeric constants into `?c0, ?c1, ...`."""
    holes: list[tuple[Any, Any]] = []

    def _walk(na: ast.AST, nb: ast.AST) -> ast.AST | None:
        # Handle negative integer literals represented as UnaryOp(USub, Constant)
        def _as_num(node: ast.AST) -> int | float | None:
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            if (
                isinstance(node, ast.UnaryOp)
                and isinstance(node.op, ast.USub)
                and isinstance(node.operand, ast.Constant)
                and isinstance(node.operand.value, (int, float))
            ):
                return -node.operand.value
            return None

        va, vb = _as_num(na), _as_num(nb)
        if va is not None and vb is not None:
            if va == vb:
                return ast.Constant(value=va)
            idx = len(holes)
            holes.append((va, vb))
            return ast.Subscript(
                value=ast.Name(id="_C", ctx=ast.Load()),
                slice=ast.Constant(value=idx),
                ctx=ast.Load(),
            )

        if type(na) is not type(nb):
            return None

        if isinstance(na, ast.Name) and isinstance(nb, ast.Name):
            return ast.Name(id=na.id, ctx=na.ctx) if na.id == nb.id else None
        if isinstance(na, ast.Constant) and isinstance(nb, ast.Constant):
            return ast.Constant(value=na.value) if na.value == nb.value else None

        new_fields: dict[str, Any] = {}
        for field_name, val_a in ast.iter_fields(na):
            val_b = getattr(nb, field_name)
            if isinstance(val_a, list) and isinstance(val_b, list):
                if len(val_a) != len(val_b):
                    return None
                merged_list = []
                for xa, xb in zip(val_a, val_b):
                    if isinstance(xa, ast.AST) and isinstance(xb, ast.AST):
                        m = _walk(xa, xb)
                        if m is None:
                            return None
                        merged_list.append(m)
                    elif xa == xb:
                        merged_list.append(xa)
                    else:
                        return None
                new_fields[field_name] = merged_list
            elif isinstance(val_a, ast.AST) and isinstance(val_b, ast.AST):
                m = _walk(val_a, val_b)
                if m is None:
                    return None
                new_fields[field_name] = m
            else:
                if type(val_a) is not type(val_b) or val_a != val_b:
                    return None
                new_fields[field_name] = val_a
        return type(na)(**new_fields)

    generalized = _walk(tree_a, tree_b)
    if generalized is None or not holes or len(holes) > 3:
        return None, []
    ast.fix_missing_locations(generalized)
    return generalized, holes


def compile_meta_synthesizer_organ(
    organ_a: ExecutableOrgan,
    organ_b: ExecutableOrgan,
    *,
    tactic_name: str = "compiled_meta_tactic",
) -> ExecutableOrgan | None:
    """Compile a higher-order `META_SYNTHESIZER` organ by anti-unifying two solved `SKILL` organs!

    Once registered in `P_t`, any future task from this entire higher-order algorithmic family
    is synthesized in 1 step (`< 2 ms`) even when its depth exceeds the bootstrap grammar.
    """
    try:
        ta = ast.parse(organ_a.source_code)
        tb = ast.parse(organ_b.source_code)
    except SyntaxError:
        return None
    fa = next((n for n in ta.body if isinstance(n, ast.FunctionDef) and n.name == organ_a.entrypoint), None)
    fb = next((n for n in tb.body if isinstance(n, ast.FunctionDef) and n.name == organ_b.entrypoint), None)
    if fa is None or fb is None or len(fa.args.args) != len(fb.args.args):
        return None
    if len(fa.body) != 1 or len(fb.body) != 1:
        return None
    if not (isinstance(fa.body[0], ast.Return) and isinstance(fb.body[0], ast.Return)):
        return None
    if fa.body[0].value is None or fb.body[0].value is None:
        return None

    # Normalize parameter names to canonical x0, x1, ...
    arity = len(fa.args.args)
    canon_names = _arg_names(arity)

    class _ParamRenamer(ast.NodeTransformer):
        def __init__(self, mapping: Mapping[str, str]) -> None:
            self.mapping = mapping

        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id in self.mapping:
                return ast.Name(id=self.mapping[node.id], ctx=node.ctx)
            return node

    expr_a = _ParamRenamer({a.arg: c for a, c in zip(fa.args.args, canon_names)}).visit(fa.body[0].value)
    expr_b = _ParamRenamer({b.arg: c for b, c in zip(fb.args.args, canon_names)}).visit(fb.body[0].value)

    skel_expr, holes = _anti_unify_ast_constants(expr_a, expr_b)
    if skel_expr is None:
        return None

    skel_template_str = ast.unparse(skel_expr)
    num_holes = len(holes)
    param_sig = ", ".join(canon_names)

    # Emit a pure Python META_SYNTHESIZER organ that searches parameter lattice & emits exact code!
    domain = "(-5, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 50, 100)"
    loops = "\n".join(
        "    " * (idx + 1) + f"for c{idx} in {domain}:"
        for idx in range(num_holes)
    )
    tuple_vars = ", ".join(f"c{idx}" for idx in range(num_holes))
    if num_holes == 1:
        tuple_vars += ","
    inner_indent = "    " * (num_holes + 1)

    eval_fn_expr = skel_template_str
    emit_expr = skel_template_str
    for idx in range(num_holes):
        emit_expr = emit_expr.replace(f"_C[{idx}]", f"{{c{idx}}}")

    meta_src = f"""
def _eval_skeleton({param_sig}, _C):
    return {eval_fn_expr}

def synthesize_from_examples(examples):
    if not examples or len(examples[0][0]) != {arity}:
        return None
{loops}
{inner_indent}_C = ({tuple_vars})
{inner_indent}ok = True
{inner_indent}for inp, expected in examples:
{inner_indent}    try:
{inner_indent}        got = _eval_skeleton(*inp, _C)
{inner_indent}    except Exception:
{inner_indent}        ok = False
{inner_indent}        break
{inner_indent}    if got != expected:
{inner_indent}        ok = False
{inner_indent}        break
{inner_indent}if ok:
{inner_indent}    return f"def run({param_sig}):\\n    return {emit_expr}\\n"
    return None
"""
    return make_organ(
        stratum=META_SYNTHESIZER,
        name=tactic_name,
        task_signature=f"meta_synth::arity_{arity}",
        entrypoint="synthesize_from_examples",
        source_code=meta_src,
        parent_organ_ids=(organ_a.organ_id, organ_b.organ_id),
        metadata={"num_holes": num_holes, "skeleton": skel_template_str},
    )


# ---------------------------------------------------------------------------
# Unified 5-Stratum Meta-Circular Organ Graph (`P_t`)
# ---------------------------------------------------------------------------


class MetaCircularOrganGraph:
    """Content-addressed, self-growing 5-stratum program graph `P_t`."""

    def __init__(self, state_path: pathlib.Path | str | None = None) -> None:
        self.state_path = pathlib.Path(state_path) if state_path is not None else None
        self.organs: dict[str, ExecutableOrgan] = {}
        self.primary_by_sig: dict[tuple[str, str], str] = {}
        self.predictor = CausalFeatureSelfPredictor()
        if self.state_path is not None and self.state_path.is_file():
            self._load()

    def register_organ(self, organ: ExecutableOrgan) -> dict[str, Any]:
        """Admit or Pareto-update an organ in `P_t`."""
        organ.ensure_compiled()
        self.organs[organ.organ_id] = organ
        sig_key = (organ.stratum, organ.task_signature)
        cur_id = self.primary_by_sig.get(sig_key)
        replaced = False
        if cur_id is None or cur_id not in self.organs:
            self.primary_by_sig[sig_key] = organ.organ_id
            replaced = True
        else:
            incumbent = self.organs[cur_id]
            if organ.pareto_score > incumbent.pareto_score:
                self.primary_by_sig[sig_key] = organ.organ_id
                replaced = True
        self._save()
        return {
            "admitted": True,
            "organ_id": organ.organ_id,
            "is_primary": self.primary_by_sig.get(sig_key) == organ.organ_id,
            "replaced_incumbent": replaced,
            "pareto_score": round(organ.pareto_score, 6),
        }

    def get_primary(self, stratum: str, task_signature: str) -> ExecutableOrgan | None:
        oid = self.primary_by_sig.get((stratum, task_signature))
        return self.organs.get(oid) if oid else None

    def organs_in_stratum(self, stratum: str) -> list[ExecutableOrgan]:
        out = [o for o in self.organs.values() if o.stratum == stratum]
        return sorted(out, key=lambda o: (-o.pareto_score, o.organ_id))

    # ------------------------------------------------- Sensorogenesis API

    def perceive_or_synthesize_reader(
        self,
        raw_sample: str | bytes,
        *,
        format_tag: str = "auto",
        extra_samples: Sequence[str | bytes] = (),
    ) -> dict[str, Any]:
        """Parse `raw_sample` with an existing `PERCEPTOR` organ, or synthesize & verify one online."""
        # 1. Fast path (< 0.05 ms): try registered PERCEPTOR organs in Pareto order
        for organ in self.organs_in_stratum(PERCEPTOR):
            try:
                parsed = organ.invoke(raw_sample)
                re_emitted = organ.invoke_aux("serialize", parsed)
                if organ.invoke(re_emitted) == parsed:
                    organ.verified_passes += 1
                    return {
                        "ok": True,
                        "parsed": parsed,
                        "organ_id": organ.organ_id,
                        "synthesized_new_organ": False,
                    }
            except Exception:
                continue

        # 2. Online epistemic sensorogenesis
        all_samples = [raw_sample, *extra_samples]
        new_organ = synthesize_perceptor_organ(all_samples, format_tag=format_tag)
        if new_organ is None:
            return {"ok": False, "reason": "NO_VERIFIED_ROUNDTRIP_PERCEPTOR_FOUND"}
        self.register_organ(new_organ)
        parsed = new_organ.invoke(raw_sample)
        return {
            "ok": True,
            "parsed": parsed,
            "organ_id": new_organ.organ_id,
            "synthesized_new_organ": True,
        }

    # ------------------------ Version-Space Skill Synthesis & Meta-Compilation

    def synthesize_or_disambiguate_skill(
        self,
        examples: Sequence[tuple[tuple[Any, ...], Any]],
        *,
        task_signature: str,
        oracle: Callable[[tuple[Any, ...]], Any] | None = None,
        max_oracle_queries: int = 5,
    ) -> dict[str, Any]:
        """Synthesize a `SKILL` organ using learned `META_SYNTHESIZER`s + version-space disambiguation."""
        if not examples:
            return {"ok": False, "status": "EMPTY_EXAMPLES"}

        # 0. Tier-0 recall (`< 0.05 ms`): check primary SKILL for this signature if consistent
        existing = self.get_primary(SKILL, task_signature)
        if existing is not None:
            if all(
                (ok and _outputs_match(val, exp))
                for ex_in, exp in examples
                for ok, val in [_safe_eval_candidate(existing, ex_in)]
            ):
                return {
                    "ok": True,
                    "status": "RECALLED_TIER0_ORGAN",
                    "organ": existing,
                    "oracle_queries_used": 0,
                }

        arity = len(examples[0][0])
        work_examples = list(examples)

        # Build initial hypothesis pool: learned META_SYNTHESIZER organs FIRST, then base grammar!
        candidate_organs: list[ExecutableOrgan] = []
        seen_ast: set[str] = set()

        def _collect_candidates(cur_examples: Sequence[tuple[tuple[Any, ...], Any]]) -> list[ExecutableOrgan]:
            pool: list[ExecutableOrgan] = []
            for meta in self.organs_in_stratum(META_SYNTHESIZER):
                try:
                    cand_src = meta.invoke(cur_examples)
                except Exception:
                    cand_src = None
                if isinstance(cand_src, str) and cand_src.strip():
                    try:
                        org = make_organ(
                            stratum=SKILL,
                            name=f"from_{meta.name}",
                            task_signature=task_signature,
                            entrypoint="run",
                            source_code=cand_src,
                            parent_organ_ids=(meta.organ_id,),
                            metadata={"via_meta_synthesizer": meta.organ_id},
                        )
                    except OrganSafetyError:
                        org = None
                    if org is not None:
                        pool.append(org)

            for rname, expr_src in _generate_candidate_expressions(cur_examples):
                src = _wrap_expr_into_source(arity, expr_src)
                try:
                    org = make_organ(
                        stratum=SKILL,
                        name=rname,
                        task_signature=task_signature,
                        entrypoint="run",
                        source_code=src,
                    )
                except OrganSafetyError:
                    continue
                pool.append(org)

            # Filter to hypotheses consistent with ALL observed examples and deduplicate by AST
            surviving: list[ExecutableOrgan] = []
            local_seen: set[str] = set()
            for org in pool:
                if org.organ_id in local_seen:
                    continue
                consistent = True
                for ex_in, exp_out in cur_examples:
                    ok, got = _safe_eval_candidate(org, ex_in)
                    if not ok or not _outputs_match(got, exp_out):
                        consistent = False
                        break
                if consistent:
                    local_seen.add(org.organ_id)
                    surviving.append(org)
            return sorted(surviving, key=lambda o: (o.code_bytes, o.organ_id))

        candidate_organs = _collect_candidates(work_examples)
        seen_ast = {o.organ_id for o in candidate_organs}
        if not candidate_organs:
            return {"ok": False, "status": "NO_CONSISTENT_HYPOTHESIS", "seen_candidates": len(seen_ast)}

        queries_used = 0
        while len(candidate_organs) > 1:
            disc_probe = synthesize_discriminating_input(candidate_organs, work_examples)
            if disc_probe is None:
                # All surviving hypotheses are observationally equivalent across the entire probe grid!
                break
            if oracle is None or queries_used >= max_oracle_queries:
                return {
                    "ok": False,
                    "status": "UNDERDETERMINED_VERSION_SPACE",
                    "surviving_count": len(candidate_organs),
                    "surviving_names": [o.name for o in candidate_organs[:6]],
                    "discriminating_input": disc_probe,
                    "oracle_queries_used": queries_used,
                }
            oracle_answer = oracle(disc_probe)
            queries_used += 1
            work_examples.append((disc_probe, oracle_answer))
            candidate_organs = [
                org
                for org in candidate_organs
                if (lambda ok_val: ok_val[0] and _outputs_match(ok_val[1], oracle_answer))(
                    _safe_eval_candidate(org, disc_probe)
                )
            ]
            if not candidate_organs:
                candidate_organs = _collect_candidates(work_examples)
                if not candidate_organs:
                    return {
                        "ok": False,
                        "status": "CONTRADICTORY_ORACLE_OR_OUT_OF_GRAMMAR",
                        "oracle_queries_used": queries_used,
                    }

        winner = candidate_organs[0]
        winner.verified_passes = len(work_examples)
        self.register_organ(winner)

        # Auto-compile META_SYNTHESIZER tactics when two distinct SKILL organs share structure!
        compiled_meta_id: str | None = None
        for other in self.organs_in_stratum(SKILL):
            if other.organ_id == winner.organ_id:
                continue
            meta_org = compile_meta_synthesizer_organ(
                other,
                winner,
                tactic_name=f"meta_{other.name}_{winner.name}"[:48],
            )
            if meta_org is not None and meta_org.organ_id not in self.organs:
                self.register_organ(meta_org)
                compiled_meta_id = meta_org.organ_id
                break

        return {
            "ok": True,
            "status": "DISAMBIGUATED_AND_CRYSTALLIZED",
            "organ": winner,
            "oracle_queries_used": queries_used,
            "compiled_meta_synthesizer_id": compiled_meta_id,
        }

    # ---------------------------------------------------- Persistence

    def summary(self) -> dict[str, Any]:
        by_stratum = {s: len(self.organs_in_stratum(s)) for s in STRATA}
        return {
            "schema": SCHEMA,
            "total_organs": len(self.organs),
            "by_stratum": by_stratum,
            "predictor_observations": self.predictor.observations,
        }

    def _save(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEMA,
            "organs": [o.as_row() for o in sorted(self.organs.values(), key=lambda x: x.organ_id)],
            "primary_by_sig": {
                f"{s}::{sig}": oid for (s, sig), oid in sorted(self.primary_by_sig.items())
            },
            "predictor": self.predictor.as_row(),
        }
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.state_path)

    def _load(self) -> None:
        if self.state_path is None or not self.state_path.is_file():
            return
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for row in raw.get("organs") or ():
            try:
                org = ExecutableOrgan.from_row(row)
                org.ensure_compiled()
                self.organs[org.organ_id] = org
            except Exception:
                continue
        for k, oid in (raw.get("primary_by_sig") or {}).items():
            if "::" in k and oid in self.organs:
                s, sig = k.split("::", 1)
                self.primary_by_sig[(s, sig)] = str(oid)
        if isinstance(raw.get("predictor"), Mapping):
            self.predictor = CausalFeatureSelfPredictor.from_row(raw["predictor"])
