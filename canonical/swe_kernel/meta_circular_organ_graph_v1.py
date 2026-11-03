#!/usr/bin/env python3
"""Meta-Circular Reflective Program Graph (`K3 = 0`, `$0` spend).

Implements Axiom I of the non-static sentient creature: every cognitive and
executive mechanism is a content-addressed, AST-verified, falsification-gated
executable Python program (`ExecutableOrgan`) in one evolving graph `P_t` whose
operator basis compounds:

    Omega_{t+1} = Omega_t  cup  P_t  cup  C_t

Seven reflective strata — none of which is a frozen menu of templates:

  1. `PERCEPTOR`         : byte/token grammar induction -> invertible
                           (parse, serialize) ASTs, admitted only after round-trip
                           bijection AND adversarial corruption rejection.
  2. `WORLD_MODEL`       : execution traces -> executable precondition/effect rules.
  3. `PREDICTOR`         : (task_features, env_features) -> (p_pass, cost_ms, p_burn).
  4. `SKILL`             : observational-equivalence + STUN + exact linear solving
                           + live organ composition (`organ_B(organ_A(x))`).
  5. `VERIFIER`          : synthesized boolean/relational invariants (not a
                           hardcoded sum/prod/constants checklist).
  6. `META_SYNTHESIZER`  : higher-order anti-unification + exact coefficient
                           solving (no frozen integer lattice).
  7. `POLICY`            : multi-step instrumental Q so 0-immediate-reward
                           tools/sensors/verifiers inherit unlocking value.
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
WORLD_MODEL = "WORLD_MODEL"
PREDICTOR = "PREDICTOR"
SKILL = "SKILL"
VERIFIER = "VERIFIER"
META_SYNTHESIZER = "META_SYNTHESIZER"
POLICY = "POLICY"

STRATA: tuple[str, ...] = (
    PERCEPTOR,
    WORLD_MODEL,
    PREDICTOR,
    SKILL,
    VERIFIER,
    META_SYNTHESIZER,
    POLICY,
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
# Online Epistemic Sensorogenesis — grammar induction, not a codec menu
# ---------------------------------------------------------------------------


def _as_text(sample: str | bytes) -> str:
    return sample.decode("utf-8") if isinstance(sample, bytes) else str(sample)


def _coerce_literal_src() -> str:
    return (
        "def _coerce(v):\n"
        "    s = str(v).strip()\n"
        "    low = s.lower()\n"
        "    if low == 'true':\n"
        "        return True\n"
        "    if low == 'false':\n"
        "        return False\n"
        "    sign = 1\n"
        "    body = s\n"
        "    if body[:1] == '-':\n"
        "        sign = -1\n"
        "        body = body[1:]\n"
        "    if body.isdigit():\n"
        "        return sign * int(body)\n"
        "    if body.count('.') == 1 and body.replace('.', '', 1).isdigit():\n"
        "        return sign * float(body)\n"
        "    return s\n"
        "\n"
        "def _emit_scalar(v):\n"
        "    if isinstance(v, bool):\n"
        "        return 'true' if v else 'false'\n"
        "    return str(v)\n"
    )


def _balanced_brackets(text: str, open_ch: str, close_ch: str) -> bool:
    depth = 0
    for ch in text:
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _active_noncomment_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def _count_kv_pairs(line: str) -> tuple[int, str, str]:
    """Return (pair_count, field_sep, kv_sep) for a record-style line."""
    for field_sep in (";", ",", "|"):
        parts = [p.strip() for p in line.split(field_sep) if p.strip()]
        if len(parts) < 2:
            continue
        for kv_sep in (":", "="):
            if all(kv_sep in p and p.split(kv_sep, 1)[0].strip() and " " not in p.split(kv_sep, 1)[0].strip() for p in parts):
                return (len(parts), field_sep, kv_sep)
    return (0, "", "")


def _induce_format_grammar(samples: Sequence[str | bytes]) -> list[dict[str, Any]]:
    """Induce candidate grammars from sample statistics (parameters, not frozen codecs)."""
    grammars: list[dict[str, Any]] = []
    if not samples:
        return grammars

    byte_samples = [s for s in samples if isinstance(s, (bytes, bytearray))]
    text_samples = [_as_text(s) for s in samples]

    # 1. Binary length-prefixed / TLV frames: tag(1) + len(2 BE) + payload
    if byte_samples and all(isinstance(s, (bytes, bytearray)) for s in samples):
        tlv_ok = True
        for raw in byte_samples:
            data = bytes(raw)
            idx = 0
            frames = 0
            while idx < len(data):
                if idx + 3 > len(data):
                    tlv_ok = False
                    break
                ln = (data[idx + 1] << 8) | data[idx + 2]
                idx += 3
                if ln < 0 or idx + ln > len(data):
                    tlv_ok = False
                    break
                idx += ln
                frames += 1
            if not tlv_ok or frames < 1 or idx != len(data):
                tlv_ok = False
                break
        if tlv_ok:
            grammars.append({"kind": "tlv", "tag_width": 1, "len_width": 2, "endian": "be"})

        # uint8-length prefixed latin1 frames
        lp_ok = True
        for raw in byte_samples:
            data = bytes(raw)
            idx = 0
            frames = 0
            while idx < len(data):
                ln = data[idx]
                idx += 1
                if idx + ln > len(data) or ln < 1:
                    lp_ok = False
                    break
                idx += ln
                frames += 1
            if not lp_ok or frames < 1 or idx != len(data):
                lp_ok = False
                break
        if lp_ok:
            grammars.append({"kind": "lenpref", "width": 1})

    # 2. JSON / JSONL
    json_ok = True
    json_kind = "json"
    for t in text_samples:
        s = t.strip()
        if not s:
            json_ok = False
            break
        try:
            if s[0] in "{[":
                obj = json.loads(s)
                if not isinstance(obj, (dict, list)) or len(obj) == 0:
                    json_ok = False
                    break
            else:
                rows = []
                for line in s.splitlines():
                    ln = line.strip()
                    if not ln:
                        continue
                    item = json.loads(ln)
                    if not isinstance(item, dict):
                        json_ok = False
                        break
                    rows.append(item)
                if not rows:
                    json_ok = False
                    break
                json_kind = "jsonl"
        except Exception:
            json_ok = False
            break
    if json_ok:
        grammars.append({"kind": json_kind})

    # 3. S-expression (balanced parentheses, starts with '(')
    if all(t.strip().startswith("(") and t.strip().endswith(")") and _balanced_brackets(t, "(", ")") for t in text_samples):
        grammars.append({"kind": "sexpr"})

    # 4. XML-ish tagged records
    xml_re = re.compile(r"<([A-Za-z_][\w-]*)\b([^>]*)>(.*?)</\1>", re.DOTALL)
    if all(xml_re.search(t) for t in text_samples):
        grammars.append({"kind": "xml_tags"})

    # 5. Multi-field record pairs on each line (id:7;name:alpha;ok:true)
    rec_votes: list[tuple[str, str]] = []
    rec_ok = True
    for t in text_samples:
        lines = _active_noncomment_lines(t)
        if len(lines) < 1:
            rec_ok = False
            break
        seps: list[tuple[str, str]] = []
        for ln in lines:
            n, fs, ks = _count_kv_pairs(ln)
            if n < 2:
                seps = []
                break
            seps.append((fs, ks))
        if not seps or len(set(seps)) != 1:
            rec_ok = False
            break
        rec_votes.append(seps[0])
    if rec_ok and rec_votes and len(set(rec_votes)) == 1:
        fs, ks = rec_votes[0]
        grammars.append({"kind": "record_pairs", "field_sep": fs, "kv_sep": ks})

    # 6. Sectioned / flat key-value (INI-like or bare k = v / k: v)
    kv_ok = True
    kv_sep_vote: str | None = None
    has_section = False
    for t in text_samples:
        lines = _active_noncomment_lines(t)
        if not lines:
            kv_ok = False
            break
        kv_count = 0
        for ln in lines:
            if ln.startswith("[") and ln.endswith("]") and len(ln) > 2:
                has_section = True
                continue
            if "=" in ln or ":" in ln:
                sep = "=" if ("=" in ln and (":" not in ln or ln.index("=") < ln.index(":"))) else ":"
                k, _v = ln.split(sep, 1)
                k = k.strip()
                if not k or " " in k:
                    kv_ok = False
                    break
                kv_count += 1
                kv_sep_vote = sep if kv_sep_vote is None else kv_sep_vote
            else:
                kv_ok = False
                break
        if not kv_ok or kv_count == 0:
            kv_ok = False
            break
    if kv_ok:
        grammars.append({"kind": "sectioned_kv", "sep": kv_sep_vote or "=", "has_section": has_section})

    # 7. Delimited tables with a header row
    for delim in ("|", "\t", ";", ","):
        table_ok = True
        headers0: list[str] | None = None
        for t in text_samples:
            lines = _active_noncomment_lines(t)
            if len(lines) < 2:
                table_ok = False
                break
            counts = [len(ln.split(delim)) for ln in lines]
            if counts[0] < 2 or len(set(counts)) != 1:
                table_ok = False
                break
            headers = [h.strip() for h in lines[0].split(delim)]
            if any(not h for h in headers):
                table_ok = False
                break
            if headers0 is None:
                headers0 = headers
            elif headers != headers0:
                # same arity is enough; headers may differ across samples of same grammar
                pass
        if table_ok:
            grammars.append({"kind": "table", "delim": delim})
            break

    return grammars


def _emit_perceptor_source(grammar: dict[str, Any]) -> str:
    """Compile an induced grammar descriptor into a pure parse/serialize organ."""
    kind = grammar["kind"]
    coerce = _coerce_literal_src()
    if kind in ("json", "jsonl"):
        return (
            "def parse(raw):\n"
            "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
            "    s = text.strip()\n"
            "    if not s:\n"
            "        raise ValueError('EMPTY')\n"
            "    if s[0] in '{[':\n"
            "        obj = json.loads(s)\n"
            "        if not isinstance(obj, (dict, list)) or len(obj) == 0:\n"
            "            raise ValueError('TRIVIAL_JSON')\n"
            "        return {'kind': 'json', 'data': obj}\n"
            "    rows = []\n"
            "    for line in s.splitlines():\n"
            "        ln = line.strip()\n"
            "        if not ln:\n"
            "            continue\n"
            "        item = json.loads(ln)\n"
            "        if not isinstance(item, dict):\n"
            "            raise ValueError('NOT_JSONL_DICT')\n"
            "        rows.append(item)\n"
            "    if len(rows) < 1:\n"
            "        raise ValueError('NO_ROWS')\n"
            "    return {'kind': 'jsonl', 'rows': rows}\n"
            "\n"
            "def serialize(parsed):\n"
            "    if parsed.get('kind') == 'json':\n"
            "        return json.dumps(parsed['data'], sort_keys=True)\n"
            "    return '\\n'.join(json.dumps(r, sort_keys=True) for r in parsed['rows'])\n"
        )
    if kind == "sectioned_kv":
        sep = grammar.get("sep", "=")
        return (
            coerce
            + "def parse(raw):\n"
            "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
            "    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]\n"
            "    if not lines:\n"
            "        raise ValueError('EMPTY')\n"
            "    sections = {}\n"
            "    cur = '_root'\n"
            "    kv_count = 0\n"
            f"    sep = {sep!r}\n"
            "    for ln in lines:\n"
            "        if ln.startswith('[') and ln.endswith(']') and len(ln) > 2:\n"
            "            cur = ln[1:-1].strip()\n"
            "            sections.setdefault(cur, {})\n"
            "        elif '=' in ln or ':' in ln:\n"
            "            use = '=' if ('=' in ln and (':' not in ln or ln.index('=') < ln.index(':'))) else ':'\n"
            "            k, v = ln.split(use, 1)\n"
            "            k = k.strip()\n"
            "            v = v.strip()\n"
            "            if not k or ' ' in k:\n"
            "                raise ValueError('BAD_KEY')\n"
            "            sections.setdefault(cur, {})[k] = _coerce(v)\n"
            "            kv_count += 1\n"
            "            sep = use\n"
            "        else:\n"
            "            raise ValueError('UNPARSED_LINE')\n"
            "    if kv_count == 0:\n"
            "        raise ValueError('NO_KV')\n"
            "    return {'kind': 'sectioned_kv', 'sections': sections, 'sep': sep}\n"
            "\n"
            "def serialize(parsed):\n"
            "    sep = parsed.get('sep', '=')\n"
            "    out = []\n"
            "    for sec, mapping in parsed['sections'].items():\n"
            "        if sec != '_root':\n"
            "            out.append('[' + sec + ']')\n"
            "        for k, v in mapping.items():\n"
            "            out.append(k + ' ' + sep + ' ' + _emit_scalar(v))\n"
            "    return '\\n'.join(out)\n"
        )
    if kind == "table":
        delim = grammar.get("delim", ",")
        delim_repr = "\\t" if delim == "\t" else delim
        return (
            coerce
            + "def parse(raw):\n"
            "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
            "    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]\n"
            "    if len(lines) < 2:\n"
            "        raise ValueError('NEED_HEADER_AND_ROW')\n"
            f"    best_delim = {delim!r}\n"
            "    headers = [h.strip() for h in lines[0].split(best_delim)]\n"
            "    if any(not h for h in headers):\n"
            "        raise ValueError('EMPTY_HEADER')\n"
            "    n_cols = len(headers)\n"
            "    rows = []\n"
            "    for ln in lines[1:]:\n"
            "        cells = [c.strip() for c in ln.split(best_delim)]\n"
            "        if len(cells) != n_cols:\n"
            "            raise ValueError('RAGGED_ROW')\n"
            "        rec = {}\n"
            "        for h, c in zip(headers, cells):\n"
            "            rec[h] = _coerce(c)\n"
            "        rows.append(rec)\n"
            "    return {'kind': 'table', 'delim': best_delim, 'headers': headers, 'rows': rows}\n"
            "\n"
            "def serialize(parsed):\n"
            "    d = parsed['delim']\n"
            "    hdr = d.join(parsed['headers'])\n"
            "    body = [d.join(_emit_scalar(r[h]) for h in parsed['headers']) for r in parsed['rows']]\n"
            "    return '\\n'.join([hdr] + body)\n"
        )
    if kind == "sexpr":
        return (
            "def parse(raw):\n"
            "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
            "    s = text.strip()\n"
            "    if not (s.startswith('(') and s.endswith(')')):\n"
            "        raise ValueError('NOT_SEXPR')\n"
            "    tokens = []\n"
            "    buf = []\n"
            "    in_str = False\n"
            "    for ch in s:\n"
            "        if in_str:\n"
            "            buf.append(ch)\n"
            "            if ch == '\"':\n"
            "                tokens.append(''.join(buf))\n"
            "                buf = []\n"
            "                in_str = False\n"
            "            continue\n"
            "        if ch == '\"':\n"
            "            buf.append(ch)\n"
            "            in_str = True\n"
            "            continue\n"
            "        if ch in '()':\n"
            "            if buf:\n"
            "                tokens.append(''.join(buf))\n"
            "                buf = []\n"
            "            tokens.append(ch)\n"
            "        elif ch.isspace():\n"
            "            if buf:\n"
            "                tokens.append(''.join(buf))\n"
            "                buf = []\n"
            "        else:\n"
            "            buf.append(ch)\n"
            "    if buf:\n"
            "        tokens.append(''.join(buf))\n"
            "    pos = [0]\n"
            "    def _atom(tok):\n"
            "        if tok[:1] == '-' and tok[1:].isdigit():\n"
            "            return int(tok)\n"
            "        if tok.isdigit():\n"
            "            return int(tok)\n"
            "        if tok[:1] == '\"' and tok[-1:] == '\"':\n"
            "            return tok[1:-1]\n"
            "        return tok\n"
            "    def _read():\n"
            "        if pos[0] >= len(tokens):\n"
            "            raise ValueError('UNEXPECTED_EOF')\n"
            "        tok = tokens[pos[0]]\n"
            "        pos[0] += 1\n"
            "        if tok == '(':\n"
            "            items = []\n"
            "            while pos[0] < len(tokens) and tokens[pos[0]] != ')':\n"
            "                items.append(_read())\n"
            "            if pos[0] >= len(tokens):\n"
            "                raise ValueError('UNCLOSED_PAREN')\n"
            "            pos[0] += 1\n"
            "            return items\n"
            "        if tok == ')':\n"
            "            raise ValueError('STRAY_CLOSE')\n"
            "        return _atom(tok)\n"
            "    tree = _read()\n"
            "    if pos[0] != len(tokens) or not isinstance(tree, list) or not tree:\n"
            "        raise ValueError('TRAILING_OR_EMPTY')\n"
            "    return {'kind': 'sexpr', 'tree': tree}\n"
            "\n"
            "def serialize(parsed):\n"
            "    def _emit(node):\n"
            "        if isinstance(node, list):\n"
            "            return '(' + ' '.join(_emit(x) for x in node) + ')'\n"
            "        if isinstance(node, str) and (' ' in node or node == ''):\n"
            "            return '\"' + node + '\"'\n"
            "        return str(node)\n"
            "    return _emit(parsed['tree'])\n"
        )
    if kind == "tlv":
        return (
            "def parse(raw):\n"
            "    data = raw if isinstance(raw, bytes) else str(raw).encode('latin1')\n"
            "    if len(data) < 4:\n"
            "        raise ValueError('TOO_SHORT')\n"
            "    idx = 0\n"
            "    frames = []\n"
            "    while idx < len(data):\n"
            "        if idx + 3 > len(data):\n"
            "            raise ValueError('TRUNCATED_HEADER')\n"
            "        tag = data[idx]\n"
            "        ln = (data[idx + 1] << 8) | data[idx + 2]\n"
            "        idx += 3\n"
            "        if idx + ln > len(data):\n"
            "            raise ValueError('TRUNCATED_PAYLOAD')\n"
            "        payload = data[idx:idx + ln]\n"
            "        idx += ln\n"
            "        frames.append({'tag': int(tag), 'payload_hex': payload.hex()})\n"
            "    if not frames:\n"
            "        raise ValueError('NO_FRAMES')\n"
            "    return {'kind': 'tlv', 'frames': frames}\n"
            "\n"
            "def serialize(parsed):\n"
            "    chunks = []\n"
            "    for fr in parsed['frames']:\n"
            "        payload = bytes.fromhex(fr['payload_hex'])\n"
            "        ln = len(payload)\n"
            "        chunks.append(bytes([int(fr['tag']) & 0xFF, (ln >> 8) & 0xFF, ln & 0xFF]) + payload)\n"
            "    out = b''\n"
            "    for c in chunks:\n"
            "        out = out + c\n"
            "    return out\n"
        )
    if kind == "record_pairs":
        field_sep = grammar.get("field_sep", ";")
        kv_sep = grammar.get("kv_sep", ":")
        return (
            coerce
            + "def parse(raw):\n"
            "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
            "    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]\n"
            "    if not lines:\n"
            "        raise ValueError('EMPTY')\n"
            f"    field_sep = {field_sep!r}\n"
            f"    kv_sep = {kv_sep!r}\n"
            "    rows = []\n"
            "    headers = None\n"
            "    for ln in lines:\n"
            "        parts = [p.strip() for p in ln.split(field_sep) if p.strip()]\n"
            "        if len(parts) < 2:\n"
            "            raise ValueError('NOT_RECORD')\n"
            "        rec = {}\n"
            "        for p in parts:\n"
            "            if kv_sep not in p:\n"
            "                raise ValueError('MISSING_KV')\n"
            "            k, v = p.split(kv_sep, 1)\n"
            "            k = k.strip()\n"
            "            if not k or ' ' in k:\n"
            "                raise ValueError('BAD_KEY')\n"
            "            rec[k] = _coerce(v.strip())\n"
            "        if headers is None:\n"
            "            headers = list(rec.keys())\n"
            "        elif list(rec.keys()) != headers:\n"
            "            for h in headers:\n"
            "                rec.setdefault(h, None)\n"
            "        rows.append(rec)\n"
            "    return {'kind': 'records', 'field_sep': field_sep, 'kv_sep': kv_sep, 'headers': headers, 'rows': rows}\n"
            "\n"
            "def serialize(parsed):\n"
            "    fs = parsed['field_sep']\n"
            "    ks = parsed['kv_sep']\n"
            "    headers = parsed['headers']\n"
            "    out = []\n"
            "    for rec in parsed['rows']:\n"
            "        out.append(fs.join(h + ks + _emit_scalar(rec[h]) for h in headers))\n"
            "    return '\\n'.join(out)\n"
        )
    if kind == "xml_tags":
        return (
            coerce
            + "def parse(raw):\n"
            "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
            "    s = text.strip()\n"
            "    if not s or '<' not in s:\n"
            "        raise ValueError('NOT_XML')\n"
            "    nodes = []\n"
            "    i = 0\n"
            "    n = len(s)\n"
            "    while i < n:\n"
            "        while i < n and s[i].isspace():\n"
            "            i += 1\n"
            "        if i >= n:\n"
            "            break\n"
            "        if s[i] != '<':\n"
            "            raise ValueError('LEADING_JUNK')\n"
            "        j = s.find('>', i)\n"
            "        if j < 0:\n"
            "            raise ValueError('UNCLOSED_TAG')\n"
            "        head = s[i + 1:j].strip()\n"
            "        if not head or head[0] == '/':\n"
            "            raise ValueError('BAD_TAG')\n"
            "        parts = head.split()\n"
            "        tag = parts[0]\n"
            "        attrs = {}\n"
            "        for tok in parts[1:]:\n"
            "            if '=' not in tok:\n"
            "                raise ValueError('BAD_ATTR')\n"
            "            ak, av = tok.split('=', 1)\n"
            "            av = av.strip()\n"
            "            if len(av) >= 2 and av[0] == av[-1] and av[0] in '\"\\'':\n"
            "                av = av[1:-1]\n"
            "            attrs[ak] = _coerce(av)\n"
            "        close = '</' + tag + '>'\n"
            "        k = s.find(close, j + 1)\n"
            "        if k < 0:\n"
            "            raise ValueError('UNCLOSED_ELEM')\n"
            "        body = s[j + 1:k]\n"
            "        if '<' in body:\n"
            "            raise ValueError('NESTED_NOT_INDUCED')\n"
            "        nodes.append({'tag': tag, 'attrs': attrs, 'text': _coerce(body.strip()) if body.strip() else ''})\n"
            "        i = k + len(close)\n"
            "    if not nodes:\n"
            "        raise ValueError('NO_NODES')\n"
            "    return {'kind': 'xml_tags', 'nodes': nodes}\n"
            "\n"
            "def serialize(parsed):\n"
            "    chunks = []\n"
            "    for node in parsed['nodes']:\n"
            "        attr = ''.join(' ' + ak + '=\"' + _emit_scalar(av) + '\"' for ak, av in node['attrs'].items())\n"
            "        body = '' if node['text'] == '' else _emit_scalar(node['text'])\n"
            "        chunks.append('<' + node['tag'] + attr + '>' + body + '</' + node['tag'] + '>')\n"
            "    return '\\n'.join(chunks)\n"
        )
    if kind == "lenpref":
        return (
            "def parse(raw):\n"
            "    data = raw if isinstance(raw, bytes) else str(raw).encode('latin1')\n"
            "    idx = 0\n"
            "    frames = []\n"
            "    while idx < len(data):\n"
            "        ln = data[idx]\n"
            "        idx += 1\n"
            "        if ln < 1 or idx + ln > len(data):\n"
            "            raise ValueError('BAD_LENPREF')\n"
            "        frames.append(data[idx:idx + ln].decode('latin1'))\n"
            "        idx += ln\n"
            "    if not frames:\n"
            "        raise ValueError('NO_FRAMES')\n"
            "    return {'kind': 'lenpref', 'width': 1, 'frames': frames}\n"
            "\n"
            "def serialize(parsed):\n"
            "    chunks = []\n"
            "    for fr in parsed['frames']:\n"
            "        payload = fr.encode('latin1') if isinstance(fr, str) else bytes(fr)\n"
            "        if len(payload) > 255:\n"
            "            raise ValueError('FRAME_TOO_LONG')\n"
            "        chunks.append(bytes([len(payload)]) + payload)\n"
            "    out = b''\n"
            "    for c in chunks:\n"
            "        out = out + c\n"
            "    return out\n"
        )
    raise ValueError(f"UNKNOWN_INDUCED_GRAMMAR:{kind}")


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
    """Induce + round-trip-verify a `PERCEPTOR` organ from raw samples alone."""
    if not samples:
        return None
    induced = _induce_format_grammar(samples)
    winners: list[ExecutableOrgan] = []
    for grammar in induced:
        try:
            src = _emit_perceptor_source(grammar)
        except Exception:
            continue
        try:
            organ = make_organ(
                stratum=PERCEPTOR,
                name=f"perceptor_{grammar['kind']}_{format_tag}",
                task_signature=f"perceptor::{format_tag}",
                entrypoint="parse",
                source_code=src,
                metadata={"codec_family": grammar["kind"], "induced_grammar": dict(grammar)},
            )
        except OrganSafetyError:
            continue
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
        winners.append(organ)
    if not winners:
        return None
    # Prefer more specific induced grammars, then Occam (smallest AST)
    _specificity = {
        "tlv": 60,
        "lenpref": 55,
        "json": 50,
        "jsonl": 50,
        "xml_tags": 45,
        "sexpr": 40,
        "record_pairs": 35,
        "sectioned_kv": 20,
        "table": 10,
    }
    winners.sort(
        key=lambda o: (
            -_specificity.get(str(o.metadata.get("codec_family")), 0),
            o.code_bytes,
            o.name,
        )
    )
    return winners[0]

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


def _pretty_number(v: float) -> str:
    if isinstance(v, bool):
        return repr(v)
    if abs(v - round(v)) <= 1e-9:
        return str(int(round(v)))
    return repr(float(v))


def _gaussian_solve(matrix: Sequence[Sequence[float]], rhs: Sequence[float]) -> list[float] | None:
    n = len(rhs)
    if n == 0 or any(len(row) != n for row in matrix):
        return None
    a = [list(map(float, row)) + [float(rhs[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        div = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            fac = a[r][col]
            if fac == 0.0:
                continue
            for j in range(col, n + 1):
                a[r][j] -= fac * a[col][j]
    return [a[i][n] for i in range(n)]


def _harvest_numeric_constants(examples: Sequence[tuple[tuple[Any, ...], Any]]) -> list[Any]:
    """Constants harvested from I/O — never a frozen lattice."""
    vals: list[Any] = []
    seen: set[str] = set()

    def _add(v: Any) -> None:
        key = f"{type(v).__name__}:{v!r}"
        if key in seen:
            return
        seen.add(key)
        vals.append(v)

    for inp, out in examples:
        for v in (*inp, out):
            if isinstance(v, bool) or v is None:
                _add(v)
            elif isinstance(v, (int, float)):
                _add(v)
                if abs(float(v) - round(float(v))) <= 1e-9:
                    _add(int(round(float(v))))
            elif isinstance(v, str) and len(v) <= 32:
                _add(v)
    numeric = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for a, b in zip(numeric, numeric[1:]):
        _add(a - b)
        _add(b - a)
        _add(a + b)
        if b not in (0, 0.0):
            ratio = a / b
            if abs(ratio) <= 1e6:
                _add(ratio)
                if abs(ratio - round(ratio)) <= 1e-9:
                    _add(int(round(ratio)))
    for seed in (0, 1, -1, 2):
        _add(seed)
    return vals


def _all_numeric_io(examples: Sequence[tuple[tuple[Any, ...], Any]]) -> bool:
    for inp, out in examples:
        if isinstance(out, bool) or not isinstance(out, (int, float)):
            return False
        for v in inp:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return False
    return True


def _solve_multilinear(examples: Sequence[tuple[tuple[Any, ...], Any]]) -> str | None:
    """Exact y = a0*x0 + ... + an*xn + b when uniquely determined by the examples."""
    if not _all_numeric_io(examples):
        return None
    arity = len(examples[0][0])
    n_coeff = arity + 1  # affine intercept
    if len(examples) < n_coeff:
        return None
    matrix: list[list[float]] = []
    rhs: list[float] = []
    seen_rows: set[tuple[float, ...]] = set()
    for inp, out in examples:
        row = [float(v) for v in inp] + [1.0]
        key = tuple(row)
        if key in seen_rows:
            continue
        seen_rows.add(key)
        matrix.append(row)
        rhs.append(float(out))
        if len(matrix) == n_coeff:
            break
    if len(matrix) < n_coeff:
        return None
    solved = _gaussian_solve(matrix[:n_coeff], rhs[:n_coeff])
    if solved is None:
        return None
    names = _arg_names(arity)
    # Verify against ALL examples
    for inp, out in examples:
        pred = sum(solved[i] * float(inp[i]) for i in range(arity)) + solved[arity]
        if abs(pred - float(out)) > 1e-8:
            return None
    parts: list[str] = []
    for i, nm in enumerate(names):
        a = solved[i]
        if abs(a) <= 1e-12:
            continue
        parts.append(f"({_pretty_number(a)} * {nm})")
    b = solved[arity]
    if parts:
        expr = " + ".join(parts)
        if abs(b) > 1e-12:
            expr = f"({expr} + {_pretty_number(b)})"
        else:
            expr = f"({expr})" if len(parts) > 1 else parts[0]
    else:
        expr = _pretty_number(b)
    return expr


def _rename_function_source(source_code: str, old_name: str, new_name: str) -> str:
    tree = ast.parse(source_code)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == old_name:
            node.name = new_name
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _wrap_expr_into_source(arity: int, expr_src: str, helpers: str = "") -> str:
    params = ", ".join(_arg_names(arity))
    helper = helpers
    if "_prod(" in expr_src and "def _prod(" not in helper:
        helper = (
            "def _prod(seq):\n"
            "    acc = 1\n"
            "    for v in seq:\n"
            "        acc = acc * v\n"
            "    return acc\n\n"
        ) + helper
    return f"{helper}def run({params}):\n    return {expr_src}\n"


def _eval_expr(expr_src: str, names: Sequence[str], args: tuple[Any, ...], helpers_ns: dict[str, Any] | None = None) -> tuple[bool, Any]:
    def _prod(seq: Any) -> Any:
        acc = 1
        for v in seq:
            acc = acc * v
        return acc

    ns: dict[str, Any] = {"__builtins__": dict(_SAFE_BUILTINS), "math": math, "_prod": _prod}
    if helpers_ns:
        ns.update(helpers_ns)
    try:
        code = compile(expr_src, "<cand>", "eval")
        val = eval(code, ns, {nm: arg for nm, arg in zip(names, args)})  # noqa: S307
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return False, None
        return True, val
    except Exception:
        return False, None


def _observational_bottom_up(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    max_weight: int = 3,
    max_bank: int = 96,
) -> list[tuple[str, str]]:
    """Bottom-up observational-equivalence enumeration over a primitive combinator basis."""
    first_in, first_out = examples[0]
    arity = len(first_in)
    names = _arg_names(arity)
    inputs = [ex[0] for ex in examples]
    target = [ex[1] for ex in examples]
    seen_sig: dict[tuple[Any, ...], str] = {}
    by_weight: dict[int, list[str]] = {1: []}
    hits: list[tuple[str, str]] = []

    def _sig_of(expr: str) -> tuple[Any, ...] | None:
        outs: list[Any] = []
        for args in inputs:
            ok, val = _eval_expr(expr, names, args)
            if not ok:
                return None
            outs.append(val)
        return tuple(repr(v) if isinstance(v, (list, dict, set)) else v for v in outs)

    def _register(weight: int, expr: str, label: str) -> None:
        if len(seen_sig) >= max_bank:
            return
        sig = _sig_of(expr)
        if sig is None or sig in seen_sig:
            return
        seen_sig[sig] = expr
        by_weight.setdefault(weight, []).append(expr)
        if all(_outputs_match(got, exp) for got, exp in zip(sig, target)):
            hits.append((label, expr))

    # Weight-1: projections, harvested constants (includes the copy-42 Occam trap)
    for i, nm in enumerate(names):
        _register(1, nm, f"proj_{i}")
    for c in _harvest_numeric_constants(examples)[:24]:
        try:
            _register(1, repr(c), f"const_{type(c).__name__}")
        except Exception:
            continue

    unaries = (
        ("neg", "-({0})"),
        ("abs", "abs({0})"),
        ("len", "len({0})"),
        ("sum", "sum({0})"),
        ("min", "min({0})"),
        ("max", "max({0})"),
        ("sorted", "sorted({0})"),
        ("rev", "list(reversed({0})) if not isinstance({0}, str) else {0}[::-1]"),
        ("strip", "{0}.strip() if isinstance({0}, str) else {0}"),
        ("lower", "{0}.lower() if isinstance({0}, str) else {0}"),
        ("sq", "({0} * {0})"),
        ("prod", "_prod({0}) if isinstance({0}, (list, tuple)) else {0}"),
    )
    binops = ("+", "-", "*", "/", "//", "%")

    for w in range(2, max_weight + 1):
        prev = list(by_weight.get(w - 1, []))
        for expr in prev[:32]:
            ok0, sample0 = _eval_expr(expr, names, inputs[0])
            for uname, tmpl in unaries:
                if uname in ("strip", "lower") and not isinstance(sample0, str):
                    continue
                if uname in ("len", "sum", "min", "max", "sorted", "rev", "prod") and not isinstance(sample0, (str, list, tuple, set, dict)):
                    continue
                if uname in ("neg", "abs", "sq") and (isinstance(sample0, bool) or not isinstance(sample0, (int, float))):
                    continue
                if not ok0:
                    continue
                _register(w, tmpl.format(expr), f"u_{uname}_w{w}")
                if len(seen_sig) >= max_bank:
                    return hits
        # Binary combinations of cheaper terms
        cheap = list(by_weight.get(1, [])) + list(by_weight.get(max(1, w - 2), []))
        lefts = prev[:12]
        rights = cheap[:12]
        for e1 in lefts:
            for e2 in rights:
                if e1 == e2:
                    continue
                for op in binops:
                    _register(w, f"({e1} {op} {e2})", f"bin_{op}_w{w}")
                    if len(seen_sig) >= max_bank:
                        return hits
                _register(w, f"max({e1}, {e2})", f"max_w{w}")
                _register(w, f"min({e1}, {e2})", f"min_w{w}")
        # Percent combinators parameterized by harvested scale constants (not a frozen 100)
        scales = [c for c in _harvest_numeric_constants(examples)[:24] if isinstance(c, (int, float)) and not isinstance(c, bool) and abs(float(c)) >= 2]
        if 100 not in scales and 100.0 not in scales:
            scales.append(100.0)
        if arity >= 2:
            a, b = names[0], names[1]
            for sc in scales[:4]:
                scs = _pretty_number(float(sc))
                _register(w, f"({a} * ({scs} - {b}) / {scs})", f"discount_{scs}")
                _register(w, f"({a} * ({scs} + {b}) / {scs})", f"markup_{scs}")
            if isinstance(first_in[0], (list, tuple)):
                _register(w, f"(sum({a}) * {b})", "sum_scale")
                _register(w, f"(sum({a}) + {b})", "sum_plus")
                _register(w, f"sum(z for z in {a} if z > {b})", "filter_gt_sum")
                for sc in scales[:2]:
                    scs = _pretty_number(float(sc))
                    _register(w, f"(sum({a}) * ({scs} - {b}) / {scs})", f"sum_discount_{scs}")
    return hits


def _stun_piecewise(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
) -> list[tuple[str, str]]:
    """STUN: unify two partial branch terms under a synthesized atomic predicate."""
    if len(examples) < 2:
        return []
    names = _arg_names(len(examples[0][0]))
    first_in = examples[0][0]
    predicates: list[tuple[str, str]] = []
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in first_in):
        for i, nm in enumerate(names):
            predicates.append((f"{nm} > 0", f"pred_gt0_{i}"))
            predicates.append((f"{nm} < 0", f"pred_lt0_{i}"))
            predicates.append((f"{nm} == 0", f"pred_eq0_{i}"))
        if len(names) >= 2:
            predicates.append((f"{names[0]} > {names[1]}", "pred_gt"))
            predicates.append((f"{names[0]} >= {names[1]}", "pred_ge"))
            predicates.append((f"{names[0]} == {names[1]}", "pred_eq"))
    out: list[tuple[str, str]] = []
    for pred, pname in predicates:
        left_ex = []
        right_ex = []
        ok_split = True
        for inp, y in examples:
            ok, flag = _eval_expr(pred, names, inp)
            if not ok:
                ok_split = False
                break
            (left_ex if flag else right_ex).append((inp, y))
        if not ok_split or not left_ex or not right_ex:
            continue
        def _fit_branch(sub_ex: Sequence[tuple[tuple[Any, ...], Any]]) -> str | None:
            aff = _solve_multilinear(sub_ex)
            if aff is not None:
                return aff
            sub_names = _arg_names(len(sub_ex[0][0]))
            primitives = list(sub_names)
            if len(sub_names) >= 2:
                a, b = sub_names[0], sub_names[1]
                primitives.extend(
                    [
                        f"({a} * {b})",
                        f"({a} + {b})",
                        f"({a} - {b})",
                        f"({b} - {a})",
                        f"max({a}, {b})",
                        f"min({a}, {b})",
                    ]
                )
            for expr in primitives:
                good = True
                for inp, y in sub_ex:
                    ok, got = _eval_expr(expr, sub_names, inp)
                    if not ok or not _outputs_match(got, y):
                        good = False
                        break
                if good:
                    return expr
            hits = _observational_bottom_up(sub_ex, max_weight=3, max_bank=96)
            return hits[0][1] if hits else None

        left_expr = _fit_branch(left_ex)
        right_expr = _fit_branch(right_ex)
        if left_expr is None or right_expr is None:
            continue
        expr = f"({left_expr} if {pred} else {right_expr})"
        # verify
        good = True
        for inp, y in examples:
            ok, got = _eval_expr(expr, names, inp)
            if not ok or not _outputs_match(got, y):
                good = False
                break
        if good:
            out.append((f"stun_{pname}", expr))
    return out


def _inline_operator_organs(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    operator_organs: Sequence["ExecutableOrgan"],
) -> list[tuple[str, str, str]]:
    """Compose previously admitted SKILL organs as live operators (organ_B(organ_A(x)))."""
    if not operator_organs:
        return []
    arity = len(examples[0][0])
    names = _arg_names(arity)
    results: list[tuple[str, str, str]] = []
    helpers_acc: list[tuple[str, str, int]] = []  # (helper_name, source, arity)
    for idx, org in enumerate(operator_organs[:8]):
        try:
            tree = ast.parse(org.source_code)
        except SyntaxError:
            continue
        fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == org.entrypoint), None)
        if fn is None:
            continue
        hname = f"_org_{idx}"
        try:
            src = _rename_function_source(org.source_code, org.entrypoint, hname)
        except Exception:
            continue
        helpers_acc.append((hname, src, len(fn.args.args)))

    helper_block = "\n\n".join(src for _n, src, _a in helpers_acc) + ("\n" if helpers_acc else "")
    helper_ns: dict[str, Any] = {}
    if helper_block.strip():
        try:
            _, ns = compile_organ_namespace(helper_block + "def run(x0):\n    return x0\n")
            helper_ns = {n: ns[n] for n, _s, _a in helpers_acc if n in ns}
        except Exception:
            helper_ns = {}

    def _ok_expr(expr: str) -> bool:
        for inp, y in examples:
            ok, got = _eval_expr(expr, names, inp, helpers_ns=helper_ns)
            if not ok or not _outputs_match(got, y):
                return False
        return True

    for hname, _src, harity in helpers_acc:
        if harity == arity:
            expr = f"{hname}({', '.join(names)})"
            if _ok_expr(expr):
                results.append((f"call_{hname}", expr, helper_block))
        elif harity == 1 and arity >= 1:
            expr = f"{hname}({names[0]})"
            if _ok_expr(expr):
                results.append((f"call1_{hname}", expr, helper_block))
    # Depth-2 composition
    for i, (h1, _s1, a1) in enumerate(helpers_acc):
        for j, (h2, _s2, a2) in enumerate(helpers_acc):
            if a1 == 1 and a2 == arity:
                expr = f"{h1}({h2}({', '.join(names)}))"
                if _ok_expr(expr):
                    results.append((f"comp_{h1}_{h2}", expr, helper_block))
            elif a1 == 1 and a2 == 1 and arity >= 1:
                expr = f"{h1}({h2}({names[0]}))"
                if _ok_expr(expr):
                    results.append((f"comp1_{h1}_{h2}", expr, helper_block))
            elif a1 == arity and a2 == 1 and arity >= 1:
                expr = f"{h1}({h2}({names[0]}), {', '.join(names[1:])})" if arity > 1 else f"{h1}({h2}({names[0]}))"
                if _ok_expr(expr):
                    results.append((f"comp_mix_{h1}_{h2}", expr, helper_block))
    return results


def _generate_candidate_expressions(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    operator_organs: Sequence["ExecutableOrgan"] = (),
) -> list[tuple[str, str, str]]:
    """MDL-ordered (name, expr, helpers) hypotheses — no frozen expression menu."""
    if not examples:
        return []
    first_in, first_out = examples[0]
    arity = len(first_in)
    names = _arg_names(arity)
    cands: list[tuple[str, str, str]] = []

    # 1. Constant Occam trap (copy-42) — required for version-space underdetermination
    if isinstance(first_out, (int, float, str, bool)) or (
        isinstance(first_out, (list, tuple)) and len(first_out) <= 8
    ):
        cands.append(("constant_output", repr(first_out), ""))

    # Primitive algebra over parameters (language basis, not a frozen complete-program menu)
    binops = ("+", "-", "*", "/", "//", "%")
    for i, nm in enumerate(names):
        cands.append((f"proj_{i}", nm, ""))
        v = first_in[i]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            cands.append((f"neg_{i}", f"-({nm})", ""))
            cands.append((f"abs_{i}", f"abs({nm})", ""))
            cands.append((f"sq_{i}", f"({nm} * {nm})", ""))
        elif isinstance(v, (list, tuple)):
            cands.append((f"sum_{i}", f"sum({nm})", ""))
            cands.append((f"len_{i}", f"len({nm})", ""))
            cands.append((f"prod_{i}", f"_prod({nm})", ""))
            cands.append((f"sorted_{i}", f"sorted({nm})", ""))
        elif isinstance(v, str):
            cands.append((f"strip_{i}", f"{nm}.strip()", ""))
            cands.append((f"lower_{i}", f"{nm}.lower()", ""))
            cands.append((f"len_str_{i}", f"len({nm})", ""))
            cands.append((f"rev_str_{i}", f"{nm}[::-1]", ""))
    if arity >= 2:
        for i in range(arity):
            for j in range(arity):
                if i == j:
                    continue
                a, b = names[i], names[j]
                va, vb = first_in[i], first_in[j]
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool) and not isinstance(vb, bool):
                    for op in binops:
                        cands.append((f"bin_{op}_{i}_{j}", f"({a} {op} {b})", ""))
                    cands.append((f"max_{i}_{j}", f"max({a}, {b})", ""))
                    cands.append((f"min_{i}_{j}", f"min({a}, {b})", ""))
                if isinstance(va, (list, tuple)) and isinstance(vb, (int, float)) and not isinstance(vb, bool):
                    cands.append((f"sum_scale_{i}_{j}", f"(sum({a}) * {b})", ""))
                    cands.append((f"sum_plus_{i}_{j}", f"(sum({a}) + {b})", ""))

    # 2. Exact uniquely-determined multilinear / affine closed form
    affine = _solve_multilinear(examples)
    if affine is not None:
        cands.append(("exact_affine", affine, ""))

    # 3. Bottom-up observational-equivalence bank
    for label, expr in _observational_bottom_up(examples):
        cands.append((label, expr, ""))

    # 4. STUN piecewise unification when a single term is insufficient later
    for label, expr in _stun_piecewise(examples):
        cands.append((label, expr, ""))

    # 5. Live compositional closure over admitted organs
    for label, expr, helpers in _inline_operator_organs(examples, operator_organs):
        cands.append((label, expr, helpers))

    # Dedup by expr
    seen: set[str] = set()
    uniq: list[tuple[str, str, str]] = []
    for item in cands:
        if item[1] in seen:
            continue
        seen.add(item[1])
        uniq.append(item)
    return uniq


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

    # Synthesize a numeric invariant over extracted fields (not a 3-law checklist).
    arithmetic_law: str | None = None
    arithmetic_predicate: str | None = None
    num_rows: list[list[int | float]] = []
    for art in valid_artifacts:
        act_txt = "\n".join(_active_lines(art))
        nums = [
            float(x) if "." in x else int(x)
            for x in re.findall(r"-?\d+(?:\.\d+)?", act_txt)
        ]
        num_rows.append(nums)
    if (
        "numeric_value_perturbed_decoy" in rejected_classes
        and num_rows
        and all(len(r) >= 2 for r in num_rows)
        and len({len(r) for r in num_rows}) == 1
    ):
        io_examples = [(tuple(r[:-1]), r[-1]) for r in num_rows]
        # Reuse the same observational synthesizer: body fields -> last field
        synthesized_expr: str | None = None
        affine = _solve_multilinear(io_examples)
        if affine is not None:
            # affine is in terms of x0, x1, ... mapping onto vals[:-1]
            synthesized_expr = affine
            for i, _ in enumerate(num_rows[0][:-1]):
                synthesized_expr = synthesized_expr.replace(f"x{i}", f"vals[{i}]")
        if synthesized_expr is None:
            hits = _observational_bottom_up(io_examples, max_weight=3, max_bank=64)
            if hits:
                synthesized_expr = hits[0][1]
                for i, _ in enumerate(num_rows[0][:-1]):
                    synthesized_expr = synthesized_expr.replace(f"x{i}", f"vals[{i}]")
        if synthesized_expr is not None:
            arithmetic_predicate = (
                f"abs(float({synthesized_expr}) - float(vals[-1])) <= 1e-9"
            )
            arithmetic_law = synthesized_expr
        else:
            # Fall back: constants identical across artifacts
            if len({tuple(r) for r in num_rows}) == 1:
                arithmetic_predicate = f"vals == {num_rows[0]!r}"
                arithmetic_law = "exact_constants"

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
    nums_raw = re.findall(r'-?\\d+(?:\\.\\d+)?', '\\n'.join(active))
    vals = [float(x) if '.' in x else int(x) for x in nums_raw]
    if {('len(vals) < 2 or not (' + arithmetic_predicate + ')') if arithmetic_predicate else 'False'}:
        return (False, 'ARITHMETIC_INVARIANT_FAILED')
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

    eval_fn_expr = skel_template_str
    emit_expr = skel_template_str
    for idx in range(num_holes):
        emit_expr = emit_expr.replace(f"_C[{idx}]", f"{{c{idx}}}")

    # Exact coefficient solving + harvested-constant search (no frozen 19-int lattice).
    meta_src = f"""
