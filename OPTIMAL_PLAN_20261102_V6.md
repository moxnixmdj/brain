# The optimal plan — V6, after the retrieval-key thesis was measured dead

Supersedes `OPTIMAL_PLAN_20261102_V5.md`, whose #1 ranked item (PR-C′, a
shape-invariant retrieval key) this document refutes by measurement.

Authority: NONE. No capability, ownership, benchmark, terminal or sentience credit
follows. `truth.achieved` stays `false`. Spend $0. Model dependency 0.

---

## 0. Why V5 was wrong, in one line

V5 claimed cross-shape transfer 0/36 was caused by the **retrieval key**
(`skeleton_fp` hashing surrounding tokens). Measured false. The rule cannot even
**match** another shape, so no key change can help: recall would find a rule that
still fails to apply.

---

## 1. The measurement chain (C0 -> C0b -> C0c)

Every step carried an oracle-validity check, a positive control and a negative
control. Two faulty oracles were caught by those guards before producing a
number, and are recorded in section 3.

### C0 — does the taught rule's TEXT transfer?

`apply_crystallized_code_rule(shape1_rule, other_shape_buggy)` on the lesson
`<= hi` -> `< hi`, five shapes, each with its own name-agnostic semantic oracle:

| shape | result |
|---|---|
| `return` | matched, passes (positive control, self) |
| `if` | **None — no match** |
| `while` | **None — no match** |
| `and` | **None — no match** |
| `method` | matched, passes — but shares `skeleton_fp` `2d75d14e021e2696` **and** `skill_id` `skill_c931b33003f95b6d` with `return`, so it is the *same rule*, not a transfer |

**2/5, and really 1/5.** The cause is visible in the compiled pattern:

```
[('kw','return'),('ws',' '),('hole_id','?id0'),('ws',' '),('op','<='),('ws',' '),('hole_id','?id1')]
```

Anti-unification kept `return` — incidental context — as part of the pattern. The
rule is anchored to the syntactic position it was taught in.

### C0b — so is the blocker the KEY or the PATTERN?

Strip the context, keep only the transformation
(`?id0 <= ?id1` -> `?id0 < ?id1`), apply to the same five shapes:

| pattern | transfers |
|---|---|
| taught (context kept) | 2/5 |
| narrow (context stripped) | **5/5** — each passes its own independent oracle |

**PR-C′ is dead.** Retrieval was never the bottleneck. The lever is pattern
narrowing, a different change to a different function.

### C0c — precision, the number C0b did not measure

A bare `<=` pattern matches *every* `<=`, including correct ones. Nine cases:
five where `<=` is a bug, four where `<=` is correct and must survive. All nine
oracles validated first (buggy fails, correct passes).

- **bare match rate: 8/9** — it rewrites 3 of the 4 correct sources
- **sound verifier: 5 accepted correct, 0 accepted wrong, 4 rejected**
- **weak verifier (`CALLER_PREDICATE` failure mode, accepts anything that
  compiles): 5 accepted correct, 3 ACCEPTED WRONG** — `at_most`,
  `inclusive_loop`, `lower_bound` all silently corrupted

**Precision is a property of the verifier, not of the pattern.** This is the same
architecture seen at `verified_skill_crystallizer_v1.py:859` — retrieve broadly,
verify narrowly — and it is why the repo already states that boolean callbacks
never establish `TEST_SUITE` or whole-task correctness.

---

## 2. The plan

### PR-C2 — pattern narrowing, gated on verification kind

Admit context-stripped (broad) patterns **only** where the verifier is strong
enough to catch a misapplication:

- `TEST_SUITE` → broad pattern admitted (measured: 0 misapplications, 5/5 recall)
- `CALLER_PREDICATE` / `SYNTAX` / `COMPILATION` → context-anchored pattern only
  (measured: 3 misapplications if broadened)

`required_verification_kind` is already in scope at the apply site, so this needs
no new plumbing.

**Negative control, and the test that keeps this from being a weakening flood:**
a `CALLER_PREDICATE` verifier must NOT receive the broad pattern. If that test
can be deleted without anything failing, the gate is decoration.

Measured baseline to beat: recall 2/5 -> 5/5; misapplications 0 (sound) / 3 (weak).

`allow_operator_generalization=False` stays untouched — different axis. That guard
governs generalizing *beyond recorded scope*; this governs pattern breadth *within*
one recorded lesson.

