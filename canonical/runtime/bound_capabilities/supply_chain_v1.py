# PROJECT_BRAIN
"""python.supply_chain.{secret_scan,vulnerability_audit}.v1 — the two acts the inventory caught
being answered by a tool that had no business answering them.

Measured before this module existed, through the front door:

    "Scan the repository R for leaked secrets"                 -> python.toolchain.bandit_security.v1 PASS
    "Audit the dependencies in R for known vulnerabilities"    -> python.toolchain.bandit_security.v1 PASS

Both were counted as answered.  Measured directly on a fixture with four planted credentials,
bandit reported 2 of 4 and the two it missed are the interesting ones:

    AKIA…  in AWS_ACCESS_KEY_ID   NOT REPORTED   (detection is by VARIABLE NAME, not credential shape)
    xoxb-… in SLACK               NOT REPORTED
    hunter2 in DB_PASSWORD        reported       B105 hardcoded_password_string
    ghp_…   in TOKEN              reported       B105 hardcoded_password_string

and for the audit there was no advisory data anywhere in the machine: bandit is a code-pattern
scanner, so "audit dependencies for vulnerabilities" was 0/0 — nothing to be right about.

The answer is not to write another scanner.  It is to use the two tools that already are the answer,
which the owner's rule names explicitly ("already solved ... hidden as tools"):

    detect-secrets (Yelp)  27 detectors + entropy, per-provider regexes, hashed findings
    pip-audit               PyPI advisory service, PYSEC ids, fix versions, aliases to CVE/GHSA

Both are on PyPI and both are DECLARED in `canonical/runtime/TOOLCHAIN_DECLARATION_V1.json`, so
`toolchain_preflight_v1.py --bootstrap` installs them and `--check` refuses when they are missing.
That is the same install-or-refuse law the analysers already obey; a capability whose tool is absent
must say so, not report an empty success.

Laws of this module:

* **a secret is never written down.** detect-secrets reports a salted SHA-1 of the secret; the
  artifact carries that hash and the location, never the plaintext.  A scanner that saves the
  credential it found has created a second leak.
* **an empty report from a tool that did not run is a lie.**  If the scanner or the advisory
  service is unreachable, the verb refuses (`TOOL_NOT_INSTALLED`, `ADVISORY_SERVICE_UNREACHABLE`)
  and writes a FAIL artifact.  Only a real run may report zero findings.
* **findings are counted by shape, not by nickname.** the artifact groups findings by detector, so
  "the AWS key detector fired" and "a high-entropy string was found" cannot be confused.
* dependencies to audit come from the project itself — the same manifest parser
  `packaging_v1`/`environment_fit_v1` already use — and a stated `requirements_path` overrides it.

Inputs (kwargs, repo-confined):
  source_root        the project/repository directory
  requirements_path  optional stated requirements file (vulnerability_audit only)
  output_path        summary artifact
  python_executable  the interpreter whose toolchain runs the tool
  timeout_s

result_fields: adapter, capability_id, act, target, gate, complete, output_path, output_sha256,
output_verified, and per-act findings.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from canonical.runtime.bound_capabilities.packaging_v1 import (
    _dependency_block,
    _requirement_name,
    _requirements_lines,
)
from canonical.runtime.bound_capabilities.quality_v1 import (
    QualityError,
    _base,
    _destination,
    _fail,
    _inside,
    _write,
)

SECRET_CAP = "python.supply_chain.secret_scan.v1"
AUDIT_CAP = "python.supply_chain.vulnerability_audit.v1"
DEFAULT_TIMEOUT_S = 300


def _tool_available(python_exe: str, module: str, timeout_s: int) -> bool:
    proc = subprocess.run([python_exe, "-c", "import " + module], capture_output=True, text=True,
                          timeout=timeout_s, check=False)
    return proc.returncode == 0


def _run(argv: list[str], cwd: Path, timeout_s: int) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # a spinner or a progress bar in captured output is not a finding
    env.setdefault("PYTHONWARNINGS", "ignore")
    try:
        return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                              timeout=timeout_s, env=env, check=False)
    except subprocess.TimeoutExpired:
        _fail("TIMEOUT:" + Path(argv[0]).name)


def _target(args, root: Path) -> Path:
    stated = str(args.get("source_root") or args.get("path") or "").strip()
    if not stated:
        _fail("PATH_NOT_STATED")
    located = _inside(root, stated)
    if located is None:
        _fail("PATH_NOT_IN_THE_REPOSITORY:" + stated)
    return located


# --------------------------------------------------------------------------- secret_scan

def _self_exclusion(target: Path, artifact: Path | None) -> list[str]:
    """argv that keep the scanner from reading the report it is about to write.

    Measured: two runs in a row disagreed -- the first artifact carries 40-character salted
    hashes, the second scan reported five `Hex High Entropy String` findings on its own output.
    A report is not evidence of a secret, and a scanner that reads its own findings is a
    feedback loop, not an instrument.
    """
    if artifact is None:
        return []
    try:
        relative = artifact.resolve().relative_to(target.resolve())
    except (ValueError, OSError):
        return []
    return ["--exclude-files", r"(^|/)" + str(relative).replace(os.sep, "/") + "$"]


def _secret_scan(args, root: Path, cap: str, artifact: Path | None = None) -> dict:
    """detect-secrets over the tree.  Real detectors, hashed findings, no plaintext anywhere."""
    target = _target(args, root)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    if not _tool_available(python_exe, "detect_secrets", timeout_s):
        _fail("TOOL_NOT_INSTALLED:detect-secrets")
    # `--all-files` is what makes this a scan of the TREE rather than of git's index: measured
    # without it, a directory of planted credentials reported {} because none was staged.
    proc = _run([python_exe, "-m", "detect_secrets", "scan", "--all-files", "--no-verify"]
                + _self_exclusion(target, artifact), target, timeout_s)
    text = (proc.stdout or "").strip()
    if not text:
        _fail("TOOL_FAILED:detect-secrets:" + (proc.stderr or "no output").strip()[:200])
    try:
        report = json.loads(text)
    except ValueError:
        _fail("TOOL_OUTPUT_UNPARSEABLE:detect-secrets")
    if "results" not in report:
        _fail("TOOL_OUTPUT_UNPARSEABLE:detect-secrets:no_results_key")
    findings = []
    for filename, hits in sorted((report.get("results") or {}).items()):
        for hit in hits:
            findings.append({
                "path": filename,
                "line": hit.get("line_number"),
                "detector": hit.get("type"),
                # the HASH, never the secret: detect-secrets reports a salted SHA-1, and this
                # artifact exists to be shared
                "secret_sha1": hit.get("hashed_secret"),
                "verified_against_provider": bool(hit.get("is_verified")),
            })
    by_detector: dict[str, int] = {}
    for finding in findings:
        detector = str(finding["detector"])
        by_detector[detector] = by_detector.get(detector, 0) + 1
    payload = _base(cap, "secret_scan", target)
    payload.update({
        "files_with_findings": len({f["path"] for f in findings}),
        "finding_count": len(findings),
        "findings_by_detector": by_detector,
        "findings": findings[:200],
        "tool": "detect-secrets " + str(report.get("version") or ""),
        "detectors_enabled": len(report.get("plugins_used") or []),
        "secrets_written_to_this_artifact": False,
        "law": ("detect-secrets' detectors run over every file in the tree (not only the staged "
                "ones); findings are recorded as salted hashes with their location, never as "
                "plaintext, because a report that quotes the credential is a second leak"),
        "complete": True,
    })
    return payload


# --------------------------------------------------------------------------- vulnerability_audit

def _declared_requirements(project: Path, stated: str | None) -> tuple[list[str], str]:
    """The requirements to audit, and where they came from.  Reuses the manifest parser."""
    if stated:
        path = project / stated if not Path(stated).is_absolute() else Path(stated)
        if not path.is_file():
            _fail("REQUIREMENTS_FILE_NOT_FOUND:" + stated)
        return _requirements_lines(path.read_text(encoding="utf-8")), str(path.name)
    pyproject = project / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        span = _dependency_block(text)
        if span is not None:
            block = text[span[0]:span[1]]
            inner = block[block.index("[") + 1:block.rindex("]")]
            specs = []
            for line in inner.replace("\n", " ").split(","):
                cleaned = line.split("#", 1)[0].strip().strip('"').strip("'")
                if cleaned:
                    specs.append(cleaned)
            if specs:
                return specs, "pyproject.toml"
    for name in ("requirements.txt", "requirements-dev.txt"):
        candidate = project / name
        if candidate.is_file():
            return _requirements_lines(candidate.read_text(encoding="utf-8")), name
    _fail("NO_DECLARED_DEPENDENCIES:" + str(project))


def _vulnerability_audit(args, root: Path, cap: str) -> dict:
    """pip-audit against the PyPI advisory service, over the project's own declared set."""
    target = _target(args, root)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    if not _tool_available(python_exe, "pip_audit", timeout_s):
        _fail("TOOL_NOT_INSTALLED:pip-audit")
    project = target if target.is_dir() else target.parent
    stated = str(args.get("requirements_path") or "").strip() or None
    specs, source_name = _declared_requirements(project, stated)
    if not specs:
        _fail("NO_DECLARED_DEPENDENCIES:" + source_name)
    with tempfile.TemporaryDirectory(prefix="brain_audit_") as tmp:
        requirements = Path(tmp) / "requirements.txt"
        requirements.write_text("\n".join(specs) + "\n", encoding="utf-8")
        proc = _run([python_exe, "-m", "pip_audit", "-r", str(requirements),
                     "--format", "json", "--progress-spinner", "off"], project, timeout_s)
    stderr = (proc.stderr or "").strip()
    # pip-audit exits 1 when it FOUND vulnerabilities, 0 when it found none, and 2/3-or-more with
    # an ERROR line when it could not do the job at all.  An unreachable advisory service and a
    # clean bill of health must never read the same -- that was the whole defect this replaces.
    if proc.returncode not in (0, 1):
        _fail("ADVISORY_SERVICE_UNREACHABLE:pip-audit:" + (stderr or "no detail")[:240])
    if "ERROR" in stderr and not (proc.stdout or "").strip():
        _fail("ADVISORY_SERVICE_UNREACHABLE:pip-audit:" + stderr[:240])
    try:
        report = json.loads((proc.stdout or "").strip() or "{}")
    except ValueError:
        _fail("TOOL_OUTPUT_UNPARSEABLE:pip-audit")
    rows = []
    dependencies = report.get("dependencies") or []
    for dependency in dependencies:
        for vuln in dependency.get("vulns") or []:
            rows.append({
                "package": dependency.get("name"),
                "version": dependency.get("version"),
                "id": vuln.get("id"),
                "fix_versions": list(vuln.get("fix_versions") or []),
                "aliases": list(vuln.get("aliases") or []),
                "summary": str(vuln.get("description") or "")[:240],
            })
    by_package: dict[str, int] = {}
    for row in rows:
        by_package[str(row["package"])] = by_package.get(str(row["package"]), 0) + 1
    payload = _base(cap, "vulnerability_audit", target)
    payload.update({
        "requirements_source": source_name,
        "requirements_audited": specs[:50],
        "packages_audited": len(dependencies),
        "vulnerable_packages": len(by_package),
        "vulnerability_count": len(rows),
        "vulnerabilities_by_package": by_package,
        "vulnerabilities": rows[:200],
        "advisory_service": "pypi (pip-audit)",
        "tool": "pip-audit",
        "law": ("the declared dependency set is resolved and checked against the PyPI advisory "
                "service; each finding carries its PYSEC id, its CVE/GHSA aliases and the "
                "versions that fix it; a run that could not reach the service refuses instead of "
                "reporting zero"),
        "complete": True,
    })
    return payload


