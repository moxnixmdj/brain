"""Deterministic paraphrase canonicalisation: rewrites must be exact, narrow, and never touch
out-of-scope or verify/inspect goals.  Measured effect is in the commit message."""
from canonical.runtime.goal_paraphrase_canonical_v1 import canonicalize


def test_exact_literal_verbs_map_to_the_compiler_shape():
    assert canonicalize('Say exactly "zeta1 quartz7".') == 'Respond with exactly "zeta1 quartz7".'
    assert canonicalize('Return the string "ember 8 river 2" verbatim.') == 'Respond with exactly "ember 8 river 2".'
    assert canonicalize('Reply with "cobalt sky 404" and nothing more.') == 'Respond with exactly "cobalt sky 404".'


def test_literal_json_frame_maps_to_containing_form():
    out = canonicalize("Write canonical/a/rec1.json with exactly one record having fields name and count: alpha1 21.")
    assert out == "Create canonical/a/rec1.json containing exactly one record with fields name and count: alpha1 21."
    assert canonicalize("Please create canonical/a/r.json with exactly 1 record that has fields id and value: k 1.").startswith(
        "Create canonical/a/r.json containing exactly one record with fields id and value")


def test_archive_paraphrase_maps_to_the_manifest_template():
    out = canonicalize("Make a compressed tarball canonical/a/p.tar.gz out of the manifest canonical/a/m.json.")
    assert out == ("Create a tar.gz archive from the manifest canonical/a/m.json, including all its "
                   "verification_paths files, and save it to canonical/a/p.tar.gz.")


def test_verify_goal_is_never_rewritten_into_a_create_goal():
    goal = "Verify the tar.gz archive canonical/a/b.tar.gz against the manifest canonical/a/m.json with gnu tar."
    assert canonicalize(goal) == goal


def test_out_of_scope_goals_are_untouched():
    for goal in [
        "Translate the sentence 'good morning' into Japanese and save it to canonical/a/o.txt.",
        "Write a haiku about the sea and save it to canonical/a/o.txt.",
        "Describe the plot of Hamlet and save it to canonical/a/o.txt.",
    ]:
        assert canonicalize(goal) == goal


def test_empty_and_plain_goals_pass_through():
    assert canonicalize("") == ""
    assert canonicalize("   ") == ""
    assert canonicalize("Create canonical/a/x.txt with the word hi.") == "Create canonical/a/x.txt with the word hi."
