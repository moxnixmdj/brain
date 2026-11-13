#!/usr/bin/env python3
"""Predicate World Abstraction & UI-to-Protocol Speed Elevation (`predicate_world_abstraction_v1`).

Closes Wall 3 between finite toy state machines and real computer / browser / repository worlds
with zero external LLM (`K3 = 0`) and `$0` spend by composing four existing repository organs:
  1. Volatile computer-state canonicalization (stripping timestamps, PIDs, UUIDs, nonces, CSRF
     tokens, and render latencies so visiting the same logical state produces the same `state_key`).
  2. `canonical/runtime/htmlform_read_v1.py` — projecting raw HTML/DOM strings onto canonical
     form/input/error predicates instead of raw markup bytes.
  3. `canonical/runtime/world_probe_v1.py` & `canonical/runtime/finite_abstraction_cover_lift_v1.py`
     — lifting concrete Boolean world facts onto verified CNF abstract predicates.
  4. `canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py` — elevating a shortest-path UI/DOM
     plan discovered by `transfer_learning_v1.drive` straight down into `< 5 ms` HTTP/SQLite/CLI
     permanent workflow skills via automatic twin-world self-experimentation (`N=1 -> N=2`).
"""
from __future__ import annotations

import pathlib
import re
from typing import Any, Callable, Hashable, Mapping, Sequence

from canonical.runtime import finite_abstraction_cover_lift_v1 as cover_lift

SCHEMA = "PROJECT_BRAIN_PREDICATE_WORLD_ABSTRACTION_V1"

_VOLATILE_KEYS = frozenset({
    "timestamp",
    "ts",
    "time_ns",
    "created_at",
    "updated_at",
    "at_utc",
    "now",
    "now_utc",
    "pid",
    "ppid",
    "nonce",
    "csrf",
    "csrf_token",
    "_csrf",
    "authenticity_token",
    "request_id",
    "req_id",
    "trace_id",
    "span_id",
    "session_id",
    "elapsed_ms",
    "latency_ms",
    "render_ms",
    "duration_ms",
    "duration_s",
})

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_ISO_TS_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b"
)


def _extract_html_predicates(html_text: str) -> dict[str, Any] | None:
    low = html_text.lower()
    if "<form" not in low and "<input" not in low and "<html" not in low and "<body" not in low:
        return None
    forms_summary: list[dict[str, Any]] = []
    try:
        from canonical.runtime import htmlform_read_v1 as hf

        if hasattr(hf, "read_html"):
            parsed = hf.read_html(html_text)
            if isinstance(parsed, Mapping) and parsed.get("forms") is not None:
                for frm in parsed.get("forms") or []:
                    if isinstance(frm, Mapping):
                        fields = [
                            {
                                "name": f.get("name"),
                                "type": f.get("type"),
                                "required": bool(f.get("required")),
                            }
                            for f in (frm.get("fields") or frm.get("inputs") or [])
                            if isinstance(f, Mapping) and str(f.get("name") or "").lower() not in _VOLATILE_KEYS
                        ]
                        forms_summary.append({
                            "action": frm.get("action") or "",
                            "method": str(frm.get("method") or "GET").upper(),
                            "fields": fields,
                        })
    except Exception:
        pass

    if not forms_summary and "<form" in low:
        for m in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html_text, flags=re.I | re.S):
            attrs, inner = m.group(1), m.group(2)
            act_m = re.search(r'action=["\']([^"\']*)["\']', attrs, re.I)
            met_m = re.search(r'method=["\']([^"\']*)["\']', attrs, re.I)
            inputs = []
            for im in re.finditer(r"<input\b([^>]*)>", inner, re.I):
                nm = re.search(r'name=["\']([^"\']+)["\']', im.group(1), re.I)
                tp = re.search(r'type=["\']([^"\']+)["\']', im.group(1), re.I)
                if nm and nm.group(1).lower() not in _VOLATILE_KEYS:
                    inputs.append((nm.group(1), (tp.group(1) if tp else "text").lower()))
            forms_summary.append({
                "action": act_m.group(1) if act_m else "",
                "method": (met_m.group(1) if met_m else "GET").upper(),
                "inputs": sorted(set(inputs)),
            })

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.I | re.S)
    status_badges = sorted(
        set(re.findall(r'data-state=["\']([^"\']+)["\']', html_text, flags=re.I))
    )
    visible_clean = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html_text, flags=re.I | re.S)
    visible_clean = re.sub(r"<[^>]+>", " ", visible_clean)
    visible_clean = _UUID_RE.sub("<UUID>", _ISO_TS_RE.sub("<TS>", " ".join(visible_clean.split())))
    return {
        "_kind": "html_surface",
        "title": (title_m.group(1).strip() if title_m else ""),
        "forms": forms_summary,
        "states": status_badges,
        "text_sig": visible_clean[:240],
    }


