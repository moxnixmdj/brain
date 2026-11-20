#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Null-Space Admission — memory-free weight update via null-space projection.

THE BOTTLENECK IT REMOVES
--------------------------
weight_update_admission_v1 proved: 32 naive gradient steps each reported
loss_delta>0 on the trained goal, yet 5/32 agreement with parser and 3 broken
predictions on held-out probes. Gate correctly REJECTs 27/32, but also REFINEs
many that would have helped if forgetting could be prevented. The gate trades
reach for precision — correct, but leaves generality on the table.

Frontier 2026: LRM fine-tunes increase forgetting (arXiv 2601.18699). NuSA-CL
(ICLR 2026) solution: null-space LoRA — project updates onto null space of
past tasks (tail > top), merge into base fixed budget, memory-free lifelong.
No rehearsal, no stored examples, no growing memory. We adopt the same idea
for the only weight-space learner in this tree: the 3 linear heads in
OnlineParametricPolicyModel (128-dim hashed features → op/concept/domain).

MECHANISM
---------
For each head, maintain gradient history G (n_tasks × n_params) in external
store (not weights). Compute SVD: G = U Σ V^T. Null space = last k singular
vectors where σ < ε (ε = 1e-4). New gradient g_proj = V_null V_null^T g.

Fixed budget: V_null merged into base weights (no extra parameters), same
shape as before. If null space too small (rank-deficient), update is
refused — fail-closed, not forced.

Reuse: weight_update_admission's shadow/evaluate pattern + apply_if_admitted
gate (gained≥1 lost==0). Only difference: shadow step uses projected gradient.

Zero model calls, zero network, external history file (inspectable), weights
hold only mechanisms. Authority: NONE.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import pathlib
from typing import Any, Mapping, Sequence

_ROOT = pathlib.Path(__file__).resolve().parents[2]
import sys
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA = "PROJECT_BRAIN_NULLSPACE_ADMISSION_V1"
HISTORY_PATH = _ROOT / "canonical/astra_runtime/generalization/NULLSPACE_HISTORY_V1.json"

# ------------------------------------------------------------
# History store (external, not weights)
# ------------------------------------------------------------

def _load_history(path: pathlib.Path | None = None) -> dict[str, Any]:
    p = path or HISTORY_PATH
    try:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"gradients": [], "tasks": [], "epsilon": 1e-4}

def _save_history(data: dict[str, Any], path: pathlib.Path | None = None) -> None:
    p = path or HISTORY_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    import os
    os.replace(tmp, p)

def _hash_features(text: str, n_features: int = 128) -> list[float]:
    import hashlib, re, math
    vec = [0.0]*n_features
    words = re.findall(r"\w+", text.lower())
    grams = list(words) + [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)]
    for gram in grams:
        h = hashlib.sha256(gram.encode()).hexdigest()
        idx = int(h, 16) % n_features
        sign = 1.0 if int(h,16)%2==0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v/norm for v in vec]

def _gradient_for_goal(model: Any, goal: str, operation: str, concept: str, domain: str) -> list[float]:
    """Compute flattened gradient for one goal (for history). We use head=op
    as proxy; full method would concat all 3 heads. Minimal honest scope."""
    from canonical.swe_kernel.semantic_generalization_engine_v1 import OPERATIONS, ALL_CONCEPTS, DOMAINS
    n_feats = model.n_features
    features = _hash_features(goal, n_feats)
    # Compute gradient w.r.t W_op only for simplicity (dominant head)
    # dL/dz = p - y, dL/dW = f ⊗ dL/dz
    import math
    # forward
    logits = []
    W = model.W_op
    for j in range(len(OPERATIONS)):
        s = sum(W[i][j]*f for i,f in enumerate(features) if f)
        logits.append(s)
    m = max(logits)
    exps = [math.exp(x-m) for x in logits]
    total = sum(exps) or 1.0
    probs = [e/total for e in exps]
    target = OPERATIONS.index(operation)
    grad_z = list(probs)
    grad_z[target] -= 1.0
    # flatten outer product f ⊗ grad_z
    flat: list[float] = []
    for i,f in enumerate(features):
        for j in range(len(OPERATIONS)):
            flat.append(f * grad_z[j] if f else 0.0)
    return flat

