"""
Stream SQL Processors for RisingWave
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class StreamSQLBuilder:
    """Build RisingWave SQL for stream processing."""

    @staticmethod
    def create_events_source_table() -> str:
        """Create source table for raw events."""
        return """
CREATE TABLE IF NOT EXISTS events_raw (
    event_id VARCHAR,
    event_type VARCHAR,
    event_version VARCHAR,
    source VARCHAR,
    source_version VARCHAR,
    timestamp TIMESTAMP,
    received_at TIMESTAMP,
    correlation_id VARCHAR,
    causation_id VARCHAR,
    tags MAP<VARCHAR, VARCHAR>,
    user_id VARCHAR,
    anonymous_id VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    external_ids MAP<VARCHAR, VARCHAR>,
    ip VARCHAR,
    user_agent VARCHAR,
    locale VARCHAR,
    timezone VARCHAR,
    screen_resolution VARCHAR,
    viewport_size VARCHAR,
    referrer VARCHAR,
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    utm_term VARCHAR,
    utm_content VARCHAR,
    properties MAP<VARCHAR, VARCHAR>,
    page_url VARCHAR,
    page_title VARCHAR,
    page_path VARCHAR,
    duration_ms BIGINT,
    event_name VARCHAR,
    value DOUBLE,
    user_id VARCHAR,
    traits MAP<VARCHAR, VARCHAR>,
    group_id VARCHAR,
    group_traits MAP<VARCHAR, VARCHAR>,
    previous_id VARCHAR,
    screen_name VARCHAR,
    screen_class VARCHAR,
    action VARCHAR,
    products MAP<VARCHAR, VARCHAR>,
    cart_id VARCHAR,
    order_id VARCHAR,
    revenue DOUBLE,
    currency VARCHAR,
    shipping DOUBLE,
    tax DOUBLE,
    discount DOUBLE,
    coupon VARCHAR,
    payment_method VARCHAR,
    shipping_method VARCHAR,
    partition_key VARCHAR,
    headers MAP<VARCHAR, VARCHAR>,
    _kafka_partition INT,
    _kafka_offset BIGINT,
    _kafka_timestamp TIMESTAMP
) WITH (
    connector = 'kafka',
    topic = 'retention.events.raw',
    properties.bootstrap.server = 'localhost:9092',
    properties.group.id = 'risingwave-events',
    scan.startup.mode = 'earliest',
    format = 'json'
);
"""

    @staticmethod
    def create_processed_events_sink() -> str:
        """Create sink table for processed events."""
        return """
CREATE TABLE IF NOT EXISTS events_processed (
    event_id VARCHAR PRIMARY KEY,
    event_type VARCHAR,
    event_version VARCHAR,
    source VARCHAR,
    source_version VARCHAR,
    timestamp TIMESTAMP,
    received_at TIMESTAMP,
    correlation_id VARCHAR,
    causation_id VARCHAR,
    user_id VARCHAR,
    anonymous_id VARCHAR,
    email VARCHAR,
    properties MAP<VARCHAR, VARCHAR>,
    enriched_data MAP<VARCHAR, VARCHAR>,
    derived_properties MAP<VARCHAR, VARCHAR>,
    user_profile MAP<VARCHAR, VARCHAR>,
    session_data MAP<VARCHAR, VARCHAR>,
    attribution MAP<VARCHAR, VARCHAR>,
    predictions MAP<VARCHAR, VARCHAR>,
    anomalies MAP<VARCHAR, VARCHAR>,
    processing_timestamp TIMESTAMP,
    processing_duration_ms BIGINT,
    _kafka_partition INT,
    _kafka_offset BIGINT
) WITH (
    connector = 'kafka',
    topic = 'retention.events.processed',
    properties.bootstrap.server = 'localhost:9092',
    format = 'json'
);
"""

    @staticmethod
    def create_dead_letter_sink() -> str:
        """Create sink table for dead letter queue."""
        return """