def project_computer_observation(
    observation: Any,
    *,
    cnf_predicates: Sequence[Mapping[str, Any]] | None = None,
    preserve_key_types: bool = False,
) -> Any:
    """Canonicalize a raw computer/browser/API observation into a noise-free hashable structure.

    ``preserve_key_types`` is for observation identity: volatile noise is still stripped,
    but mapping keys are not erased to ``str`` (so ``{1: ...}`` and ``{"1": ...}`` remain
    different observations). Default callers keep the historical string-key projection.
    """
    if observation is None or isinstance(observation, (bool, int, float)):
        return observation

    if isinstance(observation, str):
        html_proj = _extract_html_predicates(observation)
        if html_proj is not None:
            return html_proj
        return _UUID_RE.sub("<UUID>", _ISO_TS_RE.sub("<TS>", observation))

    if isinstance(observation, tuple):
        return tuple(project_computer_observation(x, preserve_key_types=preserve_key_types)
                     for x in observation)

    if isinstance(observation, list):
        return [project_computer_observation(x, preserve_key_types=preserve_key_types)
                for x in observation]

    if isinstance(observation, Mapping):
        cleaned: dict[Any, Any] = {}
        for k, v in observation.items():
            name = str(k)
            if name.lower() in _VOLATILE_KEYS:
                continue
            try:
                out_key = k if preserve_key_types and isinstance(k, Hashable) else name
            except TypeError:
                out_key = name
            if name == "screenshot_bytes" and isinstance(v, (bytes, bytearray)):
                # Project raw screenshot bytes through `osworld_v21_positioned_ocr_observer_v1`
                try:
                    from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot

                    ocr_obs = observe_screenshot(bytes(v))
                    words = sorted({
                        str(it.get("text") or "").strip().lower()
                        for it in (ocr_obs.get("text_items") or [])
                        if isinstance(it, Mapping) and str(it.get("text") or "").strip()
                    })
                    cleaned["ocr_words"] = words
                    for w in words:
                        cleaned[f"ocr_word:{w}"] = True
                except Exception:
                    cleaned["ocr_error"] = True
                continue
            cleaned[out_key] = project_computer_observation(
                v, preserve_key_types=preserve_key_types
            )

        # If structured multi-channel `observed_elements` are present, synthesize Boolean element facts
        raw_els = observation.get("observed_elements")
        if isinstance(raw_els, Sequence) and not isinstance(raw_els, (str, bytes)):
            cleaned["ui_surface_ready"] = len(raw_els) > 0
            for el in raw_els:
                if isinstance(el, Mapping) and el.get("visible", True) and el.get("enabled", True):
                    eid = str(el.get("element_id") or "").strip()
                    if eid:
                        cleaned[f"visible_enabled:{eid}"] = True

        if cnf_predicates:
            # CNF variable names are strings; the abstract predicate surface is not the
            # type-preserving identity surface. Keep the historical string-key behavior here.
            bool_vals = {str(k): bool(v) for k, v in cleaned.items() if isinstance(v, bool)}
            budget = [0]
            var_names = set(bool_vals.keys())
            abstract_out: dict[str, bool] = {}
            for pred in cnf_predicates:
                pname = str(pred.get("name") or "")
                raw_cnf = pred.get("definition_cnf")
                if pname and isinstance(raw_cnf, list):
                    for clause in raw_cnf:
                        if isinstance(clause, list):
                            for lit in clause:
                                if isinstance(lit, str) and lit:
                                    vname = lit[1:] if lit.startswith("!") else lit
                                    if vname:
                                        bool_vals.setdefault(vname, False)
                                        var_names.add(vname)
                    checked = cover_lift._check_cnf(raw_cnf, var_names, budget)
                    abstract_out[pname] = cover_lift._holds(checked, bool_vals)
            return abstract_out
        return cleaned

    return observation


