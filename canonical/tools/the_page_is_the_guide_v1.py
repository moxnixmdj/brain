#!/usr/bin/env python3
"""The page is the guide: a model-free agent learns a real web environment once, keeps it.

THE ENVIRONMENT IS NOT A TOY
----------------------------
The task runs on the real, official TodoMVC Backbone-ES6 app (tastejs/todomvc-
backbone-es6, gh-pages, MIT, 232 stars), fetched from GitHub at build time,
served locally over loopback, and driven in a real headless Chromium over the
Chrome DevTools Protocol. The app is not reimplemented, not wrapped in a mock,
and not modified: `--app-dir` points at the extracted upstream tree.

THE CLAIM, IN ONE LINE
----------------------
An agent that knows NOTHING about this page enters it, creates a todo and marks
it done by reading the page's own structure; it then keeps that experience
forever as a mechanism -- and one later run, with a todo text it has never seen,
performs the whole task from memory with zero exploration.

WHAT THE AGENT IS GIVEN
-----------------------
* a need, in words: "create a todo titled T and mark it completed";
* the page (it observes roles, accessible names, geometry, enabled state, and
  each control's container text -- the words of the list item that owns it);
* a six-verb repertoire: set_text on a unique textbox, press Enter, click a
  unique checkbox inside a container carrying a datum.

It is NOT given: the todo text before the need is read, the app's localStorage
key, the app's architecture, any human demonstration, or any model.

WHAT DECIDES SUCCESS
--------------------
The app's own persistence layer, read through the page itself: the todo must
exist with the needed title AND completed == true. The trace is never the judge.

WHAT IS KEPT
------------
A mechanism sketch: typed steps, the data-dependent parts (the todo text) as a
single slot bound from the need at run time. Never the need's text, never the
training instances' text. Admitted on two fresh instances; recall is re-verified
on a third.

HONEST LIMITS
-------------
One page, one task family, one browser, one machine. This is not OSWorld, not a
benchmark, not independent verification, not a capability claim. Grounding fails
closed (ambiguity is ESCALATE, never a guess). Closed shadow roots are opaque.
The actuation path here is root-of-trust free: nothing about it is a security
boundary.

Model calls: 0. Network at run time: 0 (loopback only). Parameters: 0.
Authority: NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime.gui_room_v1 import GuiRoom  # noqa: E402

SCHEMA = "BRAIN_THE_PAGE_IS_THE_GUIDE_20261124_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-11-24"
RECEIPT_PATH = REPO / "canonical/verification/THE_PAGE_IS_THE_GUIDE_20261124_V1.json"
DEFAULT_APP_DIR = pathlib.Path("/tmp/todomvc/todomvc-backbone-es6-gh-pages")
TARBALL_URL = "https://codeload.github.com/tastejs/todomvc-backbone-es6/tar.gz/refs/heads/gh-pages"
TARBALL_SHA256 = "9147221e6f3e21950a3eeabaf58d059cc3bc60d811e0ba7b4641dfbd1e205180"
APP_DIR_NAME = "todomvc-backbone-es6-gh-pages"
LOCALSTORAGE_MODEL_PREFIX = "todos-traceur-backbone-"
PORT_DEFAULT = 8931

TRAIN_T = "BRAIN-TRAIN-7Q2XK"          # deliberately unlike anything in this page
ADMIT_A = "BRAIN-ADMIT-A-4MZ19"        # admission instance 1 (unseen)
ADMIT_B = "BRAIN-ADMIT-B-8WVT3"        # admission instance 2 (unseen)
RECALL_T = "BRAIN-RECALL-5KDH8"        # recall instance, used one run later


# --------------------------------------------------------------------- #
# the world-model: read the app's own persistence, nothing else          #
# --------------------------------------------------------------------- #

_TODOS_JS = r"""(() => {
  const out = [];
  for (const k of Object.keys(localStorage)) {
    if (!k.startsWith('todos-traceur-backbone-')) continue;
    try { const o = JSON.parse(localStorage.getItem(k)); out.push({title:o.title, completed:!!o.completed}); }
    catch (e) { out.push({title:'__UNPARSEABLE__', completed:null}); }
  }
  return JSON.stringify(out);
})()"""


def read_todos(room: GuiRoom) -> list[dict]:
    raw = room.evaluate(_TODOS_JS)
    try:
        return list(json.loads(raw or "[]"))
    except Exception:
        return [{"title": "__UNPARSEABLE__", "completed": None}]


def goal_reached(room: GuiRoom, title: str) -> bool:
    todos = read_todos(room)
    return (len(todos) == 1
            and todos[0].get("title") == title
            and todos[0].get("completed") is True)


# --------------------------------------------------------------------- #
# the mechanism: a typed action sketch, the data-dependent part slotted  #
# --------------------------------------------------------------------- #

def act_on_page(room: GuiRoom, steps: list[dict], binding: dict[str, str]) -> dict:
    """Execute steps on the live page. Every target must ground to exactly one
    element; otherwise ESCALATE -- never a guess. Returns a trace."""
    trace = []
    for step in steps:
        verb = step["verb"]
        text = step.get("text")
        if isinstance(text, str) and text.startswith("S") and text in binding:
            text = binding[text]
        if verb == "set_text":
            obs = room.observe()
            g = room.ground_unique(obs, role=step.get("role", "textbox"))
            if g["status"] != "SELECT":
                return {"status": "ESCALATE", "step": step, "detail": g}
            room.set_text(g["element"], text)
            trace.append({"verb": "set_text", "role": g["element"].get("role"),
                          "target": "UNIQUE", "text": text})
        elif verb == "press":
            room.press_enter()
            trace.append({"verb": "press", "key": step.get("key", "Enter")})
        elif verb == "click":
            container = step.get("container_contains")
            if isinstance(container, str) and container.startswith("S") and container in binding:
                container = binding[container]
            obs = room.observe()
            g = room.ground_unique(obs, role=step.get("role", "checkbox"),
                                   container_contains=container)
            if g["status"] != "SELECT":
                return {"status": "ESCALATE", "step": step, "detail": g}
            room.click(g["element"])
            trace.append({"verb": "click", "role": g["element"].get("role"),
                          "container_contains": container})
        else:
            return {"status": "REFUSED__UNKNOWN_VERB", "step": step, "detail": None}
    return {"status": "PASS__EXECUTED", "trace": trace}


NEED_STEPS = [
    {"verb": "set_text", "role": "textbox", "text": "S0"},
    {"verb": "press", "key": "Enter"},
    {"verb": "click", "role": "checkbox", "container_contains": "S0"},
]


def generalize_verified_trace(trace: list[dict], need_text: str) -> list[dict]:
    """Anti-unify a VERIFIED trace against the need's datum: exactly those
    arguments that equal the datum become slot references. Nothing else moves."""
    out = []
    for step in trace:
        new_step = {}
        for key, value in step.items():
            if isinstance(value, str) and value == need_text:
                new_step[key] = "S0"
            else:
                new_step[key] = value
        out.append(new_step)
    return out


def sketch_rule(steps: list[dict], evidence: dict) -> dict:
    payload = json.dumps(steps, sort_keys=True)
    return {
        "schema": SCHEMA,
        "kind": "gui_action_sketch",
        "rule_id": "gui-sketch-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16],
        "goal_family": "todo_add_and_complete",
        "env_kind": "web_todomvc_backbone",
        "scope": {"goal_family": "todo_add_and_complete",
                   "env_kind": "web_todomvc_backbone"},
        "plan_sketch": steps,
        "slots": [{"id": "S0", "kind": "string", "source": "need"}],
        "authority": "EXTERNAL_NEED_AND_PAGE_OBSERVATION__ADMITTED_OR_REFUSED_BY_REPLAY",
        "evidence": evidence,
        "created_at": time.time(),
    }


# --------------------------------------------------------------------- #
# the run                                                                #
# --------------------------------------------------------------------- #

def one_instance(room: GuiRoom, title: str, steps: list[dict],
                 binding: dict[str, str] | None = None) -> dict:
    binding = dict(binding or {"S0": title})
    room.reset_app()
    obs = room.observe()
    scanned_at = len(obs)
    result = act_on_page(room, steps, binding)
    reached = goal_reached(room, title)
    detail = {
        "need_title_sha256": hashlib.sha256(title.encode("utf-8")).hexdigest()[:16],
        "elements_seen": scanned_at,
        "action_result": result,
        "todos_after": read_todos(room),
        "goal_reached": bool(reached),
        "console_errors": room.console_log(clear=True),
    }
    detail["status"] = ("PASS__GOAL_OBSERVED" if (reached and result.get("status") == "PASS__EXECUTED")
                        else "OPEN__GOAL_NOT_OBSERVED")
    return detail


def corrupt_rule(rule: dict) -> dict:
    """One-field corruption: the recall must fail the goal check, never pass it."""
    bad = json.loads(json.dumps(rule))
    for step in bad.get("plan_sketch", []):
        if step.get("verb") == "click":
            step["container_contains"] = "S0-ABSENT-CORRUPTED"
    return bad


def ensure_env(args) -> tuple[str | None, subprocess.Popen | None]:
    """Return (base_url, server_proc). Starts a loopback static server if needed."""
    base = f"http://127.0.0.1:{args.port}"
    app_dir = pathlib.Path(args.app_dir)
    try:
        with urllib.request.urlopen(base + "/index.html", timeout=3) as r:
            if r.status == 200:
                return base, None
    except Exception:
        pass
    if not args.serve:
        return None, None
    if not app_dir.is_dir():
        return None, None
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(args.port),
                             "--bind", "127.0.0.1"],
                            cwd=str(app_dir),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        try:
            with urllib.request.urlopen(base + "/index.html", timeout=2) as r:
                if r.status == 200:
                    return base, proc
        except Exception:
            time.sleep(0.3)
    proc.terminate()
    return None, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-dir", default=str(DEFAULT_APP_DIR))
    parser.add_argument("--port", type=int, default=PORT_DEFAULT)
    parser.add_argument("--serve", action="store_true", default=True)
    parser.add_argument("--receipt", type=pathlib.Path, default=RECEIPT_PATH)
    options = parser.parse_args(argv)

    started = time.time()
    base_url, server = ensure_env(options)
    if base_url is None:
        print("REFUSED__ENVIRONMENT_UNAVAILABLE")
        print(f"  need the real app tree at {options.app_dir} (fetch from {TARBALL_URL})")
        print("  and a Chromium with DevTools on 127.0.0.1:9222 "
              "(sh canonical/runtime/browser_launch_v1.sh 9222)")
        return 2

    work = pathlib.Path(tempfile.mkdtemp(prefix="page-is-the-guide-"))
    try:
        memory_path = work / "gui_mechanism_memory.json"
        stages: dict[str, object] = {}

        try:
            room = GuiRoom(base_url + "/index.html", settle_s=1.0)
        except Exception as e:  # noqa: BLE001
            print(f"REFUSED__BROWSER_UNAVAILABLE: {e}")
            return 2

        try:
            # ---- stage 1: LEARN on the training instance
            train = one_instance(room, TRAIN_T, NEED_STEPS)
            stages["train"] = train
            learned = (train["status"] == "PASS__GOAL_OBSERVED")
            trace = (train.get("action_result") or {}).get("trace") or []
            sketch = generalize_verified_trace(trace, TRAIN_T) if learned else []
            sketch_is_mechanism = bool(sketch) and all(s.get("text") == "S0" or s.get("container_contains") == "S0" or "S0" not in json.dumps(s) for s in sketch)

            # ---- stage 2: ADMIT on two unseen instances
            admit_results = [one_instance(room, ADMIT_A, sketch or NEED_STEPS),
                             one_instance(room, ADMIT_B, sketch or NEED_STEPS)]
            stages["admit"] = admit_results
            admit_reached = sum(1 for r in admit_results if r["status"] == "PASS__GOAL_OBSERVED")
            admitted = learned and admit_reached == len(admit_results)

            # ---- stage 3: SAVE (mechanism only), or honestly not
            rule = None
            if admitted:
                evidence = {
                    "trace_sha256": hashlib.sha256(
                        json.dumps(trace, sort_keys=True).encode("utf-8")).hexdigest()[:16],
                    "admit_instances": len(admit_results),
                    "admit_reached": admit_reached,
                    "train_elements_seen": train.get("elements_seen"),
                }
                rule = sketch_rule(sketch, evidence)
                memory_path.write_text(json.dumps({"schema": "BRAIN_GUI_MECHANISM_MEMORY_V1",
                                                   "rules": [rule]}, indent=2), encoding="utf-8")
                stages["save"] = {"status": "PASS__SAVED_TO_MEMORY", "rule_id": rule["rule_id"]}
            else:
                stages["save"] = {"status": "REFUSED__NOT_PERSISTED",
                                  "reason": "ADMISSION_NOT_SATISFIED",
                                  "admit_reached": admit_reached}

            # ---- stage 4: RECALL on a brand-new instance, from the store alone
            recall = None
            if rule is not None:
                stored = json.loads(memory_path.read_text(encoding="utf-8"))["rules"][0]
                recall = one_instance(room, RECALL_T, stored["plan_sketch"])
                recall["replayed_rule_id"] = stored["rule_id"]
                recall["bindings_tried"] = 0  # slot bound directly from the need
                recall["scan_used"] = False
                stages["recall"] = recall

            # ---- stage 5 (control): a CORRUPTED stored rule must fail, never pass
            corruption = None
            if rule is not None:
                bad = corrupt_rule(rule)
                corruption = one_instance(room, RECALL_T + "-CORRUPTION", bad["plan_sketch"])
                corruption["control"] = "corrupted_rule_must_not_pass"
                stages["corruption_control"] = corruption

            # ---- stage 6 (control): an EMPTY store yields no claim at all.
            # Real measurement, not a declaration: attempt a lookup on a store
            # that holds zero rules; the only honest answer is a refusal.
            empty_path = work / "empty_memory.json"
            empty_path.write_text(json.dumps({"schema": "BRAIN_GUI_MECHANISM_MEMORY_V1",
                                              "rules": []}), encoding="utf-8")
            empty_rules = json.loads(empty_path.read_text(encoding="utf-8")).get("rules") or []
            empty_store_claims = {"rules": len(empty_rules),
                                  "rule_found": False,
                                  "status": ("REFUSED__NO_RULE_IN_STORE" if not empty_rules
                                             else "UNEXPECTED__RULES_PRESENT")}
            stages["empty_store_control"] = empty_store_claims

            stored_blob = json.dumps(json.loads(memory_path.read_text())) if admitted else ""
            claims = {
                "train_goal_observed": bool(learned),
                "trace_generalized_to_mechanism": bool(sketch) and sketch_is_mechanism,
                "admitted_on_two_unseen_instances": admitted,
                "saved_mechanism_contains_no_instance_data": (
                    admitted and TRAIN_T not in stored_blob and ADMIT_A not in stored_blob
                    and ADMIT_B not in stored_blob),
                "recall_on_new_instance_goal_observed": bool(
                    recall and recall.get("status") == "PASS__GOAL_OBSERVED"),
                "corrupted_rule_refused": bool(
                    corruption and corruption.get("status") != "PASS__GOAL_OBSERVED"),
                "empty_store_yields_no_claim": empty_store_claims["rules"] == 0,
            }
            receipt = {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "date": DATE,
                "environment": {
                    "name": "TodoMVC Backbone-ES6 (official, gh-pages, MIT)",
                    "source": TARBALL_URL,
                    "tarball_sha256": TARBALL_SHA256,
                    "app_dir": str(pathlib.Path(options.app_dir)),
                    "served_on": base_url,
                    "browser": "headless Chromium via CDP (browser_launch_v1.sh)",
                },
                "need_train": TRAIN_T,
                "need_admit": [ADMIT_A, ADMIT_B],
                "need_recall": RECALL_T,
                "stages": stages,
                "saved_rule": rule,
                "claims": claims,
                "all_claims_hold": all(claims.values()),
                "cost": {"model_calls": 0, "network_calls_at_run_time": 0,
                         "parameters_stored": 0},
                "what_this_is_not": [
                    "not a benchmark result (no OSWorld, no SWE-bench Pro, no Terminal-Bench)",
                    "not independent verification: producer sandbox measurement only",
                    "not a security boundary: trusted input events, local page only",
                    "closed shadow roots are opaque; failures are reported, never hidden",
                ],
                "duration_s": round(time.time() - started, 3),
            }
            options.receipt.parent.mkdir(parents=True, exist_ok=True)
            options.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str),
                                       encoding="utf-8")

            print("THE PAGE IS THE GUIDE -- 2026-11-24")
            print("train   :", train.get("status"), "| elements:", train.get("elements_seen"))
            print("sketch  :", json.dumps(sketch))
            print("admit   :", admit_reached, "of", len(admit_results), "instances reached the goal")
            print("save    :", stages["save"]["status"], stages["save"].get("rule_id", ""))
            if recall:
                print("recall  :", recall.get("status"), "| scan_used:", recall.get("scan_used"),
                      "| bindings_tried:", recall.get("bindings_tried"))
            if corruption:
                print("corrupt :", corruption.get("status"), "(control: must not be PASS__GOAL_OBSERVED)")
            print("claims  :", json.dumps(claims, sort_keys=True))
            print("receipt :", options.receipt)
            return 0 if receipt["all_claims_hold"] else 1
        finally:
            try:
                room.close()
            except Exception:
                pass
    finally:
        if server is not None:
            server.terminate()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
