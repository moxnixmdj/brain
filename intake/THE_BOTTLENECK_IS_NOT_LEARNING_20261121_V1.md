# The bottleneck is not learning. It is four refusals, three of which can be removed.

Schema `BRAIN_EVERY_CALL_SITE_V1` · tool `canonical/swe_kernel/every_call_site_v1.py` ·
tests `canonical/tests/test_every_call_site_v1.py` (8 passed)
Receipts `intake/RECEIPT_EVERY_CALL_SITE_20261121_V1.json`,
`intake/RECEIPT_EVERY_CALL_SITE_THREE_REPOS_20261121_V1.json`,
`intake/RECEIPT_CHECKABILITY_REMEASURE_20261121_V1.json`

## §2 contradiction — resolved before any code

The constraint "zero knowledge house" and the requirement "instant learning permanently"
appear to conflict. Resolved as instructed, then tested:

- **Forbidden:** parameters acting as a lookup of memorised world facts; any runtime model.
- **Allowed:** an external, inspectable store the system computes with, written from a
  single experience.

**The test is whether the store can be edited without retraining.** Every store this work
touches is JSON on disk, keyed by `(content digest, invoked name)` for the host instruments
and by call-site vectors for the coding instruments. Nothing is in weights. Nothing is
retrained. The boundary holds as stated, and the evidence below does not move it.

## Project research: what already existed, and it was not nothing

Searched exhaustively before building. Six instruments already existed and each had already
measured a piece of the hypothesis:

| instrument | what it had already found |
|---|---|
| `one_shot_identifiability_probe_20261112` | after ONE demonstration, **14.1 of 47** hypotheses survive; leader right on **10%** of held-out inputs; **0/10** identified |
| `one_experience_is_a_point_..._20261112` | `one_demonstration_settles_nothing: true`, `repetition_still_never_identifies: true` |
| `instant_learning_transfer_probe_20261101` | one taught lesson: **2/9** solved, controls **1/2**, novel shapes **1/7**, cross-language **0/4** |
| `real_commit_repair_v1` | vocabulary learned from other repos' real diffs: **0 solved in 90 executions** on 7 real fix commits |
| `checkability_by_differential_pin_v1` | re-measured this session: **0 of 6** unguarded real commits convertible to a check |
| `argument_construction_v1` | **1 of 41** unexercised actions made runnable; refusals `EVERY_CALL_SITE_IS_UNENCODABLE 34` |

## §3 verdict, stated plainly

**False:** "we solved instant learning." One demonstration does not identify. In a 47-program
space it leaves 14.1 candidates and picks the right one 10% of the time. Repetition does not
fix it either — `repetition_still_never_identifies: true`.

**False:** "the agent only needs to do something once and it learns it permanently." A lesson
learned from a diff **transfers its syntax together with the words of the place it was
learned in** — one candidate for `tomli/_parser.py` contained `packaging`'s own
`pathlib.PureWindowsPath(path).drive`. Measured: 0 solved in 90 executions. Experience does
not accumulate this way, and that is now measured three separate times.

**True:** the host instruments from the previous rounds. Types read from a program's own
sentence transfer across hosts (225/635 typed; four exact round trips on busybox-only in
0.118 s; second visit 0 probes). That result is real and it is about *what a program states*,
not about experience.

**Unproven and not claimed:** any coding capability at frontier level. The frontier's numbers
are a scaling artifact of memorised code — the field's own November 2026 measurement says the
best single prompt on the newest model beats 37–63% of a year's engineered tools. We are
forbidden that artifact. Matching those numbers by another route is not demonstrated here.

**The real limiting factor, and it is not the one the hypothesis names.** Two independent
measurements agree:

1. **CHECKABILITY.** Re-measured this session on 14 real commits: 8 shipped their own tests,
   6 shipped none, and **0 of the 6 unguarded ones** could be converted into a differential
   check. The disambiguating input is itself knowledge, and nothing manufactures it.
2. **EXECUTABILITY.** Of 1,039 call sites of tree-defined functions in one real repository,
   only **32.6%** can be turned into an executable argument vector at all.

