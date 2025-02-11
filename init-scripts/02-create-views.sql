-- Initialize all materialized views for flight price analysis
-- Note: These views depend on the flight_searches table existing and containing data

-- Daily summary of flight prices including volatility metrics
CREATE MATERIALIZED VIEW flight_daily_summary AS 
WITH latest_price AS (
    SELECT 
        from_airport,
        to_airport,
        date(departure) AS departure_date,
        airline_name,
        price AS current_price,
        row_number() OVER (
            PARTITION BY from_airport, to_airport, date(departure), airline_name 
            ORDER BY query_time DESC
        ) AS rn
    FROM flight_searches
)
SELECT 
    date(fs.query_time) AS date,
    fs.from_airport,
    fs.to_airport,
    date(fs.departure) AS departure_date,
    fs.airline_name,
    min(fs.price) AS min_daily_price,
    max(fs.price) AS max_daily_price,
    avg(fs.price) AS avg_daily_price,
    stddev(fs.price) AS price_volatility,
    count(*) AS daily_checks,
    (max(fs.price) - min(fs.price)) AS daily_price_swing,
    lp.current_price AS latest_price
FROM flight_searches fs
LEFT JOIN latest_price lp ON 
    fs.from_airport::text = lp.from_airport::text 
    AND fs.to_airport::text = lp.to_airport::text 
    AND date(fs.departure) = lp.departure_date 
    AND fs.airline_name::text = lp.airline_name::text 
    AND lp.rn = 1
GROUP BY 
    date(fs.query_time), 
    fs.from_airport, 
    fs.to_airport, 
    date(fs.departure), 
    fs.airline_name, 
    lp.current_price;

-- Analysis of routes by day of week including historical prices
CREATE MATERIALIZED VIEW route_analysis AS 
WITH latest_prices AS (
    SELECT 
        from_airport,
        to_airport,
        EXTRACT(dow FROM departure) AS day_of_week,
        price AS latest_price,
        row_number() OVER (
            PARTITION BY from_airport, to_airport, EXTRACT(dow FROM departure)
            ORDER BY query_time DESC
        ) AS rn
    FROM flight_searches
)
SELECT 
    fs.from_airport,
    fs.to_airport,
    fs.airline_name,
    EXTRACT(dow FROM fs.departure) AS day_of_week,
    min(fs.price) AS historical_low,
    max(fs.price) AS historical_high,
    lp.latest_price,
    avg(fs.stops) AS avg_stops,
    mode() WITHIN GROUP (ORDER BY fs.duration) AS typical_duration,
    count(DISTINCT date(fs.departure)) AS days_tracked,
    count(*) AS total_searches
FROM flight_searches fs
LEFT JOIN latest_prices lp ON 
    fs.from_airport::text = lp.from_airport::text 
    AND fs.to_airport::text = lp.to_airport::text 
    AND EXTRACT(dow FROM fs.departure) = lp.day_of_week 
    AND lp.rn = 1
GROUP BY 
    fs.from_airport, 
    fs.to_airport, 
    fs.airline_name, 
    EXTRACT(dow FROM fs.departure), 
    lp.latest_price;

-- Daily price trends tracking
CREATE MATERIALIZED VIEW price_trends AS 
WITH daily_prices AS (
    SELECT 
        date(query_time) AS query_date,
        date(departure) AS departure_date,
        from_airport,
        to_airport,
        airline_name,
        min(price) AS min_price
    FROM flight_searches
    GROUP BY 
        date(query_time), 
        date(departure), 
        from_airport, 
        to_airport, 
        airline_name
)
SELECT 
    query_date,
    departure_date,
    from_airport,
    to_airport,
    airline_name,
    min_price
FROM daily_prices
ORDER BY query_date, departure_date;

-- Analysis of how prices change based on advance purchase timing
CREATE MATERIALIZED VIEW advance_purchase_analysis AS 
SELECT 
    from_airport,
    to_airport,
    airline_name,
    departure - date(query_time)::timestamp without time zone AS days_before_flight,
    avg(price) AS avg_price,
    min(price) AS min_price,
    max(price) AS max_price,
    count(*) AS sample_size
FROM flight_searches
WHERE departure > query_time
GROUP BY 
    from_airport, 
    to_airport, 
    airline_name, 
    departure - date(query_time)::timestamp without time zone
HAVING count(*) > 5;

-- Track most recent prices for each route
CREATE MATERIALIZED VIEW latest_prices AS 
WITH ranked_prices AS (
    SELECT 
        from_airport,
        to_airport,
        airline_name,
        departure,
        price,
        query_time,
        row_number() OVER (
            PARTITION BY from_airport, to_airport, airline_name, departure 
            ORDER BY query_time DESC
        ) AS rn
    FROM flight_searches
)
SELECT 
    from_airport,
    to_airport,
    airline_name,
    departure,
    price AS latest_price,
    query_time AS last_updated
FROM ranked_prices
WHERE rn = 1;

-- Track historical lowest prices
CREATE MATERIALIZED VIEW lowest_prices AS 
SELECT 
    from_airport,
    to_airport,
    airline_name,
    departure,
    min(price) AS lowest_price,
    min(query_time) AS first_seen
FROM flight_searches
GROUP BY 
    from_airport, 
    to_airport, 
    airline_name, 
    departure;

-- Track historical highest prices
CREATE MATERIALIZED VIEW highest_prices AS 
SELECT 
    from_airport,
    to_airport,
    airline_name,
    departure,
    max(price) AS highest_price,
    max(query_time) AS last_seen
FROM flight_searches
GROUP BY 
    from_airport, 
    to_airport, 
    airline_name, 
    departure;

-- Track average prices and monitoring periods
CREATE MATERIALIZED VIEW average_prices AS 
SELECT 
    from_airport,
    to_airport,
    airline_name,
    departure,
    avg(price) AS avg_price,
    count(*) AS price_points,
    min(query_time) AS first_seen,
    max(query_time) AS last_seen
FROM flight_searches
GROUP BY 
    from_airport, 
    to_airport, 
    airline_name, 
    departure;