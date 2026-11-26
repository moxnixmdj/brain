# The gap closes the loop — 2026-11-24

Authority: `NONE__PRODUCER_RUN_SANDBOX`. This is a sandbox measurement and a design record, not a
benchmark score, not independent verification, not a capability claim, and not §6 completion. The
implementation described here can be re-run: `python3 canonical/tools/the_gap_closes_the_loop_v1.py`.

Branch: `arena/d86a0174-brain`. Base: `c4f529eb`.

## 0. Requirements confirmed (as read this session)

Read fully, treated as new. Bound requirements: own weights/architecture/agent; zero runtime model
calls; parameters only as computed mechanisms, never a memorized world-fact warehouse; instant
knowledge from the project's external JIT source; exhaustive project-then-web research; first-
principles limiting factors; ultimate minimal plan with rejected ideas and a design kill; build;
hardest honest tests; continuous loop to §6; one branch; never ask the owner questions; never claim
done without §6; honest separation of verified/unverified/failed; no leakage, no borrowed outputs,
no self-promotion, no protected-path edits.

§2 contradiction resolution (adopted earlier, re-verified against this build): parameters acting as a
lookup of memorized world facts, and any runtime dependency on another model, are forbidden. An
external, inspectable, editable store of knowledge and learned skills, plus learning that writes to
it from a single experience, is allowed. Test: the stored rule below contains `template` + `slot
kinds` — nothing about the world, only a computed mechanism; it can be deleted with one `rm` and
no retraining; the weights hold no facts at all (there is no trained network in this path). The
evidence block holds hashes and counts, never the instance data.

The owner's idea, restated as a claim, and how this record answers it:

> scan everything in the environment; retrieve from memory what is known and what is not; what is
> not known, get instantly from the web; act; verify; save the important learning — in a way that
> generalizes, because the environments are always changing.

## 1. What already existed in this project (exhaustively checked, including non-obvious names)

* `canonical/swe_kernel/perfect_algorithm_v1.py` — the loop: scan → right question → plan (BFS) →
  act → verify → generalize → **admit on fresh instances** → save priors/rules. Memory is an
  external, editable JSON store with atomic replace and corrupt-store refusal.
* `canonical/runtime/environment_learning_v1.py` — `learn_model`, `shortest_plan`, `state_key`
  (V2, type/structure-preserving), `probe_closeness` (restore in `finally`; restore failure raises).
* `canonical/runtime/jit_knowledge_v1.py` — web tier; refuses single-source conclusions
  (`DEFAULT_MIN_SOURCES=2`, `DEFAULT_MIN_KINDS=2`); count of sources is not evidence of agreement.
* `canonical/runtime/local_guide_v1.py` — offline tier (md files, man pages, `--help`); completeness-
  gated; returns ≤600-char paragraph snippets, not full text.
* `canonical/tools/the_guide_is_a_test_suite_v1.py` — documentation as a test suite: 189 examples
  extracted, 138 ran, 130 matched the guide's own printed output, 88 mutants separated 71, 0 real
  blinds; stored bytes 603. Also the four-gate wire `_plan_from_document` (EXTRACTED → REPLAYED →
  MATCHED → IN_VOCABULARY) already inside `run()`.
* `canonical/tools/the_guide_is_an_action_grammar_v1.py` — the page publishes a typed verb grammar;
  11/11 servable needs verified, 2/2 held-out needs refused.
* `canonical/tools/the_branch_is_the_model_v1.py` — exact-successor search; ordering priors buy
  nothing (1337 vs 1315 executions); only deleting edges pays and costs tasks.
* `canonical/runtime/observable_probe_v1.py`, `instant_condition_store_v1.py`, `applicability_v1.py`
  — contrast-bought applicability conditions in an external store; 48/48 transfers to a third repo.
* `canonical/runtime/brain_unified_model_v1.py`, `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`
  — a compiled projection of owned capabilities. Not a trained network; carries zero learned weights.

What was MISSING (found by reading, then by failing):

1. **The document path never executed.** `run()` fetched the guide, ran the four gates, and then
   returned `PASS__PLAN_FROM_A_DOCUMENT` with `pass: False` — the matched commands were never run,
   never verified, never generalized, never admitted, never saved. The owner's central circuit was
   open at the actuation point.
2. **The saved "generalization" was a raw action list.** `generalize()` stored `plan_sketch` = a
   bare list of command strings welded to the training data. That is a cache of one instance, not a
   skill; it cannot transfer, and our own 2026-11-16 round measured such caches serving 1/20 real
   edits.
