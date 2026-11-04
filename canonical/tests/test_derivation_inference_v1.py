"""What the inference engine must not be allowed to believe about itself.

The engine infers, for every field this repository records, which derivation of the tree that
field obeys -- and then uses the inference as the live predicate that repairs documents. Every
test here exists because it was already wrong in that exact way at least once today:

  * `git_blob_sha` looked 100% fabricated (40/40 sampled disagreements) until I fetched the
    full history and found 0/200 were fabricated. The clone was depth-1. An instrument that
    cannot tell "this object is missing" from "I have not fetched this object" reports its own
    blindness as the repository's dishonesty.
  * the first shape key was the exact sibling set, so 477 shapes had ~1 record each and
    everything was INSUFFICIENT_SUPPORT -- a measurement of my granularity, not of the repo.
  * a model keyed only on field names can never say anything about a field it has not seen,
    which is what memorisation looks like from the inside.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import derivation_inference_v1 as infer  # noqa: E402


# --------------------------------------------------------------------------- fixtures
def _point_at(tmp_path, monkeypatch):
    """Aim the engine and the loop at a temporary world without recursing through patches."""
    real_tree = infer.Tree

    def factory(*args, **kwargs):
        kwargs.setdefault("root", tmp_path)
        return real_tree(*args, **kwargs)

    monkeypatch.setattr(infer, "Tree", factory)
    import canonical.tools.self_maintenance_loop_v1 as loop
    monkeypatch.setattr(loop, "change_set", lambda base_ref=None: ["doc.json"])
    monkeypatch.setattr(loop, "ROOT", tmp_path)

def _site(doc: str, record: dict, field: str, value, cls: str | None = None):
    cls = cls or infer.value_class(value)
    return infer.Site(doc, f"/{field}", field, record, value, cls)


@pytest.fixture()
def tree(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"hello")
    (tmp_path / "b.txt").write_bytes(b"hello there")
    return infer.Tree(root=tmp_path)


def _blob_sites(tmp_path, count=8):
    sites = []
    for i in range(count):
        name = f"f{i}.txt"
        (tmp_path / name).write_bytes(b"payload-%d" % i)
        record = {"path": name, "git_blob_sha": infer.git_blob_sha(b"payload-%d" % i)}
        sites.append(_site(f"doc{i}.json", record, "git_blob_sha",
                           record["git_blob_sha"], "hex40"))
    return sites


# --------------------------------------------------------------------------- DISCOVER
def test_a_field_whose_values_follow_the_tree_is_attributed(tmp_path, tree):
    sites = _blob_sites(tmp_path)
    fields = infer.attribute(sites, tree)
    got = fields["git_blob_sha|hex40"]
    assert got["state"] == "ATTRIBUTED", got
    assert got["candidate"] == "git_blob_of_referenced_file"
    assert got["rate"] == 1.0


def test_a_field_whose_values_follow_nothing_is_not_attributed(tmp_path, tree):
    """If every value is arbitrary, the honest answer is that the field is not understood."""
    sites = []
    for i in range(8):
        (tmp_path / f"g{i}.txt").write_bytes(b"x")
        record = {"path": f"g{i}.txt", "whatever": "%040x" % (i * 7919 + 13)}
        sites.append(_site("d.json", record, "whatever", record["whatever"], "hex40"))
    got = infer.attribute(sites, tree)["whatever|hex40"]
    assert got["state"] == "UNEXPLAINED", got
    assert got["rate"] < infer.BIND_THRESHOLD


class _HeadEqualsWorking(infer.Tree):
    """A tree whose committed bytes equal the working bytes -- the clean-checkout case.

    On such a tree `git_blob_of_referenced_file` and `git_blob_at_head` explain every record
    equally well, and an instrument that names only one of them is asserting more than its
    evidence supports.
    """

    def at_ref(self, relpath, ref=None):
        return self.read(relpath)


def test_two_candidates_that_always_agree_are_reported_as_ambiguous(tmp_path):
    sites = _blob_sites(tmp_path)
    got = infer.attribute(sites, _HeadEqualsWorking(root=tmp_path))["git_blob_sha|hex40"]
    assert len(got["contenders"]) >= 2, got["contenders"]
    assert set(got["contenders"]) >= {"git_blob_of_referenced_file", "git_blob_at_head"}


def test_a_field_that_is_only_mostly_explained_is_not_called_understood(tmp_path, tree):
    """7 of 10 records follow the derivation. That is a pattern, not a rule.

    This test exists because a build that lowered the binding threshold to 0.50 passed every
    other test in this file. A threshold nobody pins is a threshold that drifts, and this is
    the number that decides whether the system is allowed to rewrite a document.
    """
    sites = []
    for i in range(10):
        name = f"m{i}.txt"
        (tmp_path / name).write_bytes(b"payload-%d" % i)
        good = infer.git_blob_sha(b"payload-%d" % i)
        value = good if i < 7 else "%040x" % (i * 104729)
        sites.append(_site("d.json", {"path": name, "git_blob_sha": value},
                           "git_blob_sha", value, "hex40"))
    got = infer.attribute(sites, tree)["git_blob_sha|hex40"]
    assert got["rate"] == pytest.approx(0.7, abs=0.01), got
    assert got["state"] == "UNEXPLAINED", (
        "a field explained 70% of the time was accepted as understood")
    assert infer.BIND_THRESHOLD >= 0.9


def test_too_few_records_is_not_evidence(tmp_path, tree):
    sites = _blob_sites(tmp_path, count=2)
    got = infer.attribute(sites, tree)["git_blob_sha|hex40"]
    assert got["state"] == "INSUFFICIENT_SUPPORT"


# --------------------------------------------------------------------------- GENERALISE
def _big_blob_sites(tmp_path, count=40):
    return _blob_sites(tmp_path, count=count)


def test_the_rule_survives_withholding_half_the_records(tmp_path):
    """A system that memorised values cannot answer for records it never saw."""
    sites = _big_blob_sites(tmp_path)
    tree = infer.Tree(root=tmp_path)
    got = infer.generalise_within_field(sites, tree)
    assert got["records_predicted"] > 0
    assert got["accuracy"] == 1.0, got


def test_a_rule_learned_about_a_field_name_does_not_transfer_to_a_new_name(tmp_path):
    """This is the limitation, stated as a test so nobody mistakes the model for general.

    `git_blob_sha` is understood; `provenance_digest` holding the same kind of value is not,
    because the model is keyed on the name. Pinning this is what makes the role-level
    analogy below a *widening* rather than a description of something that was already true.
    """
    sites = _big_blob_sites(tmp_path)
    tree = infer.Tree(root=tmp_path)
    fields = infer.attribute(sites, tree)
    assert "git_blob_sha|hex40" in fields
    record = {"path": "f0.txt", "provenance_digest": infer.git_blob_sha(b"payload-0")}
    class FakeClass:
        pass
    assert "provenance_digest|hex40" not in fields, (
        "if this ever appears, name-level learning has silently become shape-level learning")


def test_the_role_lets_the_model_say_something_about_an_unseen_field_name(tmp_path):
    sites = _big_blob_sites(tmp_path)
    tree = infer.Tree(root=tmp_path)
    roles = infer.attribute_roles(sites, tree)
    got = roles["hex40|path"]
    assert got["state"] == "ATTRIBUTED", got
    assert got["candidate"] == "git_blob_of_referenced_file"


# --------------------------------------------------------------------------- the blindness
def test_a_missing_git_object_is_not_called_fabrication_in_a_shallow_clone(tmp_path, tree):
    """Measured 2026-11-04: 40/40 sampled "fabricated" shas became 0/200 after unshallowing.

    The classification must degrade to UNVERIFIABLE, and the report must say PROVISIONAL.
    """
    tree._shallow = True                    # pretend the clone is depth-1
    (tmp_path / "c.txt").write_bytes(b"real")
    record = {"path": "c.txt", "git_blob_sha": "f" * 40}
    sites = [_site("d.json", record, "git_blob_sha", "f" * 40, "hex40")]
    got = infer.diagnose_residuals("git_blob_sha|hex40", sites, tree, sample=5,
                                  candidate="git_blob_of_referenced_file")
    assert got["history_complete"] is False
    assert got["conclusion"].startswith("PROVISIONAL")
    assert "NEVER_AN_OBJECT" not in got["causes"], (
        "a shallow clone cannot distinguish a fabricated sha from an unfetched one")
    assert got["causes"].get("UNVERIFIABLE_IN_SHALLOW_CLONE") == 1


# --------------------------------------------------------------------------- persistence
def test_a_learned_model_survives_the_process(tmp_path):
    """The creature map's most repeated failure is learning that vanishes with the process."""
    sites = _blob_sites(tmp_path)
    tree = infer.Tree(root=tmp_path)
    fields = infer.attribute(sites, tree)
    doc = {"fields": {k: v for k, v in fields.items()},
           "roles": infer.attribute_roles(sites, tree), "records_seen": len(sites),
           "history_complete": True}
    path = tmp_path / "MODEL.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    infer._MODEL_CACHE = None
    loaded = infer.load_model(path, recompute_if_missing=False)
    assert loaded is not None
    assert loaded["fields"]["git_blob_sha|hex40"]["candidate"] == "git_blob_of_referenced_file"


