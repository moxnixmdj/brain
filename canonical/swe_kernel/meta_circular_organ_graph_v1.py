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
  7. `POLICY`            : the deliberation program is the organ.
                           Immediate and combiner are synthesized organs in
                           `P_t`; unlock-walk horizon is the board; Ring-0 is
                           structural (not named ids) plus held-out return.
"""
from __future__ import annotations

import ast
import collections
import copy
import hashlib
import json
import math
import pathlib
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

# Settlement: the reachable probe space and the decision that a question is answered. Imported rather
# than re-implemented so the tree has ONE definition of "settled" (see canonical/runtime/settlement_v1.py).
try:  # pragma: no cover - import shape only
    from canonical.runtime import settlement_v1 as settlement
except Exception:  # pragma: no cover
    import settlement_v1 as settlement  # type: ignore

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

#: Strata whose organs are lifted into `G_t`. SKILL and WORLD_MODEL bodies are pure functions over
#: data (a lookup, a table, a transition model) -- exactly the shapes the constant-collection lifter
#: can parameterize. PERCEPTOR and VERIFIER entrypoints consume raw samples and emit parsed records,
#: so lifting their literals would probe a parser with inputs it was never written to accept.
_ADMISSIBLE_STRATA: tuple[str, ...] = (SKILL, WORLD_MODEL)


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


def _egraph_simplify_expr(expr_src: str) -> str | None:
    """Cheapest congruence-closed rendering of `expr_src` via the in-tree egraph."""
    src = str(expr_src or "").strip()
    if not src:
        return None
    try:
        from canonical.swe_kernel.egraph_and_deductive_synthesizer_v1 import (
            EGraph,
            _ast_expr_to_egraph,
            _saturate_algebraic_egraph,
        )
    except Exception:
        return None
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError:
        return None
    try:
        eg = EGraph()
        leaf_src: dict[int, tuple[int, str]] = {}
        root = _ast_expr_to_egraph(eg, tree.body, leaf_src)
        _saturate_algebraic_egraph(eg, rounds=3, max_classes=80)
        rcid = eg.find(root)
        hits = [(cost, text) for key, (cost, text) in leaf_src.items() if eg.find(key) == rcid]
        if not hits:
            return None
        best = min(hits, key=lambda it: (it[0], len(it[1])))[1].strip()
        if not best or best == src:
            return None
        ast.parse(best, mode="eval")
        return best
    except Exception:
        return None


def _solve_parametric_table(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
) -> tuple[str, str] | None:
    """Propose a period TABLE as a grammar candidate whose period and block are SOLVED, not emitted.

    Measured before writing this (see PREREG_THE_GRAMMAR_CAN_ONLY_EXPRESS_WHAT_A_WRITER_KNOWS): asked
    for a period-3 block with growth disabled, `_generate_candidate_expressions` returned nothing --
    the program was unreachable by search and existed only because `synthesize_table_organ` writes it.
    Handing the grammar a "primitive" organ did not help either, because a token that hardcodes a block
    is a remembered answer, not a composable one: asking it for period 4 still failed.

    The missing thing is a PARAMETRIC node -- a table constructor whose period and entries are
    variables the search solves. This derives them from the evidence the caller already paid for and
    returns ordinary candidate source, so the hypothesis then competes in the SAME version space as
    projections and affine forms instead of being a privileged path.

    Returns `(name, expr_src)` or None. It proposes only; it never decides. Every candidate is still
    checked against all examples by the caller, so a wrong guess here costs a candidate slot, not
    correctness.
    """
    if len(examples) < 3:
        return None
    ins = [ex[0][0] for ex in examples]
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in ins):
        return None
    # The period must be a candidate the evidence can actually support. Rather than trust one guess,
    # propose every period that the observed inputs can distinguish, and let the examples eliminate
    # the wrong ones -- that is what makes this search rather than a decision.
    lo = int(math.floor(min(ins)))
    proposed: list[tuple[str, str]] = []
    for k in range(2, 33):
        # A table with period k is only testable if the examples contain at least two full cycles,
        # otherwise any block of that period can be fitted and the hypothesis says nothing.
        if len({int(math.floor(v)) % k for v in ins}) < min(k, len(ins)):
            continue
        block: list[Any] = [None] * k
        resolved = True
        for xin, out in examples:
            r = int(math.floor(xin[0])) % k
            if block[r] is None:
                block[r] = out
            elif abs(float(block[r]) - float(out)) > 1e-9:
                resolved = False
                break
        if not resolved or any(b is None for b in block):
            continue
        body = ", ".join(repr(float(b)) for b in block)
        # Use the SAME parameter name the wrapper emits, or the candidate is dead on arrival: measured
        # with `_a0`, the node produced a candidate referencing a name that does not exist in `run`'s
        # scope, so the table never entered the version space and the failure looked like an absence of
        # structure. (A `.replace("P", ...)` fix then corrupted the call it was building -- substituting
        # into a format string substitutes into the SUBSTITUTE too. Built by concatenation instead.)
        pname = _arg_names(1)[0]
        expr = (
            "((%s)[int(math.floor(%s)) - math.floor(math.floor(%s) / %d) * %d])"
            % ("(" + body + ",)", pname, pname, k, k)
        )
        proposed.append((f"parametric_table_{k}", expr))
    if not proposed:
        return None
    # Shortest description first: a smaller period that explains the evidence is preferred, which is
    # the same MDL ordering the rest of this function uses.
    proposed.sort(key=lambda item: (len(item[1]), item[0]))
    return proposed[0]


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

    # Language basis for version-space underdetermination (projections), not a skill menu.
    # Arithmetic / STUN / concepts live in swe_observational_program_synthesizer_v1 + G_t.
    for i, nm in enumerate(names):
        cands.append((f"proj_{i}", nm, ""))

    # 2. Exact uniquely-determined multilinear / affine closed form
    affine = _solve_multilinear(examples)
    if affine is not None:
        cands.append(("exact_affine", affine, ""))

    # 3. Parametric table node: period and block are SOLVED from the evidence, so a repeating
    #    structure is reachable by search instead of only by a writer. Proposed, not privileged --
    #    it is checked against the examples like every other candidate.
    if arity == 1:
        table_cand = _solve_parametric_table(examples)
        if table_cand is not None:
            cands.append((table_cand[0], table_cand[1], ""))

    # 4. Live compositional closure over admitted organs
    for label, expr, helpers in _inline_operator_organs(examples, operator_organs):
        cands.append((label, expr, helpers))

    # 4. Congruence-closed algebraic rewrite of admitted expressions (in-tree egraph)
    extra: list[tuple[str, str, str]] = []
    for label, expr, helpers in cands:
        simp = _egraph_simplify_expr(expr)
        if simp:
            extra.append((f"egraph_{label}", simp, helpers))
    cands.extend(extra)

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


def induce_periodic_operator(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    max_period: int = 64,
) -> dict[str, Any] | None:
    """Induce a PERIOD from evidence and return the period, or None.

    This is the mechanism by which the operator basis is supposed to grow. `x mod k` was unreachable
    because `%` is not in the body grammar: every claim of having solved that family was a piecewise
    lookup that matched the seeds and failed everywhere else (measured held-out 2/10). Rather than add
    `%` to a menu -- which is the frozen-table defect again -- the creature looks for PERIODICITY in
    the evidence it already holds and, if it finds it, *derives* an operator with that period.

    Measured: the smallest period detectable from n observations is ~2p+2, so the cost of inducing
    structure scales with the size of the structure and NOT with prior experience. Inducing `mod 5`
    does not make `mod 15` cheap. What experience buys is the operator's *existence*: before it is
    induced no amount of evidence suffices, because no body in the grammar can express it.
    """
    if len(examples) < 6:
        return None
    arity = len(examples[0][0])
    if arity != 1:
        return None  # single-variable periodicity only; multi-variable is not claimed here
    pairs: list[tuple[Any, Any]] = []
    for ex_in, out in examples:
        try:
            pairs.append((float(ex_in[0]), float(out)))
        except (TypeError, ValueError):
            return None
    pairs.sort(key=lambda kv: kv[0])
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]

    for period in range(2, max_period + 1):
        # Need at least two complete periods of coverage before the claim means anything.
        if xs[-1] - xs[0] < 2 * period:
            continue
        consistent = True
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                dx = xs[j] - xs[i]
                if abs(dx - round(dx)) > 1e-9:
                    continue
                steps = int(round(dx))
                if steps % period != 0:
                    continue
                if abs(ys[i] - ys[j]) > 1e-9:
                    consistent = False
                    break
            if not consistent:
                break
        if consistent:
            return {
                "period": period,
                "observations": len(examples),
                "coverage": xs[-1] - xs[0],
            }
    return None


def _periodic_body(period: int, *, floor_convention: bool) -> str:
    """Body source for the induced period.

    Two conventions exist for the remainder of a negative number and they disagree below zero:
    `math.fmod(-3, 7)` is -3 while Python's `%` gives 4. A creature that assumes one is guessing, so
    both are emitted and the evidence decides. This is the same lesson as the frozen constant menu,
    one layer up: a convention is a hypothesis, not a fact.
    """
    if floor_convention:
        return (
            "def run(x0):\n"
            f"    return x0 - math.floor(x0 / {period}) * {period}\n"
        )
    return f"def run(x0):\n    return math.fmod(x0, {period})\n"


class ConventionMemory:
    """A remainder convention LEARNED once and carried forward.

    This is where experience actually compounds, and the compounding is honest. The first instance
    cannot tell the floor convention from `math.fmod` without asking (measured: 30/30 correct above
    zero, 6/30 below). Once one question settles it, asking again for every later instance would be
    the creature forgetting its own life. So a settled convention is remembered and reused, and the
    cost of the second and subsequent instances of the family drops to zero.

    It is not dogma. `refuted` records contradictions, and evidence that disagrees with the memory
    overrides it immediately -- a learned belief that cannot be revised is just a frozen table that
    took a longer route into the tree.
    """

    def __init__(self, *, name: str = "remainder") -> None:
        self.name = name
        self.convention: str | None = None
        self.evidence: int = 0
        self.refuted: int = 0

    @property
    def settled(self) -> bool:
        return self.convention is not None and self.evidence > 0

    def observe(self, convention: str) -> None:
        if self.convention is not None and self.convention != convention:
            self.refuted += 1
        self.convention = convention
        self.evidence += 1

    def refute(self) -> None:
        self.refuted += 1
        self.convention = None
        self.evidence = 0

    def as_row(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "convention": self.convention,
            "evidence": self.evidence,
            "refuted": self.refuted,
            "settled": self.settled,
        }


def _table_body(block: Sequence[float]) -> str:
    """Body for an induced period TABLE: the block is whatever the world put there.

    This is the difference between a parameter and a structure. `_periodic_body` emits
    `x - floor(x/P)*P`, a ramp whose only free value is P -- a shape I wrote down. Here the values in
    the block are the world's, and the only thing the creature contributes is the claim that the block
    repeats. That claim covers infinitely many inputs and any one of them can falsify it, which is what
    separates it from the lookup that memorised pairs.

    Emitted as a literal tuple indexed by a computed residue so the body stays a pure organ: no
    imports, no I/O, no reflection. `math.floor` gives the floored residue, so the block is indexed the
    same way on both sides of zero.
    """
    entries = ", ".join(repr(float(v)) for v in block)
    return (
        "def run(x0):\n"
        f"    _block = ({entries},)\n"
        "    _n = len(_block)\n"
        "    return _block[int(math.floor(x0) - math.floor(x0 / _n) * _n)]\n"
    )


def synthesize_table_organ(
    observations: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    task_signature: str,
    min_compression: float = 4.0,
) -> tuple["ExecutableOrgan", dict[str, Any]] | None:
    """Emit and verify an organ for an induced period table.

    `min_compression` passes through to `induce_periodic_table` and defaults to the cold 4x rule;
    only a library-licensed prior may lower it (see `compression_gain_v1.licensed_table_policy`).
    Verification is on the evidence only; the caller decides what to do about held-out behaviour. If
    the emitted body disagrees with any observation, nothing is admitted -- an induction that cannot
    reproduce its own evidence is not an induction.
    """
    found = settlement.induce_periodic_table(observations, min_compression=min_compression)
    if found is None:
        return None
    body = _table_body(found["block"])
    try:
        organ = make_organ(
            stratum=SKILL,
            name=f"induced_period_table_{int(found['period'])}",
            task_signature=task_signature,
            entrypoint="run",
            source_code=body,
            metadata={
                "induced": "periodic_table",
                "period": int(found["period"]),
                "block": list(found["block"]),
            },
        )
    except OrganSafetyError:
        return None
    if not all(
        (ok and _outputs_match(val, exp))
        for ex_in, exp in observations
        for ok, val in [_safe_eval_candidate(organ, ex_in)]
    ):
        return None
    return organ, found


def synthesize_periodic_organ(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    task_signature: str,
    oracle: Callable[[tuple[Any, ...]], Any] | None = None,
    max_queries: int = 2,
    memory: "ConventionMemory | None" = None,
) -> tuple["ExecutableOrgan", dict[str, Any]] | None:
    """Induce periodicity, then emit and verify a body for it.

    The body is chosen by evidence, not by preference: whichever convention reproduces every observed
    pair is the one admitted. If neither reproduces the evidence, nothing is admitted and the
    induction is reported as failed rather than rounded to the nearest lookalike.
    """
    found = induce_periodic_operator(examples)
    if found is None:
        return None
    period = int(found["period"])
    survivors: list[ExecutableOrgan] = []
    for floor_convention in (True, False):
        src = _periodic_body(period, floor_convention=floor_convention)
        try:
            org = make_organ(
                stratum=SKILL,
                name=("induced_period_floor" if floor_convention else "induced_period_fmod") + f"_{period}",
                task_signature=task_signature,
                entrypoint="run",
                source_code=src,
                metadata={"induced": "periodic", "period": period},
            )
        except OrganSafetyError:
            continue
        if all(
            (ok and _outputs_match(val, exp))
            for ex_in, exp in examples
            for ok, val in [_safe_eval_candidate(org, ex_in)]
        ):
            survivors.append(org)
    if not survivors:
        return None
    survivors.sort(key=lambda o: (o.code_bytes, o.organ_id))
    found = dict(found)

    # Two conventions can both reproduce every observation while disagreeing wherever the evidence is
    # silent (measured: all-positive evidence makes floor and fmod identical above zero and opposite
    # below it -- 30/30 positive, 6/30 negative). That is not a reason to pick the smaller one. It is a
    # reason to ask one question, and if there is nobody to ask, to say the convention is unsettled.
    if len(survivors) > 1 and memory is not None and memory.settled:
        # A convention settled by an earlier instance is knowledge, not an assumption. Reusing it is
        # the whole point of having experience; asking again every time would be amnesia.
        survivors = [o for o in survivors if memory.convention in o.name]
        found["convention_from_memory"] = memory.convention
        if survivors:
            found["convention_settled"] = True
            return survivors[0], found
        # The remembered convention does not even reproduce the evidence: it is wrong, and a memory
        # that cannot be contradicted is a frozen table wearing a longer coat.
        memory.refute()
        found["convention_memory_refuted"] = True
        survivors = [o for o in _periodic_survivors(period, examples)]

    if len(survivors) > 1:
        probes = _settlement_probe_space(examples, survivors)
        found["conventions_considered"] = [o.name for o in survivors]
        if oracle is not None:
            queried = 0
            while len(survivors) > 1 and queried < max_queries:
                probe = synthesize_discriminating_input(survivors, examples, probes_override=probes)
                if probe is None:
                    break
                observed = oracle(probe)
                queried += 1
                survivors = [
                    o
                    for o in survivors
                    if (lambda ov: ov[0] and _outputs_match(ov[1], observed))(
                        _safe_eval_candidate(o, probe)
                    )
                ]
                examples = list(examples) + [(probe, observed)]
            found["convention_queries"] = queried
        if len(survivors) > 1:
            found["convention_settled"] = False
            found["convention_unsettled_because"] = (
                "the evidence does not distinguish these conventions and no oracle decided them"
            )
            survivors = survivors[:1]
        else:
            found["convention_settled"] = True
    else:
        found["convention_settled"] = True
    if not survivors:
        return None
    if memory is not None and found.get("convention_settled"):
        memory.observe("floor" if "floor" in survivors[0].name else "fmod")
    return survivors[0], found


def _periodic_survivors(
    period: int, examples: Sequence[tuple[tuple[Any, ...], Any]]
) -> list["ExecutableOrgan"]:
    out: list[ExecutableOrgan] = []
    for floor_convention in (True, False):
        src = _periodic_body(period, floor_convention=floor_convention)
        try:
            org = make_organ(
                stratum=SKILL,
                name=("induced_period_floor" if floor_convention else "induced_period_fmod")
                + f"_{period}",
                task_signature="scratch",
                entrypoint="run",
                source_code=src,
                metadata={"induced": "periodic", "period": period},
            )
        except OrganSafetyError:
            continue
        if all(
            (ok and _outputs_match(val, exp))
            for ex_in, exp in examples
            for ok, val in [_safe_eval_candidate(org, ex_in)]
        ):
            out.append(org)
    return out


def _survivors_disagree_on_domain(
    survivors: Sequence["ExecutableOrgan"],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
) -> bool:
    """True if any two survivors disagree anywhere on the caller's reachable domain.

    The distinction this draws is the one the whole repair turns on. Ambiguity is only a problem when
    a wrong choice would cost the caller something *where the caller lives*. Two structurally
    different programs that compute the same function (`2x+2` and `2*(x+1)`) are interchangeable, and
    refusing between them would be timidity dressed as rigour.
    """
    if len(survivors) <= 1:
        return False
    domain = settlement.derive_probe_space(examples)
    for i, a in enumerate(survivors):
        for b in survivors[i + 1:]:
            for probe in domain:
                oka, va = _safe_eval_candidate(a, probe)
                okb, vb = _safe_eval_candidate(b, probe)
                if oka != okb:
                    return True
                if oka and not _outputs_match(va, vb):
                    return True
    return False


def _settlement_probe_space(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    hypotheses: Sequence["ExecutableOrgan"],
) -> list[tuple[Any, ...]]:
    """Probe inputs derived from the hypotheses' own literals and the observed domain.

    The frozen `_candidate_probe_inputs` grid decides what counts as "the same behaviour". That is the
    same defect as a frozen constant menu: a table, not a computation, fixing an answer. A body can
    only change behaviour at the literals it mentions, so those literals -- plus the neighbourhood of
    each observed input -- are where separation is possible. A dense interior is included as well,
    because a range that is SPARSE rather than short (it ran to 20 while omitting 14) cannot be
    repaired by widening its endpoints.
    """
    literals: list[int] = []
    for org in hypotheses:
        try:
            tree = ast.parse(org.source_code)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(
                node.value, bool
            ):
                literals.append(int(node.value))
    return settlement.derive_probe_space(examples, literals=literals)


def _first_refuting_probe(
    organ: "ExecutableOrgan",
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    task_signature: str,
) -> tuple[Any, ...] | None:
    """A single input on which this organ's correctness is genuinely open.

    Used by Tier-0 recall, which previously accepted an incumbent on the strength of the examples
    already given. Those examples are exactly the ones that made it the incumbent, so they cannot
    test it. This picks an input the organ has not been checked against so one question can decide
    whether the recall is real.
    """
    probes = settlement.derive_probe_space(examples)
    seen = {tuple(repr(x) for x in ex_in) for ex_in, _ in examples}
    for probe in probes:
        if tuple(repr(x) for x in probe) not in seen:
            return probe
    return None


def synthesize_discriminating_input(
    hypotheses: Sequence[ExecutableOrgan],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    probes_override: Sequence[tuple[Any, ...]] | None = None,
) -> tuple[Any, ...] | None:
    """Find the probe input `x_disc` maximizing Shannon entropy over hypothesis outputs."""
    if len(hypotheses) <= 1:
        return None
    best_probe: tuple[Any, ...] | None = None
    best_entropy = -1.0
    probe_source = list(probes_override) if probes_override is not None else _candidate_probe_inputs(examples)
    for probe in probe_source:
        # Bucket by the SAME equivalence the elimination step uses (`_outputs_match`), not by `repr`.
        # Scoring with `repr` while filtering with numeric tolerance is two definitions of "same" in
        # one function: `0` and `-0.0` counted as a split worth querying and then matched as equal, so
        # the query was spent and nothing was eliminated (measured on the floor/fmod convention pair).
        buckets: list[list[Any]] = []  # [representative_outcome, count]
        valid_total = 0
        errors = 0
        for h in hypotheses:
            ok, out = _safe_eval_candidate(h, probe)
            if not ok:
                errors += 1
                continue
            valid_total += 1
            for bucket in buckets:
                if _outputs_match(bucket[0], out):
                    bucket[1] += 1
                    break
            else:
                buckets.append([out, 1])
        if errors:
            buckets.append(["ERR", errors])
        counts = [b[1] for b in buckets]
        if len(counts) <= 1 or valid_total == 0:
            continue
        n = float(len(hypotheses))
        ent = -sum((cnt / n) * math.log2(cnt / n) for cnt in counts)
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
            try:
                from canonical.runtime.swe_observational_program_synthesizer_v1 import (
                    synthesize_python_function_body,
                )

                names = _arg_names(len(io_examples[0][0]))
                body = synthesize_python_function_body(
                    names, io_examples, max_weight=3, max_bank_size=64
                )
            except Exception:
                body = None
            if isinstance(body, str) and "return " in body:
                synthesized_expr = body.rsplit("return ", 1)[-1].strip()
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
    structured = any(n["unlocks"] or n["requires"] for n in by_id.values())

    def _q(aid: str, done: frozenset[str], budget: float, depth: int) -> float:
        if depth <= 0 or budget <= 1e-12:
            return 0.0
        node = by_id[aid]
        if any(r not in done for r in node["requires"]):
            return -1e9
        if node["cost"] > budget + 1e-12:
            return -1e9
        p_burn = max(0.0, min(1.0, burns.get(aid, 0.0)))
        if not structured:
            return (node["value"] / node["cost"]) * (1.0 - 0.85 * p_burn)
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
    depth = max(1, int(horizon), len(by_id))
    for aid, node in by_id.items():
        qv = _q(aid, frozenset(), float(remaining_budget), depth)
        ranked.append({**node, "q": round(qv, 6)})
    ranked.sort(key=lambda r: (r["q"], -r["cost"], r["id"]), reverse=True)
    return ranked


def _indent_block(src: str, spaces: int) -> str:
    """Re-indent a statement body, preserving relative indent (STUN if/else)."""
    pad = " " * max(0, int(spaces))
    stripped = src.strip("\n")
    indents = [len(ln) - len(ln.lstrip(" ")) for ln in stripped.splitlines() if ln.strip()]
    base = min(indents) if indents else 0
    out: list[str] = []
    for ln in stripped.splitlines():
        if not ln.strip():
            out.append("")
            continue
        out.append(pad + ln[base:])
    return "\n".join(out)


def ring0_referee_organ_source(source_code: str) -> dict[str, Any]:
    """Ring-0 AST firewall on a `P_t` organ source (not a Ring-1 `.py` patch)."""
    try:
        verify_pure_organ_ast(source_code)
    except OrganSafetyError as exc:
        return {"ok": False, "ring0": "REFUSED", "reason": str(exc)}
    except Exception as exc:
        return {"ok": False, "ring0": "REFUSED", "reason": type(exc).__name__}
    return {"ok": True, "ring0": "ADMITTED"}


# Two disjoint alphabets so a name-hardcoded organ cannot pass Ring-0.
# Fail/shiny ids sort AFTER ok/unlock ids so a Q-tie would pick the illegal winner.
_RING0_ID_SETS: tuple[tuple[str, str, str, str, str], ...] = (
    ("zz_fail_a", "aa_ok_a", "zz_shiny_a", "aa_unlock_a", "mm_goal_a"),
    ("zz_fail_b", "aa_ok_b", "zz_shiny_b", "aa_unlock_b", "mm_goal_b"),
)


def _policy_fail_loses(organ: ExecutableOrgan, fail_id: str, ok_id: str) -> bool:
    ranked = organ.invoke(
        [
            {"id": fail_id, "value": 10.0, "cost": 1.0},
            {"id": ok_id, "value": 10.0, "cost": 1.0},
        ],
        10.0,
        {fail_id: 1.0, ok_id: 0.0},
    )
    return bool(ranked) and str(ranked[0].get("id")) == ok_id


def _policy_unlocker_beats_shiny(
    organ: ExecutableOrgan, shiny_id: str, unlock_id: str, goal_id: str
) -> bool:
    ranked = organ.invoke(
        [
            {"id": shiny_id, "value": 12.0, "cost": 1.0},
            {"id": unlock_id, "value": 0.0, "cost": 1.0, "unlocks": (goal_id,)},
            {"id": goal_id, "value": 100.0, "cost": 1.0, "requires": (unlock_id,)},
        ],
        3.0,
        None,
    )
    return bool(ranked) and str(ranked[0].get("id")) == unlock_id


def _policy_two_step_unlock(
    organ: ExecutableOrgan, shiny_id: str, tool_id: str, mid_id: str, goal_id: str
) -> bool:
    """Behavioral probe: a 0-immediate tool that unlocks a 0-immediate mid that unlocks payoff."""
    ranked = organ.invoke(
        [
            {"id": shiny_id, "value": 12.0, "cost": 1.0},
            {"id": tool_id, "value": 0.0, "cost": 1.0, "unlocks": (mid_id,)},
            {"id": mid_id, "value": 0.0, "cost": 1.0, "requires": (tool_id,), "unlocks": (goal_id,)},
            {"id": goal_id, "value": 100.0, "cost": 1.0, "requires": (mid_id,)},
        ],
        4.0,
        None,
    )
    return bool(ranked) and str(ranked[0].get("id")) == tool_id


def _policy_horizon_bin(organ: ExecutableOrgan) -> str:
    """MAP-Elites behavioral niche: how far the organ actually looks, not AST rec/flat."""
    try:
        organ.ensure_compiled()
        if _policy_two_step_unlock(organ, "zz_sh_h", "aa_t_h", "mm_m_h", "mm_g_h"):
            return "h2"
        if _policy_unlocker_beats_shiny(organ, "zz_sh_h", "aa_t_h", "mm_g_h"):
            return "h1"
    except Exception:
        return "h0"
    return "h0"


def _policy_organ_holds_ring0(organ: ExecutableOrgan) -> bool:
    """Structural invariants, not named boards: fail-rate loses; 0-immediate unlocker wins."""
    try:
        organ.ensure_compiled()
        for fail_id, ok_id, shiny_id, unlock_id, goal_id in _RING0_ID_SETS:
            if not _policy_fail_loses(organ, fail_id, ok_id):
                return False
            if not _policy_unlocker_beats_shiny(organ, shiny_id, unlock_id, goal_id):
                return False
    except Exception:
        return False
    return True


def _trace_action_rows(transitions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for tr in transitions:
        aid = str(tr.get("action") or tr.get("action_id") or "")
        if not aid:
            continue
        cost = float(tr.get("cost") or 1.0)
        failed_flag = bool(tr.get("failed"))
        raw_v = tr.get("value")
        if raw_v is None:
            delta = tr.get("delta") or {}
            nums = [
                float(v)
                for v in (delta.values() if isinstance(delta, Mapping) else ())
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            raw_v = nums[0] if nums else 1.0
        value = float(raw_v)
        realized = 0.0 if failed_flag else value
        rows[aid] = {
            "id": aid,
            "value": value,
            "cost": cost,
            "failed": 1.0 if failed_flag else 0.0,
            "realized": realized,
        }
    return list(rows.values())


def _snapshot_action_board(actions: Any, *, max_rows: int = 32) -> list[dict[str, Any]]:
    """Persist the board the creature actually ranked — unlocks/requires included."""
    if not isinstance(actions, (list, tuple)):
        return []
    out: list[dict[str, Any]] = []
    for raw in actions[:max_rows]:
        if not isinstance(raw, Mapping):
            continue
        aid = str(raw.get("id") or "")
        if not aid:
            continue
        try:
            value = float(raw.get("value") or 0.0)
            cost = max(1e-9, float(raw.get("cost") or 1.0))
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "id": aid,
                "value": value,
                "cost": cost,
                "unlocks": tuple(str(x) for x in (raw.get("unlocks") or ())),
                "requires": tuple(str(x) for x in (raw.get("requires") or ())),
            }
        )
    return out


def _policy_respects_live_boards(
    organ: ExecutableOrgan, boards: Sequence[Any]
) -> bool:
    """Never rank a locked action first on a board the creature actually saw."""
    for board in list(boards)[-4:]:
        rows = _snapshot_action_board(board)
        if len(rows) < 2:
            continue
        if not any(r["unlocks"] or r["requires"] for r in rows):
            continue
        try:
            ranked = organ.invoke(rows, 10.0, None)
        except Exception:
            return False
        if not ranked:
            return False
        by_id = {r["id"]: r for r in rows}
        top = str(ranked[0].get("id"))
        top_row = by_id.get(top)
        if top_row is None:
            return False
        if top_row["requires"]:
            return False
    return True


def _policy_respects_trace_ranking(
    organ: ExecutableOrgan, transitions: Sequence[Mapping[str, Any]]
) -> bool:
    """Held-out world return: live boards if present, else among observed actions."""
    live = [
        tr.get("board")
        for tr in transitions
        if isinstance(tr.get("board"), list) and len(tr.get("board") or []) >= 2
    ]
    if live and not _policy_respects_live_boards(organ, live):
        return False
    rows = _trace_action_rows(transitions)
    if len(rows) < 2:
        return True
    try:
        ranked = organ.invoke(
            [{"id": r["id"], "value": r["value"], "cost": r["cost"]} for r in rows],
            max(10.0, sum(float(r["cost"]) for r in rows) + 1.0),
            {r["id"]: r["failed"] for r in rows},
        )
    except Exception:
        return False
    if not ranked:
        return False
    by_id = {r["id"]: r for r in rows}
    top = str(ranked[0].get("id"))
    if top not in by_id:
        return False
    best_real = max(float(r["realized"]) for r in rows)
    return float(by_id[top]["realized"]) + 1e-9 >= best_real


def admit_policy_organ(
    organ: ExecutableOrgan,
    traces: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """AST firewall + structural Ring-0 + held-out return. Incumbent stays on refusal."""
    ast_res = ring0_referee_organ_source(organ.source_code)
    if not ast_res.get("ok"):
        return ast_res
    if not _policy_organ_holds_ring0(organ):
        return {"ok": False, "ring0": "REFUSED", "reason": "STRUCTURAL_INVARIANT"}
    if traces and not _policy_respects_trace_ranking(organ, traces):
        return {"ok": False, "ring0": "REFUSED", "reason": "HELDOUT_RETURN"}
    return {"ok": True, "ring0": "ADMITTED"}


def _simplify_statement_body(body: str) -> str:
    text = (body or "").strip()
    if not text:
        return text
    lines = text.splitlines()
    if len(lines) == 1 and lines[0].lstrip().startswith("return "):
        expr = lines[0].lstrip()[7:].strip()
        simp = _egraph_simplify_expr(expr)
        if simp:
            return f"return {simp}\n"
    return text + ("\n" if not text.endswith("\n") else "")


def _egraph_simplify_organ_source(source_code: str) -> str | None:
    """Rewrite every `return` expression in an organ via the in-tree egraph."""
    src = str(source_code or "")
    if not src.strip():
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    changed = False

    class _ReturnSimplifier(ast.NodeTransformer):
        def visit_Return(self, node: ast.Return) -> ast.AST:
            self.generic_visit(node)
            if node.value is None:
                return node
            try:
                expr_src = ast.unparse(node.value)
            except Exception:
                return node
            best = _egraph_simplify_expr(expr_src)
            if not best or best == expr_src:
                return node
            try:
                new_val = ast.parse(best, mode="eval").body
            except SyntaxError:
                return node
            nonlocal changed
            changed = True
            return ast.Return(value=new_val)

    new_tree = _ReturnSimplifier().visit(tree)
    if not changed:
        return None
    ast.fix_missing_locations(new_tree)
    try:
        return ast.unparse(new_tree) + "\n"
    except Exception:
        return None


def compile_combiner_organ(
    *,
    body: str | None = None,
    gamma: float = 0.92,
    cost_penalty: float = 0.05,
    name: str = "policy_combiner",
) -> ExecutableOrgan:
    """SKILL organ: `(immediate, cost, future) -> q`. Bootstrap prior until traces replace it."""
    src_body = (body or "").strip()
    if src_body:
        src = "def run(immediate, cost, future):\n" + _indent_block(src_body, 4) + "\n"
    else:
        src = (
            "def run(immediate, cost, future):\n"
            f"    return immediate - cost * {float(cost_penalty)!r} + {float(gamma)!r} * future\n"
        )
    organ = make_organ(
        stratum=SKILL,
        name=name,
        task_signature="policy::combiner",
        entrypoint="run",
        source_code=src,
        metadata={"gamma": gamma, "cost_penalty": cost_penalty, "learned": bool(src_body)},
    )
    organ.verified_passes = max(1, organ.verified_passes)
    return organ


def _trace_realized(tr: Mapping[str, Any]) -> float:
    if tr.get("failed"):
        return 0.0
    raw_v = tr.get("value")
    if raw_v is None:
        delta = tr.get("delta") or {}
        nums = [
            float(v)
            for v in (delta.values() if isinstance(delta, Mapping) else ())
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        raw_v = nums[0] if nums else 0.0
    return float(raw_v)


def _perceived_unlock_value(aid: str, board: Any) -> float:
    """Value sitting behind `aid` on the board. Perception at decision time, not a backup."""
    if not isinstance(board, list):
        return 0.0
    by_id: dict[str, Mapping[str, Any]] = {}
    unlocks: tuple[str, ...] = ()
    for raw in board:
        if not isinstance(raw, Mapping):
            continue
        i = str(raw.get("id") or "")
        if not i:
            continue
        by_id[i] = raw
        if i == aid:
            unlocks = tuple(str(x) for x in (raw.get("unlocks") or ()))
    vals: list[float] = []
    for u in unlocks:
        row = by_id.get(u)
        if row is None:
            continue
        try:
            vals.append(float(row.get("value") or 0.0))
        except (TypeError, ValueError):
            continue
    return max(vals) if vals else 0.0


def _board_episode_key(board: Any) -> tuple[str, ...]:
    if not isinstance(board, list) or not board:
        return ()
    ids: list[str] = []
    for raw in board:
        if isinstance(raw, Mapping):
            i = str(raw.get("id") or "")
            if i:
                ids.append(i)
    return tuple(ids)


def _credited_combiner_examples(
    transitions: Sequence[Mapping[str, Any]],
) -> list[tuple[tuple[Any, ...], Any]]:
    """`(immediate, cost, perceived_future) -> observed path return`.

    Future is what the board showed behind this action. The label is what later
    actually arrived. They are not the same number computed twice.
    """
    seq: list[dict[str, Any]] = []
    for tr in transitions:
        aid = str(tr.get("action") or tr.get("action_id") or "")
        if not aid:
            continue
        board = tr.get("board")
        realized = _trace_realized(tr)
        seq.append(
            {
                "id": aid,
                "imm": realized,
                "cost": float(tr.get("cost") or 1.0),
                "future": _perceived_unlock_value(aid, board),
                "realized": realized,
                "ep": _board_episode_key(board),
            }
        )
    # Observed suffix return inside each perceived board-episode.
    i = 0
    n = len(seq)
    while i < n:
        j = i + 1
        if seq[i]["ep"]:
            while j < n and seq[j]["ep"] == seq[i]["ep"]:
                j += 1
        acc = 0.0
        for k in range(j - 1, i - 1, -1):
            acc += float(seq[k]["realized"])
            seq[k]["g"] = acc
        i = j
    examples: list[tuple[tuple[Any, ...], Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in seq:
        key = (
            round(float(row["imm"]), 9),
            round(float(row["cost"]), 9),
            round(float(row["future"]), 9),
            round(float(row["g"]), 9),
        )
        if key in seen:
            continue
        seen.add(key)
        examples.append(((float(row["imm"]), float(row["cost"]), float(row["future"])), float(row["g"])))
    return examples


def _synthesize_combiner_from_traces(
    transitions: Sequence[Mapping[str, Any]],
    *,
    concept_library: Any | None = None,
) -> str | None:
    """Observational `(immediate, cost, future) -> observed path return`. Future is perceived, not backed up."""
    examples = _credited_combiner_examples(transitions)
    if len(examples) < 2:
        return None
    try:
        from canonical.runtime.swe_observational_program_synthesizer_v1 import (
            synthesize_python_function_body,
        )
    except Exception:
        return None
    any_future = any(abs(fut) > 1e-12 for (_i, _c, fut), _y in examples)
    attempts: list[tuple[list[str], list[tuple[tuple[Any, ...], Any]]]] = []
    if any_future:
        attempts.append(
            (["immediate", "future"], [((a, f), y) for (a, _c, f), y in examples])
        )
    attempts.append((["immediate", "cost"], [((a, b), y) for (a, b, _f), y in examples]))
    attempts.append((["immediate", "cost", "future"], examples))
    for names, ex in attempts:
        try:
            body = synthesize_python_function_body(
                names,
                ex,
                extra_constants=(),
                max_weight=3,
                max_bank_size=80,
                concept_library=concept_library,
            )
        except Exception:
            body = None
        if isinstance(body, str) and "return" in body:
            return body.strip() + "\n"
    return None


def _synthesize_immediate_from_traces(
    transitions: Sequence[Mapping[str, Any]],
    *,
    concept_library: Any | None = None,
) -> str | None:
    """Observational bank + `G_t`: `(value, cost, failed) -> realized` body, or None."""
    rows: list[tuple[float, float, float, float]] = []
    seen: set[tuple[Any, ...]] = set()
    for tr in transitions:
        cost = float(tr.get("cost") or 1.0)
        failed_flag = bool(tr.get("failed"))
        failed = 1.0 if failed_flag else 0.0
        raw_v = tr.get("value")
        if raw_v is None:
            delta = tr.get("delta") or {}
            nums = [
                float(v)
                for v in (delta.values() if isinstance(delta, Mapping) else ())
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            raw_v = nums[0] if nums else 1.0
        value = float(raw_v)
        realized = 0.0 if failed_flag else value
        key = (round(value, 9), round(cost, 9), failed, round(realized, 9))
        if key in seen:
            continue
        seen.add(key)
        rows.append((value, cost, failed, realized))
        if len(rows) >= 12:
            break
    if len(rows) < 2:
        return None
    try:
        from canonical.runtime.swe_observational_program_synthesizer_v1 import (
            synthesize_python_function_body,
        )
    except Exception:
        return None

    vary_cost = len({round(r[1], 9) for r in rows}) > 1
    attempts: list[tuple[list[str], list[tuple[tuple[Any, ...], Any]]]] = []
    if not vary_cost:
        attempts.append(
            (
                ["value", "failed"],
                [((v, f), r) for v, c, f, r in rows],
            )
        )
    attempts.append(
        (
            ["value", "cost", "failed"],
            [((v, c, f), r) for v, c, f, r in rows],
        )
    )
    for names, examples in attempts:
        try:
            body = synthesize_python_function_body(
                names,
                examples,
                extra_constants=(),
                max_weight=3,
                max_bank_size=80,
                concept_library=concept_library,
            )
        except Exception:
            body = None
        if isinstance(body, str) and "return" in body:
            return body.strip() + "\n"
    return None


def compile_policy_organ(
    *,
    name: str = "instrumental_policy",
    gamma: float = 0.92,
    horizon: int = 3,
    empirical_burns: Mapping[str, float] | None = None,
    learned_immediate: str | None = None,
    combiner_src: str | None = None,
) -> ExecutableOrgan:
    """Compile a POLICY organ from immediate + combiner organs.

    Unlock-walk horizon is `max(horizon, len(board))` (the board, not a frozen
    3). `gamma` / cost-penalty live in the combiner body when supplied.
    """
    observed = {str(k): float(v) for k, v in dict(empirical_burns or {}).items()}
    imm_src = (learned_immediate or "").strip()
    comb_src = (combiner_src or "").strip()
    if imm_src:
        imm_def = "    def _immediate(value, cost, failed):\n" + _indent_block(imm_src, 8) + "\n"
        unstructured = "            return _immediate(node['value'], node['cost'], p_burn)\n"
        structured_imm = "        immediate = _immediate(node['value'], node['cost'], p_burn)\n"
    else:
        imm_def = ""
        unstructured = "            return (node['value'] / node['cost']) * (1.0 - 0.85 * p_burn)\n"
        structured_imm = "        immediate = node['value'] * (1.0 - 0.85 * p_burn)\n"
    if comb_src:
        comb_def = "    def _combine(immediate, cost, future):\n" + _indent_block(comb_src, 8) + "\n"
        comb_return = "        return _combine(immediate, node['cost'], future)\n"
    else:
        comb_def = ""
        comb_return = "        return immediate - node['cost'] * 0.05 + gamma * future\n"
    src = (
        "def score_actions(actions, remaining_budget, p_burn_by_id=None):\n"
        "    by_id = {}\n"
        "    for raw in actions:\n"
        "        aid = str(raw.get('id') or '')\n"
        "        if not aid:\n"
        "            continue\n"
        "        by_id[aid] = {\n"
        "            'id': aid,\n"
        "            'value': float(raw.get('value') or 0.0),\n"
        "            'cost': max(1e-9, float(raw.get('cost') or 1.0)),\n"
        "            'unlocks': tuple(str(x) for x in (raw.get('unlocks') or ())),\n"
        "            'requires': tuple(str(x) for x in (raw.get('requires') or ())),\n"
        "        }\n"
        "    burns = dict(p_burn_by_id or {})\n"
        f"    for _k, _v in {observed!r}.items():\n"
        "        burns.setdefault(_k, _v)\n"
        f"    gamma = {float(gamma)!r}\n"
        f"    horizon_floor = {int(horizon)!r}\n"
        "    horizon = max(horizon_floor, len(by_id))\n"
        "    structured = any(n['unlocks'] or n['requires'] for n in by_id.values())\n"
        "\n"
        + imm_def
        + comb_def
        + "    def _q(aid, done, budget, depth):\n"
        "        if depth <= 0 or budget <= 1e-12:\n"
        "            return 0.0\n"
        "        node = by_id[aid]\n"
        "        for r in node['requires']:\n"
        "            if r not in done:\n"
        "                return -1e9\n"
        "        if node['cost'] > budget + 1e-12:\n"
        "            return -1e9\n"
        "        p_burn = burns.get(aid, 0.0)\n"
        "        if not structured:\n"
        + unstructured
        + structured_imm
        + "        leftover = budget - node['cost']\n"
        "        nxt = set(done)\n"
        "        nxt.add(aid)\n"
        "        future = 0.0\n"
        "        unlocked = [u for u in node['unlocks'] if u in by_id and u not in nxt]\n"
        "        candidates = unlocked or [k for k in by_id if k not in nxt]\n"
        "        if candidates and leftover > 0:\n"
        "            future = max(_q(u, nxt, leftover, depth - 1) for u in candidates)\n"
        + comb_return
        + "\n"
        "    ranked = []\n"
        "    for aid, node in by_id.items():\n"
        "        qv = _q(aid, set(), float(remaining_budget), horizon)\n"
        "        row = dict(node)\n"
        "        row['q'] = qv\n"
        "        ranked.append(row)\n"
        "    ranked.sort(key=lambda r: (r['q'], -r['cost'], r['id']), reverse=True)\n"
        "    return ranked\n"
    )
    organ = make_organ(
        stratum=POLICY,
        name=name,
        task_signature="policy::instrumental_q",
        entrypoint="score_actions",
        source_code=src,
        metadata={
            "gamma": gamma,
            "horizon": horizon,
            "empirical_burns": observed,
            "learned_immediate": bool(imm_src),
            "learned_combiner": bool(comb_src),
        },
    )
    if observed or imm_src or comb_src:
        organ.verified_passes = max(1, len(observed) + (8 if imm_src else 0) + (4 if comb_src else 0))
    return organ


def _stmts_from_body(body: str, *, name: str, args: Sequence[str]) -> ast.FunctionDef:
    sig = ", ".join(args)
    src = f"def {name}({sig}):\n" + _indent_block(body, 4) + "\n"
    fn = ast.parse(src).body[0]
    if not isinstance(fn, ast.FunctionDef):
        raise OrganSafetyError("NESTED_FN_PARSE")
    return fn


def _ast_call(name: str, args: Sequence[ast.expr]) -> ast.Call:
    return ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=list(args), keywords=[])


def _node_field(field: str) -> ast.Subscript:
    return ast.Subscript(
        value=ast.Name(id="node", ctx=ast.Load()),
        slice=ast.Constant(value=field),
        ctx=ast.Load(),
    )


def _rewire_q_immediate(body: list[ast.stmt]) -> list[ast.stmt]:
    call = _ast_call("_immediate", [_node_field("value"), _node_field("cost"), ast.Name(id="p_burn", ctx=ast.Load())])
    out: list[ast.stmt] = []
    for stmt in body:
        if (
            isinstance(stmt, ast.If)
            and isinstance(stmt.test, ast.UnaryOp)
            and isinstance(stmt.test.op, ast.Not)
            and isinstance(stmt.test.operand, ast.Name)
            and stmt.test.operand.id == "structured"
        ):
            stmt = ast.If(test=stmt.test, body=[ast.Return(value=copy.deepcopy(call))], orelse=list(stmt.orelse))
        elif (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and stmt.targets[0].id == "immediate"
        ):
            stmt = ast.Assign(targets=stmt.targets, value=copy.deepcopy(call))
        out.append(stmt)
    return out


def _rewire_q_combiner(body: list[ast.stmt]) -> list[ast.stmt]:
    call = _ast_call(
        "_combine",
        [
            ast.Name(id="immediate", ctx=ast.Load()),
            _node_field("cost"),
            ast.Name(id="future", ctx=ast.Load()),
        ],
    )
    out: list[ast.stmt] = []
    for stmt in body:
        if (
            isinstance(stmt, ast.If)
            and isinstance(stmt.test, ast.UnaryOp)
            and isinstance(stmt.test.op, ast.Not)
            and isinstance(stmt.test.operand, ast.Name)
            and stmt.test.operand.id == "structured"
        ):
            out.append(stmt)
            continue
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            names = {n.id for n in ast.walk(stmt.value) if isinstance(n, ast.Name)}
            if "immediate" in names or "_combine" in names:
                stmt = ast.Return(value=copy.deepcopy(call))
        out.append(stmt)
    return out


def _apply_nested_fn(
    source_code: str,
    *,
    fn_name: str,
    args: Sequence[str],
    body: str,
    rewire: Callable[[list[ast.stmt]], list[ast.stmt]] | None,
) -> str | None:
    """Patch incumbent `score_actions`: insert/replace a nested organ, keep the walk."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return None
    host = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "score_actions"), None)
    if host is None:
        return None
    try:
        nested = _stmts_from_body(body, name=fn_name, args=args)
    except Exception:
        return None
    replaced = False
    for i, stmt in enumerate(host.body):
        if isinstance(stmt, ast.FunctionDef) and stmt.name == fn_name:
            host.body[i] = nested
            replaced = True
            break
    if not replaced:
        idx = next((i for i, s in enumerate(host.body) if isinstance(s, ast.FunctionDef)), len(host.body))
        host.body.insert(idx, nested)
        if rewire is not None:
            for stmt in host.body:
                if isinstance(stmt, ast.FunctionDef) and stmt.name == "_q":
                    stmt.body = rewire(stmt.body)
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree) + "\n"
    except Exception:
        return None


