import unittest
from alma.experimentation import wilson, sample_size, analyze_experiments

class ExperimentTests(unittest.TestCase):
    def test_interval_boundary_and_reference_value(self):
        self.assertIsNone(wilson(0,0))
        self.assertAlmostEqual(wilson(50,100)[0],0.4038315,places=6)
        self.assertAlmostEqual(wilson(50,100)[1],0.5961685,places=6)
        self.assertAlmostEqual(wilson(0,10)[0],0)
        self.assertLess(wilson(0,10)[1],0.3)
        with self.assertRaises(ValueError):wilson(11,10)
        self.assertGreater(sample_size()['per_arm'],1700)

    def test_missing_outcomes_and_late_assignments(self):
        data={'metadata':{'as_of':'2026-09-21','coverage':{'experiments':True,'experiment_assignments':True,'experiment_outcomes':True}},'tables':{
          'experiments':[{'id':'e','start_date':'2026-08-01','end_date':'2026-08-31','status':'completed'}],
          'experiment_assignments':[{'id':'a1','experiment_id':'e','customer_id':'c1','arm':'control','assigned_date':'2026-08-03'},{'id':'a2','experiment_id':'e','customer_id':'c2','arm':'treatment','assigned_date':'2026-09-01'}],
          'experiment_outcomes':[{'assignment_id':'a1','date':'2026-08-10','converted':0,'contribution_cents':0,'returned':0}]}}
        result=analyze_experiments(data)['experiments'][0]
        self.assertIsNone(result['arms']['treatment']['conversion_rate'])
        self.assertIn('OUTCOMES_UNKNOWN',result['issues']);self.assertEqual(result['status'],'BLOCKED')
        data['tables']['experiment_assignments'].append(dict(data['tables']['experiment_assignments'][0]))
        with self.assertRaises(ValueError):analyze_experiments(data)

if __name__=='__main__':unittest.main()