_HANDLERS = {
    "secret_scan": (_secret_scan, SECRET_CAP),
    "vulnerability_audit": (_vulnerability_audit, AUDIT_CAP),
}


def run(args: dict, root) -> dict:
    root = Path(root)
    args = dict(args or {})
    verb = str(args.get("act_verb") or args.get("act") or "").strip()
    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        _fail("OUTPUT_PATH_NOT_STATED")
    destination = _destination(root, output_path)
    capability_id = str(args.get("capability_id") or "").strip()
    try:
        if verb not in _HANDLERS:
            _fail("ACT_NOT_SUPPORTED:" + (verb or "<none>"))
        handler, default_cap = _HANDLERS[verb]
        capability_id = capability_id or default_cap
        payload = handler(args, root, capability_id, destination) if verb == "secret_scan" \
            else handler(args, root, capability_id)
    except QualityError as exc:
        _write(destination, {"adapter": "supply_chain_v1", "capability_id": capability_id,
                             "act": verb, "gate": "FAIL", "reason": str(exc)})
        raise
    written = _write(destination, payload)
    return {
        "adapter": "supply_chain_v1",
        "capability_id": capability_id,
        "act": verb,
        "target": payload.get("target"),
        "finding_count": payload.get("finding_count", payload.get("vulnerability_count")),
        **({"vulnerability_count": payload["vulnerability_count"]}
           if verb == "vulnerability_audit" else {"files_with_findings":
                                                  payload["files_with_findings"]}),
        "gate": "PASS",
        "complete": True,
        "output_path": output_path,
        "output_sha256": written.get("artifact_sha256"),
        "output_verified": json.loads(Path(destination).read_text(encoding="utf-8"))[
            "artifact_sha256"] == written.get("artifact_sha256"),
        "verified": True,
        **({"findings_by_detector": payload["findings_by_detector"]} if verb == "secret_scan" else {}),
        **({"vulnerable_packages": payload["vulnerable_packages"]}
           if verb == "vulnerability_audit" else {}),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--act_verb", required=True, choices=sorted(_HANDLERS))
    parser.add_argument("--source_root", required=True)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--requirements_path", default=None)
    parser.add_argument("--timeout_s", type=int, default=None)
    ns = parser.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