def test_a_missing_model_is_not_silently_replaced_by_a_recomputation_when_told_not_to():
    infer._MODEL_CACHE = None
    assert infer.load_model("/nonexistent/MODEL.json", recompute_if_missing=False) is None


# --------------------------------------------------------------------------- ACT
def test_the_inferred_derivation_repairs_a_field_nobody_named(tmp_path, monkeypatch):
    """The whole point: the predicate comes from the inference, not from a person."""
    (tmp_path / "target.txt").write_bytes(b"0123456789")
    doc_path = tmp_path / "doc.json"
    doc = {"files": [{"path": "target.txt", "bytes": 1}]}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    model = {"fields": {"bytes|int": {"state": "ATTRIBUTED",
                                      "candidate": "size_of_referenced_file",
                                      "rate": 1.0, "records": 9, "contexts": 1}},
             "roles": {"int|path": {"state": "ATTRIBUTED",
                                    "candidate": "size_of_referenced_file", "rate": 1.0}}}
    klass = infer.make_derived_value_class(model=model)
    _point_at(tmp_path, monkeypatch)

    found = klass.find()
    assert len(found) == 1, found
    assert found[0]["tier"] == "EXPLICIT"
    out = klass.fix(found[0])
    assert out["applied"] is True
    assert json.loads(doc_path.read_text())["files"][0]["bytes"] == 10
    assert klass.verify(found[0]) is True