3. **Local guides could not feed the wire at all.** `local_guide.lookup` returns snippets ≤600
   chars; `_plan_from_document` needs the transcript text.
4. **The "gap" was not an object.** Nothing computed or recorded what the scan could not explain;
   the fetch was fired by plan-failure but querying with a fixed template.
5. **A closing ` ``` ` leaked into the last example's expected output** — `_plan_from_document` fed
   the whole document as one block instead of through the `fenced_blocks` pipeline, so a real guide
   example failed its own oracle. Found by running it, fixed by running it.

## 2. Frontier research (web, 2026-11-24; inputs, not truth)

* OSWorld-Verified is saturated: top entry 90.19% (Intelligence-Indeed Agent, 2026-07-25), above the
  72.36% human baseline [1]. OSWorld 2.0 is not: best binary completion 44.33% (Claude Opus 5, max
  effort, board updated 2026-09-17) [1]; a separate October readout puts Opus 4.8 at 20.6% binary /
  54.8% partial [3]. ~318 tool calls per 2.0 task.
* SWE-bench Verified is contaminated and saturating (best ~79–97%); SWE-bench Pro (1,865 tasks, 41
  repos, private codebases) separates agents: 61.5% top on the standardized Scale SEAL board [3,4];
  the same model drops ~35 points Verified→Pro; scaffold swings exceed model swings by ~9–22 points
  [3,4,5,6].
* Persistent external skill libraries beat fixed-stack agents: an online skill-evolution framework
  converts rollouts into a versioned library that OSWorld gains come from, with counts (27 skills
  in GIMP; 82.4% of rollouts invoke get_skill) — and it is honest that gains are domain-dependent
  and warm-up offsets limit causal claims [7]. XSkill: training-free skills + experiences, zero-shot
  transfer, +11.13 on TIR-Bench [8]. PolySkill (ICLR 2026): polymorphic PARAMETERIZED skills beat
  raw-trace libraries; separating a skill's goal from its execution is "a crucial step" [9].
* AutoContext / instance-level context learning: a one-off exploration produces a durable
  instance-specific document De; TODO forest + plan-act-extract; ReAct 37%→95% on ALFWorld/Crafter/
  TextWorld — external validation of "learn the environment once, reuse everywhere in it" [10].
* ReadSecBench: README-embedded instructions are obeyed at high rates (up to 85%); mitigations are
  provenance-aware trust and counterfactual simulation, not trust [11].
* Agent-skills survey: skills are the procedural mediation layer between models and tools [12].

Every one of these systems — without exception found — runs a frontier LLM at decision time. That
is exactly what our constraints forbid, and exactly where this project's bet sits. We take the
mechanisms (external versioned skills; parameterization/polymorphism; instance-level context;
execution-gated admission), none of the runtime models.

[1] https://presenc.ai/research/osworld-computer-use-leaderboard-2026
[2] https://www.pointer.ai/blog/sota
[3] https://decodethefuture.org/en/ai-agent-benchmarks-2026/
[4] https://localaimaster.com/models/swe-bench-explained-ai-benchmarks
[5] https://codeant.ai/blogs/swe-bench-scores
[6] https://particula.tech/blog/swe-bench-pro-multi-file-coding-collapse
[7] https://arxiv.org/html/2609.04869v1
[8] https://lacuna.tiptreesystems.com/work/xskill-continual-learning-from-experience-and-skills-in-multimodal-agents/wrk_a7c45b8a0ed8f635eb1a897ea1bef3b8
[9] https://proceedings.iclr.cc/paper_files/paper/2026/file/e350897ed832f9cad6f2e223e7acad6d-Paper-Conference.pdf
[10] https://www.arxiv.org/pdf/2510.02369
[11] https://www.alphaxiv.org/abs/2603.11862
[12] https://www.researchgate.net/publication/404720630_A_Survey_of_Agent_Skills_Toward_Procedural_Infrastructure_for_LLM_Agents

## 3. Verdict on the core hypothesis (true / false / unproven / missing)

**True (measured this round and before):** an arbitrary environment's dynamics are learnable by
acting; plans are verifiable by observation; a single verified experience can be generalized to a
MECHANISM and admitted permanently on fresh instances (this round: 2/2 admit, recall in 1 binding).
The frontier independently confirms that external parameterized skill libraries work [7,9].

**False:** "learn everything in the environment". Nothing in the evidence supports scanning a world
into completeness — coverage is the bottleneck [repo: COVERAGE_IS_THE_BOTTLENECK_20261119_V1.md], and
every successful external system stores SELECTIVELY, admitted by evidence, not exhaustively.

**Unproven:** that the mechanism generalizes beyond expression-level mechanisms (GUI action
grammars, multi-step repairs, shell pipelines with mutating side effects); that admission transfer
scales beyond two fresh instances; that OSWorld-2.0-class long workflows are reachable this way.

**Missing:** an independent verifier; a harness that runs THIS agent on OSWorld 2.0 / SWE-bench Pro /
Terminal-Bench 4.0 (Docker/Podman/Harbor absent from this sandbox); any benchmark score. All §6
claims remain open. `truth.achieved` stays false.

**Why we cannot just show the model the most advanced coding actions once and have it learn them:**
(1) there is no weights-warehouse allowed here — showing is not storing; (2) a trace names one
instance, never the set of states a mechanism applies to, and 0/10 preconditions were identifiable
from traces in the repo's own contrast study; (3) without parameterization the saved object is a
cache, and caches serve ~1/20 real edits; (4) admission without fresh instances is exactly the
failure mode of every self-graded agent — the frontier's whole edge is invisible-to-the-model
evaluator feedback [7]. What stops us now: GUI-level mechanisms need an action grammar and a
discriminating check per environment; expression-level mechanisms (this round) are solved.

## 4. The owner's questions, answered with the evidence in hand

**Goal-directed or learn-everything?** Goal-directed, curiosity-bounded. The scan exists to make the
goal reachable, then stop. Learn-everything is not a plan; coverage math kills it; every external
system that "learns everything" does so by storing selective admitted skills [7–9]. The environment
is learned TO THE GOAL, not owned.

**What to save?** Never the raw experience. Three computed objects, each with its own admission
test: (a) PRIORS — observed transitions, re-executed on every fresh instance before trust
(`verify_priors`); (b) CONDITIONS — contrast-bought applicability facts (existing store); (c)
MECHANISMS — parameterized sketches admitted on fresh instances (this round). Data appears nowhere;
evidence is hashes and counts; one `rm` removes everything.

**How to generalize instead of saving dumb traces?** Anti-unification, as this project already used
for code repair: parse the example, make every data-dependent literal a hole (a whole constant
structure is ONE hole, so variable-length data transfers), rebind by execution on unseen instances,
the goal decides. A sketch that cannot bind is REFUSED, not forced.

**Scan-everything → diff memory against environment → fetch the gap?** Adopted, with one correction
measured this round: the fetch fires only when a planning gap EXISTS, and the query names the
SUBJECT, never the ignorance — appending gap nouns (`GOAL_STATE_NEVER_OBSERVED` etc.) to the query
retrieved NOTHING from a guide that shared every subject token (measured twice). The gap is a
first-class receipt (`steps.gap`) and the trigger; it is not retrieval payload.

**What not to save?** Raw actions, the training input, the guide's data, unadmitted sketches, and
anything from a single source without independent confirmation. The prose-only negative control
proves a guide with no transcript saves nothing.

## 5. The build (what exists now that did not)

* NEW `canonical/runtime/mechanism_sketch_v1.py` — four mechanisms, zero parameters fitted:
  `parameterize` (AST anti-unification; whole constant structure = one hole; ≤8 slots),
  `candidate_values` (leaves + whole flat scalar sequences from the OBSERVATION ONLY, capped 64),
  `render` (parse→substitute→unparse; no string splicing), `bind_plan_and_verify` (product search ≤96
  tries; the goal decides; exhaustion or limit reached = honest REFUSED).
* `canonical/swe_kernel/perfect_algorithm_v1.py`:
  - `_gap_report()` — the gap as countable nouns, computed from observation; receipt `steps.gap`.
  - `_document_text_from()` — reads the FULL text of the matched local documents (read-only, capped);
    the 600-char snippet path can never feed the four-gate wire.
  - `_plan_from_document()` — closes a real defect: fenced guides leaked ` ``` ` into the last
    example's expected output; now the `fenced_blocks` pipeline runs first.
  - `_execute_document_plan()` — the closed circuit: parameterize matched commands → bind by
    execution on THIS instance (goal observed) → generalize → admit on caller-supplied fresh
    instances → save the sketch only if ADMIT. Evidence is hashed (matched count/hash, executed-plan
    hash, binding KEYS not values).
  - Recall path serves `document_sketch` rules by REBINDING to the live observation and re-checking
    the goal — never by trusting the file. Stale sketches fall through to the full loop.
  - `_instant_knowledge_query` — subject-only query (the ignorance-paste failure is documented in
    its docstring).
