"""Unified Closed-Loop Autonomous Controller (`solve_or_learn`) — v1.

Connects the Brain's fast recall, DAG composition, white-box introspection,
sandbox discovery, and causal skill compilation into a single deterministic,
zero-model (`K3=0`, `$0` spend) 4-tier escalation loop:

  Tier 0 (<5 ms)   : Compiled workflow skill recall (`CompiledWorkflowStore`)
                     + `live_brain_route_admission_v1.solve()` front door.
                     Law-pinned honest refusals fail closed immediately and are
                     never bypassed.
  Tier 1 (<150 ms) : Multi-clause `GoalDAGExecutor` with transactional rollback
                     + `composer_route_v1` capability chain composition.
  Tier 2 (<2 s)    : Targeted acquisition & permanent compilation:
                       (a) Optional K2 `demonstration_trace` -> elevated,
                           anti-unified, donor-deleted, and qualified through
                           `capability_transfer_ownership_gate_v1`.
                       (b) Semantic HTML `<form>` discovery -> `<15 ms` HTTP
                           skill compilation & ownership-gate qualification.
                       (c) Fast CLI/pipeline measurement (`computer_env_v1`) ->
                           compiled pipeline skill + ownership-gate qualification.
                       (d) Local Python white-box surface introspection &
                           `documentation_mining_v1`.
  Tier 3 (offline) : `study_open_gaps()` drains `ignorance_ledger_v1` through
                     `curriculum_v1` ordered by earned `p_useful / (1 + cost)`.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import perf_counter_ns
from typing import Any, Mapping
from urllib.parse import parse_qs

from canonical.runtime import computer_execution_boundary_v1 as computer_boundary

from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    compile_and_qualify_skill,
    elevate_trace_to_fastest_layer,
    execute_compiled_steps,
    prune_non_causal_steps_counterfactually,
    recall_and_execute_workflow,
    verify_postcondition,
)
from canonical.swe_kernel.whitebox_introspector_and_trace_synthesizer_v1 import (
    discover_and_execute_semantic_web_form,
    introspect_python_surface,
    rank_callables_for_goal,
)

SCHEMA = "BRAIN_CLOSED_LOOP_AUTONOMOUS_CONTROLLER_V1"

# Law-pinned honest refusal classes that MUST NEVER be overridden or bypassed.
_HONEST_REFUSAL_CLASSES: frozenset[str] = frozenset(
    {
        "STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER",
        "BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT",
        "TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY",
        "PROMISED_SOURCE_CHANGE_NOT_APPLIED",
        "TARGET_SYMBOL_ALREADY_EXISTS",
        "NO_MAGIC_CONSTANT_FOUND",
        "REQUESTED_CONTRACT_CHECKS_NOT_VERIFIED",
        "REMOVAL_REQUIRES_GREEN_BASELINE",
        "REMOVAL_TARGET_NOT_UNIQUE",
        "REQUEST_INVALID",
        "COMPOSITION_EXECUTION_OUTCOME_UNKNOWN",
        "COMPOSED_GOAL_NOT_VERIFIED",
        # A crossfile request whose prose/paths the grammar did not consume is a REAL answer to
        # a real defect in the request: the goal named files it does not bind. Measured
        # 2026-11-03: without this token the refusal was replaced by the generic execution
        # boundary status, because an unrecognised refusal is treated as "serve it by acting".
        # The effect was that `test_extra_goal_requirements_refuse_before_execution` -- a test
        # whose entire point is that the refusal is PRECISE -- read the wrong failure class, and
        # the door lost the reason it had already computed.
        "CROSSFILE_TASK_UNBOUND",
        "MOST_OF_THE_REQUEST_IS_NOT_EXPLAINED_BY_CAPABILITY",
        "REQUEST_WORD_NOT_ACCOUNTED_FOR_BY_CAPABILITY",
        "PROMISED_FILE_NOT_WRITTEN_BY_CAPABILITY",
        computer_boundary.FAILURE_CLASS,
    }
)

_URL_RE = re.compile(r"https?://[^\s'\"<>]+")
_FILE_CAND_RE = re.compile(r"(?:[A-Za-z0-9_./~-]+/)?[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,8}")


def _is_honest_contract_refusal(result: Mapping[str, Any]) -> bool:
    fc = str(result.get("failure_class") or "")
    st = str(result.get("status") or "")
    errs = [str(e) for e in (result.get("stated_answer_payload_errors") or [])]
    for tok in _HONEST_REFUSAL_CLASSES:
        if tok in fc or tok in st or any(tok in e for e in errs):
            return True
    adm = result.get("route_admission")
    if isinstance(adm, Mapping) and str(adm.get("rule") or "") == "R9_REQUIRED_FILE_INPUT_UNBOUND":
        return True
    return False


_LEARNABLE_FRONT_STATUSES: frozenset[str] = frozenset(
    {
        "FAIL__RAW_GOAL_COMPILATION_GAP",
        "FAIL_CLOSED__CAPABILITY_REFUSED_POLYGLOT_REFUSED",
        "FAIL_CLOSED__CAPABILITY_EXECUTION_FAILED",
    }
)


def _is_executable(name: str) -> bool:
    """Does this program exist on this machine? Checked, never assumed."""
    try:
        return bool(pathlib.Path(name).is_file() or shutil.which(name))
    except Exception:
        return False


def _named_executable(goal: str) -> str:
    """A program the goal actually names, that exists on this machine."""
    for tok in str(goal or "").replace(",", " ").replace(";", " ").split():
        t = tok.strip(".,()[]{}\"'")
        if len(t) < 2 or "/" in t:
            continue
        if pathlib.Path(t).is_file() or shutil.which(t):
            return t
    return ""


def _close_matching_ignorance_gaps(goal: str, capability_id: str) -> list[str]:
    """Resolve and close any open ignorance-ledger entry matching `goal` once a verified skill lands."""
    closed: list[str] = []
    if not goal or not capability_id:
        return closed
    try:
        from canonical.runtime import ignorance_ledger_v1 as led

        norm_goal = goal.strip().lower()
        for row in led.rank(limit=128):
            if str(row.get("what") or "").strip().lower() == norm_goal and row.get("id"):
                gid = str(row["id"])
                if led.resolve(gid, helped=True, close=True):
                    closed.append(gid)
    except Exception:
        pass
    return closed


def _promote_r3_episode_if_configured(r3_state_path: pathlib.Path | None) -> dict[str, Any] | None:
    """Drain pending R3 episodes through the Brain-owned independent verifier when configured."""
    if r3_state_path is None or not r3_state_path.is_file():
        return None
    try:
        from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
        from canonical.runtime import r3_improvement_queue_driver_v1 as qdrv

        state = learning.load_state(r3_state_path)
        drained = qdrv.drain(state)
        learning.save_state(r3_state_path, state)
        return {"drained": True, "summary": drained}
    except Exception as exc:
        return {"drained": False, "error": f"{type(exc).__name__}:{str(exc)[:160]}"}


def _deterministic_zero_llm_mcp_substrate(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic `K3 = 0` substrate for `toolathlon_brain_host_integration_v1` (zero external LLM)."""
    from canonical.runtime.brain_unified_model_v1 import tokenize

    if kind == "SUBPROBLEM":
        ctx = str(payload.get("task_context") or "").strip()
        toks = [t for t in tokenize(ctx) if len(t) >= 3 and not t.isdigit()]
        req_caps = toks[:2] if toks else ["general_action"]
        return {
            "goal": ctx[:200] or "execute_mcp_goal",
            "required_capabilities": req_caps,
            "constraint": None,
        }
    if kind == "SCHEMA_JUDGMENT":
        cap = str(payload.get("required_capability") or "").lower().strip()
        anon = payload.get("anonymous_tool") or {}
        desc = str(anon.get("description") or "").lower()
        schema = anon.get("input_schema") if isinstance(anon.get("input_schema"), Mapping) else {}
        props = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
        prop_blob = " ".join(
            f"{k} {v.get('description', '')}" if isinstance(v, Mapping) else str(k)
            for k, v in props.items()
        ).lower()
        hay = f"{desc} {prop_blob}"
        cap_stem = cap.rstrip("s") if len(cap) >= 4 else cap
        supported = bool(cap and (cap in hay or (len(cap_stem) >= 3 and cap_stem in hay)))
        return {"supported": supported, "reason": "deterministic_schema_token_grounding"}
    if kind == "ARGUMENTS":
        ctx = str(payload.get("task_context") or "")
        anon = payload.get("anonymous_selected_tool") or {}
        schema = anon.get("input_schema") if isinstance(anon.get("input_schema"), Mapping) else {}
        props = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
        args_out: dict[str, Any] = {}
        # 1. Explicit `key=value` or `key: value` bindings in `task_context`
        kv_map: dict[str, str] = {}
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*([^\s,;]+)", ctx):
            kv_map[m.group(1).lower()] = m.group(2).strip("\"'()[]{}")
        quoted = [m.group(1) or m.group(2) for m in re.finditer(r"'([^']+)'|\"([^\"]+)\"", ctx)]
        numbers = [m.group(0) for m in re.finditer(r"(?<![A-Za-z0-9_])-?\d+(?:\.\d+)?(?![A-Za-z0-9_])", ctx)]
        urls = [m.group(0).rstrip(".,;)") for m in _URL_RE.finditer(ctx)]
        files = [m.group(0).strip(".,:;()[]'\"") for m in _FILE_CAND_RE.finditer(ctx)]
        q_idx = 0
        n_idx = 0
        for p_name, p_spec in props.items():
            spec_d = p_spec if isinstance(p_spec, Mapping) else {}
            ptype = str(spec_d.get("type") or "string").lower()
            p_low = str(p_name).lower()
            if p_low in kv_map:
                raw_v = kv_map[p_low]
                if ptype == "integer":
                    args_out[p_name] = int(float(raw_v))
                elif ptype == "number":
                    args_out[p_name] = float(raw_v)
                elif ptype == "boolean":
                    args_out[p_name] = raw_v.lower() in {"true", "1", "yes"}
                else:
                    args_out[p_name] = raw_v
                continue
            if ptype == "integer" and n_idx < len(numbers):
                args_out[p_name] = int(float(numbers[n_idx]))
                n_idx += 1
            elif ptype == "number" and n_idx < len(numbers):
                args_out[p_name] = float(numbers[n_idx])
                n_idx += 1
            elif ptype == "boolean":
                args_out[p_name] = bool(re.search(rf"\b{re.escape(p_low)}\b", ctx.lower()))
            elif "url" in p_low and urls:
                args_out[p_name] = urls[0]
            elif ("path" in p_low or "file" in p_low) and files:
                args_out[p_name] = files[0]
            elif q_idx < len(quoted):
                args_out[p_name] = quoted[q_idx]
                q_idx += 1
            elif p_low in {"query", "goal", "task", "text", "prompt"}:
                args_out[p_name] = ctx
        return {"arguments": args_out}
    raise ValueError(f"UNSUPPORTED_MCP_SUBSTRATE_KIND:{kind}")
