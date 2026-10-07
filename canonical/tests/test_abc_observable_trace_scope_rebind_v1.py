from canonical.runtime.abc_observable_trace_scope_rebind_verifier_v1 import verify,reduce_scope
def test_current_pass():
 x=verify(); assert x["pass"],x; assert x["target_scope_superset_closed"]; assert not x["abc_closed"]
def test_missing_observability_reopens():
 x=reduce_scope(externally_useful_implies_observable=False,opaque_payload_total=True,composition_total=True,independent_replay_pass=True,brain_dominance_claimed=False); assert not x["pass"]
def test_composition_escape_reopens():
 x=reduce_scope(externally_useful_implies_observable=True,opaque_payload_total=True,composition_total=False,independent_replay_pass=True,brain_dominance_claimed=False); assert not x["pass"]
def test_dominance_smuggling_reopens():
 x=reduce_scope(externally_useful_implies_observable=True,opaque_payload_total=True,composition_total=True,independent_replay_pass=True,brain_dominance_claimed=True); assert not x["pass"]
