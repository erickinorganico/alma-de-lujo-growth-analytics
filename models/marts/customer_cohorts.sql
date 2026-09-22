WITH first_date AS (SELECT customer_id,MIN(delivered_date) first_delivered_date FROM orders WHERE status='delivered' GROUP BY customer_id),
first_delivery AS (SELECT d.customer_id,d.first_delivered_date,MIN(o.id) first_order_id FROM first_date d JOIN orders o ON o.customer_id=d.customer_id AND o.status='delivered' AND o.delivered_date=d.first_delivered_date GROUP BY d.customer_id,d.first_delivered_date),
customer_orders AS (
 SELECT f.customer_id,f.first_delivered_date,
        CASE WHEN f.first_delivered_date<=date((SELECT json_extract(value,'$.as_of') FROM warehouse_manifest WHERE key='metadata'),'-30 day') THEN 1 ELSE 0 END mature_30d,
        COUNT(DISTINCT CASE WHEN o.id<>f.first_order_id AND o.delivered_date>=f.first_delivered_date AND o.delivered_date<=date(f.first_delivered_date,'+30 day') THEN o.id END) repeat_orders_30d
 FROM first_delivery f LEFT JOIN orders o ON o.customer_id=f.customer_id AND o.status='delivered' GROUP BY f.customer_id,f.first_delivered_date,f.first_order_id
)
SELECT substr(first_delivered_date,1,7) cohort_month,
 CASE WHEN {{coverage:customers}}=1 AND {{coverage:orders}}=1 THEN COUNT(*) END cohort_customers,
 CASE WHEN {{coverage:customers}}=1 AND {{coverage:orders}}=1 THEN SUM(mature_30d) END eligible_customers_30d,
 CASE WHEN {{coverage:customers}}=1 AND {{coverage:orders}}=1 THEN SUM(CASE WHEN mature_30d=0 THEN 1 ELSE 0 END) END immature_customers,
 CASE WHEN {{coverage:customers}}=1 AND {{coverage:orders}}=1 AND SUM(mature_30d)>0 THEN SUM(CASE WHEN mature_30d=1 AND repeat_orders_30d>0 THEN 1 ELSE 0 END) END repeat_within_30d_customers,
 CASE WHEN {{coverage:customers}}=1 AND {{coverage:orders}}=1 AND SUM(mature_30d)>0 THEN ROUND(1.0*SUM(CASE WHEN mature_30d=1 AND repeat_orders_30d>0 THEN 1 ELSE 0 END)/SUM(mature_30d),4) END repeat_within_30d_rate,
 CASE WHEN {{coverage:customers}}=1 AND {{coverage:orders}}=1 THEN 1 ELSE 0 END cohort_coverage_known
FROM customer_orders GROUP BY cohort_month ORDER BY cohort_month