def _extract_existing_file(goal: str, cwd: pathlib.Path) -> pathlib.Path | None:
    for m in _FILE_CAND_RE.finditer(goal):
        raw = m.group(0).strip(".,:;()[]'\"")
        for base in (cwd, pathlib.Path.cwd()):
            cand = (base / raw).resolve() if not pathlib.Path(raw).is_absolute() else pathlib.Path(raw)
            if cand.is_file():
                return cand
    return None


def _qualify_http_form_skill(
    *,
    goal: str,
    url: str,
    causal_trace: Mapping[str, Any],
    form_body: Mapping[str, Any],
    method: str,
    db_path: pathlib.Path | None,
    hidden_fields: list[str] | None = None,
    stateful_csrf_or_cookie: bool = False,
) -> dict[str, Any]:
    """Spin up an ephemeral local twin server on a fresh port to qualify HTTP transfer."""
    fields = dict(form_body or {})
    hidden_set = set(hidden_fields or [])
    twin_csrf_val = "twin_csrf_token_8a7b6c"

    # Perturb the first NON-HIDDEN parameter in the goal & expected twin server
    perturbed_goal = goal
    perturbed_expected: dict[str, str] = {}
    perturbed_once = False
    for k, v in fields.items():
        if k in hidden_set:
            perturbed_expected[k] = twin_csrf_val
            continue
        sv = str(v)
        if not perturbed_once and sv and sv in perturbed_goal:
            alt = sv + "_twin" if not sv.isdigit() else str(int(sv) + 5)
            perturbed_goal = perturbed_goal.replace(sv, alt, 1)
            perturbed_expected[k] = alt
            perturbed_once = True
        else:
            perturbed_expected[k] = sv

    class _TwinHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            from urllib.parse import urlsplit
            qs = {k: vals[0] for k, vals in parse_qs(urlsplit(self.path).query).items() if vals}
            if stateful_csrf_or_cookie and not qs:
                hidden_html = "".join(
                    f'<input type="hidden" name="{hf}" value="{twin_csrf_val}">'
                    for hf in hidden_set
                )
                body_html = f"<html><body><form method='{method}'>{hidden_html}</form></body></html>".encode("utf-8")
                self.send_response(200)
                self.send_header("Set-Cookie", "twin_session=verified_cookie_1; Path=/")
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body_html)))
                self.end_headers()
                self.wfile.write(body_html)
                return
            ok = all(qs.get(k) == val for k, val in perturbed_expected.items())
            code = 200 if ok else 422
            payload = json.dumps({"ok": ok, "received": qs}).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            ctype = str(self.headers.get("Content-Type") or "")
            if "json" in ctype:
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = {}
            else:
                parsed = {k: vals[0] for k, vals in parse_qs(raw).items() if vals}
            cookie_ok = True
            if stateful_csrf_or_cookie:
                cookie_hdr = str(self.headers.get("Cookie") or "")
                cookie_ok = "twin_session=verified_cookie_1" in cookie_hdr
            ok = cookie_ok and all(str(parsed.get(k, "")) == val for k, val in perturbed_expected.items())
            code = 200 if ok else 422
            payload = json.dumps({"ok": ok, "received": parsed}).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    srv = HTTPServer(("127.0.0.1", 0), _TwinHandler)
    twin_port = srv.server_address[1]
    from urllib.parse import urlsplit, urlunsplit
    sp = urlsplit(url)
    orig_origin = f"{sp.scheme}://{sp.netloc}"
    twin_origin = f"{sp.scheme}://127.0.0.1:{twin_port}"
    perturbed_goal = perturbed_goal.replace(orig_origin, twin_origin)

    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        return compile_and_qualify_skill(
            goal=goal,
            trace=causal_trace,
            postcondition={"kind": "http_status_json", "status": 200, "json_subset": {"ok": True}},
            heldout_goal=perturbed_goal,
            sabotaged_postcondition={"kind": "http_status_json", "status": 200, "json_subset": {"ok": "__IMPOSSIBLE__"}},
            source_channel="tier2_semantic_web_form_to_http",
            db_path=db_path,
        )
    finally:
        srv.shutdown()
        srv.server_close()


def _qualify_cli_measurement_skill(
    *,
    goal: str,
    input_file: pathlib.Path,
    measured_res: Mapping[str, Any],
    cwd: pathlib.Path,
    db_path: pathlib.Path | None,
) -> dict[str, Any]:
    """Elevate a verified `computer_env_v1` CLI/pipeline survivor into a qualified skill."""
    from canonical.runtime import computer_env_v1 as cenv

    survivors = list(measured_res.get("survivors") or [])
    if not survivors:
        return {"pass": False, "reason": "NO_SURVIVORS"}
    hit = survivors[0]
    kind = str(measured_res.get("kind") or "")
    literal = cenv.goal_literal(goal) if kind == "lineswith" else None
    argv = cenv._concretise(hit.get("argv"), literal)
    try:
        rel_in = input_file.relative_to(cwd).as_posix()
    except ValueError:
        rel_in = str(input_file)
    # Use the token representation as written in the goal when present
    goal_file_tok = rel_in
    for m in _FILE_CAND_RE.finditer(goal):
        tok = m.group(0).strip(".,:;()[]'\"")
        if pathlib.Path(tok).name == input_file.name:
            goal_file_tok = tok
            break

    if hit.get("stages") == 2:
        first, second = argv
        argv1 = [first[0]] + [goal_file_tok if a == "probe.txt" else a for a in first[1:]]
        trace = [{"kind": "cli_pipeline", "stages": [argv1, list(second)]}]
    else:
        argv1 = [argv[0]] + [goal_file_tok if a == "probe.txt" else a for a in argv[1:]]
        trace = [{"kind": "cli_exec", "argv": argv1}]

    held_dir = pathlib.Path(tempfile.mkdtemp(prefix="brain_cli_heldout_"))
    try:
        held_name = "twin_" + input_file.name
        held_bytes = cenv.probe_bytes(kind, 11, literal)
        if not held_bytes:
            return {"pass": False, "reason": "NO_HELDOUT_PROBE_BYTES"}
        (held_dir / held_name).write_bytes(held_bytes)
        held_goal = goal.replace(goal_file_tok, held_name)
        return compile_and_qualify_skill(
            goal=goal,
            trace=trace,
            postcondition={"kind": "stdout_integer"},
            heldout_goal=held_goal,
            heldout_cwd=held_dir,
            heldout_postcondition={"kind": "stdout_equals", "expected": "11"},
            sabotaged_postcondition={"kind": "stdout_equals", "expected": "999999"},
            source_channel="tier2_cli_pipeline_discovery",
            db_path=db_path,
        )
    finally:
        shutil.rmtree(held_dir, ignore_errors=True)


def solve_or_learn(
    request: Mapping[str, Any] | str,
    *,
    learn: bool = True,
    registry_path: str | None = None,
    cwd: str | pathlib.Path | None = None,
    db_path: str | pathlib.Path | None = None,
    r3_state_path: str | pathlib.Path | None = None,
    allow_tier1_composition: bool = True,
    allow_tier2_learning: bool = True,
    allow_jit_network: bool = True,
    record_open_gap: bool = True,
    confinement_admitted: bool = False,
) -> dict[str, Any]:
    if type(learn) is not bool:
        raise ValueError("LEARN_FLAG_MUST_BE_BOOL")
    # A mapping request may carry its own `learn` flag (e.g. front-door calls
    # that must stay read-only). It is honoured here rather than ignored.
    if isinstance(request, Mapping) and "learn" in request:
        request_learn = request["learn"]
        if type(request_learn) is not bool:
            raise ValueError("LEARN_FLAG_MUST_BE_BOOL")
        learn = request_learn
    from canonical.runtime.memory_policy_v1 import OFF, READ_WRITE, can_read_memory, memory_policy_scope

    with memory_policy_scope(READ_WRITE if learn else OFF):
        t0_wrap = perf_counter_ns()
        res = _solve_or_learn_impl(
            request,
            learn=bool(learn and can_read_memory()),
            registry_path=registry_path,
            cwd=cwd,
            db_path=db_path,
            r3_state_path=r3_state_path,
            allow_tier1_composition=allow_tier1_composition,
            allow_tier2_learning=allow_tier2_learning,
            allow_jit_network=allow_jit_network,
            record_open_gap=bool(record_open_gap and learn and can_read_memory()),
            confinement_admitted=confinement_admitted,
        )
        if learn and can_read_memory() and isinstance(res, dict):
            try:
                from canonical.swe_kernel.sentient_cognitive_core_v1 import shared_cognitive_core

                core = shared_cognitive_core(None)
                g_txt = request if isinstance(request, str) else str(request.get("goal") or "")
                t_id = "autonomous-solve" if isinstance(request, str) else str(request.get("task_id") or "autonomous-solve")
                core.record_wake_episode(
                    task_id=t_id,
                    goal=g_txt,
                    outcome_pass=bool(res.get("pass") is True),
                    route_id=str(res.get("tier_used") or res.get("status") or "solve_or_learn"),
                    elapsed_ms=max(0.05, (perf_counter_ns() - t0_wrap) / 1e6),
                )
            except Exception:
                pass

            # Self-Reflective Learning: Reflect on execution to build understanding
            try:
                from canonical.swe_kernel.self_reflective_learning_system_v1 import get_learning_system
                learning_system = get_learning_system()
                goal_text = request if isinstance(request, str) else str(request.get("goal") or "")
                task_id_text = "autonomous-solve" if isinstance(request, str) else str(request.get("task_id") or "autonomous-solve")
                
                # Execute and reflect on the task
                reflection = learning_system.execute_and_reflect(
                    task=goal_text,
                    execution_result={
                        "status": "PASS" if res.get("pass") else "FAIL",
                        "answer": res.get("answer", ""),
                        "error": res.get("error", ""),
                    }
                )
                
                # Store the reflection for future reasoning
                learning_system.learn_from_reflection(reflection)
                
                # Add reflection metadata to result
                if isinstance(res, dict):
                    res["self_reflection"] = {
                        "task_id": reflection.task_id,
                        "success": reflection.success,
                        "causal_models_built": len(learning_system.causal_models),
                        "abstract_concepts": len(learning_system.abstract_concepts),
                        "transferable_principles": len(learning_system.transferable_principles),
                    }
            except Exception as e:
                # Self-reflection is non-critical, continue even if it fails
                pass

        return res