def test_an_analogy_is_reported_but_never_rewrites_a_document(tmp_path, monkeypatch):
    """Same action, one tier weaker: no version of "I guessed what this field means" may edit."""
    (tmp_path / "target.txt").write_bytes(b"0123456789")
    doc_path = tmp_path / "doc.json"
    doc = {"files": [{"path": "target.txt", "bytes": 1}]}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    model = {"fields": {}, "roles": {"int|path": {"state": "TRANSFERABLE_BY_ANALOGY",
                                                  "candidate": "size_of_referenced_file",
                                                  "rate": 0.85}}}
    klass = infer.make_derived_value_class(model=model)
    _point_at(tmp_path, monkeypatch)

    found = klass.find()
    assert found and found[0]["tier"] == "ANALOGY"
    out = klass.fix(found[0])
    assert out["applied"] is False
    assert out["reason"] == "ANALOGY_IS_A_SUSPICION_NOT_A_REPAIR"
    assert json.loads(doc_path.read_text())["files"][0]["bytes"] == 1


def test_only_current_tensed_derivations_are_ever_used_to_rewrite():
    """A historical derivation that disagrees is a record written at another commit."""
    assert infer.CURRENCY["git_blob_at_record_commit"] == "HISTORICAL"
    assert infer.CURRENCY["size_of_referenced_file"] == "CURRENT"
    assert infer.CURRENCY["git_blob_at_head"] == "CURRENT_AT_HEAD"


def test_the_engine_claims_no_capability():
    report = {"authority": "NO_CAPABILITY_CREDIT_INFERENCE_MEASUREMENT_ONLY"}
    assert report["authority"].startswith("NO_CAPABILITY_CREDIT")
