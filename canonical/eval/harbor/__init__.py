"""Official-benchmark evaluation harnesses (Harbor task format).

Everything here is an *adapter*: it drives the zero-model engine inside a
third-party benchmark container and reports what actually happened. No module
in this package calls a hosted model, and no number may be quoted from these
files unless it was produced by a real run whose artifacts are committed under
``canonical/eval/results/``.
"""