def _solve_or_learn_impl(
    request: Mapping[str, Any] | str,
    *,
    learn: bool = True,
    registry_path: str | None = None,
    cwd: str | pathlib.Path | None = None,
    db_path: str | pathlib.Path | None = None,
    r3_state_path: str | pathlib.Path | None = None,
    allow_tier1_composition: bool = True,
    allow_tier2_learning: bool = True,
    allow_jit_network: bool = True,
    record_open_gap: bool = True,
    confinement_admitted: bool = False,
) -> dict[str, Any]:
    """Execute a request at maximum speed, or learn & crystallize the missing skill in-run."""
    t0 = perf_counter_ns()
    if isinstance(request, str):
        req: dict[str, Any] = {"task_id": "autonomous-solve", "goal": request}
    else:
        req = dict(request)
    if confinement_admitted:
        req["confinement_admitted"] = True

    goal = str(req.get("goal") or "").strip()
    task_id = str(req.get("task_id") or "autonomous-solve")
    # Tier 0 performs its own recall before the door. A door-only policy must
    # not be silently accepted here as though it governed that earlier tier.
    if "route_memory_mode" in req:
        return {"schema": SCHEMA, "task_id": task_id, "pass": False, "executed": False,
                "status": "FAIL_CLOSED__ROUTE_MEMORY_MODE_UNSUPPORTED_BY_CONTROLLER",
                "failure_class": "ROUTE_MEMORY_MODE_UNSUPPORTED_BY_CONTROLLER",
                "semantic_acceptance_complete": False}
    work_cwd = pathlib.Path(cwd or req.get("cwd") or pathlib.Path.cwd()).resolve()
    skill_db = pathlib.Path(db_path) if db_path is not None else None
    r3_path = pathlib.Path(r3_state_path) if r3_state_path is not None else None

    _has_structured_specialist = any(
        k in req
        for k in (
            "ambiguity_problem",
            "sense_problem",
            "semantic_relation_problem",
            "domain_mapping_problem",
            "polytope_problem",
            "cross_document_problem",
            "r2_adequacy_request",
            "policy_adequacy_problem",
            "policy_cover_payload",
            "escape_repair_state",
            "scientific_discovery_problem",
            "ooxml_preflight_target",
            "trace_capsule_problem",
            "byte_verified_bridge",
            "tool_schemas",
            "api_endpoints",
            "dom_action",
            "dom_elements",
            "perf_target",
            "repair_command",
        )
    )
    if work_cwd != pathlib.Path(__file__).resolve().parents[2]:
        req.setdefault("workspace_root", str(work_cwd))

    def _typed_python_ast_lane() -> dict[str, Any] | None:
        """Bounded read-only AST adapter. Similarity is never an executor."""
        if not goal or _has_structured_specialist:
            return None
        from canonical.swe_kernel import python_ast_query_v1 as ast_query

        try:
            typed = ast_query.solve_query(goal, root=work_cwd)
        except ast_query.PythonAstQueryError as exc:
            # The bounded adapter is not the whole read-only surface. If the
            # current sentence is outside its small grammar, let the verified
            # compositional engine/door try; safety refusals still fail closed.
            if exc.code in {"UNSUPPORTED_TARGET", "UNSUPPORTED_QUERY_SHAPE"}:
                try:
                    ast_query.check_source_confinement(goal, root=work_cwd)
                except ast_query.PythonAstQueryError as confined_exc:
                    out = ast_query.failure_result(confined_exc)
                    out.update(schema=SCHEMA, task_id=task_id,
                               elapsed_ms=round((perf_counter_ns() - t0) / 1e6, 3))
                    return out
                return None
            out = ast_query.failure_result(exc)
            out.update(schema=SCHEMA, task_id=task_id,
                       elapsed_ms=round((perf_counter_ns() - t0) / 1e6, 3))
            return out
        if typed is None:
            return None
        typed.update(schema=SCHEMA, task_id=task_id, executed=True,
                     semantic_acceptance_complete=False,
                     elapsed_ms=round((perf_counter_ns() - t0) / 1e6, 3))
        return typed
    if not learn:
        allow_tier2_learning = False
        record_open_gap = False
    if not learn and not _has_structured_specialist:
        typed = _typed_python_ast_lane()
        if typed is not None:
            return typed
        from canonical.runtime import live_brain_route_admission_v1 as ra

        door_req = dict(req)
        door_req.setdefault("task_id", task_id)
        door_req["route_memory_mode"] = "exclude"
        return ra.solve(door_req)

    if not goal:
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "pass": False,
            "status": "FAIL_CLOSED__EMPTY_GOAL",
            "tier_used": "tier0_validation",
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    # ------------------------------------------------------------------
    # Optional K2 Acquisition-Time Demonstration Compile (Donor Deleted
    # Before Qualification, Mandatory Transfer Ownership Gate).
    # ------------------------------------------------------------------
    demo_trace = req.pop("demonstration_trace", None) or req.pop("acquisition_trace", None)
    demo_post = req.pop("postcondition", None)
    qualification_receipt: dict[str, Any] | None = None
    if isinstance(demo_trace, list) and demo_trace and isinstance(demo_post, Mapping):
        # Qualification executes the supplied trace. It must not precede a
        # reviewed boundary and effect admission merely because it is called a demo.
        return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                "status": computer_boundary.STATUS,
                "failure_class": computer_boundary.FAILURE_CLASS,
                "executed": False, "semantic_acceptance_complete": False,
                "tier_used": "unconfined_demonstration_refused",
                "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3)}

    # ------------------------------------------------------------------
    # ROUND-0 PATHOLOGY PRECHECK (`experience_v1` + `flywheel_v1`, < 0.5 ms)
    #         + Earned-Importance Associative Memory (`associative_memory_v1`)
    # ------------------------------------------------------------------
    exp_state_path = req.pop("experience_state_path", None)
    fly_state_path = req.pop("flywheel_state_path", None)
    assoc_mem_path = req.pop("associative_memory_path", None)
    assoc_recalled: list[dict[str, Any]] = []
    if assoc_mem_path is not None:
        try:
            from canonical.runtime import associative_memory_v1 as amem

            assoc_recalled = list(amem.recall(goal, k=5, path=str(assoc_mem_path)) or [])
        except Exception:
            assoc_recalled = []

    def _credit_assoc_memory(helped: bool, learned_note: Any = None) -> dict[str, Any] | None:
        if assoc_mem_path is None:
            return None
        try:
            from canonical.runtime import associative_memory_v1 as amem

            mp = str(assoc_mem_path)
            credited = 0
            for r_row in assoc_recalled:
                rid = str(r_row.get("id") or "")
                if rid and amem.credit(rid, helped=bool(helped), path=mp):
                    credited += 1
            remembered_id = None
            if helped and learned_note is not None:
                remembered_id = amem.remember(learned_note, kind="verified_resolution", tags=("solve_or_learn",), path=mp)
                amem.forget(capacity=5000, path=mp)
            return {
                "recalled_count": len(assoc_recalled),
                "credited_count": credited,
                "remembered_id": remembered_id,
            }
        except Exception:
            return None

    round0_meta: dict[str, Any] = {}
    try:
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            round0_pathology_precheck,
        )

        round0_meta = round0_pathology_precheck(
            goal,
            [],
            experience_state_path=str(exp_state_path) if exp_state_path else None,
            flywheel_state_path=str(fly_state_path) if fly_state_path else None,
        )
    except Exception:
        round0_meta = {}

    # ------------------------------------------------------------------
    # TIER 0-SEMANTIC (<2 ms): Lossless Ambiguity/Sense/Relation Control,
    # Exact Rational Polytopes, Cross-Doc Semantic Lattice, Unfamiliar Tool
    # Schema Planning, Browser/DOM Grounding & Perf/Command Diagnostics
    # ------------------------------------------------------------------
    amb_prob = (
        req.pop("ambiguity_problem", None)
        or req.pop("sense_problem", None)
        or req.pop("semantic_relation_problem", None)
        or req.pop("domain_mapping_problem", None)
    )
    if isinstance(amb_prob, Mapping):
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            evaluate_semantic_ambiguity_and_sense,
        )

        amb_out = evaluate_semantic_ambiguity_and_sense(amb_prob)
        passed_amb = bool(amb_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_amb, {"goal": goal, "organ": amb_out.get("control_organ")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_amb,
            "status": str(amb_out.get("status") or ("PASS__SEMANTIC_AMBIGUITY_RESOLVED" if passed_amb else "FAIL_CLOSED__AMBIGUITY_REQUIRES_SEPARATOR")),
            "tier_used": "tier0_semantic_ambiguity_sense_control",
            "semantic_control": amb_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    poly_prob = req.pop("polytope_problem", None)
    if isinstance(poly_prob, Mapping):
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            solve_exact_rational_polytope,
        )

        poly_out = solve_exact_rational_polytope(poly_prob)
        passed_poly = bool(poly_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_poly, {"goal": goal, "organ": "exact_linear_parameter_polytope_v1"})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_poly,
            "status": str(poly_out.get("status") or ("PASS__EXACT_RATIONAL_POLYTOPE" if passed_poly else "FAIL_CLOSED__POLYTOPE_INFEASIBLE")),
            "tier_used": "tier0_exact_linear_parameter_polytope",
            "polytope": poly_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    xdoc_prob = req.pop("cross_document_problem", None)
    xdoc_ver = req.pop("cross_document_relation_verifier", None)
    if isinstance(xdoc_prob, Mapping):
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            evaluate_cross_document_semantic_lattice,
        )

        xdoc_out = evaluate_cross_document_semantic_lattice(
            xdoc_prob,
            relation_verifier=xdoc_ver if callable(xdoc_ver) else None,
        )
        passed_xdoc = bool(xdoc_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_xdoc, {"goal": goal, "organ": "cross_document_effect_semantic_lattice_v8"})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_xdoc,
            "status": str(xdoc_out.get("status") or ("PASS__CROSS_DOCUMENT_LATTICE_CLOSED" if passed_xdoc else "FAIL_CLOSED__CROSS_DOCUMENT_LATTICE")),
            "tier_used": "tier0_cross_document_semantic_lattice_v8",
            "cross_document_lattice": xdoc_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    tool_schemas = req.pop("tool_schemas", None) or req.pop("api_endpoints", None)
    tool_executor = req.pop("tool_executor", None)
    tool_obs = req.pop("tool_observations", ())
    if isinstance(tool_schemas, (list, tuple)) and tool_schemas:
        from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
            plan_and_execute_unfamiliar_tool_schemas,
        )

        ts_out = plan_and_execute_unfamiliar_tool_schemas(
            goal,
            tool_schemas,
            executor=tool_executor if callable(tool_executor) else None,
            initial_observations=tool_obs if isinstance(tool_obs, (list, tuple)) else (),
        )
        passed_ts = bool(ts_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_ts, {"goal": goal, "organ": "generic_goal_tool_effect_planner_v2"})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_ts,
            "status": str(ts_out.get("status")),
            "tier_used": "tier1_unfamiliar_tool_effect_planner_v2",
            "tool_plan_result": ts_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    dom_action = req.pop("dom_action", None)
    dom_elements = req.pop("dom_elements", None)
    if isinstance(dom_action, Mapping) or isinstance(dom_elements, (list, tuple)):
        from canonical.runtime.computer_env_v1 import ground_dom_or_browser_surface

        dom_out = ground_dom_or_browser_surface(
            goal,
            action_spec=dom_action if isinstance(dom_action, Mapping) else None,
            dom_elements=dom_elements if isinstance(dom_elements, (list, tuple)) else None,
        )
        passed_dom = bool(dom_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_dom, {"goal": goal, "organ": dom_out.get("grounding_stage")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_dom,
            "status": "PASS__DOM_GROUNDING_SELECTED" if passed_dom else f"FAIL_CLOSED__DOM_{dom_out.get('status')}",
            "tier_used": "tier1_dom_browser_grounding",
            "dom_grounding": dom_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    perf_target = req.pop("perf_target", None)
    perf_git_ref = req.pop("perf_git_ref", None)
    if perf_target is not None:
        from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
            diagnose_and_verify_performance_or_architecture,
        )

        p_out = diagnose_and_verify_performance_or_architecture(
            perf_target,
            goal,
            git_ref=str(perf_git_ref) if perf_git_ref else None,
        )
        passed_p = bool(p_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_p, {"goal": goal, "organ": p_out.get("diagnostic_organ")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_p,
            "status": "PASS__PERF_OR_DESIGN_DIAGNOSTIC_VERIFIED" if passed_p else "FAIL_CLOSED__PERF_DIAGNOSTIC",
            "tier_used": "tier1_perf_and_design_diagnostics",
            "diagnostics": p_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    repair_cmd = req.pop("repair_command", None)
    repair_stderr = req.pop("repair_stderr", "")
    repair_exit = req.pop("repair_exit_code", 1)
    if repair_cmd is not None:
        from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
            diagnose_command_failure_and_transfer_strategy,
        )

        rc_out = diagnose_command_failure_and_transfer_strategy(
            str(repair_cmd),
            str(repair_stderr or ""),
            int(repair_exit),
            root=work_cwd,
        )
        passed_rc = bool(rc_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_rc, {"goal": goal, "diagnosis": rc_out["diagnosis"].get("class")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_rc,
            "status": "PASS__COMMAND_FAILURE_DIAGNOSED_AND_STRATEGY_COMPILED" if passed_rc else "FAIL_CLOSED__UNDIAGNOSED_COMMAND_FAILURE",
            "tier_used": "tier2_command_repair_and_transfer_strategy",
            "command_repair": rc_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    r2_req = req.pop("r2_adequacy_request", None)
    if isinstance(r2_req, Mapping):
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            evaluate_r2_direct_or_fixed_point_adequacy,
        )

        r2_spec = dict(r2_req)
        inner_req = r2_spec.pop("request", None) or {"task_id": task_id, "goal": goal, **r2_spec}
        r2_out = evaluate_r2_direct_or_fixed_point_adequacy(
            inner_req,
            repo_root=str(r2_spec.pop("repo_root", work_cwd)),
            information_provider=r2_spec.pop("information_provider", None),
            proposal_provider=r2_spec.pop("proposal_provider", None),
            capability_expander=r2_spec.pop("capability_expander", None),
            execution_provider=r2_spec.pop("execution_provider", None),
            max_fixed_point_steps=int(r2_spec.pop("max_fixed_point_steps", 8)),
            preflight_only=bool(r2_spec.pop("preflight_only", False)),
        )
        passed_r2 = bool(r2_out.get("pass") is True or r2_out.get("matched") is True)
        mem_rec = _credit_assoc_memory(passed_r2, {"goal": goal, "organ": r2_out.get("control_organ")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_r2,
            "status": str(r2_out.get("status") or ("PASS__R2_ADEQUACY_VERIFIED" if passed_r2 else "FAIL_CLOSED__R2_ADEQUACY")),
            "tier_used": "tier0_r2_direct_or_fixed_point_adequacy",
            "r2_adequacy": r2_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    pol_prob = (
        req.pop("policy_adequacy_problem", None)
        or req.pop("policy_cover_payload", None)
        or req.pop("escape_repair_state", None)
    )
    if isinstance(pol_prob, Mapping):
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            solve_policy_adequacy_or_escape_repair,
        )

        pol_out = solve_policy_adequacy_or_escape_repair(
            pol_prob,
            repo_root=str(req.pop("policy_repo_root", work_cwd)),
            provider=req.pop("escape_repair_provider", None),
            verifier=req.pop("escape_repair_verifier", None),
            max_rounds=int(req.pop("escape_repair_max_rounds", 4)),
        )
        passed_pol = bool(pol_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_pol, {"goal": goal, "organ": pol_out.get("control_organ")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_pol,
            "status": str(pol_out.get("status") or ("PASS__POLICY_ADEQUACY_VERIFIED" if passed_pol else "FAIL_CLOSED__POLICY_ADEQUACY")),
            "tier_used": "tier1_policy_adequacy_or_escape_repair",
            "policy_adequacy": pol_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    sci_prob = req.pop("scientific_discovery_problem", None)
    if isinstance(sci_prob, Mapping):
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            discover_symbolic_or_scientific_law,
        )

        sci_out = discover_symbolic_or_scientific_law(sci_prob)
        passed_sci = bool(sci_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_sci, {"goal": goal, "organ": sci_out.get("discovery_organ")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_sci,
            "status": str(sci_out.get("status")),
            "tier_used": "tier2_symbolic_or_scientific_law_discovery",
            "scientific_discovery": sci_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    ooxml_target = req.pop("ooxml_preflight_target", None)
    if ooxml_target is not None:
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            preflight_professional_ooxml_artifact,
        )

        ooxml_out = preflight_professional_ooxml_artifact(ooxml_target)
        passed_ooxml = bool(ooxml_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_ooxml, {"goal": goal, "organ": "professional_artifact_hard_defect_preflight_v1"})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_ooxml,
            "status": str(ooxml_out.get("status") or ("PASS__OOXML_HARD_DEFECT_PREFLIGHT" if passed_ooxml else "FAIL_CLOSED__OOXML_DEFECT")),
            "tier_used": "tier0_ooxml_hard_defect_preflight",
            "ooxml_preflight": ooxml_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    cap_prob = req.pop("trace_capsule_problem", None)
    if isinstance(cap_prob, Mapping):
        from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
            compile_and_verify_execution_capsule,
        )

        cap_out = compile_and_verify_execution_capsule(
            problem=cap_prob.get("problem"),
            planned=cap_prob.get("planned"),
            execution=cap_prob.get("execution"),
            macrosteps=cap_prob.get("macrosteps"),
            rollback_target_hash=cap_prob.get("rollback_target_hash"),
            project_requires=cap_prob.get("project_requires"),
        )
        passed_cap = bool(cap_out.get("pass") is True)
        mem_rec = _credit_assoc_memory(passed_cap, {"goal": goal, "organ": cap_out.get("capsule_organ")})
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "goal": goal,
            "pass": passed_cap,
            "status": str(cap_out.get("status")),
            "tier_used": "tier1_provenance_execution_capsule",
            "execution_capsule": cap_out,
            "associative_memory": mem_rec,
            "k3_external_llm_calls": 0,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    # ------------------------------------------------------------------
    # TIER 0A (<2 ms): Recall Compiled & Ownership-Qualified Workflow Skill
    #                  + Self-Forged Capability Spine (`forged.*`)
    # ------------------------------------------------------------------
    # Do not let the fast recall tier jump ahead of the confinement refusal
    # for the computer-task shapes identified below. Other tiers are not
    # thereby certified as confined.
    from canonical.runtime import live_brain_route_admission_v1 as ra
    from canonical.runtime import computer_env_v1 as cenv
    try:
        computer_shape = (ra._serve_by_acting({"goal": goal}) is not None
                          or cenv.query_kind(goal) is not None
                          or any(ext in goal.lower() for ext in (".tar.gz", ".tar.bz2", ".tar.xz")))
    except Exception:
        computer_shape = True  # a failed classification cannot authorize recall
    recalled = None if (not learn or computer_shape) else recall_and_execute_workflow(goal, cwd=work_cwd, db_path=skill_db)
    if recalled is not None and recalled.get("status") == computer_boundary.STATUS:
        out = dict(recalled)
        out.update(controller_schema=SCHEMA, task_id=task_id,
                   tier_used="tier0_unconfined_workflow_refused",
                   elapsed_ms=round((perf_counter_ns() - t0) / 1e6, 3))
        return out
    if recalled is not None and recalled.get("pass") is True:
        receipts = list(recalled.get("step_receipts") or [])
        last_step = receipts[-1] if receipts else {}
        ans = last_step.get("stdout") or last_step.get("response_preview") or last_step.get("rows")
        return {
            "schema": SCHEMA,
            "task_id": task_id,
            "pass": True,
            "status": "PASS__TIER0_COMPILED_SKILL_RECALL",
            "tier_used": "tier0_compiled_skill_recall",
            "from_memory": True,
            "skill_id": recalled.get("skill_id"),
            "fastest_layer": recalled.get("dominant_layer"),
            "answer": ans,
            "step_receipts": receipts,
            "qualification_receipt": qualification_receipt,
            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
        }

    # ------------------------------------------------------------------
    # TIER 0A-SEMANTIC (<25 ms): Neuro-symbolic compositional & causal
    # generalization. Replaces the old TF-IDF keyword lookup: typed
    # SemanticTaskAST -> explicit synthesized program -> interventional
    # verification -> only then an answer. Structured answers (int counts,
    # name lists, dict breakdowns), and fail-closed refusals otherwise.
    # The volatile policy update is kept in-memory; this tier never
    # silently mutates tracked experience state.
    # ------------------------------------------------------------------
    if learn and recalled is None:
        typed = _typed_python_ast_lane()
        if typed is not None:
            return typed
        try:
            from canonical.swe_kernel.semantic_generalization_engine_v1 import (
                GeneralizationEngine,
            )

            sem_engine = GeneralizationEngine()
            sem_result = sem_engine.solve_task(
                goal,
                work_cwd=work_cwd,
                top_k=3,
                persist_policy=False,
                store_experience=False,
            )

            if sem_result.get("pass") is True:
                out = dict(sem_result)
                out["schema"] = SCHEMA
                out["task_id"] = task_id
                out["status"] = "PASS__TIER0A_SEMANTIC_GENERALIZATION"
                out["tier_used"] = "tier0a_semantic_generalization"
                out["from_memory"] = False
                out["elapsed_ms"] = round((perf_counter_ns() - t0) / 1e6, 3)
                return out
        except Exception:
            pass

    forged_state_path = req.pop("forged_state_path", None)
    macro_state_path = req.pop("macro_state_path", None)
    if learn:
        try:
            from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
                match_and_invoke_forged_for_goal,
            )

            forged_hit = match_and_invoke_forged_for_goal(
                goal,
                root=work_cwd,
                state_path=forged_state_path,
                explicit_args=req.get("forged_args") if isinstance(req.get("forged_args"), Mapping) else None,
            )
            if forged_hit is not None and forged_hit.get("pass") is True:
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "pass": True,
                    "status": "PASS__TIER0_FORGED_CAPABILITY_EXECUTED",
                    "tier_used": "tier0_forged_capability",
                    "from_memory": True,
                    "capability_id": forged_hit["capability_id"],
                    "forged_execution": forged_hit,
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }
        except Exception:
            pass

    # Explicit 2-step byte-verified capability bridge (`bridge_enumeration_v1`)
    bridge_spec = req.get("byte_verified_bridge")
    if allow_tier1_composition and isinstance(bridge_spec, Mapping):
        try:
            from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
                execute_byte_verified_two_step_bridge,
            )

            b_out = execute_byte_verified_two_step_bridge(
                producer_cid=str(bridge_spec["producer_cid"]),
                producer_args=dict(bridge_spec.get("producer_args") or {}),
                artifact_type=str(bridge_spec["artifact_type"]),
                consumer_cid=str(bridge_spec["consumer_cid"]),
                consumer_artifact_arg=str(bridge_spec["consumer_artifact_arg"]),
                consumer_extra_args=dict(bridge_spec.get("consumer_extra_args") or {}),
                root=work_cwd,
            )
            if b_out.get("pass") is True:
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "pass": True,
                    "status": "PASS__TIER1_BYTE_VERIFIED_CAPABILITY_BRIDGE",
                    "tier_used": "tier1_byte_verified_bridge",
                    "from_memory": False,
                    "bridge_result": b_out,
                    "round0_precheck": round0_meta,
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }
        except Exception:
            pass

    # ------------------------------------------------------------------
    # TIER 0B: Front-Door Bound Capability Admission (`solve`)
    # ------------------------------------------------------------------
    from canonical.runtime import live_brain_route_admission_v1 as ra

    clean_req = {
        k: v
        for k, v in req.items()
        if k
        not in {
            "heldout_goal",
            "heldout_cwd",
            "heldout_postcondition",
            "sabotaged_postcondition",
            "gui_action",
            "gui_screen",
            "gui_env",
            "osworld_obs",
            "osworld_env",
            "mcp_rpc",
            "harbor_env",
            "forged_args",
            "byte_verified_bridge",
        }
    }
    if macro_state_path is not None:
        clean_req["_macro_state_path"] = str(macro_state_path)
    if not learn:
        clean_req["route_memory_mode"] = "exclude"
    if work_cwd != pathlib.Path(__file__).resolve().parents[2]:
        clean_req.setdefault("workspace_root", str(work_cwd))
    clean_req.setdefault("task_id", task_id)
    front_res = ra.solve(clean_req)
    if front_res.get("pass") is True:
        out = dict(front_res)
        out["controller_schema"] = SCHEMA
        out["tier_used"] = "tier0_bound_capability"
        out["elapsed_ms"] = round((perf_counter_ns() - t0) / 1e6, 3)
        return out

    # Respect law-pinned honest refusals immediately — except when `work_cwd`
    # itself is an external target repository with failing tests (`2B-Repo`), where
    # single-file `R9_REQUIRED_FILE_INPUT_UNBOUND` / `STATED_SWE_EFFECT_UNSERVED`
    # simply indicates the repair request is repository-scoped rather than single-file.
    adm_rule = str(((front_res.get("route_admission") or {}) if isinstance(front_res.get("route_admission"), Mapping) else {}).get("rule") or "")
    front_status = str(front_res.get("status") or "")
    is_repo_scoped_repair = (
        (adm_rule == "R9_REQUIRED_FILE_INPUT_UNBOUND" or "STATED_SWE_EFFECT_UNSERVED" in front_status)
        and work_cwd != pathlib.Path(__file__).resolve().parents[2]
        and any(w in goal.lower() for w in ("fix", "repair", "failing tests", "make all tests pass"))
        and any(work_cwd.rglob("test_*.py"))
    )
    if ((_is_honest_contract_refusal(front_res) and not is_repo_scoped_repair)
            or front_res.get("side_effects_may_exist") is True):
        out = dict(front_res)
        out["controller_schema"] = SCHEMA
        out["tier_used"] = ("tier0_uncertain_side_effects_refusal"
                            if front_res.get("side_effects_may_exist") is True
                            else "tier0_honest_contract_refusal")
        out["elapsed_ms"] = round((perf_counter_ns() - t0) / 1e6, 3)
        return out

    # ------------------------------------------------------------------
    # TIER 1 (<150 ms): Multi-Clause Goal DAG & Capability Chain Composer
    # ------------------------------------------------------------------
    if allow_tier1_composition:
        from canonical.swe_kernel.goal_dag_executor_v1 import execute_transactional_goal_dag

        clauses = [
            c.strip()
            for c in re.split(r"\s*(?:;\s+|\bthen\b|\band\s+then\b)\s*", goal, flags=re.IGNORECASE)
            if c and c.strip()
        ]
        if len(clauses) >= 2:
            from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
                lookup_verified_chain_macro,
                record_verified_chain_macro,
            )

            macro_hit = lookup_verified_chain_macro(clauses, state_path=macro_state_path)
            dag_res = execute_transactional_goal_dag(
                root=work_cwd,
                stages=clauses,
                stage_solver=lambda sub_goal, idx: ra.solve({"task_id": f"{task_id}-s{idx}", "goal": sub_goal}),
            )
            if dag_res.get("ok") is True:
                stage_recs = list(dag_res.get("stage_receipts") or [])
                macro_recorded = record_verified_chain_macro(
                    clauses,
                    [{"capability_id": r.get("capability_id") or "step", "verified": True} for r in stage_recs],
                    state_path=macro_state_path,
                )
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "pass": True,
                    "status": "PASS__TIER1_GOAL_DAG_COMPOSITION",
                    "tier_used": "tier1_goal_dag",
                    "from_memory": bool(macro_hit is not None),
                    "from_macro": bool(macro_hit is not None),
                    "macro_recorded": bool(macro_recorded),
                    "macro_key": (macro_hit or {}).get("key"),
                    "clauses": clauses,
                    "dag_result": dag_res,
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }

        composer_dispatch_started = False
        bridge_spec = req.get("byte_verified_bridge")
        if isinstance(bridge_spec, Mapping):
            try:
                from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
                    execute_byte_verified_two_step_bridge,
                )

                b_out = execute_byte_verified_two_step_bridge(
                    producer_cid=str(bridge_spec["producer_cid"]),
                    producer_args=dict(bridge_spec.get("producer_args") or {}),
                    artifact_type=str(bridge_spec["artifact_type"]),
                    consumer_cid=str(bridge_spec["consumer_cid"]),
                    consumer_artifact_arg=str(bridge_spec["consumer_artifact_arg"]),
                    consumer_extra_args=dict(bridge_spec.get("consumer_extra_args") or {}),
                    root=work_cwd,
                )
                if b_out.get("pass") is True:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "pass": True,
                        "status": "PASS__TIER1_BYTE_VERIFIED_CAPABILITY_BRIDGE",
                        "tier_used": "tier1_byte_verified_bridge",
                        "from_memory": False,
                        "bridge_result": b_out,
                        "round0_precheck": round0_meta,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        try:
            from canonical.runtime import composer_route_v1 as croute
            from canonical.runtime.live_brain_route_admission_v1 import (
                _cached_composer_graph,
            )

            try:
                routed = croute.route(goal, g=_cached_composer_graph())
            except TypeError:
                routed = croute.route(goal)
            if routed.get("status") == computer_boundary.STATUS:
                return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                        "status": computer_boundary.STATUS,
                        "failure_class": computer_boundary.FAILURE_CLASS,
                        "executed": True if front_res.get("executed") is True else None,
                        "side_effects_may_exist": True,
                        "composer_fallback_executed": False,
                        "tier_used": "tier1_unconfined_exploration_refused",
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3)}
            if routed.get("pass") is True and routed.get("chain"):
                composer_dispatch_started = True
                chained = croute.execute_chain(routed["chain"], goal)
                if chained.get("status") == computer_boundary.STATUS:
                    return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                            "status": computer_boundary.STATUS,
                            "failure_class": computer_boundary.FAILURE_CLASS,
                            "executed": True if front_res.get("executed") is True else None,
                            "side_effects_may_exist": True,
                            "composer_fallback_executed": False,
                            "tier_used": "tier1_unconfined_command_refused",
                            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3)}
                if chained.get("pass") is True:
                    acceptance = ra._composed_acceptance(goal, routed["chain"], chained)
                    complete = acceptance.get("semantic_acceptance_complete") is True
                    return {
                        "schema": SCHEMA, "task_id": task_id, "pass": complete,
                        "status": ("PASS__TIER1_CAPABILITY_CHAIN" if complete
                                   else "FAIL_CLOSED__COMPOSED_GOAL_NOT_VERIFIED"),
                        "failure_class": None if complete else "COMPOSED_GOAL_NOT_VERIFIED",
                        "tier_used": "tier1_composer_chain", "from_memory": False,
                        "chain": list(routed["chain"]), "chain_result": chained,
                        "semantic_acceptance_complete": complete,
                        "raw_goal_acceptance": acceptance.get("raw_goal_acceptance"),
                        "accepted_raw_obligation_ids": acceptance.get("accepted_raw_obligation_ids") or [],
                        "executed": True, "side_effects_may_exist": not complete,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
                if (chained.get("steps") or chained.get("executed") is True
                        or chained.get("side_effects_may_exist") is True):
                    return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                            "status": str(chained.get("status") or "FAIL__COMPOSER_CHAIN"),
                            "failure_class": str(chained.get("failure_class") or "COMPOSER_STEP_OUTCOME_UNCERTAIN"),
                            "tier_used": "tier1_composer_chain", "chain_result": chained,
                            "executed": True, "side_effects_may_exist": True,
                            "semantic_acceptance_complete": False,
                            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3)}
        except Exception as exc:  # noqa: BLE001 - a retry cannot erase possible effects
            return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                    "status": ("FAIL_CLOSED__COMPOSITION_EXECUTION_OUTCOME_UNKNOWN"
                               if composer_dispatch_started else "FAIL_CLOSED__COMPOSITION_PLANNING_ERROR"),
                    "failure_class": ("COMPOSITION_EXECUTION_OUTCOME_UNKNOWN"
                                      if composer_dispatch_started else "COMPOSITION_PLANNING_ERROR"),
                    "reason": type(exc).__name__,
                    "executed": True if composer_dispatch_started or front_res.get("executed") is True else None,
                    "side_effects_may_exist": True,
                    "semantic_acceptance_complete": False,
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3)}

    # ------------------------------------------------------------------
    # TIER 2 (<2 s): Targeted Discovery -> Speed Elevation -> Gate Qualification
    # ------------------------------------------------------------------
    if allow_tier2_learning:
        # 2A: Semantic Web HTML <form> -> Direct HTTP Skill Compilation
        url_match = _URL_RE.search(goal)
        if url_match is not None:
            target_url = url_match.group(0).rstrip(".,;)")
            web_res = discover_and_execute_semantic_web_form(goal, target_url)
            if web_res.get("ok") is True and web_res.get("causal_trace"):
                qual = _qualify_http_form_skill(
                    goal=goal,
                    url=target_url,
                    causal_trace=web_res["causal_trace"],
                    form_body=web_res.get("form_body") or {},
                    method=str(web_res.get("method") or "POST"),
                    db_path=skill_db,
                    hidden_fields=list(web_res.get("hidden_fields") or []),
                    stateful_csrf_or_cookie=bool(web_res.get("stateful_csrf_or_cookie")),
                )
                closed_gaps = _close_matching_ignorance_gaps(goal, str(qual.get("skill_id") or "http_form_skill")) if qual.get("pass") else []
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "pass": True,
                    "status": "PASS__TIER2_LEARNED_SEMANTIC_WEB_TO_HTTP",
                    "tier_used": "tier2_semantic_web_form_to_http",
                    "from_memory": False,
                    "learned_this_turn": bool(qual.get("pass")),
                    "closed_gap_ids": closed_gaps,
                    "skill_crystallized": bool(qual.get("pass")),
                    "skill_id": qual.get("skill_id"),
                    "qualification_receipt": qual,
                    "answer": web_res.get("response_body"),
                    "http_status": web_res.get("status_code"),
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }

        # CLI probes and archive discovery used to run host programs before an
        # isolation or effect-admission decision. A filename verifier is not a
        # sandbox; preserve the refusal instead of trying those paths directly.
        from canonical.runtime import computer_env_v1 as cenv
        qkind = cenv.query_kind(goal)
        if ((qkind is not None and _extract_existing_file(goal, work_cwd) is not None)
                or any(ext in goal.lower() for ext in (".tar.gz", ".tar.bz2", ".tar.xz"))):
            return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                    "status": computer_boundary.STATUS,
                    "failure_class": computer_boundary.FAILURE_CLASS,
                    "executed": True if front_res.get("executed") is True else None,
                    "side_effects_may_exist": True,
                    "served_after": front_res.get("status"), "computer_fallback_executed": False,
                    "semantic_acceptance_complete": False,
                    "tier_used": "tier2_unconfined_computer_execution_refused",
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3)}

        # 2B-Repo: Zero-Hint Multi-Step Closed-Loop Repository Repair (`solve_repository_closed_loop`)
        low_goal = goal.lower()
        if any(w in low_goal for w in ("fix", "repair", "solve", "make all tests pass", "failing tests")):
            repo_target: pathlib.Path | None = None
            for tok in re.findall(r"[A-Za-z0-9_./~-]+", goal):
                tok_clean = tok.strip(".,:;()[]'\"")
                if not tok_clean or tok_clean in {".", "/", "tests", "test"}:
                    continue
                cand_dir = (work_cwd / tok_clean).resolve() if not pathlib.Path(tok_clean).is_absolute() else pathlib.Path(tok_clean).resolve()
                if cand_dir.is_dir() and any(cand_dir.rglob("test_*.py")):
                    repo_target = cand_dir
                    break
            if repo_target is None and work_cwd != pathlib.Path(__file__).resolve().parents[2] and any(work_cwd.rglob("test_*.py")):
                repo_target = work_cwd
            if repo_target is not None:
                return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                        "status": computer_boundary.STATUS, "failure_class": computer_boundary.FAILURE_CLASS,
                        "executed": True if front_res.get("executed") is True else None,
                        "side_effects_may_exist": True, "semantic_acceptance_complete": False,
                        "tier_used": "repository_repair_execution_not_admitted"}
                # Phase 3C fast path: `< 180 ms` Zero-Copy CoW + Impact-Sliced + STUN/Guard + Coupled 2-File Zygote Engine
                try:
                    from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
                        repair_repository_in_cow_zygote,
                    )

                    cow_res = repair_repository_in_cow_zygote(repo_target, apply_to_workspace=True)
                    if cow_res.get("pass"):
                        c_ids = list(cow_res.get("crystallized_skill_ids") or [])
                        closed_gaps = _close_matching_ignorance_gaps(
                            goal, c_ids[0] if c_ids else "cow_zygote_repo_repair"
                        )
                        return {
                            "schema": SCHEMA,
                            "task_id": task_id,
                            "pass": True,
                            "status": "PASS__TIER2_COW_ZYGOTE_REPO_REPAIR",
                            "tier_used": "tier2_cow_impact_zygote_repair_engine",
                            "from_memory": str(cow_res.get("mode") or "").startswith("SKILL_RECALL"),
                            "learned_this_turn": not str(cow_res.get("mode") or "").startswith("SKILL_RECALL"),
                            "closed_gap_ids": closed_gaps,
                            "changed_files": cow_res.get("files_repaired"),
                            "crystallized_skill_ids": c_ids,
                            "zygote_eval_ms": cow_res.get("zygote_eval_ms"),
                            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                        }
                except Exception:
                    pass

                from canonical.swe_kernel.multistep_repo_closed_loop_solver_v1 import solve_repository_closed_loop

                loop_res = solve_repository_closed_loop(repo_target, goal, apply_to_source=True)
                if loop_res.get("ok") and loop_res.get("verified"):
                    c_ids = list(loop_res.get("crystallized_skill_ids") or [])
                    closed_gaps = _close_matching_ignorance_gaps(goal, c_ids[0] if c_ids else "multistep_repo_repair")
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "pass": True,
                        "status": "PASS__TIER2_MULTISTEP_CLOSED_LOOP_REPO_REPAIR",
                        "tier_used": "tier2_multistep_closed_loop_repo_solver",
                        "from_memory": False,
                        "learned_this_turn": True,
                        "closed_gap_ids": closed_gaps,
                        "steps_taken": loop_res.get("steps_taken"),
                        "changed_files": loop_res.get("changed_files"),
                        "crystallized_skill_ids": c_ids,
                        "diff": loop_res.get("diff"),
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }

        if bool(req.get("confinement_admitted") is True) and work_cwd.is_dir():
            try:
                from canonical.runtime import autonomous_v1 as _auto
                from canonical.runtime import brokered_workspace_execution_v1 as _bwe
                from canonical.runtime import taskfile_read_v1 as _tf

                declared_tasks = list(_tf.read_tasks(str(work_cwd)) or [])
                if not declared_tasks and (work_cwd / "Makefile").is_file():
                    m_mk = re.search(r"\bmake\s+([A-Za-z0-9_.-]+)", goal)
                    if m_mk:
                        declared_tasks = [{"name": m_mk.group(1), "command": f"make {m_mk.group(1)}", "source": "Makefile"}]
                g_toks = _auto.goal_tokens(goal) or [
                    w for w in re.findall(r"[a-zA-Z0-9_.-]+", goal.lower())
                    if w not in {"run", "make", "execute", "please", "the", "a", "an", "target"}
                ]
                if declared_tasks and g_toks:
                    before_snap = _auto._snapshot(str(work_cwd))
                    validators_set = {id(v) for v in _auto.find_validators(declared_tasks)}
                    ranked_tasks = sorted(
                        [t for t in declared_tasks if id(t) not in validators_set and t.get("command")],
                        key=lambda t: sum(
                            2 if tok == str(t.get("name") or "").lower() else (1 if tok in f"{t.get('name', '')} {t.get('command', '')}".lower() else 0)
                            for tok in g_toks
                        ),
                        reverse=True,
                    )
                    for cand_t in ranked_tasks[:3]:
                        cmd_s = str(cand_t.get("command") or "").strip().lstrip("@")
                        if not cmd_s:
                            continue
                        exec_argv = (
                            ["make", str(cand_t["name"])]
                            if str(cand_t.get("source") or "").endswith("Makefile") and cand_t.get("name")
                            else ["/bin/sh", "-c", cmd_s]
                        )
                        b_res = _bwe.run_staged_confined_command(
                            work_cwd,
                            exec_argv,
                            publish=True,
                            timeout=30,
                            goal=goal,
                        )
                        if not b_res.get("ok"):
                            continue
                        after_snap = _auto._snapshot(str(work_cwd))
                        touched_now = sorted(set(after_snap) - set(before_snap)) + sorted(
                            p for p in set(before_snap) & set(after_snap) if before_snap[p] != after_snap[p]
                        )
                        produces_map = {str(cand_t.get("name") or ""): touched_now} if cand_t.get("name") else None
                        val_verdicts: dict[str, bool] = {}
                        for vt in _auto.find_validators(declared_tasks):
                            vcmd = str(vt.get("command") or "").strip().lstrip("@")
                            if vcmd:
                                vr = _bwe.run_staged_confined_command(
                                    work_cwd,
                                    ["/bin/sh", "-c", vcmd],
                                    publish=False,
                                    timeout=20,
                                )
                                val_verdicts[vcmd] = bool(vr.get("ok"))
                        ver = _auto.verify(
                            goal,
                            str(work_cwd),
                            before_snap,
                            after_snap,
                            produces=produces_map,
                            validators=val_verdicts or None,
                        )
                        if ver.get("verified") is True or (
                            ver.get("reason") == "NO_GOAL_TOKENS"
                            and touched_now
                            and all(val_verdicts.values())
                        ):
                            return {
                                "schema": SCHEMA,
                                "task_id": task_id,
                                "goal": goal,
                                "pass": True,
                                "executed": True,
                                "confined": True,
                                "status": "PASS__CONFINED_AUTONOMOUS_TASK_VERIFIED",
                                "tier_used": "tier2_confined_autonomous_v1",
                                "verification": ver,
                                "changed_files": b_res.get("changed_files") or [],
                                "k3_external_llm_calls": 0,
                                "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                            }
            except Exception:
                pass

        # Documentation-mined snippets run as host Python programs. Do not
        # execute this fallback without the same admitted boundary.
        return {"schema": SCHEMA, "task_id": task_id, "pass": False,
                "status": computer_boundary.STATUS,
                "failure_class": computer_boundary.FAILURE_CLASS,
                "executed": True if front_res.get("executed") is True else None,
                "side_effects_may_exist": True,
                "served_after": front_res.get("status"), "documentation_fallback_executed": False,
                "semantic_acceptance_complete": False,
                "tier_used": "tier2_unconfined_documentation_execution_refused",
                "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3)}

        # 2D: General Computer Environment Execution (`computer_env_v1.perform`) on stated workspace paths
        try:
            from canonical.runtime import computer_env_v1 as cenv
            from canonical.runtime import goal_compiler as _gc

            stated_paths = [abs_p for _raw_p, abs_p in _gc._repo_paths(goal, ra.ROOT)]
            env_dir = (
                stated_paths[0].parent
                if stated_paths and stated_paths[0].is_file()
                else (stated_paths[0] if stated_paths and stated_paths[0].is_dir() else None)
            )
            if env_dir is not None and env_dir.is_dir():
                c_res = cenv.perform(goal, str(env_dir))
                if c_res.get("pass") is True and c_res.get("verified") is True:
                    closed_gaps = _close_matching_ignorance_gaps(goal, "computer_env.perform")
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__COMPUTER_ENV_LEARNED_AND_VERIFIED",
                        "tier_used": "tier2_computer_env_perform",
                        "executed": True,
                        "semantic_acceptance_complete": True,
                        "from_memory": bool(c_res.get("from_memory")),
                        "learned_this_turn": True,
                        "closed_gap_ids": closed_gaps,
                        "computer_env_result": c_res,
                        "model_dependency_count": 0,
                        "incremental_spend_usd": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
        except Exception:
            pass

        # 2E: Full Multi-Layer Computer, OSWorld v19, MCP JSON-RPC & Harbor Terminal Sovereignty
        mcp_rpc = req.get("mcp_rpc")
        if callable(mcp_rpc):
            try:
                import asyncio
                from canonical.runtime import toolathlon_brain_host_integration_v1 as mcp_host

                mcp_step = asyncio.run(
                    mcp_host.execute_one_brain_selected_step(
                        rpc=mcp_rpc,
                        substrate=_deterministic_zero_llm_mcp_substrate,
                        task_context=goal,
                        public_state_summary=str(req.get("public_state_summary") or ""),
                    )
                )
                gw_res = dict(mcp_step.get("gateway_result") or {})
                is_err = bool(gw_res.get("isError") is True)
                if not is_err:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__TIER2_MCP_GATEWAY_STEP_EXECUTED",
                        "tier_used": "tier2_mcp_gateway",
                        "selected_tool_id": mcp_step["selected_tool_id"],
                        "arguments": mcp_step["arguments"],
                        "gateway_result": gw_res,
                        "schema_judgment_receipts": mcp_step["schema_judgment_receipts"],
                        "k3_external_llm_calls": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        harbor_env = req.get("harbor_env")
        if harbor_env is not None:
            try:
                import asyncio
                from canonical.runtime import harbor_brain_agent as harbor_mod

                harbor_out = asyncio.run(
                    harbor_mod.run_bounded_harbor_goal(
                        goal,
                        harbor_env,
                        max_cycles=int(req.get("harbor_max_cycles", 8)),
                    )
                )
                if harbor_out.get("completed") is True or harbor_out.get("pass") is True:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__TIER2_HARBOR_TERMINAL_COMPLETED",
                        "tier_used": "tier2_harbor_terminal",
                        "harbor_result": harbor_out,
                        "k3_external_llm_calls": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        osworld_obs = req.get("osworld_obs")
        if isinstance(osworld_obs, Mapping):
            try:
                from canonical.runtime import osworld_v21_brain_subject_v19 as osw19

                subject = osw19.build_subject()
                osw_env = req.get("osworld_env")
                if osw_env is not None:
                    try:
                        subject.bind_environment(osw_env)
                    except Exception:
                        pass

                max_osw_steps = max(1, int(req.get("osworld_max_steps") or req.get("max_osworld_steps") or 6))
                cur_obs: Mapping[str, Any] = osworld_obs
                step_actions: list[list[str]] = []
                last_response = ""
                completed = False
                for _step_i in range(max_osw_steps):
                    response_text, py_actions = subject.predict(goal, cur_obs)
                    last_response = str(response_text or "")
                    act_list = list(py_actions or [])
                    if not act_list:
                        break
                    step_actions.append(act_list)
                    if act_list == ["DONE"]:
                        completed = True
                        break
                    if osw_env is not None and hasattr(osw_env, "step") and callable(osw_env.step):
                        step_out = osw_env.step(act_list[0] if len(act_list) == 1 else act_list)
                        if isinstance(step_out, tuple) and step_out and isinstance(step_out[0], Mapping):
                            cur_obs = step_out[0]
                            if len(step_out) >= 3 and bool(step_out[2]):
                                completed = True
                                break
                        elif isinstance(step_out, Mapping):
                            cur_obs = step_out
                        else:
                            break
                    else:
                        break

                # Automatic GUI/Pixel -> Sub-5ms SQLite/HTTP/CLI Layer Collapse when causal effects are observed!
                elevated_qualification = None
                causal_gui_trace = (
                    req.get("observed_causal_trace")
                    or req.get("osworld_elevated_trace")
                    or (getattr(osw_env, "causal_trace", None) if osw_env is not None else None)
                )
                gui_post = req.get("osworld_postcondition") or req.get("postcondition") or demo_post
                if isinstance(causal_gui_trace, (list, Mapping)) and causal_gui_trace and isinstance(gui_post, Mapping):
                    elevated_qualification = compile_and_qualify_skill(
                        goal=goal,
                        trace=causal_gui_trace,
                        postcondition=gui_post,
                        heldout_goal=req.get("heldout_goal"),
                        heldout_postcondition=req.get("heldout_postcondition"),
                        sabotaged_postcondition=req.get("sabotaged_postcondition"),
                        auto_synthesize_twin=True,
                        source_cwd=work_cwd,
                        db_path=skill_db,
                    )

                if step_actions:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__TIER2_OSWORLD_V19_DECIDED",
                        "tier_used": "tier2_osworld_v19",
                        "subject_id": osw19.SUBJECT_ID,
                        "response": last_response,
                        "actions": step_actions[-1],
                        "trajectory_actions": step_actions,
                        "steps_executed": len(step_actions),
                        "completed": completed,
                        "learned_this_turn": bool(
                            elevated_qualification
                            and (elevated_qualification.get("qualified") or elevated_qualification.get("pass"))
                        ),
                        "layer_elevation_receipt": elevated_qualification,
                        "k3_external_llm_calls": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        # 2F: Type-Level Multi-Step Capability Composition (`type_level_composer_v1` — 113-edge artifact type graph)
        type_chain_target = req.get("type_chain_target")
        if type_chain_target or req.get("allow_type_level_composition") is True:
            try:
                from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
                    compose_and_execute_type_level_chain,
                )

                tc_res = compose_and_execute_type_level_chain(
                    str(type_chain_target or goal),
                    macro_state_path=macro_state_path,
                )
                if tc_res.get("pass") is True:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__TIER2_TYPE_LEVEL_CHAIN_EXECUTED",
                        "tier_used": "tier2_type_level_composer",
                        "from_memory": bool(tc_res.get("from_macro_cache")),
                        "learned_this_turn": not bool(tc_res.get("from_macro_cache")),
                        "chain": tc_res.get("chain"),
                        "type_chain_result": tc_res,
                        "k3_external_llm_calls": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        # 2G: Zero-Field Plain-Sentence Workspace Autonomy (`autonomous_v1.run`) inside transactional CoW rollback
        repo_root_resolved = pathlib.Path(__file__).resolve().parents[2]
        has_project_taskfile = work_cwd != repo_root_resolved and any(
            (work_cwd / fn).is_file() for fn in ("Makefile", "package.json", "pyproject.toml", "Taskfile.yml")
        )
        if req.get("autonomous_workspace") is True or has_project_taskfile:
            try:
                from canonical.runtime import autonomous_v1 as auto_v1
                from canonical.swe_kernel.transactional_parallel_execution_v1 import (
                    execute_transactional_cow_action,
                )

                def _verify_auto_v1(_rp: pathlib.Path, res_d: Mapping[str, Any]) -> bool:
                    ver_d = res_d.get("verification") or {}
                    if not (ver_d.get("verified") is True or ver_d.get("pass") is True):
                        return False
                    g_toks = [str(t).lower() for t in (ver_d.get("goal_tokens") or []) if str(t)]
                    matched = [
                        str(p).lower()
                        for p in list(ver_d.get("matching") or []) + list(ver_d.get("new_paths") or [])
                    ]
                    if not matched:
                        return False
                    if g_toks and not any(gt in mp for gt in g_toks for mp in matched):
                        return False
                    return True

                tx_auto = execute_transactional_cow_action(
                    work_cwd,
                    lambda root_p: auto_v1.run(
                        goal,
                        root_p,
                        binary_limit=int(req.get("binary_limit", 20)),
                        iterations=int(req.get("iterations", 3)),
                    ),
                    verify_fn=_verify_auto_v1,
                )
                if tx_auto.get("committed") is True:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__TIER2_ZERO_FIELD_AUTONOMOUS_V1_VERIFIED",
                        "tier_used": "tier2_autonomous_v1",
                        "autonomous_result": tx_auto.get("action_output"),
                        "files_updated": tx_auto.get("files_updated"),
                        "k3_external_llm_calls": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        # 2H: Active Black-Box Mechanism Discovery (`h100_zero_learned_mechanism_synthesizer_v1`) & 2D Grid Rule Induction (`grid_delta_rule_inducer_v2`)
        if callable(req.get("mechanism_oracle")) or isinstance(req.get("mechanism_rows"), (list, tuple)):
            try:
                from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
                    discover_mechanism_actively,
                )

                m_out = discover_mechanism_actively(
                    req.get("mechanism_oracle"),
                    bounds=req.get("mechanism_bounds"),
                    rows=req.get("mechanism_rows"),
                    target=str(req.get("mechanism_target") or "y"),
                    inputs=req.get("mechanism_inputs"),
                    max_discriminator_rounds=int(req.get("max_discriminator_rounds", 6)),
                    holdout_points=req.get("holdout_points"),
                )
                if m_out.get("pass") is True:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__TIER2_ACTIVE_MECHANISM_DISCOVERED",
                        "tier_used": "tier2_active_mechanism_discovery",
                        "learned_this_turn": True,
                        "mechanism": m_out,
                        "k3_external_llm_calls": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        if isinstance(req.get("grid_training_pairs"), (list, tuple)):
            try:
                from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
                    induce_and_predict_grid_delta_rule,
                )

                g_out = induce_and_predict_grid_delta_rule(
                    req["grid_training_pairs"],
                    test_grids=req.get("grid_test_inputs"),
                )
                if g_out.get("pass") is True:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "goal": goal,
                        "pass": True,
                        "status": "PASS__TIER2_GRID_DELTA_RULE_INDUCED",
                        "tier_used": "tier2_grid_delta_rule_inducer",
                        "learned_this_turn": True,
                        "grid_induction": g_out,
                        "k3_external_llm_calls": 0,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
            except Exception:
                pass

        gui_action = req.get("gui_action")
        if isinstance(gui_action, Mapping):
            try:
                from canonical.runtime import osworld_computer_surface_v1 as gui_surface

                raw_screen = req.get("gui_screen") or {}
                screen = gui_surface.Screen(
                    width=int(raw_screen.get("width", 1920)),
                    height=int(raw_screen.get("height", 1080)),
                )
                compiled_gui = gui_surface.compile_osworld_pyautogui(gui_action, screen)
                gui_env = req.get("gui_env")
                exec_receipt = (
                    gui_surface.execute_typed_action(gui_env, gui_action)
                    if gui_env is not None
                    else {"compiled_pyautogui": compiled_gui, "executed_in_env": False}
                )
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "goal": goal,
                    "pass": True,
                    "status": "PASS__TIER2_TYPED_GUI_SURFACE_ACTION",
                    "tier_used": "tier2_typed_gui_surface",
                    "compiled_pyautogui": compiled_gui,
                    "gui_receipt": exec_receipt,
                    "learned_this_turn": False,
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Record Open Gap + JIT Multi-Channel Knowledge + CLI `--help` Acquisition
    # ------------------------------------------------------------------
    learned: dict[str, Any] = {"attempted": False, "gap_recorded": False}
    front_status = str(front_res.get("status") or "")
    learnable_gap = allow_tier2_learning and (front_status in _LEARNABLE_FRONT_STATUSES)

    if record_open_gap:
        try:
            from canonical.runtime import ignorance_ledger_v1 as led

            why_text = f"raw goal compilation gap ({front_status})" if front_status else "raw goal compilation gap"
            gap_id = led.note(goal or "unmatched goal", why=why_text, cost=1.0)
            learned["gap_recorded"] = True
            learned["gap_id"] = gap_id
            learned["what_to_learn_next"] = [g["what"] for g in led.rank(limit=3)]
        except Exception:
            pass

    if learnable_gap and allow_jit_network:
        try:
            from canonical.runtime import jit_knowledge_v1 as jit

            known = jit.resolve(goal, min_sources=1, limit=6, timeout=8)
            if not known.get("complete"):
                try:
                    from canonical.runtime.curriculum_v1 import query_for

                    rephrased = query_for(goal)
                    if rephrased and rephrased != goal:
                        again = jit.resolve(rephrased, min_sources=1, limit=6, timeout=8)
                        if again.get("complete") or again.get("document_count", 0) > known.get("document_count", 0):
                            known = again
                            known["query_was_rephrased_to"] = rephrased
                except Exception:
                    pass
            learned["knowledge"] = {
                "status": known.get("status"),
                "documents": known.get("document_count", 0),
                "sources_answered": known.get("sources_answered") or [],
                "kinds_answered": known.get("kinds_answered") or [],
                "min_kinds_required": known.get("min_kinds_required"),
                "gap": known.get("gap"),
                "query_was_rephrased_to": known.get("query_was_rephrased_to"),
                "complete": known.get("complete", False),
                "authority": known.get("authority"),
            }
            candidates: list[str] = []
            for doc in known.get("documents") or []:
                for text in (str(doc.get("id") or ""), str(doc.get("title") or "")):
                    head = text.strip().split()[0] if text.strip() else ""
                    head = head.strip(".,()[]{}'\"")
                    if 2 <= len(head) <= 40 and _is_executable(head):
                        candidates.append(head)
            if candidates:
                learned["knowledge"]["candidates_present"] = candidates[:6]
                if not _named_executable(goal):
                    learned.setdefault("from_knowledge", candidates[0])
        except Exception as exc:
            learned.setdefault("knowledge", {"error": f"{type(exc).__name__}:{str(exc)[:160]}"})

    if learnable_gap:
        exe = _named_executable(goal)
        if not exe:
            exe = str(learned.get("from_knowledge") or "")
            if exe:
                learned["attempted"] = True
                learned["executable"] = exe
                learned["executable_source"] = "jit_knowledge"
        if exe:
            learned["attempted"] = True
            learned["executable"] = exe
            try:
                import subprocess
                from canonical.runtime import cli_capability_acquisition_v1 as acq

                with tempfile.TemporaryDirectory(prefix="brain-learn-") as td:
                    out_proc = subprocess.run([exe, "--help"], capture_output=True, timeout=30, cwd=td)
                    help_text = (out_proc.stdout + out_proc.stderr).decode("utf-8", "replace")
                probe_doc = {"executables": [{"executable": exe, "help_attempts": [{"text": help_text}]}]}
                acquired = acq.acquire(probe_doc, goal)
                learned["acquisition_status"] = acquired.get("status")
                if acquired.get("verified"):
                    cid = "acquired." + exe.replace(".", "_")
                    reg = acq.register(acquired, cid, registry_path=registry_path)
                    learned["registered"] = reg.get("registered") is True
                    learned["capability_id"] = cid
                    if learned["registered"]:
                        _close_matching_ignorance_gaps(goal, cid)
                        r3_promo = _promote_r3_episode_if_configured(r3_path)
                        if r3_promo is not None:
                            learned["r3_promotion"] = r3_promo
                        retry = ra.solve(clean_req)
                        retry["learning"] = learned
                        retry["learned_this_turn"] = True
                        retry["controller_schema"] = SCHEMA
                        retry["tier_used"] = "tier2_cli_help_acquisition"
                        retry["elapsed_ms"] = round((perf_counter_ns() - t0) / 1e6, 3)
                        return retry
            except Exception as exc:
                learned["error"] = f"{type(exc).__name__}:{str(exc)[:200]}"

        try:
            from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

            learned["verified_skill_store_rules"] = VerifiedSkillStore().count()
        except Exception:
            pass

    r3_promo = _promote_r3_episode_if_configured(r3_path)
    if r3_promo is not None:
        learned["r3_promotion"] = r3_promo

    out = dict(front_res)
    out["controller_schema"] = SCHEMA
    out["tier_used"] = "fail_closed_unserved"
    out["qualification_receipt"] = qualification_receipt
    out["learning"] = learned
    out["learned_this_turn"] = False
    out["elapsed_ms"] = round((perf_counter_ns() - t0) / 1e6, 3)
    return out


