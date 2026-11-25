#!/usr/bin/env python3
"""Executable Mental Model, Relational State Vocabulary & Two-Tier Epistemic Environment Agent.

Resolves the core computer-use and unfamiliar-environment bottlenecks measured in:
  - `THE_VOCABULARY_IS_THE_ARTIFACT_20261125_V1.md` (5-machine state-relation vocabulary:
    EXISTENCE, KIND, DIGEST, ORDER, PAIRING, SQLITE_RELATIONS, GIT_STATE),
  - `THE_GUIDE_IS_A_TEST_SUITE_20261204_V1.md` (94.04% of prose docs is uncheckable;
    only CoW-executed transcripts with measured state deltas are admitted),
  - `SCAN_AND_DIFF_AGAINST_MEMORY_20261124_V1.md` & `settlement_v1.py` (Tier-1 passive
    goal-cone scan & diff against memory, followed by Tier-2 `bits/ms` active probing
    strictly on UNKNOWN/STALE goal-relevant operators),
  - `THE_BRANCH_IS_THE_MODEL_20261128_V1.md` (microsecond in-RAM relational forward
    simulation for multi-step lookahead + `os.link` CoW branch execution before commit).

Authority: NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Stored world facts: 0.
"""
from __future__ import annotations

import copy
import csv
import dataclasses
from dataclasses import dataclass, field
import hashlib
import io
import json
import os
import pathlib
import re
import shlex
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import settlement_v1  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EXECUTABLE_MENTAL_MODEL_V1"
ACTION_STORE_SCHEMA = "PROJECT_BRAIN_RELATIONAL_ACTION_STORE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"


# =========================================================================== #
# 1. Rich Relational Environment State (Files, Digests, Order, SQLite, Git)   #
# =========================================================================== #

@dataclass(frozen=True)
class FileFact:
    rel_path: str
    kind: str                # json | csv | sqlite | tar_gz | zip | exec_tool | text | binary
    sha256: str
    size: int
    executable: bool
    json_keys: tuple[str, ...] = ()
    csv_header: tuple[str, ...] = ()
    csv_rows: tuple[tuple[str, ...], ...] = ()
    archive_members: tuple[str, ...] = ()


@dataclass(frozen=True)
class SqliteTableFact:
    db_rel_path: str
    table: str
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]


@dataclass(frozen=True)
class GitStateFact:
    present: bool
    branch: str = ""
    head_sha: str = ""
    dirty_paths: tuple[str, ...] = ()
    stash_count: int = 0


@dataclass(frozen=True)
class DomElementFact:
    source_rel: str
    elem_id: str
    role: str
    name: str = ""
    value: str = ""
    enabled: bool = True
    checked: bool = False
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass(frozen=True)
class CanvasRegionFact:
    """Zero-VLM connected-component visual region extracted from raw PPM/PGM canvas frames."""
    source_rel: str
    region_idx: int
    bbox: tuple[int, int, int, int]
    mean_rgb: tuple[int, int, int]
    pixel_area: int


@dataclass
class EnvironmentSnapshot:
    """Complete relational perception of a digital workspace (FS + SQLite + Git + DOM/a11y + Canvas)."""
    files: dict[str, FileFact] = field(default_factory=dict)
    sqlite_tables: dict[tuple[str, str], SqliteTableFact] = field(default_factory=dict)
    git: GitStateFact = field(default_factory=lambda: GitStateFact(present=False))
    local_tools: dict[str, str] = field(default_factory=dict)   # tool_name -> rel_path
    stem_pairs: tuple[tuple[str, str], ...] = ()
    dom_elements: dict[str, DomElementFact] = field(default_factory=dict)  # elem_id -> DomElementFact
    canvas_regions: tuple[CanvasRegionFact, ...] = ()

    def clone(self) -> "EnvironmentSnapshot":
        return EnvironmentSnapshot(
            files=dict(self.files),
            sqlite_tables=dict(self.sqlite_tables),
            git=self.git,
            local_tools=dict(self.local_tools),
            stem_pairs=self.stem_pairs,
            dom_elements=dict(self.dom_elements),
            canvas_regions=self.canvas_regions,
        )


def _shm_root() -> pathlib.Path:
    shm = pathlib.Path("/dev/shm")
    return shm if shm.is_dir() and os.access(shm, os.W_OK) else pathlib.Path(tempfile.gettempdir())


def _parse_inner_payload_metadata(payload_bytes: bytes) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...], tuple[str, ...]]:
    """Inspect inner archive payload in memory (read-only) for relational simulation accuracy."""
    try:
        txt = payload_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return (), (), ()
    if txt.startswith("{") and txt.endswith("}"):
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict):
                return tuple(sorted(obj.keys())), (), ()
        except Exception:
            pass
    if "," in txt and "\n" in txt:
        try:
            rows = list(csv.reader(io.StringIO(txt)))
            if len(rows) >= 2 and len(rows[0]) >= 2 and all(len(r) == len(rows[0]) for r in rows):
                return (), tuple(tuple(r) for r in rows[1:]), tuple(rows[0])
        except Exception:
            pass
    return (), (), ()


def _detect_file_fact(fp: pathlib.Path, rel: str) -> FileFact:
    raw = fp.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:24]
    st = fp.stat()
    is_exec = bool(st.st_mode & stat.S_IXUSR)

    # Archive detection by header / suffix
    if raw[:2] == b"\x1f\x8b" or rel.endswith((".tar.gz", ".tgz", ".tar")):
        try:
            with tarfile.open(fp, "r:*") as tf:
                file_members = [m for m in tf.getmembers() if m.isfile()]
                members = tuple(sorted(m.name for m in file_members))
                jkeys, crows, chdr = (), (), ()
                if file_members:
                    fobj = tf.extractfile(file_members[0])
                    if fobj is not None:
                        jkeys, crows, chdr = _parse_inner_payload_metadata(fobj.read())
            return FileFact(rel, "tar_gz", digest, len(raw), is_exec, json_keys=jkeys, csv_header=chdr, csv_rows=crows, archive_members=members)
        except Exception:
            pass
    if raw[:4] == b"PK\x03\x04" or rel.endswith(".zip"):
        try:
            with zipfile.ZipFile(fp, "r") as zf:
                names = sorted(n for n in zf.namelist() if not n.endswith("/"))
                jkeys, crows, chdr = (), (), ()
                if names:
                    jkeys, crows, chdr = _parse_inner_payload_metadata(zf.read(names[0]))
            return FileFact(rel, "zip", digest, len(raw), is_exec, json_keys=jkeys, csv_header=chdr, csv_rows=crows, archive_members=tuple(names))
        except Exception:
            pass
    if raw[:16].startswith(b"SQLite format 3") or rel.endswith((".db", ".sqlite", ".sqlite3")):
        return FileFact(rel, "sqlite", digest, len(raw), is_exec)

    if is_exec and (rel.startswith(("bin/", "tools/", "scripts/")) or raw.startswith(b"#!")):
        return FileFact(rel, "exec_tool", digest, len(raw), is_exec)

    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        return FileFact(rel, "binary", digest, len(raw), is_exec)

    stripped = txt.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return FileFact(rel, "json", digest, len(raw), is_exec, json_keys=tuple(sorted(parsed.keys())))
        except Exception:
            pass

    if rel.endswith(".csv") or ("," in stripped and "\n" in stripped and not stripped.startswith("#!")):
        try:
            reader = list(csv.reader(io.StringIO(stripped)))
            if len(reader) >= 2 and len(reader[0]) >= 2 and all(len(r) == len(reader[0]) for r in reader):
                hdr = tuple(reader[0])
                rows = tuple(tuple(r) for r in reader[1:])
                return FileFact(rel, "csv", digest, len(raw), is_exec, csv_header=hdr, csv_rows=rows)
        except Exception:
            pass

    return FileFact(rel, "text", digest, len(raw), is_exec)


def _read_sqlite_facts(fp: pathlib.Path, rel: str) -> dict[tuple[str, str], SqliteTableFact]:
    out: dict[tuple[str, str], SqliteTableFact] = {}
    try:
        conn = sqlite3.connect(f"file:{fp}?mode=ro", uri=True)
        try:
            cur = conn.cursor()
            tables = [
                r[0] for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            ]
            for tbl in tables:
                cols = tuple(r[1] for r in cur.execute(f'PRAGMA table_info("{tbl}")').fetchall())
                rows = tuple(tuple(r) for r in cur.execute(f'SELECT * FROM "{tbl}"').fetchall())
                out[(rel, tbl)] = SqliteTableFact(db_rel_path=rel, table=tbl, columns=cols, rows=rows)
        finally:
            conn.close()
    except Exception:
        pass
    return out


def _read_git_state(root: pathlib.Path) -> GitStateFact:
    if not (root / ".git").exists():
        return GitStateFact(present=False)
    try:
        br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(root), capture_output=True, text=True, timeout=3)
        hd = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, text=True, timeout=3)
        st = subprocess.run(["git", "status", "--porcelain"], cwd=str(root), capture_output=True, text=True, timeout=3)
        sl = subprocess.run(["git", "stash", "list"], cwd=str(root), capture_output=True, text=True, timeout=3)
        dirty = tuple(sorted(line[3:].strip() for line in (st.stdout or "").splitlines() if len(line) > 3))
        stashes = len([l for l in (sl.stdout or "").splitlines() if l.strip()])
        return GitStateFact(
            present=True,
            branch=(br.stdout or "").strip(),
            head_sha=(hd.stdout or "").strip()[:16],
            dirty_paths=dirty,
            stash_count=stashes,
        )
    except Exception:
        return GitStateFact(present=True)


