"""Independent oracles for SAME_IDENTITY_SUPERVISOR_V1.

Nothing here imports the supervisor.  The reference model below is written from
the published contract (task manifest schema, causal readiness = prerequisites
present and hash-bound + mission file hash-bound, one identity per lease,
checkpoint-before-first-runtime, exit code -> state map, terminal states are
final) and it is deliberately simple: a dictionary simulation with no file
system, no locks and no JSON hashing beyond the mission/prerequisite digests
that the contract itself defines.
"""
from __future__ import annotations

import copy
import hashlib
import re

TASK_SCHEMA = "PROJECT_BRAIN_SAME_IDENTITY_TASK_V1"
TERMINAL = {"COMPLETE", "FAILED"}
HEX64 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"[A-Za-z0-9_.-]{1,160}")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _World:
    def __init__(self, inst: dict):
        self.files = dict(inst["files"])
        self.manifests = [copy.deepcopy(t["manifest"]) for t in inst["tasks"]]
        self.ids = [t["task_id"] for t in inst["tasks"]]
        self.agents = {"self": inst["agent_id"], "other": inst["other_agent_id"]}
        self.states: dict[str, dict] = {}
        self.executor_calls: list[dict] = []
        self.evidence: list[str] = []

    # --- contract predicates -------------------------------------------------
    def valid_for(self, m: dict, agent: str) -> bool:
        if m.get("schema") != TASK_SCHEMA:
            return False
        if not SAFE_ID.fullmatch(str(m.get("task_id", ""))) or not SAFE_ID.fullmatch(str(m.get("agent_id", ""))):
            return False
        if m.get("agent_id") != agent:
            return False
        if float(m.get("incremental_spend_usd", 0)) != 0.0:
            return False
        if not m.get("mission_path") or not HEX64.fullmatch(str(m.get("mission_sha256", "")).lower()):
            return False
        if not isinstance(m.get("prerequisites", []), list):
            return False
        return -1000000 <= int(m.get("priority", 50)) <= 1000000

    def prereqs_ok(self, m: dict) -> bool:
        for p in m.get("prerequisites", []):
            path = p if isinstance(p, str) else p["path"]
            if path not in self.files:
                return False
            if isinstance(p, dict) and p.get("sha256") and _sha(self.files[path]) != p["sha256"].lower():
                return False
        return True

    def mission_ok(self, m: dict) -> bool:
        text = self.files.get(m["mission_path"])
        return text is not None and _sha(text) == m["mission_sha256"].lower()

    def terminal(self, task_id: str) -> bool:
        st = self.states.get(task_id)
        return bool(st) and st["status"] in TERMINAL

    # --- operations -----------------------------------------------------------
    def choose(self) -> str | None:
        agent = self.agents["self"]
        cands = []
        for m, tid in zip(self.manifests, self.ids):
            if not self.valid_for(m, agent) or self.terminal(tid):
                continue
            if not self.prereqs_ok(m) or not self.mission_ok(m):
                continue
            cands.append((-int(m["priority"]), tid))
        if not cands:
            return None
        cands.sort()
        return cands[0][1]

    def claim(self, i: int, agent: str) -> bool:
        m, tid = self.manifests[i], self.ids[i]
        if not self.valid_for(m, agent) or not self.prereqs_ok(m) or not self.mission_ok(m):
            return False
        st = self.states.get(tid)
        if st is None:
            self.states[tid] = {
                "status": "CLAIMED", "lease_owner": agent, "claim_count": 1, "checkpoint_count": 0,
                "runtime_attempt_count": 0, "event_types": ["TASK_ACQUIRED"], "bound_manifest": copy.deepcopy(m),
            }
            return True
        if st["lease_owner"] != agent or st["bound_manifest"] != m or st["status"] in TERMINAL:
            return False
        st["claim_count"] += 1
        st["event_types"].append("TASK_RESUMED")
        return True

    def execute(self, i: int, agent: str, rc: int) -> int | None:
        m, tid = self.manifests[i], self.ids[i]
        if not self.valid_for(m, agent):
            return None
        st = self.states.get(tid)
        if st is None or st["lease_owner"] != agent or st["bound_manifest"] != m or st["status"] in TERMINAL:
            return None
        if m.get("checkpoint_before_runtime_once") and st["checkpoint_count"] == 0:
            st["checkpoint_count"] = 1
            st["status"] = "CHECKPOINTED_RELAUNCH_REQUIRED"
            st["event_types"].append("CHECKPOINT_CREATED")
            self.evidence.append(f"{tid}__CHECKPOINT.json")
            return 75
        if not self.mission_ok(m):
            return None
        st["runtime_attempt_count"] += 1
        st["event_types"].append("ASTRA_RUNTIME_STARTED")
        self.executor_calls.append({"task_id": tid, "env_agent": agent, "env_task": tid})
        self.evidence.append(f"{tid}__ATTEMPT_{st['runtime_attempt_count']}.json")
        if rc == 0:
            st["status"], ev = "COMPLETE", "TASK_COMPLETE"
        elif rc in (3, 4, 5):
            st["status"], ev = "BLOCKED", "TASK_BLOCKED"
        else:
            st["status"], ev = "FAILED", "TASK_FAILED"
        st["event_types"].append(ev)
        return rc

    def view(self, tid: str) -> dict | None:
        st = self.states.get(tid)
        if st is None:
            return None
        return {k: copy.deepcopy(st[k]) for k in ("status", "lease_owner", "claim_count", "checkpoint_count", "runtime_attempt_count", "event_types")}