def chase_until_met(goal: str, *, measure: Any, **kwargs: Any) -> dict[str, Any]:
    """Target-bound persistent chase loop (`goal_chase_v1.chase_until_met`) wired to the 4-tier controller."""
    from execution_guard.goal_chase_v1 import chase_until_met as _chase_until_met

    return _chase_until_met(goal, measure=measure, **kwargs)


def study_open_gaps(*, max_lessons: int = 5, channels: list[str] | None = None) -> dict[str, Any]:
    """Tier 3 self-directed learning: drain `ignorance_ledger_v1` via `curriculum_v1`."""
    from canonical.runtime import curriculum_v1 as cur

    return cur.run(max_lessons=max_lessons, channels=channels)


def inspect_local_repo_for_goal(goal: str, repo_or_module: str | pathlib.Path) -> dict[str, Any]:
    """Convenience bridge exposing Phase 2 white-box callable ranking for any repo/module."""
    surface = introspect_python_surface(repo_or_module)
    if not surface.get("ok"):
        return surface
    ranked = rank_callables_for_goal(goal, surface, limit=8)
    return {
        "ok": True,
        "target": surface.get("target"),
        "callable_count": len(surface.get("callables") or []),
        "top_candidates": ranked,
    }


def solve_or_learn_isolated(request: Mapping[str, Any] | str, **kwargs: Any) -> dict[str, Any]:
    """Dispatch `solve_or_learn` inside a Copy-On-Write pre-warmed `os.fork()` Zygote worker."""
    from canonical.swe_kernel.zygote_worker_pool_v1 import default_zygote_pool

    return default_zygote_pool().solve_or_learn_isolated(request, **kwargs)


