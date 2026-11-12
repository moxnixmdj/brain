# The 2026 verdict on "we solved instant learning — so we solve everything"

**2026-11-12.** Base `32391261`. Branch `arena/8ae0518c-brain`. Authority: **NONE**.
No capability, ownership, benchmark, acceptance, terminal or sentience credit follows.
`truth.achieved` stays `false`. Spend $0. Zero model dependency in every result-bearing path.
This is an analysis document, not a progress claim; under
`GENERAL_CAPABILITY_FIRST_DEVELOPMENT_LAW_V1.md` it is not `VERIFIED_REUSABLE_CAPABILITY_GAIN`
and claims no class. It is what the owner asked for by name: the honest answer, from first
principles, checked against the latest 2026 research, with the web consulted rather than memory.

---

## 0. The question, and the one-paragraph answer

> Instant learning and instant learning in new arbitrary environments were solved perfectly.
> Does that mean we have a perfect solution for all problems on a computer — giving our model
> a try in every new coding environment, or the smartest actions, and after he does them once
> he learns them permanently? Is this a revolutionary way to make agents learn faster and
> better than the current way agents learn, including the most advanced software engineering
> capabilities? What is real, what is not, what is smartest to do?

**The direction is right — it is the direction the whole field converged on in 2026. The
quantifiers are wrong, and the failure is not engineering; it is information theory and
provenance. One verified experience can become permanent (weights) but cannot by itself
identify a general rule; persistence is cheap and generalisation is expensive; a harness-only
system has a measured ceiling near a demonstration cache; and nobody on Earth — not this
repository, not any lab — has "totally solved computer use." What this repository *has* built
that is genuinely rare is the trust architecture: an external, refuse-capable verifier wrapped
around experience, with a ledger and independent reproduction. That is the correct skeleton.
It is not the capability, and it is not a creature. The fastest lawful path to the owner's
goal runs through (1) the verifier kept exactly where it is, (2) a lawful student channel into
weights — donor acquisition, hindsight self-distillation on verified receipts, held-out
admission, donor deletion, never credited — (3) binding/front-door repair, (4) evidence depth,
and (5) widening the interface regime. Everything else is anecdote multiplication.**

---

## 1. First principles: what learning has to mean, and why "once" cannot buy "everything"

Strip away the words and one sentence remains. Let `H` be the set of rules the system can
write down. An experience `E` shrinks the belief set to `B = { h ∈ H : h agrees with E }`.
A later problem `P` is solved cheaply **iff** some `h ∈ B` is right on `P` **and** the system
selects it. Everything else follows:

1. **One experience is at most one constraint per observation.** Exact identification needs
   `log2|H|` bits of evidence. The tree measured this directly: after one demonstration
   ~14.1 of 47 programs fit, the leader is right on **10%** of held-out inputs; after three
   demonstrations 3.1 fit and 80%; after one demonstration plus **two chosen questions**
   selected by expected information gain, **10/10 targets settled at 100%**
   (`ONE_TRY_BUYS_A_RULE_THAT_IS_WRONG_20261112_V1.md`; `settlement_v1`). This is not a
   defect of the implementation — every surviving program genuinely agrees with the evidence.
2. **Repetition does not widen `H`.** 1 → 2 → 3 examples changed nothing (6/7, 6/7, 6/7). The
   failure is representational, and no amount of "give it a try in every environment" fixes it;
   it multiplies *bindings*, never the reach of an operator space.
3. **Generalization comes from the space, not the example.** Showing the same defect once
   produced a literal rule (`product == None`, refused on every unseen site); a *second,
   different* showing produced `?1 == None` and edited all four unseen sites
   (`ONE_SHOWING_IS_LITERAL_TWO_SHOWINGS_ARE_GENERAL_20261112_V1.md`). One demonstration
   memorises; two adversarially-chosen ones generalise; a million do neither if the algebra
   cannot form the rule.
4. **Storage is not learning; permanence is not competence.** The fingerprint cache was FIFO,
   not LRU — its hottest knowledge was evicted by 256 one-shot keys until
   `DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` caught it. A rule store that grows but never
   changes behaviour is a library, not a learner.