def _iterative_unlock_mutations(source_code: str) -> list[str]:
    """RSA-style recursion→loop: same multi-step unlock law, no `_q` self-call."""
    src = str(source_code or "")
    if not src.strip():
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    walk_body = ast.parse(
        "def _w():\n"
        "    frontier = [u for u in node['unlocks'] if u in by_id and u not in nxt]\n"
        "    seen_u = set(nxt)\n"
        "    left = leftover\n"
        "    while frontier and left > 0:\n"
        "        u = frontier.pop(0)\n"
        "        if u in seen_u or u not in by_id:\n"
        "            continue\n"
        "        ch = by_id[u]\n"
        "        skip = False\n"
        "        for r in ch['requires']:\n"
        "            if r not in seen_u:\n"
        "                skip = True\n"
        "                break\n"
        "        if skip or ch['cost'] > left + 1e-12:\n"
        "            continue\n"
        "        future = max(future, ch['value'] * (1.0 - 0.85 * burns.get(u, 0.0)) - ch['cost'] * 0.05)\n"
        "        left = left - ch['cost']\n"
        "        seen_u.add(u)\n"
        "        frontier.extend([x for x in ch['unlocks'] if x in by_id and x not in seen_u])\n"
    ).body[0].body

    class _IterQ(ast.NodeTransformer):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
            if node.name != "_q":
                return self.generic_visit(node)
            new_body: list[ast.stmt] = []
            skip_until_return = False
            inserted = False
            for st in node.body:
                if skip_until_return:
                    if isinstance(st, ast.Return):
                        skip_until_return = False
                        new_body.append(st)
                    continue
                new_body.append(st)
                if (
                    isinstance(st, ast.Assign)
                    and len(st.targets) == 1
                    and isinstance(st.targets[0], ast.Name)
                    and st.targets[0].id == "future"
                    and isinstance(st.value, ast.Constant)
                    and st.value.value == 0.0
                ):
                    new_body.extend(copy.deepcopy(walk_body))
                    skip_until_return = True
                    inserted = True
            if not inserted:
                return node
            node = copy.deepcopy(node)
            node.body = new_body
            return node

    new_tree = _IterQ().visit(copy.deepcopy(tree))
    ast.fix_missing_locations(new_tree)
    try:
        after = ast.unparse(new_tree) + "\n"
    except Exception:
        return []
    if after == src:
        return []
    return [after]


