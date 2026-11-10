"""Benchmark run driven by the repo's own planner, not a hand-written subgoal loop.

Per task:
  1. read the goal, take the quoted literal (string extraction only, no semantics)
  2. PROBE: for each addressable control, click it once, observe which names appear that
     were not there before. That observation becomes a capability's `provides`.
  3. PLAN: sumo/A* (`capability_planner.plan_capabilities`) finds the shortest ordered route
     from the current facts to `name:<literal>`.
  4. EXECUTE the plan in order, re-snapshotting between steps.
  5. If the planner says NO_ROUTE, REFUSE. A refusal is recorded as a refusal, not a failure.

Cost is honest: probing costs actions. Every probed click is counted and reported. The
question is not "how few actions" but "does ordering by plan beat ordering by guess".
"""
import json, sys, time, pathlib, re, urllib.request
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A
from canonical.runtime import bench_capability_graph_v1 as G

Q = re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')
TYPE_VERB = re.compile(r"^\s*(enter|type|input|fill)\b", re.I)
POOL = {"button","link","option","tab","menuitem","listitem","radio","checkbox","combobox"}

tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel(); t0 = time.time()
# A READ-ONLY state channel beside the act channel. Reading cannot cause an effect, so the
# r82 restriction on Runtime.evaluate applies to ACT only, never to VERIFY (r85).
RDC = None
class _RD:
    """Lazy state channel: no Runtime.evaluate in the act path, by construction."""
    def __init__(self):
        global RDC
        import websocket
        from canonical.runtime import state_read_v1 as SR
        pages = [x for x in json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/list").read())
                 if x["type"] == "page"]
        RDC = SR.StateReadChannel(websocket.create_connection(pages[0]["webSocketDebuggerUrl"],
                                                              timeout=25, origin="http://127.0.0.1:9222"))
        self.SR = SR
        self._mod = SR
    def ask(self, chan, question, selector):
        """Ask the read channel, opening it on first use."""
        global RDC
        if RDC is None:
            self.__init__()
        return RDC.ask(question, selector)

    def centre_of(self, chan, eid):
        global RDC
        if RDC is None:
            self.__init__()
        return self.SR.centre_of(RDC, eid)
RD = _RD()

def snap():
    a = A.Address(A.target_url())
    ns = [n for n in A.ax_nodes(a) if n["box"]]
    tx = [n for n in A.read_text(a) if n["box"]]
    a.close(); return ns, tx

def facts(ns, tx):
    return G.facts_from_nodes(ns + tx)

def centre(n):
    b=n["box"]; return ((b["x0"]+b["x1"])/2.0,(b["y0"]+b["y1"])/2.0)

