# The revised plan: compete on proof, not on score

**Date:** 2026-11-24. **Authority:** NONE (producer-run sandbox).
This supersedes `THE_SMARTHEST_PLAN_20261124_V1.md`. That plan's spine was right — attack the
frontier's measured wall — but it misidentified the binding constraint, and I have since measured
why. Every number here is **verified** (measured in this tree or checked live today), **unverified**,
or **failed**.

---

## §0 What changed since the last plan — three corrections, all mine

| I said | what is actually true |
|---|---|
| "Fix transfer: 1/15 and 1.00× is the load-bearing failure" | **Wrong — already fixed.** Re-ran both instruments: **8/15 genuine saving, mean trial speedup 6.333×, 0/15 worse on trials.** I quoted a 3-week-old number without checking. |
| "Wire the decision layer to the computer-use layer, do it first" | **Blocked, and must not be done.** `confinement_v1` "is not an OS sandbox"; a sentinel was written outside the clone while `host_untouched=True`. *"Do not route around these blockers."* |
| "The binding constraint is transfer" | **It is reach.** 0 passes on the oracle-given repair corpus; **0/51 certified** on SWE-bench Pro V2. |

So the plan below is built on reach and on the one axis where we are genuinely ahead — not on transfer.

---

## §1 The harvest: what the non-obvious names actually contain

You said the capability is hidden under unfamiliar names and needs to be at the unified runtime. I
mined all **4,118 branch-only modules** for reach-oriented mechanisms. **366** match. The shared ones
are real, and one of them is remarkable.

### The find: an exact, proof-carrying LiveBench solver — on 17 branches, not on `main`

`canonical/runtime/livebench_legacy15_exact_pointwise_solver_v1.py` (branch
`breakthrough-unknown-domain-v2-impossibility-v3-20261005-sol`), with an 18-module toolkit and a
CI-verified receipt:

```
visible contracts
  -> bounded relaxed candidate search (<=31 non-empty subsets for k<=5)
  -> exact pinned LiveBench checker vector
  -> semantic next-cardinality UNSAT certificates
  -> pointwise score-optimality certificate
```

`LIVEBENCH_LEGACY15_CLEAN_PREDECESSOR_COMPOSITION_VERIFICATION_20261005_V1.json` — CI run
`verification-capsule-runner` PR 2070, `conclusion: success`:

| counter | value |
|---|---|
| eligible active15 rows | 193 |
| **solved satisfiable rows** | **192** |
| **proved visible-UNSAT rows** | **1** |
| compile / generation / checker failures | **0 / 0 / 0** |
| total candidates | 1,269 (max 28/row, 119 distinct constraint sets) |
| `hidden_terminal_data_used` | **false** |
| `active_terminal_prompt_rows_read` | **0** |

And the one failure is not a failure — it is a **proof**:

> *"Any response passing the frozen EndChecker must contain the exact terminal phrase, hence the whole
> word 'can'. The frozen ForbiddenWords checker rejects any response containing whole-word 'can'.
> Therefore the conjunction has no satisfying response."*
> `reason: EXACT_END_PHRASE_FORBIDDEN_WHOLE_WORD_COLLISION`

**That is the unusual idea, and it is already built.** The frontier fails ~18.6% of LiveBench IF and
cannot say why. This engine **proves** a task is unsatisfiable, and **certifies** its own score is
optimal. That is a different axis of competition from "score higher", and it is one the frontier does
not occupy.

### The rest of the harvest — real, shared, un-unified

| module | branches | what it is |
|---|---|---|
| `livebench_legacy15_exact_pointwise_solver_v1` | **17** | the exact solver above |
| `professional_quality_r2_candidate_branch_basis_v1` | 6 | candidate-branch basis |
| `cross_document_effect_behavioral_abstraction_v1` (+verify) | 4 | cross-document effect abstraction |
| `reached_escape_repair_potential_v1` | 3 | repair-potential estimation |
| `h100_complete_unary_chain_search_depth5/6`, `h100_complete_binary_root_search`, `h100_compiled_depth5_depth6_macro_search` | 3 each | **complete** (not heuristic) search to fixed depth |
| `oe_sygus_synthesizer_v1` | 2 | SyGuS synthesis |
| `causal_angelic_swe_engine_v1` | 2 | angelic SWE engine |

---

## §2 The honest verdict on the find — and it is not ahead

**Built, not proved on the board.** Three qualifiers, none of which I will drop:

1. **It ran on predecessor rows, not the live benchmark.** `predecessor_rows: 200`, frozen revision,
   and the receipt's own status ends `ZERO_ACCEPTANCE_CREDIT`.
2. **The target it aimed at was `LIVEBENCH_IF_GE_65_7` — 65.7%.** The frontier's LiveBench
   Instruction Following leader is **Gemini 3.8 Flash at 81.4%** (frozen final release 2026-06-25),
   then Gemini 3.7 Flash 79.9%, Muse Spark 1.3 78%, Claude Fable 5 75.8%, **GPT-6 Astra 75.6%**,
   Claude Opus 4.8 72%, Claude Sonnet 5.5 70.5%. So the target was set **~15.7 points below the
   frontier leader**, and it was hit on a rehearsal set.
3. **LiveBench 2.0 is now the live benchmark** (released 2026-10-14, seven suites, five agentic).
   Top: **Claude Fable 5.2 and GPT-6.2 Astra tied at 84.9%**, GPT-6 Astra 84.5%, Opus 5.5 83.4%.
   We have **no LiveBench 2.0 artifact at all** — the 1,046 LiveBench paths are all IF adapters,
   verifiers and carriers.

**So: not ahead.** But the *mechanism* — certified optimality and certified impossibility — is
genuinely ours and genuinely unusual.