Executability is *prior* to checkability: a check needs a call that runs.

## The build: every call site, and the four refusals named

`every_call_site_v1` re-measures the executability term the previous round refused by name.
Measured over the same tree, then across three repositories:

| repository | call sites | usable | dominant refusal |
|---|---|---|---|
| pypa/packaging 24.0 | 127 | **17.3%** | bare `Name` |
| pallets/itsdangerous 2.1.2 | 24 | **25.0%** | bare `Name` |
| hukkin/tomli 2.0.2 | 112 | **6.2%** | bare `Name` |

Four refusals, and each is a different phenomenon:

1. **Keyword arguments dropped wholesale — 26.9%.** 205 of 302 keyword values are plain
   constants (`python='3.9'`). Discarding a fully known value is not a refusal, it is a bug.
   **Removed.** A keyword now carries a token exactly like a positional argument.
2. **Bare `Name` — the dominant blocker, 131 of 252 sites.** A name that is a parameter has a
   *kind* readable from the call sites that passed it. This round builds that registry and
   records the kind beside the refusal. **But knowing the kind is not knowing the value.**
   Of the names that block a site, 58 were themselves passed a bare `Name` (an infinite
   regress) and 8 a `Constant`. Substituting one would be inventing a value, so the site
   stays refused. **Not removed, and it must not be.**
3. **Arity over a constant two — 3.5% here, 18.4% of all calls tree-wide.** A constant cap is
   not a fact about the world. **Removed** (raised to the tree's own maximum).
4. **Unencodable composites — 36.2%**, of which `Call`/`Attribute` are only 12.2% of all
   arguments. The obvious hypothesis — "nested construction is the blocker" — is **false**,
   and was killed by measurement before any code was written for it.

Two bugs in my own instrument were caught by its own tests: the module holder and the
function holders overlapped so every call inside a function was counted **twice** (127 sites
was really 252), and the parameter-type registry was built and then never wired in, leaving a
dead branch that reported nothing.

## The single ultimate plan, and what was rejected

The evidence says the loop is: **execute → require a differential check → keep only what the
check admits.** The planned parts and why the others are rejected:

**Kept**
1. **Executability mining** (`every_call_site_v1`) — the prior term. Now measured, not assumed.
2. **Differential checkability** (`checkability_by_differential_pin_v1`) — the gate. Reused.
3. **Host instrument reading** (`scan_retrieve_fetch_v1`) — knowledge from the host's own
   words, not from weights. Already measured: 0 probes on a second visit, 4 round trips on a
   foreign host.
4. **Memory keyed by `(content, name)`** — survives reinstalls, refuses to conflate `xz` with
   `unxz`.

**Rejected, with the measurement that killed it**
- *Nested-construction resolution* — killed by 12.2%.
- *Raise the arity cap as the main lever* — killed by 18.4%, and it is a constant.
- *Learn edit templates from experience* — killed by 0/90 on real commits.
- *More demonstrations instead of one* — killed by `repetition_still_never_identifies`.
- *A bigger model / more pretraining* — forbidden by §1, and the field's own numbers say
  single prompts on newer models absorb the engineering, not the reverse.

## Honest state

- **Verified this session:** the three prior "instant learning" claims are false, on the
  project's own instruments, reproduced live. Executability is 17.3% / 25.0% / 6.2% across
  three real repositories with every refusal named. The host loop is real.
- **Unverified:** whether the remaining 82.7% of call sites can be made executable by
  resolving names through *values actually observed at runtime* rather than at parse time.
  That is the next bottleneck and it is the only one of the four that is not yet closed.
- **Failed, stated as failed:** 0 of 6 unguarded real commits became checkable. 0 solved in
  90 executions from a learned vocabulary.
- `truth.achieved` remains `false`. No frontier benchmark was attempted this round, because
  the branch does not yet have a coding capability that could take one honestly.

Authority `NONE__PRODUCER_RUN_SANDBOX`. No runtime model, no network at measurement time,
no stored parameters.
