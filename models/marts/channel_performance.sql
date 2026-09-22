WITH dimensions AS (SELECT channel,id campaign_id FROM campaigns UNION SELECT channel,campaign_id FROM funnel UNION SELECT channel,campaign_id FROM orders),
delivered AS (SELECT o.channel,o.campaign_id,COUNT(DISTINCT o.id) delivered_orders,COUNT(DISTINCT o.customer_id) customers,SUM(i.quantity*i.unit_price_cents) gross_revenue_cents,SUM(i.discount_cents) discount_cents,SUM(i.quantity*i.unit_cost_cents) delivered_cogs_cents,MIN(CASE WHEN i.unit_cost_cents IS NULL THEN 0 ELSE 1 END) cost_known FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.status='delivered' GROUP BY o.channel,o.campaign_id),
credits AS (SELECT o.channel,o.campaign_id,SUM(cn.amount_cents) credit_note_cents FROM credit_notes cn JOIN order_items i ON i.id=cn.order_item_id JOIN orders o ON o.id=i.order_id GROUP BY o.channel,o.campaign_id),
restocks AS (SELECT o.channel,o.campaign_id,SUM(r.quantity*i.unit_cost_cents) restock_cogs_reversal_cents,MIN(CASE WHEN i.unit_cost_cents IS NULL THEN 0 ELSE 1 END) cost_known FROM returns r JOIN order_items i ON i.id=r.order_item_id JOIN orders o ON o.id=i.order_id WHERE r.restock=1 GROUP BY o.channel,o.campaign_id),
marketing AS (SELECT channel,campaign_id,SUM(spend_cents) marketing_spend_cents FROM funnel GROUP BY channel,campaign_id)
SELECT x.channel,x.campaign_id,
 CASE WHEN {{coverage:orders}}=1 THEN COALESCE(d.delivered_orders,0) END delivered_orders,
 CASE WHEN {{coverage:orders}}=1 AND {{coverage:customers}}=1 THEN COALESCE(d.customers,0) END customers,
 CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:credit_notes}}=1 THEN COALESCE(d.gross_revenue_cents,0) END gross_revenue_cents,
 CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:credit_notes}}=1 THEN COALESCE(d.discount_cents,0) END discount_cents,
 CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:credit_notes}}=1 THEN COALESCE(c.credit_note_cents,0) END credit_note_cents,
 CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:credit_notes}}=1 THEN COALESCE(d.gross_revenue_cents,0)-COALESCE(d.discount_cents,0)-COALESCE(c.credit_note_cents,0) END net_revenue_cents,
 CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:returns}}=1 AND COALESCE(d.cost_known,1)=1 AND COALESCE(r.cost_known,1)=1 THEN COALESCE(d.delivered_cogs_cents,0)-COALESCE(r.restock_cogs_reversal_cents,0) END cogs_cents,
 CASE WHEN {{coverage:funnel}}=1 THEN COALESCE(m.marketing_spend_cents,0) END marketing_spend_cents,
 1 AS attribution_unknown,CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:credit_notes}}=1 THEN 1 ELSE 0 END revenue_coverage_known
FROM dimensions x LEFT JOIN delivered d ON d.channel=x.channel AND d.campaign_id=x.campaign_id LEFT JOIN credits c ON c.channel=x.channel AND c.campaign_id=x.campaign_id LEFT JOIN restocks r ON r.channel=x.channel AND r.campaign_id=x.campaign_id LEFT JOIN marketing m ON m.channel=x.channel AND m.campaign_id=x.campaign_id ORDER BY x.channel,x.campaign_id
