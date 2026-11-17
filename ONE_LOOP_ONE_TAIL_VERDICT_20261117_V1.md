# One loop, one tail — the verdict on "instant learning solves everything"

**Receipt:** `canonical/verification/ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1.json`
**Tests:** `canonical/tests/test_one_loop_one_tail_verdict_v1.py` (every number below is re-read
from a merged receipt by that test; nothing here is re-measured, because re-testing a known
result is banned).
**Authority:** NONE. No model called, no external model used, no new execution in this pass —
the research half (project notes + four fresh web rounds, Nov 16–17 2026) and the answer half.

---

## 1. The claim, answered literally

> "Instant learning + instant learning in new arbitrary environments, solved perfectly ⇒ give
> the model the smartest actions, experience once, learn permanently ⇒ all computer use +
> advanced SWE solved. True or false?"

**FALSE as stated.** It is a chain of five links; this tree has now measured all five:

| # | Link | Measured | Verdict |
|---|------|----------|---------|
| 1 | act at all | 56/92 MiniWoB pages reachable with one hand | real, but a precondition — not the prize |
| 2 | one success → rule → permanent reuse | **60.0% vs 15.0% cache vs 18.9% prior** on unseen instances (4×); 52/92 never demonstrated once; 3 extra practices buy only +6.1 | **real, with sharp diminishing returns** |
| 3 | learn permanently | ungated: 228 real compositions, **53.5% stale, 31.1% silently corrupt**; gated: zero drift (106/106) | **conditional on the gate** |
| 4 | skills compose | the known no-op pair (`≤10→<10` then `<10→≤10`) passes every per-step check; only sequence/proved-premise composition refuses it | **false unconditionally; now refused before execution** |
| 5 | solves all computer use + advanced SWE | frontier **20.6%** on OSWorld 2.0; repeated syntax ~2.2% SWE-bench Verified | **false** |

