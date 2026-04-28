-- Sample queries against the base dataset.
.mode column
.headers on

.print "=== Portfolio overview ==="
SELECT * FROM v_portfolio_kpis;

.print
.print "=== Top 10 cantons by exposure ==="
SELECT a.canton, COUNT(*) n_loans,
       ROUND(SUM(l.current_outstanding)/1e6,1) outstanding_mchf,
       ROUND(AVG(l.ltv_pct),1) avg_ltv
  FROM loan l
  JOIN property p USING(property_id)
  JOIN address  a ON a.address_id = p.address_id
 GROUP BY 1 ORDER BY outstanding_mchf DESC LIMIT 10;

.print
.print "=== Per-object-type CHF/m² of current valuations ==="
SELECT p.object_type,
       COUNT(*)                                                  n,
       ROUND(AVG(v.market_value/p.living_area_sqm))              chf_per_sqm,
       ROUND(MIN(v.market_value/p.living_area_sqm))              min_chf_sqm,
       ROUND(MAX(v.market_value/p.living_area_sqm))              max_chf_sqm
  FROM v_current_valuation v
  JOIN property p USING(property_id)
 WHERE p.living_area_sqm > 0
 GROUP BY 1 ORDER BY chf_per_sqm DESC;

.print
.print "=== Watchlist (top 10) ==="
SELECT * FROM v_watchlist ORDER BY expected_loss DESC LIMIT 10;

.print
.print "=== Open events by severity ==="
SELECT severity, COUNT(*) n FROM v_open_events GROUP BY 1 ORDER BY 2 DESC;

.print
.print "=== Event types most frequent ==="
SELECT event_type, COUNT(*) n FROM event GROUP BY 1 ORDER BY 2 DESC LIMIT 12;

.print
.print "=== Data quality: PLZ ↔ canton mismatch ==="
SELECT a.address_id, a.postal_code, a.city, a.canton, pc.canton_code AS expected
  FROM address a
  JOIN postal_code pc ON pc.postal_code = a.postal_code
 WHERE a.canton <> pc.canton_code AND length(a.canton)=2
 LIMIT 10;

.print
.print "=== Data quality: birth_date dot-format ==="
SELECT client_id, last_name, birth_date FROM client
 WHERE birth_date LIKE '%.%' LIMIT 10;
