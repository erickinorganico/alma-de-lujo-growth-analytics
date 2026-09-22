WITH known AS (
 SELECT CASE WHEN {{coverage:payments}}=1 AND {{coverage:refunds}}=1 AND {{coverage:supplier_payments}}=1 AND {{coverage:expense_payments}}=1 THEN 1 ELSE 0 END AS value
), events AS (
 SELECT date,amount_cents AS cash_in_cents,0 AS refund_out_cents,0 AS supplier_out_cents,0 AS expense_out_cents FROM payments WHERE status='settled'
 UNION ALL SELECT date,0,amount_cents,0,0 FROM refunds WHERE status='settled'
 UNION ALL SELECT date,0,0,amount_cents,0 FROM supplier_payments
 UNION ALL SELECT date,0,0,0,amount_cents FROM expense_payments
), daily AS (
 SELECT date,SUM(cash_in_cents) cash_in_cents,SUM(refund_out_cents) refund_out_cents,SUM(supplier_out_cents) supplier_out_cents,SUM(expense_out_cents) expense_out_cents FROM events GROUP BY date
)
SELECT d.date,
 CASE WHEN k.value=1 THEN d.cash_in_cents END cash_in_cents,CASE WHEN k.value=1 THEN d.refund_out_cents END refund_out_cents,
 CASE WHEN k.value=1 THEN d.supplier_out_cents END supplier_out_cents,CASE WHEN k.value=1 THEN d.expense_out_cents END expense_out_cents,
 CASE WHEN k.value=1 THEN d.cash_in_cents-d.refund_out_cents-d.supplier_out_cents-d.expense_out_cents END net_cash_change_cents,
 CASE WHEN k.value=1 THEN SUM(d.cash_in_cents-d.refund_out_cents-d.supplier_out_cents-d.expense_out_cents) OVER (ORDER BY d.date) END cumulative_cash_movement_cents,
 k.value AS cash_coverage_known FROM daily d CROSS JOIN known k ORDER BY d.date