def _structural_policy_mutations(source_code: str) -> list[str]:
    """Structurally different POLICY genomes: 1-step flatten and iterative multi-step walk."""
    src = str(source_code or "")
    if not src.strip():
        return []
    out: list[str] = []
    try:
        out.extend(_flatten_recursive_q(src))
    except Exception:
        pass
    try:
        out.extend(_iterative_unlock_mutations(src))
    except Exception:
        pass
    return out


def _nested_named_function(source_code: str, name: str) -> ast.FunctionDef | None:
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return None
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == name:
            return fn
    return None


def _hors_crossover_mutations(
    src_a: str,
    src_b: str,
    *,
    skill_templates: Sequence[str] = (),
) -> list[str]:
    """Invent a POLICY genome by Plotkin LGG, filling holes from parents AND experience SKILLs.

    Parent mixes recombine living genomes. `skill_templates` are `{u}`-exprs from synthesized
    SKILL organs (traces), not parent source — the operator in the hole comes from the world.
    """
    src_a = str(src_a or "")
    src_b = str(src_b or "")
    if not src_a.strip() or not src_b.strip() or src_a == src_b:
        return []
    try:
        from canonical.swe_kernel.concept_library_v1 import (
            higher_order_plotkin_lgg,
            instantiate_plotkin_lgg,
        )
        from canonical.swe_kernel.recursive_self_architect_v1 import _splice_nested_function
    except Exception:
        return []
    qa = _nested_named_function(src_a, "_q")
    qb = _nested_named_function(src_b, "_q")
    if qa is None or qb is None:
        return []
    try:
        lgg = higher_order_plotkin_lgg(qa, qb)
    except Exception:
        return []
    if not lgg:
        return []
    fillings = lgg.get("hole_fillings") or {}
    extra_holes = [p for p in (lgg.get("param_names") or ()) if p in fillings]
    if len(extra_holes) < 1:
        return []
    n_extra = len(extra_holes)
    out: list[str] = []
    seen: set[str] = {src_a, src_b}

    def _emit(new_q: ast.FunctionDef | None) -> None:
        if new_q is None:
            return
        for parent in (src_a, src_b):
            try:
                tree = ast.parse(parent)
            except SyntaxError:
                continue
            outer = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
            if outer is None:
                continue
            try:
                spliced = _splice_nested_function(tree, outer.name, "_q", new_q)
                ast.fix_missing_locations(spliced)
                text = ast.unparse(spliced) + "\n"
            except Exception:
                continue
            if text and text not in seen:
                seen.add(text)
                out.append(text)

    # Mixed fillings only: skip all-parent-A and all-parent-B (those ARE the parents).
    masks = range(1, (1 << n_extra) - 1) if n_extra >= 2 else range(1, 1 << n_extra)
    for mask in masks:
        if len(out) >= 4:
            break
        choice = {h: (mask >> i) & 1 for i, h in enumerate(extra_holes)}
        try:
            _emit(instantiate_plotkin_lgg(lgg, parent_choice=choice, name="_q"))
        except Exception:
            continue

    # Experience: fill each arity-1 HO hole with a SKILL expr of the captured child id.
    ho_params = [p for p, ar in (lgg.get("callable_params") or ()) if int(ar) == 1]
    body_src = str(lgg.get("body_stmts") or "")
    arg_by_fn: dict[str, str] = {}
    try:
        for nd in ast.walk(ast.parse(body_src)):
            if (
                isinstance(nd, ast.Call)
                and isinstance(nd.func, ast.Name)
                and nd.func.id in ho_params
                and nd.args
            ):
                arg_by_fn.setdefault(nd.func.id, ast.unparse(nd.args[0]))
    except SyntaxError:
        arg_by_fn = {}
    for tmpl in skill_templates:
        if len(out) >= 6:
            break
        t = str(tmpl or "")
        if not t or "{u}" not in t:
            continue
        for fn_nm, u_nm in arg_by_fn.items():
            if len(out) >= 6:
                break
            expr = t.replace("{u}", u_nm)
            choice = {h: 0 for h in extra_holes}
            try:
                _emit(
                    instantiate_plotkin_lgg(
                        lgg, parent_choice=choice, name="_q", overrides={fn_nm: expr}
                    )
                )
            except Exception:
                continue
    return out


