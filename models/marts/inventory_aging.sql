WITH positive_events AS (SELECT variant_id,MAX(date) last_inbound_date FROM movements WHERE quantity>0 GROUP BY variant_id)
SELECT p.*,e.last_inbound_date,
 CASE WHEN p.inventory_coverage_known=1 AND e.last_inbound_date IS NOT NULL THEN CAST(julianday((SELECT json_extract(value,'$.as_of') FROM warehouse_manifest WHERE key='metadata'))-julianday(e.last_inbound_date) AS INTEGER) END days_since_last_inbound
FROM inventory_position p LEFT JOIN positive_events e ON e.variant_id=p.variant_id ORDER BY p.variant_id
