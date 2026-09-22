SELECT 'sales_net_revenue' check_id,
 (SELECT COALESCE(SUM(i.quantity*i.unit_price_cents-i.discount_cents),0) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='delivered')-(SELECT COALESCE(SUM(amount_cents),0) FROM credit_notes) source_cents,
 (SELECT COALESCE(SUM(net_revenue_cents),0) FROM sales_daily) mart_cents
UNION ALL SELECT 'cash_in',(SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE status='settled'),(SELECT COALESCE(SUM(cash_in_cents),0) FROM cash_daily)
UNION ALL SELECT 'cash_out',(SELECT COALESCE(SUM(amount_cents),0) FROM refunds WHERE status='settled')+(SELECT COALESCE(SUM(amount_cents),0) FROM supplier_payments)+(SELECT COALESCE(SUM(amount_cents),0) FROM expense_payments),(SELECT COALESCE(SUM(refund_out_cents+supplier_out_cents+expense_out_cents),0) FROM cash_daily)
UNION ALL SELECT 'purchase_receipts',(SELECT COALESCE(SUM(received_qty),0) FROM purchase_orders),(SELECT COALESCE(SUM(receipt_event_qty),0) FROM procurement)
UNION ALL SELECT 'supplier_payments',(SELECT COALESCE(SUM(paid_cents),0) FROM purchase_orders),(SELECT COALESCE(SUM(supplier_payment_event_cents),0) FROM procurement)
UNION ALL SELECT 'marketing_spend',(SELECT COALESCE(SUM(spend_cents),0) FROM funnel),(SELECT COALESCE(SUM(marketing_spend_cents),0) FROM channel_performance)
