from __future__ import annotations
import copy, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PREIMAGE_COMMIT="779b28dbf4f6b9bf1d6ef01dacbcaf3bbdbcced0"
AUTH_PATH="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
ROOT_PATH="canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"

EXPECTED_PREIMAGE_AUTH_BLOB="59632d81b723c4840ed599005490e28341e81054"
EXPECTED_POST_AUTH_BLOB="ee6bc2482cadf275bf754bc72f84a542e002968f"
EXPECTED_ROOT_BLOB="601e82d00104b4ed36ee5968ad966a0c02e627c1"
EXPECTED_RECONCILIATION_BLOB="51c7e73e55b26bc211c8609b70975dd41a31d9c2"
EXPECTED_LB_V2_BLOB="d410d6952cb34f2fd3fb4dc48bf2a613d11c57d1"
EXPECTED_LB_TRANSPORT_RECEIPT_BLOB="e91092e6937adc0e22beb0e8907a548b42155e54"

def git_blob_bytes(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def file_blob(path:str)->str:
 return git_blob_bytes((ROOT/path).read_bytes())

def git_show(commit:str,path:str)->bytes:
 return subprocess.check_output(["git","show",f"{commit}:{path}"],cwd=ROOT)

assert git_blob_bytes(git_show(PREIMAGE_COMMIT,AUTH_PATH))==EXPECTED_PREIMAGE_AUTH_BLOB
assert file_blob(AUTH_PATH)==EXPECTED_POST_AUTH_BLOB
assert file_blob(ROOT_PATH)==EXPECTED_ROOT_BLOB
assert file_blob("canonical/governance/CURRENT_TERMINAL_AUTHORITY_ROOT2_OUTPUT_RECONCILIATION_V1.json")==EXPECTED_RECONCILIATION_BLOB
assert file_blob("canonical/governance/LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V2.json")==EXPECTED_LB_V2_BLOB
assert file_blob("canonical/verification/LIVEBENCH_THRESHOLD_ROOT_AUTHORITY_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")==EXPECTED_LB_TRANSPORT_RECEIPT_BLOB

before=json.loads(git_show(PREIMAGE_COMMIT,AUTH_PATH))
after=json.loads((ROOT/AUTH_PATH).read_text())
transport=json.loads((ROOT/"canonical/verification/LIVEBENCH_THRESHOLD_ROOT_AUTHORITY_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
lbv2=json.loads((ROOT/"canonical/governance/LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V2.json").read_text())

assert transport["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert transport["subject"]["current_root_git_blob_sha"]==EXPECTED_ROOT_BLOB
assert transport["verified"]["exact_root_delta"]==["scheduler_policy.root2_output_only_threshold_dag"]
assert transport["verified"]["authorized_predicates"]==["LIVEBENCH_IF_GE_65_7"]
assert transport["verified"]["global_fresh_reality_authority"] is False
assert lbv2["authority_basis"]["root_state"]["git_blob_sha"]==EXPECTED_ROOT_BLOB
assert lbv2["authorized_predicates"]==["LIVEBENCH_IF_GE_65_7"]

expected=copy.deepcopy(before)
expected["authorities"]["root2_output_only_threshold_dag_v1"]={
 "reconciliation_path":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_ROOT2_OUTPUT_RECONCILIATION_V1.json",
 "reconciliation_git_blob_sha":EXPECTED_RECONCILIATION_BLOB,
 "activation_path":"canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_ACTIVATION_V1.json",
 "activation_git_blob_sha":"7ea4dd4edb59c8526bd3993e02f4a8fb53c65085",
 "activation_verification_path":"canonical/verification/ROOT2_OUTPUT_ONLY_THRESHOLD_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "activation_verification_git_blob_sha":"eef494009e47b758a99ab48649e050c332e4988a",
 "subject_path":"canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json",
 "subject_git_blob_sha":"1fba51d15bcfdf6accd90948155517f7c9b98bbb",
 "status":"ACTIVE__INDEPENDENT_ROOT_PROJECTION_PASS__19_ROOT2_TOUCHING_PREDICATES__SCHEDULING_ONLY__ZERO_CREDIT",
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0
}
expected["authorities"]["livebench_current_predicate_local_direct_authority_v2"]={
 "activation_path":"canonical/governance/LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V2.json",
 "activation_git_blob_sha":EXPECTED_LB_V2_BLOB,
 "transport_verification_path":"canonical/verification/LIVEBENCH_THRESHOLD_ROOT_AUTHORITY_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "status":"ACTIVE_IFF_EXACT_TRANSPORT_VERIFICATION_RECEIPT_EXISTS_AND_PASSES_AND_CURRENT_ROOT_HASH_REMAINS_601E82D00104B4ED36EE5968AD966A0C02E627C1",
 "authorized_predicates":["LIVEBENCH_IF_GE_65_7"],
 "predicate_local_fresh_reality_authority":True,
 "global_fresh_reality_authority":False,
 "promotion_authority":False,
 "acceptance_credit_authority":False
}
expected["next_terminal_action"]="APPLY_VERIFIED_OUTPUT_ONLY_THRESHOLD_DAG_TO_ALL_19_ROOT2_TOUCHING_PREDICATES__STOP_ON_SOUND_FORCED_PASS_OR_FAIL__OTHERWISE_EXECUTE_ONLY_MINIMUM_NONOVERLAPPING_ZERO_REALITY_CERTIFICATE_RESIDUALS__AFTER_PREPASS_ALLOW_FRESH_REALITY_ONLY_WHERE_A_SEPARATE_EXACT_PREDICATE_LOCAL_AUTHORITY_EXISTS_AND_PASSES_POINT_OF_USE_GATES__CURRENTLY_LIVEBENCH_IF_GE_65_7_ONLY__NO_GLOBAL_FRESH_REALITY"

assert after==expected
assert after["truth"]==before["truth"]
assert after["ownership_state"]==before["ownership_state"]
assert after["atomic_acceptance_frontier"]==before["atomic_acceptance_frontier"]
for k,v in before["authorities"].items():
 assert after["authorities"][k]==v

assert after["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert after["atomic_acceptance_frontier"]["proved"]==12
assert after["atomic_acceptance_frontier"]["unresolved"]==26
assert after["authorities"]["root2_output_only_threshold_dag_v1"]["fresh_reality_authority"] is False
assert after["authorities"]["livebench_current_predicate_local_direct_authority_v2"]["global_fresh_reality_authority"] is False

print(json.dumps({
 "schema":"PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_ROOT2_OUTPUT_RECONCILIATION_PRIVATE_VERIFIER_V1",
 "pass":True,
 "preimage_authority_blob":EXPECTED_PREIMAGE_AUTH_BLOB,
 "post_authority_blob":EXPECTED_POST_AUTH_BLOB,
 "root_blob_unchanged":EXPECTED_ROOT_BLOB,
 "declared_delta":[
   "ADD_AUTHORITIES_ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_V1",
   "ADD_AUTHORITIES_LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_V2",
   "REPLACE_NEXT_TERMINAL_ACTION_ONLY"
 ],
 "acceptance":"5/19",
 "proved_atomic":12,
 "unresolved_atomic":26,
 "global_fresh_reality_authority":False
},sort_keys=True))