CREATE TABLE IF NOT EXISTS events_dlq (
    event_id VARCHAR,
    event_type VARCHAR,
    error VARCHAR,
    error_type VARCHAR,
    retry_count INT,
    first_failed_at TIMESTAMP,
    last_failed_at TIMESTAMP,
    processing_context MAP<VARCHAR, VARCHAR>,
    original_event MAP<VARCHAR, VARCHAR>,
    failed_at TIMESTAMP
) WITH (
    connector = 'kafka',
    topic = 'retention.events.dlq',
    properties.bootstrap.server = 'localhost:9092',
    format = 'json'
);
"""

    @staticmethod
    def create_session_window_aggregation() -> str:
        """Create session window aggregation for user behavior."""
        return """
CREATE MATERIALIZED VIEW IF NOT EXISTS user_sessions AS
SELECT
    user_id,
    session_id,
    session_start,
    session_end,
    event_count,
    page_views,
    total_duration_ms,
    revenue,
    first_page,
    last_page,
    channel,
    device_type,
    country,
    source,
    medium,
    campaign
FROM (
    SELECT
        COALESCE(user_id, anonymous_id) AS user_id,
        session_id,
        MIN(timestamp) AS session_start,
        MAX(timestamp) AS session_end,
        COUNT(*) AS event_count,
        COUNT(CASE WHEN event_type = 'page_view' THEN 1 END) AS page_views,
        SUM(COALESCE(duration_ms, 0)) AS total_duration_ms,
        SUM(COALESCE(revenue, 0)) AS revenue,
        MIN(CASE WHEN event_type = 'page_view' THEN page_path END) AS first_page,
        MAX(CASE WHEN event_type = 'page_view' THEN page_path END) AS last_page,
        MAX(CASE WHEN event_type = 'page_view' THEN utm_source END) AS source,
        MAX(CASE WHEN event_type = 'page_view' THEN utm_medium END) AS medium,
        MAX(CASE WHEN event_type = 'page_view' THEN utm_campaign END) AS campaign,
        MAX(user_agent) AS device_type,
        MAX(ip) AS country,
        MAX(CASE WHEN event_type = 'page_view' THEN utm_source END) AS channel
    FROM events_raw
    WHERE user_id IS NOT NULL OR anonymous_id IS NOT NULL
    WINDOW SESSION (timestamp, INTERVAL '30' MINUTES)
    GROUP BY COALESCE(user_id, anonymous_id), session_id
);
"""

    @staticmethod
    def create_tumbling_window_aggregations() -> str:
        """Create tumbling window aggregations for real-time metrics."""
        return """
-- 1-minute tumbling window for real-time metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_1m AS
SELECT
    window_start,
    window_end,
    event_type,
    source,
    COUNT(*) AS event_count,
    COUNT(DISTINCT COALESCE(user_id, anonymous_id)) AS unique_users,
    SUM(COALESCE(revenue, 0)) AS revenue,
    AVG(duration_ms) AS avg_duration_ms
FROM events_raw
WHERE user_id IS NOT NULL OR anonymous_id IS NOT NULL
WINDOW TUMBLING (timestamp, INTERVAL '1' MINUTE)
GROUP BY window_start, window_end, event_type, source;

-- 5-minute tumbling window for dashboard
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_5m AS
SELECT
    window_start,
    window_end,
    event_type,
    source,
    COUNT(*) AS event_count,
    COUNT(DISTINCT COALESCE(user_id, anonymous_id)) AS unique_users,
    SUM(COALESCE(revenue, 0)) AS revenue,
    AVG(duration_ms) AS avg_duration_ms
FROM events_raw
WHERE user_id IS NOT NULL OR anonymous_id IS NOT NULL
WINDOW TUMBLING (timestamp, INTERVAL '5' MINUTE)
GROUP BY window_start, window_end, event_type, source;

-- 1-hour tumbling window for daily reporting
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_1h AS
SELECT
    window_start,
    window_end,
    event_type,
    source,
    COUNT(*) AS event_count,
    COUNT(DISTINCT COALESCE(user_id, anonymous_id)) AS unique_users,
    SUM(COALESCE(revenue, 0)) AS revenue,
    AVG(duration_ms) AS avg_duration_ms
