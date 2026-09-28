FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends apt-file python3 ca-certificates \
 && apt-file update \
 && command -v apt-file \
 && apt-file list-indices

WORKDIR /opt/brain
COPY . /opt/brain

RUN set -eu; \
  test "$(sha256sum canonical/runtime/capability_discovery.py | awk '{print $1}')" = "40bb62bf05ed315356f428f6c6d7ed2aaef788d6b8c715cf4c833106b46d07d0"; \
  test "$(sha256sum canonical/experiments/run_batched_executable_evidence_fresh_validation_001.py | awk '{print $1}')" = "da59add8a6ddaff4e97271a7ae7e4b77dfd22827a432b0ca4af502f5fb2b14c1"; \
  test "$(sha256sum canonical/experiments/BATCHED_EXECUTABLE_EVIDENCE_FRESH_VALIDATION_001.json | awk '{print $1}')" = "f8dd361e5134c51f70908b7c3735973624ca5da3636d62098ca32699a977d4e6"; \
  echo "__PR85_EXACT_BYTES_VERIFIED__"

RUN bash -lc 'set +e; test ! -e /tmp/PR85_FROZEN_GATE_RAN || exit 97; touch /tmp/PR85_FROZEN_GATE_RAN; python3 canonical/experiments/run_batched_executable_evidence_fresh_validation_001.py > /tmp/pr85_gate.out 2>&1; ec=$?; cat /tmp/pr85_gate.out; echo "__VALIDATOR_EXIT_CODE__=$ec"; exit "$ec"'

CMD ["python3","-m","http.server","10000","--bind","0.0.0.0"]
