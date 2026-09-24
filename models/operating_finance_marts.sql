-- name: obligations
SELECT obligation_id, origin_type, origin_id, due_date, original_cents,
       currency, status_code, source_ref
FROM obligations
ORDER BY obligation_id;

-- name: payments_by_id
SELECT payment_id, obligation_id, paid_date,
       SUM(amount_cents) AS amount_cents, source_ref
FROM obligation_payments
WHERE paid_date <= :as_of
GROUP BY payment_id, obligation_id, paid_date, source_ref
ORDER BY payment_id;

-- name: cash_events
SELECT event_id, economic_event_id, supersedes_event_id, scenario_id, event_date,
       level, direction, amount_cents, currency, obligation_id, payment_id, source_ref
FROM cash_events
ORDER BY scenario_id, economic_event_id, event_id;

-- name: cash_balance_evidence
SELECT balance_evidence_id, scenario_id, period_start, period_end,
       opening_balance_cents, closing_balance_cents, opening_observed_at,
       closing_observed_at, evidence_status, source_ref
FROM cash_balance_evidence
WHERE scenario_id = :scenario_id AND period_start <= :as_of AND period_end >= :as_of
ORDER BY period_start DESC, balance_evidence_id;

-- name: budgets
SELECT budget_id, period_start, period_end, drop_code, channel_code,
       approved_cents, source_ref
FROM budgets
WHERE period_start <= :as_of AND period_end > :as_of
ORDER BY budget_id;

-- name: budgets_all
SELECT budget_id, period_start, period_end, drop_code, channel_code,
       approved_cents, source_ref
FROM budgets
ORDER BY budget_id;

-- name: budget_allocations
SELECT budget_allocation_id, budget_id, origin_type, origin_id,
       drop_code, channel_code, allocated_cents, source_ref
FROM budget_allocations
ORDER BY origin_type, origin_id, budget_id, drop_code, channel_code;

-- name: purchase_sources
SELECT purchase_order_id, budget_id, ordered_units, agreed_unit_cents,
       order_date, status_code, source_ref
FROM purchase_orders
WHERE order_date <= :as_of
ORDER BY purchase_order_id;

-- name: purchase_receipt_totals
SELECT purchase_order_id, SUM(received_units) AS received_units
FROM purchase_receipts
WHERE received_date <= :as_of
GROUP BY purchase_order_id;

-- name: expense_sources
SELECT expense_id, budget_id, incurred_date, amount_cents,
       status_code, source_ref
FROM expenses
WHERE incurred_date <= :as_of
ORDER BY expense_id;
