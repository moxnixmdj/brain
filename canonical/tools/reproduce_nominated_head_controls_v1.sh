#!/usr/bin/env bash
# Explicit constructed calls on exported pinned source, not loading lists into the live agent.
set -euo pipefail
r=$(git rev-parse --show-toplevel); w=$(realpath -m "${1:?new external directory required}"); cd "$r"
case "$w/" in "$PWD/"*) exit 2;; esac
mkdir "$w"; k=faea7c3177fc447499e0c7fe2abc5fe0575c23d0; s=f247563228102c67282d1696806b42b3aa2e29b4
for kind in wave site; do
  d=$w/$kind; mkdir -p "$d"/{root/app,tests,empty}; app=$d/root/app
  if [[ $kind = wave ]]; then
    curl -fsSL "https://codeload.github.com/moxnixmdj/brain/tar.gz/$k" | tar -xz --strip-components=1 -C "$app" \
      "brain-$k/canonical/runtime" "brain-$k/canonical/swe_kernel" "brain-$k/canonical/tools"
    worker=pr_head_claim_controls_v1.py
  else
    mkdir -p "$app/canonical/"{tools,runtime}
    for f in grammar_closed_repair_v1.py site_general_expression_synthesis_v1.py; do
      gh api -H 'Accept: application/vnd.github.raw+json' "repos/moxnixmdj/brain/contents/canonical/tools/$f?ref=$s" > "$app/canonical/tools/$f"
    done
    cp canonical/runtime/finite_minimax_decision_region_v1.py "$app/canonical/runtime/"; worker=compare_site_and_query_v1.py
  fi
  cp "canonical/tools/$worker" "$d/tests/"; printf '#!/bin/sh\nexec /usr/bin/python3 -I -S -B /tests/%s /app\n' "$worker" > "$d/tests/test.sh"
  unshare -Urmpnf --kill-child bash canonical/tools/source_verifier_root_v1.sh "$d/root" "$d/tests" "$d/empty" > "$w/$kind.json"
done