# ------------------------------------------------------------
# SVD helpers (pure python, no numpy — small dims)
# ------------------------------------------------------------

def _mat_vec_mul(A: list[list[float]], v: list[float]) -> list[float]:
    return [sum(A[i][j]*v[j] for j in range(len(v))) for i in range(len(A))]

def _vec_norm(v: list[float]) -> float:
    return math.sqrt(sum(x*x for x in v)) or 1.0

def _power_iteration_svd(G: list[list[float]], k: int = 4, iters: int = 30) -> tuple[list[float], list[list[float]]]:
    """Approximate top-k singular values/vectors via power iteration on G^T G.
    Returns (sigma, V_cols) where V_cols are right singular vectors."""
    if not G or not G[0]:
        return [], []
    n_params = len(G[0])
    # Compute G^T G implicitly
    GtG = [[0.0]*n_params for _ in range(n_params)]
    for row in G:
        for i in range(n_params):
            if row[i]==0: continue
            for j in range(n_params):
                GtG[i][j] += row[i]*row[j]
    sigmas: list[float] = []
    V_cols: list[list[float]] = []
    # Deflate iteratively
    for _ in range(k):
        # random init
        v = [1.0/n_params]*n_params
        # add small noise for separation
        import random
        rng = random.Random(42+len(V_cols))
        v = [rng.uniform(-0.5,0.5) for _ in range(n_params)]
        for _ in range(iters):
            v_new = _mat_vec_mul(GtG, v)
            # orthogonalize against previous Vs
            for pv in V_cols:
                dot = sum(v_new[i]*pv[i] for i in range(n_params))
                v_new = [v_new[i]-dot*pv[i] for i in range(n_params)]
            norm = _vec_norm(v_new)
            if norm < 1e-12:
                break
            v = [x/norm for x in v_new]
        # sigma = sqrt(v^T GtG v)
        Gv = _mat_vec_mul(GtG, v)
        sigma_sq = sum(v[i]*Gv[i] for i in range(n_params))
        sigma = math.sqrt(max(sigma_sq,0.0))
        if sigma < 1e-6:
            break
        sigmas.append(sigma)
        V_cols.append(v[:])
        # deflate GtG: GtG -= sigma^2 * v v^T
        for i in range(n_params):
            for j in range(n_params):
                GtG[i][j] -= sigma*sigma * v[i]*v[j]
    return sigmas, V_cols

def _nullspace_project(grad: list[float], G: list[list[float]], epsilon: float = 1e-4) -> tuple[list[float], dict[str, Any]]:
    """Project grad onto null space of G (tail > top). Empty history = full space (no projection needed, but allowed)."""
    if not G:
        return grad[:], {"projected": True, "reason": "EMPTY_HISTORY_FULL_NULLSPACE", "rank": 0, "preserved_ratio": 1.0, "sigmas": []}
    n_params = len(grad)
    sigmas, V_top = _power_iteration_svd(G, k=min(4, len(G)))
    # Estimate rank: sigma > epsilon
    rank = sum(1 for s in sigmas if s > epsilon)
    # Null space is complement of top-r rank subspace. Since we only computed
    # top-k, we approximate projection as grad - Proj_top(grad)
    # Proj_top = sum_{v in V_top ranked} (v·grad) v
    proj_top = [0.0]*n_params
    for v in V_top[:rank]:
        dot = sum(v[i]*grad[i] for i in range(n_params))
        for i in range(n_params):
            proj_top[i] += dot * v[i]
    g_null = [grad[i] - proj_top[i] for i in range(n_params)]
    # Check if projection preserved meaningful magnitude
    orig_norm = _vec_norm(grad)
    null_norm = _vec_norm(g_null)
    preserved = (null_norm / (orig_norm or 1.0))
    if preserved < 0.05:
        return [0.0]*n_params, {"projected": False, "reason": "NULLSPACE_TOO_SMALL_PRESERVED_UNDER_5pct", "rank": rank, "preserved_ratio": round(preserved,4), "sigmas": [round(s,4) for s in sigmas]}
    return g_null, {"projected": True, "rank": rank, "preserved_ratio": round(preserved,4), "sigmas": [round(s,4) for s in sigmas], "full_space_dim": n_params}