def execute_and_elevate_confined_trajectory(
    goal: str,
    workspace_root: str | pathlib.Path | None = None,
    trajectory_steps: Sequence[str | Sequence[str]] | None = None,
    *,
    cwd: str | pathlib.Path | None = None,
    expected_artifacts: Sequence[str] = (),
    macro_db_path: str | pathlib.Path | None = None,
    workflow_db_path: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute multi-step workspace actions inside `brokered_workspace_execution_v1` and elevate 2-instance verified plans into `macro_v1`."""
    from canonical.runtime import autonomous_v1, brokered_workspace_execution_v1 as bwe, macro_v1, taskfile_read_v1
    from canonical.runtime.memory_policy_v1 import can_read_memory, can_write_memory
    from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
        lookup_verified_chain_macro,
        record_verified_chain_macro,
    )

    ws = pathlib.Path(workspace_root or cwd or pathlib.Path.cwd()).resolve()
    macro_state_p = (
        pathlib.Path(macro_db_path or workflow_db_path).resolve()
        if (macro_db_path is not None or workflow_db_path is not None)
        else (ws / ".brain_chain_macros_v1.json")
    )
    clauses = ["discover workspace taskfile", goal.strip()]

    # 1. Fast `< 1 ms` recall from real `macro_v1` once promoted (`N >= 2` distinct instances)
    recalled_hit = lookup_verified_chain_macro(clauses, state_path=macro_state_p) if (not trajectory_steps and can_read_memory()) else None
    from_macro = False
    steps_list: list[str | Sequence[str]] = list(trajectory_steps or ())
    if not steps_list and recalled_hit is not None:
        plan = list(recalled_hit.get("plan") or [])
        recalled_cmds = [str(p.get("capability_id") or "").removeprefix("confined_cmd:") for p in plan[1:] if str(p.get("capability_id") or "").startswith("confined_cmd:")]
        if recalled_cmds:
            steps_list = recalled_cmds
            from_macro = True

    # 2. Cold discovery via `taskfile_read_v1` + `autonomous_v1.goal_tokens`
    if not steps_list:
        tasks_rep = list(taskfile_read_v1.read_tasks(str(ws)) or [])
        goal_l = goal.lower()
        g_tokens = set(autonomous_v1.goal_tokens(goal))
        validator_names = {str(v.get("name") or "") for v in autonomous_v1.find_validators(tasks_rep)}
        for t_row in tasks_rep:
            t_name = str(t_row.get("name") or "")
            src_origin = str(t_row.get("source") or t_row.get("origin") or "")
            if t_name and (
                re.search(rf"\b{re.escape(t_name.lower())}\b", goal_l)
                or (t_name not in validator_names and t_name.lower() in g_tokens)
            ):
                if src_origin.endswith("Makefile"):
                    steps_list.append(["make", t_name])
                elif t_row.get("command"):
                    steps_list.append(str(t_row["command"]).lstrip("@"))
                break
        if not steps_list:
            m_mk = re.search(r"\bmake\s+([A-Za-z0-9_.-]+)", goal)
            if m_mk:
                steps_list.append(["make", m_mk.group(1)])
    if not steps_list:
        return {"schema": SCHEMA, "ok": False, "pass": False, "confined": False, "reason": "NO_TRAJECTORY_STEPS"}

    executed_cmds: list[str] = []
    changed_union: set[str] = set()
    for step_cmd in steps_list:
        cmd_arg: str | Sequence[str] = (
            ["/bin/sh", "-c", step_cmd] if isinstance(step_cmd, str) else step_cmd
        )
        res = bwe.run_staged_confined_command(ws, cmd_arg, publish=True, timeout=30, goal=goal)
        if not res.get("ok"):
            if from_macro and recalled_hit is not None:
                orig_st = macro_v1.STATE
                try:
                    macro_v1.STATE = macro_state_p
                    macro_v1.note_failure(str(recalled_hit["key"]))
                finally:
                    macro_v1.STATE = orig_st
            return {
                "schema": SCHEMA,
                "ok": False,
                "pass": False,
                "confined": bool(res.get("confined")),
                "reason": str(res.get("blocked") or "STEP_FAILED"),
            }
        executed_cmds.append(step_cmd if isinstance(step_cmd, str) else " ".join(str(x) for x in step_cmd))
        changed_union.update(str(p) for p in (res.get("changed_files") or ()))

    for rel_art in expected_artifacts:
        fp = ws / rel_art
        if not fp.is_file() or fp.stat().st_size == 0:
            return {
                "schema": SCHEMA,
                "ok": False,
                "pass": False,
                "confined": True,
                "reason": f"EXPECTED_ARTIFACT_MISSING:{rel_art}",
            }

    macro_saved = False
    macro_name: str | None = None
    if can_write_memory() and executed_cmds:
        sig_key = macro_v1.signature(clauses)
        raw_doc: dict[str, Any] = {"schema": macro_v1.SCHEMA, "macros": {}, "pending_instances": {}}
        if macro_state_p.is_file():
            try:
                loaded = json.loads(macro_state_p.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    raw_doc.update(loaded)
            except Exception:
                pass
        pending = dict(raw_doc.get("pending_instances") or {})
        inst_list = list(pending.get(sig_key) or [])
        ws_id = str(ws)
        if ws_id not in inst_list:
            inst_list.append(ws_id)
        pending[sig_key] = inst_list
        raw_doc["pending_instances"] = pending
        macro_state_p.parent.mkdir(parents=True, exist_ok=True)
        macro_state_p.write_text(json.dumps(raw_doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")

        if len(inst_list) >= 2:
            macro_steps = [{"capability_id": "taskfile_read_v1", "verified": True}] + [
                {"capability_id": f"confined_cmd:{c}", "verified": True} for c in executed_cmds
            ]
            # Preserve `pending_instances` across `macro_v1.record`
            macro_saved = record_verified_chain_macro(clauses, macro_steps, state_path=macro_state_p)
            after_doc = json.loads(macro_state_p.read_text(encoding="utf-8"))
            after_doc["pending_instances"] = pending
            macro_state_p.write_text(json.dumps(after_doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        macro_name = sig_key

    return {
        "schema": SCHEMA,
        "ok": True,
        "pass": True,
        "confined": True,
        "from_macro": from_macro,
        "changed_files": sorted(changed_union),
        "macro_promoted": macro_saved,
        "macro_id": macro_name,
        "k3_external_llm_calls": 0,
    }


