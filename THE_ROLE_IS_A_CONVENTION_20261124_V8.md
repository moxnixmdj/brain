# THE ROLE IS A CONVENTION — I built the control that could kill my own result, and it partly did
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user.
> §2 resolution stands unchanged. No model call, no stored parameter, no network this round.

---

## 1. What I set out to falsify

Last round's headline was **95.3% portability** (244 of 256 laws re-running their reason on a different
machine) with the first sound transfer in this tree: **93 predictions, 0 wrong**, against blind
inheritance's 216 errors.

But that gain rested on one inference, stated in the code as an assumption:

> every machine in this family fills slot `A4` with the same kind of atom, so `A4` is what travels.

If that is a **naming convention** rather than a property of stored procedures, the 95.3% is the
convention and not the mechanism. So I built the control: a tenth machine, `SCRAMBLED`, whose atoms do
the family's work in a **permuted order** — `A1` sorts, `A2` tac's-then-sorts, `A3` appends, `A4`
drops-a-line-then-sorts. It is a real machine over a real file with real `sh`/`sort`/`tac`/`head`, and
it exists only to be uncooperative.

## 2. The result — two numbers, and they disagree

| quantity | family unchanged (9 machines) | **with SCRAMBLED (10 machines)** |
|---|---|---|
| laws offered | 256 | 288 |
| reason re-ran on the student | 244 (**95.3%**) | 274 (**95.1%**) |
| effect reproduced *and* restated | 12 | **12** |
| held-out reach | 93 | **103** |
| held-out wrong | **0** | **0** |

Scrambling the roles changed nothing. Portability stayed at 95.1%, transfers stayed sound, reach still
grew soundly. **The 95.3% is not the convention.**

But the control earned its keep elsewhere, and this is the part that matters:

```
SCRAMBLED involvements: 32 laws offered · 30 reasons re-ran (94%) · 2 admitted
pairs where transfer added reach: 4 — LIST→ARCHIVE2, →FILESYSTEM, →SQLITE, →TARBALL
```

**Every single transfer that added reach came from LIST.** As a teacher, `SCRAMBLED` admitted 2 laws
across 14 pairs and added zero predictions. So the honest statement of where this stands is:

* **The procedure is portable** — a reason re-runs on ~95% of foreign machines regardless of whether
  roles correspond. That claim survived its control.
* **Portability is not the binding constraint any more.** The binding constraint is that **one teacher
  in ten produces laws that survive**, because a law needs two independent witnesses *and* a contrast,
  and only LIST's state space is rich enough to supply both.

## 3. The mistake I was making, now visible

For three rounds I have measured "reach" mostly as a property of the **learner**. The control shows it
is a property of the **teacher's state diversity**. LIST has 7 atoms and the largest reachable state set;
it is the only machine whose exploration produces enough pairs of states with differing effects to
license a two-witness law with a non-empty contrast.

That reframes the next step completely, and it is the kind of reframing §10 asks for: **stop improving
transfer; increase the density of contrasting evidence per machine.** A machine that yields more
contrasts is worth more than a better transfer rule applied to a machine that yields none.

## 4. Verified / unverified / failed

**This round, by execution:**

* `SCRAMBLED` built and measured: 24 transitions at depth 3, 4 atoms, real file operations. **verified**
* Portability at 95.1% with the control in the family. **verified**
* Zero errors across 103 transferred+own predictions. **verified**
* "Transfer is broadly available across machines" — **FAILED**, and by this round's own control: 4 of 4
  reach gains came from a single teacher.

**Blockers, logged once and not worked around:**
`docker: command not found` in this sandbox, and the benchmark images (SWE-bench Pro, Terminal-Bench 4.0,
OSWorld-V2) require it. No official number can be published from here without falsifying it. This is the
only outstanding item that I cannot do myself, and it is an environment capability, not a decision.

## 5. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0
```

Repo integrity guard PASS (17 rules, 0 violations). Branch `arena/50c05c04-brain`, everything committed.

## 6. Next

The measurement above says where the leverage is: contrast density per machine, not transfer quality.
The next instrument counts, for each machine, **how many two-witness laws with a non-empty contrast its
exploration produces per hundred transitions** — and tests whether a targeted exploration policy
(aimed at producing contrasting pairs, which `ask_instead_of_stare` already does 3.5× better than
random) raises that density. If it does, transfer becomes widely available as a consequence rather than
as a headline, and the LIST-only artefact disappears for a measurable reason.
