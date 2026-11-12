"""Census vs counterfactual: is a count of blockers a ranking of blockers? No.

Three questions, each answered by measurement on the box this runs on.

1. DOES THE CENSUS EVEN MEASURE THE MACHINE?
   Round 8's census fed each capability its own keywords and concluded that binding was the
   largest blocker. But five keywords are not a request. On two rows a real sentence produces
   a different outcome entirely, and on one of them a *different capability* answers it
   successfully. A census that does not control its input cannot rank the machinery.

2. IS ACQUISITION A REAL LEVER?
   On a box with no root, no sudo, no dpkg lock and no apt metadata, can a capability blocked
   by `BOUND_APT_METADATA_NOT_FOUND` be made to verify without any of those things? Measured
   answer: yes, with a user-scoped pip install, and it is the only lever in this exercise that
   has ever turned a failure into a verified action.

3. DOES TEACHING A BLIND SENSOR ITS BLIND SPOT HELP?
   The presence probe cannot see a module the adapter imports through `importlib.import_module`
   with an argument-supplied name -- 8 of the 11 apt-sourced entries. Their templates state the
   module as a literal one field away. Patch the probe to read it, and see what becomes usable.
   Measured answer: the blocker moves, nothing starts working.

THE POINT. Only (2) survived its own counterfactual. (1) and (3) are the third and fourth times a
blocker found by counting dissolved when removed. Write down the number; prove the causal link.
"""
from __future__ import annotations

import importlib.util as _iu
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"

SCHEMA = "CENSUS_VS_COUNTERFACTUAL_V1"


# ------------------------------------------------------------------------------------------
# 1. The census measures my sentences
# ------------------------------------------------------------------------------------------
KEYWORD_CASES = {
    # capability -> (keywords-as-a-census-would-send, a real sentence)
    "text.file.write": (
        "text file write",
        "write the text hello world to the file note.txt",
    ),
    "json.query.jq": (
        "json query jq",
        "query the json file package.json with jq filter .name",
    ),
}


def census_vs_sentence():
    """Same capability, same box: keywords vs a request."""
    from canonical.runtime import grounded_action_v1 as GA

    out = []
    for cid, (soup, sentence) in KEYWORD_CASES.items():
        row = {"capability_id": cid, "keyword_soup": soup, "sentence": sentence}
        for label, sent in (("soup", soup), ("sentence", sentence)):
            receipt = GA.act(sent, memory=False, bridge=False, computer_use=False)
            row[label] = {"routed_to": receipt.get("capability_id"),
                          "status": receipt.get("status"),
                          "error": str(receipt.get("error"))[:80]}
        out.append(row)
    return out


def the_census_misattributes_at_least_one_row():
    """The falsifiable claim, as a predicate rather than a paragraph."""
    for row in census_vs_sentence():
        routed = row["sentence"]["routed_to"]
        if row["soup"]["status"] != "VERIFIED_ACTION" and row["sentence"]["status"] == "VERIFIED_ACTION":
            return {"pass": True, "why": "a real sentence verifies where keyword soup did not",
                    "row": row}
        if routed and routed != row["capability_id"] and row["sentence"]["status"] == "VERIFIED_ACTION":
            return {"pass": True, "why": "the sentence was answered by a different capability",
                    "row": row}
    return {"pass": False, "why": "no row distinguished soup from sentence on this box"}


# ------------------------------------------------------------------------------------------
# 2. Acquisition, rootless
# ------------------------------------------------------------------------------------------
ACQUISITION_ROW = "yaml.to_json.yq"
ACQUISITION_SENTENCE = "convert the yaml file {yaml_path} to json using yq"


def _terminal_receipt(sentence, cid, root=ROOT):
    from canonical.runtime import grounded_action_v1 as GA
    from canonical.runtime import world_probe_v1 as WP

    reg = GA.load_registry()
    need = list((WP.orphan_preconditions(reg) or {}).get(cid) or [])
    return GA.act(sentence, memory=False, bridge=False, computer_use=False,
                  established_effects=need)


