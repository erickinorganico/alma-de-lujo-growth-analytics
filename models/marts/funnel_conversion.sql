WITH cohorts AS (
 SELECT channel,campaign_id FROM sessions UNION SELECT channel,campaign_id FROM leads UNION SELECT channel,campaign_id FROM orders UNION SELECT channel,campaign_id FROM funnel
), session_counts AS (SELECT channel,campaign_id,COUNT(DISTINCT id) sessions FROM sessions GROUP BY channel,campaign_id),
lead_counts AS (SELECT channel,campaign_id,COUNT(DISTINCT id) all_leads,COUNT(DISTINCT CASE WHEN session_id IS NOT NULL THEN id END) linked_leads,COUNT(DISTINCT session_id) linked_sessions,COUNT(DISTINCT CASE WHEN session_id IS NULL THEN id END) unlinked_leads,COUNT(DISTINCT order_id) linked_orders FROM leads GROUP BY channel,campaign_id),
spend AS (SELECT channel,campaign_id,SUM(spend_cents) marketing_spend_cents,MIN(CASE WHEN visits IS NULL THEN 0 ELSE 1 END) visits_coverage_known FROM funnel GROUP BY channel,campaign_id)
SELECT c.channel,c.campaign_id,
 CASE WHEN {{coverage:sessions}}=1 THEN COALESCE(s.sessions,0) END sessions,
 CASE WHEN {{coverage:leads}}=1 THEN COALESCE(l.all_leads,0) END all_leads,CASE WHEN {{coverage:leads}}=1 THEN COALESCE(l.linked_leads,0) END linked_leads,CASE WHEN {{coverage:leads}}=1 THEN COALESCE(l.unlinked_leads,0) END unlinked_leads,CASE WHEN {{coverage:leads}}=1 THEN COALESCE(l.linked_sessions,0) END session_linked_leads,
 CASE WHEN {{coverage:leads}}=1 THEN COALESCE(l.linked_orders,0) END linked_orders,
 CASE WHEN {{coverage:funnel}}=1 THEN f.marketing_spend_cents END marketing_spend_cents,
 CASE WHEN {{coverage:sessions}}=1 AND {{coverage:leads}}=1 AND COALESCE(s.sessions,0)>0 THEN ROUND(1.0*COALESCE(l.linked_sessions,0)/s.sessions,4) END session_to_lead_rate,
 CASE WHEN {{coverage:leads}}=1 AND COALESCE(l.all_leads,0)>0 THEN ROUND(1.0*COALESCE(l.linked_orders,0)/l.all_leads,4) END lead_to_linked_order_rate,
 CASE WHEN {{coverage:sessions}}=1 AND {{coverage:leads}}=1 THEN 1 ELSE 0 END funnel_coverage_known
FROM cohorts c LEFT JOIN session_counts s ON s.channel=c.channel AND s.campaign_id=c.campaign_id LEFT JOIN lead_counts l ON l.channel=c.channel AND l.campaign_id=c.campaign_id LEFT JOIN spend f ON f.channel=c.channel AND f.campaign_id=c.campaign_id ORDER BY c.channel,c.campaign_id
