# Recognition is the bottleneck

`--audit` evaluates the human's own replacement at every recorded frame and names why it is refused.

**Before:** of 14 audited rows the instrument accepted the truth **1** time and accused it of a wrong value **6**
times. The audit named the causes: 2 refusals were fixes that **introduce their own names** (`_SkipClose`, an
added attribute) — composite edits that had been counted as single-expression repairs — and 3 of the 6
accusations rested on demands that were **pytest's rendering of the failure**, not values.

**Two corrections:** `is_prose_demand()` refuses rendered assertions (14 strings refused on this corpus), and a
fix referencing a name the parent lacks is reclassified out of the denominator.

**After (30 rows, 71.9 s, 0 parameters):** 15 not single-expression · **2 fix-introduces-a-name** · **6
no-relation (prose refused)** · 5 no-value-matches · 1 site-never-ran · **1 verified, the human's own fix**.
Accusations against the truth fell from 6 to 3, and all three are named: one mis-attributed demand (`[0]` vs
`[True]`) and two exception-message demands.

**Law:** you cannot search for what you cannot accept. Recognition comes before search, and search before
verification.

**Next, acceptance declared first:** bind each comparison to the assertion whose operands the site produced and
refuse a demand that cannot be bound. Acceptance: accusations = 0, ADMISSIBLE ≥ 6 of the audited rows, verified
count unchanged or better.