FROM events_raw
WHERE user_id IS NOT NULL OR anonymous_id IS NOT NULL
WINDOW TUMBLING (timestamp, INTERVAL '1' HOUR)
GROUP BY window_start, window_end, event_type, source;
"""

    @staticmethod
    def create_hopping_window_aggregations() -> str:
        """Create hopping window aggregations for trend detection."""
        return """
-- 5-minute hopping window (advances every 1 minute) for trend detection
CREATE MATERIALIZED VIEW IF NOT EXISTS trends_5m AS
SELECT
    window_start,
    window_end,
    event_type,
    source,
    COUNT(*) AS event_count,
    COUNT(DISTINCT COALESCE(user_id, anonymous_id)) AS unique_users,
    SUM(COALESCE(revenue, 0)) AS revenue
FROM events_raw
WHERE user_id IS NOT NULL OR anonymous_id IS NOT NULL
WINDOW HOP (timestamp, INTERVAL '5' MINUTE, INTERVAL '1' MINUTE)
GROUP BY window_start, window_end, event_type, source;
"""

    @staticmethod
    def create_funnel_analysis() -> str:
        """Create funnel analysis materialized view."""
        return """
CREATE MATERIALIZED VIEW IF NOT EXISTS funnel_analysis AS
WITH funnel_steps AS (
    SELECT
        COALESCE(user_id, anonymous_id) AS user_id,
        CASE
            WHEN event_type = 'page_view' AND page_path = '/' THEN 1
            WHEN event_type = 'page_view' AND page_path LIKE '/product/%' THEN 2
            WHEN event_type = 'track' AND event_name = 'add_to_cart' THEN 3
            WHEN event_type = 'track' AND event_name = 'checkout_started' THEN 4
            WHEN event_type = 'track' AND event_name = 'order_completed' THEN 5
        END AS step
    FROM events_raw
    WHERE (user_id IS NOT NULL OR anonymous_id IS NOT NULL)
    AND (
        (event_type = 'page_view' AND page_path IN ('/', '/product/%'))
        OR (event_type = 'track' AND event_name IN ('add_to_cart', 'checkout_started', 'order_completed'))
    )
),
user_max_step AS (
    SELECT user_id, MAX(step) AS max_step
    FROM funnel_steps
    GROUP BY user_id
)
SELECT
    step,
    COUNT(DISTINCT user_id) AS users_reached,
    COUNT(DISTINCT user_id) * 100.0 / SUM(COUNT(DISTINCT user_id)) OVER () AS conversion_rate
FROM user_max_step
GROUP BY step
ORDER BY step;
"""

    @staticmethod
    def create_retention_cohorts() -> str:
        """Create retention cohort analysis."""
        return """
CREATE MATERIALIZED VIEW IF NOT EXISTS retention_cohorts AS
WITH user_first_activity AS (
    SELECT
        COALESCE(user_id, anonymous_id) AS user_id,
        DATE_TRUNC('day', MIN(timestamp)) AS cohort_date
    FROM events_raw
    WHERE user_id IS NOT NULL OR anonymous_id IS NOT NULL
    GROUP BY COALESCE(user_id, anonymous_id)
),
user_activity AS (
    SELECT
        COALESCE(user_id, anonymous_id) AS user_id,
        DATE_TRUNC('day', timestamp) AS activity_date
    FROM events_raw
    WHERE user_id IS NOT NULL OR anonymous_id IS NOT NULL
),
cohort_activity AS (
    SELECT
        ufa.cohort_date,
        ua.activity_date,
        COUNT(DISTINCT ua.user_id) AS active_users
    FROM user_first_activity ufa
    JOIN user_activity ua ON ufa.user_id = ua.user_id
    WHERE ua.activity_date >= ufa.cohort_date
    GROUP BY ufa.cohort_date, ua.activity_date
),
cohort_sizes AS (
    SELECT cohort_date, COUNT(DISTINCT user_id) AS cohort_size
    FROM user_first_activity
    GROUP BY cohort_date
)
SELECT
    ca.cohort_date,
    ca.activity_date,
    ca.active_users,
    cs.cohort_size,
    ca.active_users * 100.0 / cs.cohort_size AS retention_rate,
    DATE_PART('day', ca.activity_date - ca.cohort_date) AS day_number
