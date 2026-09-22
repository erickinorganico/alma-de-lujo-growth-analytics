WITH latest_count AS (
 SELECT variant_id,date,counted_qty FROM (SELECT c.*,ROW_NUMBER() OVER(PARTITION BY variant_id ORDER BY date DESC,id DESC) rn FROM inventory_counts c) WHERE rn=1
), ledger_now AS (SELECT variant_id,SUM(quantity) on_hand_qty FROM movements GROUP BY variant_id),
ledger_at_count AS (SELECT c.variant_id,c.date,SUM(m.quantity) qty FROM latest_count c LEFT JOIN movements m ON m.variant_id=c.variant_id AND m.date<=c.date GROUP BY c.variant_id,c.date),
reserve AS (SELECT i.variant_id,SUM(r.quantity) qty FROM reservations r JOIN order_items i ON i.id=r.order_item_id WHERE r.status='active' GROUP BY i.variant_id),
transit AS (SELECT variant_id,SUM(ordered_qty-received_qty) qty FROM purchase_orders WHERE status<>'cancelled' GROUP BY variant_id),
net_sold AS (
 SELECT i.variant_id,SUM(i.quantity) qty FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.status='delivered' AND o.delivered_date>date((SELECT json_extract(value,'$.as_of') FROM warehouse_manifest WHERE key='metadata'),'-30 day') GROUP BY i.variant_id
 UNION ALL SELECT i.variant_id,-SUM(r.quantity) FROM returns r JOIN order_items i ON i.id=r.order_item_id WHERE r.restock=1 AND r.date>date((SELECT json_extract(value,'$.as_of') FROM warehouse_manifest WHERE key='metadata'),'-30 day') GROUP BY i.variant_id
), sold AS (SELECT variant_id,SUM(qty) qty FROM net_sold GROUP BY variant_id)
SELECT v.id variant_id,v.product_id,p.name product_name,p.category,p.lifecycle,v.color,v.size,v.cost_cents,
 CASE WHEN {{coverage:movements}}=1 THEN COALESCE(ln.on_hand_qty,0) END ledger_on_hand_qty,
 CASE WHEN {{coverage:reservations}}=1 AND {{coverage:order_items}}=1 THEN COALESCE(r.qty,0) END reserved_qty,
 CASE WHEN {{coverage:movements}}=1 AND {{coverage:reservations}}=1 AND {{coverage:order_items}}=1 THEN COALESCE(ln.on_hand_qty,0)-COALESCE(r.qty,0) END available_qty,
 CASE WHEN {{coverage:purchase_orders}}=1 THEN COALESCE(t.qty,0) END in_transit_qty,
 lc.date count_date,CASE WHEN {{coverage:inventory_counts}}=1 THEN lc.counted_qty END counted_qty,CASE WHEN {{coverage:inventory_counts}}=1 AND {{coverage:movements}}=1 AND lc.date IS NOT NULL THEN lc.counted_qty-lc2.qty END count_discrepancy_qty,
 CASE WHEN {{coverage:movements}}=1 AND v.cost_cents IS NOT NULL THEN COALESCE(ln.on_hand_qty,0)*v.cost_cents END inventory_value_cents,
 CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:returns}}=1 THEN COALESCE(s.qty,0) END trailing_30d_net_sold_qty,
 CASE WHEN {{coverage:movements}}=1 AND {{coverage:reservations}}=1 AND {{coverage:order_items}}=1 AND {{coverage:orders}}=1 AND {{coverage:returns}}=1 AND COALESCE(s.qty,0)>0 THEN ROUND((COALESCE(ln.on_hand_qty,0)-COALESCE(r.qty,0))*30.0/s.qty,2) END cover_days,
 CASE WHEN {{coverage:products}}=0 OR {{coverage:variants}}=0 OR {{coverage:movements}}=0 OR {{coverage:reservations}}=0 OR {{coverage:order_items}}=0 THEN 'UNKNOWN' WHEN p.lifecycle IN ('idea','sample') THEN 'PRELAUNCH' WHEN COALESCE(ln.on_hand_qty,0)-COALESCE(r.qty,0)<=0 THEN 'STOCKOUT' ELSE 'AVAILABLE' END stock_status,
 CASE WHEN {{coverage:products}}=1 AND {{coverage:variants}}=1 AND {{coverage:movements}}=1 AND {{coverage:reservations}}=1 AND {{coverage:order_items}}=1 THEN 1 ELSE 0 END inventory_coverage_known
FROM variants v JOIN products p ON p.id=v.product_id LEFT JOIN ledger_now ln ON ln.variant_id=v.id LEFT JOIN reserve r ON r.variant_id=v.id LEFT JOIN transit t ON t.variant_id=v.id LEFT JOIN latest_count lc ON lc.variant_id=v.id LEFT JOIN ledger_at_count lc2 ON lc2.variant_id=v.id AND lc2.date=lc.date LEFT JOIN sold s ON s.variant_id=v.id ORDER BY v.id
