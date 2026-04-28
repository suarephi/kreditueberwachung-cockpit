.mode column
.headers on

.print "=== Portfolio EL by scenario at horizon end ==="
SELECT m.scenario_id,
       ROUND(SUM(m.stressed_expected_loss)/1e6,2) el_mchf,
       ROUND(SUM(m.exposure_at_default_chf)/1e6,1) exposure_mchf
  FROM stress_loan_metrics m
  JOIN (SELECT scenario_id, MAX(period) p FROM stress_loan_metrics GROUP BY 1) mx
       ON mx.scenario_id=m.scenario_id AND mx.p=m.period
 GROUP BY m.scenario_id
 ORDER BY el_mchf DESC;

.print
.print "=== Loans flipping active → covenant breach (severe correction) ==="
SELECT COUNT(*) AS new_breaches
  FROM v_stress_loan_compare
 WHERE scenario_id='severe_correction_25'
   AND base_breach=0 AND stressed_breach=1
   AND period=(SELECT MAX(period) FROM stress_loan_metrics WHERE scenario_id='severe_correction_25');

.print
.print "=== Top-10 LTV jumps under combined adverse ==="
SELECT loan_id,
       ROUND(base_ltv,1) base_ltv,
       ROUND(stressed_ltv,1) stressed_ltv,
       ROUND(stressed_ltv-base_ltv,1) jump
  FROM v_stress_loan_compare
 WHERE scenario_id='combined_adverse'
   AND period=(SELECT MAX(period) FROM stress_loan_metrics WHERE scenario_id='combined_adverse')
 ORDER BY jump DESC LIMIT 10;

.print
.print "=== Regional concentration of LTV breaches (severe correction) ==="
SELECT a.canton, COUNT(*) n_breach
  FROM stress_event e
  JOIN loan l USING(loan_id)
  JOIN property p USING(property_id)
  JOIN address  a ON a.address_id = p.address_id
 WHERE e.scenario_id='severe_correction_25'
   AND e.event_type='ltv_trigger_breach'
 GROUP BY 1 ORDER BY 2 DESC;

.print
.print "=== KPI snapshot (last period) ==="
SELECT scenario_id, period,
       ROUND(total_exposure/1e6,1) exposure_mchf,
       ROUND(expected_loss_total/1e6,2) el_mchf,
       ROUND(weighted_avg_ltv,1) avg_ltv,
       ROUND(share_ltv_gt80*100,1) pct_ltv_gt80,
       ROUND(share_dsti_gt33*100,1) pct_dsti_gt33
  FROM v_stress_summary
 WHERE period=(SELECT MAX(period) FROM stress_loan_metrics m WHERE m.scenario_id=v_stress_summary.scenario_id)
 ORDER BY el_mchf DESC;

.print
.print "=== Stress events by type & scenario ==="
SELECT scenario_id, event_type, COUNT(*) n
  FROM stress_event
 GROUP BY 1,2 ORDER BY 1, 3 DESC;