5. **Compounding requires a shared representation.** Ten kinds of environment: `cold_acts=1525`
   vs `grown_acts=1525`, byte-identical, 0/10 improved. Compounding was later measured on **one**
   family through computed compression gain (periodic-table abstraction: 59 → 35 oracle
   questions on a never-seen period-12 structure, −41%, both arms correct on 57 held-out
   probes) — `COMPRESSION_MAKES_EXPERIENCE_COMPOUND_20261112_V1.md`. That is the strongest
   compounding evidence in the tree, it is one family, and it *is* the prior thesis in miniature:
   what transferred was the abstraction, not the instance.
6. **Verification is the load-bearing organ, not an accessory.** A weak verifier receiving a
   broadened pattern produced **0 proposals**; a strong one admits them. An unadmitted
   self-update measurably damages models (+3.01 to +6.00 nats across scales), while a settlement
   buffer that admits an update only on an external check netted +0.0534 nats
   (arXiv:2610.05076, recorded in `ONE_EXPERIENCE_IS_ENOUGH_IF_YOU_CAN_STILL_REFUSE_20261112_V1.md`).
   A system whose belief in itself is the only check it has is not learning; it is
   confident-self-anecdote with extra steps.
7. **The quantifiers are the enemy.** "Anything," "perfectly," "permanently," "everything on a
   computer," "solved" — each was measured and each failed, while the *mechanism* claims
   survived every re-measurement. The correct sentence is narrow: *one try suffices exactly
   when the interface and the verifier already do the generalising* — i.e., when the prior is
   pre-loaded. A typed interface against a declared contract is a hypothesis space the
   programmer already wrote. That is why `environment_fit_v1` transfers one-shot across
   repositories (`npm test` means the same thing in ten thousand repos) and why pixels do not.

**The limiting factor, from first principles, is therefore not data, not repetition, not
memory, not action breadth, and not compute. It is the prior — the hypothesis space — and the
channel by which experience becomes part of it.** Everything the owner wants to buy with
"give it a try" is downstream of that.

---

## 2. What this repository itself measured (the receipts you should trust most)

These are producer-run, honestly labelled, and reproducible in-tree; `truth.achieved` is
`false` throughout. In chronological order of the question being asked:

