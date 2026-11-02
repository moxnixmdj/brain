# The optimal plan — V5, re-ranked by what measurement actually survived

> **SUPERSEDED IN PART by `OPTIMAL_PLAN_20261102_V6.md`.** Section 2's #1 item,
> PR-C' (replace `skeleton_fp` with a shape-invariant retrieval key), was measured
> **dead** after this file was committed: the taught rule cannot *match* another
> syntactic shape at all, because anti-unification keeps incidental context (the
> `return` keyword) inside the pattern. Transfer measured 2/5 with the taught
> pattern and 5/5 with a context-stripped one, so the blocker is pattern breadth,
> not retrieval. Do not implement PR-C'. Everything else here stands.

Supersedes the ranking in `OPTIMAL_PLAN_20261102_V4.md`, which is still on this branch.
V4 was written before three measurements that changed the order. This is the corrected plan.

Authority: NONE. No capability, ownership, benchmark, terminal or sentience credit follows
from this document. `truth.achieved` stays `false`. Spend $0. Model dependency 0.

---

## 0. The principle that produced this ranking

Four times this session a confident plan was wrong, and four times a measurement caught it:

| prediction | measurement | outcome |
|---|---|---|
| posture is decorative in the assembly | `step()` on a board with an uncheckable best-payer | **confirmed** → PR-B′ landed |
| generate-and-test is the cheap move on the 112 | read `Proposal.check`'s type | **refuted** — wrong target |
| blind search closed 9/9 novel cases | pre-registered positive control | **refuted** — probe was contaminated |
| a shape-invariant key over-retrieves | dumped the compiled token rules | **refuted** — collision is pre-existing |

Hit rate on predictions: poor. Hit rate on measurements: good.

So the plan is ordered by **cost of refutation**, not by expected payoff. Each step is a
measurement cheap enough that a negative result costs hours, and only a surviving
measurement earns the right to become a PR. This is the same discipline that made PR-B′
credible: the decisive test was written so it could fail, and it was verified to fail.

---

## 1. What is now measured, and will not be re-litigated

### 1.1 Authoring is absent, and deterministically unreachable

`VerifiedSkillStore.crystallize_code_fix` takes `after_snippet` as an **input**. Every caller
in the tree hands it in from outside the system:

- `multistep_repo_closed_loop_solver_v1.py` — `step_rec.get("after_snippet")`, an edit already made
- `retained_repair_session_v1.py` — `self.target.read_text()`, the fixed file read off disk
- the tests — `config['expert_after']`, named for what it is

**No organ computes an `after_snippet`.** That is the missing contestant, located as a
parameter rather than as an impression.

Two measurements close the deterministic route:

1. **The 112 obligations are the wrong target.** Each is
   `claim="{cid} has a registered inspector that refuses a decoy"`, with
   `check: Callable[[Mapping[str, Any]], bool]` — it scores a *world*, not source. A real
   inspector is a 43-line `(args, result, root)` function encoding capability-specific
   semantics (`transition_preimages`, `PYTHON_OPERATIONS`, live gate names). The fitness
   function for an inspector **is** an inspector. Circular: search cannot be graded here.

2. **Blind search closes 0/8 outside its vocabulary's reach.** With the mutation vocabulary
   frozen (sha256 `069d77da48271481`, imported verbatim, never extended): 2/2 true positive
   controls closed, all 7 measurement oracles valid (buggy fails its own spec, expert passes),
   **0 closed**. The cause is structural, not budget: the generator can **substitute but never
   introduce**. `s[:1]` → `s[:-1]` was unreachable because `-1` is not a token of the source,
   and the vocabulary produced only `s[:2]`, `s[:0]`, `not (s[:1])`.

Authoring therefore requires a token the broken source does not contain. That is a
**governance fork** (§4), not an engineering task.

### 1.2 Generalization has a located, mechanical cause

`skeleton_fp = sha256("|".join(skeleton_parts))[:16]` hashes the **surrounding token
sequence**. One lesson, `<= hi` → `< hi`, in three shapes:

| shape | `skeleton_fp` | holes |
|---|---|---|
| `return x <= hi` | `2d75d14e021e2696` | 2 |
| `if x <= hi:` | `062af2c04e5cdf36` | 2 |
| `while i <= hi:` | `6583a6e11b6d106e` | 2 |

Identical abstraction, three keys. A lesson learned in a `return` is invisible in a `while`.
Across five shapes the current key yields 4 distinct fingerprints and retrieves 1/5. That is
cross-shape transfer 0/36, explained rather than observed.

A shape-invariant key — hash the transformation, not the syntax — measured **5 shapes → 1 key**
(`5b19089f82bb6da5`).

### 1.3 The precision objection is dissolved, not waved away

The prototype flagged the new key **DANGEROUS**: `hi <= x` → `hi < x` (a *lower* bound)
collided with `x <= hi` → `x < hi` (an *upper* bound). Chasing it down:

```
L1  pattern: [('kw','return'),('ws',' '),('hole_id','?id0'),('ws',' '),('op','<='),('ws',' '),('hole_id','?id1')]
L4  pattern: [('kw','return'),('ws',' '),('hole_id','?id0'),('ws',' '),('op','<='),('ws',' '),('hole_id','?id1')]
```