FROM cohort_activity ca
JOIN cohort_sizes cs ON ca.cohort_date = cs.cohort_date
WHERE DATE_PART('day', ca.activity_date - ca.cohort_date) <= 30
ORDER BY ca.cohort_date, ca.activity_date;
"""

    @staticmethod
    def create_revenue_attribution() -> str:
        """Create revenue attribution analysis."""
        return """
CREATE MATERIALIZED VIEW IF NOT EXISTS revenue_attribution AS
WITH attributed_revenue AS (
    SELECT
        COALESCE(user_id, anonymous_id) AS user_id,
        event_type,
        utm_source AS source,
        utm_medium AS medium,
        utm_campaign AS campaign,
        revenue,
        timestamp
    FROM events_raw
    WHERE revenue IS NOT NULL AND revenue > 0
),
touchpoints AS (
    SELECT
        user_id,
        source,
        medium,
        campaign,
        SUM(revenue) AS attributed_revenue,
        COUNT(*) AS conversions
    FROM attributed_revenue
    WHERE source IS NOT NULL
    GROUP BY user_id, source, medium, campaign
)
SELECT
    source,
    medium,
    campaign,
    COUNT(DISTINCT user_id) AS converting_users,
    SUM(attributed_revenue) AS total_revenue,
    SUM(conversions) AS total_conversions,
    AVG(attributed_revenue) AS avg_order_value
FROM touchpoints
GROUP BY source, medium, campaign
ORDER BY total_revenue DESC;
"""

    @staticmethod
    def create_anomaly_detection() -> str:
        """Create anomaly detection for metrics."""
        return """
CREATE MATERIALIZED VIEW IF NOT EXISTS anomaly_detection AS
WITH metrics_with_stats AS (
    SELECT
        window_start,
        event_type,
        source,
        event_count,
        AVG(event_count) OVER (PARTITION BY event_type, source ORDER BY window_start ROWS BETWEEN 168 PRECEDING AND 1 PRECEDING) AS avg_7d,
        STDDEV(event_count) OVER (PARTITION BY event_type, source ORDER BY window_start ROWS BETWEEN 168 PRECEDING AND 1 PRECEDING) AS stddev_7d
    FROM metrics_1h
),
anomalies AS (
    SELECT
        window_start,
        event_type,
        source,
        event_count,
        avg_7d,
        stddev_7d,
        CASE
            WHEN stddev_7d > 0 AND ABS(event_count - avg_7d) > 3 * stddev_7d THEN 'anomaly'
            WHEN stddev_7d > 0 AND ABS(event_count - avg_7d) > 2 * stddev_7d THEN 'warning'
            ELSE 'normal'
        END AS anomaly_level,
        CASE
            WHEN stddev_7d > 0 THEN (event_count - avg_7d) / stddev_7d
            ELSE 0
        END AS z_score
    FROM metrics_with_stats
    WHERE avg_7d IS NOT NULL AND stddev_7d IS NOT NULL
)
SELECT * FROM anomalies WHERE anomaly_level IN ('anomaly', 'warning');
"""

    @staticmethod
    def get_all_sql() -> List[str]:
        """Get all SQL statements for deployment."""
        return [
            StreamSQLBuilder.create_events_source_table(),
            StreamSQLBuilder.create_processed_events_sink(),
            StreamSQLBuilder.create_dead_letter_sink(),
            StreamSQLBuilder.create_session_window_aggregation(),
            StreamSQLBuilder.create_tumbling_window_aggregations(),
            StreamSQLBuilder.create_hopping_window_aggregations(),
            StreamSQLBuilder.create_funnel_analysis(),
            StreamSQLBuilder.create_retention_cohorts(),
            StreamSQLBuilder.create_revenue_attribution(),
            StreamSQLBuilder.create_anomaly_detection(),
        ]