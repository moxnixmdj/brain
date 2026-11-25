> **RETRACTED IN PART — see `THE_LEAK_20261124_V14.md`.**
> This report's tool built its condition vocabulary from the FULL depth enumeration rather than from the
> walk, i.e. from states the learner never visited. The growth of the question supply and its sublinear
> shape survive; **the exponent (0.41) and every accuracy figure and mechanism below do not.** Under the
> correct vocabulary, accuracy after acquisition is flat in depth (0.920 / 0.906 / 0.932), not falling.
> Kept unedited below so the retraction has something to point at.

# QUESTIONS SCALE SUBLINEARLY — the first law in this work with a measurable exponent, and it is bad news
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. Where this came from

Last round measured that acquisition exhausts its **questions** — not its budget — at about 14 probes
per machine. That raised a falsifiable question: does the supply grow with exploration depth, or is
~14 a ceiling? A question is "(a support-1 law, a reachable state it admits that no probe has visited)",
and depth is what sets the number of unvisited states.

## 2. The measurement

Ten machines, depths 2, 3, 4, 400-probe budget per run:

| depth | states | questions | per 100 states | accuracy after acquisition |
|---|---|---|---|---|
| 2 | 77 | 51 | **66.2** | **0.678** |
| 3 | 231 | 72 | 31.2 | 0.618 |
| 4 | 767 | **131** | **17.1** | **0.596** |

```
questions ~ states ** 0.41     (exponents 0.314 then 0.499, mean 0.406)
```

**The supply grows — three orders of magnitude of headroom — but sublinearly, and accuracy after
acquisition FALLS with depth.** At depth 4, acquisition produces 404 predictions of which 274 are
wrong.

## 3. What the exponent means, precisely

An exponent below 1 says: as the state space grows, the number of questions the environment can answer
grows **more slowly than the space itself**. Concretely, per 100 enumerated states the askable-unknown
density falls 66 → 31 → 17. So each additional state costs *more* exploration to turn into a question
than the one before it.

That is the opposite of what the architecture thesis assumes. §9 says: scan, diff memory against what
must be known, fetch only the unknown — the picture is that unknowns are plentiful and the skill is
choosing which to fetch. The measurement says **unknowns that a question can actually resolve are
scarce and get scarcer** as the environment gets bigger. The scarce resource is not answers; it is
*tractable* questions.

And the accuracy column explains why: at depth 4 the walk covers a smaller *fraction* of a much larger
space, so acquisition's boundary-moving probes land in regions with almost no surrounding evidence.
Reach quadruples and precision collapses. Acquisition is not a bootstrap; it is a refinement that needs
a dense base to refine.

## 4. The practical rule this produces

```
explore until the question supply stops growing per unit of state
```

Because density falls monotonically with depth, the marginal question is never *cheaper* — so the loop
should stop when `questions_per_100_states` falls below the rate at which a question buys correct
predictions. That is a stopping rule about **exploration**, and it replaces both the fixed budgets
(16/30/40/200) and the accuracy gate that failed last round.

This is the first time in thirteen rounds that a limit on this project has been stated as a **scaling
law** rather than a wall. A wall says "this approach stops here". An exponent says "here is the exchange
rate", and exchange rates can be reasoned about: to double the questions available, the state space must
grow by 2^(1/0.41) ≈ **5.4×**.

## 5. Verified / unverified / failed

**Verified by execution:** the depth table; monotone growth of the supply (51 → 72 → 131); collapse of
density (66.2 → 31.2 → 17.1); declining accuracy after acquisition (0.678 → 0.618 → 0.596); the supply
never reached the 400-probe budget at any depth.

**Unverified:** the exponent is fitted on three points and a fourth, partial check at depth 5 on four
machines (15 questions over 94 states, consistent with continued sublinearity but not with the same
fitted curve). Two points define the trend; it needs depth 5–6 on all ten machines to be a law rather
than a trend, and I have not got that cheaply — depth 4 took 327 s and depth 5 on ten machines would
take substantially longer.

**Failed:** last round's accuracy-gated stopping rule remains failed and is not revived here.

**Audited (re-checked):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — 2 files each, both mine. None is a commit or module here.

**Blocked, logged once:** `docker: command not found`. No official benchmark row is producible from this
sandbox; this remains the only item outside my control.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 327.4 s (depths 2-4)
```

4 new tests; repo integrity guard PASS (17 rules, 0 violations). Committed on `arena/50c05c04-brain`.

## 7. Next

Fit the exponent properly: depths 5 and 6 on the four machines whose state spaces stay tractable
(VAULT, SQLITE, TARBALL, JOURNAL), and test whether `questions_per_100_states` predicts the accuracy
drop without needing to run acquisition. If density alone predicts precision, then a real environment
can be assessed — how much can be learned from it, and at what error — **before** spending any probes.
That would be the first predictive instrument in this body of work rather than a descriptive one.
