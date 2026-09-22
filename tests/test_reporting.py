import tempfile
import unittest
from pathlib import Path
from alma.analytics import analyze
from alma.fixtures import generate
from alma.reporting import _color_chart, _monthly_chart, write_reports

class ReportingTests(unittest.TestCase):
    def test_artifacts_exist_and_escape_html(self):
        report=analyze(generate())
        report['market'][0]['title']='<table><img src=x onerror=alert(1)></table>'
        with tempfile.TemporaryDirectory() as tmp:
            files=write_reports(report,tmp)
            self.assertEqual(5,len(files))
            self.assertTrue(all((Path(tmp)/name).is_file() for name in files))
            html=(Path(tmp)/'report.html').read_text(encoding='utf-8')
            self.assertNotIn('<img src=x onerror=alert(1)>', html)
            self.assertIn('&lt;table&gt;&lt;img src=x onerror=alert(1)&gt;&lt;/table&gt;', html)
            self.assertIn('<table>', html)
            self.assertIn('<th>Canal</th>', html)

    def test_unknowns_are_not_zero_in_report_or_charts(self):
        report=analyze(generate(scenario='missing_cost'))
        with tempfile.TemporaryDirectory() as tmp:
            write_reports(report,tmp)
            text=(Path(tmp)/'report.md').read_text(encoding='utf-8')
            self.assertIn('Sin datos',text)
            self.assertIn('Sin datos', (Path(tmp)/'charts'/'color_stock.svg').read_text(encoding='utf-8'))

    def test_missing_coverage_counts_are_unknown_not_zero(self):
        report=analyze(generate())
        report['meta']['coverage']={'purchase_orders':False,'products':False,'orders':False,'movements':False}
        with tempfile.TemporaryDirectory() as tmp:
            write_reports(report,tmp)
            text=(Path(tmp)/'report.md').read_text(encoding='utf-8')
            self.assertIn('Compras: Sin datos · productos: Sin datos', text)
            self.assertIn('Cohortes con madurez de 30 días: Sin datos', text)
            self.assertIn('Sin datos SKU(s)', text)

    def test_signed_and_zero_values_keep_their_semantics(self):
        svg=_monthly_chart([{'month':'2026-01','net_revenue_cents':-100,'cogs_cents':0,'opex_cents':None}])
        self.assertIn('height="240.0"',svg)
        self.assertIn('>0</text>',svg)
        self.assertIn('?',svg)
        colors=_color_chart([{'category':'Pilates socks','color':'Rose','available':-2},{'category':'Sports top','color':'Rose','available':99}])
        self.assertIn('Calcetines de Pilates',colors)
        self.assertIn('>-2</text>',colors)
        self.assertNotIn('>99</text>',colors)

if __name__=='__main__': unittest.main()
