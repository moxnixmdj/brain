# The four branch claims, audited against their own receipts

**2026-11-24.** Supersedes nothing; adds. Pillar 0 of the incoming plan rests on four
numeric claims, none of which had been checked. All four are checked here against the
committed artefacts on their own branches, and two of the four are **improved facts
that the plan undersells**, which is the opposite of the usual failure and worth saying
plainly.

| claim | verdict |
|---|---|
| `aab1b545` — "45/45 = 100%", "51.11% transfer" | **FAILED** (fabricated; see `THE_TRANSFER_RECEIPT_IS_FABRICATED_...`) |
| `b81b2217` — "244 verified real OSS commits" | **UNVERIFIED** — no receipt with that number was located; not used |
| `06dc079e` — "15.4% blind real C in cJSON", "live Terminal-Bench 4.0" | **FAILED as stated / MIXED** — see below |
| `1412289d` — "11/13 = 84.6% blind multi-repo" | **FAILED as stated; the real receipt says 10/13 = 76.9%** and is the most honest artefact in the repository |

## `06dc079e`: the "live Terminal-Bench 4.0 Docker run" is a zero

The claim of a live Docker benchmark run was checked against GitHub, not just the
receipt. The runs are real:

```
gh run view 45621009866 --repo moxnixmdj/brain   →  ✓ pro-smoke in 6m38s
```

and the job annotation is unambiguous:

```json
{"tb4_rev":"452bf305…","rows":[
  {"task":"terminal-bench/session-window-debug","exception":null,
   "agent_status":"BLOCKED_NO_MODEL_PROPOSAL",
   "external_status":"EXPERIMENTAL_DISPATCH__UNVERIFIED","rewards":{"reward":0.0}},
  {"task":"terminal-bench/wal-recovery-ordering","exception":null,
   "agent_status":"BLOCKED_NO_MODEL_PROPOSAL",
   "external_status":"EXPERIMENTAL_DISPATCH__UNVERIFIED","rewards":{"reward":0.0}}]}
```

and for SWE-bench Pro:

```json
{"task":"instance_NodeBB__…","patch_bytes":0,"agent_status":"BLOCKED_NO_MODEL_PROPOSAL","rewards":{"reward":0.0}}
```

**`conclusion: success` is the CI job succeeding. The benchmark scored 0.0 on all four
tasks, `patch_bytes` is 0, and the status is `BLOCKED_NO_MODEL_PROPOSAL` — our system
produced no proposal at all.** The receipt's own note says the quiet part: *"Artifact
completeness only; no capability or benchmark success claim."* The plan's Step 3 and
Pillar 0 both cite these runs as a live baseline. It is not a baseline; it is an empty
harness.

Honest credit where due: **this artefact states its own limit**, and
`external_status=EXPERIMENTAL_DISPATCH__UNVERIFIED` is self-labelled. The failure is
in the plan reading it as a score, not in the receipt.

Also inside that receipt, and materially better than the plan's framing: a real
differential-witness corpus with real baselines —

```
witness_inversion_v1 standalone    0/30  (0%)
unmodified causal CEGIS baseline   0/12  (0%)
unified COGS differential witness  6/30  (20%)
```

and a boltons/more-itertools curriculum `0/4 → 4/4`. Those are the first non-trivial
blind numbers in this repository that are *not* on my 45-commit corpus.

## `06dc079e`: the cross-issue law transfer is a memory hit, not a memory cause

The receipt presents the exact §6 experiment: teach `ichunked_zero`, hold out
`chunked_even_zero`, and show the law being recalled first. It also ran the ablation
that decides whether the law mattered, and **the ablation says it did not**:

```
step1  teacher ichunked_zero         solved  crystallized uir_law_d14dfdade03f  5 sims
step2  held-out chunked_even + law   solved  SEMANTIC_LAW_RECALL               4 sims
step3  surgical remove law           removed, remaining_law_ids: []
step4  held-out chunked_even, NO law solved  COGS_REVERSE_PRECONDITION         5 sims
```