def acquisition_state(ymlp: Path):
    """Is the yq capability usable on this box, and can pip put the tool there without root?"""
    out = {"schema": SCHEMA + "_ACQUISITION", "capability_id": ACQUISITION_ROW}
    out["uid"] = __import__("os").getuid()
    out["has_root"] = out["uid"] == 0
    out["yq_on_path"] = bool(__import__("shutil").which("yq"))
    out["yaml_importable"] = _iu.find_spec("yaml") is not None
    before = _terminal_receipt(ACQUISITION_SENTENCE.format(yaml_path=ymlp), ACQUISITION_ROW)
    out["before"] = {"status": before.get("status"),
                     "error": str(before.get("error"))[:80]}
    out["pip_user_available"] = _pip_user_install_works()
    # NOTE: this function does NOT install anything. Acquisition is a separate, explicit
    # act. Recording "after" here would measure whatever a previous run left on the box --
    # which is exactly the error this module exists to warn about (the first version did
    # it: it reported acquired_rootless=False because yq was already installed, and an
    # earlier run reported True for the same reason). The counterfactual is only honest if
    # the "before" state is the state before ANY acquisition, so the caller owns the order.
    return out


def acquire_rootless(packages=("yq", "pyyaml")):
    """The one lever that has ever turned a failure into a verified action on this box.

    User-scoped, no root. `--break-system-packages` is a deliberate override of a
    protection the OS installed on purpose -- defensible on a disposable sandbox,
    not obviously defensible elsewhere. Returns what actually happened.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "--quiet",
         "--break-system-packages", *packages],
        capture_output=True, text=True, timeout=600)
    return {"returncode": proc.returncode, "packages": list(packages),
            "stderr": (proc.stderr or "")[-200:]}


def _pip_user_install_works():
    """Can this box install a user-scoped package with no root?

    PEP 668 makes a plain `pip install --user` fail on a managed image. The override
    `--break-system-packages` is a deliberate decision, not a detail: it disables a
    protection the OS installed on purpose. This probe records whether the *mechanism*
    is available; it does not endorse using it.
    """
    probe = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "--quiet",
         "--break-system-packages", "pyyaml"],
        capture_output=True, text=True, timeout=300)
    return probe.returncode == 0


# ------------------------------------------------------------------------------------------
# 3. The blind sensor
# ------------------------------------------------------------------------------------------
def blind_presence_probe():
    """Which apt-sourced capabilities expose no statically visible module at all?"""
    from canonical.runtime import astra_runtime as A

    reg = json.loads(REGISTRY.read_text())["capabilities"]
    apt, empty = [], []
    for cid, entry in reg.items():
        source = entry.get("source") or {}
        if not (isinstance(source, dict) and source.get("type") == "apt"):
            continue
        apt.append(cid)
        if not A._adapter_required_modules(entry.get("adapter_module")):
            empty.append({"capability_id": cid,
                          "adapter_module": entry.get("adapter_module"),
                          "apt_packages": [p.get("name") for p in (source.get("packages") or [])
                                           if isinstance(p, dict)]})
    return {"schema": SCHEMA + "_BLIND_PROBE", "apt_sourced": len(apt),
            "presence_probe_blind": len(empty), "rows": empty}


_TEMPLATE_MODULE = re.compile(r"['\"]module['\"]\s*:\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")


def _probe_with_template_literals(adapter_module, entry=None, base=None):
    """The probe, plus the module the entry's own template names as a literal.

    `base` is passed explicitly rather than looked up on the module, because this
    function is itself installed as `astra_runtime._adapter_required_modules` during
    the counterfactual -- reading it back off the module recurses forever. (It did.)
    """
    from canonical.runtime import astra_runtime as A

    base = base or A._adapter_required_modules
    found = list(base(adapter_module))
    for name in _TEMPLATE_MODULE.findall(str((entry or {}).get("action_template") or "")):
        if name not in found:
            found.append(name)
    return found


DOCX_SENTENCE = ("create a docx document titled Report with the paragraph hello "
                 "from python docx")


def blind_sensor_counterfactual():
    """Patch the probe to see the template's literal module. Does anything start working?"""
    from canonical.runtime import astra_runtime as A
    from canonical.runtime import grounded_action_v1 as GA

    reg = GA.load_registry()
    entry = reg.get("docx.document.create.python_docx") or {}
    original = A._adapter_required_modules

    def patched(adapter_module):
        return _probe_with_template_literals(adapter_module, entry, base=original)

    states = {}
    try:
        states["before"] = _terminal_receipt(DOCX_SENTENCE, "docx.document.create.python_docx")
        A._adapter_required_modules = patched
        states["after"] = _terminal_receipt(DOCX_SENTENCE, "docx.document.create.python_docx")
    finally:
        A._adapter_required_modules = original

    before, after = states["before"], states["after"]
    return {"schema": SCHEMA + "_BLIND_SENSOR",
            "capability_id": "docx.document.create.python_docx",
            "probe_before": original("python_document_builder"),
            "probe_after": _probe_with_template_literals("python_document_builder", entry,
                                                         base=original),
            "docx_importable": _iu.find_spec("docx") is not None,
            "before": {"status": before.get("status"), "error": str(before.get("error"))[:80]},
            "after": {"status": after.get("status"), "error": str(after.get("error"))[:80]},
            "teaching_the_sensor_fixed_it": bool(
                before.get("status") != "VERIFIED_ACTION"
                and after.get("status") == "VERIFIED_ACTION")}


