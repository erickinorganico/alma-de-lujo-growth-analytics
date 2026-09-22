SELECT po.id purchase_order_id,po.date ordered_date,po.supplier_id,po.variant_id,po.ordered_qty,po.received_qty,po.ordered_qty-po.received_qty open_qty,
 po.unit_cost_cents,po.ordered_qty*po.unit_cost_cents ordered_value_cents,po.paid_cents,
 CASE WHEN {{coverage:purchase_receipts}}=1 THEN COALESCE(r.receipt_qty,0) END receipt_event_qty,
 CASE WHEN {{coverage:supplier_payments}}=1 THEN COALESCE(p.payment_cents,0) END supplier_payment_event_cents,
 CASE WHEN {{coverage:purchase_receipts}}=1 AND {{coverage:supplier_payments}}=1 AND po.received_qty=COALESCE(r.receipt_qty,0) AND po.paid_cents=COALESCE(p.payment_cents,0) THEN 1 ELSE 0 END reconciled,
 CASE WHEN {{coverage:purchase_orders}}=1 AND {{coverage:purchase_receipts}}=1 AND {{coverage:supplier_payments}}=1 THEN 1 ELSE 0 END coverage_known
FROM purchase_orders po LEFT JOIN (SELECT purchase_order_id,SUM(quantity) receipt_qty FROM purchase_receipts GROUP BY purchase_order_id) r ON r.purchase_order_id=po.id
LEFT JOIN (SELECT purchase_order_id,SUM(amount_cents) payment_cents FROM supplier_payments GROUP BY purchase_order_id) p ON p.purchase_order_id=po.id ORDER BY po.date,po.id
