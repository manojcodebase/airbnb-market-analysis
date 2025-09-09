-- 1) Average price by neighbourhood group
SELECT neighbourhood_group,
       ROUND(AVG(price), 2) AS avg_price,
       COUNT(*)             AS total_listings
FROM listings
GROUP BY neighbourhood_group
ORDER BY avg_price DESC;

-- 2) Room type mix (share) per neighbourhood group
WITH counts AS (
  SELECT neighbourhood_group, room_type, COUNT(*) AS cnt
  FROM listings
  GROUP BY neighbourhood_group, room_type
),
totals AS (
  SELECT neighbourhood_group, SUM(cnt) AS total_cnt
  FROM counts
  GROUP BY neighbourhood_group
)
SELECT c.neighbourhood_group,
       c.room_type,
       c.cnt,
       ROUND(100.0 * c.cnt / t.total_cnt, 1) AS pct
FROM counts c
JOIN totals t USING (neighbourhood_group)
ORDER BY c.neighbourhood_group, pct DESC;

-- 3) Top 15 hosts by number of active listings
SELECT host_id, COALESCE(host_name, 'Unknown') AS host_name,
       COUNT(*) AS listings_count
FROM listings
GROUP BY host_id, host_name
ORDER BY listings_count DESC
LIMIT 15;

-- 4) Availability profile (bucketize)
SELECT CASE
         WHEN availability_365 BETWEEN 0 AND 30   THEN '0-30'
         WHEN availability_365 BETWEEN 31 AND 90  THEN '31-90'
         WHEN availability_365 BETWEEN 91 AND 180 THEN '91-180'
         WHEN availability_365 BETWEEN 181 AND 270 THEN '181-270'
         WHEN availability_365 BETWEEN 271 AND 365 THEN '271-365'
         ELSE 'Unknown'
       END AS availability_bucket,
       COUNT(*) AS cnt
FROM listings
GROUP BY availability_bucket
ORDER BY
  CASE availability_bucket
    WHEN '0-30' THEN 1 WHEN '31-90' THEN 2 WHEN '91-180' THEN 3
    WHEN '181-270' THEN 4 WHEN '271-365' THEN 5 ELSE 6 END;

-- 5) Correlation proxies (binned comparisons)
-- Average price by reviews_per_month buckets
WITH buckets AS (
  SELECT CASE
           WHEN reviews_per_month IS NULL THEN '0'
           WHEN reviews_per_month < 0.5 THEN '<0.5'
           WHEN reviews_per_month < 1.0 THEN '0.5-1.0'
           WHEN reviews_per_month < 2.0 THEN '1.0-2.0'
           ELSE '>=2.0'
         END AS rpm_bucket,
         price
  FROM listings
)
SELECT rpm_bucket,
       ROUND(AVG(price),2) AS avg_price,
       COUNT(*)            AS n
FROM buckets
GROUP BY rpm_bucket
ORDER BY n DESC;

-- 6) Seasonal pattern: average price by month of last_review
-- (Proxy for when listings get reviewed; not exact occupancy)
SELECT EXTRACT(MONTH FROM last_review) AS review_month,
       ROUND(AVG(price), 2)            AS avg_price,
       COUNT(*)                        AS n
FROM listings
WHERE last_review IS NOT NULL
GROUP BY review_month
ORDER BY review_month;

-- 7) Price percentiles by neighbourhood group (robust view)
WITH p AS (
  SELECT neighbourhood_group,
         PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS p50,
         PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY price) AS p90
  FROM listings
  WHERE price IS NOT NULL
  GROUP BY neighbourhood_group
)
SELECT * FROM p ORDER BY p50 DESC;

-- 8) View for your dashboard queries
CREATE OR REPLACE VIEW vw_group_price AS
SELECT neighbourhood_group,
       ROUND(AVG(price),2) AS avg_price,
       COUNT(*)            AS n
FROM listings
GROUP BY neighbourhood_group;

-- 9) Most expensive neighbourhoods (not group)
SELECT neighbourhood,
       ROUND(AVG(price),2) AS avg_price,
       COUNT(*) AS n
FROM listings
GROUP BY neighbourhood
HAVING COUNT(*) >= 50   -- avoid tiny-sample noise
ORDER BY avg_price DESC
LIMIT 25;

-- 10) Price vs availability quick sample (for scatter plotting tools)
SELECT price, availability_365
FROM listings
WHERE price IS NOT NULL
  AND availability_365 IS NOT NULL
ORDER BY random()
LIMIT 5000;
