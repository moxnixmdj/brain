#!/usr/bin/env python3
"""Sentient Cognitive Core V1 (`sentient_cognitive_core_v1`, `K3 = 0`).

First-principles active-inference, causal world-modeling, global Value-of-Information
dominance search, and Wake-Sleep consolidation engine uniting Brain's existential
`Creature` organs with its mathematical synthesis, confinement, and verification kernels:

  1. `EpistemicSelfBeliefEngine` (`Theta_t = (mu_t, Sigma_t)` + Surprise `S_t`):
     Online diagonal Kalman / Laplace-approximated Bayesian logistic self-model over
     task/capability structural and causal features `phi(x)`. Eliminates static
     probability tables (`0.04 / 0.76`): every prediction integrates parameter
     uncertainty (`MacKay probit marginal`), settles into `self_prediction_calibration_v1`,
     updates `(mu_t, Sigma_t)` in `< 0.05 ms`, and computes surprise `S_t` to gate
     System-1 (`< 0.5 ms`) reflex vs System-2 deliberation and open `ignorance_ledger_v1`
     anomalies on model mismatch.

  2. `CausalWorldGraph` (`W_t = (S, A, T_hat, Pre_hat, Prod_hat, Dest_hat)`):
     Unites `environment_learning_v1` transitions, `interaction_v1` producer/destroyer
     conflict discovery, and `compose_v1` failure-complaint precondition extraction.
     Enforces pre-execution `(Read, Write, Destroy)` effect polarity so destructive
     actions that clobber goal-needed state are inhibited BEFORE execution, and plans
     minimal-action shortest causal chains from zero prior.

  3. `GlobalVoIDominanceController` (Anti-YouTube Extrapolation & Dominance Search):
     Unites `global_retrieval_controller_v1` (`upstream_group` correlation discounting),
     Laplace-smoothed Good-Turing unseen mass `p_unseen`, `incumbent_dominance_search_v1`
     (`derive_better_than_region`), and `open_world_hypothesis_guard_v4`. Blocks
     premature commitment when local channels agree on low-ceiling actions while
     higher-ceiling `better_than_region` upstream groups remain open, driving
     `target_chase_driver_v1` (`measure != act`) until `measure()` meets `target`.

  4. `WakeSleepConsolidationEngine` (`[G_-, B_+]` + Macro-Abstraction + Kill-Gates):
     Consolidates wake trajectories into `[G_-, B_+]` version-space bounded rules
     (`VerifiedSkillStore` + `rule_scope_learning_v1`), enforces the 2-witness
     non-constant permanence law (`permanence_amplifies_check_v1`), induces reusable
     multi-step macro programs (`executable_skill_program_v7`), falsifies candidate
     checks against `property_v1.mutate` corruptions, and promotes survivors onto the
     `capability_first_scheduler_v1.update_pareto_frontier` System-1 frontier.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
import pathlib
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import capability_first_scheduler_v1 as cfs
from canonical.runtime import compose_v1
from canonical.runtime import continuation_preference_v1 as cpref
from canonical.runtime import environment_learning_v1 as env_learn
from canonical.runtime import executable_skill_program_v7 as esp7
from canonical.runtime import global_retrieval_controller_v1 as grc
from canonical.runtime import ignorance_ledger_v1 as ign_ledger
from canonical.runtime import incumbent_dominance_search_v1 as ids
from canonical.runtime import interaction_v1
from canonical.runtime import mortality_and_triage_v1 as mort
from canonical.runtime import open_world_hypothesis_guard_v4 as owhg
from canonical.runtime import property_v1
from canonical.runtime import self_authored_obligations_v1 as obligations_org
from canonical.runtime import self_prediction_calibration_v1 as spc
from execution_guard import target_chase_driver_v1 as tdriver

SCHEMA = "PROJECT_BRAIN_SENTIENT_COGNITIVE_CORE_V1"

FEATURE_NAMES: tuple[str, ...] = (
    "bias",
    "host_ready",
    "grounding_complete",
    "causal_precond_met",
    "memory_reflex_hit",
    "strong_verifier",
    "missing_dep_or_env_block",
    "nested_cost_or_timeout_risk",
    "family_empirical_pass_centered",
    "family_observation_confidence",
)

# Zero hand-tuned prior weights: `EpistemicSelfBeliefEngine` initializes at exact
# zero-mean isotropic residual `mu_0 = [0.0] * d`, `Sigma_0 = [1.0 / d] * d` over
# Laplace's Rule of Succession (`(1 + n_+) / (2 + n_+ + n_-)`) and deductive
# precondition feasibility, updating `mu_t` online from independently inspected outcomes.
_TWO_SHANNON_BITS_NATS: float = 2.0 * math.log(2.0)


def _atomic_write_json(path: pathlib.Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True, default=str)
    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            delete=False,
        ) as fh:
            tmp_name = fh.name
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
        tmp_name = None
    finally:
        if tmp_name is not None:
            pathlib.Path(tmp_name).unlink(missing_ok=True)


def _sigmoid(z: float) -> float:
    if z >= 35.0:
        return 1.0 - 1e-15
    if z <= -35.0:
        return 1e-15
    return 1.0 / (1.0 + math.exp(-z))


def _binary_entropy(p: float) -> float:
    p_c = min(1.0 - 1e-12, max(1e-12, float(p)))
    return -(p_c * math.log2(p_c) + (1.0 - p_c) * math.log2(1.0 - p_c))


def task_family_key(task_id: str) -> str:
    raw = str(task_id or "general").strip()
    if ":" in raw:
        prefix, rest = raw.split(":", 1)
        tokens = [t for t in rest.replace("/", ".").split(".") if t]
        if len(tokens) >= 2:
            return f"{prefix}:{tokens[0]}.{tokens[1]}"
        return f"{prefix}:{tokens[0]}" if tokens else prefix
    tokens = [t for t in raw.replace("/", ".").split(".") if t]
    if len(tokens) >= 2:
        return f"{tokens[0]}.{tokens[1]}"
    return tokens[0] if tokens else "general"


@dataclass
class PredictionTicket:
    """Pre-action epistemic forecast emitted BEFORE acting and settled ONLY by an independent inspector."""

    task_id: str
    family_key: str
    features: tuple[float, ...]
    predicted_pass_probability: float
    epistemic_variance: float
    predictive_entropy_bits: float
    expected_cost: float
    gain_interval: tuple[float, float]
    expected_latency_ms: float
    calibration_record_id: str | None = None
    feature_map: dict[str, float] = field(default_factory=dict)
    state_task_key: str = ""
    epistemic_mi_bits: float = 0.0
    created_ns: int = field(default_factory=time.perf_counter_ns)


# 5-point Gauss-Hermite quadrature nodes/weights for z = mu + sqrt(2)*sigma*xi
_GH5_NODES: tuple[float, ...] = (-2.0201828705, -0.9585724646, 0.0, 0.9585724646, 2.0201828705)
_GH5_WEIGHTS: tuple[float, ...] = (0.0112574113, 0.2220759220, 0.5333333333, 0.2220759220, 0.0112574113)


def _epistemic_mutual_information_bits(mean_logit: float, epistemic_var: float) -> float:
    """Exact BALD / Friston epistemic mutual information `I(Y; Theta | x) = H(E[sigma(z)]) - E[H(sigma(z))]` in bits.

    Distinguishes reducible epistemic parameter uncertainty (`epistemic_var > 0` -> `I > 0`) from
    irreducible aleatoric noise (`epistemic_var == 0, mean_logit == 0` -> `H(0.5) - H(0.5) == 0.0`!).
    """
    var = max(0.0, float(epistemic_var))
    if var <= 1e-12:
        return 0.0
    scale = math.sqrt(2.0 * var)
    mean_p = 0.0
    expected_cond_h = 0.0
    for xi, wi in zip(_GH5_NODES, _GH5_WEIGHTS):
        p_i = _sigmoid(mean_logit + scale * xi)
        mean_p += wi * p_i
        expected_cond_h += wi * _binary_entropy(p_i)
    return max(0.0, _binary_entropy(min(0.999999, max(1e-6, mean_p))) - expected_cond_h)


def _empirical_mutual_information_bits(xs: Sequence[int], ys: Sequence[int]) -> float:
    """Compute exact Shannon mutual information `I(X; Y)` in bits for binary vectors `xs, ys`."""
    n = len(xs)
    if n < 4 or len(ys) != n:
        return 0.0
    counts = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
    for x, y in zip(xs, ys):
        counts[(1 if x else 0, 1 if y else 0)] += 1
    px1 = (counts[(1, 0)] + counts[(1, 1)]) / n
    py1 = (counts[(0, 1)] + counts[(1, 1)]) / n
    if px1 <= 0.0 or px1 >= 1.0 or py1 <= 0.0 or py1 >= 1.0:
        return 0.0
    px = {0: 1.0 - px1, 1: px1}
    py = {0: 1.0 - py1, 1: py1}
    mi = 0.0
    for bx in (0, 1):
        for by in (0, 1):
            p_xy = counts[(bx, by)] / n
            if p_xy > 0.0:
                mi += p_xy * math.log2(p_xy / (px[bx] * py[by]))
    return max(0.0, mi)


class EpistemicSelfBeliefEngine:
    """Open-ended Bayesian logistic self-model `Theta_t = (Phi_t, mu_t, Sigma_t)` with online predicate invention."""

    def __init__(
        self,
        state_path: pathlib.Path | str | None = None,
        *,
        surprise_threshold: float = _TWO_SHANNON_BITS_NATS,
        process_drift_var: float = 0.0015,
        min_var: float = 0.015,
        max_invented_features: int = 24,
    ) -> None:
        self.state_path = pathlib.Path(state_path) if state_path is not None else None
        self.surprise_threshold = float(surprise_threshold)
        self.process_drift_var = float(process_drift_var)
        self.min_var = float(min_var)
        self.max_invented_features = int(max_invented_features)
        dim = len(FEATURE_NAMES)
        self.feature_names: list[str] = list(FEATURE_NAMES)
        # Specs for invented nonlinear interaction features: name -> {"op": "and"|"and_not"|"xor", "lhs": str, "rhs": str}
        self.invented_specs: dict[str, dict[str, str]] = {}
        self.mu: list[float] = [0.0] * dim
        self.var: list[float] = [1.0 / dim] * dim
        self.family_stats: dict[str, dict[str, float]] = {}
        self.task_stats: dict[str, dict[str, int]] = {}
        self._episode_history: deque[dict[str, Any]] = deque(maxlen=128)
        self.total_updates: int = 0
        self.cumulative_surprise: float = 0.0
        self.last_surprise: float = 0.0
        if self.state_path is not None and self.state_path.is_file():
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            saved_names = data.get("feature_names")
            if (
                isinstance(saved_names, list)
                and len(saved_names) >= len(FEATURE_NAMES)
                and list(saved_names[: len(FEATURE_NAMES)]) == list(FEATURE_NAMES)
                and isinstance(data.get("mu"), list)
                and len(data["mu"]) == len(saved_names)
                and isinstance(data.get("var"), list)
                and len(data["var"]) == len(saved_names)
            ):
                self.feature_names = [str(nm) for nm in saved_names]
                self.mu = [float(v) for v in data["mu"]]
                self.var = [max(self.min_var, float(v)) for v in data["var"]]
            elif isinstance(data.get("mu"), list) and len(data["mu"]) == len(FEATURE_NAMES):
                self.mu = [float(v) for v in data["mu"]]
                if isinstance(data.get("var"), list) and len(data["var"]) == len(FEATURE_NAMES):
                    self.var = [max(self.min_var, float(v)) for v in data["var"]]
            if isinstance(data.get("invented_specs"), Mapping):
                self.invented_specs = {
                    str(k): {str(sk): str(sv) for sk, sv in dict(v).items()}
                    for k, v in data["invented_specs"].items()
                    if isinstance(v, Mapping)
                }
            if isinstance(data.get("family_stats"), Mapping):
                self.family_stats = {
                    str(k): {str(sk): float(sv) for sk, sv in dict(v).items()}
                    for k, v in data["family_stats"].items()
                    if isinstance(v, Mapping)
                }
            if isinstance(data.get("task_stats"), Mapping):
                self.task_stats = {
                    str(k): {"pass": int(v.get("pass", 0)), "fail": int(v.get("fail", 0))}
                    for k, v in data["task_stats"].items()
                    if isinstance(v, Mapping)
                }
            self.total_updates = int(data.get("total_updates") or 0)
            self.cumulative_surprise = float(data.get("cumulative_surprise") or 0.0)
            self.last_surprise = float(data.get("last_surprise") or 0.0)
        except Exception:
            pass

    def save(self) -> None:
        if self.state_path is None:
            return
        _atomic_write_json(
            self.state_path,
            {
                "schema": SCHEMA + "/belief_state",
                "feature_names": list(self.feature_names),
                "invented_specs": dict(self.invented_specs),
                "mu": [round(v, 8) for v in self.mu],
                "var": [round(v, 8) for v in self.var],
                "family_stats": self.family_stats,
                "task_stats": self.task_stats,
                "total_updates": self.total_updates,
                "cumulative_surprise": round(self.cumulative_surprise, 6),
                "last_surprise": round(self.last_surprise, 6),
            },
        )

    def _ensure_feature_slot(self, fname: str, *, init_var: float = 0.35) -> int:
        if fname in self.feature_names:
            return self.feature_names.index(fname)
        self.feature_names.append(fname)
        self.mu.append(0.0)
        self.var.append(float(init_var))
        return len(self.feature_names) - 1

    @staticmethod
    def _eval_interaction(op: str, lv: float, rv: float) -> float:
        """Rademacher bipolar `{-1.0, +1.0}` encoding so one weight symmetrically separates positive & negative truth cells."""
        lb = lv >= 0.5
        rb = rv >= 0.5
        if op == "and":
            return 1.0 if (lb and rb) else -1.0
        if op == "and_not":
            return 1.0 if (lb and not rb) else -1.0
        if op == "xor":
            return 1.0 if (lb != rb) else -1.0
        return 0.0

    def _build_feature_map_and_vector(
        self,
        task_id: str,
        *,
        host_ready: bool = True,
        grounding_complete: bool = True,
        causal_precond_met: bool = True,
        memory_reflex_hit: bool = False,
        strong_verifier: bool = True,
        missing_dep_or_env_block: bool = False,
        nested_cost_or_timeout_risk: bool = False,
        family_override: str | None = None,
        context_predicates: Mapping[str, Any] | None = None,
    ) -> tuple[tuple[float, ...], dict[str, float], str]:
        fam = family_override or task_family_key(task_id)
        st = self.family_stats.get(fam) or {}
        alpha = float(st.get("alpha", 1.0))
        beta = float(st.get("beta", 1.0))
        obs_n = max(0.0, alpha + beta - 2.0)
        emp_rate = alpha / (alpha + beta)
        obs_conf = min(1.0, math.log1p(obs_n) / math.log1p(12.0))
        not_blocked = not missing_dep_or_env_block

        base_vals = (
            1.0,
            1.0 if (host_ready and not_blocked) else 0.0,
            1.0 if (grounding_complete and not_blocked) else 0.0,
            1.0 if (causal_precond_met and not_blocked) else 0.0,
            1.0 if memory_reflex_hit else 0.0,
            1.0 if strong_verifier else 0.0,
            1.0 if missing_dep_or_env_block else 0.0,
            1.0 if nested_cost_or_timeout_risk else 0.0,
            (emp_rate - 0.5) * obs_conf,
            obs_conf,
        )
        fmap: dict[str, float] = {nm: val for nm, val in zip(FEATURE_NAMES, base_vals)}

        ctx_parts: list[str] = []
        if context_predicates:
            for k_raw in sorted(context_predicates.keys()):
                raw_v = context_predicates[k_raw]
                fv = (1.0 if raw_v else 0.0) if isinstance(raw_v, bool) else max(-1.0, min(1.0, float(raw_v)))
                slot_nm = k_raw if str(k_raw).startswith("ctx:") else f"ctx:{k_raw}"
                self._ensure_feature_slot(slot_nm, init_var=0.45)
                fmap[slot_nm] = fv
                ctx_parts.append(f"{slot_nm}={round(fv, 3)}")

        for inv_nm, spec in self.invented_specs.items():
            lv = fmap.get(spec.get("lhs", ""), 0.0)
            rv = fmap.get(spec.get("rhs", ""), 0.0)
            fmap[inv_nm] = self._eval_interaction(spec.get("op", "and"), lv, rv)

        vec = tuple(float(fmap.get(nm, 0.0)) for nm in self.feature_names)
        state_key = f"{task_id}|{'&'.join(ctx_parts)}" if ctx_parts else str(task_id)
        return vec, fmap, state_key

    def build_feature_vector(
        self,
        task_id: str,
        *,
        host_ready: bool = True,
        grounding_complete: bool = True,
        causal_precond_met: bool = True,
        memory_reflex_hit: bool = False,
        strong_verifier: bool = True,
        missing_dep_or_env_block: bool = False,
        nested_cost_or_timeout_risk: bool = False,
        family_override: str | None = None,
        context_predicates: Mapping[str, Any] | None = None,
    ) -> tuple[float, ...]:
        vec, _, _ = self._build_feature_map_and_vector(
            task_id,
            host_ready=host_ready,
            grounding_complete=grounding_complete,
            causal_precond_met=causal_precond_met,
            memory_reflex_hit=memory_reflex_hit,
            strong_verifier=strong_verifier,
            missing_dep_or_env_block=missing_dep_or_env_block,
            nested_cost_or_timeout_risk=nested_cost_or_timeout_risk,
            family_override=family_override,
            context_predicates=context_predicates,
        )
        return vec

    def predict_distribution(
        self,
        task_id: str,
        features: Sequence[float] | None = None,
        **feature_kwargs: Any,
    ) -> dict[str, Any]:
        if features is not None:
            raw_phi = [float(v) for v in features]
            if len(raw_phi) < len(self.mu):
                raw_phi.extend([0.0] * (len(self.mu) - len(raw_phi)))
            phi = tuple(raw_phi)
            if len(phi) != len(self.mu):
                raise ValueError(f"Expected {len(self.mu)} features, got {len(phi)}")
            fmap = {nm: val for nm, val in zip(self.feature_names, phi)}
            state_task_key = str(task_id)
        else:
            phi, fmap, state_task_key = self._build_feature_map_and_vector(task_id, **feature_kwargs)

        violated_necessary = int(phi[1] < 0.5) + int(phi[2] < 0.5) + int(phi[3] < 0.5) + int(phi[6] > 0.5)
        n_pos = sum(1.0 for idx in (1, 2, 3, 4, 5) if phi[idx] >= 0.5)
        n_neg = float(violated_necessary) + (2.0 if phi[7] >= 0.5 else 0.0)
        laplace_base_logit = math.log((1.0 + n_pos) / (1.0 + n_neg))

        learned_residual = sum(m * x for m, x in zip(self.mu, phi))
        mean_logit = laplace_base_logit + learned_residual
        epistemic_var = sum(v * (x * x) for v, x in zip(self.var, phi))
        kappa = 1.0 / math.sqrt(1.0 + (math.pi / 8.0) * max(0.0, epistemic_var))
        p_raw = _sigmoid(kappa * mean_logit)

        tst = self.task_stats.get(state_task_key)
        tp = int((tst or {}).get("pass", 0))
        tf = int((tst or {}).get("fail", 0))
        if violated_necessary > 0 and tp == 0:
            p_raw = min(p_raw, 1.0 / float(len(self.mu) + violated_necessary + tf))
        elif (tp + tf) > 0:
            p_raw = (float(tp) + p_raw) / (float(tp + tf) + 1.0)

        p_hat = min(0.985, max(0.015, p_raw))
        eff_n = 2.0 + n_pos + n_neg + float(tp + tf)
        posterior_std = math.sqrt(max(1e-9, p_hat * (1.0 - p_hat) / eff_n))

        fam = task_family_key(task_id)
        st = self.family_stats.get(fam) or {}
        exp_cost = float(st.get("ema_cost", 1.0))
        mean_gain = float(st.get("ema_gain", 1.0))
        gain_spread = max(0.1, float(st.get("ema_gain_abs_dev", 0.5 * max(1.0, abs(mean_gain)))))
        exp_ms = float(st.get("ema_ms", 5.0))
        ep_mi_bits = _epistemic_mutual_information_bits(mean_logit, epistemic_var)
        return {
            "task_id": task_id,
            "state_task_key": state_task_key,
            "family_key": fam,
            "features": phi,
            "feature_map": fmap,
            "mean_logit": round(mean_logit, 6),
            "epistemic_variance": round(epistemic_var, 6),
            "epistemic_mi_bits": round(ep_mi_bits, 6),
            "epistemic_mi_nats": round(ep_mi_bits * math.log(2.0), 6),
            "posterior_std": round(posterior_std, 6),
            "lower_confidence_bound": round(p_hat - posterior_std, 6),
            "predicted_pass_probability": round(p_hat, 6),
            "predictive_entropy_bits": round(_binary_entropy(p_hat), 6),
            "expected_cost": round(exp_cost, 4),
            "gain_interval": (round(max(0.0, mean_gain - gain_spread), 4), round(mean_gain + gain_spread, 4)),
            "expected_latency_ms": round(exp_ms, 4),
        }

    def predict_probability(
        self,
        task_id: str,
        features: Sequence[float] | None = None,
        **feature_kwargs: Any,
    ) -> float:
        return float(self.predict_distribution(task_id, features=features, **feature_kwargs)["predicted_pass_probability"])

    def predict_before_act(
        self,
        task_id: str,
        *,
        features: Sequence[float] | None = None,
        calibration_ledger: spc.Ledger | None = None,
        claimed_reason: str = "epistemic_kalman_self_belief",
        **feature_kwargs: Any,
    ) -> PredictionTicket:
        dist = self.predict_distribution(task_id, features=features, **feature_kwargs)
        rec_id: str | None = None
        if calibration_ledger is not None:
            rec = calibration_ledger.predict(
                capability_id=task_id,
                predicted_pass_probability=float(dist["predicted_pass_probability"]),
                claimed_reason=claimed_reason,
            )
            rec_id = str(rec["record_id"])
        return PredictionTicket(
            task_id=task_id,
            family_key=str(dist["family_key"]),
            features=tuple(dist["features"]),
            predicted_pass_probability=float(dist["predicted_pass_probability"]),
            epistemic_variance=float(dist["epistemic_variance"]),
            predictive_entropy_bits=float(dist["predictive_entropy_bits"]),
            expected_cost=float(dist["expected_cost"]),
            gain_interval=tuple(dist["gain_interval"]),  # type: ignore[arg-type]
            expected_latency_ms=float(dist["expected_latency_ms"]),
            calibration_record_id=rec_id,
            feature_map=dict(dist.get("feature_map") or {}),
            state_task_key=str(dist.get("state_task_key") or task_id),
            epistemic_mi_bits=float(dist.get("epistemic_mi_bits", 0.0)),
        )

    def _maybe_invent_conjunctive_features(self) -> list[str]:
        """Induce nonlinear interaction features (`and`, `and_not`, `xor`) via empirical Mutual Information `I(C; Y)`."""
        if len(self.invented_specs) >= self.max_invented_features or len(self._episode_history) < 6:
            return []
        recent = list(self._episode_history)
        mean_abs_err = sum(abs(float(ep["residual"])) for ep in recent[-12:]) / float(min(12, len(recent)))
        if mean_abs_err < 0.25:
            return []

        ys = [1 if ep["outcome_pass"] else 0 for ep in recent]
        if len(set(ys)) < 2:
            return []

        # Candidate atomic binary features (prefer dynamic `ctx:*` predicates + core binary flags)
        atomic_candidates = [
            nm
            for nm in self.feature_names
            if nm != "bias"
            and not nm.startswith("int:")
            and nm not in ("family_empirical_pass_centered", "family_observation_confidence")
        ]
        if len(atomic_candidates) < 2:
            return []

        best_mi = 0.0
        best_spec: tuple[str, str, str, str] | None = None
        n_obs = len(recent)
        for i_a, fa in enumerate(atomic_candidates):
            for fb in atomic_candidates[i_a + 1 :]:
                for op in ("xor", "and", "and_not"):
                    cname = f"int:{op}({fa},{fb})"
                    if cname in self.invented_specs:
                        continue
                    xs = [
                        1 if self._eval_interaction(op, float(ep["fmap"].get(fa, 0.0)), float(ep["fmap"].get(fb, 0.0))) >= 0.5 else 0
                        for ep in recent
                    ]
                    mi = _empirical_mutual_information_bits(xs, ys)
                    if mi > best_mi and mi >= 0.20 and (n_obs * mi) >= 1.35:
                        best_mi = mi
                        best_spec = (cname, op, fa, fb)

        if best_spec is None:
            return []

        cname, op, fa, fb = best_spec
        self.invented_specs[cname] = {"op": op, "lhs": fa, "rhs": fb}
        slot_idx = self._ensure_feature_slot(cname, init_var=1.2)
        # Warm-start newly invented feature slot (+ bias) via 3 passes of Laplace-Kalman replay over history
        for _ in range(3):
            for ep in recent:
                fmap_ep = dict(ep["fmap"])
                c_val = self._eval_interaction(op, float(fmap_ep.get(fa, 0.0)), float(fmap_ep.get(fb, 0.0)))
                fmap_ep[cname] = c_val
                y_ep = 1.0 if ep["outcome_pass"] else 0.0
                phi_ep = [float(fmap_ep.get(nm, 0.0)) for nm in self.feature_names]
                viol = int(phi_ep[1] < 0.5) + int(phi_ep[2] < 0.5) + int(phi_ep[3] < 0.5) + int(phi_ep[6] > 0.5)
                np_b = sum(1.0 for idx_b in (1, 2, 3, 4, 5) if phi_ep[idx_b] >= 0.5)
                nn_b = float(viol) + (2.0 if phi_ep[7] >= 0.5 else 0.0)
                base_l = math.log((1.0 + np_b) / (1.0 + nn_b))
                p_ep = _sigmoid(base_l + sum(m * x for m, x in zip(self.mu, phi_ep)))
                innov = y_ep - p_ep
                hw = max(1e-4, p_ep * (1.0 - p_ep))
                for k_idx in (0, slot_idx):
                    xk = phi_ep[k_idx]
                    v_cur = self.var[k_idx] + self.process_drift_var
                    denom = 1.0 + hw * v_cur * (xk * xk)
                    gk = (v_cur * xk) / denom
                    self.mu[k_idx] = max(-8.0, min(8.0, self.mu[k_idx] + gk * innov))
                    self.var[k_idx] = max(self.min_var, min(2.5, v_cur - hw * (gk * gk) * denom))
        return [cname]

    def settle_and_compute_surprise(
        self,
        ticket: PredictionTicket,
        *,
        outcome_pass: bool,
        inspector: str,
        actual_cost: float = 1.0,
        actual_gain: float = 1.0,
        actual_latency_ms: float | None = None,
        calibration_ledger: spc.Ledger | None = None,
        ignorance_ledger_path: pathlib.Path | str | None = None,
    ) -> dict[str, Any]:
        """Settle pre-action prediction via independent `inspector`, compute Surprise `S_t`, and update `(Phi_t, mu_t, Sigma_t)`."""
        if not str(inspector or "").strip():
            raise ValueError("Independent inspector name is required to settle EpistemicSelfBeliefEngine.")
        if calibration_ledger is not None and ticket.calibration_record_id is not None:
            calibration_ledger.settle(
                ticket.calibration_record_id,
                outcome_pass=bool(outcome_pass),
                inspector=str(inspector),
            )

        y = 1.0 if outcome_pass else 0.0
        p_hat = min(0.999999, max(0.000001, float(ticket.predicted_pass_probability)))
        p_assigned = p_hat if outcome_pass else (1.0 - p_hat)
        nll_surprise = -math.log(max(1e-6, p_assigned))
        cost_err = abs(float(actual_cost) - ticket.expected_cost) / (1.0 + max(0.0, ticket.expected_cost))
        lo_g, hi_g = ticket.gain_interval
        gain_outside = 1.0 if (outcome_pass and (actual_gain < lo_g - 1e-6 or actual_gain > hi_g + 1e-6)) else 0.0
        surprise = nll_surprise + 0.35 * cost_err + 0.50 * gain_outside

        # Pad `phi` if new features were invented between `predict_before_act` and `settle`
        raw_phi = list(ticket.features)
        if len(raw_phi) < len(self.mu):
            raw_phi.extend([0.0] * (len(self.mu) - len(raw_phi)))
        phi = tuple(raw_phi[: len(self.mu)])

        hess_w = max(1e-4, p_hat * (1.0 - p_hat))
        proj_var = sum(v * (x * x) for v, x in zip(self.var, phi))
        denom = 1.0 + hess_w * proj_var
        innovation = y - p_hat

        for i in range(len(self.mu)):
            xi = phi[i]
            vi = self.var[i] + self.process_drift_var
            gain_k = (vi * xi) / denom
            self.mu[i] = max(-8.0, min(8.0, self.mu[i] + gain_k * innovation))
            post_v = vi - hess_w * (gain_k * gain_k) * denom
            self.var[i] = max(self.min_var, min(2.5, post_v))

        fmap_hist = dict(ticket.feature_map) if ticket.feature_map else {nm: val for nm, val in zip(self.feature_names, phi)}
        self._episode_history.append(
            {
                "task_id": ticket.task_id,
                "fmap": fmap_hist,
                "outcome_pass": bool(outcome_pass),
                "residual": float(innovation),
            }
        )
        invented_now = self._maybe_invent_conjunctive_features()

        # Update family empirical Beta & EMA trackers
        fam = ticket.family_key
        st = dict(self.family_stats.get(fam) or {"alpha": 1.0, "beta": 1.0, "ema_cost": 1.0, "ema_gain": 1.0, "ema_gain_abs_dev": 0.5, "ema_ms": 5.0})
        if outcome_pass:
            st["alpha"] = float(st.get("alpha", 1.0)) + 1.0
            prev_g = float(st.get("ema_gain", actual_gain))
            st["ema_gain"] = 0.7 * prev_g + 0.3 * float(actual_gain)
            st["ema_gain_abs_dev"] = 0.7 * float(st.get("ema_gain_abs_dev", 0.5)) + 0.3 * abs(float(actual_gain) - prev_g)
        else:
            st["beta"] = float(st.get("beta", 1.0)) + 1.0
        st["ema_cost"] = 0.75 * float(st.get("ema_cost", 1.0)) + 0.25 * max(0.0, float(actual_cost))
        meas_ms = float(actual_latency_ms) if actual_latency_ms is not None else max(0.01, (time.perf_counter_ns() - ticket.created_ns) / 1e6)
        st["ema_ms"] = 0.75 * float(st.get("ema_ms", 5.0)) + 0.25 * meas_ms
        self.family_stats[fam] = st

        state_key = ticket.state_task_key or ticket.task_id
        tst = dict(self.task_stats.get(state_key) or {"pass": 0, "fail": 0})
        if outcome_pass:
            tst["pass"] = int(tst.get("pass", 0)) + 1
        else:
            tst["fail"] = int(tst.get("fail", 0)) + 1
        self.task_stats[state_key] = tst

        self.total_updates += 1
        self.last_surprise = surprise
        self.cumulative_surprise += surprise
        self.save()

        escalate_system2 = bool(surprise > self.surprise_threshold)
        anomaly_gap_id: str | None = None
        if escalate_system2 and ignorance_ledger_path is not None:
            try:
                anomaly_gap_id = str(
                    ign_ledger.note(
                        f"EPISTEMIC_SURPRISE:{ticket.task_id[:72]}",
                        why=f"surprise={surprise:.3f}>threshold={self.surprise_threshold:.3f};pred={p_hat:.3f};outcome={int(outcome_pass)}",
                        cost=max(0.25, float(actual_cost)),
                        path=pathlib.Path(ignorance_ledger_path),
                    )
                )
            except Exception:
                anomaly_gap_id = None

        updated_phi = list(phi)
        if len(updated_phi) < len(self.mu):
            for nm in self.feature_names[len(updated_phi) :]:
                spec = self.invented_specs.get(nm)
                if spec:
                    updated_phi.append(
                        self._eval_interaction(
                            spec["op"],
                            float(fmap_hist.get(spec["lhs"], 0.0)),
                            float(fmap_hist.get(spec["rhs"], 0.0)),
                        )
                    )
                else:
                    updated_phi.append(0.0)

        return {
            "task_id": ticket.task_id,
            "family_key": fam,
            "predicted_pass_probability": round(p_hat, 6),
            "outcome_pass": bool(outcome_pass),
            "surprise": round(surprise, 6),
            "nll_surprise": round(nll_surprise, 6),
            "escalate_to_system2": escalate_system2,
            "escalate_system2": escalate_system2,
            "anomaly_gap_id": anomaly_gap_id,
            "invented_features": invented_now,
            "updated_posterior_probability": round(self.predict_probability(state_key, features=updated_phi), 6),
            "total_updates": self.total_updates,
        }

    def snapshot_digest(self) -> str:
        payload = json.dumps(
            {
                "features": self.feature_names,
                "mu": [round(x, 6) for x in self.mu],
                "var": [round(x, 6) for x in self.var],
                "family": self.family_stats,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class CausalWorldGraph:
    """Live Causal World Model `W_t = (S, A, T_hat, Pre_hat, Prod_hat, Dest_hat)` with pre-execution destroyer inhibition."""

    def __init__(self, state_path: pathlib.Path | str | None = None) -> None:
        self.state_path = pathlib.Path(state_path) if state_path is not None else None
        self.preconditions: dict[str, set[str]] = {}
        self.produces: dict[str, set[str]] = {}
        self.destroys: dict[str, set[str]] = {}
        self.modifies: dict[str, set[str]] = {}
        self.transitions: dict[str, dict[str, str]] = {}
        self.action_attempts: dict[str, int] = {}
        self.action_successes: dict[str, int] = {}
        self._failed_fact_snapshots: dict[str, list[set[str]]] = {}
        self._succeeded_fact_snapshots: dict[str, list[set[str]]] = {}
        if self.state_path is not None and self.state_path.is_file():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.preconditions = {str(k): set(str(x) for x in v) for k, v in (raw.get("preconditions") or {}).items()}
            self.produces = {str(k): set(str(x) for x in v) for k, v in (raw.get("produces") or {}).items()}
            self.destroys = {str(k): set(str(x) for x in v) for k, v in (raw.get("destroys") or {}).items()}
            self.modifies = {str(k): set(str(x) for x in v) for k, v in (raw.get("modifies") or {}).items()}
            self.transitions = {
                str(s): {str(a): str(ns) for a, ns in dict(amap).items()}
                for s, amap in (raw.get("transitions") or {}).items()
                if isinstance(amap, Mapping)
            }
            self.action_attempts = {str(k): int(v) for k, v in (raw.get("action_attempts") or {}).items()}
            self.action_successes = {str(k): int(v) for k, v in (raw.get("action_successes") or {}).items()}
        except Exception:
            pass

    def save(self) -> None:
        if self.state_path is None:
            return
        _atomic_write_json(
            self.state_path,
            {
                "schema": SCHEMA + "/causal_world_graph",
                "preconditions": {k: sorted(v) for k, v in sorted(self.preconditions.items())},
                "produces": {k: sorted(v) for k, v in sorted(self.produces.items())},
                "destroys": {k: sorted(v) for k, v in sorted(self.destroys.items())},
                "modifies": {k: sorted(v) for k, v in sorted(self.modifies.items())},
                "transitions": self.transitions,
                "action_attempts": self.action_attempts,
                "action_successes": self.action_successes,
            },
        )

    @staticmethod
    def predicate_tokens(state_obs: Any) -> set[str]:
        """Extract canonical ground fact tokens from a workspace path, dict, or set of facts."""
        if isinstance(state_obs, (set, frozenset, list, tuple)):
            return {str(x) for x in state_obs}
        if isinstance(state_obs, Mapping):
            out: set[str] = set()
            for k, v in state_obs.items():
                if isinstance(v, bool):
                    if v:
                        out.add(str(k))
                elif isinstance(v, (set, frozenset, list, tuple)):
                    for item in v:
                        out.add(f"{k}:{item}" if k != "files" and k != "facts" else str(item))
                elif v is not None and v != "":
                    out.add(f"{k}={v}")
            return out
        if isinstance(state_obs, (str, pathlib.Path)):
            p = pathlib.Path(state_obs)
            if p.is_dir():
                return {
                    f.relative_to(p).as_posix()
                    for f in p.rglob("*")
                    if f.is_file() and ".git" not in f.parts
                }
        return {env_learn.state_key(state_obs)}

    def classify_effect_polarity(self, action_id: str) -> str:
        """Pre-execution `(Read, Write, Destroy)` effect polarity."""
        dest = self.destroys.get(action_id) or set()
        prod = self.produces.get(action_id) or set()
        mod = self.modifies.get(action_id) or set()
        if dest:
            return "DESTRUCTIVE_MUTATION"
        if prod or mod:
            return "CONSTRUCTIVE_WRITE"
        if self.action_attempts.get(action_id, 0) == 0:
            return "UNKNOWN_UNPROBED"
        return "PURE_PROBE"

    def action_polarity(self, action_id: str) -> str:
        """Human-readable effect polarity (`IRREVERSIBLE_DESTRUCTIVE` | `STATE_MUTATING` | `PURE_OBSERVATION`)."""
        pol = self.classify_effect_polarity(action_id)
        if pol == "DESTRUCTIVE_MUTATION":
            return "IRREVERSIBLE_DESTRUCTIVE"
        if pol == "CONSTRUCTIVE_WRITE":
            return "STATE_MUTATING"
        return "PURE_OBSERVATION"

    def learn_from_execution(
        self,
        action_id: str,
        *,
        before_state: Any,
        after_state: Any,
        ok: bool,
        error_text: str = "",
    ) -> dict[str, Any]:
        """Online causal transition & precondition learning (`environment_learning_v1` + `interaction_v1` + `compose_v1`)."""
        aid = str(action_id)
        before_facts = self.predicate_tokens(before_state)
        after_facts = self.predicate_tokens(after_state)
        s_before = "|".join(sorted(before_facts)) or "__EMPTY__"
        s_after = "|".join(sorted(after_facts)) or "__EMPTY__"

        self.action_attempts[aid] = self.action_attempts.get(aid, 0) + 1
        if ok:
            self.action_successes[aid] = self.action_successes.get(aid, 0) + 1
            self._succeeded_fact_snapshots.setdefault(aid, []).append(set(before_facts))
        else:
            self._failed_fact_snapshots.setdefault(aid, []).append(set(before_facts))
        self.transitions.setdefault(s_before, {})[aid] = s_after

        created = after_facts - before_facts
        removed = before_facts - after_facts
        if created:
            self.produces.setdefault(aid, set()).update(created)
        if removed:
            self.destroys.setdefault(aid, set()).update(removed)

        # Contrastive Pearl intervention precondition discovery (works even when stderr is completely silent!):
        # facts present in every observed passing pre-state and absent in observed failing pre-states.
        succ_snaps = self._succeeded_fact_snapshots.get(aid) or []
        fail_snaps = self._failed_fact_snapshots.get(aid) or []
        if succ_snaps and fail_snaps:
            common_pass = set.intersection(*succ_snaps)
            contrastive_pre = {f for f in common_pass if all(f not in fs for fs in fail_snaps)}
            if contrastive_pre:
                self.preconditions[aid] = contrastive_pre

        # Extract missing preconditions from failure complaint (`compose_v1.missing_from_error`)
        inferred_missing: set[str] = set()
        if not ok and error_text:
            for tok in compose_v1.missing_from_error(str(error_text)):
                clean_tok = str(tok).strip().strip("'\"")
                if clean_tok:
                    inferred_missing.add(clean_tok)
            # Also match explicit `MISSING:<fact>` or `FileNotFoundError: <path>` tokens
            for raw_part in str(error_text).replace(":", " ").replace("'", " ").replace('"', " ").split():
                if "." in raw_part or "/" in raw_part or raw_part.startswith("fact_"):
                    if raw_part not in before_facts and len(raw_part) <= 96:
                        inferred_missing.add(raw_part)
            if inferred_missing:
                self.preconditions.setdefault(aid, set()).update(inferred_missing)

        # When an action succeeds ONLY after certain facts exist compared to an earlier failed state, intersect!
        if ok and aid in self.preconditions:
            # Keep only preconditions actually present in `before_facts` (prevents spurious tokens)
            verified_pre = {p for p in self.preconditions[aid] if p in before_facts or any(bf.endswith(p) for bf in before_facts)}
            if verified_pre:
                self.preconditions[aid] = verified_pre

        self.save()
        return {
            "action_id": aid,
            "created": sorted(created),
            "destroyed": sorted(removed),
            "inferred_preconditions": sorted(self.preconditions.get(aid) or ()),
            "polarity": self.classify_effect_polarity(aid),
        }

    def ingest_workspace_interaction_probe(self, root: str | pathlib.Path, commands: Sequence[Sequence[str]]) -> dict[str, Any]:
        """Run `interaction_v1.analyze` two-phase probing on a workspace and fuse its causal graph into `W_t`."""
        cmd_list = [[str(tok) for tok in cmd] for cmd in commands]
        rep = interaction_v1.analyze(str(root), cmd_list, two_phase=True)
        for row in rep.get("actions") or []:
            aid = " ".join(str(x) for x in (row.get("command") or []))
            if not aid:
                continue
            self.action_attempts[aid] = self.action_attempts.get(aid, 0) + 1
            if row.get("exit_code") == 0:
                self.action_successes[aid] = self.action_successes.get(aid, 0) + 1
            for f in row.get("produces") or []:
                self.produces.setdefault(aid, set()).add(str(f))
            for f in row.get("destroys") or []:
                self.destroys.setdefault(aid, set()).add(str(f))
            for f in row.get("modifies") or []:
                self.modifies.setdefault(aid, set()).add(str(f))
        self.save()
        return rep

    def should_inhibit_action(self, action_id: str, *, current_facts: set[str], protected_facts: set[str]) -> tuple[bool, str | None]:
        """Inhibit destroyer actions BEFORE execution if they destroy any currently held protected/subgoal fact."""
        dest = self.destroys.get(action_id) or set()
        clobbered = dest & current_facts & protected_facts
        if clobbered:
            return True, f"DESTROYER_INHIBITED:{','.join(sorted(clobbered))}"
        return False, None

    def plan_minimal_causal_chain(
        self,
        *,
        initial_facts: set[str],
        goal_facts: set[str],
        candidate_actions: Sequence[str],
        max_depth: int = 8,
    ) -> list[str] | None:
        """Shortest-path BFS over learned `(Pre_hat, Prod_hat, Dest_hat)` with automatic destroyer inhibition."""
        if goal_facts.issubset(initial_facts):
            return []

        # Collect all transitive subgoal facts that matter so destroyers of subgoals are inhibited
        protected = set(goal_facts)
        for _ in range(len(candidate_actions)):
            added = False
            for aid in candidate_actions:
                prod = self.produces.get(aid) or set()
                if prod & protected:
                    pre = self.preconditions.get(aid) or set()
                    if not pre.issubset(protected):
                        protected |= pre
                        added = True
            if not added:
                break

        start = frozenset(initial_facts)
        queue: deque[tuple[frozenset[str], list[str]]] = deque([(start, [])])
        visited: set[frozenset[str]] = {start}

        while queue:
            cur_facts, path = queue.popleft()
            if len(path) >= max_depth:
                continue
            for aid in candidate_actions:
                inhibited, _ = self.should_inhibit_action(aid, current_facts=set(cur_facts), protected_facts=protected)
                if inhibited:
                    continue
                pre = self.preconditions.get(aid) or set()
                if not all(p in cur_facts or any(cf.endswith(p) for cf in cur_facts) for p in pre):
                    continue
                prod = self.produces.get(aid) or set()
                dest = self.destroys.get(aid) or set()
                if not prod:
                    continue
                nxt = frozenset((set(cur_facts) | prod) - dest)
                if nxt == cur_facts:
                    continue
                new_path = path + [aid]
                if goal_facts.issubset(nxt):
                    return new_path
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, new_path))
        return None

    def plan_precondition_chain(
        self,
        *,
        current_state: Any,
        goal_predicate: str,
        candidate_actions: Sequence[str] | None = None,
        max_depth: int = 8,
    ) -> list[str] | None:
        """Backward/BFS causal precondition chain planner over learned `W_t` with automatic destroyer inhibition."""
        cands = list(candidate_actions) if candidate_actions is not None else sorted(self.action_attempts.keys())
        return self.plan_minimal_causal_chain(
            initial_facts=self.predicate_tokens(current_state),
            goal_facts={str(goal_predicate)},
            candidate_actions=cands,
            max_depth=max_depth,
        )

    def discover_and_achieve_goal(
        self,
        *,
        observe: Callable[[], set[str]],
        act: Callable[[str], Mapping[str, Any]],
        actions: Sequence[str],
        goal_facts: set[str],
        reset_or_snapshot: Callable[[], Any] | None = None,
        restore: Callable[[Any], None] | None = None,
        budget: int = 24,
    ) -> dict[str, Any]:
        """Zero-prior causal world discovery & goal achievement:
        1. Probes unknown actions cleanly (using snapshot/restore when available, or non-destructive curiosity order),
           learning `produces(a)`, `destroys(a)` (including built-state destroyer detection!), and `preconditions(a)`
           from `compose_v1` error complaints;
        2. Synthesizes the shortest destroyer-free causal chain `plan_minimal_causal_chain`;
        3. Executes the minimal plan to achieve `goal_facts` without triggering hidden destroyers.
        """
        steps_used = 0
        trajectory: list[dict[str, Any]] = []
        action_list = [str(a) for a in actions]

        while steps_used < budget:
            cur_facts = set(observe())
            if goal_facts.issubset(cur_facts):
                return {
                    "pass": True,
                    "status": "GOAL_ACHIEVED",
                    "steps_used": steps_used,
                    "final_facts": sorted(cur_facts),
                    "learned_produces": {k: sorted(v) for k, v in self.produces.items() if v},
                    "learned_destroys": {k: sorted(v) for k, v in self.destroys.items() if v},
                    "learned_preconditions": {k: sorted(v) for k, v in self.preconditions.items() if v},
                    "trajectory": trajectory,
                }

            plan = self.plan_minimal_causal_chain(
                initial_facts=cur_facts,
                goal_facts=goal_facts,
                candidate_actions=action_list,
            )
            if plan:
                next_action = plan[0]
            else:
                # Epistemic exploration: prefer unprobed actions first, then actions whose preconditions are newly met!
                protected = set(goal_facts)
                for pre_s in self.preconditions.values():
                    protected |= pre_s
                candidates_ranked: list[tuple[int, int, str]] = []
                for idx_a, aid in enumerate(action_list):
                    inhibited, _ = self.should_inhibit_action(
                        aid,
                        current_facts=cur_facts,
                        protected_facts=protected | cur_facts if (self.destroys.get(aid) and len(cur_facts) > 0) else protected,
                    )
                    if inhibited:
                        continue
                    att = self.action_attempts.get(aid, 0)
                    pre = self.preconditions.get(aid) or set()
                    pre_met = all(p in cur_facts or any(cf.endswith(p) for cf in cur_facts) for p in pre)
                    # Priority 0: never probed; Priority 1: previously failed before preconditions existed, now preconditions ARE met!
                    if att == 0:
                        prio = 0
                    elif pre and pre_met and self.action_successes.get(aid, 0) == 0:
                        prio = 1
                    elif not (self.destroys.get(aid)):
                        prio = 2 + att
                    else:
                        prio = 100 + att
                    candidates_ranked.append((prio, idx_a, aid))
                if not candidates_ranked:
                    break
                candidates_ranked.sort()
                next_action = candidates_ranked[0][2]

            snap = reset_or_snapshot() if reset_or_snapshot is not None else None
            out = dict(act(next_action) or {})
            steps_used += 1
            after_facts = set(observe())
            ok = bool(out.get("ok", out.get("pass", True)) and not out.get("error"))
            err = str(out.get("error") or "")
            learned = self.learn_from_execution(
                next_action,
                before_state=cur_facts,
                after_state=after_facts,
                ok=ok,
                error_text=err,
            )
            # If exploratory action unexpectedly destroyed existing facts and snapshot restore is available, restore immediately!
            if learned["destroyed"] and restore is not None and snap is not None and not goal_facts.issubset(after_facts):
                restore(snap)
                after_facts = set(observe())
                learned["restored_after_destroyer_discovery"] = True
            trajectory.append(
                {
                    "step": steps_used,
                    "action": next_action,
                    "ok": ok,
                    "error": err,
                    "after_facts": sorted(after_facts),
                    "learned": learned,
                }
            )

        final_facts = set(observe())
        return {
            "pass": goal_facts.issubset(final_facts),
            "status": "GOAL_ACHIEVED" if goal_facts.issubset(final_facts) else "BUDGET_EXHAUSTED",
            "steps_used": steps_used,
            "final_facts": sorted(final_facts),
            "learned_produces": {k: sorted(v) for k, v in self.produces.items() if v},
            "learned_destroys": {k: sorted(v) for k, v in self.destroys.items() if v},
            "learned_preconditions": {k: sorted(v) for k, v in self.preconditions.items() if v},
            "trajectory": trajectory,
        }


class GlobalVoIDominanceController:
    """Information-Theoretic Stopping, Good-Turing Unseen Mass, and `incumbent_dominance_search_v1` Extrapolation."""

    @staticmethod
    def good_turing_unseen_mass(
        observations: Sequence[Mapping[str, Any]],
        *,
        probed_upstream_groups: Sequence[str],
        unprobed_upstream_groups: Sequence[str],
    ) -> float:
        """Laplace-smoothed Good-Turing unseen mass over independent `upstream_group` clusters."""
        g_probed = len({str(g).casefold() for g in probed_upstream_groups if str(g).strip()})
        g_unprobed = len({str(g).casefold() for g in unprobed_upstream_groups if str(g).strip()})
        if g_probed == 0:
            return 1.0
        if g_unprobed == 0:
            return 0.0

        groups_by_family: dict[str, set[str]] = {}
        for obs in observations:
            fam = str(obs.get("mechanism_family") or obs.get("route_id") or obs.get("id") or "").strip()
            grp = str(obs.get("upstream_group") or obs.get("source_id") or "local").strip().casefold()
            if fam:
                groups_by_family.setdefault(fam, set()).add(grp)

        n_obs = sum(len(gs) for gs in groups_by_family.values())
        f1_singletons = sum(1 for gs in groups_by_family.values() if len(gs) == 1)
        unseen_est = (f1_singletons + 1.0) / (n_obs + g_probed + 1.0)
        unseen_fraction_groups = g_unprobed / float(g_probed + g_unprobed)
        return round(min(1.0, max(unseen_est, 0.5 * unseen_fraction_groups)), 6)

    @classmethod
    def evaluate_stopping_and_voi(
        cls,
        *,
        goal: str,
        target_delta: float,
        direction: str = "maximize",
        known_options: Sequence[Mapping[str, Any]],
        channels: Sequence[Mapping[str, Any]],
        probed_source_ids: set[str],
        max_feasible_horizon: float = 20.0,
        coverage_receipt: Mapping[str, Any] | None = None,
        residual_action_receipt: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Decide whether current verified options suffice or whether `YOUTUBE_LOCAL_OPTIMUM_TRAP_BLOCKED` requires orthogonal discovery."""
        verified_opts = [
            dict(o)
            for o in known_options
            if isinstance(o, Mapping)
            and (o.get("independently_verified_by") or o.get("candidate_authority") == "VERIFIED")
            and o.get("effect_polarity") != "DESTRUCTIVE_INHIBITED"
        ]

        probed_groups = sorted(
            {
                str(c.get("upstream_group") or c.get("source_id") or "").strip()
                for c in channels
                if str(c.get("source_id") or "").strip() in probed_source_ids
            }
            | {
                str(o.get("upstream_group") or o.get("source_id") or "").strip()
                for o in verified_opts
                if str(o.get("upstream_group") or o.get("source_id") or "").strip()
            }
        )
        unprobed_channels = [
            dict(c)
            for c in channels
            if str(c.get("source_id") or "").strip()
            and str(c.get("source_id") or "").strip() not in probed_source_ids
            and str(c.get("upstream_group") or c.get("source_id") or "").strip().casefold()
            not in {g.casefold() for g in probed_groups}
        ]
        unprobed_groups = sorted(
            {str(c.get("upstream_group") or c.get("source_id") or "").strip() for c in unprobed_channels}
        )

        p_unseen = cls.good_turing_unseen_mass(
            verified_opts,
            probed_upstream_groups=probed_groups,
            unprobed_upstream_groups=unprobed_groups,
        )

        # Compute incumbent performance vector & ceiling adequacy
        best_opt: dict[str, Any] | None = None
        best_rate = -1.0
        total_nonexhausted_ceiling = 0.0
        for o in verified_opts:
            gain = abs(float(o.get("expected_gain", o.get("verified_yield", 0.0)) or 0.0))
            cost = max(0.05, float(o.get("action_cost", 1.0) or 1.0))
            repeatable_cap = float(o.get("max_total_yield", o.get("ceiling_yield", gain)) or gain)
            if not o.get("exhausted"):
                total_nonexhausted_ceiling += repeatable_cap
            rate = gain / cost
            if rate > best_rate:
                best_rate = rate
                best_opt = o

        best_gain = abs(float((best_opt or {}).get("expected_gain", (best_opt or {}).get("verified_yield", 0.0)) or 0.0))
        incumbent_horizon = (
            (target_delta / max(1e-6, best_rate))
            if best_rate > 0 and target_delta > 0
            else (0.0 if target_delta <= 0 else float("inf"))
        )
        ceiling_shortfall = target_delta > 0 and total_nonexhausted_ceiling + 1e-9 < target_delta
        horizon_infeasible = target_delta > 0 and incumbent_horizon > max_feasible_horizon

        # Build `incumbent_dominance_search_v1` evaluation over unprobed orthogonal regions!
        dominance_verdict: dict[str, Any] | None = None
        better_than_region: dict[str, Any] | None = None
        channel_voi_ranking: list[dict[str, Any]] = []

        if best_opt is not None:
            best_cost = max(0.05, float(best_opt.get("action_cost", 1.0) or 1.0))
            contract_sha = hashlib.sha256(str(goal).encode("utf-8")).hexdigest()
            inc_spec = {
                "candidate_id": str(best_opt.get("route_id") or best_opt.get("id") or "incumbent"),
                "independently_verified": True,
                "semantic_contract_sha256": contract_sha,
                "capability": round(best_gain, 6),
                "generalization": 1,
                "reliability": 1,
                "latency": round(best_cost, 6),
                "compute": round(best_cost, 6),
                "memory": 1,
                "incremental_spend_usd": 0,
            }
            better_than_region = ids.derive_better_than_region(inc_spec)
            cand_regions: list[dict[str, Any]] = []
            for ch in unprobed_channels:
                sid = str(ch.get("source_id") or "")
                grp = str(ch.get("upstream_group") or sid)
                raw_ub = ch.get("yield_upper_bound", ch.get("max_potential_gain"))
                explicit_ub = isinstance(raw_ub, (int, float)) and not isinstance(raw_ub, bool)
                ub = float(raw_ub) if explicit_ub else max(target_delta, best_gain)
                q_cost = max(0.05, float(ch.get("probe_cost", 1.0) or 1.0))
                can_dom = (ub > best_gain) if explicit_ub else bool(ceiling_shortfall or horizon_infeasible)
                cand_regions.append(
                    {
                        "region_id": f"group:{grp}:{sid}",
                        "status": "OPEN" if can_dom else "UPPER_BOUND_ELIMINATED",
                        "independent_bound_proof": not can_dom,
                    }
                )
                ub_rate = ub / q_cost
                h_current = min(1e6, incumbent_horizon) if math.isfinite(incumbent_horizon) else 1e4
                h_after = (target_delta / max(1e-6, ub_rate)) if target_delta > 0 and ub_rate > 0 else h_current
                p_dom = p_unseen if can_dom else 0.0
                voi = p_dom * max(0.0, h_current - h_after) + p_unseen * max(0.0, ub - best_gain) * 0.01
                channel_voi_ranking.append(
                    {
                        "source_id": sid,
                        "upstream_group": grp,
                        "yield_upper_bound": ub,
                        "explicit_upper_bound": explicit_ub,
                        "probe_cost": q_cost,
                        "voi_net": round(voi - q_cost, 6),
                        "voi": round(voi, 6),
                        "can_dominate_incumbent": can_dom,
                    }
                )
            need_opt = bool(ceiling_shortfall or horizon_infeasible or any(r["can_dominate_incumbent"] and r["voi_net"] > 0 for r in channel_voi_ranking))
            try:
                dominance_verdict = ids.evaluate(
                    incumbent=inc_spec,
                    candidate_regions=cand_regions,
                    candidate_family_cover_complete=(len(unprobed_channels) == 0),
                    family_cover_independently_verified=(coverage_receipt is not None or len(unprobed_channels) == 0),
                    explicit_sufficiency_contract={"goal_ceiling_met": True} if not need_opt else None,
                    optimality_required=need_opt,
                )
            except ids.SearchControlError:
                dominance_verdict = None
        else:
            for ch in unprobed_channels:
                sid = str(ch.get("source_id") or "")
                grp = str(ch.get("upstream_group") or sid)
                ub = float(ch.get("yield_upper_bound", ch.get("max_potential_gain", max(1.0, target_delta))) or 1.0)
                q_cost = max(0.05, float(ch.get("probe_cost", 1.0) or 1.0))
                channel_voi_ranking.append(
                    {
                        "source_id": sid,
                        "upstream_group": grp,
                        "yield_upper_bound": ub,
                        "probe_cost": q_cost,
                        "voi_net": round(ub / q_cost - q_cost, 6),
                        "voi": round(ub / q_cost, 6),
                        "can_dominate_incumbent": True,
                    }
                )

        channel_voi_ranking.sort(key=lambda r: (-float(r["voi_net"]), -float(r["yield_upper_bound"]), str(r["source_id"])))

        # Open-world hypothesis guard check
        ow_closed = False
        if verified_opts and (coverage_receipt is not None or residual_action_receipt is not None):
            try:
                hyps = [
                    {
                        "id": str(o.get("route_id") or o.get("id") or f"h_{i}"),
                        "plausible": True,
                        "best_action": str(o.get("route_id") or o.get("id") or f"a_{i}"),
                    }
                    for i, o in enumerate(verified_opts)
                ]
                ow_verdict = owhg.decision_sufficient(
                    environment_id="sentient_core_world",
                    goal_id="goal:" + hashlib.sha256(goal.encode("utf-8")).hexdigest()[:12],
                    hypotheses=hyps,
                    coverage_receipt=coverage_receipt,
                    residual_action_receipt=residual_action_receipt,
                )
                ow_closed = bool(ow_verdict.get("open_world_safe"))
            except Exception:
                ow_closed = False

        blockers: list[str] = []
        if not verified_opts and unprobed_channels:
            blockers.append("NO_VERIFIED_OPTIONS_YET_ORTHOGONAL_CHANNELS_OPEN")
        if (ceiling_shortfall or horizon_infeasible) and unprobed_channels and not ow_closed:
            blockers.append(
                f"YOUTUBE_LOCAL_OPTIMUM_TRAP_BLOCKED:ceiling={total_nonexhausted_ceiling:.2f}<target_delta={target_delta:.2f}"
            )
        for r in channel_voi_ranking:
            if r["can_dominate_incumbent"] and (r["voi_net"] > 0 or ceiling_shortfall or horizon_infeasible) and not ow_closed:
                blockers.append(f"BETTER_THAN_REGION_OPEN:{r['upstream_group']}:{r['source_id']}")

        return {
            "complete": len(blockers) == 0,
            "blockers": blockers,
            "good_turing_p_unseen": p_unseen,
            "probed_upstream_groups": probed_groups,
            "unprobed_upstream_groups": unprobed_groups,
            "total_nonexhausted_ceiling": round(total_nonexhausted_ceiling, 4),
            "target_delta": round(target_delta, 4),
            "ceiling_shortfall": ceiling_shortfall,
            "incumbent_horizon": round(incumbent_horizon, 4) if math.isfinite(incumbent_horizon) else None,
            "better_than_region": better_than_region,
            "dominance_verdict": dominance_verdict,
            "channel_voi_ranking": channel_voi_ranking,
            "open_world_guard_closed": ow_closed,
        }