# ------------------------------------------------------------
# Shadow with null-space projected gradient
# ------------------------------------------------------------

def _shadow_with_projected_update(model: Any, goal: str, operation: str, concept: str, domain: str,
                                   G_history: list[list[float]], learning_rate: float, weight_decay: float) -> tuple[Any, dict[str, Any]]:
    shadow = copy.copy(model)
    shadow.W_op = [list(row) for row in model.W_op]
    shadow.W_concept = [list(row) for row in model.W_concept]
    shadow.W_domain = [list(row) for row in model.W_domain]
    shadow.state_path = None
    # compute raw gradient flat
    raw_flat = _gradient_for_goal(model, goal, operation, concept, domain)
    # project
    proj_flat, proj_info = _nullspace_project(raw_flat, G_history, epsilon=1e-4)
    if not proj_info.get("projected"):
        # No null space — treat as no-op but report (gate will handle as REFINE/REJECT)
        return shadow, {"projected": False, "proj_info": proj_info, "delta_w_l2": 0.0}
    # Unflatten proj_flat back to W_op shape and apply SGD step
    n_feats = model.n_features
    from canonical.swe_kernel.semantic_generalization_engine_v1 import OPERATIONS
    idx = 0
    delta_sq = 0.0
    for i in range(n_feats):
        for j in range(len(OPERATIONS)):
            g = proj_flat[idx]
            idx += 1
            # weight decay
            g_total = g + weight_decay * shadow.W_op[i][j]
            change = learning_rate * g_total
            shadow.W_op[i][j] -= change
            delta_sq += change*change
    return shadow, {"projected": True, "proj_info": proj_info, "delta_w_l2": round(math.sqrt(delta_sq),6)}

def evaluate_nullspace_update(
    model: Any,
    goal: str, operation: str, concept: str, domain: str,
    probes: Sequence[Any],
    G_history: list[list[float]] | None = None,
    learning_rate: float = 0.05,
    weight_decay: float = 1e-4,
) -> dict[str, Any]:
    """Evaluate a null-space projected update on held-out probes (same gate as weight_update_admission)."""
    from canonical.swe_kernel.weight_update_admission_v1 import ADMIT, REJECT, REFINE, REFUSED, label_is_in_vocabulary, _correct, fingerprint
    base = {"schema": SCHEMA, "authority": "NONE", "whole_capability_proved": False, "trained_goal": goal}
    if not label_is_in_vocabulary(operation, concept, domain):
        return {**base, "verdict": REFUSED, "reason": "TRAINED_LABEL_OUTSIDE_HEAD_VOCABULARY"}
    usable = [p for p in probes if p.goal.strip() != goal.strip()]
    if not probes:
        return {**base, "verdict": REFUSED, "reason": "NO_PROBES_OFFERED"}
    if not usable:
        return {**base, "verdict": REFUSED, "reason": "EVERY_PROBE_IS_THE_TRAINED_GOAL"}
    before = _correct(model, usable)
    if G_history is None:
        G_history = _load_history().get("gradients", [])
    shadow, proj_receipt = _shadow_with_projected_update(model, goal, operation, concept, domain, G_history, learning_rate, weight_decay)
    if not proj_receipt.get("projected"):
        return {**base, "verdict": REFINE, "reason": proj_receipt["proj_info"]["reason"], "proj_receipt": proj_receipt, "counts": {"probes": len(usable), "correct_before": len(before), "correct_after": len(before), "gained":0, "lost":0}}
    after = _correct(shadow, usable)
    gained, lost = after - before, before - after
    counts = {"probes": len(usable), "correct_before": len(before), "correct_after": len(after), "gained": len(gained), "lost": len(lost)}
    report = {**base, "counts": counts, "gained_goals": sorted(gained), "lost_goals": sorted(lost), "proj_receipt": proj_receipt}
    if lost:
        return {**report, "verdict": REJECT, "reason": "BROKE_A_PREDICTION_THAT_WAS_RIGHT_EVEN_IN_NULLSPACE"}
    if not gained:
        return {**report, "verdict": REFINE, "reason": "NO_MEASURED_GAIN_ON_ANY_OTHER_INPUT"}
    return {**report, "verdict": ADMIT, "reason": None}

