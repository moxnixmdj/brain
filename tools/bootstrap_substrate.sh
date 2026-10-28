#!/bin/sh
# Restore the sandbox substrate (see substrate-requirements.txt header).
set -e
pip install --quiet --disable-pip-version-check --break-system-packages \
    -r "$(dirname "$0")/../substrate-requirements.txt"
python3 - <<'PY'
import importlib
for m in ("tree_sitter", "tree_sitter_languages", "mypy", "ruff", "bandit", "coverage"):
    importlib.import_module(m)
print("SUBSTRATE_OK")
PY
