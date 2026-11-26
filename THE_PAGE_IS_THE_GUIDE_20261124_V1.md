# The page is the guide — 2026-11-24

Authority: `NONE__PRODUCER_RUN_SANDBOX`. A sandbox measurement and a design record, not a benchmark
score, not independent verification, not a capability claim, and not §6 completion. Re-runnable:
`python3 canonical/tools/the_page_is_the_guide_v1.py` (exit 0; 7/7 claims hold when the environment
below exists).

Branch: `arena/d86a0174-brain`.

## 0. Requirements confirmed (as read this session)

Read fully, treated as new. Own weights/architecture/agent; zero runtime model calls; parameters
only as computed mechanisms; instant knowledge from the external JIT source; research first
(project exhaustively, then web, with 10/11/2026 as "today"); first principles; Elon's law (remove
before adding); real understanding over pattern matching; honest separation of verified, unverified,
failed; no leakage, no borrowed outputs, no test hand-solved; one branch; protected paths untouched;
never ask the owner questions; never claim done without §6. §2 resolution stands: the persisted
object below contains *mechanism* (typed steps + a slot) only — no data, no facts, removable with one
`rm`, retrained nothing. The §6 bar is untouched and unmet.

## 1. Research findings

### Project (what already existed, reused, not rebuilt)

* `canonical/runtime/browser_launch_v1.sh` — obtains a REAL headless Chromium (`@sparticuz/chromium`
  from the npm registry, the only browser path this sandbox can run; Playwright/Puppeteer CDNs and
  `apt`/root are unreachable). This round it installed cleanly in 11.5 s and served the page; the
  repo's lawful launch path made this test possible.
* `canonical/runtime/osworld_v21_browser_cdp_v1.py` — a declarative CDP driver bound to OSWorld's
  exposed endpoint; reused the CDP API knowledge, not the module (it needs Playwright, which is
  absent here and was not installed).
* `canonical/runtime/exact_dom_grounding.py`, `consensus_dom_grounding.py` — deterministic,
  fail-closed element grounding by role/name/text/attrs. The GUI room implements the same
  unique-or-ESCALATE contract; it did not grow a second notion of "fires".
* `canonical/swe_kernel/perfect_algorithm_v1.py` — last round's document-as-test-suite circuit
  (mechanism sketches, anti-unification, admit-on-fresh-instances). The GUI loop is the same
  discipline in a different executor: same admission rule (save nothing without fresh instances),
  same refusal shapes, implemented GUI-side because the expression sketch is AST-bound.
* Non-obvious checked-and-not-used: `computer_env_v1` (discovers affordances, not task execution),
  `browser_v1.py` + `browser_launch_v1.sh` (seam module, reused its launch path only),
  OSWorld ledger stacks (completion proof, not applicable).

### Web (inputs, not truth; fetched 2026-11-24)

* Accessibility trees beat screenshots for structured interfaces: 15.6% (a11y) vs 7.0% (pixels
  alone) on 358 OSWorld tasks; 20.7% with a compressed tree [1]. Browser/desktop consensus in
  2026 guides is the same: a11y tree first, pixels as fallback [2]. We adopt exactly that, minus
  the model: the tree here is the page's own DOM (roles, accessible names, geometry) — deterministic,
  model-free.
* The frontier's best open numbers stand unchanged: OSWorld-Verified saturated (90.19%), OSWorld
  2.0 unsolved (~44% binary, Opus 5), SWE-bench Pro separates agents (~61.5% standardized) [3,4].
  Nothing we build today is a benchmark result; nothing below should be quoted as one.
* 2026 research on persistent computer-use skills agrees on the mechanism: store versioned,
  admitted procedures, not raw traces [5]. Our mechanism sketches are that, plus a hard gate.
* README-embedded instructions are obeyed by high-privilege agents at high rates — provenance of
  the guide matters [6]. Our stored authority labels the source every time; the runtime still
  re-verifies.

[1] https://yourstash.ai/articles/accessibility-tree-vs-screenshot-ai-agents
[2] https://dev.to/agdex_ai/beyond-the-browser-building-desktop-gui-agents-in-2026-with-ui-tars-claude-computer-use-and-2gpe
[3] https://presenc.ai/research/osworld-computer-use-leaderboard-2026
[4] https://decodethefuture.org/en/ai-agent-benchmarks-2026/
[5] https://arxiv.org/html/2609.04869v1
[6] https://www.alphaxiv.org/abs/2603.11862

## 2. What was built

* NEW `canonical/tools/cdp_bridge_v1.cjs` — a 120-line stdio↔CDP bridge (node ≥22 built-ins only):
  open/navigate, evaluate, click at coordinates, insert text, Enter keydown with `text='\r'`
  (rawKeyDown suppresses keypress; the real app binds `keypress` — found by running it), console
  drain, close. It is plumbing; all decisions live elsewhere.
* NEW `canonical/runtime/gui_room_v1.py` — the GUI room: opens the page in Chromium, observes it
  (injected serializer computes role/accessible-name/title/geometry/enabled and each control's
  `container_text` — the words of the owning list item), acts with trusted Input-domain events,
  reads the app's OWN persistence (`localStorage`) as the goal oracle, and grounds unique-or-ESCALATE.
