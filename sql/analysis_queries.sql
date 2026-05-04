-- ============================================================
-- DELIVERY IMPACT ANALYSIS — SQL Queries
-- Table: clean_orders
-- ============================================================

-- ============================================================
-- 1. OVERALL KPI COMPARISON: Before vs After
-- ============================================================
SELECT
    period,
    COUNT(order_id)                                          AS total_orders,
    ROUND(AVG(delivery_time_min), 2)                        AS avg_delivery_time,
    ROUND(AVG(CASE WHEN on_time_flag = 1 THEN 1.0 ELSE 0 END) * 100, 1) AS on_time_pct,
    ROUND(AVG(CASE WHEN cancelled_flag = 1 THEN 1.0 ELSE 0 END) * 100, 2) AS cancel_rate_pct,
    ROUND(AVG(CASE WHEN sla_breach = 1 THEN 1.0 ELSE 0 END) * 100, 1) AS sla_breach_pct,
    ROUND(AVG(customer_rating), 2)                          AS avg_rating
FROM clean_orders
GROUP BY period
ORDER BY period DESC;


-- ============================================================
-- 2. PEAK VS NON-PEAK BREAKDOWN
-- ============================================================
SELECT
    period,
    peak_flag,
    COUNT(order_id)                            AS total_orders,
    ROUND(AVG(delivery_time_min), 2)           AS avg_delivery_time,
    ROUND(AVG(on_time_flag) * 100, 1)          AS on_time_pct
FROM clean_orders
GROUP BY period, peak_flag
ORDER BY period DESC, peak_flag;


-- ============================================================
-- 3. ZONE-WISE PERFORMANCE
-- ============================================================
SELECT
    period,
    zone,
    COUNT(order_id)                            AS total_orders,
    ROUND(AVG(delivery_time_min), 2)           AS avg_delivery_time,
    ROUND(AVG(cancelled_flag) * 100, 2)        AS cancel_rate_pct
FROM clean_orders
GROUP BY period, zone
ORDER BY period DESC, zone;


-- ============================================================
-- 4. DISTANCE BUCKET ANALYSIS
-- ============================================================
SELECT
    period,
    distance_bucket,
    COUNT(order_id)                             AS total_orders,
    ROUND(AVG(delivery_time_min), 2)            AS avg_delivery_time,
    ROUND(AVG(sla_breach) * 100, 1)             AS sla_breach_pct
FROM clean_orders
GROUP BY period, distance_bucket
ORDER BY period DESC,
    CASE distance_bucket
        WHEN 'Short (0-3 km)'   THEN 1
        WHEN 'Medium (3-7 km)'  THEN 2
        WHEN 'Long (7+ km)'     THEN 3
    END;


-- ============================================================
-- 5. TOP 10 WORST PERFORMING RIDERS (Post-Feature Removal)
-- ============================================================
SELECT
    rider_id,
    COUNT(order_id)                            AS total_orders,
    ROUND(AVG(delivery_time_min), 2)           AS avg_delivery_time,
    ROUND(AVG(cancelled_flag) * 100, 1)        AS cancel_rate_pct
FROM clean_orders
WHERE period = 'After'
GROUP BY rider_id
HAVING COUNT(order_id) >= 30
ORDER BY avg_delivery_time DESC
LIMIT 10;


-- ============================================================
-- 6. DAILY AVERAGE TREND
-- ============================================================
SELECT
    order_date,
    period,
    COUNT(order_id)                            AS total_orders,
    ROUND(AVG(delivery_time_min), 2)           AS avg_delivery_time,
    ROUND(AVG(on_time_flag) * 100, 1)          AS on_time_pct
FROM clean_orders
GROUP BY order_date, period
ORDER BY order_date;


-- ============================================================
-- 7. COMBINED STRESS SCENARIO: Peak + Long Distance + Low Zone
-- ============================================================
SELECT
    period,
    COUNT(order_id)                            AS total_orders,
    ROUND(AVG(delivery_time_min), 2)           AS avg_delivery_time,
    ROUND(AVG(cancelled_flag) * 100, 1)        AS cancel_pct
FROM clean_orders
WHERE peak_flag = 'Peak'
  AND distance_bucket = 'Long (7+ km)'
  AND zone = 'Low'
GROUP BY period
ORDER BY period DESC;


-- ============================================================
-- 8. ESTIMATED REVENUE IMPACT (Hypothetical)
-- Assume: avg order value = ₹350, margin = 15%
-- Lost revenue = extra cancellations × avg order value
-- ============================================================
WITH cancel_counts AS (
    SELECT
        period,
        SUM(cancelled_flag) AS cancelled_orders,
        COUNT(order_id)     AS total_orders
    FROM clean_orders
    GROUP BY period
),
rates AS (
    SELECT
        MAX(CASE WHEN period = 'Before' THEN 1.0 * cancelled_orders / total_orders END) AS cancel_rate_before,
        MAX(CASE WHEN period = 'After'  THEN cancelled_orders END)                      AS cancel_after_count,
        MAX(CASE WHEN period = 'After'  THEN total_orders END)                          AS total_after
    FROM cancel_counts
)
SELECT
    ROUND(cancel_rate_before * 100, 2)                                         AS baseline_cancel_rate_pct,
    ROUND((1.0 * cancel_after_count / total_after) * 100, 2)                   AS actual_cancel_rate_pct,
    ROUND((1.0 * cancel_after_count / total_after - cancel_rate_before)
          * total_after, 0)                                                    AS extra_cancellations,
    ROUND((1.0 * cancel_after_count / total_after - cancel_rate_before)
          * total_after * 350 * 0.15, 0)                                       AS estimated_revenue_loss_inr
FROM rates;