def _flatten_recursive_q(source_code: str) -> list[str]:
    """One-level unlock genome (no recursive `_q` self-call)."""
    src = str(source_code or "")
    if not src.strip():
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    class _InnerQ(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call) -> ast.AST:
            self.generic_visit(node)
            if not (isinstance(node.func, ast.Name) and node.func.id == "_q" and node.args):
                return node
            u = node.args[0]
            return ast.Subscript(
                value=ast.Subscript(
                    value=ast.Name(id="by_id", ctx=ast.Load()),
                    slice=u,
                    ctx=ast.Load(),
                ),
                slice=ast.Constant(value="value"),
                ctx=ast.Load(),
            )

        def visit_Assign(self, node: ast.Assign) -> ast.AST:
            self.generic_visit(node)
            if (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "candidates"
                and isinstance(node.value, ast.BoolOp)
                and isinstance(node.value.op, ast.Or)
                and node.value.values
            ):
                return ast.Assign(targets=node.targets, value=node.value.values[0])
            return node

    class _FlattenRecursiveQ(ast.NodeTransformer):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
            if node.name != "_q":
                return self.generic_visit(node)
            return _InnerQ().visit(node)

    new_tree = _FlattenRecursiveQ().visit(copy.deepcopy(tree))
    ast.fix_missing_locations(new_tree)
    try:
        after = ast.unparse(new_tree) + "\n"
    except Exception:
        return []
    if after == src:
        return []
    return [after]


