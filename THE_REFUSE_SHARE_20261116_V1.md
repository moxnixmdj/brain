# The Refuse Share: 71% of Real Commits Have No Mechanical Postcondition

**`THE_REFUSE_SHARE_20261116_V1`** · 2026-11-16 · branch `arena/c0f2af42-brain`

## The term I said was missing, now measured

Last session split real work three ways and admitted one part had never been measured:

| | share | status then |
|---|---|---|
| **MEMORISE** | 4.81% | measured |
| **SYNTHESISE** | the rest | measured |
| **REFUSE** | — | **"the least honest number in this tree"** |

It is measured now, and it is the number that decides whether a verification-gated agent can be
trusted at all.

## The question, stated so it can be checked

A human committed a change. If the project's **own tests**, at the state the author left them, do not
notice when that change is undone, then that change had **no mechanical postcondition** — the
repository could not tell whether it was present.

That is not a criticism of the commit. It is a fact about what the repository can certify — and it is
exactly the set of changes where the only correct output for a gated agent is a **refusal**.

## The naive experiment is wrong, and I ran it first to show why

```
git revert <sha>;  run the project's tests   ->   PASSES
```

It passes because many commits change the tests **as well as** the source. Reverting removes the very
tests that would have caught it. **On the measured corpus this naive method missed 2 of the 4 guarded
commits entirely.**

The honest experiment holds the tests **fixed at the post-commit state** and reverts only non-test
files:

```
revert only non-test files;  restore tests to post-commit state;  run tests
    any NEW failure  ->  GUARDED     the repository can certify this change
    no new failure   ->  UNGUARDED   nothing in the repository can tell
```

## The result

**14 real commits across 2 real repositories: 4 GUARDED, 10 UNGUARDED — REFUSE share 71.4%.**

| repo | commit | verdict | subject |
|---|---|---|---|
| click | 89d3bfda | **GUARDED** | Make it possible to define aliases for the secondary… |
| click | 36f83d91 | **GUARDED** | Password prompt now prints a newline on `^C` |
| packaging | a2b3e346 | **GUARDED** | Rename Py_NOGIL to Py_GIL_DISABLED |
| packaging | c1346dfd | **GUARDED** | Detect when a platform is 32-bit more accurately |
| click | 09583679 | UNGUARDED | Fix a bug in the docs |
| click | c6df8e64 | UNGUARDED | Add shortcut for PyPI upload |
| click | 7e8da559 | UNGUARDED | Version 5.0 |
| click | 421e46ac | UNGUARDED | Documented the use of get_current_context |
| packaging | 7bcd6d8e | UNGUARDED | Apply some refurb suggestions |
| packaging | 5e84eeb6 | UNGUARDED | Stop using deprecated/removed keys on RtD |
| packaging | d7ce40d8 | UNGUARDED | Fix code blocks in CHANGELOG.md |
| packaging | 3030822b | UNGUARDED | Include CHANGELOG.rst in sdist |

**The shape of the split is the finding, and it is clean.** What gets guarded is *behaviour*: a
rename that matters, a detection that is wrong by one bit, a prompt that breaks on interrupt. What
does not is *everything else*: documentation, release bumps, packaging metadata, style changes.

## The three-way split of 100% of real work, closed

| | share | what it needs |
|---|---|---|
| **MEMORISE** | **4.81%** | a lookup plus a postcondition check |
| **SYNTHESISE** | ~24% (of what is left after refuse) | compose a new edit, check it mechanically |
| **REFUSE** | **71.4%** | the honest answer: **no mechanical check exists** |

Read that table as an answer to your question. **Roughly seven in ten real changes cannot be verified
by the repository that contains them.** An agent that gates every action on a mechanical check —
which is this project's entire discipline — will therefore be *unable to certify* most of what it is
asked to do.

That is not a reason to abandon the gate. It is the reason the gate must be able to **refuse**, and
the reason a refusal is a real output rather than a failure.

## What this means for the claim

> *"Do it once, learn it permanently, and everything on a computer is solved."*

Three measured reasons it is not, and now they are all on the same axis — **not one of them is
learning speed**:

1. **4.81%** of real edits are served by permanent memory (1 in 21).
2. **0 of 14** multi-line edits are. Advanced engineering is the multi-line part.
3. **71.4%** of real changes have no mechanical postcondition, so there is nothing to learn *and*
   nothing to verify.

And composition fails independently: two individually-verified skills produce a no-op while every
local check passes.

## The bottleneck, final form

> **Not learning speed. Not storage. Not parameters.** The bottleneck is that **real work is mostly
> not repetition, and most of it cannot be mechanically checked.** An agent can only learn from what
> it can verify, and it can only verify about a quarter of the work.

The leverage is therefore not in making the agent learn faster. It is in **manufacturing
verification where none exists** — turning uncheckable work into checkable work. Every test ever
written is that act. A guarded plan is that act. The one-call premise sense is that act.

**That is the honest version of "solved instant learning": it is a fast path over the quarter of
work the system can check, and its real value is that it makes the checkable quarter nearly free.**

## The control, because an instrument failure is never a finding

Five repositories were attempted and **three were excluded rather than graded**:

- `pallets/itsdangerous` — produced no GUARDED verdict, so its harness was never proven; excluded.
- `pypa/pyproject-hooks`, `encode/httpcore`, `encode/httpx` — baseline did not run under this
  harness.
- `pallets/markupsafe` — editable install fails on its own `egg-info`.

**They are reported as instrument limits, not as unguarded commits.** The rule: a repository that
never produces a GUARDED verdict cannot produce evidence, and excluding it is the only honest move.

## Three bugs I found in my own instrument, and fixed

1. **The naive experiment** — reverting also removes the tests. Fixed by holding tests fixed; it
   would have missed **2 of 4** guarded commits.
2. **A blob-filtered clone of a historical commit** produced a `tests/` tree with no sources, so a
   broken harness looked like an unguarded commit. Fixed with full clones.
3. **Requiring a green baseline** discarded every repository with a pre-existing failure — click
   carries one, and it is a legitimate repository. Fixed by judging **relative** to baseline. This
   was an instrument rule masquerading as a finding, which is the exact failure this project has
   recorded twice before.

## Reproduce

```bash
python3 canonical/swe_kernel/the_refuse_share_v1.py 8 \
        canonical/verification/THE_REFUSE_SHARE_20261116_V1.json
/tmp/v4/bin/python -m pytest canonical/tests/test_the_refuse_share_v1.py -q   # 12 passed
```

## Instrument limits — stated plainly

- **14 commits from 2 repositories.** Small, and both are Python web/packaging libraries. This is
  not a census and not a distribution.
- **`pytest` only.** A project's own chosen runner may behave differently.
- **Test files are identified by path markers** — a declared rule, reported in the receipt so a
  reader can disagree with it.
- **A commit can be correct and still unguarded.** This measures what the repository can certify,
  not the quality of the change. "Fix a bug in the docs" being unguarded is not a defect in click.
- **Reverts that fail to apply cleanly are harness limits, not results.**
- **No capability credit, no benchmark rank, no independent verification.** Authority
  `NONE__PRODUCER_RUN`. $0, zero model calls.
- The corpus is public code; the test runs are the projects' own, unmodified, at their own state.