def apply_nullspace_if_admitted(
    model: Any,
    goal: str, operation: str, concept: str, domain: str,
    probes: Sequence[Any],
    G_history: list[list[float]] | None = None,
    learning_rate: float = 0.05,
    weight_decay: float = 1e-4,
    persist: bool = True,
    history_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Apply null-space projected update only on ADMIT, and append gradient to history."""
    report = evaluate_nullspace_update(model, goal, operation, concept, domain, probes, G_history, learning_rate, weight_decay)
    before_fp = __import__("canonical.swe_kernel.weight_update_admission_v1", fromlist=["fingerprint"]).fingerprint(model)
    if report.get("verdict") != "ADMIT":
        return {**report, "applied": False, "weights_unchanged": True}
    # Apply for real (same projected step but on live model)
    history = G_history if G_history is not None else _load_history(history_path).get("gradients", [])
    shadow, proj_receipt = _shadow_with_projected_update(model, goal, operation, concept, domain, history, learning_rate, weight_decay)
    # copy back shadow weights to live
    model.W_op = shadow.W_op
    model.W_concept = shadow.W_concept
    model.W_domain = shadow.W_domain
    if persist and hasattr(model, "_save"):
        try: model._save()
        except Exception: pass
    # Update history with raw gradient (not projected) for future nullspace
    raw_flat = _gradient_for_goal(model, goal, operation, concept, domain)
    history_data = _load_history(history_path)
    history_data["gradients"].append(raw_flat)
    history_data["tasks"].append({"goal": goal, "operation": operation, "concept": concept, "domain": domain})
    # cap history to 64 tasks (fixed budget, not growing)
    if len(history_data["gradients"]) > 64:
        history_data["gradients"] = history_data["gradients"][-64:]
        history_data["tasks"] = history_data["tasks"][-64:]
    _save_history(history_data, history_path)
    from canonical.swe_kernel.weight_update_admission_v1 import fingerprint as fp
    return {**report, "applied": True, "applied_receipt": proj_receipt, "weights_unchanged": False, "weights_before_sha256": before_fp, "weights_after_sha256": fp(model)}

def main(argv: list[str] | None = None) -> int:
    import tempfile, json, pathlib
    from canonical.swe_kernel.weight_update_admission_v1 import probes_from_goals, stream_goals, fresh_model
    parser = __import__("argparse").ArgumentParser(description="Null-space admission probe")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    built = probes_from_goals(stream_goals())
    probes = built["probes"]
    with tempfile.TemporaryDirectory() as tmp:
        model = fresh_model(pathlib.Path(tmp))
        # Use empty history initially
        report = evaluate_nullspace_update(model, probes[0].goal, probes[0].operation, probes[0].concept, probes[0].domain, [p for p in probes if p.goal != probes[0].goal], G_history=[])
        print(json.dumps(report, indent=2) if args.json else f"verdict={report['verdict']} counts={report.get('counts')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