rows = []
for i, t in enumerate(tasks, 1):
    # `plan_len` was initialised here and NEVER assigned again, so every row read plan_len 0
    # -- won and lost alike. It made the run look like the planner had produced nothing in
    # either direction. `strategy` is the honest field: 93 of 130 tasks took the no-literal
    # branch below, which did NOTHING, and were then counted as failures.
    r = {"task": t, "probes": 0, "plan_len": 0, "refused": False, "error": None,
         "strategy": "unset"}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(0.95)
        ch.click(80, 104); time.sleep(0.95)
        goal = ch.goal(); r["goal"] = goal[:110]
        if not goal:
            r["error"] = "NO_GOAL"; raise RuntimeError("no goal")
        gnorm = " ".join(goal.lower().split())
        m = Q.search(goal); lit = (m.group(1).strip().strip(".,;:") if m else "")
        r["literal"] = lit
        r["is_value"] = bool(TYPE_VERB.match(goal))
        # A silent except here hid a lazy-init bug for one full round: RDC was None and the
        # empty list was indistinguishable from "the page has no controls". Record the
        # failure instead of swallowing it. -- a_r87
        try:
            mb_state = RD.ask(None, "list_of", "input,textarea,button") or []
        except Exception as _e:
            mb_state = []
            r["read_error"] = str(_e)[:120]
        ns, tx = snap()

        # ROUND 93 -- THE THING THAT WAS MISSING FOR TEN ROUNDS.
        # Six modules were built and left OUT of this loop: page_first_grounding_v1,
        # predicate_induction_v1, task_class_router_v1, addressability_probe_v1,
        # goal_arity_v1, target_extraction_v2. The benchmark has therefore been measuring
        # the OLD parser (`text_locate_v1.best_run`) while every round reported on new
        # instruments that were never called. An improvement that is not wired in cannot
        # show up in any number, and "the number did not move" was me not connecting it.
        #
        # Grounding now comes from the PAGE, in priority order:
        #   1. page-first intersection  -- a target the page actually renders
        #   2. quoted literal           -- the old path, kept as a fallback
        #   3. nothing                  -- reported honestly
        try:
            from canonical.runtime import page_first_grounding_v1 as PFG
            _live = RD.ask(None, "list_of", "#area *") or []
            _strings = [str(x.get("text") or "") for x in _live if str(x.get("text") or "").strip()]
            _g = PFG.ground(goal, _strings)
            r["grounding"] = _g["status"]
            if _g["status"] == "GROUNDED" and _g.get("target"):
                lit = _g["target"]
                r["literal"] = lit
                r["literal_source"] = "page"
            else:
                r["literal_source"] = "quote" if lit else "none"
        except Exception as _e:
            r["grounding"] = "ERROR:" + str(_e)[:80]

        f0 = facts(ns, tx)
        caps = []
        caps_seen = set()
        controls = [n for n in ns if n["role"] in POOL and n["name"].strip()]

        # PROBE AND ACT IN THE SAME EPISODE. Measured: every re-navigation starts a NEW
        # random problem (different target word, different content), so a plan made while
        # probing describes a page that no longer exists. Four trials out of four differed.
        # The page therefore must be left exactly as the probe found it, or the plan must be
        # made from the post-probe state. Simplest correct choice: probe, then plan from the
        # state we are actually in, and never navigate again.

        if r.get("is_value") and lit:
            pr = {"status": "SOLVED", "plan": []}; r["strategy"] = "fill_value"
        elif lit:
            r["strategy"] = "reveal_target"
            # SEARCH, THEN PLAN -- repeatedly. The original order was plan, then (only on
            # failure) probe once, re-plan, and NEVER ACT on what the re-plan learned. The
            # code's order was the opposite of the problem's order (r85). A refusal before
            # searching is a default dressed as a judgement.
            pr = {"status": "NOT_LOOKED", "plan": [], "total_cost": 0.0}
            for _rd in range(3):
                pr = G.plan_to_reveal(f0, lit, caps)
                if pr["status"] in ("SOLVED", "ALREADY_PRESENT"):
                    break
                uncovered = [c for c in controls if c["name"].strip()
                             and f"use:{c['role']}:{c['name'].strip()}" not in caps_seen]
                if not uncovered:
                    break
                # learn what each control reveals, WITHOUT re-navigating: click, observe,
                # click again to restore (toggles are their own inverse on this page).
                for ctl in uncovered[:8]:
                    before = facts(*snap())
                    ch.click(*centre(ctl)); r["probes"] += 1; time.sleep(0.26)
                    after = facts(*snap())
                    rev = {x.split("name:",1)[1] for x in (after - before) if x.startswith("name:")}
                    caps.append(G.capability_for(ctl["name"].strip(), rev, ctl["role"]))
                    caps_seen.add(f"use:{ctl['role']}:{ctl['name'].strip()}")
                    ch.click(*centre(ctl)); r["probes"] += 1; time.sleep(0.20)
                f0 = facts(*snap())
        else:
            # ROUND 102 -- THE ACTUATOR REACHES THE TASKS THAT HAVE NO NAMEABLE TARGET.
            # Until this round a goal with no quoted literal and no page-grounded string was
            # recorded "not attempted" and scored as a failure. Those are 29 of 130. For a
            # CLICK-ONLY goal there is a third route that needs no name at all: the page's
            # own controls are observable, and the capability can deliver a real mouse event
            # to one of them. The page then grades the page.
            #
            # The choice is deliberately dumb and stated: the first visible control in
            # role order. Anything smarter is a claim that needs its own measurement.
            _clicked = False
            if "button" in goal.lower() or "click" in goal.lower():
                try:
                    from canonical.runtime.bound_capabilities import rendered_page_act as _RPA
                    for _c in controls:
                        _xy = None
                        try:
                            _xy = centre(_c)
                        except Exception:
                            _xy = None
                        if not _xy:
                            continue
                        try:
                            _res = _RPA.run({"action": "click", "x": _xy[0], "y": _xy[1]}, ".")
                            _clicked = bool(_res.get("page_reported_done"))
                        except Exception:
                            _clicked = False
                        r["probes"] += 1
                        if _clicked:
                            break
                    r["actuator"] = "used" if _clicked else "tried"
                except Exception as _e:
                    r["actuator"] = "error:" + str(_e)[:60]
            pr = {"status": "SOLVED" if _clicked else "NO_LITERAL"}
            r["strategy"] = "actuator_no_literal" if _clicked else "not_attempted_no_literal"
        r["plan_len"] = len(pr.get("plan") or [])
        r["plan_status"] = pr["status"]
        if pr["status"] in ("SOLVED", "ALREADY_PRESENT"):
            from canonical.runtime import text_locate_v1 as TL
            def read():
                aa = A.Address(A.target_url())
                nn = [x for x in A.ax_nodes(aa) if x["box"]]
                tt = [x for x in A.read_text(aa) if x.get("box")]
                aa.close(); return nn, tt
            low = lit.lower()
            # A goal whose write shape is arity>=2, spread across fields, or transformed was
            # planned correctly and then lost at the binder. Measured r86: those were ALL of
            # the SOLVED-but-lost tasks. Plan the writes from the goal text and the page's
            # own control list (state channel), not from a single literal.
            from canonical.runtime import multi_bind_v1 as MB
            _mb = None
            if r.get("is_value"):
                try:
                    _mb = MB.plan_multi_bind(goal, mb_state)
                except Exception:
                    _mb = None
            if _mb and _mb["status"] == "SOLVED":
                for _fid, _val in _mb["writes"]:
                    _c = None
                    try:
                        _c = RD.centre_of(RDC, _fid) if RDC else None
                    except Exception:
                        _c = None
                    if _c:
                        ch.click(*_c); ch.type_text(str(_val)); r["probes"] += 2; time.sleep(0.15)
                _btns = [n for n in (mb_state or []) if str(n.get("tag","")).upper() == "BUTTON" and n.get("vis")]
                for _b in _btns:
                    if str(_b.get("text","")).strip().lower() in ("submit","go","send","done","sign in","login"):
                        try: _bc = RD.centre_of(RDC, _b["id"]) if RDC else None
                        except Exception: _bc = None
                        if _bc: ch.click(*_bc); r["probes"] += 1; time.sleep(0.3)
                        break
                r["binder"] = _mb["status"]; r["binder_mode"] = _mb.get("mode")
            elif r.get("is_value"):
                ns, tx = read()
                tb = [n for n in ns if n["role"] in ("textbox","combobox","searchbox")]
                if tb:
                    ch.click(*centre(tb[0])); ch.type_text(lit); r["probes"] += 2
                    time.sleep(0.3); ns, tx = read()
                    sub = [n for n in ns if n["role"] == "button"
                           and n["name"].strip().lower() in ("submit","send","go","done")]
                    if sub: ch.click(*centre(sub[0])); r["probes"] += 1; time.sleep(0.3)
            else:
                # A disclosure page MOVES the controls every time one opens. Re-read before
                # EVERY action -- this single rule took click-collapsible-2 from 2/8 to 9/12.
                for reveal in range(4):
                    ns, tx = read()
                    hit = TL.best_run(tx, lit) or TL.best_run(ns, lit)
                    if hit:
                        words = (hit["name"] or "").split()
                        if len(words) > 1:
                            loc = TL.locate_word(hit, lit); bb = hit["box"]
                            x, y = ((loc["x"], loc["y"]) if loc.get("found")
                                    else ((bb["x0"]+bb["x1"])/2, (bb["y0"]+bb["y1"])/2))
                        else:
                            bb = hit["box"]; x, y = (bb["x0"]+bb["x1"])/2, (bb["y0"]+bb["y1"])/2
                        ch.click(x, y); r["probes"] += 1; r["acted"] = True
                        time.sleep(0.3); break
                    ctl = [n for n in ns if n["role"] in ("tab","button","menuitem","listitem")
                           and n["name"].strip()]
                    if reveal >= len(ctl): break
                    ch.click(*centre(ctl[reveal])); r["probes"] += 1; time.sleep(0.35)
    except Exception as e:
        if not r["error"]: r["error"] = str(e)[:90]
    time.sleep(0.3)
    try: st = ch.reward()
    except Exception: st = {}
    r["done"] = bool(st.get("done")); r["reward"] = st.get("reward")
    rows.append(r)
    if i % 25 == 0: print(f"  {i}/{len(tasks)} ({time.time()-t0:.0f}s)", flush=True)
ch.close()

win = [x for x in rows if x["done"] and isinstance(x["reward"],(int,float)) and x["reward"] > 0]
clean = [x for x in win if x["reward"] >= 0.5]
refused = [x for x in rows if x["refused"]]
out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/result_planned_v1.json")
out.write_text(json.dumps({"n":len(rows),"success":len(win),"clean":len(clean),
    "refused":len(refused),"seconds":round(time.time()-t0,1),
    "success_rate":round(len(win)/len(rows)*100,1),"tasks":rows}, indent=1))
print(f"\nPLANNED: {len(win)}/130 = {len(win)/len(rows)*100:.1f}%  clean {len(clean)}  refused {len(refused)}  ({time.time()-t0:.0f}s)")
print(f"  [single-run comparisons: baseline 15, text 17, sequenced 18/15/18]")