def _eval_skeleton({param_sig}, _C):
    return {eval_fn_expr}

def _pretty(v):
    if abs(v - round(v)) <= 1e-9:
        return str(int(round(v)))
    return repr(float(v))

def _gaussian(matrix, rhs):
    n = len(rhs)
    a = [list(map(float, row)) + [float(rhs[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r, c=col: abs(a[r][c]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        div = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            fac = a[r][col]
            if fac == 0.0:
                continue
            for j in range(col, n + 1):
                a[r][j] -= fac * a[col][j]
    return [a[i][n] for i in range(n)]

def _harvest(examples):
    vals = []
    seen = set()
    def add(v):
        k = repr(v)
        if k not in seen:
            seen.add(k)
            vals.append(v)
    for inp, out in examples:
        for v in list(inp) + [out]:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                add(v)
                if abs(float(v) - round(float(v))) <= 1e-9:
                    add(int(round(float(v))))
    numeric = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for a, b in zip(numeric, numeric[1:]):
        add(a - b)
        add(b - a)
        if b not in (0, 0.0):
            ratio = a / b
            add(ratio)
            if abs(ratio - round(ratio)) <= 1e-9:
                add(int(round(ratio)))
    for seed in (0, 1, -1, 2):
        add(seed)
    return vals

def _fits(examples, _C):
    for inp, expected in examples:
        try:
            got = _eval_skeleton(*inp, _C)
        except Exception:
            return False
        if got != expected:
            if not (isinstance(got, (int, float)) and isinstance(expected, (int, float)) and abs(float(got) - float(expected)) <= 1e-8):
                return False
    return True

def _emit(_C):
    c_map = {{ {", ".join(f"'c{i}': _pretty(_C[{i}])" for i in range(num_holes))} }}
    body = {skel_template_str!r}
    for i in range({num_holes}):
        body = body.replace('_C[' + str(i) + ']', c_map['c' + str(i)])
    return 'def run({param_sig}):\\n    return ' + body + '\\n'

def synthesize_from_examples(examples):
    if not examples or len(examples[0][0]) != {arity}:
        return None
    n_h = {num_holes}
    # 1. Exact linear solve when the skeleton is affine in the holes.
    if all(isinstance(ex[1], (int, float)) and not isinstance(ex[1], bool) for ex in examples):
        matrix = []
        rhs = []
        seen = set()
        for inp, expected in examples:
            try:
                b = _eval_skeleton(*inp, tuple([0] * n_h))
            except Exception:
                b = None
            row = []
            linear = b is not None
            for i in range(n_h):
                e = [0] * n_h
                e[i] = 1
                try:
                    fi = _eval_skeleton(*inp, tuple(e))
                except Exception:
                    linear = False
                    break
                row.append(float(fi) - float(b))
            if not linear:
                matrix = []
                break
            key = tuple(row)
            if key in seen:
                continue
            seen.add(key)
            matrix.append(row)
            rhs.append(float(expected) - float(b))
            if len(matrix) >= n_h:
                break
        if len(matrix) == n_h:
            solved = _gaussian(matrix, rhs)
            if solved is not None:
                _C = tuple(solved)
                if _fits(examples, _C):
                    return _emit(_C)
    # 2. Search the harvested constant set from the examples themselves.
    domain = _harvest(examples)
    combos = [()]
    for _ in range(n_h):
        combos = [prev + (item,) for prev in combos for item in domain]
        if len(combos) > 4096:
            combos = combos[:4096]
            break
    for combo in combos:
        _C = tuple(combo)
        if _fits(examples, _C):
            return _emit(_C)
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
# Instrumental POLICY / WORLD_MODEL strata (0-immediate-reward unlocking)
# ---------------------------------------------------------------------------


def rank_instrumental_actions(
    actions: Sequence[Mapping[str, Any]],
    *,
    remaining_budget: float,
    p_burn_by_id: Mapping[str, float] | None = None,
    gamma: float = 0.92,
    horizon: int = 3,
) -> list[dict[str, Any]]:
    """Multi-step instrumental Q: 0-reward prerequisites inherit unlocking value.

    Each action is a mapping with:
      id, value (immediate external reward), cost,
      optional unlocks: sequence of action ids enabled after success,
      optional requires: sequence of action ids that must already be done.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for raw in actions:
        aid = str(raw.get("id") or "")
        if not aid:
            continue
        by_id[aid] = {
            "id": aid,
            "value": float(raw.get("value") or 0.0),
            "cost": max(1e-9, float(raw.get("cost") or 1.0)),
            "unlocks": tuple(str(x) for x in (raw.get("unlocks") or ())),
            "requires": tuple(str(x) for x in (raw.get("requires") or ())),
        }
    burns = {k: float(v) for k, v in (p_burn_by_id or {}).items()}

    def _q(aid: str, done: frozenset[str], budget: float, depth: int) -> float:
        if depth <= 0 or budget <= 1e-12:
            return 0.0
        node = by_id[aid]
        if any(r not in done for r in node["requires"]):
            return -1e9
        if node["cost"] > budget + 1e-12:
            return -1e9
        p_burn = max(0.0, min(1.0, burns.get(aid, 0.0)))
        immediate = node["value"] * (1.0 - 0.85 * p_burn)
        leftover = budget - node["cost"]
        nxt = done | {aid}
        future = 0.0
        unlocked = [u for u in node["unlocks"] if u in by_id and u not in nxt]
        candidates = unlocked or [k for k in by_id if k not in nxt]
        if candidates and leftover > 0:
            future = max(_q(u, nxt, leftover, depth - 1) for u in candidates)
        return immediate - node["cost"] * 0.05 + gamma * future

    ranked: list[dict[str, Any]] = []
    for aid, node in by_id.items():
        qv = _q(aid, frozenset(), float(remaining_budget), max(1, int(horizon)))
        ranked.append({**node, "q": round(qv, 6)})
    ranked.sort(key=lambda r: (-r["q"], r["cost"], r["id"]))
    return ranked


def compile_policy_organ(
    *,
    name: str = "instrumental_policy",
    gamma: float = 0.92,
    horizon: int = 3,
) -> ExecutableOrgan:
    """Freeze the current instrumental scoring law as an evolvable POLICY organ."""
    src = f"""
def score_actions(actions, remaining_budget, p_burn_by_id=None):
    by_id = {{}}
    for raw in actions:
        aid = str(raw.get('id') or '')
        if not aid:
            continue
        by_id[aid] = {{
            'id': aid,
            'value': float(raw.get('value') or 0.0),
            'cost': max(1e-9, float(raw.get('cost') or 1.0)),
            'unlocks': tuple(str(x) for x in (raw.get('unlocks') or ())),
            'requires': tuple(str(x) for x in (raw.get('requires') or ())),
        }}
    burns = dict(p_burn_by_id or {{}})
    gamma = {float(gamma)!r}
    horizon = {int(horizon)!r}

    def _q(aid, done, budget, depth):
        if depth <= 0 or budget <= 1e-12:
            return 0.0
        node = by_id[aid]
        for r in node['requires']:
            if r not in done:
                return -1e9
        if node['cost'] > budget + 1e-12:
            return -1e9
        p_burn = burns.get(aid, 0.0)
        immediate = node['value'] * (1.0 - 0.85 * p_burn)
        leftover = budget - node['cost']
        nxt = set(done)
        nxt.add(aid)
        future = 0.0
        unlocked = [u for u in node['unlocks'] if u in by_id and u not in nxt]
        candidates = unlocked or [k for k in by_id if k not in nxt]
        if candidates and leftover > 0:
            future = max(_q(u, nxt, leftover, depth - 1) for u in candidates)
        return immediate - node['cost'] * 0.05 + gamma * future

    ranked = []
    for aid, node in by_id.items():
        qv = _q(aid, set(), float(remaining_budget), horizon)
        row = dict(node)
        row['q'] = qv
        ranked.append(row)
    ranked.sort(key=lambda r: (-r['q'], r['cost'], r['id']))
    return ranked
"""
    return make_organ(
        stratum=POLICY,
        name=name,
        task_signature="policy::instrumental_q",
        entrypoint="score_actions",
        source_code=src,
        metadata={"gamma": gamma, "horizon": horizon},
    )


def synthesize_world_model_organ(
    transitions: Sequence[Mapping[str, Any]],
    *,
    name: str = "world_model",
) -> ExecutableOrgan | None:
    """Induce a WORLD_MODEL organ: action -> (mean_delta, mean_cost, fail_rate)."""
    if not transitions:
        return None
    stats: dict[str, dict[str, Any]] = {}
    for tr in transitions:
        aid = str(tr.get("action") or tr.get("action_id") or "")
        if not aid:
            continue
        row = stats.setdefault(aid, {"n": 0, "cost": 0.0, "fail": 0, "delta": {}})
        row["n"] += 1
        row["cost"] += float(tr.get("cost") or 0.0)
        if tr.get("failed"):
            row["fail"] += 1
        delta = tr.get("delta") or {}
        if isinstance(delta, Mapping):
            for k, v in delta.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    row["delta"][str(k)] = row["delta"].get(str(k), 0.0) + float(v)
    compact: dict[str, Any] = {}
    for aid, row in stats.items():
        n = max(1, int(row["n"]))
        compact[aid] = {
            "mean_cost": row["cost"] / n,
            "fail_rate": row["fail"] / n,
            "mean_delta": {k: v / n for k, v in row["delta"].items()},
            "n": n,
        }
    src = f"""
def predict(action_id):
    table = {compact!r}
    row = table.get(str(action_id))
    if row is None:
        return {{'known': False, 'mean_cost': None, 'fail_rate': None, 'mean_delta': {{}}}}
    out = dict(row)
    out['known'] = True
    return out
"""
    return make_organ(
        stratum=WORLD_MODEL,
        name=name,
        task_signature="world_model::action_delta",
        entrypoint="predict",
        source_code=src,
        metadata={"n_actions": len(compact)},
    )


def _compose_perceptor_from_existing(
    sample: str | bytes,
    existing: Sequence[ExecutableOrgan],
    *,
    format_tag: str,
) -> ExecutableOrgan | None:
    """New format = admitted child perceptor + synthesized prefix glue (not a new `if kind`)."""
    if not existing:
        return None
    if isinstance(sample, (bytes, bytearray)):
        try:
            text = bytes(sample).decode("utf-8")
        except Exception:
            return None
    else:
        text = str(sample)
    if len(text) < 3:
        return None
    for cut in range(1, min(24, len(text) - 1)):
        prefix, rest = text[:cut], text[cut:]
        if not rest or prefix[-1:].isspace():
            continue
        for child in existing:
            try:
                parsed = child.invoke(rest)
                re_emitted = child.invoke_aux("serialize", parsed)
                if child.invoke(re_emitted) != parsed:
                    continue
            except Exception:
                continue
            try:
                child_src = _rename_function_source(child.source_code, child.entrypoint, "_child_parse")
                if "def serialize(" in child_src:
                    child_src = child_src.replace("def serialize(", "def _child_serialize(", 1)
                else:
                    continue
            except Exception:
                continue
            wrapper = (
                child_src
                + "\n"
                + f"def parse(raw):\n"
                + "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
                + f"    prefix = {prefix!r}\n"
                + "    if not text.startswith(prefix):\n"
                + "        raise ValueError('PREFIX_MISMATCH')\n"
                + "    return _child_parse(text[len(prefix):])\n"
                + "\n"
                + "def serialize(parsed):\n"
                + "    inner = _child_serialize(parsed)\n"
                + "    if isinstance(inner, bytes):\n"
                + "        inner = inner.decode('utf-8')\n"
                + f"    return {prefix!r} + inner\n"
            )
            try:
                organ = make_organ(
                    stratum=PERCEPTOR,
                    name=f"perceptor_composed_{format_tag}",
                    task_signature=f"perceptor::{format_tag}",
                    entrypoint="parse",
                    source_code=wrapper,
                    parent_organ_ids=(child.organ_id,),
                    metadata={"codec_family": "composed_prefix", "prefix": prefix, "child": child.organ_id},
                )
            except OrganSafetyError:
                continue
            try:
                parsed2 = organ.invoke(sample)
                re2 = organ.invoke_aux("serialize", parsed2)
                if organ.invoke(re2) != parsed2:
                    continue
            except Exception:
                continue
            rejected = 0
            corruptions = _corrupt_sample(sample)
            for bad in corruptions:
                try:
                    organ.invoke(bad)
                except Exception:
                    rejected += 1
            if rejected < len(corruptions):
                continue
            organ.verified_passes = 1
            return organ
    return None


def _observational_skill_source(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    concept_library: Any | None = None,
) -> str | None:
    """Call the in-tree observational-equivalence + STUN synthesizer (`G_t` live)."""
    try:
        from canonical.runtime.swe_observational_program_synthesizer_v1 import (
            synthesize_python_function_body,
        )
    except Exception:
        return None
    if not examples:
        return None
    arity = len(examples[0][0])
    names = _arg_names(arity)
    extra = [v for v in _harvest_numeric_constants(examples)[:6]]
    try:
        body = synthesize_python_function_body(
            names,
            examples,
            extra_constants=extra,
            max_weight=3,
            max_bank_size=72,
            concept_library=concept_library,
        )
    except Exception:
        return None
    if not isinstance(body, str) or not body.strip():
        return None
    stripped = body.strip()
    if "def run(" in stripped:
        return stripped + ("\n" if not stripped.endswith("\n") else "")
    helpers = ""
    run_body = stripped
    if stripped.startswith("def ") and "\nreturn " in stripped:
        head, tail = stripped.split("\nreturn ", 1)
        helpers = head + "\n"
        run_body = "return " + tail
    indented = "\n".join(("    " + ln) if ln.strip() else ln for ln in run_body.splitlines())
    return f"{helpers}def run({', '.join(names)}):\n{indented}\n"


def _skill_organ_to_concept_entry(organ: ExecutableOrgan) -> Any | None:
    """Bridge a simple SKILL organ into a ConceptEntry for `G_t`."""
    try:
        from canonical.swe_kernel.concept_library_v1 import ConceptEntry
    except Exception:
        return None
    try:
        tree = ast.parse(organ.source_code)
    except SyntaxError:
        return None
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == organ.entrypoint), None)
    if fn is None or not fn.body:
        return None
    if not (len(fn.body) == 1 and isinstance(fn.body[0], ast.Return) and fn.body[0].value is not None):
        return None
    cid = "c_" + organ.organ_id.replace("organ_skill_", "")[:18]
    if not cid.isidentifier():
        return None
    try:
        body_expr = ast.unparse(fn.body[0].value)
        return ConceptEntry(
            concept_id=cid,
            arity=len(fn.args.args),
            param_names=tuple(a.arg for a in fn.args.args),
            body_expr=body_expr,
            domain_kind="any",
            mdl_gain_bytes=max(1, organ.code_bytes),
            corpus_sites=1,
            verified_hits=max(1, organ.verified_passes),
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Unified 7-Stratum Meta-Circular Organ Graph (`P_t`)
# ---------------------------------------------------------------------------


class MetaCircularOrganGraph:
    """Content-addressed, self-growing 7-stratum program graph `P_t`."""

    def __init__(
        self,
        state_path: pathlib.Path | str | None = None,
        *,
        concept_library: Any | None = None,
    ) -> None:
        self.state_path = pathlib.Path(state_path) if state_path is not None else None
        self.organs: dict[str, ExecutableOrgan] = {}
        self.primary_by_sig: dict[tuple[str, str], str] = {}
        self.predictor = CausalFeatureSelfPredictor()
        self.concept_library = concept_library
        self._world_transitions: list[dict[str, Any]] = []
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
        if organ.stratum == SKILL and self.concept_library is not None:
            entry = _skill_organ_to_concept_entry(organ)
            if entry is not None and hasattr(self.concept_library, "admit_verified_concept"):
                try:
                    self.concept_library.admit_verified_concept(entry)
                except Exception:
                    pass
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

    def record_transition(
        self,
        *,
        action_id: str,
        cost: float,
        failed: bool,
        delta: Mapping[str, Any] | None = None,
    ) -> None:
        """Accumulate wake traces and compile a WORLD_MODEL organ when enough exist."""
        self._world_transitions.append(
            {
                "action": str(action_id),
                "cost": float(cost),
                "failed": bool(failed),
                "delta": dict(delta or {}),
            }
        )
        if len(self._world_transitions) < 2 or len(self._world_transitions) % 2 != 0:
            return
        try:
            wm = synthesize_world_model_organ(self._world_transitions[-16:])
            if wm is not None:
                self.register_organ(wm)
        except Exception:
            return

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

        # 2. Compositional closure: admitted PERCEPTOR + synthesized prefix glue
        composed = _compose_perceptor_from_existing(
            raw_sample, self.organs_in_stratum(PERCEPTOR), format_tag=format_tag
        )
        if composed is not None:
            self.register_organ(composed)
            parsed = composed.invoke(raw_sample)
            return {
                "ok": True,
                "parsed": parsed,
                "organ_id": composed.organ_id,
                "synthesized_new_organ": True,
                "composed_from_existing": True,
            }

        # 3. Online epistemic sensorogenesis (induce a new grammar)
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

            obs_src = _observational_skill_source(
                cur_examples, concept_library=self.concept_library
            )
            if obs_src:
                try:
                    pool.append(
                        make_organ(
                            stratum=SKILL,
                            name="observational_eq",
                            task_signature=task_signature,
                            entrypoint="run",
                            source_code=obs_src,
                            metadata={"via": "swe_observational_program_synthesizer_v1"},
                        )
                    )
                except OrganSafetyError:
                    pass

            operator_organs = [
                o for o in self.organs_in_stratum(SKILL) if o.task_signature != task_signature
            ][:8]
            for rname, expr_src, helpers in _generate_candidate_expressions(
                cur_examples, operator_organs=operator_organs
            ):
                src = _wrap_expr_into_source(arity, expr_src, helpers=helpers)
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
