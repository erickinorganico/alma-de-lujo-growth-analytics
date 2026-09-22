SELECT e.id experiment_id,e.name,e.status,e.primary_metric,e.guardrail,e.start_date,e.end_date,a.arm,
 CASE WHEN {{coverage:experiments}}=1 AND {{coverage:experiment_assignments}}=1 THEN COUNT(a.id) END assigned_customers,
 CASE WHEN {{coverage:experiments}}=1 AND {{coverage:experiment_assignments}}=1 AND {{coverage:experiment_outcomes}}=1 THEN SUM(CASE WHEN o.converted=1 THEN 1 ELSE 0 END) END converted_customers,
 CASE WHEN {{coverage:experiments}}=1 AND {{coverage:experiment_assignments}}=1 AND {{coverage:experiment_outcomes}}=1 AND COUNT(a.id)>0 THEN AVG(CASE WHEN o.converted=1 THEN 1.0 ELSE 0.0 END) END conversion_rate,
 CASE WHEN {{coverage:experiments}}=1 AND {{coverage:experiment_assignments}}=1 AND {{coverage:experiment_outcomes}}=1 THEN SUM(o.net_revenue_cents) END net_revenue_cents,
 CASE WHEN {{coverage:experiments}}=1 AND {{coverage:experiment_assignments}}=1 AND {{coverage:experiment_outcomes}}=1 THEN SUM(o.contribution_cents) END contribution_cents,
 CASE WHEN {{coverage:experiments}}=1 AND {{coverage:experiment_assignments}}=1 AND {{coverage:experiment_outcomes}}=1 THEN SUM(o.returned) END returned_customers,
 CASE WHEN {{coverage:experiments}}=1 AND {{coverage:experiment_assignments}}=1 AND {{coverage:experiment_outcomes}}=1 THEN 1 ELSE 0 END outcome_coverage_known,
 1 AS synthetic_descriptive_only
FROM experiments e JOIN experiment_assignments a ON a.experiment_id=e.id LEFT JOIN experiment_outcomes o ON o.assignment_id=a.id GROUP BY e.id,a.arm ORDER BY e.id,a.arm
