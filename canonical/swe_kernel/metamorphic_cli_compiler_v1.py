#!/usr/bin/env python3
"""Table-Free Metamorphic Behavioral Signatures & Snapshot-Checkpointed CLI Chains.

Implements the Constructor-Table elimination law (`NEXT_STEP_THE_CONSTRUCTOR_TABLE_20261019_V1.md`):
instead of hand-authored synthetic probe files (`probe_bytes`), candidate single-stage and
two-stage CLI pipelines are identified by their **algebraic transformation signature** on
deterministic perturbations of the real target file `F` itself:

  - `F_0`        : the real input file
  - `F_cat`      : `F || F` (whole-file concatenation)
  - `F_wdup`     : each line `L` mapped to `L + " " + L` (within-line token doubling)
  - `F_sing(k)`  : `F` + `k` fresh unique singleton lines
  - `F_nonadj(k)`: `k` fresh unique lines prepended at top AND appended at bottom of `F`
                   (non-adjacent twins, catching neighbour-only `uniq` without `sort`!)

Every natural file measurement (`lines`, `uniquelines`, `duplicatelines`, `words`, `bytes`)
occupies a distinct, provable point in `(d_cat, d_wdup, d_sing, d_nonadj)` space — rejecting
version printers, exit-code constants, and neighbour-only run counters with K3 = 0 and $0 spend.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_METAMORPHIC_CLI_COMPILER_V1"


def _ensure_trailing_newline(raw: bytes) -> bytes:
    if not raw:
        return b""
    return raw if raw.endswith(b"\n") else (raw + b"\n")


def build_metamorphic_tuple(real_bytes: bytes, *, k: int = 5) -> dict[str, Any] | None:
    """Construct `(F_0, F_cat, F_wdup, F_sing, F_nonadj)` purely from `real_bytes`."""
    norm = _ensure_trailing_newline(real_bytes)
    lines = norm.splitlines()
    if len(lines) < 2:
        return None

    # Use a deterministic content-derived salt so fresh lines cannot collide with existing lines in F
    salt = hashlib.sha256(norm).hexdigest()[:10].encode("ascii")
    fresh_lines = [b"__meta_%s_%d__" % (salt, i) for i in range(k)]

    f0 = b"\n".join(lines) + b"\n"
    f_cat = f0 + f0
    f_wdup = b"\n".join((ln + b" " + ln if ln else b"a a") for ln in lines) + b"\n"
    f_sing = f0 + b"\n".join(fresh_lines) + b"\n"
    # Prepend fresh_lines at top AND append at bottom so every fresh twin is >= len(lines) apart!
    f_nonadj = b"\n".join(fresh_lines) + b"\n" + f0 + b"\n".join(fresh_lines) + b"\n"

    return {
        "k": k,
        "f0": f0,
        "f_cat": f_cat,
        "f_wdup": f_wdup,
        "f_sing": f_sing,
        "f_nonadj": f_nonadj,
    }


def _parse_single_int(out: bytes) -> int | None:
    txt = out.decode("utf-8", "replace").strip()
    if not txt or "\n" in txt or len(txt) > 80:
        return None
    parts = txt.split()
    if len(parts) > 2:
        return None
    tok = parts[0]
    if tok.isdigit() or (tok.startswith("-") and tok[1:].isdigit()):
        return int(tok)
    return None


def _run_pipeline_bytes(
    stages: Sequence[Sequence[str]],
    input_path: pathlib.Path,
    *,
    timeout: float = 2.5,
) -> int | None:
    """Execute a 1-stage or 2-stage pipeline with `{in}` substituted or stdin fed from `input_path`."""
    env = {
        **os.environ,
        "LC_ALL": "C",
        "LANG": "C",
    }
    try:
        if len(stages) == 1:
            raw_argv = list(stages[0])
            has_in = any("{in}" in a for a in raw_argv)
            argv = [str(input_path) if a == "{in}" else a for a in raw_argv]
            if has_in:
                proc = subprocess.run(
                    argv,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    env=env,
                    timeout=timeout,
                )
            else:
                with input_path.open("rb") as fh:
                    proc = subprocess.run(
                        argv,
                        stdin=fh,
                        capture_output=True,
                        env=env,
                        timeout=timeout,
                    )
            if proc.returncode != 0:
                return None
            return _parse_single_int(proc.stdout)

        if len(stages) == 2:
            s1_raw, s2_raw = list(stages[0]), list(stages[1])
            s1_has_in = any("{in}" in a for a in s1_raw)
            s1 = [str(input_path) if a == "{in}" else a for a in s1_raw]
            s2 = [a for a in s2_raw if a != "{in}"]
            if s1_has_in:
                p1 = subprocess.run(
                    s1,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    env=env,
                    timeout=timeout,
                )
            else:
                with input_path.open("rb") as fh:
                    p1 = subprocess.run(
                        s1,
                        stdin=fh,
                        capture_output=True,
                        env=env,
                        timeout=timeout,
                    )
            if p1.returncode != 0:
                return None
            p2 = subprocess.run(
                s2,
                input=p1.stdout,
                capture_output=True,
                env=env,
                timeout=timeout,
            )
            if p2.returncode != 0:
                return None
            return _parse_single_int(p2.stdout)
    except Exception:
        return None
    return None


def classify_metamorphic_signature(
    vals: Mapping[str, int],
    *,
    k: int,
    f0_bytes: bytes,
    fwdup_bytes: bytes,
) -> str | None:
    """Map observed `(v0, v_cat, v_wdup, v_sing, v_nonadj)` to its unique algebraic kind."""
    v0 = vals["f0"]
    v_cat = vals["f_cat"]
    v_wdup = vals["f_wdup"]
    v_sing = vals["f_sing"]
    v_nonadj = vals["f_nonadj"]

    d_sing = v_sing - v0
    d_nonadj = v_nonadj - v0

    # Constant / version printer rejection: must respond to injected lines/bytes!
    if d_sing == 0 and d_nonadj == 0:
        return None

    # 1. Total lines: doubles on F||F, invariant to within-line doubling, +k on sing, +2k on nonadj
    if v0 > 0 and v_cat == 2 * v0 and v_wdup == v0 and d_sing == k and d_nonadj == 2 * k:
        return "lines"

    # 2. Distinct lines (`uniquelines`): invariant on F||F, invariant on within-line doubling,
    #    +k on sing, AND +k (NOT +2k!) on non-adjacent twins!
    if v0 > 0 and v_cat == v0 and v_wdup == v0 and d_sing == k and d_nonadj == k:
        return "uniquelines"

    # 3. Duplicate lines (`duplicatelines`): invariant on within-line doubling,
    #    +0 on fresh singletons, +k on fresh non-adjacent twins!
    if v0 >= 0 and v_wdup == v0 and d_sing == 0 and d_nonadj == k:
        return "duplicatelines"

    # 4. Total words (`words`): doubles on F||F, doubles on within-line token doubling (when non-empty lines),
    #    +k single-token fresh lines on sing, +2k on nonadj
    if v0 > 0 and v_cat == 2 * v0 and v_wdup == 2 * v0 and d_sing == k and d_nonadj == 2 * k:
        return "words"

    # 5. Exact byte count (`bytes`): tracks byte delta on every perturbation
    if (
        v0 == len(f0_bytes)
        and v_cat == 2 * len(f0_bytes)
        and v_wdup == len(fwdup_bytes)
    ):
        return "bytes"

    return None


def evaluate_pipeline_signature(
    stages: Sequence[Sequence[str]],
    files_map: Mapping[str, pathlib.Path],
    meta: Mapping[str, Any],
    *,
    timeout: float = 2.0,
) -> dict[str, Any] | None:
    """Measure `stages` across the 5 metamorphic perturbations and classify its behavioral kind."""
    vals: dict[str, int] = {}
    # Fast-reject on f0 and f_sing first before paying for all 5 invocations!
    v0 = _run_pipeline_bytes(stages, files_map["f0"], timeout=timeout)
    if v0 is None or v0 < 0:
        return None
    v_sing = _run_pipeline_bytes(stages, files_map["f_sing"], timeout=timeout)
    if v_sing is None:
        return None
    v_nonadj = _run_pipeline_bytes(stages, files_map["f_nonadj"], timeout=timeout)
    if v_nonadj is None or (v_sing == v0 and v_nonadj == v0):
        return None
    v_cat = _run_pipeline_bytes(stages, files_map["f_cat"], timeout=timeout)
    if v_cat is None:
        return None
    v_wdup = _run_pipeline_bytes(stages, files_map["f_wdup"], timeout=timeout)
    if v_wdup is None:
        return None

    vals = {
        "f0": v0,
        "f_cat": v_cat,
        "f_wdup": v_wdup,
        "f_sing": v_sing,
        "f_nonadj": v_nonadj,
    }
    kind = classify_metamorphic_signature(
        vals,
        k=int(meta["k"]),
        f0_bytes=meta["f0"],
        fwdup_bytes=meta["f_wdup"],
    )
    return {
        "stages": [list(s) for s in stages],
        "values": vals,
        "classified_kind": kind,
        "answer_on_raw": v0,
    }


def answer_query_by_metamorphic_signature(
    kind: str,
    target_file: str | pathlib.Path,
    candidate_programs: Sequence[str] | None = None,
    *,
    min_agreement: int = 1,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Answer `lines` / `uniquelines` / `duplicatelines` / `words` / `bytes` WITHOUT `probe_bytes`."""
    fpath = pathlib.Path(target_file).resolve()
    if not fpath.is_file():
        return {"pass": False, "status": "OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL"}

    raw_bytes = fpath.read_bytes()
    meta = build_metamorphic_tuple(raw_bytes)
    if meta is None:
        return {
            "pass": False,
            "status": "OPEN__FILE_TOO_SMALL_FOR_METAMORPHIC_SIGNATURE",
            "kind": kind,
        }

    # Harvest available binaries from PATH or provided `candidate_programs`
    if candidate_programs is not None:
        progs = [p for p in candidate_programs if shutil.which(p)]
    else:
        default_pool = ["wc", "grep", "nl", "sort", "uniq"]
        progs = [p for p in default_pool if shutil.which(p)]

    if not progs:
        return {"pass": False, "status": "OPEN__NO_CANDIDATE_PROGRAMS", "kind": kind}

    # Build candidate 1-stage and 2-stage pipelines by introspecting boolean `--help` flags
    # (skipping flags that take a `=VALUE` argument such as `--output=FILE` or `--files0-from=F`).
    flag_map: dict[str, list[str]] = {}
    flag_re = __import__("re").compile(
        r"(?:^|[\s,])(--[a-z][a-z0-9-]+|-[a-zA-Z])(?![=a-zA-Z0-9-])(?!\s+(?:FILE|F|SEP|KEYDEF|NUM|PROG|DIR|SIZE|N)\b)"
    )
    _UNSAFE_FLAGS = frozenset({"--help", "--version", "-V", "-o", "--output", "-i", "--in-place", "-f", "--file"})
    for p in progs:
        flags: list[str] = []
        try:
            hp = subprocess.run([p, "--help"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1.0)
            txt = (hp.stdout or "") + "\n" + (hp.stderr or "")
            for m in flag_re.finditer(txt):
                fl = m.group(1)
                if fl not in _UNSAFE_FLAGS and fl not in flags:
                    flags.append(fl)
        except Exception:
            pass
        flag_map[p] = flags[:64]

    single_candidates: list[list[list[str]]] = []
    for p in progs:
        single_candidates.append([[p, "{in}"]])
        for fl in flag_map.get(p, ()):
            single_candidates.append([[p, fl, "{in}"]])
            if fl in ("-c", "--count"):
                single_candidates.append([[p, fl, "", "{in}"]])

    with tempfile.TemporaryDirectory(prefix="brain_meta_sig_") as td:
        tdir = pathlib.Path(td)
        files_map: dict[str, pathlib.Path] = {}
        for key in ("f0", "f_cat", "f_wdup", "f_sing", "f_nonadj"):
            fp = tdir / f"{key}.txt"
            fp.write_bytes(meta[key])
            os.chmod(fp, 0o444)
            files_map[key] = fp

        # Also measure exact answer on exact un-normalized `fpath` in case trailing newline differs
        matched_survivors: list[dict[str, Any]] = []
        line_counters: list[list[str]] = []

        for stages in single_candidates:
            ev = evaluate_pipeline_signature(stages, files_map, meta, timeout=timeout)
            if ev is None:
                continue
            if ev["classified_kind"] == "lines" and len(line_counters) < 4:
                # Convert `{in}` counter into stdin-capable stage-2 counter
                s_stdin = [tok for tok in stages[0] if tok != "{in}"]
                if s_stdin not in line_counters:
                    line_counters.append(s_stdin)
            if ev["classified_kind"] == kind:
                exact_val = _run_pipeline_bytes(stages, fpath, timeout=timeout)
                if exact_val is not None:
                    ev["exact_answer"] = str(exact_val)
                    ev["real_binary"] = os.path.realpath(shutil.which(stages[0][0]) or stages[0][0])
                    matched_survivors.append(ev)

        # If 1-stage did not find a match (e.g., `uniquelines` or `duplicatelines`), compose 2-stage!
        if not matched_survivors and line_counters:
            two_stage_candidates: list[list[list[str]]] = []
            for p in progs:
                for fl in flag_map.get(p, ()):
                    if fl in ("-u", "--unique", "-d", "--repeated"):
                        for lc in line_counters[:2]:
                            two_stage_candidates.append([[p, fl, "{in}"], lc])
            # Also allow `sort {in} | uniq -d | wc -l` folded as `sort` -> `uniq -d` or 2-stage transforms
            for p1 in progs:
                for p2 in progs:
                    if p1 == p2:
                        continue
                    for fl2 in flag_map.get(p2, ()):
                        if fl2 in ("-d", "--repeated", "-u", "--unique"):
                            # Evaluate `p1 {in} | p2 fl2` followed by line counting on stdout
                            pass
            for stages in two_stage_candidates:
                ev = evaluate_pipeline_signature(stages, files_map, meta, timeout=timeout)
                if ev is not None and ev["classified_kind"] == kind:
                    exact_val = _run_pipeline_bytes(stages, fpath, timeout=timeout)
                    if exact_val is not None:
                        ev["exact_answer"] = str(exact_val)
                        ev["real_binary"] = (
                            os.path.realpath(shutil.which(stages[0][0]) or stages[0][0])
                            + "|"
                            + os.path.realpath(shutil.which(stages[1][0]) or stages[1][0])
                        )
                        matched_survivors.append(ev)

            # For `duplicatelines` where `sort` + `uniq -d` + `wc -l` is 3 unix filters (or `sort` -> `uniq -d` counted):
            if not matched_survivors and kind == "duplicatelines" and line_counters:
                lc = line_counters[0]
                for p1 in progs:
                    for p2 in progs:
                        if p1 == p2:
                            continue
                        for fl2 in flag_map.get(p2, ()):
                            if fl2 not in ("-d", "--repeated"):
                                continue
                            # Test 3-stage `p1 {in} | p2 fl2 | lc` across the 5 metamorphic files!
                            vals3: dict[str, int] = {}
                            ok3 = True
                            for mkey, mpath in files_map.items():
                                try:
                                    r1 = subprocess.run([p1, str(mpath)], capture_output=True, timeout=timeout)
                                    if r1.returncode != 0:
                                        ok3 = False
                                        break
                                    r2 = subprocess.run([p2, fl2], input=r1.stdout, capture_output=True, timeout=timeout)
                                    if r2.returncode != 0:
                                        ok3 = False
                                        break
                                    r3 = subprocess.run(lc, input=r2.stdout, capture_output=True, timeout=timeout)
                                    val = _parse_single_int(r3.stdout) if r3.returncode == 0 else None
                                    if val is None:
                                        ok3 = False
                                        break
                                    vals3[mkey] = val
                                except Exception:
                                    ok3 = False
                                    break
                            if ok3 and classify_metamorphic_signature(
                                vals3, k=int(meta["k"]), f0_bytes=meta["f0"], fwdup_bytes=meta["f_wdup"]
                            ) == "duplicatelines":
                                r1 = subprocess.run([p1, str(fpath)], capture_output=True, timeout=timeout)
                                r2 = subprocess.run([p2, fl2], input=r1.stdout, capture_output=True, timeout=timeout)
                                r3 = subprocess.run(lc, input=r2.stdout, capture_output=True, timeout=timeout)
                                exact_val = _parse_single_int(r3.stdout)
                                if exact_val is not None:
                                    matched_survivors.append({
                                        "stages": [[p1, "{in}"], [p2, fl2], lc],
                                        "values": vals3,
                                        "classified_kind": "duplicatelines",
                                        "exact_answer": str(exact_val),
                                        "real_binary": f"{p1}|{p2}|{lc[0]}",
                                    })
                                    break
                        if matched_survivors:
                            break
                    if matched_survivors:
                        break

    if not matched_survivors:
        return {
            "pass": False,
            "status": "OPEN__NOTHING_MATCHED_METAMORPHIC_SIGNATURE",
            "kind": kind,
        }

    votes: dict[str, set[str]] = {}
    for sv in matched_survivors:
        ans = sv["exact_answer"]
        votes.setdefault(ans, set()).add(sv["real_binary"])
    best_ans, bins = sorted(votes.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0]
    if len(bins) < min_agreement:
        return {
            "pass": False,
            "status": "OPEN__INSUFFICIENT_METAMORPHIC_AGREEMENT",
            "kind": kind,
        }

    return {
        "pass": True,
        "status": (
            "PASS__MEASURED_BY_METAMORPHIC_AGREEMENT"
            if len(bins) > 1
            else "PASS__MEASURED_BY_METAMORPHIC_SIGNATURE"
        ),
        "kind": kind,
        "value": best_ans,
        "answer": best_ans,
        "agreement": len(bins),
        "table_free_metamorphic": True,
        "survivors": [
            {"argv": sv["stages"], "metamorphic_values": sv["values"]}
            for sv in matched_survivors
        ],
        "votes": {k: sorted(v) for k, v in votes.items()},
    }
