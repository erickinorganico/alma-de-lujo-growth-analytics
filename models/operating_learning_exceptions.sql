-- name: sales_by_cohort
SELECT sales_date, sku_id, channel_code, delivery_cohort_id,
       SUM(delivered_units) AS delivered_units,
       SUM(returned_units) AS returned_units,
       SUM(restocked_units) AS restocked_units,
       MIN(coverage_status) AS coverage_status,
       MIN(source_ref) AS source_ref
FROM sales_aggregates
WHERE sku_id=:sku AND sales_date>=:start AND sales_date<:end
GROUP BY sales_date, sku_id, channel_code, delivery_cohort_id
ORDER BY sales_date, channel_code;

-- name: opening_count
SELECT count_id, cutoff_date, on_hand_units, non_sellable_units,
       reserved_units, source_ref
FROM inventory_counts
WHERE sku_id=:sku AND cutoff_date<=:start
ORDER BY cutoff_date DESC LIMIT 1;

-- name: accepted_receipts
SELECT r.receipt_id, r.received_date, r.accepted_units, r.inspection_units,
       r.rejected_units, r.source_ref
FROM purchase_receipts AS r
JOIN purchase_orders AS p ON p.purchase_order_id=r.purchase_order_id
WHERE p.sku_id=:sku AND r.received_date>=:start AND r.received_date<:end
ORDER BY r.received_date,r.receipt_id;

-- name: physical_restocks
SELECT movement_id, event_date, quality_event_id, units, source_ref
FROM inventory_movements
WHERE sku_id=:sku AND movement_type='RETURN_RESTOCK'
  AND event_date>=:start AND event_date<:end
ORDER BY event_date,movement_id;

-- name: quality_events
SELECT quality_event_id, sku_id, receipt_id, delivery_cohort_id,
       event_date, event_type, units, reason_code, resolution_code, source_ref
FROM quality_events
WHERE sku_id=:sku AND event_date<=:as_of
ORDER BY event_date,quality_event_id;

-- name: availability
SELECT availability_date, observed_minutes, sellable_minutes,
       stockout_minutes, coverage_status, source_ref
FROM availability_daily
WHERE sku_id=:sku AND availability_date>=:start AND availability_date<:end
ORDER BY availability_date;

-- name: unmet
SELECT demand_event_id, event_date, sku_id, channel_code,
       requested_units, reason_code, source_ref
FROM unmet_demand
WHERE sku_id=:sku AND event_date>=:start AND event_date<:end
ORDER BY event_date,demand_event_id;

-- name: sku_identity
SELECT sku_id, product_code, variant_code, category_code, size_code
FROM sku_catalog WHERE sku_id=:sku;

-- name: product_variants
SELECT sku_id, variant_code FROM sku_catalog
WHERE product_code=:product_code AND lifecycle_status='ACTIVE'
ORDER BY sku_id;

-- name: variant_sales
SELECT s.sku_id, s.channel_code, SUM(s.delivered_units) AS delivered_units,
       MIN(s.coverage_status) AS coverage_status
FROM sales_aggregates AS s
JOIN sku_catalog AS k ON k.sku_id=s.sku_id
WHERE k.product_code=:product_code AND s.sales_date>=:start AND s.sales_date<:end
GROUP BY s.sku_id,s.channel_code
ORDER BY s.channel_code,s.sku_id;

-- name: variant_availability
SELECT a.sku_id, COUNT(*) AS observed_days,
       SUM(a.observed_minutes) AS observed_minutes,
       SUM(a.stockout_minutes) AS stockout_minutes,
       MIN(a.coverage_status) AS coverage_status
FROM availability_daily AS a
JOIN sku_catalog AS k ON k.sku_id=a.sku_id
WHERE k.product_code=:product_code AND a.availability_date>=:start AND a.availability_date<:end
GROUP BY a.sku_id ORDER BY a.sku_id;

-- name: variant_prices
SELECT v.sku_id, v.public_price_cents FROM cost_versions AS v
JOIN sku_catalog AS k ON k.sku_id=v.sku_id
WHERE k.product_code=:product_code AND v.lifecycle_status='ACTIVE'
  AND v.effective_date=(
    SELECT MAX(v2.effective_date) FROM cost_versions AS v2
    WHERE v2.sku_id=v.sku_id AND v2.lifecycle_status='ACTIVE'
      AND v2.effective_date<=:as_of)
ORDER BY v.sku_id;

-- name: readiness_latest
SELECT s.sku_id, s.effective_date, s.readiness_status,
       s.missing_info_code, s.source_ref
FROM sales_readiness AS s
WHERE s.effective_date<=:as_of AND s.effective_date=(
  SELECT MAX(s2.effective_date) FROM sales_readiness AS s2
  WHERE s2.sku_id=s.sku_id AND s2.effective_date<=:as_of)
ORDER BY s.sku_id;

-- name: pending_receipts
SELECT r.receipt_id, p.sku_id, r.received_date,
       r.inspection_units, r.source_ref
FROM purchase_receipts AS r
JOIN purchase_orders AS p ON p.purchase_order_id=r.purchase_order_id
WHERE r.received_date<=:as_of AND r.inspection_units>0
ORDER BY r.receipt_id;

-- name: all_quality
SELECT quality_event_id, sku_id, receipt_id, delivery_cohort_id,
       event_date, event_type, units, reason_code, resolution_code, source_ref
FROM quality_events
WHERE event_date<=:as_of
ORDER BY quality_event_id;

-- name: all_loans
SELECT loan_id, sku_id, quantity, borrowed_date, due_date,
       returned_date, status_code, condition_code, source_ref
FROM loans WHERE borrowed_date<=:as_of ORDER BY loan_id;

-- name: loan_return_movements
SELECT loan_id, SUM(units) AS returned_units
FROM inventory_movements
WHERE movement_type='LOAN_IN' AND event_date<=:as_of
GROUP BY loan_id;
