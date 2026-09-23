-- name: cost_components
SELECT c.component_id, c.cost_version_id, c.component_code, c.classification,
       c.amount_cents, c.required_flag, c.quality_status,
       c.included_in_component_id, c.source_ref
FROM cost_components AS c
WHERE c.cost_version_id = :cost_version_id
ORDER BY c.component_id;

-- name: cost_allocations
SELECT a.allocation_id, a.component_id, a.sku_id,
       SUM(a.allocated_cents) AS allocated_cents,
       SUM(a.remainder_cents) AS remainder_cents,
       a.source_ref
FROM cost_allocations AS a
WHERE a.component_id IN (
  SELECT c.component_id FROM cost_components AS c
  WHERE c.cost_version_id = :cost_version_id
)
GROUP BY a.allocation_id, a.component_id, a.sku_id, a.source_ref
ORDER BY a.component_id, a.allocation_id;

-- name: purchase_receipts
SELECT p.purchase_order_id, p.sku_id, p.ordered_units, p.status_code,
       COALESCE(SUM(r.received_units), 0) AS received_units,
       COALESCE(SUM(r.inspection_units), 0) AS inspection_units,
       COALESCE(SUM(r.accepted_units), 0) AS accepted_units,
       COALESCE(SUM(r.rejected_units), 0) AS rejected_units
FROM purchase_orders AS p
LEFT JOIN purchase_receipts AS r
  ON r.purchase_order_id = p.purchase_order_id AND r.received_date <= :as_of
WHERE p.order_date <= :as_of
GROUP BY p.purchase_order_id, p.sku_id, p.ordered_units, p.status_code
ORDER BY p.purchase_order_id;
