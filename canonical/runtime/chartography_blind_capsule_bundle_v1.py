#!/usr/bin/env python3
"""Assemble a self-contained capsule for the public verification-capsule-runner.

The capsule contains exactly the Brain files the blind Chartography run needs, a SHA-256 manifest
binding every byte, and the workflow that (1) pulls surgeai/chartography data.parquet with the
runner's HF_TOKEN, (2) builds solver/scorer views, (3) runs the zero-model solver in a scrubbed
subprocess with the scorer view sealed, (4) scores, (5) uploads the receipt — never the dataset.

Usage: python3 canonical/runtime/chartography_blind_capsule_bundle_v1.py --out /tmp/capsule
Then copy the capsule tree into a verification-capsule-runner PR (repo root).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "canonical/__init__.py",
    "canonical/runtime/__init__.py",
    "canonical/runtime/bound_capabilities/__init__.py",
    "canonical/runtime/bound_capabilities/image_ocr_tesseract.py",
    "canonical/runtime/chartography_deterministic_professional_solver_v1.py",
    "canonical/runtime/chartography_blind_harness_v1.py",
    "canonical/tests/__init__.py",
    "canonical/tests/test_chartography_blind_harness_v1.py",
]
WORKFLOW_NAME = "run-chartography-blind-zero-model-v1.yml"

WORKFLOW = """name: Chartography blind zero-model run V1

on:
  workflow_dispatch:
  pull_request:
    branches: [main]
    paths:
      - ".github/workflows/run-chartography-blind-zero-model-v1.yml"
      - "capsules/chartography_blind_v1/**"

permissions:
  contents: read

jobs:
  blind-run:
    runs-on: ubuntu-24.04
    timeout-minutes: 120
    env:
      HF_TOKEN: ${{ secrets.HF_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - name: Verify capsule bytes against manifest
        shell: bash
        working-directory: capsules/chartography_blind_v1
        run: |
          set -euo pipefail
          sha256sum -c MANIFEST.sha256
      - name: Install deterministic dependencies
        shell: bash
        run: |
          set -euo pipefail
          sudo apt-get update -qq
          sudo apt-get install -y -qq tesseract-ocr tesseract-ocr-eng git-lfs
          python3 -m pip install --quiet --disable-pip-version-check pillow pyarrow
          tesseract --version | head -1
      - name: Harness self-test (no dataset)
        shell: bash
        working-directory: capsules/chartography_blind_v1
        run: PYTHONPATH=. python3 -m unittest canonical.tests.test_chartography_blind_harness_v1
      - name: Fail closed without credential
        shell: bash
        run: |
          if [ -z "${HF_TOKEN:-}" ]; then echo "HF_TOKEN_ABSENT__OWNER_SELF_SERVICE_REQUIRED"; exit 78; fi
      - name: Fetch official dataset bytes (never printed)
        shell: bash
        run: |
          set -euo pipefail
          git lfs install --skip-repo
          GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 "https://user:${HF_TOKEN}@huggingface.co/datasets/surgeai/chartography" hf-chartography >/dev/null 2>&1
          git -C hf-chartography lfs pull --include="data.parquet" >/dev/null 2>&1
          test -f hf-chartography/data.parquet
          mkdir -p out
          sha256sum hf-chartography/data.parquet | tee out/data-parquet-sha256.txt
          git -C hf-chartography rev-parse HEAD | tee out/hf-head.txt
      - name: Build pack and views (held-out split)
        shell: bash
        working-directory: capsules/chartography_blind_v1
        run: |
          set -euo pipefail
          PYTHONPATH=. python3 -m canonical.runtime.chartography_blind_harness_v1 build-pack --parquet ../../hf-chartography/data.parquet --pack ../../work/pack | tee ../../out/build-pack.json
          PYTHONPATH=. python3 -m canonical.runtime.chartography_blind_harness_v1 build-views --pack ../../work/pack --views ../../work/views | tee ../../out/build-views.json
      - name: Blind solver run (scrubbed env, scorer view sealed)
        shell: bash
        working-directory: capsules/chartography_blind_v1
        run: |
          set -euo pipefail
          PYTHONPATH=. python3 -m canonical.runtime.chartography_blind_harness_v1 run --views ../../work/views --results ../../out/results.jsonl | tee ../../out/run.json
      - name: Score
        shell: bash
        working-directory: capsules/chartography_blind_v1
        run: |
          set -euo pipefail
          PYTHONPATH=. python3 -m canonical.runtime.chartography_blind_harness_v1 score --views ../../work/views --results ../../out/results.jsonl --receipt ../../out/CHARTOGRAPHY_BLIND_ZERO_MODEL_RECEIPT.json | tee ../../out/score-summary.json
      - name: Upload receipt only (no dataset bytes)
        uses: actions/upload-artifact@v4
        with:
          name: chartography-blind-zero-model-receipt
          path: |
            out/*.json
            out/*.txt
            out/results.jsonl
          retention-days: 90
"""

README = """# Chartography blind zero-model capsule V1

Source: moxnixmdj/brain, branch arena/086851e2-brain. Every file is bound by MANIFEST.sha256.

What runs: the Brain's deterministic chart solver (`chartography_deterministic_professional_solver_v1`,
bounded OCR only, zero general-purpose-model cognition) over all official Chartography tasks, with
answers held out in a sealed scorer view, in a scrubbed subprocess. Output: a receipt with per-task
pass/abstain/fail, score under ASSUMED grading semantics, and a question-type taxonomy census.

Owner prerequisite (self-service, not outreach): accept the surgeai/chartography dataset terms on a
free Hugging Face account and add `HF_TOKEN` as a repository secret here. Without it the workflow
exits 78 (neutral) at "Fail closed without credential".

Zero credit: the receipt is not the official Chartography score and promotes nothing.
"""


def build(out: Path) -> dict:
    cap = out / "capsules" / "chartography_blind_v1"
    if cap.exists():
        shutil.rmtree(cap)
    manifest_lines = []
    for rel in FILES:
        src = REPO_ROOT / rel
        dst = cap / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not src.exists():
            if src.name == "__init__.py":
                dst.write_text("")  # brain uses namespace packages; the capsule gets explicit ones
            else:
                raise SystemExit(f"MISSING_SOURCE_FILE__{rel}")
        else:
            shutil.copy2(src, dst)
        manifest_lines.append(f"{hashlib.sha256(dst.read_bytes()).hexdigest()}  {rel}")
    (cap / "README.md").write_text(README, encoding="utf-8")
    manifest_lines.append(f"{hashlib.sha256(README.encode()).hexdigest()}  README.md")
    (cap / "MANIFEST.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    wf = out / ".github" / "workflows" / WORKFLOW_NAME
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(WORKFLOW, encoding="utf-8")
    return {
        "capsule_dir": str(cap),
        "workflow": str(wf),
        "file_count": len(FILES) + 1,
        "manifest_sha256": hashlib.sha256((cap / "MANIFEST.sha256").read_bytes()).hexdigest(),
        "workflow_sha256": hashlib.sha256(WORKFLOW.encode()).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(json.dumps(build(Path(a.out)), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