After deleting the law, the held-out task still solves, by the engine's own general
mechanism. **The law was a recall hit, not a cause.** That is the same null I measured
two other ways on my own corpus (ranker ceiling zero by construction; originator 0/26),
now confirmed by a third, differently-built system that ran the ablation properly.

## `1412289d`: the most honest receipt in the repository, and its numbers are lower

This one is worth reading in full. Its `honest_verdict` states:

> 10 of 13 graded unseen OSS commits repaired and verified against their own suites
> (76.92%), 0 regressions, 2 env-blocked, K3=0 runtime model calls. The new capability is
> real but narrow: it resolves commits whose fix is restated in the project's own test as
> `pytest.raises` contracts. Ten graded commits still fail, no public benchmark container
> score was produced here, and nothing in this receipt was obtained by gating, mocking, or
> reading a human diff.

The plan claims **11/13 = 84.6%**. The receipt says **10/13 = 76.9%**. The plan rounds up
by one commit and then quotes the rounded-up rate.

What makes this the best artefact here — and it is the reason to read it rather than
dismiss the branch — is that it fails its own gates in writing:

- **`law_library_v15`: `gate_result: "FAILED: 1 of 6"`** against a gate declared in
  advance (`>=3 of 6 commits must fire on the buggy tree and be silent on the fixed
  tree`). Per commit: `attrs 3b0378dd` buggy 0, `click 05f6fd0` buggy 0,
  `more-itertools cca32949` buggy 0, "no law fires on the exercised path".
- **`metamorphic_oracle_v13` coverage: `1/6`.** The five silent commits "have no
  lifecycle verb in their vocabulary (encoders, parsers, iterators)". This independently
  reproduces my Wall 1 result on a different implementation: metamorphic laws from a
  green suite do not discriminate.
- **`memory_ablation_v11`: `benchmark_effect: "none yet"`** — the delta candidate was
  dropped by a replay cap; store-vs-empty on `pluggy@50585e0` was
  `25 cand / 22.41 s` vs `25 cand / 23.21 s`.
- **`memory_ablation_v12`** replays delta-first and gets `REPAIRED 25 cand 24.08 s` with
  the store versus `REPAIRED 25 cand 22.41 s` without — **the store is marginally slower
  and changes no outcome**. And it names the real reason better than I did:

  > every graded commit ships the test that specifies the repair, so the store competes
  > with a specification that is already present; its comparative advantage (a defect met
  > again without a spec) is not represented in this catalogue.

- **`integrity_notes`**: `more-itertools@c629214` is flagged **CONTAMINATED** — its
  human diff was printed during diagnosis — and excluded from every tally.

That last paragraph is the best sentence written about this problem in the whole
repository, and it is exactly the conclusion I reached from three independent
measurements. Two separate builders, two separate engines, same finding.

## What this changes about Pillar 0

Pillar 0 says: merge seven proven mechanisms, and expect "244+ verified OSS commits +
100% 45-commit corpus + 84.6% blind suite in one binary."

Checked: the 100% is fabricated, the 84.6% is really 76.9% and is narrow
(`pytest.raises`-restated fixes), the live container baseline is 0.0, and the 244 is
unverified. The one genuinely load-bearing number in the plan, `6/30` differential
witness, is smaller than the plan implies but real.

**The reason the merge would not produce the promised gain is now measured four ways:**
`aab1b545` ablation → law deleted, task still solved; `1412289d` → store changes nothing
and is slower; `94363358` ranker → ceiling zero by construction; `94363358` originator →
0/26. Four independent engines, four nulls, one mechanism.

## The single next action this implies

Docker **is** available on a GitHub Actions runner — `06dc079e` proved the pipeline
dispatches and runs official `terminal-bench@452bf305` and `swebench-pro-v2` images under
`network_mode:none`. What it never had was an agent that could emit a proposal:
`BLOCKED_NO_MODEL_PROPOSAL`, `patch_bytes: 0`.

So the container route is **not blocked by infrastructure. It is blocked by the same
Wall 1 that blocks everything else**: on those tasks there is no failing test to hand
over, and every engine here hard-refuses without one. That is now the tightest
statement of the bottleneck in the repository, and it is testable on the 4 already-run
tasks at zero cost.
