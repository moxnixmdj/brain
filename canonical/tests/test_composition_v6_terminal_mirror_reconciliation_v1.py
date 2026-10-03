import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def L(p): return json.loads((R/p).read_text())
def test_v6_mirror():
 t=L('canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json')
 assert t['truth']['opus55_acceptance']=='5/19_PASS__14/19_OPEN'
 assert t['truth']['achieved'] is False
 assert 'composition_component_proof_current_authority_v5' not in t['sources']
 a=t['sources']['composition_component_proof_current_authority_v6']
 assert a['git_blob_sha']=='5bb089582a5bc2ee4a44143c8d3a11e919fecdff'
 assert a['verification_git_blob_sha']=='28c5fe9e456cc6bd5171bb74ab291b043d7e85e4'
 assert t['integrator_reconciliation_20261002_current']['composition']=='4_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_RECOVERY_DELEGATION_AND_TOOL_DISCOVERY_SCOPED_PROVED__8_OPEN__PARENT_OPEN'
 flat=json.dumps(t)
 assert 'FROZEN_COMPOSITION_COMPONENT_INTERFACES__3_OF_12_CURRENTLY_ADMISSIBLE' not in flat
 assert 'COMPOSITION_CURRENT_SLICE_V5_RECEIPT_DERIVED' not in flat
 assert 'FROZEN_COMPOSITION_COMPONENT_INTERFACES__4_OF_12_CURRENTLY_ADMISSIBLE' in flat