def simulate(inst: dict) -> dict:
    w = _World(inst)
    ops = []
    for op in inst["script"]:
        kind = op["op"]
        rec = {"op": kind, "ok": True, "selected": None, "returncode": None}
        if kind == "choose":
            rec["selected"] = w.choose()
            rec["ok"] = rec["selected"] is not None
        elif kind == "claim":
            rec["ok"] = w.claim(op["task"], w.agents[op.get("agent", "self")])
        elif kind == "run":
            agent = w.agents[op.get("agent", "self")]
            rec["ok"] = w.claim(op["task"], agent)
            if rec["ok"]:
                rec["returncode"] = w.execute(op["task"], agent, int(op["rc"]))
                rec["ok"] = rec["returncode"] is not None
        elif kind == "execute":
            rec["returncode"] = w.execute(op["task"], w.agents[op.get("agent", "self")], int(op["rc"]))
            rec["ok"] = rec["returncode"] is not None
        elif kind == "edit_manifest":
            w.manifests[op["task"]][op["field"]] = op["value"]
        elif kind == "edit_file":
            w.files[op["path"]] = op["content"]
        elif kind == "delete_file":
            w.files.pop(op["path"], None)
        if kind in {"claim", "run", "execute"}:
            rec["state_after"] = w.view(w.ids[op["task"]])
        ops.append(rec)
    return {
        "ops": ops,
        "executor_calls": w.executor_calls,
        "final_states": {tid: w.view(tid) for tid in w.ids},
        "evidence_files": sorted(w.evidence),
    }


def _strip(view: dict | None) -> dict | None:
    if view is None:
        return None
    return {k: view.get(k) for k in ("status", "lease_owner", "claim_count", "checkpoint_count", "runtime_attempt_count", "event_types")}