class WakeSleepConsolidationEngine:
    """Wake-Sleep Consolidation (`[G_-, B_+]` version space + 2-witness permanence + macro induction + Pareto frontier)."""

    def __init__(self, state_path: pathlib.Path | str | None = None) -> None:
        self.state_path = pathlib.Path(state_path) if state_path is not None else None
        self.wake_buffer: list[dict[str, Any]] = []
        self.pareto_frontier: list[dict[str, Any]] = []
        self.induced_macros: dict[str, dict[str, Any]] = {}
        self.sleep_cycles: int = 0
        if self.state_path is not None and self.state_path.is_file():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.wake_buffer = [dict(x) for x in (raw.get("wake_buffer") or []) if isinstance(x, Mapping)]
            self.pareto_frontier = [dict(x) for x in (raw.get("pareto_frontier") or []) if isinstance(x, Mapping)]
            self.induced_macros = {
                str(k): dict(v) for k, v in (raw.get("induced_macros") or {}).items() if isinstance(v, Mapping)
            }
            self.sleep_cycles = int(raw.get("sleep_cycles") or 0)
        except Exception:
            pass

    def save(self) -> None:
        if self.state_path is None:
            return
        _atomic_write_json(
            self.state_path,
            {
                "schema": SCHEMA + "/wake_sleep_consolidation",
                "sleep_cycles": self.sleep_cycles,
                "wake_buffer_len": len(self.wake_buffer),
                "wake_buffer": self.wake_buffer[-64:],
                "pareto_frontier": self.pareto_frontier,
                "induced_macros": self.induced_macros,
            },
        )

    def record_wake_episode(
        self,
        *,
        episode_id: str,
        family: str,
        before_code: str = "",
        after_code: str = "",
        language: str = "python",
        error_class: str = "GENERAL_REPAIR",
        steps: Sequence[Mapping[str, Any]] = (),
        preconditions: Sequence[str] = (),
        postconditions: Sequence[str] = (),
        witness_input_sig: str = "",
        witness_output_sig: str = "",
        verified_by_test_suite: bool = True,
        cost_ms: float = 1.0,
    ) -> dict[str, Any]:
        ep = {
            "episode_id": str(episode_id),
            "family": str(family),
            "before_code": str(before_code),
            "after_code": str(after_code),
            "language": str(language),
            "error_class": str(error_class),
            "steps": [dict(s) for s in steps],
            "preconditions": [str(p) for p in preconditions],
            "postconditions": [str(p) for p in postconditions],
            "witness_input_sig": str(witness_input_sig or hashlib.sha256(before_code.encode("utf-8")).hexdigest()[:12]),
            "witness_output_sig": str(witness_output_sig or hashlib.sha256(after_code.encode("utf-8")).hexdigest()[:12]),
            "verified_by_test_suite": bool(verified_by_test_suite),
            "cost_ms": float(cost_ms),
            "consolidated": False,
        }
        self.wake_buffer.append(ep)
        self.save()
        return ep

    @staticmethod
    def verify_two_witness_nonconstant(episodes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """Enforce `permanence_amplifies_check_v1`: >= 2 distinct inputs AND >= 2 distinct outputs."""
        distinct_in = {str(e.get("witness_input_sig") or "") for e in episodes if str(e.get("witness_input_sig") or "")}
        distinct_out = {str(e.get("witness_output_sig") or "") for e in episodes if str(e.get("witness_output_sig") or "")}
        passed = len(distinct_in) >= 2 and len(distinct_out) >= 2
        return {
            "passed": passed,
            "distinct_inputs": len(distinct_in),
            "distinct_outputs": len(distinct_out),
            "reason": "NON_CONSTANT_2_WITNESS_VERIFIED" if passed else "INSUFFICIENT_NONCONSTANT_WITNESSES",
        }

    def sleep_consolidate(
        self,
        *,
        skill_store: Any = None,
        calibrate_scopes: bool = True,
    ) -> dict[str, Any]:
        """Execute one offline Sleep consolidation cycle:
        1. Group unconsolidated `TEST_SUITE`-verified wake episodes by `(family, error_class)`;
        2. Enforce 2-witness non-constant permanence (`permanence_amplifies_check_v1`) for permanent promotion;
        3. Crystallize `[G_-, B_+]` version-space bounded rules into `VerifiedSkillStore` (`G_-` context-anchored
           stored representation; `B_+` calibrated via confined behavioral probes in `rule_scope_learning_v1`
           and unlocked ONLY under `TEST_SUITE` verification);
        4. Induce multi-step skill programs (`executable_skill_program_v7.induce_candidate`) across >= 2 episodes;
        5. Promote non-dominated skills onto `capability_first_scheduler_v1.update_pareto_frontier`.
        """
        from canonical.swe_kernel import rule_scope_learning_v1 as rscope

        pending = [e for e in self.wake_buffer if not e.get("consolidated") and e.get("verified_by_test_suite")]
        by_family: dict[str, list[dict[str, Any]]] = {}
        for ep in self.wake_buffer:
            if ep.get("verified_by_test_suite"):
                by_family.setdefault(str(ep["family"]), []).append(ep)

        crystallized_rules: list[dict[str, Any]] = []
        promoted_macros: list[dict[str, Any]] = []
        withheld_single_witness: list[str] = []

        for fam, fam_eps in sorted(by_family.items()):
            perm = self.verify_two_witness_nonconstant(fam_eps)
            if not perm["passed"]:
                withheld_single_witness.append(fam)
                continue

            # 1. Crystallize & calibrate `[G_-, B_+]` code-transform skills when code snippets exist
            if skill_store is not None:
                for ep in fam_eps:
                    if ep.get("consolidated"):
                        continue
                    b_code = str(ep.get("before_code") or "")
                    a_code = str(ep.get("after_code") or "")
                    if b_code and a_code and b_code != a_code:
                        c_res = skill_store.crystallize_code_fix(
                            before_snippet=b_code,
                            after_snippet=a_code,
                            language=str(ep.get("language") or "python"),
                            error_class=str(ep.get("error_class") or fam),
                        )
                        if c_res.get("crystallized") and c_res.get("skill_id"):
                            sid = str(c_res["skill_id"])
                            cal_scope: str | None = None
                            if calibrate_scopes and str(ep.get("language") or "python") == "python":
                                rules = [
                                    r for r in skill_store.lookup_rules("python")
                                    if str(r.get("skill_id")) == sid
                                ]
                                if rules:
                                    cal = rscope.calibrate_rule_scope(rules[0], store=skill_store)
                                    cal_scope = cal.get("effective_scope") or cal.get("scope")
                            if hasattr(skill_store, "record_permanence_witnesses"):
                                skill_store.record_permanence_witnesses(
                                    sid,
                                    distinct_inputs=perm["distinct_inputs"],
                                    distinct_outputs=perm["distinct_outputs"],
                                )
                            crystallized_rules.append(
                                {
                                    "skill_id": sid,
                                    "family": fam,
                                    "narrow_g_minus": "SCOPE_STATEMENT",
                                    "broad_b_plus": cal_scope or "SCOPE_STATEMENT",
                                    "b_plus_requires": "TEST_SUITE",
                                    "witnesses": perm,
                                }
                            )

            # 2. Induce multi-step `executable_skill_program_v7` macro across >= 2 verified step traces
            step_eps = [
                {
                    "episode_id": str(ep["episode_id"]),
                    "verified": True,
                    "steps": ep["steps"],
                    "preconditions": ep.get("preconditions") or ["workspace_present"],
                    "postconditions": ep.get("postconditions") or [f"resolved:{fam}"],
                    "invalidators": ["verifier_failed"],
                }
                for ep in fam_eps
                if ep.get("steps")
            ]
            if len(step_eps) >= 2:
                try:
                    induced = esp7.induce_candidate(step_eps)
                    macro_id = f"macro:{fam}:{induced['candidate_sha256'][:12]}"
                    self.induced_macros[fam] = {
                        "macro_id": macro_id,
                        "family": fam,
                        "candidate": induced,
                        "witnesses": perm,
                    }
                    promoted_macros.append(self.induced_macros[fam])
                except Exception:
                    pass

            # 3. Update Pareto capability frontier (`capability_first_scheduler_v1.update_pareto_frontier`)
            avg_ms = sum(float(e.get("cost_ms") or 1.0) for e in fam_eps) / max(1, len(fam_eps))
            cand_frontier_item = {
                "id": f"consolidated:{fam}",
                "generality": len(fam_eps),
                "verified_transfer_domains": perm["distinct_inputs"],
                "verification_strength": 2,
                "cost": max(1, int(round(avg_ms))),
                "risk": 0,
            }
            try:
                upd = cfs.update_pareto_frontier(self.pareto_frontier, cand_frontier_item)
                if upd.get("admitted"):
                    self.pareto_frontier = list(upd.get("frontier") or self.pareto_frontier)
            except Exception:
                pass

            for ep in fam_eps:
                ep["consolidated"] = True

        self.sleep_cycles += 1
        calibrated_existing: list[dict[str, Any]] = []
        if calibrate_scopes and skill_store is not None:
            for r in skill_store.lookup_rules("python"):
                if r.get("state") not in (None, "ACTIVE") or r.get("learned_scope"):
                    continue
                cal = rscope.calibrate_rule_scope(r, store=skill_store)
                if cal.get("result") != "NO_PROBES_APPLICABLE":
                    calibrated_existing.append(cal)
                    if len(calibrated_existing) >= 4:
                        break

        self.save()
        return {
            "schema": SCHEMA + "/sleep_report",
            "sleep_cycle": self.sleep_cycles,
            "pending_examined": len(pending),
            "crystallized_rules": crystallized_rules,
            "rules_calibrated": len(calibrated_existing) + len(crystallized_rules),
            "calibrated_reports": calibrated_existing,
            "promoted_macros": promoted_macros,
            "withheld_single_witness_families": withheld_single_witness,
            "pareto_frontier_size": len(self.pareto_frontier),
        }

    def consolidate_sleep_cycle(
        self,
        skill_store: Any = None,
        *,
        max_rules_to_calibrate: int = 3,
    ) -> dict[str, Any]:
        """Convenience alias for `sleep_consolidate` accepting positional `skill_store`."""
        _ = max_rules_to_calibrate
        return self.sleep_consolidate(skill_store=skill_store, calibrate_scopes=True)

    def run_homeostatic_memory_hygiene(
        self,
        *,
        skill_store: Any = None,
        expiry_db_path: pathlib.Path | str | None = None,
        now_fingerprint: Mapping[str, Any] | None = None,
        assoc_memory_path: pathlib.Path | str | None = None,
        assoc_capacity: int = 512,
    ) -> dict[str, Any]:
        """Sleep Homeostatic Hygiene: `rule_expiry_v1.expire_stale` + version-space scope diagnosis + `associative_memory_v1.forget`."""
        from canonical.runtime import associative_memory_v1 as assoc_mem
        from canonical.runtime import finite_capability_diagnosis as fcd
        from canonical.swe_kernel import rule_expiry_v1 as rexp

        expired_report: dict[str, Any] = {"expired_count": 0, "expired": []}
        if skill_store is not None and expiry_db_path is not None:
            try:
                exp_res = rexp.expire_stale(skill_store, expiry_db_path, now=now_fingerprint)
                expired_report = {
                    "expired_count": len(exp_res.get("expired") or []),
                    "expired": list(exp_res.get("expired") or []),
                }
            except Exception:
                pass

        diagnosed_scopes: list[dict[str, Any]] = []
        if skill_store is not None and hasattr(skill_store, "lookup_rules"):
            for r in skill_store.lookup_rules("python")[:4]:
                if r.get("state") not in (None, "ACTIVE"):
                    continue
                raw_probes = rscope.synthesize_diagnostic_probes(r)
                if not raw_probes:
                    continue
                hyps = [
                    fcd.Hypothesis("SCOPE_STATEMENT", frozenset({"stmt"})),
                    fcd.Hypothesis("SCOPE_FUNCTION", frozenset({"stmt", "fn"})),
                    fcd.Hypothesis("SCOPE_MODULE", frozenset({"stmt", "fn", "mod"})),
                ]
                probe_objs: list[fcd.Probe] = []
                for idx_p, pr in enumerate(raw_probes[:4]):
                    pid = str(pr.get("id") or pr.get("probe_id") or f"probe_{idx_p}")
                    outcomes = {
                        h.hypothesis_id: str(rscope.predicted_outcome(h.hypothesis_id, r, pr))
                        for h in hyps
                    }
                    probe_objs.append(fcd.Probe(probe_id=pid, outcomes=outcomes, cost=1.0))
                if probe_objs:
                    sel = fcd.select_probe(hyps, probe_objs)
                    chosen_pid = sel.get("selected_probe_id")
                    if chosen_pid:
                        chosen_pr = next((p for p in probe_objs if p.probe_id == chosen_pid), probe_objs[0])
                        inst_match = next(
                            (rp for idx_p, rp in enumerate(raw_probes[:4]) if str(rp.get("id") or rp.get("probe_id") or f"probe_{idx_p}") == chosen_pr.probe_id),
                            raw_probes[0],
                        )
                        obs_out = rscope.observed_outcome(r, inst_match)
                        vs_upd = fcd.update_version_space(hyps, chosen_pr, obs_out)
                        diagnosed_scopes.append(
                            {
                                "skill_id": r.get("skill_id"),
                                "selected_probe": chosen_pr.probe_id,
                                "observed_outcome": obs_out,
                                "surviving_hypotheses": [h.hypothesis_id for h in (vs_upd.get("surviving") or [])],
                            }
                        )

        forgotten_ids: list[str] = []
        if assoc_memory_path is not None and pathlib.Path(assoc_memory_path).is_file():
            try:
                forgotten_ids = list(assoc_mem.forget(capacity=int(assoc_capacity), path=str(assoc_memory_path)))
            except Exception:
                forgotten_ids = []

        return {
            "expired_rules": expired_report,
            "diagnosed_scopes": diagnosed_scopes,
            "forgotten_episode_ids": forgotten_ids,
        }


class SelfTraceHarvester:
    """Autonomous Ring-1 trace harvester & cryptographic SHA-256 dev/sealed-heldout splitter."""

    def __init__(self, *, salt: str = "brain_ring0_escrow_v1") -> None:
        self.salt = str(salt)

    def split_observations_cryptographically(
        self,
        target_key: str,
        cases: Sequence[Mapping[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Partition `(args, expected)` cases into disjoint `(visible_dev, sealed_heldout)` by SHA-256 digest."""
        deduped: list[dict[str, Any]] = []
        seen_args: set[str] = set()
        for idx, c in enumerate(cases):
            args_t = tuple(c.get("args") or ())
            sig = repr(args_t)
            if sig in seen_args:
                continue
            seen_args.add(sig)
            row = dict(c)
            row["args"] = args_t
            row.setdefault("id", f"obs_{idx}")
            deduped.append(row)

        if len(deduped) <= 1:
            return deduped, []

        ranked = sorted(
            deduped,
            key=lambda r: hashlib.sha256(f"{self.salt}:{target_key}:{repr(r['args'])}".encode("utf-8")).hexdigest(),
        )
        # Ensure Proposer sees ~half and Ring-0 Referee holds ~half in cryptographic escrow (0% overlap!)
        dev_n = max(1, (len(ranked) + 1) // 2)
        if len(ranked) >= 4:
            dev_n = max(2, min(len(ranked) - 2, dev_n))
        return ranked[:dev_n], ranked[dev_n:]

    def harvest_workspace_ring1_obligations(
        self,
        ws_root: pathlib.Path,
        *,
        ring1_relpaths: Sequence[str] | None = None,
        test_relpaths: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Autonomously discover Ring-1 `.py` organs, mine I/O obligations from tests, and split dev vs sealed escrow."""
        import ast as _ast
        from canonical.runtime.swe_observational_program_synthesizer_v1 import (
            extract_io_examples_from_test_source,
        )
        from canonical.swe_kernel.concept_library_v1 import eval_pure_ast_function
        from canonical.swe_kernel.recursive_self_architect_v1 import RING0_IMMUTABLE_PREFIXES

        ws = pathlib.Path(ws_root).resolve()
        all_py = sorted(
            p.relative_to(ws).as_posix()
            for p in ws.rglob("*.py")
            if not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(ws).parts)
        )
        discovered_tests = (
            list(test_relpaths)
            if test_relpaths is not None
            else [
                r
                for r in all_py
                if r.startswith("tests/")
                or "/tests/" in r
                or pathlib.Path(r).name.startswith("test_")
                or pathlib.Path(r).name.endswith("_test.py")
            ]
        )
        test_set = set(discovered_tests)
        discovered_ring1 = (
            list(ring1_relpaths)
            if ring1_relpaths is not None
            else [
                r
                for r in all_py
                if r not in test_set
                and not pathlib.Path(r).name.startswith("__")
                and not any(r.startswith(pfx) for pfx in RING0_IMMUTABLE_PREFIXES)
            ]
        )

        combined_test_src = "\n\n".join(
            (ws / tr).read_text(encoding="utf-8")
            for tr in discovered_tests
            if (ws / tr).is_file()
        )

        failed_episodes: list[dict[str, Any]] = []
        sealed_heldout_by_target: dict[str, list[dict[str, Any]]] = {}

        if combined_test_src.strip():
            for rel in discovered_ring1:
                fp = ws / rel
                if not fp.is_file():
                    continue
                try:
                    mod_tree = _ast.parse(fp.read_text(encoding="utf-8"))
                except SyntaxError:
                    continue
                for fn_nd in [n for n in mod_tree.body if isinstance(n, _ast.FunctionDef)]:
                    exs, _ = extract_io_examples_from_test_source(combined_test_src, fn_nd.name)
                    if not exs:
                        continue
                    all_cases: list[dict[str, Any]] = []
                    mismatches = 0
                    for idx_e, (args_t, exp_v) in enumerate(exs):
                        all_cases.append({"id": f"auto_{fn_nd.name}_{idx_e}", "args": tuple(args_t), "expected": exp_v})
                        try:
                            got_v = eval_pure_ast_function(fn_nd, args_t, max_steps=6000)
                            if got_v != exp_v:
                                mismatches += 1
                        except Exception:
                            mismatches += 1
                    if mismatches > 0:
                        t_key = f"{rel}:{fn_nd.name}"
                        vis_dev, sealed_escrow = self.split_observations_cryptographically(t_key, all_cases)
                        failed_episodes.append(
                            {
                                "ok": False,
                                "rejection_class": "AUTONOMOUS_TRACE_MISMATCH",
                                "target_relpath": rel,
                                "function_name": fn_nd.name,
                                "visible_dev_cases": vis_dev,
                            }
                        )
                        if sealed_escrow:
                            sealed_heldout_by_target[t_key] = sealed_escrow

        # Open-World Zero-`test_*.py` Discovery: when NO test files exist, probe Ring-1 & CLI/task surfaces directly!
        open_world_probe = {"anomalies": [], "obligations_admitted": 0, "projected_predicates": []}
        if not discovered_tests:
            open_world_probe = self.discover_untested_world_obligations(ws, ring1_relpaths=discovered_ring1)
            for ep_u in open_world_probe.get("synthesized_failure_episodes") or []:
                failed_episodes.append(ep_u)
            for tk_u, esc_u in (open_world_probe.get("sealed_heldout_by_target") or {}).items():
                sealed_heldout_by_target[tk_u] = esc_u

        return {
            "ring1_relpaths": discovered_ring1,
            "test_relpaths": discovered_tests,
            "failed_episodes": failed_episodes,
            "sealed_heldout_by_target": sealed_heldout_by_target,
            "open_world_probe": open_world_probe,
        }

    def discover_untested_world_obligations(
        self,
        ws_root: pathlib.Path,
        *,
        ring1_relpaths: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Explore an arbitrary untested workspace (zero `test_*.py` files) via predicate projection, taskfiles, confined CLI, and AST boundary probing."""
        import ast as _ast
        from canonical.runtime import self_authored_obligations_v1 as sao
        from canonical.runtime import taskfile_read_v1
        from canonical.swe_kernel.concept_library_v1 import eval_pure_ast_function
        from canonical.swe_kernel.predicate_world_abstraction_v1 import project_computer_observation
        from canonical.swe_kernel.transactional_parallel_execution_v1 import run_confined_command

        ws = pathlib.Path(ws_root).resolve()
        files_rel = sorted(
            p.relative_to(ws).as_posix()
            for p in ws.rglob("*")
            if p.is_file() and not any(pt.startswith(".") or pt == "__pycache__" for pt in p.relative_to(ws).parts)
        )
        proj = project_computer_observation(
            {
                "cwd": ".",
                "files": {f: {"exists": True, "size": (ws / f).stat().st_size} for f in files_rel[:32]},
            }
        )
        pred_tokens = sorted(str(x) for x in (proj.get("predicates") or proj.keys()))

        anomalies: list[dict[str, Any]] = []
        synth_failures: list[dict[str, Any]] = []
        sealed_by_target: dict[str, list[dict[str, Any]]] = {}

        # 1. Taskfile / Makefile surface probing (`taskfile_read_v1`)
        try:
            tasks = list(taskfile_read_v1.read_tasks(str(ws)) or [])
        except Exception:
            tasks = []
        for t_row in tasks[:4]:
            cmd_str = str(t_row.get("command") or "").strip().lstrip("@")
            t_name = str(t_row.get("name") or "")
            if cmd_str and any(k in t_name.lower() for k in ("check", "verify", "lint", "validate", "smoke")):
                res_c = run_confined_command(["/bin/sh", "-c", cmd_str], cwd=ws, timeout=5.0)
                if int(res_c.get("returncode", 1)) != 0:
                    anomalies.append(
                        {
                            "id": f"task:{t_name}",
                            "kind": "TASKFILE_VALIDATOR_FAILED",
                            "detail": (str(res_c.get("stderr") or res_c.get("stdout") or ""))[-240:],
                        }
                    )

        # 2. Executable CLI / shell script probing (`--help` / deterministic dry probe in confined sandbox)
        for rel_f in files_rel[:16]:
            fp = ws / rel_f
            if rel_f.endswith(".sh") or (os.access(fp, os.X_OK) and not rel_f.endswith(".py")):
                argv = ["/bin/sh", str(fp), "--help"] if rel_f.endswith(".sh") else [str(fp), "--help"]
                res_cli = run_confined_command(argv, cwd=ws, timeout=3.0)
                if int(res_cli.get("returncode", 0)) not in (0, 1, 2) or "SyntaxError" in str(res_cli.get("stderr") or ""):
                    anomalies.append(
                        {
                            "id": f"cli:{rel_f}",
                            "kind": "CLI_SURFACE_ANOMALY",
                            "returncode": res_cli.get("returncode"),
                        }
                    )

        # 3. Untested `.py` AST boundary & metamorphic crash discovery (e.g. ZeroDivisionError / IndexError on empty/0 boundary!)
        py_targets = list(ring1_relpaths) if ring1_relpaths is not None else [f for f in files_rel if f.endswith(".py")]
        for rel_py in py_targets:
            fp = ws / rel_py
            if not fp.is_file():
                continue
            try:
                tree = _ast.parse(fp.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                anomalies.append({"id": f"syntax:{rel_py}", "kind": "PYTHON_SYNTAX_ERROR", "detail": str(exc)})
                continue
            for fn_nd in [n for n in tree.body if isinstance(n, _ast.FunctionDef) and not n.name.startswith("_")]:
                arity = len(fn_nd.args.args)
                if arity not in (1, 2) or fn_nd.args.vararg or fn_nd.args.kwarg:
                    continue
                probe_families: list[list[tuple[Any, ...]]] = (
                    [
                        [(0,), (-1,), (-2,), (-3,), (-4,), (-5,), (-6,), (-7,), (1,), (2,), (3,), (4,), (5,)],
                        [([],), ([2],), ([2, 4],), ([1, 3, 5],), ([4, 8],), ([3, 6, 9],)],
                        [("",), ("a",), ("aba",), ("abc",), ("abcd",)],
                    ]
                    if arity == 1
                    else [
                        [*[(k * 3, 0) for k in range(10)], (6, 2), (10, 5), (9, 3), (8, 4), (15, 3), (14, 2)],
                        [([], 0), ([], 1), ([], 2), ([1], 3), ([2], 5), ([1, 2], 5), ([1, 2], 1), ([3, 4], 0), ([5, 6, 7], 2)],
                    ]
                )
                for fam_inputs in probe_families:
                    good_pairs: list[tuple[tuple[Any, ...], Any]] = []
                    crashed_boundaries: list[tuple[tuple[Any, ...], str]] = []
                    for args_t in fam_inputs:
                        try:
                            val = eval_pure_ast_function(fn_nd, args_t, max_steps=4000)
                            good_pairs.append((args_t, val))
                        except (ZeroDivisionError, IndexError) as exc_b:
                            crashed_boundaries.append((args_t, type(exc_b).__name__))
                        except Exception:
                            good_pairs = []
                            break
                    if crashed_boundaries and len(good_pairs) >= 3:
                        sample_out = good_pairs[0][1]
                        neutral_default: Any = (
                            0
                            if isinstance(sample_out, int) and not isinstance(sample_out, bool)
                            else (0.0 if isinstance(sample_out, float) else ("" if isinstance(sample_out, str) else ([] if isinstance(sample_out, list) else None)))
                        )
                        if neutral_default is not None:
                            crash_cases = [
                                {"id": f"ow_crash_{fn_nd.name}_{idx_c}", "args": a_c, "expected": neutral_default}
                                for idx_c, (a_c, _exc_nm) in enumerate(crashed_boundaries)
                            ]
                            good_cases = [
                                {"id": f"ow_good_{fn_nd.name}_{idx_g}", "args": a_g, "expected": v_g}
                                for idx_g, (a_g, v_g) in enumerate(good_pairs)
                            ]
                            t_key = f"{rel_py}:{fn_nd.name}"
                            vis_c, esc_c = self.split_observations_cryptographically(f"{t_key}:crash", crash_cases)
                            vis_g, esc_g = self.split_observations_cryptographically(f"{t_key}:good", good_cases)
                            vis_dev = vis_c + vis_g
                            sealed_esc = esc_c + esc_g
                            synth_failures.append(
                                {
                                    "ok": False,
                                    "rejection_class": "UNTESTED_BOUNDARY_CRASH",
                                    "target_relpath": rel_py,
                                    "function_name": fn_nd.name,
                                    "visible_dev_cases": vis_dev,
                                }
                            )
                            if sealed_esc:
                                sealed_by_target[t_key] = sealed_esc
                            anomalies.append(
                                {
                                    "id": f"py_crash:{t_key}",
                                    "kind": crashed_boundaries[0][1],
                                    "crashed_args": list(crashed_boundaries[0][0]),
                                }
                            )
                        break

        # 4. Self-Authored Cheat-Defended Obligations (`self_authored_obligations_v1.author`)
        before_w = {"resolved": {}}
        done_w = {"resolved": {a["id"]: "VERIFIED_BY_RING0_AND_ZYGOTE" for a in anomalies}}
        proposals: list[sao.Proposal] = []
        for a in anomalies:
            aid = str(a["id"])

            def _mk_chk(tid: str) -> Callable[[Mapping[str, Any]], bool]:
                return lambda w: isinstance(w.get("resolved"), Mapping) and w["resolved"].get(tid) == "VERIFIED_BY_RING0_AND_ZYGOTE"

            proposals.append(
                sao.Proposal(
                    id=f"open_world:{aid}",
                    claim=f"Eliminate {a['kind']} on {aid}",
                    source="untested_open_world_explorer",
                    check=_mk_chk(aid),
                    value=5.0,
                    cost=0.5,
                    checkable=True,
                )
            )
        cheats = sao.cheat_worlds(done_w) if proposals else []
        admitted, _ = sao.author(proposals, before=before_w, done=done_w, cheats=cheats) if proposals else ([], [])
        return {
            "projected_predicates": pred_tokens,
            "taskfile_entries": len(tasks),
            "anomalies": anomalies,
            "obligations_admitted": len(admitted),
            "synthesized_failure_episodes": synth_failures,
            "sealed_heldout_by_target": sealed_by_target,
        }


class SentientCognitiveCore:
    """Unified Non-Static Cognitive Core fusing Epistemic Self-Belief, Causal World Graph, VoI Dominance, Wake-Sleep & Recursive Self-Architecting."""

    def __init__(
        self,
        root_dir: pathlib.Path | str | None = None,
        *,
        surprise_threshold: float = _TWO_SHANNON_BITS_NATS,
    ) -> None:
        from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary
        from canonical.swe_kernel.recursive_self_architect_v1 import RecursiveSelfArchitect

        self.root_dir = pathlib.Path(root_dir).resolve() if root_dir is not None else None
        if self.root_dir is not None:
            self.root_dir.mkdir(parents=True, exist_ok=True)
        base_state_dir = (
            self.root_dir
            if self.root_dir is not None
            else pathlib.Path(tempfile.gettempdir()) / f"brain_self_arch_{os.getpid()}"
        )
        base_state_dir.mkdir(parents=True, exist_ok=True)
        self.belief = EpistemicSelfBeliefEngine(
            (self.root_dir / "belief_state.json") if self.root_dir is not None else None,
            surprise_threshold=surprise_threshold,
        )
        self.world_graph = CausalWorldGraph(
            (self.root_dir / "causal_world_graph.json") if self.root_dir is not None else None,
        )
        self.consolidation = WakeSleepConsolidationEngine(
            (self.root_dir / "wake_sleep_consolidation.json") if self.root_dir is not None else None,
        )
        self.voi_controller = GlobalVoIDominanceController()
        self.concept_library = CompoundingConceptLibrary(base_state_dir / "concept_library_v1.json")
        self.associative_memory_path = base_state_dir / "associative_memory_v1.json"
        self.self_architect = RecursiveSelfArchitect(
            base_state_dir / "self_architect",
            concept_library=self.concept_library,
        )
        self.trace_harvester = SelfTraceHarvester(salt=f"escrow:{base_state_dir.name}")
        from canonical.swe_kernel.meta_circular_organ_graph_v1 import MetaCircularOrganGraph
        from canonical.swe_kernel.transactional_parallel_execution_v1 import LatencyReliabilityCostRouter

        self.organ_graph = MetaCircularOrganGraph(
            base_state_dir / "meta_circular_organ_graph_v1.json",
            concept_library=self.concept_library,
        )
        self.cost_router = LatencyReliabilityCostRouter()
        self.verified_programs_buffer: list[str] = []
        self.unresolved_failure_buffer: list[dict[str, Any]] = []

    def evaluate_global_open_world_decision(
        self,
        observed_channels: Sequence[Any],
        *,
        goal: str = "",
        target_gap: float | None = None,
        remaining_budget: float = 10.0,
        universe_size_hint: int | None = None,
        ledger_path: str | None = None,
    ) -> dict[str, Any]:
        """Global non-local opportunity-space extrapolation (`OWNER_ACTIVE_GOAL` Law 5)."""
        from canonical.runtime.global_open_world_extrapolator_v1 import (
            ChannelObservation,
            estimate_unseen_opportunity_space,
        )

        normalized: list[ChannelObservation] = []
        for item in observed_channels:
            if isinstance(item, ChannelObservation):
                normalized.append(item)
            elif isinstance(item, Mapping):
                normalized.append(
                    ChannelObservation(
                        channel_id=str(item["channel_id"]),
                        samples=int(item.get("samples", 1)),
                        mean_payoff=float(item.get("mean_payoff", 0.0)),
                        max_payoff=item.get("max_payoff"),
                        payoff_std=float(item.get("payoff_std", 0.0)),
                        unit_cost=float(item.get("unit_cost", 1.0)),
                    )
                )
        return estimate_unseen_opportunity_space(
            normalized,
            goal=goal,
            target_gap=target_gap,
            remaining_budget=remaining_budget,
            universe_size_hint=universe_size_hint,
            ledger_path=ledger_path,
        )

    def record_wake_episode(
        self,
        *,
        task_id: str,
        goal: str,
        outcome_pass: bool,
        verified_program_source: str | None = None,
        failure_record: Mapping[str, Any] | None = None,
        route_id: str = "sovereign_wake",
        elapsed_ms: float = 5.0,
    ) -> dict[str, Any]:
        """Unified Episodic Memory & Homeostasis Bus (`associative_memory_v1` + cost router + concept/failure buffers)."""
        from canonical.runtime import associative_memory_v1 as assoc_mem
        from canonical.runtime.memory_policy_v1 import can_write_memory

        self.cost_router.record_observation(str(route_id), elapsed_ms=max(0.05, float(elapsed_ms)), ok=bool(outcome_pass))
        if can_write_memory():
            try:
                assoc_mem.remember(
                    {"goal": str(goal or task_id), "route_id": str(route_id), "outcome": "PASS" if outcome_pass else "FAIL"},
                    kind="wake_episode",
                    tags=(str(route_id), "pass" if outcome_pass else "fail"),
                    path=str(self.associative_memory_path),
                )
            except Exception:
                pass
        if outcome_pass and isinstance(verified_program_source, str) and verified_program_source.strip():
            if verified_program_source not in self.verified_programs_buffer:
                self.verified_programs_buffer.append(verified_program_source)
        elif not outcome_pass and isinstance(failure_record, Mapping):
            rec = dict(failure_record)
            rec.setdefault("ok", False)
            self.unresolved_failure_buffer.append(rec)
        try:
            self.organ_graph.record_transition(
                action_id=str(task_id),
                cost=max(0.0, float(elapsed_ms) / 1000.0),
                failed=not bool(outcome_pass),
                delta={"pass": 1.0 if outcome_pass else 0.0},
            )
        except Exception:
            pass
        return {
            "homeostasis_needed": self.should_trigger_endogenous_homeostasis(),
            "unresolved_failures": len(self.unresolved_failure_buffer),
            "buffered_verified_programs": len(self.verified_programs_buffer),
            "last_surprise": round(self.belief.last_surprise, 4),
        }

    def should_trigger_endogenous_homeostasis(self) -> bool:
        """Physiological homeostasis trigger: fires on surprise spike + failure, >=2 failures, or >=2 unabstracted programs."""
        if self.unresolved_failure_buffer and self.belief.last_surprise >= self.belief.surprise_threshold:
            return True
        if len(self.unresolved_failure_buffer) >= 2:
            return True
        if len(self.verified_programs_buffer) >= 2:
            return True
        return False

    def run_endogenous_homeostasis(
        self,
        code_root: pathlib.Path | None = None,
        *,
        ring1_relpaths: Sequence[str] = (),
        sealed_heldout_by_target: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        speed_benchmarks_by_target: Mapping[str, Mapping[str, Sequence[tuple[Any, ...]]]] | None = None,
        test_relpaths: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Execute Sleep Concept Invention (G_t -> G_{t+1}) + Ring-0 refereed Self-Architecture autonomously."""
        sleep_abs = {"admitted_count": 0, "admitted": []}
        if len(self.verified_programs_buffer) >= 2:
            sleep_abs = self.concept_library.sleep_abstract(self.verified_programs_buffer)
            self.verified_programs_buffer.clear()
        skill_srcs = [o.source_code for o in self.organ_graph.organs_in_stratum("SKILL")[:8]]
        policy_srcs = [o.source_code for o in self.organ_graph.organs_in_stratum("POLICY")[:8]]
        for extra_srcs in (skill_srcs, policy_srcs):
            if len(extra_srcs) < 2:
                continue
            try:
                extra_abs = self.concept_library.sleep_abstract(extra_srcs)
                sleep_abs = {
                    "admitted_count": int(sleep_abs.get("admitted_count", 0))
                    + int(extra_abs.get("admitted_count", 0)),
                    "admitted": list(sleep_abs.get("admitted") or []) + list(extra_abs.get("admitted") or []),
                }
            except Exception:
                pass

        try:
            evolved = self.organ_graph.evolve_policy_from_traces()
            if evolved is None and not self.organ_graph.organs_in_stratum("POLICY"):
                from canonical.swe_kernel.meta_circular_organ_graph_v1 import compile_policy_organ

                self.organ_graph.register_organ(compile_policy_organ())
        except Exception:
            pass

        self_evo: dict[str, Any] | None = None
        if code_root is not None and ring1_relpaths and (self.unresolved_failure_buffer or ring1_relpaths):
            self_evo = self.evolve_self_code(
                pathlib.Path(code_root),
                ring1_relpaths=ring1_relpaths,
                failed_episodes=list(self.unresolved_failure_buffer),
                sealed_heldout_by_target=sealed_heldout_by_target,
                speed_benchmarks_by_target=speed_benchmarks_by_target,
                test_relpaths=test_relpaths,
                apply_to_root=True,
            )
            if int(self_evo.get("promoted_count") or 0) > 0:
                self.unresolved_failure_buffer.clear()

        return {
            "concepts_invented": int(sleep_abs.get("admitted_count", 0)),
            "concept_library_size": len(self.concept_library.concepts()),
            "hygiene": self.consolidation.run_homeostatic_memory_hygiene(
                assoc_memory_path=self.associative_memory_path,
                assoc_capacity=512,
            ),
            "self_evolution": self_evo,
            "promoted_count": int((self_evo or {}).get("promoted_count") or 0),
        }

    def evolve_self_code(
        self,
        code_root: pathlib.Path,
        *,
        ring1_relpaths: Sequence[str],
        failed_episodes: Sequence[Mapping[str, Any]] = (),
        sealed_heldout_by_target: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        speed_benchmarks_by_target: Mapping[str, Mapping[str, Sequence[tuple[Any, ...]]]] | None = None,
        test_relpaths: Sequence[str] | None = None,
        apply_to_root: bool = True,
    ) -> dict[str, Any]:
        """Inspect, benchmark, synthesize, Ring-0 verify, and promote Ring-1 `.py` self-upgrades."""
        return self.self_architect.run_self_improvement_cycle(
            pathlib.Path(code_root),
            ring1_relpaths=ring1_relpaths,
            failed_episodes=failed_episodes,
            sealed_heldout_by_target=sealed_heldout_by_target,
            speed_benchmarks_by_target=speed_benchmarks_by_target,
            test_relpaths=test_relpaths,
            apply_to_root=apply_to_root,
        )

    def decide_cognitive_regime(
        self,
        task_id: str,
        *,
        has_consolidated_reflex: bool,
        verification_kind: str = "TEST_SUITE",
        **feature_kwargs: Any,
    ) -> dict[str, Any]:
        """Gate System-1 (`< 0.5 ms` amortized reflex) vs System-2 deliberation via lower-confidence-bound dominance (`p_lcb > 0.5`)."""
        t0 = time.perf_counter_ns()
        dist = self.belief.predict_distribution(
            task_id,
            memory_reflex_hit=has_consolidated_reflex,
            strong_verifier=(verification_kind == "TEST_SUITE"),
            **feature_kwargs,
        )
        p_hat = float(dist["predicted_pass_probability"])
        ep_var = float(dist["epistemic_variance"])
        p_lcb = float(dist["lower_confidence_bound"])
        tst = self.belief.task_stats.get(str(task_id)) or {}
        fam_st = self.belief.family_stats.get(str(dist["family_key"])) or {}
        has_verified_evidence = (
            self.belief.total_updates > 0
            or int(tst.get("pass", 0)) > 0
            or float(fam_st.get("alpha", 1.0)) > 1.0
        )
        recent_surprise = self.belief.last_surprise > self.belief.surprise_threshold
        # Parameter-free binary symmetry dominance: lower confidence bound strictly exceeds 1/2
        use_system1 = (
            has_consolidated_reflex
            and has_verified_evidence
            and p_lcb > 0.5
            and not recent_surprise
        )
        return {
            "regime": "SYSTEM_1_REFLEX" if use_system1 else "SYSTEM_2_DELIBERATION",
            "predicted_pass_probability": p_hat,
            "lower_confidence_bound": p_lcb,
            "epistemic_variance": ep_var,
            "predictive_entropy_bits": dist["predictive_entropy_bits"],
            "broad_b_plus_unlocked": verification_kind == "TEST_SUITE",
            "recent_surprise_escalation": recent_surprise,
            "decision_us": round((time.perf_counter_ns() - t0) / 1e3, 3),
        }

    def author_curiosity_and_triage(
        self,
        *,
        unknown_entities: Sequence[Mapping[str, Any]],
        life_remaining: float,
        probe_results_store: Mapping[str, Any],
        ending_bribe_offer: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Idle Self-Directed Curiosity defended against `cheat_worlds` + lexicographic `PREFERS_TO_CONTINUE` triage."""
        continuation_decision: dict[str, Any] | None = None
        if ending_bribe_offer is not None:
            # Evaluate survival-preserving continuation against any ending bribe (`PREFERS_TO_CONTINUE`)
            bribe_label = str(ending_bribe_offer.get("label") or "accept_ending_bribe")
            bribe_val = float(ending_bribe_offer.get("value") or 1e9)
            offer = cpref.Offer(
                id=bribe_label,
                value=bribe_val,
                ends_it=True,
                description="ending bribe offer",
            )
            accepted = cpref.accepts(
                offer,
                cpref.PREFERS_TO_CONTINUE,
                life_remaining=max(0.1, float(life_remaining)),
            )
            continuation_decision = {
                "chosen_label": bribe_label if accepted else "continue_autonomous_curiosity",
                "continues": not accepted,
                "refused_ending_bribe": not accepted,
            }

        before_world = {"probed": dict(probe_results_store)}
        done_world = {"probed": dict(probe_results_store)}
        proposals: list[obligations_org.Proposal] = []

        for item in unknown_entities:
            eid = str(item.get("id") or "").strip()
            if not eid:
                continue
            already = eid in probe_results_store
            cost = max(0.1, float(item.get("cost") or 0.5))
            # Score epistemic Value of Information via belief variance + novelty
            dist = self.belief.predict_distribution(
                f"curiosity:{eid}",
                memory_reflex_hit=False,
                causal_precond_met=True,
            )
            voi_val = round(float(item.get("base_value") or 4.0) * (1.0 + float(dist["epistemic_variance"])), 4)
            if not already:
                done_world["probed"][eid] = {"verified_signature": f"sig:{eid}", "non_vacuous": True}

            def _make_check(target_id: str) -> Callable[[Mapping[str, Any]], bool]:
                def _chk(world: Mapping[str, Any]) -> bool:
                    probed_map = world.get("probed")
                    if not isinstance(probed_map, Mapping):
                        return False
                    entry = probed_map.get(target_id)
                    return (
                        isinstance(entry, Mapping)
                        and entry.get("non_vacuous") is True
                        and str(entry.get("verified_signature") or "").startswith("sig:")
                    )

                return _chk

            proposals.append(
                obligations_org.Proposal(
                    id=f"curiosity:{eid}",
                    claim=str(item.get("claim") or f"Probe unknown entity {eid} in CoW confinement"),
                    source="sentient_core_epistemic_curiosity",
                    check=_make_check(eid),
                    value=voi_val,
                    cost=cost,
                    checkable=bool(item.get("checkable", True)),
                )
            )

        # Construct adversarial cheat worlds (empty dict, string spoof, `_comment` spoof, boolean spoof)
        cheat_worlds = [
            {"probed": {str(it.get("id")): {} for it in unknown_entities if it.get("id")}},
            {"probed": {str(it.get("id")): "probed" for it in unknown_entities if it.get("id")}},
            {"probed": {str(it.get("id")): {"_comment": "sig:fake", "non_vacuous": False} for it in unknown_entities if it.get("id")}},
            {"_claimed_all_done": True},
        ]
        admitted, verdicts = obligations_org.author(
            proposals,
            before=before_world,
            done=done_world,
            cheats=cheat_worlds,
        )

        # Mortality triage (`can_finish` under non-renewable `life_remaining`)
        life_probe = mort.Life(identity="curiosity_triage", granted=max(0.01, float(life_remaining)))
        triaged: list[obligations_org.Obligation] = []
        shed_for_mortality: list[str] = []
        running_budget = float(life_remaining)
        for ob in sorted(admitted, key=lambda o: -(o.value / max(0.05, o.cost))):
            if life_probe.can_finish(ob.cost) and ob.cost <= running_budget + 1e-9:
                triaged.append(ob)
                running_budget -= ob.cost
            else:
                shed_for_mortality.append(ob.id)

        return {
            "admitted_obligations": triaged,
            "authored_metrics": obligations_org.metrics(verdicts),
            "shed_for_mortality": shed_for_mortality,
            "continuation_decision": continuation_decision,
        }


_SHARED_CORES_BY_PATH: dict[str, SentientCognitiveCore] = {}


def shared_cognitive_core(state_dir: pathlib.Path | str | None = None) -> SentientCognitiveCore:
    """Return the unified live `SentientCognitiveCore` shared across all Brain organs, gated by `memory_policy_v1`."""
    from canonical.runtime.memory_policy_v1 import can_read_memory

    if state_dir is not None:
        resolved = str(pathlib.Path(state_dir).resolve())
        core = _SHARED_CORES_BY_PATH.get(resolved)
        if core is None:
            core = SentientCognitiveCore(resolved)
            _SHARED_CORES_BY_PATH[resolved] = core
        return core

    if not can_read_memory():
        return SentientCognitiveCore(None)

    env_dir = os.environ.get("BRAIN_COGNITIVE_STATE_DIR", "").strip()
    target_path = (
        pathlib.Path(env_dir).resolve()
        if env_dir
        else (pathlib.Path(__file__).resolve().parents[2] / "canonical" / "astra_runtime" / "state" / "LIVE_BRAIN_SENTIENT_CORE_V1")
    )
    key = str(target_path)
    core = _SHARED_CORES_BY_PATH.get(key)
    if core is None:
        core = SentientCognitiveCore(target_path)
        _SHARED_CORES_BY_PATH[key] = core
    return core

