# Ours vs. the frontier, capability by capability

**Date:** 2026-11-24. **Authority:** NONE (producer-run sandbox). Every number below is either
measured in this tree or cited from a live leaderboard checked today. Where we have no measurement,
the table says so — **"we never ran it" is a loss, not a tie.**

---

## §0 Method, and its limits

**What "all of our capabilities" could mean here, and what I actually did.** The remote has
**6,969 branches**. I could not read all of them, so I did three things and I am stating them
rather than implying completeness:

1. **Read this branch's own capability ledgers** — the repo maintains its own frontier comparison:
   `FRONTIER_CAPABILITY_SURFACE_NORMALIZED_V1.json` (dated 2026-09-28),
   `FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json`, and the per-capability records inside them.
2. **Read the branch's own claim-scoring document**, `SEVEN_CLAIMS_SCORED_AGAINST_MEASUREMENT_20261112_V1.md`,
   which scores the owner's thesis against measurement, including the claims that come out false.
3. **Verified the cited branches' tips** and the benchmark numbers by live search today.

**Limit, stated plainly:** 104 branches are opaque `arena/<sha>-brain` names; 6,865 are descriptive
labels ("breakthrough", "successor") that are **aspirational, not evidence**. I audited the
evidence-bearing subset. Any capability that exists only on an unaudited branch is not represented
here, and I am not going to invent it.

---

## §1 The frontier, verified today

| benchmark | leader | score | source |
|---|---|---|---|
| **SWE-bench Pro** | Claude Opus 5.5 | **89.9%** | Anthropic system card |
| **Terminal-Bench 4.1** (66 tasks) | Copilot Fusion (GitHub Copilot) | **71.2% ±2.9** | official board, 2026-11-19 |
| Terminal-Bench 4.1 | Opus 5.5 (Claude Code) | 65.8% ±3.1 | official board |
| Terminal-Bench 4.1 | GPT-6.2 Astra / GPT-6.2 Sol | 62.1% / 61.5% | official board |
| **OSWorld 2.1** (108 long-horizon, binary) | Claude Opus 5.5 | **48.7%** (81.8% partial) | official leaderboard |
| OSWorld 2.1 | Sonnet 5.5 / Fable 5.1 / Muse Wonder Full | 43.5 / 42.8 / 39.4 | official leaderboard |
| OSWorld (original, 369 tasks) | human expert baseline | ~72.4% | XLANG Lab |

The model names in the brief are **real**: GPT-6 Astra, GPT-6.1 Sol, GPT-6.2 Astra/Sol, Claude Opus 5.5,
Claude Sonnet 5.5, Copilot Fusion, Fable 5.2, Gemini 4 Carbon, Muse Wonder, Kimi K3.1 Pro. I could not
verify a system called "Muse Spark 1.1" — the leaderboard shows **Muse Wonder**, which may be the
same family under a different name. Treat that one name as unverified.

**What the frontier cannot do, measured:** long-horizon computer use. The best agent in the world
completes **48.7%** of OSWorld 2.1's 108 workflows, against a ~72.4% human baseline. At the 2.0
release the best was 20.6%. The gap is constraint tracking, mid-task change detection, and
verification — not GUI control.

---

## §2 Capability by capability

"Ours" is the measured number from this tree. "Frontier" is the verified leaderboard figure.
**Winner** is by outcome on the capability, not by effort or elegance.

| # | capability | ours (measured) | frontier (verified) | winner |
|---|---|---|---|---|
| 1 | **SWE-bench Pro** (real multi-file PRs) | **0/3** (V2 smoke, official images, own verifier, $0.00) | **89.9%** (Opus 5.5) | **Frontier, by ~90 points** |
| 2 | **SWE-bench Verified** | **5/128 = 3.9%** (one submission; control 0; pre-registered [4,10] held) | ~77–81% (Opus 5.5 / Sonnet 5.5 class) | **Frontier, ~20×** |
| 3 | **Terminal-Bench 4.1** | **never run** | **71.2%** (Copilot Fusion) | **Frontier** |
| 4 | **OSWorld 2.1** long-horizon computer use | **never run — no benchmark score, no GUI/browser success** | **48.7%** binary | **Frontier** |
| 5 | **GUI / browser perception** | **none** (no GUI success recorded) | 48.7% on 108 desktop workflows | **Frontier** |
| 6 | **Transfer from one experience to a new environment** | **1/40 = 2.5%** (3/40 with every generalisation on) | no single-experience mechanism; generalises from pretraining instead | **Frontier, on outcome** |
| 7 | **Rules shipped with, on unseen programs** | **0/40** | n/a — frontier does not ship rules | **Frontier** (we score zero) |
| 8 | **Exact recall of a repair once learned** | **22/22 = 100%** (same bug, from stored rule) | no equivalent organ — an LLM re-derives or is fine-tuned | **Ours** |
| 9 | **Bounded exact symbolic computation** | `OBSOLETE_VERIFIED`, exact_correctness = 1, verifier = Wolfram Language | no exactness guarantee | **Ours**, narrowly |
| 10 | **Marginal cost per solved task** | **$0.00** | $0.3k–$16.5k per Terminal-Bench run | **Ours** |
| 11 | **Determinism / reproducibility** | deterministic, re-runnable from a receipt | stochastic, ±2.3–3.2 pp | **Ours** |
| 12 | **Auditability of a capability claim** | 2,986 verification receipts; a queue that **revokes its own ownership claims** | vendor-published system cards | **Ours** |
| 13 | **Localisation of a repair site** | expert's file rank-1 only **40%**; 44% of tasks get no candidate at all | solved end-to-end at 89.9% | **Frontier** |
| 14 | **Precision once a target test passes** | **18/25** such tasks still do not resolve; 16 never reach the whole-module run | passes hidden tests at 89.9% | **Frontier** |
| 15 | **Knowledge-work output quality (GDPval)** | **no score found on this branch** (97 branches carry the name; none produced a number I can cite) | GDPval-AA v2.1 ≈ 1846 (Opus 5.5, vendor) | **Frontier** |

