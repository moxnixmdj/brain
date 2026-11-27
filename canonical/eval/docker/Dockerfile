# Clean-room Docker evaluation of the causal-angelic SWE engine.
#
# WHAT THIS IS: a from-scratch python:3.11-slim image that carries ONLY the
# package trees the two engine suites import (namespace packages, stdlib-only,
# zero third-party runtime dependencies, zero model calls, zero network at run
# time) and runs both suites with pytest.
#
# WHAT THIS IS NOT: it is NOT a SWE-bench Pro / Terminal-Bench score and NOT a
# benchmark claim of any kind. It proves the engine and its tests reproduce
# from a pristine closure inside Docker. No result produced here may be quoted
# as "SWE-bench Pro" or "Terminal-Bench" performance.
FROM python:3.11-slim

WORKDIR /app

# Namespace-package trees actually exercised by the suites.
COPY canonical/runtime ./canonical/runtime
COPY canonical/swe_kernel ./canonical/swe_kernel
COPY canonical/corpus ./canonical/corpus
COPY canonical/tests/test_causal_angelic_swe_engine_v1.py ./canonical/tests/test_causal_angelic_swe_engine_v1.py
COPY canonical/tests/test_repo_component_and_cow_engine_v1.py ./canonical/tests/test_repo_component_and_cow_engine_v1.py

RUN pip install --no-cache-dir pytest==8.3.4

CMD ["python", "-m", "pytest", \
     "canonical/tests/test_causal_angelic_swe_engine_v1.py", \
     "canonical/tests/test_repo_component_and_cow_engine_v1.py", \
     "-q"]
