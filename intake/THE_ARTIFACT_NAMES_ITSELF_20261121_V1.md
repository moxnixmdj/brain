# The artifact names itself

**Date:** 2026-11-21
**Status:** measured. +16 items, zero regressions. Largest single gain of the session.

## What was actually limiting

After the signature work, 67 ceiling-achievable items still failed. I had been assuming the
bottleneck was body construction. It was not:

    67-item gap
      truth name IS in the installed corpus ................ 43
      truth name absent from the corpus .................... 24

and of the 43 that were present, **37 never entered `stated_symbols` at all.** The failure was
upstream of construction: the grammar was never told the name. That is a QUESTION failure.

## The question, and why the artifact can answer it

Your framing: *"all he should do is ask the right question."* This is that, made concrete and
free. The goal says:

    "compute the matrix exponential of batched matrices"

The artifact's own docstring for `expm` says:

    "Compute the matrix exponential of an array."

    "applies a median filter on batched images"
    -> `median_filter`: "Calculate a multidimensional median filter."

    "combines the p values from various independent tests"
    -> `combine_pvalues`: "Combine p-values from independent tests that bear upon..."

Neither side is a synonym table, a stored fact, or a trained parameter. **The artifact is asked
what it is, and the goal that describes it is the one it answers.** The ground truth is shipped
inside the library.

## The mechanism

Score every corpus entry by how much of the GOAL's content it covers in its own summary:

    score(name) = sum of IDF(w) for w in goal_words ∩ summary_words
                  ------------------------------------------------
                        sum of IDF(w) for w in goal_words

* `IDF` is computed **over the artifact's own summaries**, so a word that appears in hundreds of
  numpy docstrings (`matrix`) is worth far less than one that appears in a single one
  (`exponential`). Without this, "matrix exponential" tied at 0.500 with `svd`
  ("Singular Value Decomposition ... into two unitary matrices") and lost on the tie-break.
* The **summary** is the artifact's text before its `Parameters` section -- prose it wrote
  about itself, not a signature.
* The benchmark's boilerplate (`complete`, `should`, `parameters`, `default value`) is a
  stopword list and also structurally harmless, because scoring is coverage of the goal.

## Result

    before:  51/193 = 26.4%
    after:   67/193 = 34.7%
    delta:   +16, 0 regressions
    ceiling: 110/193
    we now reach 60.9% of it

The sixteen, and every one is a body the artifact's own prose named:

    66,67,68 numpy   np.convolve(...) mode="full"/"valid" ; np.correlate(...)
    73      numpy   np.cumprod(arr)              <- "cumulative product"
    94      nltk    align_words(hypothesis, reference)
    96      nltk    Tree.fromstring(sentence)
    111     scipy   np.stack([linalg.expm(A[i]) for i in range(...)])
    112     scipy   linalg.expm(A)                <- "matrix exponential"
    117     scipy   1 - np.abs(np.mean(np.exp(1j*a)))
    118     scipy   stats.circvar(a)              <- "circular variance"
    196     sympy   sympy.use(expr, lambda x: x.doit())
    201,203,204,207 sympy  jacobi_symbol / primeomega / primepi / legendre_symbol
    270     plotly  make_subplots(rows=rows, cols=cols)

## Second mechanism, same run: a stated axis is a list literal

scipy 133's goal says "batched images (**batched in the first dimention**)"; the reference is
`median_filter(A, size=size, axes=[1,2])`. The prose stated the axis and the grammar had no way
to turn the word "first" into `[1, 2]`, so every one of scipy's filter items (133, 135, 137,
138, 139, 140, 141, 142) died at `median_filter(A, size)`. The ordinals are now read and the
small axis lists emitted; the oracle decides, which is the standing rule for a hypothesis.

## What this says about the bigger question you asked

You asked: **what should be saved, and what generalized?**

This mechanism saves **nothing**. It is a question with a computed answer. What generalizes is
the question -- "which artifact does this goal describe?" -- and it applied unchanged to numpy,
scipy, sympy, nltk and plotly in one run. That is the same conclusion the project already
reached for shell programs (`ask_the_host_the_right_question_v1.py`: *"what is worth SAVING is
the QUESTION, not the answer"*), now measured on software engineering.

## Not claimed

* 34.7% is the score on the **193 no-dependency items**, in the environment as installed.
* `truth.achieved` remains **false**. Authority remains **NONE**.
* The remaining 43-item gap has not been re-measured against this new number. Doing so is the
  next step, not an assumption that the same mechanism keeps paying.
