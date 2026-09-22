"""Predeclared fixed-window experiment diagnostics for simulated observations."""
from __future__ import annotations
import math
from statistics import NormalDist


def wilson(successes, trials, confidence=0.95):
    if type(successes) is not int or type(trials) is not int or not 0<=successes<=trials or not 0<confidence<1:
        raise ValueError('Valid binomial counts and confidence required')
    if trials==0:return None
    z=NormalDist().inv_cdf((1+confidence)/2);p=successes/trials;den=1+z*z/trials
    centre=(p+z*z/(2*trials))/den
    half=z*math.sqrt(p*(1-p)/trials+z*z/(4*trials*trials))/den
    return [max(0.,centre-half),min(1.,centre+half)]


def sample_size(baseline=0.10,absolute_mde=0.03,alpha=0.05,power=0.8):
    """Approximate two-sided two-proportion planning; independent balanced arms."""
    target=baseline+absolute_mde
    if not 0<baseline<target<1 or not 0<alpha<1 or not 0.5<power<1:raise ValueError('Invalid design assumptions')
    z=NormalDist().inv_cdf(1-alpha/2);zp=NormalDist().inv_cdf(power);pbar=(baseline+target)/2
    n=((z*math.sqrt(2*pbar*(1-pbar))+zp*math.sqrt(baseline*(1-baseline)+target*(1-target)))**2)/(absolute_mde**2)
    return {'per_arm':math.ceil(n),'baseline_assumption':baseline,'absolute_mde':absolute_mde,'alpha':alpha,'power':power,'method':'normal approximation for independent balanced binomial arms; planning only'}


def analyze_experiments(data):
    t=data['tables'];coverage=data['metadata']['coverage'];results=[]
    assignment_ids=[a['id'] for a in t['experiment_assignments']]
    if len(assignment_ids)!=len(set(assignment_ids)):raise ValueError('Duplicate assignment id')
    unique=[(a['experiment_id'],a['customer_id']) for a in t['experiment_assignments']]
    if len(unique)!=len(set(unique)):raise ValueError('Customer assigned twice in one experiment')
    outcomes={o['assignment_id']:o for o in t['experiment_outcomes']}
    if len(outcomes)!=len(t['experiment_outcomes']):raise ValueError('Duplicate outcome')
    for exp in t['experiments']:
        arms={};problems=[]
        for arm in ('control','treatment'):
            assignments=[a for a in t['experiment_assignments'] if a['experiment_id']==exp['id'] and a['arm']==arm]
            observed=[]
            for a in assignments:
                if not exp['start_date']<=a['assigned_date']<=exp['end_date']:problems.append('ASSIGNMENT_OUTSIDE_WINDOW')
                o=outcomes.get(a['id'])
                if o is not None:
                    if not a['assigned_date']<=o['date']<=data['metadata']['as_of']:problems.append('OUTCOME_TIME_INVALID')
                    observed.append(o)
            n=len(assignments);nobs=len(observed)
            known=all(coverage.get(k) for k in ('experiments','experiment_assignments','experiment_outcomes')) and n==nobs
            successes=sum(o['converted'] for o in observed)
            # Missing outcomes cannot be labeled failures or converted into known revenue.
            arms[arm]={'assigned':n,'observed':nobs,'coverage_known':known,'converted':successes if known else None,
                'conversion_rate':successes/n if known and n else None,'wilson_95':wilson(successes,n) if known else None,
                'mean_contribution_cents':sum(o['contribution_cents'] for o in observed)/n if known and n else None,
                'returned_rate_per_assigned':sum(o['returned'] for o in observed)/n if known and n else None}
            if not known:problems.append('OUTCOMES_UNKNOWN')
        n0,n1=arms['control']['assigned'],arms['treatment']['assigned'];total=n0+n1
        chi=((n0-total/2)**2+(n1-total/2)**2)/(total/2) if total else None
        srm_p=math.erfc(math.sqrt(chi/2)) if chi is not None else None
        if srm_p is not None and srm_p<0.001:problems.append('SAMPLE_RATIO_MISMATCH')
        if exp['status']!='completed' or data['metadata']['as_of']<exp['end_date']:problems.append('WINDOW_OPEN')
        c,treat=arms['control']['conversion_rate'],arms['treatment']['conversion_rate']
        results.append({'experiment_id':exp['id'],'synthetic':True,'arms':arms,'observed_conversion_difference':treat-c if c is not None and treat is not None else None,
            'balanced_assignment_srm_p':srm_p,'issues':sorted(set(problems)),
            'status':'BLOCKED' if any(x in problems for x in ('ASSIGNMENT_OUTSIDE_WINDOW','OUTCOME_TIME_INVALID','SAMPLE_RATIO_MISMATCH')) else 'REVIEW',
            'decision':'No automated winner; analyst must evaluate a predeclared fixed-window protocol and contribution/return guardrails. Synthetic outcomes cannot establish real lift.',
            'interval_method':'Wilson 95% for each arm separately; overlapping intervals are not a formal test of the difference.'})
    return {'version':'2.0','synthetic':True,'experiments':results,'planning_example':sample_size(),
        'method_source':'https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm'}