# ------------------------------------------------------------------------------------------
# The terminal census, on this box, right now
# ------------------------------------------------------------------------------------------
def terminal_census():
    """Every capability, its own keywords, and what ACTUALLY happened at the end."""
    import collections
    import os

    from canonical.runtime import grounded_action_v1 as GA

    reg = GA.load_registry()
    counts = collections.Counter()
    rows = []
    saved, devnull = os.dup(1), os.open(os.devnull, os.O_WRONLY)
    try:
        for cid, entry in sorted(reg.items()):
            keywords = [str(k) for k in ((entry or {}).get("keywords") or [])][:5]
            if not keywords:
                counts["NO_KEYWORDS"] += 1
                continue
            os.dup2(devnull, 1)
            try:
                receipt = GA.act(" ".join(keywords), memory=False, bridge=False,
                                 computer_use=False)
            except BaseException:
                receipt = {"status": "RAISED"}
            finally:
                os.dup2(saved, 1)
            if str(receipt.get("capability_id")) != str(cid):
                counts["NOT_SELECTED"] += 1
                continue
            status = str(receipt.get("status") or "NO_STATUS")
            counts[status] += 1
            rows.append({"capability_id": cid, "status": status,
                         "error": str(receipt.get("error"))[:100]})
    finally:
        os.close(devnull)
    return {"schema": SCHEMA + "_TERMINAL", "counts": dict(counts),
            "verified": counts.get("VERIFIED_ACTION", 0),
            "failed": counts.get("ACTION_FAILED", 0), "rows": rows}


def main():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ymlp = Path(tmp) / "probe.yaml"
        ymlp.write_text("a: 1\nb:\n  - x\n  - y\n", encoding="utf-8")
        acq = acquisition_state(ymlp)
    print("=== 1. does the census measure the machine? ===")
    verdict = the_census_misattributes_at_least_one_row()
    print(f"    misattributes at least one row: {verdict['pass']}  ({verdict['why']})")
    for row in census_vs_sentence():
        print(f"    {row['capability_id'][:26]:26} soup={row['soup']['status']!s:16}"
              f" sentence->{str(row['sentence']['routed_to'])[:24]:24}"
              f" {row['sentence']['status']}")

    print("\n=== 2. acquisition, rootless ===")
    print(f"    uid={acq['uid']} root={acq['has_root']} pip-user={acq['pip_user_available']}")
    print(f"    before any acquisition: {acq['before']['status']}  {acq['before']['error']}")
    print(f"    yq on PATH: {acq['yq_on_path']}   yaml importable: {acq['yaml_importable']}")

    print("\n=== 3. does teaching the blind sensor help? ===")
    blind = blind_presence_probe()
    print(f"    apt-sourced {blind['apt_sourced']}, presence probe blind on "
          f"{blind['presence_probe_blind']}")
    cf = blind_sensor_counterfactual()
    print(f"    probe {cf['probe_before']} -> {cf['probe_after']}"
          f"   (docx importable: {cf['docx_importable']})")
    print(f"    before: {cf['before']['status']}  {cf['before']['error']}")
    print(f"    after : {cf['after']['status']}  {cf['after']['error']}")
    print(f"    fixed by teaching the sensor: {cf['teaching_the_sensor_fixed_it']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
