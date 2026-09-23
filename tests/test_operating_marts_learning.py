"""Learning, exception, and private publication oracles for operating marts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alma.operating_mart_contracts import bind_cut, load_policy
from alma.operating_workspace import build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"
POLICY = ROOT / "policies" / "operating-metrics-synthetic-v1.json"


class LearningTests(unittest.TestCase):
    def test_eligible_sell_through_and_mature_cohort_controls(self) -> None:
        from alma.operating_learning_exceptions import sell_through, mature_return_rate, variant_mix

        sold = sell_through(12, 1, 20, 16, coverage="COMPLETE")
        self.assertEqual(11, sold["numerator"])
        self.assertEqual(36, sold["denominator"])
        self.assertEqual("0.3055555556", sold["value"])
        self.assertEqual("NOT_APPLICABLE", sell_through(0, 0, 0, 0, coverage="COMPLETE")["status"])
        early = mature_return_rate(12, 2, cohort_date="2026-09-15", as_of="2026-09-21",
                                   maturity_days=30, linked=True, coverage="COMPLETE")
        self.assertEqual("UNKNOWN", early["status"])
        mature = mature_return_rate(12, 2, cohort_date="2026-09-15", as_of="2026-10-20",
                                    maturity_days=30, linked=True, coverage="COMPLETE")
        self.assertEqual("0.1666666667", mature["value"])
        self.assertEqual("UNKNOWN", mature_return_rate(12, 2, cohort_date="2026-09-15",
            as_of="2026-10-20", maturity_days=30, linked=False, coverage="COMPLETE")["status"])
        self.assertEqual("0.4", variant_mix(4, 10, exposure_comparable=True,
            price_comparable=True, coverage="COMPLETE")["value"])
        self.assertEqual("UNKNOWN", variant_mix(4, 10, exposure_comparable=False,
            price_comparable=True, coverage="COMPLETE")["status"])

    def test_stockout_and_unmet_are_observations_not_preference_or_channel_zero(self) -> None:
        from alma.operating_learning_exceptions import project_learning

        policy = load_policy(POLICY, as_of="2026-09-21", real_cut=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                learning = project_learning(cut, "synthetic:sku-001", "2026-09-01", "2026-09-22", policy)
                self.assertEqual(12, learning["gross_delivered_units"])
                self.assertEqual(11, learning["net_depleted_units"])
                self.assertEqual(480, learning["exposure"]["stockout_minutes"])
                self.assertEqual("UNKNOWN", learning["preference_status"])
                self.assertEqual("UNKNOWN", learning["sell_through"]["status"])
                self.assertEqual("UNKNOWN", learning["mature_returns"]["status"])
                self.assertEqual(3, learning["recorded_unmet"][0]["requested_units_lower_bound"])
                self.assertFalse(any(row["channel_code"] == "synthetic:wholesale" for row in learning["recorded_unmet"]))


if __name__ == "__main__":
    unittest.main()
