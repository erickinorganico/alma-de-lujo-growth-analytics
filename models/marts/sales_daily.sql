WITH events AS (
  SELECT o.delivered_date AS date,
         SUM(i.quantity * i.unit_price_cents) AS gross_revenue_cents,
         SUM(i.discount_cents) AS discount_cents, 0 AS credit_note_cents,
         SUM(i.quantity * i.unit_cost_cents) AS cogs_cents,
         MIN(CASE WHEN i.unit_cost_cents IS NULL THEN 0 ELSE 1 END) AS cost_known
  FROM orders o JOIN order_items i ON i.order_id=o.id
  WHERE o.status='delivered' GROUP BY o.delivered_date
  UNION ALL
  SELECT cn.date,0,0,SUM(cn.amount_cents),0,1 FROM credit_notes cn GROUP BY cn.date
  UNION ALL
  SELECT r.date,0,0,0,-SUM(r.quantity*i.unit_cost_cents),
         MIN(CASE WHEN i.unit_cost_cents IS NULL THEN 0 ELSE 1 END)
  FROM returns r JOIN order_items i ON i.id=r.order_item_id
  WHERE r.restock=1 GROUP BY r.date
), known AS (
 SELECT CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:credit_notes}}=1 THEN 1 ELSE 0 END revenue_known,
        CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:returns}}=1 THEN 1 ELSE 0 END cost_coverage_known
)
SELECT e.date,
 CASE WHEN k.revenue_known=1 THEN SUM(e.gross_revenue_cents) END AS gross_revenue_cents,
 CASE WHEN k.revenue_known=1 THEN SUM(e.discount_cents) END AS discount_cents,
 CASE WHEN k.revenue_known=1 THEN SUM(e.credit_note_cents) END AS credit_note_cents,
 CASE WHEN k.revenue_known=1 THEN SUM(e.gross_revenue_cents)-SUM(e.discount_cents)-SUM(e.credit_note_cents) END AS net_revenue_cents,
 CASE WHEN k.cost_coverage_known=1 AND MIN(e.cost_known)=1 THEN SUM(e.cogs_cents) END AS cogs_cents,
 CASE WHEN k.revenue_known=1 AND k.cost_coverage_known=1 AND MIN(e.cost_known)=1 THEN SUM(e.gross_revenue_cents)-SUM(e.discount_cents)-SUM(e.credit_note_cents)-SUM(e.cogs_cents) END AS gross_profit_cents,
 k.revenue_known AS revenue_coverage_known,
 CASE WHEN k.cost_coverage_known=1 AND MIN(e.cost_known)=1 THEN 1 ELSE 0 END AS cost_coverage_known
FROM events e CROSS JOIN known k GROUP BY e.date ORDER BY e.date