### Tally

- **Frontier wins 11 of 15** — and every one of the 11 is a *capability* row.
- **Ours wins 4 of 15** — and all four are *properties* (recall, exactness, cost, determinism,
  auditability), not task capability.

That asymmetry is the whole finding. We win on what we *are*; they win on what we can *do*.

---

## §3 The three numbers that decide it

**1. Candidate generation, not selection, is where SWE-bench dies.**
10 of 2,422 candidates resolve = **0.41%**. 44% of tasks never get a candidate. And perfect selection
is worth at most **+2 tasks of 128 (<2%)** — so the ranker was never the bottleneck. Our own loss
decomposition says the cheap half is **precision**: 18 of 25 tasks whose target test starts passing
still fail, 16 because they never reach the whole-module run. A breakage that a local re-run would
have shown was never taken.

**2. Instant learning is real; instant learning *in a new environment* is not, and merging those two
sentences is the most expensive error available.**

| what is asked | result |
|---|---|
| same bug again, from the stored rule | **22 / 22** |
| a *different* program, taught all the other fixes | **1 / 40** (2.5%) |
| same, every generalisation switched on | **3 / 40** |
| the rules the tree ships with, on any of the 40 | **0 / 40** |

18 of 40 fixes could not even be stored. One experience does not reliably become one lesson.

**3. The one thing we own outright is exact, and it is narrow.**
`EXACT_SYMBOLIC_COMPUTATION_V1` — bounded operation classes, `exact_correctness = 1`, verified
against Wolfram Language. That is a real, permanent, zero-cost asset. It is also the **only**
record at `VERIFIED_OWNED_EQUAL_OR_BETTER` in the entire obsolescence queue: 3 records are
`OWNERSHIP_REVOKED`, 3 are `OWNED_COMPONENT_NOT_FULL_FAMILY`, 1 is verification-pending.

---

## §4 Where the frontier is genuinely beatable, and it is not capability

Not by building a better generator — we measured that ceiling at +2 of 128. The asymmetry that
actually favours us is the **economics of verification**:

- The frontier pays **$0.3k–$16.5k and 1.1B–15.7B tokens** per Terminal-Bench 4.1 run, and still
  gets **65.8%**. We pay **$0.00** and get 0 on the same class of task.
- So the only defensible attack is not "score higher". It is: **make the verification and
  localisation loop free**, then spend the savings on search breadth. Our own measurements say the
  loss is localisation (40% rank-1) and precision (16 tasks lost to an untaken re-run) — both of
  which are *cheap to fix and do not require a model*.
- And the honest counter-argument, which the tree already records: negative transfer is worse than
  no memory at all (a production agent scoring **−100** on a task family a memoryless agent solves;
  ΔNL **−26.1** on the hard cases). A memory that makes an agent worse than none is a real failure
  mode here, not a hypothetical — 55% of self-authored rules regressed something that worked.

---

## §5 Verdict

**On capability, the frontier wins decisively, and it is not close.** 89.9% vs 0/3 on SWE-bench Pro;
71.2% vs never-run on Terminal-Bench; 48.7% vs never-run on OSWorld.

**We win on four properties that no frontier system offers**: perfect exact recall of a stored
repair, bounded exact symbolic computation, $0.00 marginal cost, and deterministic reproducibility
with 2,986 receipts — including a ledger that revokes its own ownership claims when the evidence
does not support them.

**Nothing here meets §6.** The gap is not architectural elegance or cost; it is that we generate a
candidate for 56% of tasks and resolve 0.41% of the candidates we generate, while the frontier
resolves 89.9% of the tasks outright.
