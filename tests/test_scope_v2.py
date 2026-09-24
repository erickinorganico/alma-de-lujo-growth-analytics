import unittest

from scripts.check_scope_v2 import ROOT, ScopeRunner, V02_ROLE_FILES


class ScopeV02RoleScopeTests(unittest.TestCase):
    def test_historical_agent_gate_excludes_v1_catalog(self):
        runner = ScopeRunner(ROOT / "evidence" / "v0.2" / "workspace",
                             ROOT / "evidence" / "v0.2" / "verification.json")

        passed, observed = runner._check_agent_002()

        self.assertTrue(passed, observed)
        self.assertEqual(7, observed["roles"])
        self.assertEqual(
            set(V02_ROLE_FILES),
            {path.name for path in (ROOT / "agents").glob("*.json")
             if path.name in V02_ROLE_FILES},
        )
        self.assertTrue((ROOT / "agents" / "native-cycle-v1.roles.json").is_file())


if __name__ == "__main__":
    unittest.main()
