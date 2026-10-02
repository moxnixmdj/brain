import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import terminal_replacement_wave as trw


class TerminalReplacementWaveGuardTests(unittest.TestCase):
    def _files(self, active, states):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        reg=root/"registry.json"; basis=root/"basis.json"
        reg.write_text(json.dumps({"active_contracted_residuals":[{"behavior_id":x} for x in active]}),encoding="utf-8")
        basis.write_text(json.dumps({"contracts":[{"behavior_id":x,"proof_state":states.get(x,"ROUTE_REQUIRED")} for x in active]}),encoding="utf-8")
        return td,reg,basis

    def test_rejects_nonadmissible_routes_before_any_case_generation(self):
        active=list(trw.CONTRACTS)+["CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001","SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"]
        td,reg,basis=self._files(active,{})
        self.addCleanup(td.cleanup)
        with mock.patch.object(trw,"ACTIVE_REGISTRY",reg), mock.patch.object(trw,"ACTIVE_BASIS",basis):
            with self.assertRaisesRegex(ValueError,"TERMINAL_ROUTES_NOT_ADMISSIBLE"):
                trw._preflight_active_basis()

    def test_rejects_executor_contract_mismatch_even_if_basis_claims_ready(self):
        active=list(trw.CONTRACTS)+["CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001","SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"]
        states={x:"TERMINAL_ROUTE_FROZEN_ADMISSIBLE" for x in active}
        td,reg,basis=self._files(active,states)
        self.addCleanup(td.cleanup)
        with mock.patch.object(trw,"ACTIVE_REGISTRY",reg), mock.patch.object(trw,"ACTIVE_BASIS",basis):
            with self.assertRaisesRegex(ValueError,"EXECUTOR_CONTRACT_SET_MISMATCH"):
                trw._preflight_active_basis()

    def test_duplicate_active_contract_registry_fails(self):
        active=["A","A"]
        td,reg,basis=self._files(active,{"A":"TERMINAL_ROUTE_FROZEN_ADMISSIBLE"})
        self.addCleanup(td.cleanup)
        with mock.patch.object(trw,"ACTIVE_REGISTRY",reg), mock.patch.object(trw,"ACTIVE_BASIS",basis):
            with self.assertRaisesRegex(ValueError,"ACTIVE_CONTRACT_REGISTRY_INVALID"):
                trw._preflight_active_basis()


if __name__=="__main__":
    unittest.main()
