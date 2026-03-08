-- Peacock Subscriber Watch Time Analysis
-- Calculates top subscribers by watch time with churn risk indicator

WITH subscriber_activity AS (
    SELECT
        s.subscriber_id,
        s.email,
        s.subscription_tier,
        s.subscription_start_date,
        SUM(w.watch_time_minutes)                    AS total_watch_time_minutes,
        COUNT(DISTINCT w.content_id)                 AS unique_titles_watched,
        COUNT(DISTINCT DATE(w.watched_at))           AS active_days,
        MAX(w.watched_at)                            AS last_watched_at,
        DATEDIFF(day, MAX(w.watched_at), CURRENT_DATE()) AS days_since_last_watch
    FROM
        subscribers s
        LEFT JOIN watch_history w ON s.subscriber_id = w.subscriber_id
    WHERE
        s.is_active = TRUE
        AND w.watched_at >= DATEADD(month, -3, CURRENT_DATE())
    GROUP BY
        s.subscriber_id,
        s.email,
        s.subscription_tier,
        s.subscription_start_date
),

churn_risk AS (
    SELECT
        *,
        CASE
            WHEN days_since_last_watch > 30 THEN 'High'
            WHEN days_since_last_watch > 14 THEN 'Medium'
            ELSE 'Low'
        END                                          AS churn_risk_level,
        RANK() OVER (
            PARTITION BY subscription_tier
            ORDER BY total_watch_time_minutes DESC
        )                                            AS rank_within_tier
    FROM subscriber_activity
)

SELECT
    subscriber_id,
    email,
    subscription_tier,
    total_watch_time_minutes,
    ROUND(total_watch_time_minutes / 60, 2)          AS total_watch_time_hours,
    unique_titles_watched,
    active_days,
    days_since_last_watch,
    churn_risk_level,
    rank_within_tier
FROM churn_risk
WHERE rank_within_tier <= 100
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY subscription_tier, churn_risk_level
    ORDER BY total_watch_time_minutes DESC
) <= 10
ORDER BY
    subscription_tier,
    churn_risk_level,
    total_watch_time_minutes DESC;
