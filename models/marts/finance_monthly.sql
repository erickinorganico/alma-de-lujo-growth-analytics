WITH known AS (
 SELECT CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:credit_notes}}=1 THEN 1 ELSE 0 END revenue_known,
        CASE WHEN {{coverage:orders}}=1 AND {{coverage:order_items}}=1 AND {{coverage:returns}}=1 THEN 1 ELSE 0 END cost_source_known,
        CASE WHEN {{coverage:expenses}}=1 THEN 1 ELSE 0 END expense_known,
        CASE WHEN {{coverage:payments}}=1 AND {{coverage:refunds}}=1 AND {{coverage:supplier_payments}}=1 AND {{coverage:expense_payments}}=1 THEN 1 ELSE 0 END cash_known
), spine AS (SELECT substr(date,1,7) month FROM sales_daily UNION SELECT substr(date,1,7) FROM expenses UNION SELECT substr(date,1,7) FROM cash_daily),
sales AS (SELECT substr(date,1,7) month,SUM(net_revenue_cents) net_revenue_cents,SUM(cogs_cents) cogs_cents,MIN(cost_coverage_known) cost_coverage_known FROM sales_daily GROUP BY 1),
expense_rollup AS (SELECT substr(date,1,7) month,SUM(amount_cents) expense_accrual_cents,SUM(CASE WHEN variable=1 THEN amount_cents ELSE 0 END) variable_expense_cents FROM expenses GROUP BY 1),
cash AS (SELECT substr(date,1,7) month,SUM(net_cash_change_cents) net_cash_change_cents FROM cash_daily GROUP BY 1),
computed AS (SELECT sp.month,k.*,s.net_revenue_cents,s.cogs_cents,COALESCE(s.cost_coverage_known,1) row_cost_known,e.variable_expense_cents,e.expense_accrual_cents,c.net_cash_change_cents FROM spine sp CROSS JOIN known k LEFT JOIN sales s ON s.month=sp.month LEFT JOIN expense_rollup e ON e.month=sp.month LEFT JOIN cash c ON c.month=sp.month)
SELECT month,CASE WHEN revenue_known=1 THEN COALESCE(net_revenue_cents,0) END net_revenue_cents,
 CASE WHEN cost_source_known=1 AND row_cost_known=1 THEN COALESCE(cogs_cents,0) END cogs_cents,
 CASE WHEN revenue_known=1 AND cost_source_known=1 AND row_cost_known=1 THEN COALESCE(net_revenue_cents,0)-COALESCE(cogs_cents,0) END gross_profit_cents,
 CASE WHEN expense_known=1 THEN COALESCE(variable_expense_cents,0) END variable_expense_cents,CASE WHEN expense_known=1 THEN COALESCE(expense_accrual_cents,0) END expense_accrual_cents,
 CASE WHEN revenue_known=1 AND cost_source_known=1 AND row_cost_known=1 AND expense_known=1 THEN COALESCE(net_revenue_cents,0)-COALESCE(cogs_cents,0)-COALESCE(variable_expense_cents,0) END contribution_after_variable_cents,
 CASE WHEN revenue_known=1 AND cost_source_known=1 AND row_cost_known=1 AND expense_known=1 THEN COALESCE(net_revenue_cents,0)-COALESCE(cogs_cents,0)-COALESCE(expense_accrual_cents,0) END operating_after_all_expenses_cents,
 CASE WHEN cash_known=1 THEN COALESCE(net_cash_change_cents,0) END net_cash_change_cents,revenue_known AS revenue_coverage_known,
 CASE WHEN cost_source_known=1 AND row_cost_known=1 THEN 1 ELSE 0 END cost_coverage_known,expense_known AS expense_coverage_known,cash_known AS cash_coverage_known FROM computed ORDER BY month