* NEW `canonical/tools/the_gap_closes_the_loop_v1.py` — the demonstration; writes
  `canonical/verification/THE_GAP_CLOSES_THE_LOOP_20261124_V1.json` (13.7 KB).
* Tests: NEW `canonical/tests/test_mechanism_sketch_v1.py` (15),
  NEW `canonical/tests/test_document_sketch_loop_v1.py` (4, end-to-end incl. recall and controls).

Rejected for cause: literal execution of the matched example (would run the GUIDE's data, fail the
rehearsal trap; this repo already paid for that lesson) — replaced by bind-by-execution. Pasting
the gap into the retrieval query — measured retrieval failure, removed. A new learner — the
version-space/admission machinery exists; no second notion of "fires" or "breaks" was added. Web-
first instant knowledge — the local tier is free and version-matched; web stays behind its gate.
Executing the document plan without a binding step — wrong data, observed failure. Re-embedding
examples into the rule — warehouses data, transfers nothing. Changing AGENTS.md/guard/policy —
protected paths; not touched.

## 6. Hard honest tests and their real results

Environment: Python 3.11.2; `pytest` is NOT installed and `AGENTS.md` forbids pip/apt here — tests
ran under `python3 -m unittest`. Pre-existing modules importing pytest fail at COLLECTION in this
sandbox exactly as before (`test_the_guide_is_a_test_suite_v1.py`, `test_tool_census_v1.py` — verified
against HEAD, not caused by this work).