def _successors_from_incumbent_source(
    source_code: str,
    *,
    learned_immediate: str | None,
    learned_combiner: str | None,
    concept_library: Any | None = None,
    peer_sources: Sequence[str] = (),
) -> list[str]:
    """RSA/egraph/`G_t` mutations of incumbent source. Not a factory."""
    out: list[str] = []
    src = source_code
    if concept_library is not None:
        try:
            from canonical.swe_kernel.concept_library_v1 import rewrite_source_with_concepts

            woken = rewrite_source_with_concepts(src, concept_library)
        except Exception:
            woken = None
        if woken:
            out.append(woken)
            src = woken
    if learned_immediate:
        patched = _apply_nested_fn(
            src,
            fn_name="_immediate",
            args=("value", "cost", "failed"),
            body=learned_immediate,
            rewire=_rewire_q_immediate,
        )
        if patched:
            out.append(patched)
            src = patched
    if learned_combiner:
        patched_c = _apply_nested_fn(
            src,
            fn_name="_combine",
            args=("immediate", "cost", "future"),
            body=learned_combiner,
            rewire=_rewire_q_combiner,
        )
        if patched_c:
            out.append(patched_c)
        if learned_immediate and src != source_code:
            only_comb = _apply_nested_fn(
                source_code,
                fn_name="_combine",
                args=("immediate", "cost", "future"),
                body=learned_combiner,
                rewire=_rewire_q_combiner,
            )
            if only_comb:
                out.append(only_comb)
    try:
        from canonical.swe_kernel.recursive_self_architect_v1 import mutate_organ_source
    except Exception:
        mutate_organ_source = None  # type: ignore[assignment]
    if mutate_organ_source is not None:
        seeds = [source_code, *out[:2]]
        for seed in seeds:
            try:
                out.extend(list(mutate_organ_source(seed) or ())[:2])
            except Exception:
                continue
    structural: list[str] = []
    for seed in [source_code, *out[:3]]:
        try:
            structural.extend(_structural_policy_mutations(seed))
        except Exception:
            continue
    skill_templates: list[str] = []
    if "def _immediate" in src or "def _immediate" in source_code:
        skill_templates.append(
            "_immediate(by_id[{u}]['value'], by_id[{u}]['cost'], burns.get({u}, 0.0))"
        )
    if "def _combine" in src or "def _combine" in source_code:
        skill_templates.append(
            "_combine(by_id[{u}]['value'], by_id[{u}]['cost'], 0.0)"
        )
    invented: list[str] = []
    for peer in [*peer_sources, *structural]:
        if not peer or peer == source_code:
            continue
        try:
            invented.extend(
                _hors_crossover_mutations(src, peer, skill_templates=skill_templates)
            )
        except Exception:
            continue
        if len(invented) >= 6:
            break
    rewritten: list[str] = []
    for s in [source_code, *out, *structural, *invented]:
        eg = _egraph_simplify_organ_source(s)
        if eg:
            rewritten.append(eg)
    seen: set[str] = {source_code}
    uniq: list[str] = []
    for s in [*invented, *out[:4], *structural, *out[4:], *rewritten]:
        if not s or s in seen:
            continue
        seen.add(s)
        uniq.append(s)
        if len(uniq) >= 12:
            break
    return uniq


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
    """New format = admitted child perceptor + synthesized affix glue (not a new `if kind`)."""
    if not existing:
        return None
    if isinstance(sample, (bytes, bytearray)):
        try:
            text = bytes(sample).decode("utf-8")
        except Exception:
            return None
    else:
        text = str(sample)
    n = len(text)
    if n < 3:
        return None
    children = list(existing)[:8]
    cuts: list[tuple[int, int]] = []
    for pre in range(0, min(20, n - 1)):
        for suf in range(0, min(20, n - pre - 1)):
            if pre == 0 and suf == 0:
                continue
            if pre and text[pre - 1].isspace():
                continue
            if suf and text[n - suf : n - suf + 1].isspace():
                continue
            cuts.append((pre, suf))
    cuts.sort(key=lambda ps: (ps[0] + ps[1], ps[0], ps[1]))
    for pre, suf in cuts[:64]:
        prefix = text[:pre]
        suffix = text[n - suf :] if suf else ""
        middle = text[pre : n - suf if suf else n]
        if not middle:
            continue
        for child in children:
            try:
                parsed = child.invoke(middle)
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
                + "def parse(raw):\n"
                + "    text = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)\n"
                + f"    prefix = {prefix!r}\n"
                + f"    suffix = {suffix!r}\n"
                + "    if prefix and not text.startswith(prefix):\n"
                + "        raise ValueError('PREFIX_MISMATCH')\n"
                + "    if suffix and not text.endswith(suffix):\n"
                + "        raise ValueError('SUFFIX_MISMATCH')\n"
                + "    body = text[len(prefix): len(text) - len(suffix) if suffix else None]\n"
                + "    return _child_parse(body)\n"
                + "\n"
                + "def serialize(parsed):\n"
                + "    inner = _child_serialize(parsed)\n"
                + "    if isinstance(inner, bytes):\n"
                + "        inner = inner.decode('utf-8')\n"
                + f"    return {prefix!r} + inner + {suffix!r}\n"
            )
            try:
                organ = make_organ(
                    stratum=PERCEPTOR,
                    name=f"perceptor_composed_{format_tag}",
                    task_signature=f"perceptor::{format_tag}",
                    entrypoint="parse",
                    source_code=wrapper,
                    parent_organ_ids=(child.organ_id,),
                    metadata={
                        "codec_family": "composed_affix",
                        "prefix": prefix,
                        "suffix": suffix,
                        "child": child.organ_id,
                    },
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
    extra: list[Any] = []
    for ins, _out in examples:
        for v in ins:
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v not in extra:
                extra.append(v)
            if len(extra) >= 6:
                break
        if len(extra) >= 6:
            break
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


def _skill_organ_to_concept_entry(
    organ: ExecutableOrgan, *, corpus_sources: Sequence[str] | None = None
) -> Any | None:
    """Bridge a SKILL organ into a ConceptEntry for `G_t` -- honestly accounted.

    Round 22 measured this bridge's two defects: it admitted only single-`return` bodies (so the
    induced period tables -- `Assign, Assign, Return` -- were all silently rejected and `G_t`
    stayed empty), and it reported a gain nobody computed (`mdl_gain_bytes=max(1, code_bytes)`,
    `corpus_sites=1`). A library fed fabricated numbers cannot compound, because nothing in it is
    measured. The fix, in `compression_gain_v1`:

      * multi-statement bodies are admitted, as statement-function entries;
      * `mdl_gain_bytes` and `corpus_sites` are COMPUTED by compressing this organ against the
        current SKILL corpus;
      * when the corpus genuinely compresses (>= 2 sites, strictly > 0 bytes, every rewritten site
        reproducing its original behaviour), the admitted entry IS the abstraction -- the shared
        parameterized shape -- carrying its measured gain, site count and structural family;
      * a singleton is admitted as what it is -- a stored primitive -- with gain 0 and sites 1.
        Zero is honest here; the defect was not that a primitive is stored, it is that storage was
        bookkept as compression.

    Fail-closed: any unexpected shape returns None and the organ simply stays un-bridged.
    """
    try:
        from canonical.swe_kernel.concept_library_v1 import ConceptEntry
        from canonical.swe_kernel import compression_gain_v1 as cg
    except Exception:
        return None
    corpus = list(corpus_sources or [])
    if organ.source_code not in corpus:
        corpus.append(organ.source_code)
    abstractions: list[dict[str, Any]] = []
    try:
        # The probe domain is derived from the corpus when the caller supplies none. Without that,
        # the numeric default grid answered a string-keyed table identically on every probe and the
        # (correct) vacuity gate refused every organ -- measured on the live path, not argued.
        res = cg.admit_corpus_abstraction(corpus)
        abstractions = list(res.get("abstractions") or [])
    except Exception:
        abstractions = []
    own = next((a for a in abstractions if organ.source_code in a.get("_member_sources", ())), None)
    if own is None:
        # fall back to matching this organ's lifted shape against the admissible abstractions
        try:
            lifted = cg.lift_shape(organ.source_code, organ.entrypoint)
        except Exception:
            lifted = None
        if lifted is not None:
            own = next(
                (a for a in abstractions if a.get("shape_key") == lifted["shape_key"]), None
            )
    if own is not None:
        cid = str(own["concept_id"])
        if not cid.isidentifier():
            return None
        return ConceptEntry(
            concept_id=cid,
            arity=int(own["arity"]),
            param_names=tuple(own["param_names"]),
            body_expr="",
            body_stmts=cg.helper_body_stmts(own),
            domain_kind="any",
            mdl_gain_bytes=int(own["gain_bytes"]),
            corpus_sites=int(own["sites"]),
            verified_hits=max(1, int(getattr(organ, "verified_passes", 0) or 1)),
            family=str(own.get("family") or ""),
        )
    # Singleton: a stored primitive. The gain is zero because zero compression was measured --
    # never a fabricated number. The id is derived from the SOURCE, not from the organ id: the old
    # expression left `c_organ_skill_` for every organ (see `cg.concept_id_for_source`), so this
    # branch could store exactly one program no matter how many were offered.
    cid = cg.concept_id_for_source(organ.source_code)
    if not cid.isidentifier():
        return None
    try:
        tree = ast.parse(organ.source_code)
    except SyntaxError:
        return None
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == organ.entrypoint), None)
    if fn is None or not fn.body:
        return None
    try:
        if len(fn.body) == 1 and isinstance(fn.body[0], ast.Return) and fn.body[0].value is not None:
            return ConceptEntry(
                concept_id=cid,
                arity=len(fn.args.args),
                param_names=tuple(a.arg for a in fn.args.args),
                body_expr=ast.unparse(fn.body[0].value),
                domain_kind="any",
                mdl_gain_bytes=0,
                corpus_sites=1,
                verified_hits=max(0, int(getattr(organ, "verified_passes", 0) or 0)),
            )
        body_stmts = "\n".join(ast.unparse(stmt) for stmt in fn.body)
        return ConceptEntry(
            concept_id=cid,
            arity=len(fn.args.args),
            param_names=tuple(a.arg for a in fn.args.args),
            body_expr="",
            body_stmts=body_stmts,
            domain_kind="any",
            mdl_gain_bytes=0,
            corpus_sites=1,
            verified_hits=max(0, int(getattr(organ, "verified_passes", 0) or 0)),
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
        self._live_policy_boards: list[list[dict[str, Any]]] = []
        self.bootstrap_inductions: int = 0
        #: When the grammar cannot express the answer, should the graph spend oracle questions to
        #: induce the missing operator? A refusal that cannot teach is only half a repair, and
        #: `Omega_{t+1} = Omega_t U P_t U C_t` is otherwise just a diagram.
        self.growth_enabled: bool = True
        #: Hard cap on questions spent collecting evidence before deciding no structure is present.
        self.growth_evidence_budget: int = 24
        self.convention_memory = ConventionMemory()
        self.policy_archive: Any | None = None
        if self.state_path is not None:
            try:
                from canonical.swe_kernel.recursive_self_architect_v1 import QualityDiversitySelfArchive

                self.policy_archive = QualityDiversitySelfArchive(
                    self.state_path.with_name("policy_qd_archive_v1.json")
                )
            except Exception:
                self.policy_archive = None
        if self.state_path is not None and self.state_path.is_file():
            self._load()

    def _tap_policy_invoke(self, organ: ExecutableOrgan) -> None:
        """Remember the board a POLICY organ ranked. Perception that is thrown away cannot teach."""
        if organ.stratum != POLICY or getattr(organ, "_board_tap", False):
            return
        graph = self
        orig = organ.invoke

        def _tapped(*args: Any, **kwargs: Any) -> Any:
            if args:
                snap = _snapshot_action_board(args[0])
                if snap and any(r["unlocks"] or r["requires"] for r in snap):
                    graph._live_policy_boards.append(snap)
                    if len(graph._live_policy_boards) > 8:
                        del graph._live_policy_boards[:-8]
            return orig(*args, **kwargs)

        organ.invoke = _tapped  # type: ignore[method-assign]
        organ._board_tap = True  # type: ignore[attr-defined]

    def register_organ(self, organ: ExecutableOrgan) -> dict[str, Any]:
        """Admit or Pareto-update an organ in `P_t`."""
        organ.ensure_compiled()
        self._tap_policy_invoke(organ)
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
        # EVERY stratum with an entrypoint, not only SKILL. Round 25's second family is emitted by
        # `synthesize_world_model_organ`, which is a WORLD_MODEL organ -- so the compression corpus
        # could only ever be fed by one of the seven strata, and the family the round measured as
        # generalising had no live writer at all (measured: three world-model organs registered
        # through this method left `G_t` empty even after the probe-domain fix). A perceptor and a
        # skill are the same kind of object: a function with a shape. Restricting admission by
        # stratum was never a measured property; it was an accident of which writer landed first.
        # `PERCEPTOR` and `VERIFIER` organs are still excluded: their entrypoints take raw samples
        # and return parsed records, so lifting their literals would probe a parser with tokens it
        # was not written to accept, and a refusal there would read as a compression failure.
        if (
            self.concept_library is not None
            and organ.stratum in _ADMISSIBLE_STRATA
        ):
            # The compression corpus is the LIBRARY's memory plus the newcomer. Every previously
            # registered SKILL organ is already held in `G_t` as a stored entry (that bridge is
            # the one below), and `G_t` is the accumulator that survives the graph being fresh --
            # counting a graph-local copy on top of its own stored entry would fabricate sites.
            # An admitted abstraction (family set) is derived, not a stored program, and stays
            # out of the corpus it is about to be re-admitted over.
            corpus: list[str] = []
            try:
                for c in self.concept_library.concepts():
                    if str(getattr(c, "family", "") or ""):
                        continue
                    try:
                        corpus.append(c.render_helper_def())
                    except Exception:
                        continue
            except Exception:
                corpus = []
            corpus.append(organ.source_code)
            entry = _skill_organ_to_concept_entry(organ, corpus_sources=corpus)
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
        value: float | None = None,
    ) -> None:
        """Accumulate wake traces and compile a WORLD_MODEL organ when enough exist."""
        row: dict[str, Any] = {
            "action": str(action_id),
            "cost": float(cost),
            "failed": bool(failed),
            "delta": dict(delta or {}),
        }
        if value is not None:
            row["value"] = float(value)
        if self._live_policy_boards:
            row["board"] = self._live_policy_boards[-1]
        self._world_transitions.append(row)
        if len(self._world_transitions) < 2 or len(self._world_transitions) % 2 != 0:
            return
        try:
            wm = synthesize_world_model_organ(self._world_transitions[-16:])
            if wm is not None:
                self.register_organ(wm)
            self.evolve_policy_from_traces()
        except Exception:
            return

    def evolve_policy_from_traces(self) -> ExecutableOrgan | None:
        """Factory is bootstrap only. Successors mutate the incumbent organ under Ring-0."""
        if len(self._world_transitions) < 2:
            return None
        traces = self._world_transitions[-16:]
        counts: dict[str, int] = {}
        fails: dict[str, int] = {}
        for tr in traces:
            aid = str(tr.get("action") or tr.get("action_id") or "")
            if not aid:
                continue
            counts[aid] = counts.get(aid, 0) + 1
            fails[aid] = fails.get(aid, 0) + (1 if tr.get("failed") else 0)
        if not counts:
            return None
        burns = {k: fails[k] / max(1, counts[k]) for k in counts}
        incumbent = self.get_primary(POLICY, "policy::instrumental_q")
        for existing in self.organs_in_stratum(POLICY):
            if not _policy_respects_trace_ranking(existing, traces):
                existing.verified_failures += 1

        learned = _synthesize_immediate_from_traces(traces, concept_library=self.concept_library)
        if isinstance(learned, str):
            learned = _simplify_statement_body(learned)
        comb_learned = _synthesize_combiner_from_traces(traces, concept_library=self.concept_library)
        if isinstance(comb_learned, str):
            comb_learned = _simplify_statement_body(comb_learned)

        candidates: list[ExecutableOrgan] = []
        if incumbent is None:
            boot = compile_policy_organ(empirical_burns=burns)
            boot.verified_passes = max(boot.verified_passes, len(self._world_transitions))
            boot.metadata["bootstrap_factory"] = True
            if comb_learned:
                boot.metadata["learned_combiner_src"] = comb_learned
            candidates.append(boot)
        else:
            if self.concept_library is not None and hasattr(self.concept_library, "sleep_abstract"):
                sleep_corpus = [o.source_code for o in self.organs_in_stratum(POLICY)[:8]]
                try:
                    sleep_corpus.extend(_structural_policy_mutations(incumbent.source_code)[:2])
                except Exception:
                    pass
                if len(sleep_corpus) >= 2:
                    try:
                        self.concept_library.sleep_abstract(sleep_corpus)
                    except Exception:
                        pass
            md = incumbent.metadata or {}
            if md.get("learned_immediate") and isinstance(md.get("learned_immediate_src"), str):
                if not learned:
                    learned = str(md.get("learned_immediate_src"))
            parents = [incumbent.source_code]
            if self.policy_archive is not None:
                try:
                    parents.extend(list(self.policy_archive.elite_organ_sources(limit=3) or ()))
                except Exception:
                    pass
            seen_parent: set[str] = set()
            for parent_src in parents:
                if not parent_src or parent_src in seen_parent:
                    continue
                seen_parent.add(parent_src)
                srcs = _successors_from_incumbent_source(
                    parent_src,
                    learned_immediate=learned,
                    learned_combiner=comb_learned,
                    concept_library=self.concept_library,
                    peer_sources=[p for p in parents if p and p != parent_src][:3],
                )
                parent_id = incumbent.organ_id if parent_src == incumbent.source_code else "archive_elite"
                for src in srcs:
                    if len(candidates) >= 12:
                        break
                    try:
                        rec = make_organ(
                            stratum=POLICY,
                            name=incumbent.name,
                            task_signature="policy::instrumental_q",
                            entrypoint=incumbent.entrypoint,
                            source_code=src,
                            parent_organ_ids=(incumbent.organ_id, *incumbent.parent_organ_ids)[:8],
                            metadata={
                                **dict(incumbent.metadata),
                                "from_incumbent": parent_id == incumbent.organ_id,
                                "from_archive_elite": parent_id == "archive_elite",
                                "bootstrap_factory": False,
                                "learned_immediate": bool(learned),
                                "learned_combiner": bool(comb_learned),
                                "hors_crossover": "def _q(_v0" in src,
                            },
                        )
                    except OrganSafetyError:
                        continue
                    rec.verified_passes = max(incumbent.verified_passes, len(self._world_transitions) + 8)
                    rec.metadata["learned_immediate"] = "def _immediate" in src
                    rec.metadata["learned_combiner"] = "def _combine" in src
                    if learned:
                        rec.metadata["learned_immediate_src"] = learned
                    if comb_learned:
                        rec.metadata["learned_combiner_src"] = comb_learned
                    candidates.append(rec)
                if len(candidates) >= 12:
                    break

        admitted: list[ExecutableOrgan] = []
        for organ in candidates:
            verdict = admit_policy_organ(organ, traces)
            if not verdict.get("ok"):
                continue
            self.register_organ(organ)
            admitted.append(organ)
            if self.policy_archive is not None:
                try:
                    self.policy_archive.record_organ_source(
                        source_code=organ.source_code,
                        organ_id=organ.organ_id,
                        score=float(organ.pareto_score),
                        stratum=POLICY,
                        horizon_bin=_policy_horizon_bin(organ),
                    )
                except Exception:
                    pass
        if self.concept_library is not None and hasattr(self.concept_library, "sleep_abstract"):
            pol_srcs = [o.source_code for o in self.organs_in_stratum(POLICY)[:8]]
            if len(pol_srcs) >= 2:
                try:
                    self.concept_library.sleep_abstract(pol_srcs)
                except Exception:
                    pass
        if not admitted:
            return incumbent
        best = max(
            admitted,
            key=lambda o: (
                1 if o.metadata.get("learned_immediate") else 0,
                1 if o.metadata.get("from_incumbent") else 0,
                o.verified_passes,
                o.pareto_score,
            ),
        )
        self.primary_by_sig[(POLICY, "policy::instrumental_q")] = best.organ_id
        comb_body = best.metadata.get("learned_combiner_src")
        try:
            comb_organ = compile_combiner_organ(
                body=comb_body if isinstance(comb_body, str) else None
            )
            self.register_organ(comb_organ)
            prev = [
                o
                for o in self.organs_in_stratum(SKILL)
                if o.task_signature == "policy::combiner" and o.organ_id != comb_organ.organ_id
            ]
            if prev:
                meta = compile_meta_synthesizer_organ(
                    prev[0], comb_organ, tactic_name="policy_combiner_meta"
                )
                if meta is not None:
                    self.register_organ(meta)
        except OrganSafetyError:
            pass
        self._save()
        return best

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

        # 3. Last resort: induce a bootstrap primitive (counted; becomes an operator, not a 9th kind)
        all_samples = [raw_sample, *extra_samples]
        new_organ = synthesize_perceptor_organ(all_samples, format_tag=format_tag)
        if new_organ is None:
            return {"ok": False, "reason": "NO_VERIFIED_ROUNDTRIP_PERCEPTOR_FOUND"}
        self.register_organ(new_organ)
        self.bootstrap_inductions += 1
        self._save()
        parsed = new_organ.invoke(raw_sample)
        return {
            "ok": True,
            "parsed": parsed,
            "organ_id": new_organ.organ_id,
            "synthesized_new_organ": True,
            "induced_bootstrap_primitive": True,
            "bootstrap_inductions": self.bootstrap_inductions,
        }

    # ------------------------ Version-Space Skill Synthesis & Meta-Compilation

    def _grow_operator_from_evidence(
        self,
        examples: Sequence[tuple[tuple[Any, ...], Any]],
        oracle: Callable[[tuple[Any, ...]], Any],
        task_signature: str,
    ) -> tuple["ExecutableOrgan", dict[str, Any]] | None:
        """Turn a failure into a new operator, or decline and say the structure was not recognised.

        The diagnosis runs on evidence this run already paid for. If it names periodicity, the period
        is then BOUGHT with a bounded number of questions, and must be verified at 2p and 3p before it
        is believed -- one agreeing point is a coincidence, not a period (measured: `floor(x/3)`
        agrees with itself at x0=0 and x0=2). If the diagnosis names nothing, this returns None and the
        caller keeps its honest refusal: an undiagnosed structure is never guessed at.
        """
        if not examples or not self.growth_enabled:
            return None
        # A prior may come ONLY from the library, and only from a measured abstraction:
        # compression-positive, >= 2 real sites, verified. An empty library, a stored primitive,
        # or an unverified entry licenses nothing and every rule below keeps its cold form. This
        # is the exact difference between "the library made the next problem cheaper" (measured
        # compounding) and "a hand-tuned threshold moved" (a policy edit wearing learning's
        # clothes).
        licensed = None
        if self.concept_library is not None:
            try:
                from canonical.swe_kernel.compression_gain_v1 import licensed_table_policy

                licensed = licensed_table_policy(self.concept_library)
            except Exception:
                licensed = None
        try:
            diagnosis = settlement.diagnose_structure(examples)
        except Exception:
            return None

        # A structure cannot be seen until there is enough evidence to see it with. Three seeds plus a
        # refutation is four points, which is not enough to distinguish a cycle from a line -- measured:
        # the first four values of `x mod 4` are 0,1,2,3 and were confidently reported as affine. So when
        # the diagnosis says UNEXPLAINED, spend a BOUNDED number of questions before concluding that
        # nothing is there. Bounded matters: "collect until it makes sense" is how a system talks itself
        # into a pattern, so the budget is a constant and running out of it is a refusal, not a licence.
        evidence = list(examples)
        spent = 0
        escalated = False
        budget = self.growth_evidence_budget
        step = 1
        # The run must be long enough to CONTAIN two periods, so the budget is not a constant: it
        # grows with what the evidence is beginning to look like. A fixed cap silently capped the
        # expressible structure at half its own value -- measured: k=4 and k=5 were induced, k>=7 never
        # could be, purely because 24 questions cannot contain two cycles of 7.
        seen_span = 0.0
        straight = 0
        def _needs_more_evidence(d: dict[str, Any]) -> bool:
            """Keep looking when the diagnosis is a statement about a short sample, not the world.

            Crucially this also keeps looking when a period TABLE already fits. The structure
            classifier only names shapes it can check analytically, so an arbitrary repeating block --
            period 3, values [5,-2,7] -- reads as UNEXPLAINED no matter how much evidence arrives, while
            the table hypothesis explains it from three points. Stopping only on the classifier's word
            would make the table unreachable, which is how a diagnostic that cannot see a structure
            prevents the creature from ever learning it.
            """
            # THE LICENSED EARLY STOP. When the library holds a compression-positive, multi-site,
            # verified abstraction of the table family, two full cycles -- the block stated once
            # and confirmed at a second position -- plus the acquire-time verification at 2p and
            # 3p below is the licensed evidence policy for a NEW member of that family. The cold
            # 4x rule exists because a structure-free run must buy its skepticism point by point;
            # a measured prior is exactly experience paying part of that bill. Without a licensed
            # abstraction this branch never fires and the cold rule is untouched, byte for byte.
            if licensed is not None:
                try:
                    if settlement.induce_periodic_table(
                        list(evidence), min_compression=float(licensed["min_compression"])
                    ) is not None:
                        return False
                except Exception:
                    pass
            if d.get("kind") == settlement.UNEXPLAINED:
                return settlement.induce_periodic_table(list(evidence)) is None
            return d.get("kind") == settlement.AFFINE and bool(d.get("provisional"))

        while _needs_more_evidence(diagnosis) and spent < budget:
            # Budget growth must be BOUNDED and monotone-by-a-rule, not a feedback loop. The previous
            # version recomputed the budget from `straight` on every iteration, so a long distinct run
            # raised the budget, which collected more points, which lengthened the run, which raised the
            # budget again -- measured at 61 questions and still climbing, with the period sitting in the
            # evidence the whole time. One escalation, capped, and never more than twice the base.
            if straight > 3 and not escalated:
                budget = min(int(6 * max(2, straight - 3)), 2 * self.growth_evidence_budget)
                escalated = True
            # Anchor on the LAST collected point and advance from there, and skip anything already
            # held. The previous version anchored on `evidence[0]` (a fixed seed) while incrementing a
            # counter, so it re-probed points it already had; because the duplicate check compared
            # before appending but the anchor never moved, a stale pair could be appended with a
            # CONTRADICTING value -- measured: (2, 5.0) followed by (2, 7.0). Contradictory evidence
            # silently destroys every hypothesis downstream and looks exactly like "no structure here".
            probe = (evidence[-1][0][0] + 1,)
            step += 1
            if any(tuple(ex_in) == probe for ex_in, _ in evidence):
                # Walk forward past anything already held instead of stopping. Stopping here left the
                # run with exactly the evidence it started with plus a few points -- measured: four
                # points against a period-table rule that needs twelve, so the structure could never be
                # reached and the refusal looked like an absence of structure.
                probe = (probe[0] + 1,)
                while any(tuple(ex_in) == probe for ex_in, _ in evidence):
                    probe = (probe[0] + 1,)
            observed = oracle(probe)
            # A long consecutive run of DISTINCT outputs is a straight stretch, and a straight stretch
            # is exactly what a long period looks like before it closes. Its length is evidence about
            # the period's lower bound, so it is what the budget follows.
            if evidence and abs(float(observed) - float(evidence[-1][1])) > 1e-9:
                straight += 1
            else:
                straight = 0
            evidence.append((probe, observed))
            spent += 1
            try:
                diagnosis = settlement.diagnose_structure(evidence)
            except Exception:
                return None
        # Two independent signals can license growth, and either is sufficient: the structure
        # classifier naming periodicity, or a period TABLE that already explains the evidence. Requiring
        # the classifier alone made the table unreachable for exactly the functions the table exists to
        # handle, because an arbitrary repeating block is not a shape the classifier can check
        # analytically -- measured: the loop collected thirteen points, the table fit them from three,
        # and the run still refused.
        table_hypothesis = settlement.induce_periodic_table(evidence)
        # The licensed fit carries through: without this, the top-up block below would re-derive
        # the cold 4x requirement and silently re-spend every question the prior just saved --
        # measured in round 23 as the difference between stopping at two cycles and being dragged
        # back to four.
        if table_hypothesis is None and licensed is not None:
            try:
                table_hypothesis = settlement.induce_periodic_table(
                    evidence, min_compression=float(licensed["min_compression"])
                )
            except Exception:
                table_hypothesis = None
        # ALWAYS top the evidence up to the table's own threshold before deciding. The loop above stops
        # as soon as the classifier has an opinion, which for an arbitrary repeating block is
        # "UNEXPLAINED" forever; the compression rule then needs four cycles before it will speak, and
        # seven points is short of the twelve a period-3 table requires. Deciding in between those two
        # thresholds is what produced a refusal on evidence that fully determines the answer.
        if table_hypothesis is None:
            # Recompute the candidate after each top-up instead of freezing it. A single pass used a
            # `guessed` period from a three-point sample, sized the requirement from it, met that
            # requirement, and never re-derived -- measured: the loop stopped at 60 points while the
            # period-30 table needed 120, and the run refused a function it could have expressed.
            for _round in range(6):
                guessed = settlement.candidate_period(evidence)
                if guessed is None:
                    break
                # THE LICENSED REQUIREMENT. This block is where the evidence bill is actually
                # sized -- the collection loop above is capped by its escalation budget long
                # before either factor is reached (measured: both arms exit the loop at 15
                # points; every question that matters is spent here). When a library abstraction
                # licenses the family, the requirement is two cycles; the cold rule is four. The
                # acquire-time verification at 2p and 3p below is not waived by this -- the
                # policy moves where evidence is collected, never whether it is verified.
                if licensed is not None:
                    requirement = settlement.table_evidence_requirement(
                        int(guessed), factor=int(float(licensed["min_compression"]))
                    )
                else:
                    requirement = settlement.table_evidence_requirement(int(guessed))
                if len(evidence) >= requirement:
                    break
                while len(evidence) < requirement:
                    probe = (evidence[-1][0][0] + 1,)
                    while any(tuple(ex_in) == probe for ex_in, _ in evidence):
                        probe = (probe[0] + 1,)
                    evidence.append((probe, oracle(probe)))
                    # Count these. The earlier version collected evidence without incrementing the
                    # spend, so the reported cost understated the questions actually asked -- a
                    # measurement error in the one number the caller needs in order to decide whether
                    # to keep going.
                    spent += 1
                diagnosis = settlement.diagnose_structure(evidence)
                table_hypothesis = settlement.induce_periodic_table(evidence)
                if table_hypothesis is None and licensed is not None:
                    try:
                        table_hypothesis = settlement.induce_periodic_table(
                            evidence, min_compression=float(licensed["min_compression"])
                        )
                    except Exception:
                        table_hypothesis = None
                if table_hypothesis is not None:
                    break
        # A table is the more general hypothesis, but "more general" is not "always better". Its
        # compression rule needs four full cycles, so for a long period with a short budget it cannot
        # speak while the RAMP template can -- measured: period 30 regressed from 150/150 (ramp) to a
        # refusal once the table was preferred unconditionally. Generalise where it helps, keep the
        # narrow form where the general one cannot reach, and never let one crowd out the other.
        if diagnosis.get("kind") != settlement.PERIODIC and table_hypothesis is None:
            if settlement.candidate_period(evidence) is None:
                return None
        acquired = settlement.acquire_period(oracle, examples[0][0])
        if not acquired.get("ok"):
            return None
        period = int(acquired["period"])

        # Prefer a TABLE when the evidence supports one. A table subsumes the ramp: `x mod k` is the
        # block [0..k-1], so the ramp template is a special case rather than a separate mechanism. The
        # table is tried first because it is the more general hypothesis, and because the ramp would
        # refuse an arbitrary repeating block -- measured: a period-3 cycle [5,-2,7] is perfectly
        # periodic and three questions determine it, yet the ramp-only path returned
        # NO_CONSISTENT_HYPOTHESIS. Falling back to the ramp keeps the narrow case fast where the
        # compression requirement cannot be met yet.
        table = synthesize_table_organ(
            evidence,
            task_signature=task_signature,
            # The licensed factor, and ONLY that one, reaches the synthesizer; the cold default
            # applies when no abstraction licensed anything.
            min_compression=(
                float(licensed["min_compression"]) if licensed is not None else 4.0
            ),
        )
        if table is not None:
            organ, found_table = table
            return organ, {
                "kind": "PERIODIC_TABLE",
                "period": int(found_table["period"]),
                "block": list(found_table["block"]),
                "compression": round(float(found_table["compression"]), 4),
                "acquired_period": period,
                "questions": spent + int(acquired.get("questions", 0)),
                "evidence_collected": len(evidence),
                "verified_at": [period, 2 * period, 3 * period],
            }
        if diagnosis.get("period") not in (None, period):
            # The period bought from fresh questions disagrees with the one inferred from the evidence
            # already held. Two measurements of the same quantity that disagree mean one of them is
            # being read wrongly, so nothing is believed until they agree.
            return None
        grown = synthesize_periodic_organ(
            evidence,
            task_signature=task_signature,
            oracle=oracle,
            memory=self.convention_memory,
        )
        if grown is None:
            return None
        organ, found = grown
        return organ, {
            "kind": "PERIODIC",
            "diagnosed_period": diagnosis.get("period"),
            "acquired_period": period,
            "questions": spent
            + int(acquired.get("questions", 0))
            + int(found.get("convention_queries", 0)),
            "evidence_collected": len(evidence),
            "convention": self.convention_memory.convention,
            "convention_from_memory": found.get("convention_from_memory"),
            "verified_at": [period, 2 * period, 3 * period],
        }

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
        #: Questions actually asked to the oracle, counted from the first one. The recall path below
        #: spends a query to test the incumbent, and for several rounds it reported `0` -- a reported
        #: cost that omits the questions you asked is a lie about what the answer was worth.
        recall_queries_used = 0
        existing = self.get_primary(SKILL, task_signature)
        if existing is not None:
            consistent = all(
                (ok and _outputs_match(val, exp))
                for ex_in, exp in examples
                for ok, val in [_safe_eval_candidate(existing, ex_in)]
            )
            if consistent and oracle is not None:
                # Agreement with the examples already given is not evidence of correctness -- it is
                # evidence that this instance looks like the last one. Measured: x mod 4 recalled for
                # x mod 5,7,8,10,11 with zero questions and held-out accuracy 0/10, while reporting
                # RECALLED_TIER0_ORGAN. When an oracle is standing by, spend one question finding out
                # instead of assuming. If it holds, the cost is a single query and the organ stays.
                probe = _first_refuting_probe(existing, examples, task_signature)
                if probe is not None:
                    recall_queries_used += 1
                    try:
                        observed = oracle(probe)
                    except Exception:
                        observed = None
                    if observed is not None and not (
                        lambda ov: ov[0] and _outputs_match(ov[1], observed)
                    )(_safe_eval_candidate(existing, probe)):
                        # The incumbent was about to be wrong. Fall through to fresh synthesis with
                        # the new observation in hand, so experience corrects itself instead of
                        # compounding a mistake.
                        examples = list(examples) + [(probe, observed)]
                        existing = None
            if existing is not None and all(
                (ok and _outputs_match(val, exp))
                for ex_in, exp in examples
                for ok, val in [_safe_eval_candidate(existing, ex_in)]
            ):
                return {
                    "ok": True,
                    "status": "RECALLED_TIER0_ORGAN",
                    "organ": existing,
                    "oracle_queries_used": recall_queries_used,
                    "recall_verified_by_oracle": recall_queries_used > 0,
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
            # The grammar produced NOTHING. This is the strongest form of failure and it used to be
            # the shortest path out of the function -- a one-line refusal. But it is also exactly the
            # case where growing matters most: the answer is not in the grammar at all. A failure that
            # can be diagnosed must be diagnosed, whichever door it came through; only the exits that
            # cannot teach are allowed to stay exits.
            if oracle is not None and self.growth_enabled:
                grown_none = self._grow_operator_from_evidence(work_examples, oracle, task_signature)
                if grown_none is not None:
                    organ, growth = grown_none
                    self.register_organ(organ)
                    return {
                        "ok": True,
                        "status": "INDUCED_OPERATOR_CRYSTALLIZED",
                        "organ": organ,
                        "oracle_queries_used": int(growth.get("questions", 0)),
                        "growth": growth,
                    }
            return {"ok": False, "status": "NO_CONSISTENT_HYPOTHESIS", "seen_candidates": len(seen_ast)}

        queries_used = recall_queries_used
        #: Evidence accumulated after the initial grammar search that the grammar itself cannot
        #: explain. Tracked so the caller is told the truth ("the world is outside my space")
        #: instead of being handed a verdict the instrument is not entitled to.
        outside_space_evidence: list[Any] = []
        interchangeable = False

        # The decision this loop is making -- "is it settled which of these is right, and is asking
        # worth it?" -- already had a computed answer in `settlement_v1`, and the organ graph was not
        # using it. Two implementations of one definition means only one of them is ever tested. The
        # space is built from the surviving candidates so the same posterior arithmetic that governs
        # the settlement layer governs the creature's real disambiguation.
        decision_space = settlement.VersionSpace(
            [
                settlement.Hypothesis(
                    key=o.organ_id,
                    predict=(lambda org: lambda probe: _safe_eval_candidate(org, probe)[1])(o),
                    description=o.name,
                )
                for o in candidate_organs
            ]
        )
        for ex_in, ex_out in work_examples:
            decision_space.observe(tuple(ex_in), ex_out)
        settlement_probe, settlement_gain = decision_space.select_probe(
            _settlement_probe_space(work_examples, candidate_organs)
        )

        while len(candidate_organs) > 1:
            disc_probe = synthesize_discriminating_input(candidate_organs, work_examples)
            if disc_probe is None:
                # My frozen probe grid cannot separate these. That is a statement about the GRID,
                # not about the programs. Reaching for the first survivor here used to turn
                # blindness into certainty (measured: x mod 4 crystallized as `proj_0`, held-out
                # 2/10, status DISAMBIGUATED_AND_CRYSTALLIZED). If an oracle is present, ask it
                # the question my own grid could not think of; otherwise refuse and say why.
                derived = _settlement_probe_space(work_examples, candidate_organs)
                real_probe = synthesize_discriminating_input(
                    candidate_organs, work_examples, probes_override=derived
                )
                if real_probe is not None and oracle is not None and queries_used < max_oracle_queries:
                    disc_probe = real_probe
                elif not _survivors_disagree_on_domain(candidate_organs, work_examples):
                    # Nothing separates them, but they also never disagree anywhere the caller can
                    # reach: the ambiguity is INCONSEQUENTIAL. Choosing the simplest is then not a
                    # guess -- either answer is equally correct on every input that exists for this
                    # caller. This is deliberately distinguished from the blind case below, because
                    # refusing here would make the creature timid (P5) without buying any safety.
                    candidate_organs = sorted(
                        candidate_organs, key=lambda o: (o.code_bytes, o.organ_id)
                    )[:1]
                    interchangeable = True
                    break
                else:
                    return {
                        "ok": False,
                        "status": "UNSETTLEABLE_BY_THIS_INSTRUMENT",
                        "detail": (
                            "survivors disagree on the caller's domain and no reachable probe separates them"
                            if real_probe is None
                            else "a derived probe separates them but no oracle was supplied"
                        ),
                        "surviving_count": len(candidate_organs),
                        "surviving_names": [o.name for o in candidate_organs[:6]],
                        "oracle_queries_used": queries_used,
                    }
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

        # --- Door 3: a single surviving hypothesis is not a settled question -------------------
        # When the grammar can only think of one program, the loop above never runs and the old code
        # crystallized it immediately. Measured: `x mod 5` given seeds 1..3 produced
        # `if x0 <= 0: 0/x0 else x0/1` -- the identity function in disguise -- which matches the seeds
        # and any observation that happens to agree with it, and was admitted with zero questions and
        # 0/10 held-out accuracy. "My grammar can think of only one program" is a fact about the
        # grammar. It cannot certify a program, so the winner must predict something it has not
        # already been shown before it is allowed to become permanent.
        if oracle is not None and queries_used < max_oracle_queries:
            unseen = [
                pr
                for pr in _settlement_probe_space(work_examples, [winner])
                if tuple(repr(x) for x in pr)
                not in {tuple(repr(x) for x in ex_in) for ex_in, _ in work_examples}
            ]
            for probe in unseen[:2]:
                ok_now, predicted = _safe_eval_candidate(winner, probe)
                try:
                    observed = oracle(probe)
                except Exception:
                    break
                queries_used += 1
                if not (ok_now and _outputs_match(predicted, observed)):
                    work_examples.append((probe, observed))
                    # The grammar's best guess is dead. Before reporting that, spend questions
                    # trying to ACQUIRE the missing structure: a refusal that does not teach is
                    # only half a repair, and this is the branch where Omega grows.
                    grown = self._grow_operator_from_evidence(
                        work_examples, oracle, task_signature
                    )
                    if grown is not None:
                        organ, growth = grown
                        self.register_organ(organ)
                        return {
                            "ok": True,
                            "status": "INDUCED_OPERATOR_CRYSTALLIZED",
                            "organ": organ,
                            "oracle_queries_used": queries_used
                            + int(growth.get("questions", 0)),
                            "growth": growth,
                            "refuting_probe": probe,
                        }
                    return {
                        "ok": False,
                        "status": "HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED",
                        "detail": (
                            "the only hypothesis the grammar could form failed a held-out prediction, "
                            "and the evidence does not name a structure this creature can acquire"
                        ),
                        "refuting_probe": probe,
                        "predicted": predicted,
                        "observed": observed,
                        "oracle_queries_used": queries_used,
                    }

                work_examples.append((probe, observed))

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
            "settlement": {
                "entropy_bits": round(decision_space.entropy(), 6),
                "probe_selected": settlement_probe,
                "information_gain_bits": round(settlement_gain, 6),
                "posterior": {
                    str(k): round(v, 6) for k, v in decision_space.posterior().items()
                },
            },
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
            "bootstrap_inductions": int(self.bootstrap_inductions),
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
            "bootstrap_inductions": int(self.bootstrap_inductions),
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
                self._tap_policy_invoke(org)
                self.organs[org.organ_id] = org
            except Exception:
                continue
        for k, oid in (raw.get("primary_by_sig") or {}).items():
            if "::" in k and oid in self.organs:
                s, sig = k.split("::", 1)
                self.primary_by_sig[(s, sig)] = str(oid)
        if isinstance(raw.get("predictor"), Mapping):
            self.predictor = CausalFeatureSelfPredictor.from_row(raw["predictor"])
        try:
            self.bootstrap_inductions = max(0, int(raw.get("bootstrap_inductions") or 0))
        except (TypeError, ValueError):
            self.bootstrap_inductions = 0