---

## §3 The unusual idea, stated as a plan

**Stop competing on score. Compete on proof.** The frontier's defining weakness, named by its own
authors on OSWorld and by LiveBench's unsolved tail, is that it **fails without being able to say
why**. We have an engine that produces machine-checkable certificates of *optimality* and
*impossibility*. That is a capability class the frontier does not have, and it is worth more than
another point of score, because it is *composable*: a certificate can gate an action.

Three moves, in order of value per line of code:

**Move 1 — Promote the certificate machinery to the unified runtime.** Not the solver — the
*certificate* layer: `pointwise_certificate_v1`, `exact_postvalidator_v1`, the next-cardinality UNSAT
certificates. That is the reusable part, and it is what is missing from `main`. It is small, it is
already CI-verified, and it is a *library*, not a benchmark hack.

**Move 2 — Point certificates at reach, which is the measured binding constraint.** On the repair
corpus we get **0 passes**, and the oracle accepts **44.44%** of wrong fixes while the whole test file
catches **56.25%** of them. A certificate turns that from a guess into a decision: *this patch is
provably not a fix for this test vector* is a **refusal with a reason**, which is exactly what
`FAIL_CLOSED` needs in order to stop being a dead end. Today refusal and wrong patch both score 0.0;
a certificate makes the refusal *informative*.

**Move 3 — Run the certified solver on the live benchmark, with the certificate or not at all.** The
predecessor result is real but it is rehearsal. The honest next measurement is LiveBench 2.0 IF with
the certificate attached, reported as *solved / proved-UNSAT / unproved*, three numbers instead of
one. If the certificate layer is real, the unproved bucket should be small. That bucket size **is**
the capability claim.

**Why this is the smartest use of what exists:** it takes the one thing we have that the frontier
structurally cannot copy with more parameters — a proof — and applies it to the one place we are
measurably stuck (reach), without routing around the isolation blocker, and without claiming a score
we have not earned.

---

## §4 Fresh web research — what the frontier is doing about the same problems

- **LiveBench Instruction Following is near-saturated and frozen** (final release 2026-06-25):
  Gemini 3.8 Flash **81.4%**, Muse Spark 1.3 78%, GPT-6 Astra 75.6%, Opus 4.8 72%. The live
  benchmark is **LiveBench 2.0** — Fable 5.2 / GPT-6.2 Astra **84.9%**. Related and also near-saturated:
  IFBench (Grok 4.3 **83.3%**), MultiChallenge (Gemini 4 Carbon **85.9%**).
- **Instruction following is not where the frontier is weak.** It is near-saturated. Our exact solver
  is impressive *and* aimed at a target (65.7) below a saturated board. That is a reason to move the
  certificate machinery, not to chase this board.
- **Where the frontier *is* weak, per its own authors:** OSWorld long-horizon — *"lose track of
  constraints, miss mid-task information, guess rather than ask, skip verification"*, completion
  **zero above 163 minutes**. And on LiveBench 2.0, five of seven suites are **agentic** (long agentic
  work, coding, browser use, research, design) — i.e. the frontier has moved the benchmark *onto* its
  own weak ground. That is where a certificate-bearing agent would be unusual.
- **Training-free external skill memory is now validated** (Memento-Skills 2603.18743: GAIA 66.0 vs
  52.3, HLE +116.2% relative, no retraining; MSCE 2607.16621: L1/L2/L3 with applicability boundaries
  and verification rules). Our transfer fix (8/15, 6.333×) is consistent with that literature, and our
  `settled_admission_v1` / `rule_expiry_v1` / `skill_recheck_v1` are the gates those papers prescribe.

---

## §5 Rejected

| idea | verdict | reason |
|---|---|---|
| Chase LiveBench IF with the exact solver | **rejected** | near-saturated, frozen, and our target was 65.7 vs the frontier's 81.4. Move the *certificate layer*, not the solver. |
| Wire decision ↔ computer-use now | **rejected** | isolation substrate leaks; "do not route around these blockers". |
| Fix transfer | **rejected — already done** | 8/15, 6.333×, 0/15 worse-on-trials. |
| Compete on SWE-bench Pro generation | **rejected** | 89.9% vs certified 0/51. |
| Unify 7 branches into one binary | **rejected** | only 1 branch-only module is on ≥50 branches; the 4,118 are single-branch experiments. Harvest mechanisms. |
| Bigger mutation grammar / 16-way CoW now | **rejected** | 75.2% unreachable; 16 × 0% = 0%. |
| Vision model for GUI perception | **rejected for now** | the frontier's own diagnosis says perception is not the bottleneck. |

---

## §6 What would make this plan wrong

1. **If the certificate layer cannot be lifted without the solver** — i.e. if it is a benchmark hack
   wearing a library's clothes. Test: import it into `main` and use it on the repair corpus. If it
   only works on LiveBench IF rows, it is not a capability, it is a fixture.
2. **If certificates do not change the reach number** — if provable non-fixes do not convert any
   refusal into a useful decision, Move 2 is falsified and the plan collapses to "we have a nice
   certificate library".
3. **If LiveBench 2.0 stays unrun** — then the strongest exact result remains a rehearsal, and the
   honest claim is "192/193 on frozen predecessor rows with proofs", nothing more.

**§6 is not met.** The frontier leads on every board that pays: SWE-bench Pro 89.9%, Terminal-Bench
4.1 71.2%, OSWorld 2.1 48.7%, LiveBench 2.0 84.9%. This plan does not claim otherwise. It claims one
narrow, real, unusual thing: **we can prove what the frontier can only attempt**, and that is worth
more than another point — if it survives contact with the reach problem.