def ground_multichannel_ui_observation(
    observation: Mapping[str, Any],
    *,
    action_request: Mapping[str, Any] | None = None,
    cnf_predicates: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fuse DOM + Accessibility + Positioned OCR (`consensus_dom_grounding` + `osworld_v21_positioned_ocr_observer_v1`)."""
    from canonical.runtime.consensus_dom_grounding import (
        ConsensusRequest,
        ObservedElement,
        ground_consensus_action,
    )

    ocr_items: list[dict[str, Any]] = []
    ocr_words_lower: set[str] = set()
    shot = observation.get("screenshot_bytes")
    if isinstance(shot, (bytes, bytearray)) and shot:
        try:
            from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot

            ocr_rep = observe_screenshot(bytes(shot))
            ocr_items = list(ocr_rep.get("text_items") or [])
            ocr_words_lower = {
                str(it.get("text") or "").strip().casefold()
                for it in ocr_items
                if isinstance(it, Mapping) and str(it.get("text") or "").strip()
            }
        except Exception:
            ocr_items = []

    elements: list[ObservedElement] = []
    for raw_el in observation.get("observed_elements") or []:
        if isinstance(raw_el, ObservedElement):
            elements.append(raw_el)
        elif isinstance(raw_el, Mapping):
            ocr_txt = raw_el.get("ocr_text")
            if ocr_txt is None and ocr_words_lower:
                cand_lbl = str(raw_el.get("text") or raw_el.get("name") or "").strip()
                if cand_lbl and cand_lbl.casefold() in ocr_words_lower:
                    ocr_txt = cand_lbl
            elements.append(
                ObservedElement(
                    element_id=str(raw_el.get("element_id") or ""),
                    role=raw_el.get("role"),
                    name=raw_el.get("name"),
                    text=raw_el.get("text"),
                    ocr_text=ocr_txt,
                    attrs=dict(raw_el.get("attrs") or {}),
                    actions=frozenset(str(a) for a in (raw_el.get("actions") or ("click",))),
                    visible=bool(raw_el.get("visible", True)),
                    enabled=bool(raw_el.get("enabled", True)),
                )
            )

    grounding: dict[str, Any] | None = None
    bool_aug = dict(observation)
    if action_request is not None:
        req_obj = ConsensusRequest(
            action=str(action_request.get("action") or "click"),
            role=action_request.get("role"),
            name=action_request.get("name"),
            text=action_request.get("text"),
            ocr_text=action_request.get("ocr_text"),
            attrs=action_request.get("attrs"),
            min_independent_cues=int(action_request.get("min_independent_cues", 2)),
        )
        grounding = ground_consensus_action(req_obj, elements)
        is_grounded = grounding.get("status") in {"SELECT", "GROUNDED"}
        bool_aug["consensus_grounded"] = is_grounded
        if is_grounded and grounding.get("element_id"):
            bool_aug[f"grounded:{grounding['element_id']}"] = True

    projected = project_computer_observation(bool_aug, cnf_predicates=cnf_predicates)
    return {
        "schema": SCHEMA + "/multichannel_ui_grounding",
        "projected_state": projected,
        "grounding": grounding,
        "ocr_item_count": len(ocr_items),
        "element_count": len(elements),
        "k3_external_llm_calls": 0,
    }


class ProjectedComputerEnv:
    """Adapter presenting canonical predicate observations over a noisy or checkpointed environment."""

    def __init__(
        self,
        raw_env: Any,
        *,
        projector: Callable[[Any], Any] | None = None,
        cnf_predicates: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        self._raw = raw_env
        self._projector = projector
        self._cnf = cnf_predicates
        self._raw_by_proj: dict[str, Any] = {}
        self._initial_checkpoint: Any = None
        if not hasattr(raw_env, "reset") and hasattr(raw_env, "snapshot"):
            self._initial_checkpoint = raw_env.snapshot()

    def reset(self) -> None:
        if hasattr(self._raw, "reset"):
            self._raw.reset()
        elif self._initial_checkpoint is not None and hasattr(self._raw, "restore"):
            self._raw.restore(self._initial_checkpoint)

    def raw_state(self) -> Any:
        return self._raw.state()

    def raw_for_projected(self, projected: Any) -> Any:
        import json

        key = json.dumps(projected, sort_keys=True, default=str)
        return self._raw_by_proj.get(key, projected)

    def state(self) -> Any:
        import json

        raw = self._raw.state()
        proj = (
            self._projector(raw)
            if self._projector is not None
            else project_computer_observation(raw, cnf_predicates=self._cnf)
        )
        self._raw_by_proj[json.dumps(proj, sort_keys=True, default=str)] = raw
        return proj

    def act(self, action: Any) -> Any:
        return self._raw.act(action)

    def snapshot(self) -> Any:
        if hasattr(self._raw, "snapshot"):
            return self._raw.snapshot()
        raise AttributeError("snapshot unavailable")

    def restore(self, snap: Any) -> None:
        if hasattr(self._raw, "restore"):
            self._raw.restore(snap)
            return
        raise AttributeError("restore unavailable")


def explore_and_elevate_computer_env(
    env: Any,
    actions: Sequence[Any],
    *,
    is_goal: Callable[[Any], bool],
    goal_text: str | None = None,
    postcondition: Mapping[str, Any] | None = None,
    extract_trace: Callable[[Any, Sequence[str]], Sequence[Mapping[str, Any]]] | None = None,
    projector: Callable[[Any], Any] | None = None,
    cnf_predicates: Sequence[Mapping[str, Any]] | None = None,
    budget: int = 48,
    max_depth: int = 6,
    seed: int = 0,
    skill_db: pathlib.Path | None = None,
    source_cwd: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Learn/transfer shortest plan on a noisy computer surface, then elevate UI steps to `<5 ms` skill."""
    from canonical.runtime import transfer_learning_v1 as tl
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import compile_and_qualify_skill

    wrapped = env if isinstance(env, ProjectedComputerEnv) else ProjectedComputerEnv(
        env, projector=projector, cnf_predicates=cnf_predicates
    )

    def _wrapped_goal(projected_obs: Any) -> bool:
        raw_obs = wrapped.raw_for_projected(projected_obs)
        try:
            if is_goal(raw_obs):
                return True
        except Exception:
            pass
        try:
            return bool(is_goal(projected_obs))
        except Exception:
            return False

    # Give `_wrapped_goal` a stable name derived from `is_goal` so transfer_learning keys match!
    _wrapped_goal.__name__ = getattr(is_goal, "__name__", "computer_goal")

    drive_res = tl.drive(
        wrapped,
        actions,
        is_goal=_wrapped_goal,
        budget=budget,
        max_depth=max_depth,
        seed=seed,
    )
    out = dict(drive_res)
    out["abstraction_schema"] = SCHEMA

    if (
        drive_res.get("pass")
        and drive_res.get("plan")
        and goal_text
        and postcondition is not None
        and extract_trace is not None
    ):
        kind_to_layer = {
            "pixel_click": "pixel_ui",
            "dom_click": "semantic_dom",
            "sql_exec": "sqlite_exec",
            "sqlite_sql": "sqlite_exec",
            "http": "http_request",
            "http_api": "http_request",
            "cli": "cli_exec",
            "cli_subprocess": "cli_exec",
            "cli_command": "cli_exec",
            "file_write": "python_file_op",
            "file_mutation": "python_file_op",
        }
        raw_trace = []
        for st in extract_trace(env, drive_res["plan"]):
            d = dict(st)
            if "layer" not in d and "kind" in d:
                d["layer"] = kind_to_layer.get(str(d["kind"]), str(d["kind"]))
            raw_trace.append(d)
        if raw_trace:
            qual = compile_and_qualify_skill(
                goal=goal_text,
                trace=raw_trace,
                postcondition=postcondition,
                auto_synthesize_twin=True,
                source_cwd=source_cwd,
                source_channel="noisy_env_predicate_elevation",
                db_path=skill_db,
            )
            out["elevated_skill"] = qual
    return out


# ---------------------------------------------------------------------------
# Wave 4: OSWorld Full Desktop A11y XML Policy & Deterministic Chartography
# ---------------------------------------------------------------------------


def decide_osworld_desktop_action(
    instruction: str,
    *,
    a11y_xml: str | None = None,
    ocr_items: Sequence[Mapping[str, Any]] | None = None,
    history: Sequence[Mapping[str, Any]] | None = None,
    screenshot_sha256: str | None = None,
) -> dict[str, Any]:
    """Zero-LLM desktop A11y XML + OCR decision via `osworld_v21_generic_policy_v1` (`K3 = 0`)."""
    from canonical.runtime.osworld_v21_generic_policy_v1 import decide, parse_a11y

    elements = parse_a11y(a11y_xml)
    state: dict[str, Any] = {
        "instruction": str(instruction),
        "a11y_tree": a11y_xml or "",
        "ocr": list(ocr_items or []),
        "history": list(history or []),
    }
    if screenshot_sha256 is not None:
        state["screenshot_sha256"] = screenshot_sha256
    decision = dict(decide(state))
    return {
        "schema": SCHEMA + "/osworld_desktop_decision",
        "decision": decision,
        "actions": list(decision.get("actions") or []),
        "parsed_element_count": len(elements),
        "parsed_elements": [
            {"tag": el.tag, "label": el.label, "x": el.x, "y": el.y, "clickable": el.clickable, "editable": el.editable}
            for el in elements
        ],
        "k3_external_llm_calls": 0,
    }


def solve_professional_chart_spec(
    spec: Mapping[str, Any],
    *,
    root: str | Any = None,
) -> dict[str, Any]:
    """Read & solve a rendered scientific/professional chart image via `chartography_deterministic_professional_solver_v1`."""
    import pathlib
    from canonical.runtime import chartography_deterministic_professional_solver_v1 as chart_solver

    if root is not None:
        out = dict(chart_solver.run(dict(spec), pathlib.Path(root).resolve()))
    else:
        out = dict(chart_solver.solve(pathlib.Path(str(spec["path"])).resolve(), str(spec.get("prompt") or "")))
    out["k3_external_llm_calls"] = 0
    return out

