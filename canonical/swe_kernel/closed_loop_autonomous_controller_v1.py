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

from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    compile_and_qualify_skill,
    recall_and_execute_workflow,
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
        "TARGET_SYMBOL_ALREADY_EXISTS",
        "NO_MAGIC_CONSTANT_FOUND",
        "REQUESTED_CONTRACT_CHECKS_NOT_VERIFIED",
        "REMOVAL_REQUIRES_GREEN_BASELINE",
        "REMOVAL_TARGET_NOT_UNIQUE",
        "REQUEST_INVALID",
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
    return False


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
) -> dict[str, Any]:
    """Spin up an ephemeral local twin server on a fresh port to qualify HTTP transfer."""
    fields = dict(form_body or {})

    # Perturb the first parameter in the goal & expected twin server
    perturbed_goal = goal
    perturbed_expected: dict[str, str] = {}
    perturbed_once = False
    for k, v in fields.items():
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
            ok = all(str(parsed.get(k, "")) == val for k, val in perturbed_expected.items())
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
    cwd: str | pathlib.Path | None = None,
    db_path: str | pathlib.Path | None = None,
    allow_tier1_composition: bool = True,
    allow_tier2_learning: bool = True,
    record_open_gap: bool = True,
) -> dict[str, Any]:
    """Execute a request at maximum speed, or learn & crystallize the missing skill in-run."""
    t0 = perf_counter_ns()
    if isinstance(request, str):
        req: dict[str, Any] = {"task_id": "autonomous-solve", "goal": request}
    else:
        req = dict(request)

    goal = str(req.get("goal") or "").strip()
    task_id = str(req.get("task_id") or "autonomous-solve")
    work_cwd = pathlib.Path(cwd or req.get("cwd") or pathlib.Path.cwd()).resolve()
    skill_db = pathlib.Path(db_path) if db_path is not None else None

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
    demo_trace = req.pop("demonstration_trace", None)
    demo_post = req.pop("postcondition", None)
    qualification_receipt: dict[str, Any] | None = None
    if isinstance(demo_trace, list) and demo_trace and isinstance(demo_post, Mapping):
        held_goal = str(req.pop("heldout_goal", "") or goal)
        held_cwd = req.pop("heldout_cwd", None)
        held_post = req.pop("heldout_postcondition", None)
        sab_post = req.pop("sabotaged_postcondition", None)
        # Drop donor reference locally before qualification executes
        trace_copy = list(demo_trace)
        del demo_trace
        qualification_receipt = compile_and_qualify_skill(
            goal=goal,
            trace=trace_copy,
            postcondition=demo_post,
            heldout_goal=held_goal,
            heldout_cwd=held_cwd or work_cwd,
            heldout_postcondition=held_post,
            sabotaged_postcondition=sab_post,
            source_channel="k2_demonstration_transfer",
            db_path=skill_db,
        )

    # ------------------------------------------------------------------
    # TIER 0A (<2 ms): Recall Compiled & Ownership-Qualified Workflow Skill
    # ------------------------------------------------------------------
    recalled = recall_and_execute_workflow(goal, cwd=work_cwd, db_path=skill_db)
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
    # TIER 0B: Front-Door Bound Capability Admission (`solve`)
    # ------------------------------------------------------------------
    from canonical.runtime import live_brain_route_admission_v1 as ra

    clean_req = {
        k: v
        for k, v in req.items()
        if k not in {"heldout_goal", "heldout_cwd", "heldout_postcondition", "sabotaged_postcondition"}
    }
    clean_req.setdefault("task_id", task_id)
    front_res = ra.solve(clean_req)
    if front_res.get("pass") is True:
        out = dict(front_res)
        out["controller_schema"] = SCHEMA
        out["tier_used"] = "tier0_bound_capability"
        out["elapsed_ms"] = round((perf_counter_ns() - t0) / 1e6, 3)
        return out

    # Respect law-pinned honest refusals immediately — never paper over them.
    if _is_honest_contract_refusal(front_res):
        out = dict(front_res)
        out["controller_schema"] = SCHEMA
        out["tier_used"] = "tier0_honest_contract_refusal"
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
            dag_res = execute_transactional_goal_dag(
                root=work_cwd,
                stages=clauses,
                stage_solver=lambda sub_goal, idx: ra.solve({"task_id": f"{task_id}-s{idx}", "goal": sub_goal}),
            )
            if dag_res.get("ok") is True:
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "pass": True,
                    "status": "PASS__TIER1_GOAL_DAG_COMPOSITION",
                    "tier_used": "tier1_goal_dag",
                    "from_memory": False,
                    "clauses": clauses,
                    "dag_result": dag_res,
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }

        try:
            from canonical.runtime import composer_route_v1 as croute

            routed = croute.route(goal)
            if routed.get("pass") is True and routed.get("chain"):
                chained = croute.execute_chain(routed["chain"], goal)
                if chained.get("pass") is True:
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "pass": True,
                        "status": "PASS__TIER1_CAPABILITY_CHAIN",
                        "tier_used": "tier1_composer_chain",
                        "from_memory": False,
                        "chain": list(routed["chain"]),
                        "chain_result": chained,
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }
        except Exception:
            pass

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
                )
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "pass": True,
                    "status": "PASS__TIER2_LEARNED_SEMANTIC_WEB_TO_HTTP",
                    "tier_used": "tier2_semantic_web_form_to_http",
                    "from_memory": False,
                    "skill_crystallized": bool(qual.get("pass")),
                    "skill_id": qual.get("skill_id"),
                    "qualification_receipt": qual,
                    "answer": web_res.get("response_body"),
                    "http_status": web_res.get("status_code"),
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }

        # 2B: CLI / Pipeline Measurement Discovery (`computer_env_v1`)
        from canonical.runtime import computer_env_v1 as cenv

        qkind = cenv.query_kind(goal)
        if qkind is not None:
            in_file = _extract_existing_file(goal, work_cwd)
            if in_file is not None:
                measured = cenv.answer_query(goal, in_file)
                if measured.get("pass") is True:
                    qual = _qualify_cli_measurement_skill(
                        goal=goal,
                        input_file=in_file,
                        measured_res=measured,
                        cwd=work_cwd,
                        db_path=skill_db,
                    )
                    return {
                        "schema": SCHEMA,
                        "task_id": task_id,
                        "pass": True,
                        "status": "PASS__TIER2_LEARNED_CLI_INSTRUMENT",
                        "tier_used": "tier2_cli_instrument_discovery",
                        "from_memory": bool(measured.get("from_memory")),
                        "skill_crystallized": bool(qual.get("pass")),
                        "skill_id": qual.get("skill_id"),
                        "qualification_receipt": qual,
                        "answer": measured.get("answer"),
                        "value": measured.get("value"),
                        "survivors": measured.get("survivors"),
                        "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                    }

        # 2C: White-Box Stdlib / Local Python Documentation & Surface Mining
        try:
            from canonical.runtime import documentation_mining_v1 as dm

            mined = dm.learn_or_recall(goal)
            if mined.get("pass") is True:
                return {
                    "schema": SCHEMA,
                    "task_id": task_id,
                    "pass": True,
                    "status": "PASS__TIER2_LEARNED_PYTHON_DOCUMENTATION",
                    "tier_used": "tier2_documentation_mining",
                    "from_memory": bool(mined.get("from_memory")),
                    "module": mined.get("module"),
                    "result": mined,
                    "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                }
        except Exception:
            pass

    # Record open gap into `ignorance_ledger_v1` so Tier 3 curriculum can study it.
    if record_open_gap:
        try:
            from canonical.runtime import ignorance_ledger_v1 as led

            led.record(
                kind="unserved_goal",
                what=goal,
                blocked_task=task_id,
                evidence={"front_status": front_res.get("status"), "failure_class": front_res.get("failure_class")},
            )
        except Exception:
            pass

    out = dict(front_res)
    out["controller_schema"] = SCHEMA
    out["tier_used"] = "fail_closed_unserved"
    out["qualification_receipt"] = qualification_receipt
    out["elapsed_ms"] = round((perf_counter_ns() - t0) / 1e6, 3)
    return out


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