**The true core inside the false claim:** verified, gated, effect-checked experience reuse is
real and large — 4× cache, zero-weight instant knowledge, ~7 ops per new environment,
composition 24/40 + 31/80 with zero damage. That core is also exactly what the Nov-2026
literature converges on (Learning by Doing +4.5…+18.8 training-free, ALFWorld +32.6 from a weak
base, Trace2Skill 0/8→6/8 with no weight updates — and, honestly, Learning by Doing's failed
tasks gain +0.6 ≈ 0, the field's own refutation of "once ⇒ everything").

## 2. The three barriers — the owner's frame is correct, and each is measured here

* **Identifiability** — one experience carries too little information: **0/200** one-shot
  successes identified; precision floor 0.069; the settled path needs **2.76 chosen queries**
  (a chosen query carries 1.9088 bits vs the demo's 1.0927 = 1.747×).
* **Vocabulary insufficiency** — the deciding fact sometimes cannot be stated at all:
  `INSUFFICIENCY_CERTIFICATE_20261113_V1.json` fires `unrepairable_by_repetition: true`;
  the oracle failed **4×1200** on value-nothing-stated pages; 8.4M candidate facts vs a cap of 12.
* **Synthesis–verification asymmetry** — what you synthesize cannot check itself:
  ungated replay 53.5% stale / 31.1% silent; the first-case instrument chose the wrong
  observation on 81% of cases (FIRST_CASE 4/21 vs ALL_CASES 16/16; +9 tasks), and externally
  an unanchored verifier collapses to always-pass *and trains skills just as well*
  (arXiv 2610.11464 — downstream score cannot certify a verifier).

## 3. The single bottleneck — the question has two axes, and the tree's four answers were right on each

**Loop axis (GOAL → GENERATE → ACT → VERIFY → INDEX).** Four merged notes each called one
station "the single bottleneck": goal sense (112/168→168/168), candidate generator (oracle
4×1200 fail; one arithmetic-reading fix 11→13/14, 1232→472 actions), the instrument
(4/21→16/16, +9), the index (5 families 0 usable; rename 7/10→0/10). These are not
contradictions — they are four stations of one judgment loop, each measured as a wall on
different task families.

**Deepest station: the observation–verdict pair (the instrument).** Because the three barriers
are all failures of that one station: without the separating observation there is no
information (identifiability); without a name the page contains there is no statement
(vocabulary); and nothing else can correct what generation, storage, or composition produced
(synthesis–verification) — external Nov-2026 work agrees: verification bandwidth is the
structural cap (2602.20946), evolving verifier skills are worth +6.4 (2610.00972), dense
verifier feedback is the lever (2604.01687, 2605.21810).

**Coverage axis (task classes): NO single lever — measured and test-pinned.** 46 unsolved
pages in **16 classes, largest class 6**; a test already fails any fabricated single-lever.
The remainder needs one part per class, in demand order, never one universal part.

**Reconciliation in one line:** *one loop (instrument deepest) + one long tail (no single
part).* "Single bottleneck" is a true statement about the loop and a false statement about
coverage — every honest answer in this tree was answering one of the two.

## 4. Can we do it NOW — smartest coding actions, experience once, permanent?

**No, for three measured reasons:** (a) the right action must be *derived* per state — the
pre-given aimed arm scores 0/46 vs derived 13/46 (actions are not a list you can hand over);
(b) one experience does not identify — 0/200, floor 0.069, needs 2.76 chosen; (c) permanence
without an anchored verifier corrupts — 53.5%/31.1% here, always-pass collapse externally.

**What is doable today, in ranked order (each with pass/kill):**

1. **Typed DERIVED candidate generator** — kill phrase gates; pass: oracle-unreachable pages
   become budget-reachable; kill: any working page changes its spend.
2. **Anchor every self-judged verdict** to data the judging loop cannot read; pass: always-pass
   collapse caught at admission; kill: anchor readable by the judge.
3. **One part per coverage class**, size order (6→5→4…); pass: that class solves without
   regressing others; kill: a solved class regresses.
4. **Re-key the inert prior** by instruction-bound liveness (transfer must beat shuffled).
5. **Weights last** — procedure + prior only, every bit calculated, zero knowledge in
   parameters (`ready_to_train=False`; precision 0.069 says identified-success data doesn't
   exist at scale yet). *The best part is no part:* facts live in the zero-weight
   content-addressed store, corroborated externally — knowledge access beats model size
   (8B+memory 30.5 F1 vs 235B bare 13.7 F1, 2603.23013) and parametric knowledge is
   un-auditable/un-deletable (2603.07670).

## 5. Revolutionary or just learning?

**Revolutionary in the loop, refuted in the one-shot form.** The one-shot form fails
everywhere — 0/200 here; one-shot skill generation loses repeatedly (2608.01678, 2606.01139);
Learning-by-Doing gains exist only where a teacher already solved. The loop form —
observation → anchored verdict → gated permanence → effect-checked composition, knowledge
outside weights — is what Nov-2026 is converging on, and this tree has it measured end to end
where the field has fragments. Sentience was never claimed: three measurable proxies only
(state continuity, self-verification, recovery), no more.

## 6. Research exhaustion record

Project (all read this pass, under the non-obvious names the owner remembered): THESIS_VERDICT,
WHAT_IS_REAL ×2, THERE_IS_NO_SINGLE_BOTTLENECK, THE_INSTRUMENT_NOT_THE_EXPERIENCE,
SEPARATION_IS_THE_BOTTLENECK, THE_GOAL/THE_HAND/THE_BOTTLENECK_IS_THE_INDEX,
WHY_LEARN_ONCE_REPLAY_FOREVER_FAILS, SKILLS_DONT_COMPOSE, plus the receipts they cite.
Web (fetched Nov 16–17 2026, 20 sources pinned with URLs in the receipt): VeriHarness,
Who-Verifies-the-Verifier, Measurability Gap, Learning by Doing, GitHub skills study,
Progressive Skill Generation, SkillRevise, EvoSkills, Trace2Skill, VASO, SkillComposer,
Skill-V, CompoSkill, SkillCommit, skill-selection scaling, agent-memory survey,
knowledge-beats-model-size, continual-learning-moves-to-memory, Hierarchical Memory Tree,
world-model action correction. Full URLs and one-line takeaways: receipt §external.
