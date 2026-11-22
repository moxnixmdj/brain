#!/usr/bin/env python3
"""Run GitChameleon 2.0 items honestly: the stub must fail, the given solution must pass.

This is a harness, not a solution. Its only job is to establish, item by item, that the
oracle the benchmark ships actually discriminates -- so that any later claim about solving
items is measured against a check that would have failed the stub and passes the reference.

It deliberately does NOT read `solution` when evaluating; `solution` is used once, to prove
the oracle is real, and never during scoring of a method under test.

The contract comes from the benchmark's own evaluator (`gitchameleon/eval_sample.py`):
  * the candidate body is concatenated onto `starting_code` and written to `sample_{id}.py`
  * the hidden test file is written verbatim and run with pytest
  * a return code of 0 means pass

Nothing here calls a model. Authority: NONE.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable, Mapping

SCHEMA = "BRAIN_GITCHAMELEON_HARNESS_V1"
DATASET = "dataset/dataset.jsonl"


def load(bench: str | pathlib.Path) -> list[dict]:
    path = pathlib.Path(bench) / DATASET
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _test_path(bench: pathlib.Path, example_id: str) -> pathlib.Path:
    return bench / "dataset" / "hidden_tests" / f"test_sample_{example_id}.py"


def no_dependency(items: Iterable[Mapping[str, Any]]) -> list[dict]:
    """Items whose only requirement is the library itself -- no pinned extras."""
    return [dict(r) for r in items if not (r.get("additional_dependencies") or "").strip()]


def run_item(
    bench: str | pathlib.Path,
    item: Mapping[str, Any],
    body: str,
    *,
    python: str,
    timeout: float = 300.0,
) -> dict:
    """Write stub+body as sample_{id}.py beside the hidden test and run it."""
    bench = pathlib.Path(bench)
    item = dict(item)
    src = f"{item['starting_code']}{body}\n"
    test_src_path = _test_path(bench, item["example_id"])
    if not test_src_path.exists():
        return {"example_id": item["example_id"], "status": "NO_TEST"}
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = pathlib.Path(tmp)
        (tmpd / f"sample_{item['example_id']}.py").write_text(src, encoding="utf-8")
        shutil.copy2(test_src_path, tmpd / f"test_sample_{item['example_id']}.py")
        try:
            proc = subprocess.run(
                [python, "-m", "pytest", "--disable-warnings", "-q", str(tmpd)],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"example_id": item["example_id"], "status": "TIMEOUT", "passed": False}
        except OSError as exc:
            return {"example_id": item["example_id"], "status": f"OSERROR:{exc}", "passed": False}
    out = (proc.stdout or "") + (proc.stderr or "")
    return {
        "example_id": item["example_id"],
        "status": "RAN",
        "passed": proc.returncode == 0,
        "returncode": proc.returncode,
        "tail": "\n".join(out.strip().splitlines()[-4:])[:400],
    }


def stub_body() -> str:
    """A body that supplies nothing: the starting_code already ends at the stub."""
    return "None"


def analyse_oracle(bench: str | pathlib.Path, item: Mapping[str, Any]) -> dict:
    """Describe what the oracle is, without running it.

    `names_the_call` means the test references the library with attribute access, so the
    call it expects is stated somewhere in the test source. This is a property of the
    benchmark, not of any method under test, and it is reported because a score is only
    meaningful alongside what the test actually gave away.
    """
    bench = pathlib.Path(bench)
    path = _test_path(bench, item["example_id"])
    if not path.exists():
        return {"example_id": item["example_id"], "exists": False}
    src = path.read_text(encoding="utf-8", errors="replace")
    lib = str(item["library"]).split("-")[0].replace("-", "_")
    imports_lib = bool(re.search(rf"\b(?:import|from)\s+{re.escape(lib)}\b", src))
    attr_use = bool(re.search(rf"\b{re.escape(lib)}\.", src))
    return {
        "example_id": item["example_id"],
        "exists": True,
        "imports_library": imports_lib,
        "names_the_call": attr_use,
        "test_lines": len(src.splitlines()),
        "needs": sorted({n for n in re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w\.]*)", src, re.M)}),
    }
