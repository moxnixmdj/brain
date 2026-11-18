# Permanence fails loudly where it is learnable, and cannot be learned where it is not

*Round 6. 2026-11-16. Branch `arena/331bd3ac-brain`, base `78125a64`.*

## The question this round had to answer

Round 5 ended with the law and one number: **permanence = action × the check that validates it**, and the
bottleneck is the contrast. The tree had already stated the law more sharply, in
`permanence_amplifies_check_v1`:

> Permanence is a **multiplier** on the check, not an achievement. One demonstration leaves two rules; the
> simpler one is wrong; a weak check accepts 40/40 while 1 of 40 is correct.

What was never measured is the multiplier **on real code**. So round 6 asks the only question that decides
the claim in practice:

> Of the learned actions a real environment actually **moved**, what fraction does a check built from
> experience fail to see?

## The design, and why it cannot fool itself

- An **action** is `(module, callable, witness, shape)`: call it, record the observable. The witness is drawn
  from the environment's **own** vocabulary (string literals in the module that defines the callable) plus
  neutral tokens, and it is applied in both the scalar and the **element** shape — round 5 measured that a
  `str` is not a `list`.
- Witnesses are split by a fixed rule, **even positions learned, odd positions held out**. The check's
  blindness is a property of the module, never of a seed.
- **Nondeterminism control:** the old revision is executed **twice**. Anything that differs at the same
  revision is excluded and named, so randomness can never be reported as an environment change.
- **Kinds are never added together:** `REMOVED`, `NOW_RAISES`, `NO_LONGER_RAISES`, `VALUE_CHANGED`.
- **Per-witness risk:** for every moved action, what fraction of *single* learned witnesses would have seen
  it. That, not the four-witness row, is the risk of "learn it once" — because one experience is one witness.
- One real **minor** bump is reported apart, because 2026 measurements put **33.8% of patch and 64.4% of
  minor** releases at carrying a semantic break: exactly the regime where "permanent" is assumed safe.

Real libraries, real releases, all of them already pinned in the tree: packaging 21.0 → 24.0,
itsdangerous 2.0.0 → 2.1.2, tomli 1.0.0 → 2.0.2, plus packaging 24.0 → **24.1**. No model, no network at
measurement time, no parameter, no knowledge house.

## The measurement

**The tree's own pinned major bumps** — 76 learned actions over 22 real modules:

| class | count |
|---|---|
| stable (never moved) | 29 |
| **moved** | **13** (5 `REMOVED`, 6 `NOW_RAISES`, 2 `VALUE_CHANGED`) |
| caught by a learned witness | **13** |
| **blind** (moved, every learned witness identical) | **0** |
| never observable (never returned at old) | 30 |
| excluded: nondeterministic at the same revision | 4 |
| excluded: module does not import at old | 1 module |

`per-witness blind risk = 0.0`; **0 of 13** moves had even one blind single witness.
bl_k contrast curve: blind **0** at k = 1, 2, 3 and 4.

**The real minor bump** — packaging 24.0 → 24.1: 74 callables, **45 stable, 0 moved**, 25 never observable,
4 nondeterministic.

## Four corrections I had to make to my own instrument before any of those numbers meant anything

Each one moved the answer, and three of them moved it the wrong way:

1. **Modules were keyed by path.** packaging 21.0 keeps its package at `packaging/`, 24.0 at
   `src/packaging/`. Every module of the biggest bump reported `GONE_AT_NEW` — a **false zero** dressed as
   "nothing changed", which I would have published. Keying by module *name* fixed it: a module that moves is
   the same module.
2. **An arm that raised at the old revision was counted as a learned action.** 17 of 33 "moves" were
   `tomli._parser` arms going `AttributeError → TypeError` because the witness was the wrong type in *both*
   revisions. Nothing was learned, so nothing moved. An arm is learned only if it **returned** at old.
3. **A module that does not import at old was measured.** `packaging.markers` (21.0) does not import under
   this interpreter; every callable "moved", inflating *caught* with the interpreter's problem.
4. **Blindness was only reported at the full witness set.** Four witnesses showing 0 blind says nothing
   about "learn it once", which is one witness. Hence the per-witness risk and the k-curve.

## What is real, what is not, and why the honest answer is the opposite of the alarm

**Real.** The environment does invalidate learned actions: **31% of the observable actions** (13 of 42) moved
across the tree's pinned releases, and the kinds are concrete — five functions were **removed**
(`_parse_version_parts`, `_legacy_cmpkey`, `_require_version_compare`, `_platform_tags`, `_get_elf_header`),
six **now raise** where they used to return, and two **changed value**.

**Also real, and this is the finding.** Every single one of those moves was visible at **every** learned
witness. Permanence, on these libraries, fails **loudly**: the action raises, or the name disappears, and any
check that ever ran once sees it. The minor bump — the regime the literature flags as silently dangerous —
moved **nothing** at the behaviour level across 74 callables.

**So the danger is not where I expected it.** It is not "learned and silently wrong". It is upstream:
**30 of 76 actions (39%) could not be exercised at all** with witness arguments. They need real objects — a
parser state, a `Version`, a `Signer` — and with the environment's own scalar vocabulary they raise in both
revisions. Four more read the host (`sys_tags`, `cpython_tags`, `compatible_tags`, `generic_tags`) and are
nondeterministic across processes, so they are not learnable permanently *by construction*.

That is the vocabulary-insufficiency certificate of 2026-11-13, counted: **when the causal observable is
missing from the representation, no amount of repetition separates success from failure** — and when it is
missing, the action is not "learned but stale", it is **not learnable at all**.

## The answer to the standing claim

| claim | verdict |
|---|---|
| instant learning in a new environment is solved | **cost law** — 13 of 16 real requests at 29–36 probe trials each |
| one exposure identifies an action | **FALSE** — 0 survivors, 6.9% held-out accuracy, 93.1% dangerous errors |
| once learned, it stays learned | **FALSE** — 31% of observable actions invalidated by real major bumps |
| …and the failure is silent | **FALSE as measured here** — 0 of 13 blind, even at one witness; it fails loudly |
| …so all computer use and advanced coding are solved | **FALSE** — the ceiling is **binding**: 39% of actions cannot be exercised, 5% are host-dependent, and the specification supply is the same ceiling rounds 1–5 measured |

The chain the user proposed is therefore true in a narrower and more useful form than proposed:

> Give the model an action, let it act **once**, and keep the **check** — and it will keep working while the
> observable it checks keeps being observed; it will announce its own death when the environment breaks it;
> and it will never be learnable at all where the observable is missing.

That is worth having. It is not "solves everything on a computer". The 39% is the work.

## What the next round must attack

**Binding.** Not learning, not permanence, not the model: **the construction of arguments that make an action
executable at all.** Every round of this series has hit it from a different side — round 4 could not ground a
value, round 5 could not find a site that responded, round 6 cannot exercise 39% of real actions. A system
that can build the argument that makes a real callable run is doing something no witness scheme can do, and
it is the only thing standing between "13 of 42 actions checked" and "all of them".

*Reproduce:* `.venv/bin/python canonical/swe_kernel/renewable_action_v1.py --json
canonical/verification/RENEWABLE_ACTION_20261116_V1.json`