def oracles():
    def reference_model_trace(inst, out, solve):
        exp = simulate(inst)
        got_ops = out.get("ops") or []
        if len(got_ops) != len(exp["ops"]):
            return False, f"op count {len(got_ops)} != {len(exp['ops'])}"
        for k, (g, e) in enumerate(zip(got_ops, exp["ops"])):
            if bool(g.get("ok")) != e["ok"]:
                return False, f"op {k} {e['op']}: ok={g.get('ok')} expected {e['ok']} ({g.get('error')})"
            if g.get("selected") != e["selected"]:
                return False, f"op {k} choose: selected={g.get('selected')} expected {e['selected']}"
            if g.get("returncode") != e["returncode"]:
                return False, f"op {k} {e['op']}: rc={g.get('returncode')} expected {e['returncode']}"
            if "state_after" in e and _strip(g.get("state_after")) != e["state_after"]:
                return False, f"op {k} {e['op']}: state {_strip(g.get('state_after'))} expected {e['state_after']}"
        if out.get("executor_calls") != exp["executor_calls"]:
            return False, f"executor calls {out.get('executor_calls')} expected {exp['executor_calls']}"
        fin = {tid: _strip(v) for tid, v in (out.get("final_states") or {}).items()}
        if fin != exp["final_states"]:
            return False, "final states differ"
        if sorted(out.get("evidence_files") or []) != exp["evidence_files"]:
            return False, f"evidence {out.get('evidence_files')} expected {exp['evidence_files']}"
        return True, f"{len(got_ops)} ops, {len(exp['executor_calls'])} runtime calls match"

    def lease_exclusivity(inst, out, solve):
        agents = {"self": inst["agent_id"], "other": inst["other_agent_id"]}
        ids = [t["task_id"] for t in inst["tasks"]]
        owner: dict[str, str] = {}
        for op, rec in zip(inst["script"], out.get("ops") or []):
            if op["op"] not in {"claim", "run", "execute"}:
                continue
            tid = ids[op["task"]]
            acting = agents[op.get("agent", "self")]
            st = rec.get("state_after")
            if tid in owner and acting != owner[tid] and rec.get("ok"):
                return False, f"{acting} succeeded on {tid} leased by {owner[tid]}"
            if st is not None:
                if tid in owner and st.get("lease_owner") != owner[tid]:
                    return False, f"lease owner of {tid} changed {owner[tid]} -> {st.get('lease_owner')}"
                if st.get("lease_owner") is not None:
                    owner[tid] = st["lease_owner"]
                if rec.get("ok") and st.get("lease_owner") != acting:
                    return False, f"{acting} succeeded on {tid} but lease owner is {st.get('lease_owner')}"
        for call in out.get("executor_calls") or []:
            if call.get("env_agent") != owner.get(call.get("task_id")) or call.get("env_task") != call.get("task_id"):
                return False, f"runtime launched outside the lease identity: {call}"
        return True, f"{len(owner)} leases, all single-identity"

    def no_terminal_reexecution(inst, out, solve):
        ids = [t["task_id"] for t in inst["tasks"]]
        terminal_seen: set[str] = set()
        expected_calls: list[str] = []
        for op, rec in zip(inst["script"], out.get("ops") or []):
            if op["op"] not in {"run", "execute"}:
                continue
            tid = ids[op["task"]]
            rc = rec.get("returncode")
            if rc is not None and rc != 75:
                if tid in terminal_seen:
                    return False, f"runtime re-executed terminal task {tid}"
                expected_calls.append(tid)
            st = rec.get("state_after") or {}
            if st.get("status") in TERMINAL:
                terminal_seen.add(tid)
        calls = [c.get("task_id") for c in out.get("executor_calls") or []]
        if calls != expected_calls:
            return False, f"runtime call sequence {calls} != {expected_calls}"
        attempts = sum(int((v or {}).get("runtime_attempt_count", 0)) for v in (out.get("final_states") or {}).values())
        if attempts != len(calls):
            return False, f"runtime_attempt_count total {attempts} != {len(calls)} launches"
        return True, f"{len(calls)} launches, none after a terminal state"

    def event_log_integrity(inst, out, solve):
        ids = [t["task_id"] for t in inst["tasks"]]
        last: dict[str, list] = {}
        for op, rec in zip(inst["script"], out.get("ops") or []):
            if op["op"] not in {"claim", "run", "execute"}:
                continue
            st = rec.get("state_after")
            if st is None:
                continue
            tid = ids[op["task"]]
            types, seqs = list(st.get("event_types") or []), list(st.get("event_seqs") or [])
            if seqs != list(range(1, len(types) + 1)):
                return False, f"{tid}: seqs {seqs} not contiguous"
            if not types or types[0] != "TASK_ACQUIRED":
                return False, f"{tid}: log does not start with TASK_ACQUIRED"
            prev = last.get(tid, [])
            if types[:len(prev)] != prev:
                return False, f"{tid}: event log rewritten (prefix lost)"
            last[tid] = types
        for tid, st in (out.get("final_states") or {}).items():
            if st is None:
                continue
            types = list(st.get("event_types") or [])
            if types.count("TASK_RESUMED") != int(st.get("claim_count", 0)) - 1:
                return False, f"{tid}: TASK_RESUMED count vs claim_count"
            if types.count("ASTRA_RUNTIME_STARTED") != int(st.get("runtime_attempt_count", 0)):
                return False, f"{tid}: runtime events vs runtime_attempt_count"
            if types.count("CHECKPOINT_CREATED") != int(st.get("checkpoint_count", 0)):
                return False, f"{tid}: checkpoint events vs checkpoint_count"
            terminal_events = [t for t in types if t in {"TASK_COMPLETE", "TASK_FAILED"}]
            if len(terminal_events) > 1 or (terminal_events and types[-1] != terminal_events[0]):
                return False, f"{tid}: events continue after terminal event"
            if (st.get("status") in TERMINAL) != bool(terminal_events):
                return False, f"{tid}: status {st.get('status')} vs terminal events {terminal_events}"
        return True, f"{len(last)} task logs append-only and consistent"

    def priority_shift_invariance(inst, out, solve):
        delta = 4000 if (len(inst["script"]) % 2 == 0) else -4000
        shifted = copy.deepcopy(inst)
        for t in shifted["tasks"]:
            t["manifest"]["priority"] = int(t["manifest"]["priority"]) + delta
        for op in shifted["script"]:
            if op["op"] == "edit_manifest" and op["field"] == "priority":
                op["value"] = int(op["value"]) + delta
        out2 = solve(shifted)
        same = (
            [(o.get("ok"), o.get("selected"), o.get("returncode"), _strip(o.get("state_after"))) for o in out.get("ops") or []]
            == [(o.get("ok"), o.get("selected"), o.get("returncode"), _strip(o.get("state_after"))) for o in out2.get("ops") or []]
            and out.get("executor_calls") == out2.get("executor_calls")
            and {k: _strip(v) for k, v in (out.get("final_states") or {}).items()} == {k: _strip(v) for k, v in (out2.get("final_states") or {}).items()}
            and sorted(out.get("evidence_files") or []) == sorted(out2.get("evidence_files") or [])
        )
        return same, f"uniform priority shift by {delta:+d} {'preserves' if same else 'changes'} the trace"

    return [
        {"id": "REFERENCE_MODEL_TRACE", "check": reference_model_trace},
        {"id": "LEASE_EXCLUSIVITY", "check": lease_exclusivity},
        {"id": "NO_TERMINAL_REEXECUTION", "check": no_terminal_reexecution},
        {"id": "EVENT_LOG_INTEGRITY", "check": event_log_integrity},
        {"id": "PRIORITY_SHIFT_INVARIANCE", "check": priority_shift_invariance},
    ]
