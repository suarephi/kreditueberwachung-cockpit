-- 005_views.sql

CREATE VIEW v_current_valuation AS
  SELECT v.*
    FROM valuation v
   WHERE v.is_current = 1;

CREATE VIEW v_loan_overview AS
  SELECT l.loan_id,
         c.client_id,
         c.first_name || ' ' || c.last_name AS client_name,
         a.canton,
         a.city,
         p.object_type,
         p.living_area_sqm,
         vc.market_value,
         vc.mortgage_lending_value,
         l.current_outstanding,
         l.ltv_pct,
         l.dsti_pct,
         l.status            AS loan_status,
         rm.rating_internal,
         rm.watchlist_flag,
         rm.npl_flag,
         rm.expected_loss
    FROM loan l
    JOIN client   c  ON c.client_id    = l.primary_client_id
    JOIN property p  ON p.property_id  = l.property_id
    JOIN address  a  ON a.address_id   = p.address_id
    LEFT JOIN v_current_valuation vc ON vc.property_id = p.property_id
    LEFT JOIN risk_metrics rm        ON rm.loan_id     = l.loan_id;

CREATE VIEW v_open_events AS
  SELECT e.event_id, e.event_type, e.severity, e.status, e.detected_at,
         e.sla_due_date, e.assigned_to, e.title,
         e.loan_id, e.client_id, e.property_id
    FROM event e
   WHERE e.status IN ('open','in_progress','escalated');

CREATE VIEW v_watchlist AS
  SELECT l.loan_id, c.last_name, c.first_name, l.ltv_pct, l.dsti_pct,
         rm.expected_loss, rm.rating_internal, rm.npl_flag, rm.forbearance_flag
    FROM loan l
    JOIN client c   ON c.client_id = l.primary_client_id
    JOIN risk_metrics rm ON rm.loan_id = l.loan_id
   WHERE rm.watchlist_flag = 1 OR rm.npl_flag = 1;

CREATE VIEW v_portfolio_kpis AS
  SELECT COUNT(*)                                                   AS n_loans,
         ROUND(SUM(current_outstanding)/1e6, 1)                     AS total_outstanding_mchf,
         ROUND(AVG(ltv_pct), 2)                                     AS avg_ltv,
         ROUND(AVG(dsti_pct), 2)                                    AS avg_dsti,
         SUM(CASE WHEN ltv_pct > 80 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS share_ltv_gt80,
         SUM(CASE WHEN dsti_pct > 33 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS share_dsti_gt33
    FROM loan;