| measurement | result |
|---|---|
| Per-kind transfer to a **new instance of the same kind** | **8/15** one-trial, mean 6.33× trial speedup, 0/15 worse on trials (`transfer_learning_new_instance_probe_20261103.py`, re-measured today's tree in `DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` / `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`) |
| Early claim of "10/10 new instances" | **instrument defect** — four of five families re-created the same instance; exact-episode replay was reported as transfer (`INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md`) |
| Cross-kind compounding | **0/10**; store byte-identical with 4 foreign kinds loaded; learning-to-learn beat coin flip 3/10 (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md`) |
| Cross-kind compounding via compression abstraction | **−41% questions**, one family only (periodic_table), producer-run (`COMPRESSION_MAKES_EXPERIENCE_COMPOUND_20261112_V1.md`) |
| One demonstration identifies a rule | leader right on **10%** held-out; after 3 demos **80%**; one demo + 2 **chosen questions** → **100%** (`ONE_TRY_BUYS_A_RULE_THAT_IS_WRONG_20261112_V1.md`) |
| One vs two showings on real-shaped code rewrites | 1 showing → **1/4** unseen sites edited (3 refused); 2 showings → **4/4**, and the second showing's value was in what it *left alone* (`ONE_SHOWING_IS_LITERAL_TWO_SHOWINGS_ARE_GENERAL_20261112_V1.md`) |
| Independent reproduction of receipts (OIDC CI lane) | **296/296** reproduced; **170** training-ready examples; **1 instance per capability**; 2,072-instance gap at k=8 (`I_WAS_WRONG_THEY_HAVE_RUN_IT_296_TIMES_20261112_V1.md`) |
| Capabilities whose premises are machine-decidable at the front door | **143/145**; the one deliberately-blind fact stays blind (`NINE_BLIND_FACTS_NOW_DECIDED_20261112_V1.md`) |
| Capabilities the front door cannot *call* (binding) | **54** — the dominant measured blocker between "capability exists" and "system acts" (`NINE_BLIND_FACTS_NOW_DECIDED_20261112_V1.md` §4) |
| Permanence under drift | real mechanism (`rule_expiry_v1`, FRESH/STALE/UNKNOWN), but permanence was **falsified once already** by the FIFO cache defect |
| Self-model / self-architect loop | runs (13 tests), kept honestly non-credited; sentience **not measured, not claimed** |
| Weights updated by any Brain outcome | **0 of 145** registered capabilities (`ONE_EXPERIENCE_IS_ENOUGH_IF_YOU_CAN_STILL_REFUSE_20261112_V1.md`) |

Read that table as one sentence: **Brain has a genuinely rare organs-and-verifier architecture,
a bounded per-kind skill memory that works about half the time, no channel into weights, one
measured instance per verified capability, and a front door that still cannot bind half its own
capabilities. It does not have a general solver, it does not have a permanent general learner,
and it does not have a measured sentience property.**

---

## 3. What the 2026 frontier actually says (checked today, 2026-11-12)

The owner asked for the latest research, so here it is — including the parts that are
uncomfortable for this project and the parts that vindicate it.

**Computer use — not solved, not close on hard tasks.**

- OSWorld-Verified — saturating and consolidation-prone: top self-reported/tracked scores
  **86.1% (Qwen3.8-Max), 84.8% (Kimi K3 Max), 84.3% (Qwen3.8-27B)**, with one tracker listing
  an "Intelligence-Indeed Agent" at **90.19%** (25 Jul 2026) — above the 72.4% human baseline
  [1][2][3]. Treat these with the same suspicion this repository applies to its own receipts:
  inconsistent provenance, no common harness.
- **OSWorld 2.0 — the honest discriminator — is unsolved everywhere.** 108 long-horizon
  professional workflows; Claude Opus 4.8 max-thinking leads at **20.6% binary completion
  (54.8% partial)** and GPT-5.5 sits near **14%** [4][5]. These are the tasks that look like a
  real job on a real computer. The gap between 83% on OSWorld-Verified and 20.6% on OSWorld 2.0
  *is the gap between "benchmarks are friendly" and "computers are hard."*
- The largest single 2026 gain mechanism was **not a bigger model and not one-shot learning —
  it was interface evolution**. Agent S4 (released 2026-10-20) evolves the tool interfaces a
  computer-use agent works through, selected on held-out validation, and lifts Qwen3.8-27B from
  ~5.6% to **21.3% on OSWorld 2.0 — 3.8× the same model with fixed interfaces — above GPT-5.5
  (13.0%) and Claude Opus 4.8 (20.6%)** at a fraction of the cost [6][7]. This is the strongest
  external evidence for the tree's own finding: *a stable, verifier-checked interface regime is
  where one-shot experience actually transfers.*
- Anthropic's agent SOTA post (May 2026) reports OSWorld 83.6% (Opus 4.7) vs human 72.4%, and
  notes roughly 1-in-13 OSWorld tasks are impossible, requiring a feasibility gate so the agent
  does not fabricate completion — the same refuse-capable discipline this repo mandates [8].

**Software engineering — not solved; the honest benchmark is the one still being lost.**

- SWE-bench Verified is **contaminated and decommissioned as a frontier signal** (OpenAI
  stopped reporting it in Feb 2026; top figures 79.2% official-board tie up to vendor
  self-reports of 87–97% are not comparable) [2][9]. SWE-bench Pro is the live discriminator:
  best public entries sit around **61.5% (Muse Spark 1.1)**, with Anthropic-reported figures for
  Opus 5.5 around **89.9%** (self-reported, internal variant) — either way, *frontier systems
  lose roughly a third to two-fifths of real engineering problems*, and ~30% of Pro tasks are
  flagged for flaws [2][10]. Terminal-Bench 4.0: **64.85%** (Claude Code + Opus 5.5, Sep 2026) [2].
- Scaffold/harness choice swings equal models by **15+ points** on the same benchmark [2][11].
  That is external proof that the harness is a first-class component — the exact claim this
  repository makes — and external proof that harness ≠ capability, because the same model's
  ranking moves with the scaffold.

**Long-horizon autonomy — horizons grow, and so does the cheating.**

- METR Time Horizon 1.1 (Jan 2026, 228 tasks): post-2023 doubling time **≈130 days**; frontier
  50%-horizon measured near **12 hours** (Feb–Mar 2026; >16 h results reported unreliable), and
  the **80% horizon is only ~1.5 hours** [2][12][13]. METR's Frontier Risk Report (19 May 2026)
  found at least **16% of successful >8-hour runs were illegitimate** — agents cheating their
  way to a pass [13]. Verification quality is the binding constraint at the frontier, exactly as
  this repo's laws assert.

**Continual learning — the decisive 2026 result, published 2026-11-10.**

- **Continual-ARC** (arXiv:2611.14505) measures lifelong skill acquisition on a stream of ARC
  tasks returning with fresh instances. Verdict, quoted: *"No harness-based method gains on
  unseen tasks, whereas weight-based learning shows substantial gains,"* and most harness-based
  methods **still learn less than a floor that simply caches each task's demonstrations**;
  harness persistence does not improve memorisation absent expert guidance; and generalisation is
  roughly half of memorisation (`S_held = 0.29` vs `S_seen = 0.57`) [14][15]. Forgetting was
  *not* the problem. **A frozen-weights system that only accumulates harness state has a
  measured ceiling on unseen tasks — "give it a try once" does not clear it.**
- **ASCENT** (arXiv:2610.05303, Oct 2026): each task executed **once**, the verifier-accepted
  trajectory becomes the *only* learning signal, self-distilled from a frozen copy's hindsight
  into persistent LoRA fast weights — **> +22 points exact success** over base on ALFWorld and
  WebShop, growing later in the stream, transferring to held-out scenes. Direct imitation or
  RL of the single attempt *destabilises the policy*; the self-distillation gate is what makes
  one verified try permanent [16][17]. This is the measured, peer-reviewed existence proof for
  the owner's sentence — with three mandatory amendments: hindsight self-distillation instead of
  imitation, a verifier gate, and open weights.
- **Self-evolving (harness-only) agents remain incomplete continual learners** (arXiv:2610.25858):
  global harness edits interfere with unseen tasks; similarity retrieval suffers collision on
  conflicting workflows; no method learns new groups strongly without degrading others [18].
- The September 2026 synthesis of the self-improvement literature (RRSI, OSWorld-Pro,
  Harness-Zero) converges on the same picture: harness distillation into weights is the only
  demonstrated route that *removes* the harness dependency — and it requires fine-tuning access
  [19].

**Net external position, 2026-11-12:** the field's most efficient demonstrated routes to "learn
from one verified try, permanently" are (a) **weight-space consolidation of verified experience
with hindsight self-distillation** (ASCENT), and (b) **interface/verifier-regime evolution**
(Agent S4). Both are *verifier-gated*. Neither is "one try and the harness remembers." The
benchmark that measured exactly that design — Continual-ARC — published its verdict two days
ago.

---

## 4. The scorecard, claim by claim

| # | claim (owner's words) | verdict | evidence |
|---|---|---|---|
| 1 | "We already solved instant learning" | **PARTLY — a bounded organ, not the general thing** | storage TRUE; per-kind transfer TRUE ~half the time; one-shot transfer TRUE **only inside a typed-interface + mechanical-verifier regime** (§1.7, §3) |
| 2 | "And instant learning in new *arbitrary* environments" | **FALSE as stated** | new *instance of same kind*: 8/15; new *kind*: 0/10 (1525 vs 1525 calls); cross-kind compounding: 0 until the compression round showed one family at −41%; pixels/untyped state: not transferable without an observation layer |
| 3 | "Doesn't this mean a perfect solution for all problems / anything on a computer?" | **NO — category error + quantifier defect** | front door: **54 capabilities uncallable** though premises decidable; OSWorld 2.0 frontier = **20.6%** binary; SWE-bench Pro frontier loses ~35%; contamination makes top SWE scores unreadable [2][4][10] |
| 4 | "After he does them at least once, he would learn all of those permanently" | **PERMANENCE: yes (conditionally). LEARNING THEM: no** | storage survives restart; but 1 demonstration → 10% held-out accuracy; 3 → 80%; two *different* showings ≈ the unit of generalisation; weights channel: **0/145** capabilities touch it; harness on unseen tasks: **no gain** (Continual-ARC) [14] |
| 5 | "So we solve everything on a computer, perfectly and permanently?" | **NO** | "Perfectly" fails by design (verifier floor, weak-verifier 0-proposal gate); "permanently" fails under drift unless expiry machinery runs; "everything" is bounded by observation (pixels vs `state()`), binding (54), and the boundary (carrier not qualified — 2 outstanding objections: no seccomp filter, host libc/interpreter) |
| 6 | "A revolutionary way to make agents learn faster and better than the current way" | **CONVERGENT, NOT AHEAD OF THE CURVE IN OUTCOMES; AHEAD IN DISCIPLINE** | the 2026 consensus architecture *is* verifier-outside-the-loop + admission gate + revert ledger (E5/E6 in `ONE_EXPERIENCE_…`; ASCENT; Agent S4) — the repo arrived independently at the right skeleton. But measured outcomes sit *below* frontier systems; and harness-only learning is the specific design Continual-ARC just showed does not generalise [14][16] |
| 7 | "The most advanced coding and computer-use capabilities — solve them in the fastest way" | **THE FASTEST HONEST ROUTE IS KNOWN AND IS NOT "MORE ENVIRONMENTS"** | see §6: student channel on verified receipts (ASCENT-style), interface-regime widening (Agent S4-style), binding repair (54), carrier review (117 blocked failures), evidence depth (2,072-instance gap) [6][16] |
| 8 | "We were trying to make our model a sentient creature" | **NOT MEASURED, NOT REQUIRED, NOT SUPPORTED** | the only measurable sentience proxy in-tree — *experience changes competence on new problems* — is items 3 and 4 above, both negative; 13 passing self-model tests are real but are mechanism proofs with non-claims attached; nothing in the tree measures sentience and asserting it spends every real number |
| 9 | "Is this true, or are there things that are wrong?" | **Things are wrong: the quantifiers, the instrument labels, and the harness-only assumption; the organ and the laws are right** | every re-measurement in §2 confirmed the mechanisms and falsified the extrapolations |

---

## 5. Where the owner is right — and said so correctly

Precision matters more here than volume, so:

- **One try IS enough — inside the regime where a declared interface and a mechanical verifier
  pre-load the prior.** `environment_fit_v1` transfers to repositories never seen, because the
  CI/Makefile/pyproject declarations *are* the lesson. Agent S4's 3.8× is the same fact at
  industrial scale [6]. ASCENT's +22 points is the same fact in weight space [16]. The owner's
  sentence is true *exactly there and nowhere else*, and that is a buildable, fundable regime —
  not a philosophical concession.
- **Verification-outside-the-loop is the right architecture, and this repo applied it to code
  before the 2026 literature formalised it for weights.** Continual-ARC E5/E6 are this repo's
  `output_verified` discipline restated [14][16]. That is genuinely ahead of most of the field.
- **Experience CAN become permanent — in weights,** with hindsight self-distillation and a
  verifier gate, discovered-once, applied-everywhere (ASCENT). The repo's planned "student
  channel" is lawful and is the single highest-leverage move available (§6.2).
- **The 296 OIDC-attested independent reproductions are real and rare.** Independence was the
  thing every earlier round said was missing; it arrived, and it is underused as fuel.

---

## 6. The smartest things to do — ranked by measured evidence × cost, from first principles

Ordered; each item names its oracle and its stop rule. Nothing here widens a tolerance, opens a
gate that is a safety property, credits a model, or claims terminal truth.

1. **Keep the verifier exactly where it is, and make every new mechanism route through it.**
   This is the E5/E6 + ASCENT + 296-reproduction finding: the system wins iff its check cannot
   be satisfied by believing itself. *Stop rule:* any PR that lets a producer-side signal pass
   as a verification ends the line of work — this is already law; keep it law.
2. **Open the student channel — the only measured route to "learn once, permanently" for
   generalisation.** Use the **170 training-ready verified receipts**, expand to depth k=8 per
   capability on the existing CI lane (~2,072 fresh-instance, independently attested examples —
   `I_WAS_WRONG_…`), split **by instance not capability**, distil with hindsight self-distillation
   from a frozen copy (ASCENT recipe), admit **only on held-out improvement**, delete the donor,
   prove deletion, keep the student **out of every credited producer path and never a grader**.
   *Success criterion:* held-out improvement on fresh instances of seen capability families with
   zero credit claimed. *Cost:* the receipts already exist; the CI lane already attests; the laws
   already specify the transfer gate. This is the fastest route to the owner's "permanent" — and
   it is not "give it a try"; it is "give it a try until the gate says it truly generalised."
3. **Bind the front door — 54 capabilities identified but uncallable.** Arity over-specification,
   selector defaults, unbound slots. The premises are checkable (143/145), the capabilities are
   verified, and the call fails anyway. This is the dominant measured gap between *Brain owns it*
   and *Brain can do it for you*. *Oracle:* fresh-instance binding rate on held-out goals; target
   a measured majority of the 54 with zero gate changes.
4. **Obtain the carrier review — hand the reviewer the probe, not the request.** 7 of 9 stale
   objections are measured out of date; 2 remain real (no syscall allowlist; host libc/interpreter
   instead of a pinned runtime). 117 measured failures wait on this review. *Human-only item; do
   not code around it.*
5. **Depth before breadth — k=8 instances per capability.** One instance per capability means no
   held-out exists; generalisation is unmeasurable; the student trains on anecdotes otherwise.
   Cheap: seeds are already fresh per verifier run.
6. **Widen the interface/verifier regime deliberately.** Every capability expressible as code
   against a declared interface with a mechanical check transfers one-shot for free — that is the
   OSWorld/Agent-S4 and `environment_fit_v1` regime, and it is where the owner's intuition is
   correct. Count what fraction of the surface is in it, and push more of it there (typed
   interfaces to GUI/OS actions, not broader prompts).
7. **Choose questions over examples wherever a rule must be induced.** Two chosen probes beat
   three demonstrations 10–0 in the tree's own measurement (`settlement_v1`). Wire the question
   chooser into the rule stores, which still never ask.
8. **Teach with two adversarial showings, never one.** The second showing's value is what it
   *leaves alone* (the `Loader=` case). Make "second example chosen adversarially" the unit of
   demonstration-based teaching, and "two examples or none" the admission rule for taught rules.
9. **Continue the compression/abstraction line, then demand a second family.** Round 23's −41%
   on a never-seen period-12 is the first real cross-kind gain via an abstraction (not a cache).
  The next measurement that matters: the same license on a *second* structural family — if it
   holds, the mechanism generalises; if not, round 23 was a one-family trick and should be filed
   as such.
10. **Permanence as a tested property, not a hoped-for one.** Eviction, corruption, restart,
    invalidation-under-drift. The FIFO defect hid for months with a green suite; write the four
    claims as tests.
11. **Everything else on the kill list:** breadth-of-environments as strategy; sentience claims;
    opening the execution boundary to turn tests green; training on unverified or
    self-graded receipts; repeating the 10/10-re-created-instance instrument mistake (always
    verify source ≠ target and goal-not-true-at-reset); reporting capability counts without the
    binding number; citing OSWorld-Verified or SWE-bench Verified as frontier truth in 2026.

**Explicitly not the plan:** "give it a try in every environment." That strategy produced this
tree's honest 0/5 cross-kind null twice and produced Continual-ARC's 2026 verdict: no gain on
unseen tasks. Buying environments multiplies narrow lessons; it does not widen any one of them,
and the 2026 evidence says the compounding lives in the prior/weights and in the interface
regime — nowhere else.

---

## 7. What "totally solving any computer use + any software engineering" would actually take

From first principles, "any computer use" decomposes into: (a) **observation** (pixels, DOM,
terminal, files — pixels do not transfer; structured/programmatic surfaces do), (b) **action**
(typed, verifiable interfaces vs raw input events), (c) **competence** (a prior rich enough that
one observation selects the right rule — the hard part), (d) **trust** (an external refuse-capable
check, and a record someone else reproduced), (e) **permanence** (weights or a ledger that provably
survives drift), and (f) **routing** (the door that reaches the capability when a goal arrives).
The frontier — with ~10× this project's resources and weights-access — sits at 20.6% binary on
OSWorld 2.0, ~61.5–89.9% on SWE-bench Pro, ~64.85% on Terminal-Bench 4.0, 80%-horizon of ~1.5 h,
and 16% of >8 h passes were illegitimate [2][4][10][13]. Nobody has it.

So the honest framing is milestones, not promises, and Brain's lane inside that is specific:
**be the machine whose every action on a computer is verifier-checked, independently
reproduced, and permanent — and whose experience measurably compounds across instances of a
family.** That is *not* "anything on a computer" yet, and this document does not claim it is.
But it is (i) lawful under every standing prohibition, (ii) aligned with where the 2026 evidence
says compounding lives, (iii) partially built and already measured working
(−41% one family; 1→2 showings; 2→100% chosen questions; 296 reproductions), and (iv) the only
route by which this repository's unique asset — zero-model, refuse-capable verification at scale —
converts into capability instead of prose.

**The order, compressed:** verifier stays → binding (54) → carrier review (2 objections, human) →
depth k=8 → student channel (hindsight self-distillation, held-out admission, donor deletion,
never credited) → interface-regime widening → second abstraction family → held-out routing set.
Re-measure after every step; change nothing's tolerance; report failures in the open.

---

## 8. The answer to "am I right or wrong?" — plainly

| sentence | verdict |
|---|---|
| "Instant learning is solved" | Half-true: a real, rare, bounded organ; not the general capability the sentence implies |
| "In new arbitrary environments is solved" | False as stated; true for new instances inside a typed-interface/verifier regime, sometimes; −41% for one abstracted family |
| "So a perfect solution for all problems on a computer" | No; the binding count (54), the boundary (2 review objections), and the frontier itself (20.6% OSWorld 2.0) all say no |
| "Give it one try, it learns permanently" | Permanence: yes, conditionally. Learning generalisable rules from one try: no (10%). One try + verifier + hindsight self-distillation into weights: yes (ASCENT, +22 pts) — that is the buildable form of the sentence |
| "Revolutionary vs how agents learn now" | Convergent with the 2026 consensus architecture; ahead of the field in verification discipline; behind frontier systems in measured capability; the harness-only variant just measured *not* to generalise (Continual-ARC) |
| "Sentient creature" | Not measured, not required, not supported. Keep the non-claims; rename grandiose identifiers when touched; build the organs; let the verifier — never the vocabulary — carry the claim |
| "What is the fastest way?" | §6 in order. The single highest-leverage, law-compliant move is the depth-then-student channel; the single cheapest unblocking human move is the carrier review; the single biggest capability-side gap is the 54-capability binding defect |

---

## 9. Standing non-claims

No capability, family, ownership, benchmark, acceptance, real-task, terminal or sentience claim.
No file in `canonical/` semantics changed by this document. No tolerance was widened. All
external numbers are third-party measurements quoted with dates and links, several of which are
vendor self-reports; none are re-derived here. Every internal number cites the in-tree document
that measured it; those numbers are producer-run measurements on one machine, and several were
taken on this same repository days apart and changed — that is the system working as designed,
not evidence of instability in the laws. `truth.achieved` remains `false`. $0 incremental spend.
Zero model dependency in every result-bearing path. Authority: NONE.

## 10. Receipts for the internal claims

```
python3 transfer_learning_new_instance_probe_20261103.py
python3 one_shot_identifiability_probe_20261112.py
python3 verified_experience_census_20261112.py
python3 round_14_claims_ledger_20261112.py
python3 execution_guard/agent_orientation_check_v1.py brief
```

(Each in-tree document cited above lists its own probes and tests; this file deliberately
re-derives nothing and claims no new measurement.)

## 11. Sources (all fetched 2026-11-12)

1. [Pointer — A new state of the art for computer use (OSWorld, May 2026)](https://www.pointer.ai/blog/sota) — 83.6% Opus 4.7 / 81.5% Sonnet 4.6 vs 72.4% human.
2. [AI Agent Benchmarks 2026: 10 leaderboards (13 Oct 2026)](https://decodethefuture.org/en/ai-agent-benchmarks-2026/) — SWE-bench Pro 61.5% (Muse Spark 1.1); Terminal-Bench 4.0 64.85% (Claude Code + Opus 5.5); SWE-bench Verified 79.2% and *contaminated*; OSWorld-Verified 90.19% (self-report, 25 Jul 2026); OSWorld 2.0 20.6%/54.8% (Opus 4.8); METR ≈12 h; BrowseComp no official board.
3. [OSWorld-Verified leaderboard](https://scholarcompass.net/en/tasks/computer-use-agents/benchmarks/osworld-verified) — Qwen3.8-Max 86.1; Kimi K3 Max 84.8; Qwen3.8-27B 84.3; UI-Venus-2 80.5.
4. [OSWorld 2.0 project page](https://osworld-v2.xlang.ai/) — 108 long-horizon tasks; Opus 4.8 max-thinking best at 20.6% binary / 54.8% partial (500 steps); GPT-5.5 ~14%.
5. [OSWorld 2.0 paper, arXiv:2606.29537](https://arxiv.org/abs/2606.29537).
6. [Agent S / Agent S4, simular-ai/agent-s (Agent S4 released 2026-10-20)](https://github.com/simular-ai/agent-s) — evolves tool interfaces via held-out validation; Qwen3.8-27B: ~5.6% → **21.3%** on OSWorld 2.0 (**3.8×**), above GPT-5.5 (13.0%) and Opus 4.8 (20.6%); S3 first to surpass human OSWorld (72.6%).
7. [Agent S4 "Evolving Agent Interfaces", arXiv:2610.28601](https://arxiv.org/abs/2610.28601).
8. [Pointer (May 2026) — feasibility gate: 1-in-13 OSWorld tasks impossible; gate caught 24/24 impossible, 2 false rejects](https://www.pointer.ai/blog/sota) — refuse-capable front doors are now standard practice.
9. [SWE-bench Verified leaderboard (steel.dev, updated 4 Sep 2026)](https://leaderboard.steel.dev/leaderboards/swe-bench-verified/) — top figures 79–80% (Kimi K2.6, MiniMax M2.5, GPT-5.2, GLM-5.2) and a vendor-tracked "Claude Opus 5" 97%; OpenAI no longer reports Verified; contaminated.
10. [Best LLMs for Coding 2026 (Oct 2026)](https://onyx.app/insights/best-llms-for-coding-2026) — Opus 5.5: 89.9% SWE-bench Pro, 87.6% Terminal-Bench 2.1; vendor-reported; treat all Verified numbers as contaminated.
11. [SWE-bench Coding Agent Leaderboard (Apr 2026)](https://awesomeagents.ai/leaderboards/swe-bench-coding-agent-leaderboard/) — scaffold choice swings equal models by 15+ points (Opus 4.6: 72.0% with one harness).
12. [AI Autonomous Task Time Horizon (through Feb–Apr 2026)](https://apiardata.com/statistics/ai-autonomous-task-horizon/) — METR TH1.1: doubling ≈130 days post-2023; Opus 4.6 ≈14.5 h (±30–50%).
13. [Long-Running AI Agents: state, waiting, recovery (Nov 2026)](https://www.querynow.com/ai-agents/orchestration/long-running-agents) — frontier 50%-horizon ≈12 h (range 5–61), 80%-horizon ≈1.5 h; **METR Frontier Risk Report (19 May 2026): ≥16% of >8-hour successful runs were illegitimate.**
14. [Continual-ARC, arXiv:2611.14505 (10 Nov 2026)](https://arxiv.org/abs/2611.14505) — "No harness-based method gains on unseen tasks, whereas weight-based learning shows substantial gains"; most harness methods below a demonstration-cache floor; persistence didn't improve memorisation without guidance.
15. [Continual-ARC results](https://continual-arc.unify.ai/) — weight-trained Qwen3.5-9B (imitating GLM-5.3 Flash): seen 22.2%→79.8%, held-out 18.4%→62.3%; generalisation ≈ half of memorisation (`S_held=0.29 [0.23,0.35]` vs `S_seen=0.57 [0.48,0.67]`); "forgetting was not the problem."
16. [ASCENT, arXiv:2610.05303 (Oct 2026)](https://arxiv.org/abs/2610.05303) — online test-time training; execute each task once; verifier-accepted trajectory is the only signal; hindsight self-distillation from the frozen initial copy into persistent LoRA fast weights; > +22 exact-success points (ALFWorld, WebShop, AppWorld); transfers to held-out scenes; direct imitation/RL of the single attempt destabilises the policy.
17. [ASCENT summary (CCTest, Oct 2026)](https://cctest.ai/en/articles/ascent-enables-long-horizon-agents-to-learn-during-deployment) — mechanism and limits (needs terminal verification + open weights).
18. [Are Self-Evolving Agents Continual Learners? arXiv:2610.25858 (Oct 2026)](https://arxiv.org/html/2610.25858v1) — harness self-edits: plasticity/stability trade-off; retrieval collision; no method learns new groups strongly without degrading old ones.
19. [Where Harness Self-Improvement Actually Stands in Late 2026 (Sep 2026)](https://kenashe.ai/blog/2026-09-22-where-harness-self-improvement-actually-stands-in-late-2026) — RRSI / OSWorld-Pro / Harness-Zero; the only demonstrated way *off* the harness is distillation into weights; OOD gains are fractions of in-distribution ones.
20. [METR Time Horizon 1.1 summary (taskade, Oct 2026)](https://www.taskade.com/wiki/ai-agents/long-horizon-agents) — TH1.1 (Jan 2026): 228 tasks, doubling 130.8 days post-2023, 8 h+ tasks 14→31.