* NEW `canonical/tools/the_page_is_the_guide_v1.py` — the loop, end to end on the real app.
* Tests NEW `canonical/tests/test_gui_mechanism_loop_v1.py` — unit tests always run; the live
  end-to-end test skips with a printed reason when the app tree / node / Chromium are absent.
  No test fakes a browser.

## 3. Hard test (not a benchmark): the exact run

Environment: real headless Chromium 158.0.8127.0 (CDP on 9222), real official app served on loopback
(`http://127.0.0.1:8931`, tarball sha256 `9147221e6f3e21950a3eeabaf58d059cc3bc60d811e0ba7b4641dfbd1e205180`,
MIT, 232 stars, Backbone ES6 2018 — chosen because it is a real, nontrivial, self-contained app that
must parse with Traceur and persist through backbone.localStorage).

The agent was given only: the need in words ("create a todo titled T, mark it completed"), the page
itself, and a three-verb repertoire. NOT given: the todo text before reading the need, the storage
key, the app architecture, or any model.

Results (receipt `canonical/verification/THE_PAGE_IS_THE_GUIDE_20261124_V1.json`, exit 0):

* TRAIN (T = BRAIN-TRAIN-7Q2XK, deliberately unlike anything in the page): scan saw 3 elements;
  the unique-textbox binding held; text inserted through the Input domain (real keystrokes); Enter
  created the todo through the app's own `keypress #new-todo` handler; the checkbox inside the list
  item whose container text carries T was clicked. **Goal OBSERVED in the app's own storage**
  (`{title: …, completed: true}`), not from the trace.
* GENERALIZE: anti-unification of the verified trace against the need's datum produced
  `set_text(textbox, S0) → press Enter → click(checkbox where container contains S0)` — the only
  data-dependent arguments slotted, nothing else touched.
* ADMIT: two unseen instances (T = BRAIN-ADMIT-A-4MZ19, BRAIN-ADMIT-B-8WVT3), both goal-observed,
  1 binding try each. Mechanism saved as `gui-sketch-ebaff70d7db1b37b`.
* RECALL (T = BRAIN-RECALL-5KDH8, brand-new): zero exploration, zero binding tries, goal observed,
  re-verified through storage.
* Controls: a corrupted stored rule (one field) FAILS the goal check and is reported, never trusted;
  an empty store yields a refusal, never a claim; the saved rule's JSON contains none of the four
  instance texts (checked verbatim).
* Console shows one benign pre-existing message (`unload` permissions policy, 4 occurrences); recorded,
  not hidden. The app targets 2018 Chrome; it works unchanged.

## 4. Verdict deltas (this round)

**True:** expression-level mechanisms (last round) AND GUI-control mechanisms (this round) can be
learned once, admitted on unseen instances, kept as data-free templates, and recalled instantly with
the goal re-verified — in a real browser, against a real application, with zero models anywhere.

**Unproven:** anything beyond one page/one task family/one browser; shadow DOM; iframes; long
workflows (OSWorld 2.0's ~318 tool calls); SWE-bench Pro class repair. No benchmark was run or will
be quoted.

**Still missing:** an independent verifier; a harness that runs THIS agent on OSWorld 2.0 / Pro /
Terminal-Bench 4.0; the preregistered sketch-vs-trace-cache transfer experiment; GUI needs beyond
"add and complete" need task-family expansion (delete, edit, filter — mechanical extensions, not
done).

**Answer to "why not show the model the advanced actions once?"** — because showing is not storing
(no weight warehouse allowed), a trace names one instance, and without admission on fresh instances
nothing has been learned. This round shows the positive form of that argument on a real GUI: the
stored object is the mechanism, the runtime re-verifies by execution, and one corrupt field breaks
it — as it should.

## 5. Rejected ideas for cause

* Pixel/vision-based grounding — forbidden (no model) and weaker on a11y-rich pages (7.0% vs 20.7%
  [1]); kept out.
* Rewriting the app or wrapping it in a mock — that would make the test synthetic and the result
  meaningless; served the upstream tree unmodified.
* Hardcoding the storage key / the selectors as "the answer" — the key was derived by exercising the
  app, not by reading its source; no selector appears in the mechanism.
* Silently handling the `rawKeyDown`/`keypress` mismatch with a JS `.click()` shortcut — found by
  running; fixed with the trusted `text='\r'` keyDown. Trusted events only.
* Storing raw traces or the instance texts in the rule — admission requires fresh instances and a
  data-free sketch; enforced by test (`saved_rule` contains none of the four data strings).
* Reusing the expression-sketch module for GUI steps — it is AST-bound; forcing the shapes to fit
  would weld a fake abstraction over two different executors. Cross-referenced instead.

## 6. Next bottleneck (not started; named honestly)

The GUI mechanism binding works for ONE need family on ONE app. The wall that actually gates OSWorld
is **multi-step mechanisms with conditional structure** (if the page shows X, do Y; else Z) and
**recovery from a failed step** — today a failed step is an honest stop, not a repaired path. The
repo's action-grammar round (11/11 local needs, 44% strict page readability) and its refusal-is-a-
specification reader are the two ingredients; the missing part is binding the mechanism to the
page's OWN verification at each step (the app knows whether its todo was created — this run used
only the final check). In parallel, the transfer experiment comparing sketch vs trace-cache vs
shuffled/backwards persists as the discriminating test of the whole durable-unit thesis.

§6 status: NOT MET. No benchmark has been run or claimed.
