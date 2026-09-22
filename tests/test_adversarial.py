"""Independent synthetic adversarial regressions from the final review."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from alma.analytics import analyze
from alma.fixtures import generate
from alma.reporting import write_reports
from alma.validation import ContractError


class AdversarialRegressionTests(unittest.TestCase):
    def test_invalid_relationship_or_delivery_stops_deliberately(self):
        for mutation in ('fk', 'delivery'):
            with self.subTest(mutation=mutation):
                data = generate()
                if mutation == 'fk':
                    data['tables']['order_items'][0]['order_id'] = 'MISSING'
                else:
                    next(o for o in data['tables']['orders'] if o['status'] == 'delivered')['delivered_date'] = None
                with self.assertRaises(ContractError):
                    analyze(data)

    def test_absent_input_contract_stops_deliberately(self):
        with self.assertRaises(ContractError):
            analyze({})

    def test_unknown_variant_and_movement_coverage_withholds_valuation(self):
        for source in ('variants', 'movements'):
            with self.subTest(source=source):
                data = generate()
                data['metadata']['coverage'][source] = False
                report = analyze(data)
                self.assertEqual('BLOCKED', report['meta']['status'])
                self.assertIsNone(report['kpis']['inventory_value_cents'])
                for row in report['inventory']:
                    self.assertIsNone(row['value_cents'])
                    self.assertIsNone(row['on_hand'])
                    self.assertIsNone(row['sell_through_pct'])
                self.assertTrue(all(p['status'] == 'BLOCKED' for p in report['decisions']))

    def test_monthly_event_bridges_reconcile_to_snapshot(self):
        report = analyze(generate())
        for metric in ('net_revenue_cents', 'cogs_cents', 'opex_cents', 'net_cash_cents'):
            with self.subTest(metric=metric):
                self.assertEqual(report['kpis'][metric], sum(r[metric] for r in report['trend']))
        self.assertEqual(report['kpis']['net_revenue_cents'], sum(r['net_revenue_cents'] for r in report['channels']))

    def test_rendered_absent_coverage_is_not_a_zero_count(self):
        cases = {
            'purchase_orders': 'Compras: 0',
            'products': 'productos: 0',
            'orders': 'Cohortes con madurez de 30 días: 0 de 0',
            'movements': '0 SKU(s) con estado de revisión, reposición o agotado',
            'variants': '0 SKU(s) con estado de revisión, reposición o agotado',
            'reservations': '0 SKU(s) con estado de revisión, reposición o agotado',
        }
        for source, false_zero in cases.items():
            with self.subTest(source=source):
                data = generate()
                data['metadata']['coverage'][source] = False
                with TemporaryDirectory(prefix='alma-adversarial-') as tmp:
                    write_reports(analyze(data), tmp)
                    text = (Path(tmp) / 'report.md').read_text(encoding='utf-8')
                self.assertTrue(false_zero not in text, f'{source}: missing coverage rendered as a zero count')
                self.assertIn('Sin datos', text)


if __name__ == '__main__':
    unittest.main()