New tests, all green: mechanism_sketch 15/15; document_sketch_loop 4/4 (end-to-end learn → verify →
admit 2/2 → save → recall on a brand-new instance with zero scan; prose-only guide refused; no
fresh instances ⇒ not persisted).

Pre-existing suites still green under unittest: perfect_algorithm_v1 23/23;
perfect_algorithm_probe_restore_v1 8/8; local_guide_v1 13/13. The four-gate wire contract checks
were re-run by hand (module imports without pytest): all four behaviors hold.

Demonstration (`the_gap_closes_the_loop_v1.py`, exit 0, 6/6 claims true): instance A is an
environment the agent knows nothing about — data (7,2,9,4,11), deliberately DISJOINT from the
guide's printed example ([3,1,4,1,5]), so nothing is rehearsed. Scan observes nothing goal-relevant;
gap report is emitted; local guide retrieved from a real file; both guide examples replayed and
MATCHED EXACT; one mechanism step extracted (`statistics.median(S0)`); binding found in 1 try; goal
OBSERVED (7 == stdlib median); admitted on 2 unseen instances (2/2, 1 try each); MECHANISM saved
(`sketch-3ae1551b4f711c8b`); a THIRD, never-used instance recalled with no scan at all and passed
its goal check after re-verification; prose-only guide control: nothing executed, OPEN. Training
blob contains no training data, no admission data.

What this does NOT show (do not quote otherwise): no GUI/browser; no OSWorld 2.0; no SWE-bench Pro;
no Terminal-Bench 4.0; one machine; expression-level mechanisms only; admission proven on 2 fresh
instances of one family; the goal check here recomputes with the stdlib (held-out-test discipline);
the actuation-layer containment is program-root-level (demo environment), NOT a security boundary;
the single experience can still be a fluke of the family; nothing about sentience.

## 7. The single bottleneck now

The mechanism layer is solved for single-expression mechanisms. The next wall is the ACTION GRAMMAR
of GUI/browser worlds: an arbitrary application's mechanism is a typed verb grammar plus a check
per verb (the repo's action-grammar round proved 11/11 local needs, 44% page readable strictly), and
today NOTHING binds a mechanism from a live observation there. Next iteration: close that loop the
same way — observe the room, derive the verb/object join from the page's own grammar, verify with
the page's own check, admit on an unseen window. In parallel, the transfer experiment preregistered
in `OWN_MODEL_RESEARCH_AND_NEXT_EXPERIMENT_20261124_V1.md` (empty vs trace-cache vs
shuffled/backwards vs sketches, fixed distributions and seeds) is the discriminating test of whether
the sketch is the right durable unit, and it should be run before §6 is claimed.

§6 status: NOT MET. No benchmark has been run. This is real progress on one pillar — "one experience,
saved permanently, recalled instantly on an unseen instance" — not a completion certificate.