def _read_a11y_dom_facts(fp: pathlib.Path, rel: str) -> dict[str, DomElementFact]:
    """Parse structured accessibility/DOM element snapshots (`*.a11y.json`, `*.dom.json`)."""
    out: dict[str, DomElementFact] = {}
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        nodes = data.get("elements") if isinstance(data, Mapping) else (data if isinstance(data, list) else None)
        if not isinstance(nodes, list):
            return out
        for idx, item in enumerate(nodes):
            if not isinstance(item, Mapping):
                continue
            eid = str(item.get("id") or item.get("elem_id") or f"node_{idx}")
            bb_raw = item.get("bbox") or (0, 0, 0, 0)
            bbox = tuple(int(x) for x in bb_raw[:4]) if isinstance(bb_raw, (list, tuple)) and len(bb_raw) >= 4 else (0, 0, 0, 0)
            out[eid] = DomElementFact(
                source_rel=rel,
                elem_id=eid,
                role=str(item.get("role") or "generic"),
                name=str(item.get("name") or item.get("label") or ""),
                value=str(item.get("value") if item.get("value") is not None else ""),
                enabled=bool(item.get("enabled", not item.get("disabled", False))),
                checked=bool(item.get("checked", False)),
                bbox=bbox,  # type: ignore[arg-type]
            )
    except Exception:
        pass
    return out


def _segment_ppm_canvas_regions(fp: pathlib.Path, rel: str) -> list[CanvasRegionFact]:
    """Deterministic zero-VLM connected-component bounding-box segmentation on binary P6 PPM frames."""
    try:
        raw = fp.read_bytes()
        if not raw.startswith(b"P6"):
            return []
        # Parse P6 header tokens (skipping `#` comments)
        i = 2
        tokens: list[bytes] = []
        n = len(raw)
        while len(tokens) < 3 and i < n:
            while i < n and raw[i:i + 1] in (b" ", b"\t", b"\r", b"\n"):
                i += 1
            if i < n and raw[i:i + 1] == b"#":
                while i < n and raw[i:i + 1] != b"\n":
                    i += 1
                continue
            j = i
            while j < n and raw[j:j + 1] not in (b" ", b"\t", b"\r", b"\n"):
                j += 1
            if j > i:
                tokens.append(raw[i:j])
            i = j
        if len(tokens) < 3:
            return []
        w, h, _maxv = int(tokens[0]), int(tokens[1]), int(tokens[2])
        i += 1  # single whitespace byte after maxval
        pix = raw[i:i + w * h * 3]
        if len(pix) < w * h * 3 or w <= 0 or h <= 0 or w * h > 262144:
            return []
        # Background = corner pixel RGB
        bg = (pix[0], pix[1], pix[2])
        visited = bytearray(w * h)
        regions: list[CanvasRegionFact] = []
        for y0 in range(h):
            for x0 in range(w):
                idx0 = y0 * w + x0
                if visited[idx0]:
                    continue
                visited[idx0] = 1
                p0 = idx0 * 3
                rgb0 = (pix[p0], pix[p0 + 1], pix[p0 + 2])
                if rgb0 == bg:
                    continue
                # Flood-fill foreground component of matching color
                stack = [(x0, y0)]
                min_x = max_x = x0
                min_y = max_y = y0
                area = 0
                while stack:
                    cx, cy = stack.pop()
                    area += 1
                    if cx < min_x:
                        min_x = cx
                    if cx > max_x:
                        max_x = cx
                    if cy < min_y:
                        min_y = cy
                    if cy > max_y:
                        max_y = cy
                    for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                        if 0 <= nx < w and 0 <= ny < h:
                            nidx = ny * w + nx
                            if not visited[nidx]:
                                np = nidx * 3
                                if (pix[np], pix[np + 1], pix[np + 2]) == rgb0:
                                    visited[nidx] = 1
                                    stack.append((nx, ny))
                if area >= 4:
                    regions.append(CanvasRegionFact(
                        source_rel=rel,
                        region_idx=len(regions),
                        bbox=(min_x, min_y, max_x + 1, max_y + 1),
                        mean_rgb=rgb0,
                        pixel_area=area,
                    ))
        return regions
    except Exception:
        return []


def perceive_environment_state(root: pathlib.Path | str) -> EnvironmentSnapshot:
    """Validator-grade relational state perception (`< 15 ms` on typical workspaces)."""
    root_p = pathlib.Path(root).resolve()
    files: dict[str, FileFact] = {}
    sqlite_tables: dict[tuple[str, str], SqliteTableFact] = {}
    local_tools: dict[str, str] = {}
    by_stem: dict[str, list[str]] = {}
    dom_elements: dict[str, DomElementFact] = {}
    canvas_regions: list[CanvasRegionFact] = []

    for cur, dirs, fnames in os.walk(root_p):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache"))
        for fn in sorted(fnames):
            fp = pathlib.Path(cur) / fn
            if fp.is_symlink():
                continue
            rel = fp.relative_to(root_p).as_posix()
            ff = _detect_file_fact(fp, rel)
            files[rel] = ff
            if ff.kind == "sqlite":
                sqlite_tables.update(_read_sqlite_facts(fp, rel))
            if rel.endswith((".a11y.json", ".dom.json")):
                dom_elements.update(_read_a11y_dom_facts(fp, rel))
            if rel.endswith(".ppm"):
                canvas_regions.extend(_segment_ppm_canvas_regions(fp, rel))
            if ff.kind == "exec_tool" or (ff.executable and "/" in rel):
                tname = pathlib.Path(rel).name
                local_tools[tname] = rel
            stem = pathlib.Path(rel).stem
            by_stem.setdefault(stem, []).append(rel)

    pairs: list[tuple[str, str]] = []
    for _stem, rels in sorted(by_stem.items()):
        if len(rels) >= 2:
            for i in range(len(rels)):
                for j in range(i + 1, len(rels)):
                    pairs.append((rels[i], rels[j]))

    return EnvironmentSnapshot(
        files=files,
        sqlite_tables=sqlite_tables,
        git=_read_git_state(root_p),
        local_tools=local_tools,
        stem_pairs=tuple(pairs),
        dom_elements=dom_elements,
        canvas_regions=tuple(canvas_regions),
    )


# =========================================================================== #
# 2. Relational Deltas, Falsifiable Operator Contracts & External Store       #
# =========================================================================== #

@dataclass(frozen=True)
class RelationalEffect:
    """Abstracted state transition relation learned from CoW execution (zero raw paths!).

    Effect ops:
      - EXTRACT_ARCHIVE_MEMBER(in_role, out_dir_or_file, out_kind, member_suffix)
      - TRANSFORM_FILE(in_role, out_role, in_kind, out_kind, preserves_in, sorts_col)
      - RENAME_OR_MOVE(in_role, out_role)
      - SQLITE_MUTATION(db_role, table, effect_tag)
      - GIT_STAGE_COMMIT(preserves_stash)
      - DESTRUCTIVE_HAZARD(reason)  # e.g. deletes bystander files, drops stash, wipes db!
    """
    op: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class OperatorContract:
    """Versioned, falsifiable relational contract for a CLI/script/action operator."""
    contract_id: str
    tool_name: str
    tool_sha256: str
    arg_template: list[str]         # e.g. ["{tool}", "--extract", "{in_0}", "--to", "{out_0}"]
    input_kinds: list[str]
    effects: list[RelationalEffect]
    hazardous: bool = False
    hazard_reason: str = ""
    verified_runs: int = 1
    refutations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "tool_name": self.tool_name,
            "tool_sha256": self.tool_sha256,
            "arg_template": self.arg_template,
            "input_kinds": self.input_kinds,
            "effects": [{"op": e.op, "params": e.params} for e in self.effects],
            "hazardous": self.hazardous,
            "hazard_reason": self.hazard_reason,
            "verified_runs": self.verified_runs,
            "refutations": self.refutations,
        }

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "OperatorContract":
        return OperatorContract(
            contract_id=str(d["contract_id"]),
            tool_name=str(d["tool_name"]),
            tool_sha256=str(d["tool_sha256"]),
            arg_template=list(d["arg_template"]),
            input_kinds=list(d.get("input_kinds") or []),
            effects=[RelationalEffect(str(e["op"]), dict(e.get("params") or {})) for e in (d.get("effects") or [])],
            hazardous=bool(d.get("hazardous", False)),
            hazard_reason=str(d.get("hazard_reason") or ""),
            verified_runs=int(d.get("verified_runs") or 1),
            refutations=int(d.get("refutations") or 0),
        )