Same `skeleton_fp`, same `pattern_tokens`, same `replacement_tokens`, **same `skill_id`**. The
two lessons already compile to the identical token rule in the shipped system. Hole
normalisation binds identifiers by first appearance, so operand role is **not representable**
at this level. The collision is pre-existing; a new key does not introduce it.

And it is not harmful, because precision was never the key's job. At
`verified_skill_crystallizer_v1.py:859` every candidate passes a gate before the rule is
applied and hit-counted:

```python
verification = evaluate(verifier, candidate, required_verification_kind, scope_id)
if verification is not None:
    ...
```

The architecture **retrieves broadly and verifies narrowly**. The verifier is the precision
mechanism; the key is only the recall mechanism.

### 1.4 Posture was decorative in the assembly — fixed

`Standing.posture()` was a genuine function of its counters, persisted per identity, covered by
16 passing tests — and the assembled creature never consulted it, because `step()` chose through
`M.choose_next(life, work)` (no standing argument) and `author_board` dropped `checkable` when
converting `Obligation` → `Work`. Composing both gates flipped the decisive measurement from
`causal=False` to `causal=True`. Landed as PR #6590; it does **not** move 0/112, because all 112
real obligations carry `checkable=True`, making the gate a no-op on the creature's own board.

---

## 2. The plan, ranked by cost of refutation

### PR-C′ — shape-invariant retrieval, gated on verification kind

**Step C0 (measurement, hours, kills the PR cheaply if negative).** On the existing harness
(`instant_learning_transfer_probe_20261101.py`, 13 cases, name-agnostic `boundary_oracle`),
measure shape-invariant recall against the 0/36 baseline with **zero** misapplications. Two
numbers, both pre-registered:

- recall: cross-shape pairs retrieved, baseline 0/36
- precision: candidates applied that the verifier then rejected as wrong

If recall does not move, or precision degrades, stop. Do not open the PR.

**Step C1 (the PR, only if C0 survives).** Replace the key with the transformation signature
and gate the broadening on `required_verification_kind`, which is already in scope at the call
site — no new plumbing:

- `TEST_SUITE` → shape-invariant recall (verifier strong enough to catch a misapplication)
- `CALLER_PREDICATE` / `SYNTAX` / `COMPILATION` → strict `skeleton_fp`, unchanged

That gate is the load-bearing part. The repo already states *"Boolean callbacks never establish
TEST_SUITE or whole-task correctness"*; broadening recall under a boolean verifier would be a
weakening flood dressed as a feature. The negative control is therefore:

> a `CALLER_PREDICATE` verifier must **not** receive broadened retrieval.

Invariants held: `allow_operator_generalization=False` untouched (different axis — that governs
generalizing beyond recorded scope, not retrieval width). No protected path. No authority.

### PR-A — owner-only cron

Demoted from first to last. Running unattended a thing that closes 0/112 accumulates honest
failure faster; it is hygiene, not frontier. It becomes worth doing once something closes.
It is yours regardless: CI-only → production is an owner action by design.

---

## 3. What is explicitly NOT the plan

- **Hand-authoring an inspector** to move 0/112 → 1/112. That is
  `OBJECTIVE_CANNOT_BE_REPLACED`, forbidden twice. An agent executing it would be substituting
  itself for the missing organ and reporting the substitution as progress.
- **Chasing the 112 with search.** Refuted twice over (§1.1): circular fitness, and
  substitution cannot introduce.
- **Re-running the 9/9 probe.** It was contaminated — the vocabulary contained the answer, and
  the nine "novel" cases were one bug class in nine surface forms. Its own positive control
  caught it. The corrected number is 0/8.
- **Weakening `allow_operator_generalization`.** A safety control. Never.

---

## 4. The fork only the owner can decide

Authoring is measured absent, and §1.1 shows no deterministic route to it. Two options, both
coherent:

**(a) Keep the demonstrator.** Accept that an `after_snippet` arrives from a human, a donor
trace, or history — which is what the tree does today, and which the guards enforce
deliberately. Then the honest claim is: *this system learns instantly and permanently from what
it is shown, and refuses to fabricate capability it was not shown.* That claim is **true**, and
it is worth more than an inflated one.

**(b) Admit a model-driven generator.** A model can introduce tokens the source lacks, which is
exactly what §1.1 measured as missing. The cost is `MODEL_DEPENDENCE_AUDIT = 0`, currently
audited clean, and it changes what "it learned this permanently" means — the capability would
live partly outside the tree. This is a spend, and it is yours to authorise, not mine to
assume.

PR-C′ is deliberately independent of this fork: it improves what the system does with lessons it
already has, under either answer.

---

## 5. Standing non-claims

Nothing here moves 0/112. Nothing here registers a capability, flips a family, or claims
sentience in any sense — phenomenal or operational. The operational creature (continuity across
an OS kill, self-authored obligations, a self-model that can be wrong, ranked ignorance) exists
on `main` and reports its own failure honestly; after PR-B′ its history also changes what it
chooses, not only what it reports. That is the whole of the claim.
