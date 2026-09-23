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
