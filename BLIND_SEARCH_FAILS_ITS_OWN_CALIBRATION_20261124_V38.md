# BLIND SEARCH FAILS ITS OWN CALIBRATION

**Round V38 · 2026-11-24 · branch `arena/50c05c04-brain`**

---

## 1. What I tried to replace

V37 concluded that adding one hand-written operator per bug family repeats the fitting V36 measured — 0 of 6
tasks whose fixes are four lines or fewer. So this round removed the per-family design entirely and tried
**one generic mechanism**: localise a file, then enumerate minimal edits drawn from five blind forms.

| form | what it does | knows nothing about |
|---|---|---|
| `FLIP` | a token becomes its documented opposite (`*`↔`+`, `==`↔`!=`, `is`↔`is not`) | what the token means |
| `QUANTIFIER` | a `*`, `+` or `?` inside a string literal changes | that it is a regex |
| `GUARD` | insert the test's own condition, negated, raising the exception it names | what the function does |
| `BIND` | bind a name that is used but never bound, to an expression already in the file | why it was unbound |
| `REBIND` | swap a name for one in the file sharing its tail (`cls` → `Metadata`) | which object is correct |

If this worked, nothing would ever need writing per task again. **It solves 0 of 6.**

## 2. The calibration is what makes that result readable

A negative result is worthless unless the instrument is proven able to produce a positive. So before accepting
"the targets are hard", I ran the same mechanism on the **3 tasks the old operator set is known to solve**.

**It solves 0 of 3.**

That converts the finding from *"these fixes are too hard for blind search"* into **"this mechanism is weaker
than the thing it replaces"** — which is a different and more useful conclusion, and it is why the calibration
was worth 38 seconds.

## 3. Why it failed, mechanically

An elegant one-character fix — `[\s;)]*` → `[\s;)]+` — is genuinely in this operator's vocabulary. The problem
is that the pool is capped at 60 candidates drawn from a file of 700+ lines, and the correct edit sits at an
*unknown offset* while `GUARD`, `BIND` and `REBIND` generate 12 each. **Token-level search does not reach the
position.** Knowing the *kind* of edit was never enough; the four-round lesson was that the family must be
narrowed until the position is nearly implied.

## 4. Instrument defects found on the way

1. **`QUANTIFIER` silently skipped every f-string.** It reconstructed literals as `prefix + quote + value +
   quote`, which no f-string survives. Finding the real quantifier was impossible until a *separate*
   calibration noticed.
2. **Candidate order was family-major**, so the noisy `FLIP` family could consume the whole budget before a
   precise family ran. Now interleaved.
3. **A quoting error mangled my own patch** of the literal scanner, and the file still imported — nothing
   failed loudly. Silent success is the same defect family as silent failure.
4. **Two of my own tests were wrong**, not the tool: one asserted a substring (`"*"`) that the edited line
   removes, the other searched for the word "licence" and found it in my own docstring. The second is fixed by
   inspecting the AST for string comparisons in *code* rather than grepping text.

## 5. What has actually held, across seven rounds

```
localisation from the assertion   17/28 top-1, 27 within five, 0 blind, 0 model calls
hand-written operators, 8 tasks   3 solved  (fitted; 0 on 20 unseen)
hand-written operators, 28 tasks  0 solved
blind generic search, 6 easy      0 solved
blind generic search, 3 known     0 solved
```

One component generalises. Every generation mechanism tried on top of it has converted that into nothing.

## 6. What this does not establish

Not that generic search is impossible — only that **this** generic search does not work, which is enough to
stop building it and is more than was known yesterday.

**No SWE-bench, Terminal-Bench or OSWorld task has been attempted by this system. No benchmark row exists or
is claimed.** The honest position remains: localisation is a solved-enough problem at this scale; generation
is not solved at all.