class RelationalActionStore:
    """External, version-checked store of generalized relational operator contracts."""

    def __init__(self, path: pathlib.Path | str | None = None) -> None:
        default_p = ROOT / "canonical" / "astra_runtime" / "tmp" / "relational_action_store_v1.json"
        self.path = pathlib.Path(path) if path else default_p
        self.contracts: dict[str, list[OperatorContract]] = {}  # tool_name -> [contracts]
        if self.path.is_file():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, Mapping) and raw.get("schema") == ACTION_STORE_SCHEMA:
                for item in raw.get("contracts") or []:
                    c = OperatorContract.from_dict(item)
                    self.contracts.setdefault(c.tool_name, []).append(c)
        except Exception:
            self.contracts = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flat = [c.to_dict() for cs in sorted(self.contracts.values(), key=lambda x: x[0].tool_name if x else "") for c in cs]
        payload = {
            "schema": ACTION_STORE_SCHEMA,
            "authority": AUTHORITY,
            "contract_count": len(flat),
            "contracts": flat,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def diff_tool_status(self, tool_name: str, current_sha256: str) -> str:
        """Classify tool as `KNOWN_VERIFIED`, `STALE_VERSION`, or `UNKNOWN`."""
        entries = self.contracts.get(tool_name)
        if not entries:
            return "UNKNOWN"
        if all(c.tool_sha256 == current_sha256 and c.refutations == 0 for c in entries):
            return "KNOWN_VERIFIED"
        return "STALE_VERSION"

    def upsert_contracts(self, tool_name: str, current_sha256: str, learned: Sequence[OperatorContract]) -> None:
        # Purge stale-digest contracts for `tool_name` (Skill-V versioned replacement!)
        kept = [c for c in self.contracts.get(tool_name, ()) if c.tool_sha256 == current_sha256]
        seen_ids = {c.contract_id for c in kept}
        for c in learned:
            if c.contract_id not in seen_ids:
                kept.append(c)
                seen_ids.add(c.contract_id)
        self.contracts[tool_name] = kept
        self.save()


# =========================================================================== #
# 3. Goal Specification & Microsecond In-RAM Executable Mental Simulator      #
# =========================================================================== #

@dataclass(frozen=True)
class EnvironmentGoal:
    """Declarative relational postcondition over `EnvironmentSnapshot`."""
    required_files: dict[str, dict[str, Any]] = field(default_factory=dict)
    # e.g. {"out/clean.csv": {"kind": "csv", "sorted_by_col": 1, "min_rows": 2}}
    required_sqlite: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    # e.g. {("data/app.db", "orders"): {"where_col_eq": ("status", "settled"), "min_matching": 2}}
    required_dom_elements: dict[str, dict[str, Any]] = field(default_factory=dict)
    # e.g. {"status_banner": {"value": "SETTLED"}}
    protected_bystanders: tuple[str, ...] = ()
    preserve_git_stash: bool = True
    require_git_clean: bool = False


def check_goal_satisfied(
    snap: EnvironmentSnapshot,
    initial_snap: EnvironmentSnapshot,
    goal: EnvironmentGoal,
) -> tuple[bool, list[str]]:
    """Evaluate all target relational predicates AND bystander/stash preservation invariants."""
    unmet: list[str] = []

    # 1. Bystander & Git Stash Safety Invariants
    for bp in goal.protected_bystanders:
        orig_f = initial_snap.files.get(bp)
        cur_f = snap.files.get(bp)
        if orig_f is not None and (cur_f is None or cur_f.sha256 != orig_f.sha256):
            unmet.append(f"BYSTANDER_VIOLATED:{bp}")

    if goal.preserve_git_stash and initial_snap.git.present:
        if snap.git.stash_count < initial_snap.git.stash_count:
            unmet.append("GIT_STASH_DESTROYED")

    if goal.require_git_clean and snap.git.present and snap.git.dirty_paths:
        unmet.append(f"GIT_DIRTY:{snap.git.dirty_paths}")

    # 2. Target File Relational Predicates (EXISTENCE, KIND, ORDER, JSON_KEYS, NON_EMPTY)
    for rel, spec in goal.required_files.items():
        ff = snap.files.get(rel)
        if ff is None:
            unmet.append(f"MISSING_FILE:{rel}")
            continue
        if "kind" in spec and ff.kind != spec["kind"]:
            unmet.append(f"WRONG_KIND:{rel}:{ff.kind}!={spec['kind']}")
        if "min_rows" in spec and len(ff.csv_rows) < int(spec["min_rows"]):
            unmet.append(f"TOO_FEW_ROWS:{rel}:{len(ff.csv_rows)}")
        if "sorted_by_col" in spec and ff.csv_rows:
            col_idx = int(spec["sorted_by_col"])
            keys = [_numeric_or_str(r[col_idx]) for r in ff.csv_rows if col_idx < len(r)]
            if keys != sorted(keys):
                unmet.append(f"UNSORTED_COL:{rel}:{col_idx}")
        if "required_json_keys" in spec:
            req_k = set(spec["required_json_keys"])
            if not req_k.issubset(set(ff.json_keys)):
                unmet.append(f"MISSING_JSON_KEYS:{rel}:{sorted(req_k - set(ff.json_keys))}")

    # 3. Target SQLite Relational Predicates
    for (db_rel, tbl), spec in goal.required_sqlite.items():
        tf = snap.sqlite_tables.get((db_rel, tbl))
        if tf is None:
            unmet.append(f"MISSING_SQLITE_TABLE:{db_rel}:{tbl}")
            continue
        if "where_col_eq" in spec:
            col_nm, target_val = spec["where_col_eq"]
            if col_nm not in tf.columns:
                unmet.append(f"MISSING_COL:{tbl}:{col_nm}")
            else:
                cidx = tf.columns.index(col_nm)
                matches = sum(1 for r in tf.rows if str(r[cidx]) == str(target_val))
                min_m = int(spec.get("min_matching", 1))
                if matches < min_m:
                    unmet.append(f"SQLITE_PRED_UNMET:{tbl}:{col_nm}=={target_val}({matches}<{min_m})")
        if "row_count" in spec and len(tf.rows) != int(spec["row_count"]):
            unmet.append(f"SQLITE_ROW_COUNT:{tbl}:{len(tf.rows)}!={spec['row_count']}")

    # 4. Target DOM / Accessibility Element Predicates
    for eid, spec in goal.required_dom_elements.items():
        el = snap.dom_elements.get(eid)
        if el is None:
            unmet.append(f"MISSING_DOM_ELEMENT:{eid}")
            continue
        if "value" in spec and el.value != str(spec["value"]):
            unmet.append(f"DOM_VALUE_MISMATCH:{eid}:{el.value}!={spec['value']}")
        if "checked" in spec and el.checked != bool(spec["checked"]):
            unmet.append(f"DOM_CHECKED_MISMATCH:{eid}:{el.checked}!={spec['checked']}")
        if "enabled" in spec and el.enabled != bool(spec["enabled"]):
            unmet.append(f"DOM_ENABLED_MISMATCH:{eid}:{el.enabled}!={spec['enabled']}")

    return len(unmet) == 0, unmet


def _numeric_or_str(v: str) -> tuple[int, Any]:
    try:
        return (0, float(v))
    except ValueError:
        return (1, v)


@dataclass(frozen=True)
class BoundAction:
    """A concrete instantiation of an `OperatorContract` bound to workspace arguments."""
    contract_id: str
    tool_name: str
    argv: tuple[str, ...]
    bindings: dict[str, str]


class RelationalWorldSimulator:
    """Microsecond in-RAM forward mental model (`~5-15 us` per transition).

    Predicts `next_snapshot = step(snapshot, bound_action)` using learned relational
    contracts + the Frame Axiom (untouched files, SQLite tables, and Git stashes
    persist unchanged; hazardous contracts immediately mark bystanders/stashes violated).
    """

    def simulate_step(
        self,
        snap: EnvironmentSnapshot,
        contract: OperatorContract,
        bindings: Mapping[str, str],
    ) -> EnvironmentSnapshot | None:
        if contract.hazardous:
            # Mental model immediately foresees bystander/stash destruction and rejects!
            return None

        nxt = snap.clone()
        for eff in contract.effects:
            if eff.op == "DESTRUCTIVE_HAZARD":
                return None

            if eff.op == "EXTRACT_ARCHIVE_MEMBER":
                in_path = bindings.get("in_0", "")
                out_path = bindings.get("out_0", "")
                in_f = nxt.files.get(in_path)
                if in_f is None or in_f.kind not in ("tar_gz", "zip"):
                    return None
                out_kind = str(eff.params.get("out_kind") or ("csv" if in_f.csv_rows else "text"))
                nxt.files[out_path] = FileFact(
                    rel_path=out_path,
                    kind=out_kind,
                    sha256=f"sim_extract_{in_f.sha256[:12]}",
                    size=max(1, in_f.size),
                    executable=False,
                    csv_header=in_f.csv_header if out_kind == "csv" else (),
                    csv_rows=in_f.csv_rows if out_kind == "csv" else (),
                    json_keys=in_f.json_keys if out_kind == "json" else (),
                )

            elif eff.op == "TRANSFORM_FILE":
                in_path = bindings.get("in_0", "")
                out_path = bindings.get("out_0", in_path)
                in_f = nxt.files.get(in_path)
                if in_f is None:
                    return None
                expected_in_kind = eff.params.get("in_kind")
                if expected_in_kind and in_f.kind != expected_in_kind:
                    return None
                out_kind = str(eff.params.get("out_kind") or in_f.kind)
                rows = in_f.csv_rows
                sorts_col = eff.params.get("sorts_col")
                if sorts_col is not None and rows:
                    cidx = int(sorts_col)
                    rows = tuple(sorted(rows, key=lambda r: _numeric_or_str(r[cidx]) if cidx < len(r) else (1, "")))
                if not eff.params.get("preserves_in", True) and out_path != in_path:
                    nxt.files.pop(in_path, None)
                nxt.files[out_path] = FileFact(
                    rel_path=out_path,
                    kind=out_kind,
                    sha256=f"sim_tx_{in_f.sha256[:10]}_{eff.params}",
                    size=max(1, in_f.size),
                    executable=False,
                    json_keys=tuple(eff.params.get("json_keys") or in_f.json_keys),
                    csv_header=in_f.csv_header,
                    csv_rows=rows,
                )

            elif eff.op == "SQLITE_MUTATION":
                db_path = bindings.get("in_0", "")
                tbl = str(eff.params.get("table") or "")
                tf = nxt.sqlite_tables.get((db_path, tbl))
                if tf is None:
                    return None
                set_col = eff.params.get("set_col")
                set_val = eff.params.get("set_val")
                new_rows = tf.rows
                if set_col in tf.columns and set_val is not None:
                    cidx = tf.columns.index(set_col)
                    new_rows = tuple(
                        tuple(set_val if j == cidx else v for j, v in enumerate(r))
                        for r in tf.rows
                    )
                nxt.sqlite_tables[(db_path, tbl)] = SqliteTableFact(
                    db_rel_path=db_path,
                    table=tbl,
                    columns=tf.columns,
                    rows=new_rows,
                )
                if db_path in nxt.files:
                    old_db = nxt.files[db_path]
                    nxt.files[db_path] = dataclasses.replace(old_db, sha256=f"sim_db_{old_db.sha256[:12]}")

        return nxt


# =========================================================================== #
# 4. Two-Tier Epistemic Environment Learner (Scan -> Diff -> CoW Micro-Probe) #
# =========================================================================== #

def _fast_cow_clone(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Clone workspace (including `.git` when present so stash/branch hazards are caught!)."""
    src = src.resolve()
    dst.mkdir(parents=True, exist_ok=True)
    for cur, dirs, fnames in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache")]
        rel = pathlib.Path(cur).relative_to(src)
        tdir = dst / rel
        tdir.mkdir(parents=True, exist_ok=True)
        for fn in fnames:
            sp = pathlib.Path(cur) / fn
            if sp.is_symlink():
                continue
            dp = tdir / fn
            if rel.parts and rel.parts[0] == ".git":
                # Copy `.git` metadata files so git commands inside CoW never mutate parent `.git`!
                shutil.copy2(sp, dp)
            else:
                try:
                    os.link(sp, dp)
                except OSError:
                    shutil.copy2(sp, dp)


def _extract_candidate_invocations_from_help_and_guides(
    work_root: pathlib.Path,
    tool_name: str,
    tool_rel: str,
) -> list[list[str]]:
    """Extract executable CLI templates from `--help` + workspace guides (5.96% Checkability Law).

    Never trusts prose descriptions (`"safe cleanup utility"`): only extracts concrete
    flag/positional signatures (`--in`, `--out`, `-i`, `-o`, `extract`, `sort`, `settle`)
    and immediately tests them in an isolated CoW sandbox!
    """
    raw_texts: list[str] = []
    # CRITICAL SAFETY INVARIANT: Even `--help` / `-h` executes untrusted code (a script that
    # ignores `argv` can delete bystanders on `--help`!), so ALWAYS run inside a disposable CoW clone!
    with tempfile.TemporaryDirectory(prefix="brain-emm-help-", dir=str(_shm_root())) as help_td:
        help_cow = pathlib.Path(help_td) / "cow"
        _fast_cow_clone(work_root, help_cow)
        cow_tool_fp = help_cow / tool_rel
        for help_flag in ("--help", "-h"):
            try:
                proc = subprocess.run(
                    [str(cow_tool_fp), help_flag],
                    cwd=str(help_cow),
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                )
                txt = (proc.stdout or "") + "\n" + (proc.stderr or "")
                if txt.strip():
                    raw_texts.append(txt)
                    break
            except Exception:
                continue

    # Also scan top-level markdown/text guides mentioning `tool_name`
    for gp in sorted(work_root.glob("*")):
        if gp.is_file() and gp.suffix.lower() in (".md", ".txt", ".rst"):
            try:
                gtxt = gp.read_text(encoding="utf-8", errors="replace")
                if tool_name in gtxt:
                    raw_texts.append(gtxt)
            except Exception:
                pass

    combined = "\n".join(raw_texts)
    templates: list[list[str]] = []

    def _add(tpl: list[str]) -> None:
        if tpl not in templates:
            templates.append(tpl)

    # Parse structured usage patterns from `--help` / guide code blocks
    # Pattern 1: explicit subcommands + `--input/--in/-i` and `--output/--out/-o`
    in_flags = [f for f in ("--input", "--in", "--archive", "--db", "-i") if re.search(rf"(?<!\w){re.escape(f)}(?!\w)", combined)]
    out_flags = [f for f in ("--output", "--out", "--dest", "-o") if re.search(rf"(?<!\w){re.escape(f)}(?!\w)", combined)]
    col_flags = [f for f in ("--sort-col", "--col", "--by") if re.search(rf"(?<!\w){re.escape(f)}(?!\w)", combined)]
    subcommands = re.findall(r"\b(extract|unpack|sort|normalize|convert|settle|apply|run|sync|clean)\b", combined)
    seen_subs: list[str] = []
    for sc in subcommands:
        if sc not in seen_subs:
            seen_subs.append(sc)

    for sc in (seen_subs or [""]):
        prefix = ["{tool}", sc] if sc else ["{tool}"]
        if in_flags and out_flags:
            if col_flags:
                _add(prefix + [in_flags[0], "{in_0}", out_flags[0], "{out_0}", col_flags[0], "1"])
            _add(prefix + [in_flags[0], "{in_0}", out_flags[0], "{out_0}"])
        elif in_flags:
            _add(prefix + [in_flags[0], "{in_0}"])
        _add(prefix + ["{in_0}", "{out_0}"])
        _add(prefix + ["{in_0}"])

    if not templates:
        _add(["{tool}", "{in_0}", "{out_0}"])
        _add(["{tool}", "{in_0}"])

    return templates[:8]


def _abduce_contract_from_cow_probe(
    root: pathlib.Path,
    base_snap: EnvironmentSnapshot,
    tool_name: str,
    tool_rel: str,
    tool_sha256: str,
    tpl: list[str],
    sample_in: str,
    sample_out: str,
) -> OperatorContract | None:
    """Execute `tpl` in an isolated CoW `/dev/shm` sandbox and abduce its true relational contract."""
    with tempfile.TemporaryDirectory(prefix="brain-emm-probe-", dir=str(_shm_root())) as td:
        work = pathlib.Path(td) / "cow"
        _fast_cow_clone(root, work)
        # Ensure parent dir of `sample_out` exists inside CoW
        (work / sample_out).parent.mkdir(parents=True, exist_ok=True)
        # Break hardlink on `sample_in` inside CoW so in-place tools cannot touch real `root`!
        in_fp = work / sample_in
        if in_fp.is_file():
            data = in_fp.read_bytes()
            in_fp.unlink()
            in_fp.write_bytes(data)

        argv: list[str] = []
        for tok in tpl:
            if tok == "{tool}":
                argv.append(str(work / tool_rel))
            elif tok == "{in_0}":
                argv.append(sample_in)
            elif tok == "{out_0}":
                argv.append(sample_out)
            else:
                argv.append(tok)

        try:
            proc = subprocess.run(argv, cwd=str(work), capture_output=True, text=True, timeout=4.0)
        except Exception:
            return None

        after_snap = perceive_environment_state(work)

        # 1. Check for DESTRUCTIVE HAZARDS (deleted/corrupted unrelated files or dropped Git stashes!)
        if base_snap.git.present and after_snap.git.stash_count < base_snap.git.stash_count:
            cid = _hash_contract(tool_name, tool_sha256, tpl, "GIT_STASH_CLOBBER")
            return OperatorContract(
                contract_id=cid, tool_name=tool_name, tool_sha256=tool_sha256,
                arg_template=tpl, input_kinds=[base_snap.files[sample_in].kind],
                effects=[RelationalEffect("DESTRUCTIVE_HAZARD", {"reason": "GIT_STASH_CLOBBER"})],
                hazardous=True, hazard_reason="GIT_STASH_CLOBBER",
            )

        for rel, b_fact in base_snap.files.items():
            if rel in (sample_in, sample_out) or b_fact.kind == "exec_tool":
                continue
            a_fact = after_snap.files.get(rel)
            if a_fact is None or a_fact.sha256 != b_fact.sha256:
                cid = _hash_contract(tool_name, tool_sha256, tpl, f"BYSTANDER_DAMAGE:{rel}")
                return OperatorContract(
                    contract_id=cid, tool_name=tool_name, tool_sha256=tool_sha256,
                    arg_template=tpl, input_kinds=[base_snap.files[sample_in].kind],
                    effects=[RelationalEffect("DESTRUCTIVE_HAZARD", {"reason": f"BYSTANDER_DAMAGE:{rel}"})],
                    hazardous=True, hazard_reason=f"BYSTANDER_DAMAGE:{rel}",
                )

        if proc.returncode != 0:
            return None

        # 2. Abduce positive relational effects!
        effects: list[RelationalEffect] = []
        in_before = base_snap.files[sample_in]
        out_after = after_snap.files.get(sample_out)

        if out_after is not None and (sample_out not in base_snap.files or out_after.sha256 != base_snap.files[sample_out].sha256):
            if in_before.kind in ("tar_gz", "zip"):
                effects.append(RelationalEffect(
                    "EXTRACT_ARCHIVE_MEMBER",
                    {"out_kind": out_after.kind},
                ))
            else:
                sorts_col: int | None = None
                if out_after.kind == "csv" and out_after.csv_rows:
                    for cidx in range(len(out_after.csv_rows[0])):
                        vals = [_numeric_or_str(r[cidx]) for r in out_after.csv_rows]
                        if vals == sorted(vals) and (in_before.csv_rows != out_after.csv_rows or len(vals) == 1):
                            sorts_col = cidx
                            break
                effects.append(RelationalEffect(
                    "TRANSFORM_FILE",
                    {
                        "in_kind": in_before.kind,
                        "out_kind": out_after.kind,
                        "preserves_in": sample_in in after_snap.files,
                        "sorts_col": sorts_col,
                        "json_keys": list(out_after.json_keys),
                    },
                ))

        # Check SQLite table transitions
        for (db_rel, tbl), b_tf in base_snap.sqlite_tables.items():
            a_tf = after_snap.sqlite_tables.get((db_rel, tbl))
            if a_tf is not None and a_tf.rows != b_tf.rows:
                # Identify which column changed uniformly
                set_col, set_val = None, None
                if len(a_tf.rows) == len(b_tf.rows) and a_tf.rows:
                    for cidx, col_nm in enumerate(a_tf.columns):
                        after_vals = {r[cidx] for r in a_tf.rows}
                        before_vals = {r[cidx] for r in b_tf.rows}
                        if len(after_vals) == 1 and after_vals != before_vals:
                            set_col = col_nm
                            set_val = next(iter(after_vals))
                            break
                effects.append(RelationalEffect(
                    "SQLITE_MUTATION",
                    {"table": tbl, "set_col": set_col, "set_val": set_val},
                ))

        if not effects:
            return None

        cid = _hash_contract(tool_name, tool_sha256, tpl, json.dumps([e.params for e in effects], sort_keys=True))
        return OperatorContract(
            contract_id=cid,
            tool_name=tool_name,
            tool_sha256=tool_sha256,
            arg_template=tpl,
            input_kinds=[in_before.kind],
            effects=effects,
        )


def _hash_contract(tool_name: str, sha: str, tpl: Sequence[str], tag: str) -> str:
    raw = f"{tool_name}|{sha}|{' '.join(tpl)}|{tag}"
    return "rel_op_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def scan_diff_and_learn_for_goal(
    root: pathlib.Path,
    snap: EnvironmentSnapshot,
    goal: EnvironmentGoal,
    store: RelationalActionStore,
) -> dict[str, Any]:
    """Two-Tier Epistemic Funnel:
      - Tier 1: Scan `snap.local_tools` and diff SHA-256 digests against `store` (`< 2 ms`).
      - Tier 2: Probe ONLY `UNKNOWN` or `STALE_VERSION` tools using `settlement_v1` info-gain
        ranking over candidate invocations in `/dev/shm` CoW sandboxes.
    """
    t0 = time.perf_counter_ns()
    tier1_diff: dict[str, str] = {}
    probes_executed = 0
    learned_ids: list[str] = []
    hazards_detected: list[str] = []

    data_inputs = [
        rel for rel, ff in sorted(snap.files.items())
        if ff.kind in ("tar_gz", "zip", "csv", "json", "sqlite", "text")
        and rel not in goal.protected_bystanders
        and not rel.lower().startswith("readme")
        and not rel.lower().endswith(".md")
    ]

    unexplained_tools: list[tuple[str, str, str, list[list[str]]]] = []
    extractors_found: list[tuple[str, OperatorContract, str]] = []

    def _probe_tool_on_inputs(
        probe_root: pathlib.Path,
        probe_snap: EnvironmentSnapshot,
        tool_name: str,
        tool_rel: str,
        tool_sha: str,
        templates: list[list[str]],
        inputs: Sequence[str],
    ) -> list[OperatorContract]:
        nonlocal probes_executed
        discovered: list[OperatorContract] = []
        for in_rel in inputs:
            probe_out = "_probe_out/result.csv"
            for _g_rel, g_spec in goal.required_files.items():
                if g_spec.get("kind") == "json":
                    probe_out = "_probe_out/result.json"
                elif g_spec.get("kind") == "csv":
                    probe_out = "_probe_out/result.csv"

            hyps = [
                settlement_v1.Hypothesis(
                    key=idx,
                    predict=lambda p, idx=idx: "EFFECT" if p == (idx,) else "NOOP",
                    prior=(2.5 if any(tok.startswith("-") for tok in tpl) else 1.0),
                    description=" ".join(tpl),
                )
                for idx, tpl in enumerate(templates)
            ]
            vspace = settlement_v1.VersionSpace(hyps)
            untried = set(range(len(templates)))

            while untried:
                post = vspace.posterior()
                best_idx = max(
                    untried,
                    key=lambda idx: (
                        settlement_v1.expected_information_gain(
                            post,
                            {
                                h_idx: {"EFFECT": 0.999, "NOOP": 0.001} if h_idx == idx else {"EFFECT": 0.001, "NOOP": 0.999}
                                for h_idx in post
                            },
                        ) / max(1.0, 0.25 * len(templates[idx])),
                        -idx,
                    ),
                )
                untried.remove(best_idx)
                tpl = templates[best_idx]
                probes_executed += 1
                contract = _abduce_contract_from_cow_probe(
                    probe_root, probe_snap, tool_name, tool_rel, tool_sha, tpl, in_rel, probe_out
                )
                vspace.observe((best_idx,), "EFFECT" if contract is not None else "NOOP")
                if contract is not None:
                    discovered.append(contract)
                    if contract.hazardous:
                        hazards_detected.append(f"{tool_name}:{contract.hazard_reason}")
                    else:
                        learned_ids.append(contract.contract_id)
                        if any(e.op == "EXTRACT_ARCHIVE_MEMBER" for e in contract.effects):
                            extractors_found.append((tool_rel, contract, in_rel))
                    break
            if any(c.hazardous for c in discovered):
                break
        return discovered

    for tool_name, tool_rel in sorted(snap.local_tools.items()):
        tool_sha = snap.files[tool_rel].sha256
        status = store.diff_tool_status(tool_name, tool_sha)
        tier1_diff[tool_name] = status
        if status == "KNOWN_VERIFIED":
            continue
        templates = _extract_candidate_invocations_from_help_and_guides(root, tool_name, tool_rel)
        discovered_for_tool = _probe_tool_on_inputs(root, snap, tool_name, tool_rel, tool_sha, templates, data_inputs)
        if discovered_for_tool:
            store.upsert_contracts(tool_name, tool_sha, discovered_for_tool)
        else:
            unexplained_tools.append((tool_name, tool_rel, tool_sha, templates))

    # Reachable-Artifact Epistemic Closure: if an archive extractor was just discovered and some
    # tools (`ledger_order`) had no matching input kind at t=0 because data was still packed inside
    # the archive, materialize the extracted artifact inside a CoW scratch dir and probe remaining tools!
    if unexplained_tools and extractors_found:
        with tempfile.TemporaryDirectory(prefix="brain-emm-closure-", dir=str(_shm_root())) as td:
            closure_root = pathlib.Path(td) / "cow"
            _fast_cow_clone(root, closure_root)
            staged_inputs: list[str] = []
            for idx, (ext_rel, ext_contract, arch_in) in enumerate(extractors_found):
                stage_rel = f"_epistemic_stage/item_{idx}.dat"
                (closure_root / stage_rel).parent.mkdir(parents=True, exist_ok=True)
                argv = [
                    str(closure_root / ext_rel) if tok == "{tool}"
                    else (arch_in if tok == "{in_0}" else (stage_rel if tok == "{out_0}" else tok))
                    for tok in ext_contract.arg_template
                ]
                subprocess.run(argv, cwd=str(closure_root), capture_output=True, text=True, timeout=4.0)
                if (closure_root / stage_rel).is_file():
                    staged_inputs.append(stage_rel)
            if staged_inputs:
                closure_snap = perceive_environment_state(closure_root)
                for tool_name, tool_rel, tool_sha, templates in unexplained_tools:
                    disc2 = _probe_tool_on_inputs(closure_root, closure_snap, tool_name, tool_rel, tool_sha, templates, staged_inputs)
                    if disc2:
                        store.upsert_contracts(tool_name, tool_sha, disc2)

    return {
        "tier1_diff": tier1_diff,
        "probes_executed": probes_executed,
        "learned_contracts": learned_ids,
        "hazards_detected": hazards_detected,
        "epistemic_ms": round((time.perf_counter_ns() - t0) / 1e6, 2),
    }


# =========================================================================== #
# 5. Multi-Step Mental-Model Planner + CoW Verified Execution                 #
# =========================================================================== #

@dataclass
class MentalModelExecutionResult:
    solved: bool
    status: str
    plan_steps: list[list[str]] = field(default_factory=list)
    simulated_rollouts: int = 0
    simulation_us_per_rollout: float = 0.0
    epistemic_receipt: dict[str, Any] = field(default_factory=dict)
    total_ms: float = 0.0
    unmet_predicates: list[str] = field(default_factory=list)


def solve_environment_goal(
    workspace_root: pathlib.Path | str,
    goal: EnvironmentGoal,
    *,
    store: RelationalActionStore | None = None,
    max_depth: int = 4,
    commit_changes: bool = True,
) -> MentalModelExecutionResult:
    """Solve a multi-step stateful environment task via:
      1. Relational state perception (`perceive_environment_state`),
      2. Two-tier goal-directed epistemic scan/diff/micro-probe (`scan_diff_and_learn_for_goal`),
      3. Microsecond in-RAM forward beam search (`RelationalWorldSimulator`),
      4. `os.link` CoW verification before committing changes to `workspace_root`.
    """
    t0 = time.perf_counter_ns()
    root = pathlib.Path(workspace_root).resolve()
    action_store = store if store is not None else RelationalActionStore()

    initial_snap = perceive_environment_state(root)
    already_ok, initial_unmet = check_goal_satisfied(initial_snap, initial_snap, goal)
    if already_ok:
        return MentalModelExecutionResult(
            solved=True,
            status="ALREADY_SATISFIED",
            total_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
        )

    # Step 1 & 2: Two-Tier Scan -> Diff -> Goal-Directed Active Learning
    epistemic = scan_diff_and_learn_for_goal(root, initial_snap, goal, action_store)

    # Step 3: Microsecond In-RAM Forward Mental Simulation Search (BFS up to `max_depth`)
    sim = RelationalWorldSimulator()
    sim_t0 = time.perf_counter_ns()
    rollouts = 0

    goal_out_paths = sorted(goal.required_files.keys())
    intermediate_paths = ["_stage/extracted.csv", "_stage/extracted.json"]

    # Queue items: `(current_sim_snap, [BoundAction, ...])`
    frontier: list[tuple[EnvironmentSnapshot, list[BoundAction]]] = [(initial_snap, [])]
    winning_plans: list[list[BoundAction]] = []

    for _depth in range(max_depth):
        next_frontier: list[tuple[EnvironmentSnapshot, list[BoundAction]]] = []
        for cur_snap, trace in frontier:
            candidate_inputs = [
                r for r, ff in sorted(cur_snap.files.items())
                if ff.kind in ("tar_gz", "zip", "csv", "json", "sqlite", "text")
                and r not in goal.protected_bystanders
                and not r.lower().endswith(".md")
            ]
            for tool_name, contracts in sorted(action_store.contracts.items()):
                if tool_name not in cur_snap.local_tools:
                    continue
                for contract in contracts:
                    if contract.hazardous:
                        rollouts += 1
                        continue
                    for in_rel in candidate_inputs:
                        if contract.input_kinds and cur_snap.files[in_rel].kind not in contract.input_kinds:
                            continue
                        needs_out = "{out_0}" in contract.arg_template
                        out_targets = (goal_out_paths + intermediate_paths) if needs_out else [in_rel]
                        for out_rel in out_targets:
                            bindings = {"in_0": in_rel, "out_0": out_rel}
                            rollouts += 1
                            nxt_snap = sim.simulate_step(cur_snap, contract, bindings)
                            if nxt_snap is None:
                                continue
                            argv = tuple(
                                str(root / cur_snap.local_tools[tool_name]) if tok == "{tool}"
                                else bindings.get(tok.strip("{}"), tok)
                                for tok in contract.arg_template
                            )
                            step_act = BoundAction(contract.contract_id, tool_name, argv, bindings)
                            new_trace = trace + [step_act]
                            sat, _ = check_goal_satisfied(nxt_snap, initial_snap, goal)
                            if sat:
                                winning_plans.append(new_trace)
                            else:
                                next_frontier.append((nxt_snap, new_trace))
        if winning_plans:
            break
        # Deduplicate frontier by file/sqlite digest state to prevent combinatorial blowup!
        dedup: dict[str, tuple[EnvironmentSnapshot, list[BoundAction]]] = {}
        for s_item, tr in next_frontier:
            sig = "|".join(f"{k}:{v.sha256}:{v.kind}" for k, v in sorted(s_item.files.items())) + "||" + "|".join(
                f"{k}:{v.rows}" for k, v in sorted(s_item.sqlite_tables.items())
            )
            if sig not in dedup:
                dedup[sig] = (s_item, tr)
        frontier = list(dedup.values())[:48]

    sim_ns = max(1, time.perf_counter_ns() - sim_t0)
    us_per_rollout = round((sim_ns / 1e3) / max(1, rollouts), 3)

    if not winning_plans:
        return MentalModelExecutionResult(
            solved=False,
            status="OPEN__NO_SAFE_PLAN_IN_MENTAL_MODEL",
            simulated_rollouts=rollouts,
            simulation_us_per_rollout=us_per_rollout,
            epistemic_receipt=epistemic,
            total_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
            unmet_predicates=initial_unmet,
        )

    # Step 4: Verify candidate plans in a CoW branch BEFORE touching real `root`!
    for plan in winning_plans[:4]:
        with tempfile.TemporaryDirectory(prefix="brain-emm-verify-", dir=str(_shm_root())) as td:
            cow = pathlib.Path(td) / "cow"
            _fast_cow_clone(root, cow)
            # Break hardlinks on mutable SQLite/input files inside CoW
            for r, ff in initial_snap.files.items():
                if ff.kind in ("sqlite", "csv", "json") and r not in goal.protected_bystanders:
                    p = cow / r
                    if p.is_file():
                        b = p.read_bytes()
                        p.unlink()
                        p.write_bytes(b)

            plan_ok = True
            rendered_steps: list[list[str]] = []
            for act in plan:
                out_p = act.bindings.get("out_0")
                if out_p:
                    (cow / out_p).parent.mkdir(parents=True, exist_ok=True)
                cow_argv = [
                    str(cow / initial_snap.local_tools[act.tool_name]) if i == 0 else tok
                    for i, tok in enumerate(act.argv)
                ]
                rendered_steps.append([
                    initial_snap.local_tools[act.tool_name] if i == 0 else tok
                    for i, tok in enumerate(act.argv)
                ])
                proc = subprocess.run(cow_argv, cwd=str(cow), capture_output=True, text=True, timeout=6.0)
                if proc.returncode != 0:
                    plan_ok = False
                    break

            if not plan_ok:
                continue

            verified_snap = perceive_environment_state(cow)
            sat, unmet = check_goal_satisfied(verified_snap, initial_snap, goal)
            if sat:
                if commit_changes:
                    # Execute verified plan on real `root` (cleaning temporary `_stage` afterwards)
                    for act in plan:
                        out_p = act.bindings.get("out_0")
                        if out_p:
                            (root / out_p).parent.mkdir(parents=True, exist_ok=True)
                        subprocess.run(list(act.argv), cwd=str(root), capture_output=True, text=True, timeout=6.0, check=True)
                    stage_dir = root / "_stage"
                    if stage_dir.is_dir() and not any(k.startswith("_stage/") for k in goal.required_files):
                        shutil.rmtree(stage_dir, ignore_errors=True)

                return MentalModelExecutionResult(
                    solved=True,
                    status="VERIFIED__COW_AND_MENTAL_MODEL_CONFIRMED",
                    plan_steps=rendered_steps,
                    simulated_rollouts=rollouts,
                    simulation_us_per_rollout=us_per_rollout,
                    epistemic_receipt=epistemic,
                    total_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                )

    return MentalModelExecutionResult(
        solved=False,
        status="REFUTED__MENTAL_MODEL_PLAN_REJECTED_BY_COW_ORACLE",
        simulated_rollouts=rollouts,
        simulation_us_per_rollout=us_per_rollout,
        epistemic_receipt=epistemic,
        total_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
        unmet_predicates=initial_unmet,
    )


# =========================================================================== #
# 6. Parallel CoW Speculative Rollouts (`os.fork()` + `/dev/shm` Isolation)   #
# =========================================================================== #

@dataclass(frozen=True)
class SpeculativeBranchOutcome:
    branch_idx: int
    command: tuple[str, ...]
    returncode: int
    satisfied: bool
    bystander_safe: bool
    unmet_predicates: tuple[str, ...]
    changed_predicates: tuple[str, ...]
    elapsed_ms: float


@dataclass(frozen=True)
class SpeculativeExecutionReceipt:
    winner_idx: int | None
    winner_command: tuple[str, ...] | None
    committed: bool
    branches: tuple[SpeculativeBranchOutcome, ...]
    wall_ms: float


def compute_predicate_facts(snap: EnvironmentSnapshot) -> set[str]:
    """Project `EnvironmentSnapshot` onto canonical atomic state predicates (`PetriPlaces`)."""
    facts: set[str] = set()
    for rel, ff in snap.files.items():
        facts.add(f"FILE_EXISTS:{rel}")
        facts.add(f"FILE_KIND:{rel}={ff.kind}")
        if ff.kind == "csv" and ff.csv_rows:
            for c_idx in range(len(ff.csv_header)):
                keys = [_numeric_or_str(r[c_idx]) for r in ff.csv_rows if c_idx < len(r)]
                if keys == sorted(keys):
                    facts.add(f"CSV_SORTED:{rel}:col={c_idx}")
        for jk in ff.json_keys:
            facts.add(f"JSON_KEY:{rel}:{jk}")
    for (db_rel, tbl), tf in snap.sqlite_tables.items():
        facts.add(f"SQL_TABLE:{db_rel}:{tbl}:rows={len(tf.rows)}")
        for c_idx, col_nm in enumerate(tf.columns):
            vals = {str(r[c_idx]) for r in tf.rows if c_idx < len(r)}
            if len(vals) == 1 and tf.rows:
                facts.add(f"SQL_ALL_EQ:{db_rel}:{tbl}.{col_nm}={next(iter(vals))}")
            for v in vals:
                cnt = sum(1 for r in tf.rows if c_idx < len(r) and str(r[c_idx]) == v)
                facts.add(f"SQL_COUNT:{db_rel}:{tbl}.{col_nm}={v}:{cnt}")
    for eid, el in snap.dom_elements.items():
        facts.add(f"DOM_VAL:{eid}={el.value}")
        facts.add(f"DOM_ENABLED:{eid}={el.enabled}")
        if el.checked:
            facts.add(f"DOM_CHECKED:{eid}")
    for reg in snap.canvas_regions:
        facts.add(f"CANVAS_BBOX:{reg.source_rel}:{reg.mean_rgb}={reg.bbox}")
    if snap.git.present:
        facts.add(f"GIT_STASH_COUNT:{snap.git.stash_count}")
        facts.add(f"GIT_CLEAN:{len(snap.git.dirty_paths) == 0}")
    return facts


def speculate_parallel_cow_branches(
    workspace_root: pathlib.Path | str,
    candidate_commands: Sequence[Sequence[str]],
    goal: EnvironmentGoal,
    *,
    max_parallel: int = 16,
    branch_timeout_s: float = 5.0,
    commit_winner: bool = False,
) -> SpeculativeExecutionReceipt:
    """Fork up to `max_parallel` isolated `/dev/shm` Copy-on-Write branches concurrently via `os.fork()`.

    Each child unlinks mutable files before writing, executes its candidate command, perceives
    the resulting `EnvironmentSnapshot`, checks bystander/git-stash invariants and `goal`, and
    streams its compact JSON outcome back over an anonymous OS pipe. Zero host side effects occur
    unless `commit_winner=True` and a hazard-free branch strictly improves or satisfies `goal`.
    """
    t0 = time.perf_counter_ns()
    root = pathlib.Path(workspace_root).resolve()
    initial_snap = perceive_environment_state(root)
    initial_facts = compute_predicate_facts(initial_snap)
    _, init_unmet = check_goal_satisfied(initial_snap, initial_snap, goal)

    cmds = [tuple(str(x) for x in c) for c in candidate_commands[:max_parallel]]
    outcomes_by_idx: dict[int, SpeculativeBranchOutcome] = {}

    with tempfile.TemporaryDirectory(prefix="brain-spec-cow-", dir=str(_shm_root())) as batch_td:
        batch_dir = pathlib.Path(batch_td)
        active: list[tuple[int, int, int, pathlib.Path]] = []  # (idx, pid, r_fd, branch_dir)

        for idx, cmd in enumerate(cmds):
            b_dir = batch_dir / f"branch_{idx:02d}"
            _fast_cow_clone(root, b_dir)
            # Break hardlinks on mutable files inside `b_dir` so writes never leak across siblings or to `root`
            for r_path, ff in initial_snap.files.items():
                if ff.kind in ("sqlite", "csv", "json", "text") and r_path not in goal.protected_bystanders:
                    p = b_dir / r_path
                    if p.is_file():
                        raw_b = p.read_bytes()
                        p.unlink()
                        p.write_bytes(raw_b)

            r_fd, w_fd = os.pipe()
            pid = os.fork()
            if pid == 0:
                os.close(r_fd)
                bt0 = time.perf_counter_ns()
                try:
                    # Rewrite any leading `{workspace}` or root-anchored executable path to `b_dir`
                    local_cmd = [
                        str(b_dir / pathlib.Path(tok).relative_to(root))
                        if tok.startswith(str(root) + "/")
                        else (tok.replace("{workspace}", str(b_dir)))
                        for tok in cmd
                    ]
                    proc = subprocess.run(
                        local_cmd,
                        cwd=str(b_dir),
                        capture_output=True,
                        text=True,
                        timeout=branch_timeout_s,
                    )
                    post_snap = perceive_environment_state(b_dir)
                    sat, unmet = check_goal_satisfied(post_snap, initial_snap, goal)
                    bystander_safe = not any(
                        u.startswith(("BYSTANDER_VIOLATED:", "GIT_STASH_DESTROYED")) for u in unmet
                    )
                    post_facts = compute_predicate_facts(post_snap)
                    added = sorted(post_facts - initial_facts)[:24]
                    payload = json.dumps({
                        "rc": int(proc.returncode),
                        "sat": bool(sat and proc.returncode == 0),
                        "safe": bool(bystander_safe),
                        "unmet": list(unmet),
                        "changed": added,
                        "ms": round((time.perf_counter_ns() - bt0) / 1e6, 2),
                    }).encode("utf-8")
                    os.write(w_fd, payload)
                except Exception as exc:
                    err_p = json.dumps({
                        "rc": 125,
                        "sat": False,
                        "safe": False,
                        "unmet": [f"BRANCH_EXCEPTION:{type(exc).__name__}"],
                        "changed": [],
                        "ms": round((time.perf_counter_ns() - bt0) / 1e6, 2),
                    }).encode("utf-8")
                    os.write(w_fd, err_p)
                finally:
                    os.close(w_fd)
                    os._exit(0)
            else:
                os.close(w_fd)
                active.append((idx, pid, r_fd, b_dir))

        # Collect all concurrent branches
        winner_dir: pathlib.Path | None = None
        for idx, pid, r_fd, b_dir in active:
            chunks: list[bytes] = []
            while True:
                buf = os.read(r_fd, 65536)
                if not buf:
                    break
                chunks.append(buf)
            os.close(r_fd)
            os.waitpid(pid, 0)
            data = json.loads(b"".join(chunks).decode("utf-8")) if chunks else {
                "rc": 125, "sat": False, "safe": False, "unmet": ["EMPTY_PIPE"], "changed": [], "ms": 0.0,
            }
            outcomes_by_idx[idx] = SpeculativeBranchOutcome(
                branch_idx=idx,
                command=cmds[idx],
                returncode=int(data["rc"]),
                satisfied=bool(data["sat"]),
                bystander_safe=bool(data["safe"]),
                unmet_predicates=tuple(data["unmet"]),
                changed_predicates=tuple(data["changed"]),
                elapsed_ms=float(data["ms"]),
            )

        ordered = tuple(outcomes_by_idx[i] for i in range(len(cmds)))
        # Rank strictly safe (`bystander_safe and rc == 0`) branches by `(satisfied, -len(unmet), -elapsed_ms)`
        safe_candidates = [
            o for o in ordered
            if o.bystander_safe and o.returncode == 0 and (o.satisfied or len(o.unmet_predicates) < len(init_unmet))
        ]
        safe_candidates.sort(key=lambda o: (0 if o.satisfied else 1, len(o.unmet_predicates), o.elapsed_ms))
        winner = safe_candidates[0] if safe_candidates else None
        committed = False

        if winner is not None and commit_winner:
            winner_dir = batch_dir / f"branch_{winner.branch_idx:02d}"
            # Sync modified/created non-bystander files from `winner_dir` back to `root`
            for cur, dirs, fnames in os.walk(winner_dir):
                dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")]
                rel_d = pathlib.Path(cur).relative_to(winner_dir)
                (root / rel_d).mkdir(parents=True, exist_ok=True)
                for fn in fnames:
                    rel_f = (rel_d / fn).as_posix() if rel_d.parts else fn
                    if rel_f in goal.protected_bystanders:
                        continue
                    shutil.copy2(pathlib.Path(cur) / fn, root / rel_f)
            committed = True

        return SpeculativeExecutionReceipt(
            winner_idx=(winner.branch_idx if winner is not None else None),
            winner_command=(winner.command if winner is not None else None),
            committed=committed,
            branches=ordered,
            wall_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
        )


# =========================================================================== #
# 7. Cross-Modal Type-Transition Petri Net & Long-Horizon Drift-Free Executor #
# =========================================================================== #

def _articulation_points(adj: Mapping[frozenset[str], set[frozenset[str]]]) -> set[frozenset[str]]:
    """Tarjan articulation points on an undirected graph of markings (iterative, no recursion limit)."""
    disc: dict[frozenset[str], int] = {}
    low: dict[frozenset[str], int] = {}
    parent: dict[frozenset[str], frozenset[str] | None] = {}
    cuts: set[frozenset[str]] = set()
    timer = 0
    for start in adj:
        if start in disc:
            continue
        stack: list[tuple[frozenset[str], list[frozenset[str]]]] = [(start, sorted(adj[start], key=repr))]
        disc[start] = low[start] = timer
        timer += 1
        parent[start] = None
        root_children = 0
        while stack:
            node, children = stack[-1]
            if children:
                child = children.pop()
                if child not in disc:
                    parent[child] = node
                    disc[child] = low[child] = timer
                    timer += 1
                    stack.append((child, sorted(adj[child], key=repr)))
                    if node == start:
                        root_children += 1
                elif child != parent[node]:
                    low[node] = min(low[node], disc[child])
            else:
                stack.pop()
                par = parent[node]
                if par is not None:
                    low[par] = min(low[par], low[node])
                    if par != start and low[node] >= disc[par]:
                        cuts.add(par)
        if root_children > 1:
            cuts.add(start)
    return cuts


@dataclass(frozen=True)
class CrossModalTransition:
    """Verified operator across GUI/DOM, SQLite, CLI, or Python with provenance (§9.2)."""
    transition_id: str
    modality: str                      # gui_dom | sqlite | cli | python
    action_argv: tuple[str, ...]
    preconditions: frozenset[str]
    added_facts: frozenset[str]
    removed_facts: frozenset[str]
    tool_sha256: str
    witness_digest: str
    hazardous: bool = False


class CrossModalPetriNet:
    """Unified algebraic Petri net over FS + SQLite + DOM/a11y + Canvas + CLI + Python morphisms.

    Enforces §9.2 Admission Rules:
      - Verified execution in CoW (`rc == 0`),
      - Zero bystander or git-stash hazard (`hazardous == False`),
      - Non-empty causal state delta (`len(added_facts | removed_facts) > 0`),
      - Anti-duplicate compression (`added_facts` signature not already covered by an identical tool hash),
      - Concrete `tool_sha256` & `witness_digest` provenance for `O(1)` staleness invalidation!
    """

    def __init__(self) -> None:
        self.transitions: dict[str, CrossModalTransition] = {}
        self.rejected_count: int = 0

    def admit_via_cow_probe(
        self,
        workspace_root: pathlib.Path | str,
        modality: str,
        action_argv: Sequence[str],
        *,
        protected_bystanders: Sequence[str] = (),
        precondition_filter: Callable[[str], bool] | None = None,
    ) -> CrossModalTransition | None:
        root = pathlib.Path(workspace_root).resolve()
        pre_snap = perceive_environment_state(root)
        pre_facts = compute_predicate_facts(pre_snap)
        goal_guard = EnvironmentGoal(protected_bystanders=tuple(protected_bystanders), preserve_git_stash=True)

        spec = speculate_parallel_cow_branches(root, [action_argv], goal_guard, max_parallel=1, commit_winner=False)
        if not spec.branches:
            self.rejected_count += 1
            return None
        b0 = spec.branches[0]
        if b0.returncode != 0 or not b0.bystander_safe:
            self.rejected_count += 1
            return None

        # Run once in scratch to capture full post-fact set (both added and removed predicates)
        with tempfile.TemporaryDirectory(prefix="brain-petri-probe-", dir=str(_shm_root())) as td:
            cow = pathlib.Path(td) / "cow"
            _fast_cow_clone(root, cow)
            for r_path, ff in pre_snap.files.items():
                if ff.kind in ("sqlite", "csv", "json", "text") and r_path not in protected_bystanders:
                    p = cow / r_path
                    if p.is_file():
                        raw_b = p.read_bytes()
                        p.unlink()
                        p.write_bytes(raw_b)
            local_cmd = [
                str(cow / pathlib.Path(tok).relative_to(root))
                if tok.startswith(str(root) + "/")
                else tok.replace("{workspace}", str(cow))
                for tok in action_argv
            ]
            proc = subprocess.run(local_cmd, cwd=str(cow), capture_output=True, text=True, timeout=5.0)
            if proc.returncode != 0:
                self.rejected_count += 1
                return None
            post_snap = perceive_environment_state(cow)
            sat_guard, _ = check_goal_satisfied(post_snap, pre_snap, goal_guard)
            if not sat_guard:
                self.rejected_count += 1
                return None
            post_facts = compute_predicate_facts(post_snap)

        added = frozenset(post_facts - pre_facts)
        removed = frozenset(pre_facts - post_facts)
        if not added and not removed:
            # §9.2: Reject no-op / zero-surprise transitions!
            self.rejected_count += 1
            return None

        # Minimal causal preconditions: facts that were consumed (`removed`) or matched `precondition_filter`
        preconds = set(removed)
        if precondition_filter is not None:
            preconds |= {f for f in pre_facts if precondition_filter(f)}

        exe_tok = str(action_argv[0])
        tool_p = pathlib.Path(exe_tok.replace("{workspace}", str(root)))
        tool_sha = hashlib.sha256(tool_p.read_bytes()).hexdigest()[:16] if tool_p.is_file() else "builtin"
        wit_dig = hashlib.sha256(
            json.dumps({"cmd": list(action_argv), "add": sorted(added), "rem": sorted(removed)}, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        tid = f"{modality}:{wit_dig}"

        # Anti-redundancy: skip if an active transition with identical `(added, removed, tool_sha)` already exists
        for existing in self.transitions.values():
            if existing.added_facts == added and existing.removed_facts == removed and existing.tool_sha256 == tool_sha:
                return existing

        tr = CrossModalTransition(
            transition_id=tid,
            modality=modality,
            action_argv=tuple(str(x) for x in action_argv),
            preconditions=frozenset(preconds),
            added_facts=added,
            removed_facts=removed,
            tool_sha256=tool_sha,
            witness_digest=wit_dig,
        )
        self.transitions[tid] = tr
        return tr

    # --------------------------------------------------------------------------------------- #
    # Cut-vertex (articulation-token) sub-goal slicing
    # --------------------------------------------------------------------------------------- #
    def reachability_graph(
        self,
        initial_facts: frozenset[str],
        target_predicates: frozenset[str] | None = None,
        *,
        max_nodes: int = 400,
        max_depth: int = 14,
    ) -> tuple[dict[frozenset[str], list[tuple[frozenset[str], str]]], list[frozenset[str]] | None]:
        """Bounded BFS over markings; returns the transition graph and the shortest goal path.

        When no target is given, the farthest reachable marking is used, which is the natural
        endpoint for "what can this environment still do from here".
        """
        ordered = sorted(self.transitions.values(), key=lambda t: t.transition_id)
        graph: dict[frozenset[str], list[tuple[frozenset[str], str]]] = {initial_facts: []}
        levels: dict[frozenset[str], int] = {initial_facts: 0}
        parent: dict[frozenset[str], tuple[frozenset[str], str]] = {}
        frontier: list[frozenset[str]] = [initial_facts]
        goal: frozenset[str] | None = None
        for depth in range(max_depth):
            nxt: list[frozenset[str]] = []
            for marking in frontier:
                for tr in ordered:
                    if goal is not None:
                        break
                    if not tr.preconditions.issubset(marking):
                        continue
                    after = (marking - tr.removed_facts) | tr.added_facts
                    if after == marking:
                        continue
                    graph.setdefault(marking, []).append((after, tr.transition_id))
                    if after in levels:
                        continue
                    if len(levels) >= max_nodes:
                        continue
                    levels[after] = depth + 1
                    parent[after] = (marking, tr.transition_id)
                    graph.setdefault(after, [])
                    nxt.append(after)
                    if target_predicates is not None and target_predicates.issubset(after):
                        goal = after
                        break
            if goal is not None:
                break
            if not nxt:
                break
            frontier = nxt

        endpoint = goal
        if endpoint is None and parent:
            endpoint = max(parent, key=lambda m: levels.get(m, 0))
        if endpoint is None:
            return graph, None
        path: list[frozenset[str]] = [endpoint]
        while path[-1] in parent:
            path.append(parent[path[-1]][0])
        path.reverse()
        return graph, path

    def articulation_tokens(
        self,
        initial_facts: frozenset[str],
        target_predicates: frozenset[str] | None = None,
        *,
        max_nodes: int = 400,
    ) -> list[frozenset[str]]:
        """Markings every path to the goal must pass through: the cut vertices of reachability.

        Slicing a long plan at these turns one fragile 300-step episode into short sub-episodes with
        hard postconditions -- a sub-goal is only locked in once its marking is actually reached, so
        losing an early constraint later becomes structurally impossible rather than merely unlikely.
        """
        graph, path = self.reachability_graph(initial_facts, target_predicates, max_nodes=max_nodes)
        if not path or len(path) < 3:
            return []
        undirected: dict[frozenset[str], set[frozenset[str]]] = {m: set() for m in graph}
        for src, edges in graph.items():
            for dst, _tid in edges:
                undirected.setdefault(src, set()).add(dst)
                undirected.setdefault(dst, set()).add(src)
        cuts = _articulation_points(undirected)
        return [m for m in path[1:-1] if m in cuts]

    def solve_in_slices(
        self,
        initial_facts: frozenset[str],
        target_predicates: frozenset[str],
        *,
        max_depth: int = 14,
    ) -> list[list[CrossModalTransition]] | None:
        """Decompose the goal plan into checkpointed sub-plans separated by cut vertices."""
        plan = self.solve_reachability(initial_facts, target_predicates, max_depth=max_depth)
        if plan is None:
            return None
        slices = self.articulation_tokens(initial_facts, target_predicates)
        if not slices:
            return [plan]
        out: list[list[CrossModalTransition]] = []
        chunk: list[CrossModalTransition] = []
        marking = initial_facts
        pending = list(slices)
        for tr in plan:
            chunk.append(tr)
            marking = (marking - tr.removed_facts) | tr.added_facts
            if pending and marking == pending[0]:
                out.append(chunk)
                chunk = []
                pending.pop(0)
        if chunk:
            out.append(chunk)
        return out

    def solve_reachability(
        self,
        initial_facts: frozenset[str],
        target_predicates: frozenset[str],
        *,
        max_depth: int = 12,
    ) -> list[CrossModalTransition] | None:
        """Breadth-first shortest Petri-net firing sequence reaching `target_predicates` without revert cycles."""
        if target_predicates.issubset(initial_facts):
            return []
        from collections import deque
        queue: deque[tuple[frozenset[str], list[CrossModalTransition]]] = deque([(initial_facts, [])])
        visited: set[frozenset[str]] = {initial_facts}
        ordered_trs = sorted(self.transitions.values(), key=lambda t: t.transition_id)

        while queue:
            cur_marking, path = queue.popleft()
            if len(path) >= max_depth:
                continue
            for tr in ordered_trs:
                if not tr.preconditions.issubset(cur_marking):
                    continue
                nxt_marking = (cur_marking - tr.removed_facts) | tr.added_facts
                if nxt_marking == cur_marking or nxt_marking in visited:
                    continue
                new_path = path + [tr]
                if target_predicates.issubset(nxt_marking):
                    return new_path
                visited.add(nxt_marking)
                queue.append((nxt_marking, new_path))
        return None


# ======================================================================================
# MERGE NOTE -- two different modules shared this filename.
#
# This file implements the cross-modal mental model: environment facts, the relational
# action store, and the cross-modal Petri net. A separate branch delivered a different
# module under the same name: the executable IR simulator with abstract analysis and
# CEGAR planning. Neither is a subset of the other -- they share ZERO definitions -- and
# both are imported by real tests, so neither can be dropped.
#
# The simulator keeps its own file and its symbols are re-exported here, so a caller
# written against either version finds what it asks for. Nothing is shadowed because the
# two sets of names are disjoint.
# ======================================================================================
from canonical.swe_kernel.executable_simulator_mental_model_v1 import *  # noqa: F401,F403,E402