**Gap CLOSED by end-to-end measurement (probes D and E).** C0b/C0c had measured
`apply_crystallized_code_rule` directly with a hand-built rule; the real path is
`crystallize_code_fix` -> store -> `recall_and_apply_verified`. Measured through
the real API with a name-agnostic oracle (C0's teaching failure was that harness
bug, section 3, not a system limit -- teaching now returns `crystallized=True`):

| path | bug cases recalled | misapplications |
|---|---|---|
| as taught, context-anchored | 2/5 | 0 |
| narrowed, sound verifier | **5/5** | **0** |
| narrowed, weak verifier | 5/5 | **3** |

The mechanism survives end-to-end, and the stored pattern really is
context-anchored: `[['kw','return'],['ws',' '],['hole_id','?id0'], ...]`.

**This changes where the change goes.** Probe D simulated narrowing at TEACH time
-- storing the narrow pattern. That variant is UNSAFE, and is the 3-misapplication
row above: a broad rule in the store is inherited by every caller, weak ones
included. PR-C2 must broaden at APPLY time and keep the stored pattern
context-anchored.

**The gate is enforced by `evaluate()`, not by convention** (probe E):

| caller | required_kind | result |
|---|---|---|
| weak (bool; accepts anything that compiles) | `CALLER_PREDICATE` | 4/9 recalled, **2 wrong** |
| the same weak callback | `TEST_SUITE` | **0/9 recalled** |
| sound (each case's own semantics) | `CALLER_PREDICATE` | 2/9 recalled, 0 wrong |

A bool return is auto-demoted to `CALLER_PREDICATE` and then rejected for kind
mismatch, so a weak caller cannot escalate into the gate that would admit broad
patterns. Measured 0/9, not assumed.

**Corroborating code fact:** `_load_rules` is
`SELECT pattern_json ... WHERE domain='swe_code_repair' AND language=? ORDER BY
verified_hits DESC LIMIT 128` -- it has **no `skeleton_fp` filter**. That is
code-level proof PR-C' was dead, independent of the behavioural measurement: the
key was never the retrieval gate.

**Pre-existing exposure on `main`, found by the same probe and NOT caused by
PR-C2:** with today's context-anchored rule and a weak caller verifier, recall
already misapplies 2/9. `def at_most(x, hi): return x <= hi` and
`def above(x, lo): return lo <= x` both match the pattern taught from
`return x <= hi`, and both are silently rewritten to `<`. That is the L1/L4
collision V5 reported, now measured as a real misapplication through the real
path. A sound verifier rejects both (0 wrong). Recorded because PR-C2 widens the
match surface, which is precisely why the gate must sit at apply time.

**The precondition is now measured, and banked.** The gate was cleared with real
evidence, not forged evidence: the tests build a project in a temp directory
(`bounds.py` plus a unittest suite asserting the upper bound is exclusive) and
verify candidates through the repo's own `ProjectTestOracle`, which copies the
tree, runs a real subprocess, and re-manifests the original to prove it was
untouched.

| measurement | result |
|---|---|
| buggy source vs the real suite | `passed=False`, `test_count=2`, `returncode=1`, candidate hash matches |
| fixed source | `passed=True`, `test_count=2`, `returncode=0` |
| `evaluate()` at `TEST_SUITE` | real oracle **admitted**; `lambda c: True` **refused** |
| compiling-but-wrong (`return True`) | `passed=False`, `returncode=1`, **refused** -- a gate that only rejected syntax errors would admit it |
| scoped teach, then scoped recall | `crystallized=True`; recall patches to the fixed source, `kind=TEST_SUITE` |

So the gate PR-C2 depends on is **real and satisfiable without forgery**. It is
now a repo test (`test_a_candidate_that_fails_the_suite_is_refused_v1.py`, 7
tests) that CI runs in `capability-transfer-governance.yml`. Before this, **no
workflow ran any crystallizer or contract test**, so the gate was unenforced --
a gate nothing executes is half-banked.

**What is still not measured, and cannot be until PR-C2 exists:** that apply-time
broadening lifts recall from 2/5 to 5/5 *while gated at `TEST_SUITE`*, and that a
weak verifier still receives the context-anchored pattern and never the broad one.
That is the PR's own success criterion, not a precondition for opening it.

### The authoring fork — the owner's decision, unchanged

Measured and unrefuted: no organ computes an `after_snippet`; blind deterministic
search closes 0/8 outside its vocabulary because it can **substitute but never
introduce**; and the 112 obligations each demand an *inspector*, whose fitness
function is an inspector (circular). Either keep the demonstrator — the honest
claim today, and worth more than an inflated one — or admit a model-driven
generator and spend the model-dependence invariant.

**That price was quoted wrong, and is corrected here.** `MODEL_DEPENDENCE_AUDIT`
is four cases and its scan scope is narrow:

| case | what it actually covers |
|---|---|
| `no_model_client_import_in_runtime` | **3 files only**: `brain_unified_model_v1.py`, `compile_brain_unified_model_v1.py`, `verify_brain_unified_model_v1.py` |
| `no_capability_route_names_a_model_provider` | the `route` text of capabilities and engines, against 10 vendor markers |
| `compiler_declares_zero_model_and_network_calls` | the compiler's own provenance: 0 model calls, 0 network calls, $0 |
| `model_vendor_name_occurrences_are_reported_not_hidden` | disclosure only; always passes |

The 17-rule integrity guard says nothing about models. And **8 files in this
repository already import `litellm`, `openai` or `httpx`** -- vendored agent
capability trees -- referenced by **0 capabilities**, i.e. inert. The invariant is
therefore *the artifact and its producer are model-free and cost $0*. It is not
*the repository contains no model*.

So admitting a generator does not automatically zero the audit. It spends it only
if the generator is wired as a capability whose route names a provider -- which is
precisely what case 2 exists to force into the open.

**The trap this creates, stated so that it is not walked into:** a generator placed
deliberately outside those three files, running at teach time, outside every
capability route, would leave all four cases green. That green would be a defect,
not a result -- the same category as an all-green suite produced by harness tricks.
The honest sequence is therefore to **widen the audit to cover the generator's home
before the generator exists**, so that admitting a model cannot be done quietly.
Widening is strengthening, and it must land first; otherwise the number meant to
price this decision cannot be trusted to price it.

PR-C2 is independent of this fork: it multiplies the value of every demonstration
under either answer.

### Cron — last

Running unattended a thing that closes 0/112 accumulates honest failure faster.

---

## 3. Faulty oracles caught this session, so they are not repeated

1. **9/9 blind-search probe — FALSE.** The vocabulary contained `("<=", "<")`,
   the literal answer, and the nine "novel" cases were one bug class in nine
   surface forms. Its own pre-registered positive control caught it. Corrected
   number: 0/8.
2. **C0 oracle — `bool(eval("lambda ns: ..."))`.** `eval` of a lambda expression
   yields a *function object*; `bool` of it is always `True`, so every buggy
   source looked correct. The validity guard aborted the run before any finding.
   Fix: call the lambda.
3. **C0 L2 teaching — `FAILED_MUTATED_TWIN_VERIFICATION`.** The oracle looked up
   `ns['a']`, but the mutated twin is alpha-renamed, so it raised `KeyError` and
   rejected for the wrong reason. Oracles here must be **name-agnostic**: take the
   first callable. This is why C0b/C0c use `first_callable`.
4. **The banked gate test was decoration -- caught by its own negative control.**
   Its first version passed all 7 tests with the kind-mismatch check in
   `evaluate()` deleted. Cause: passing a non-empty `scope_id` let the scope check
   (`if scope_id and result.scope_id != scope_id`) do the refusing, and a demoted
   bool carries `scope_id=''`, so the gate being pinned never decided anything.
   Fix: assert the **unscoped** call, where only the kind check can refuse; and on
   the recall path use `VerificationResult(True, 'CALLER_PREDICATE', sha, SCOPE,
   {})` -- right scope, wrong kind -- because an empty scope would instead make the
   contract-taught rule inapplicable and mask the gate a second way. Deleting the
   check now fails exactly 2 of 7. **Rule: run the negative control on a new test
   before claiming it pins anything, and check which check is doing the refusing.**

---

## 4. Standing non-claims

Nothing here moves 0/112. Nothing registers a capability, flips a family, or
claims sentience in any sense. The operational creature exists on `main`, survives
an OS kill, authors 112 obligations, closes 0, and reports that honestly; after
PR-B′ (#6590) its history also changes what it *chooses*, not only what it reports.
That is the whole of the claim.
