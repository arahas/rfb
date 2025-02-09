from datetime import datetime
import psycopg2
from .database import create_connection

def create_analysis_views(conn):
    """Create all materialized views for flight analysis"""
    with conn.cursor() as cur:
        # 1. Daily Price Summary
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS flight_daily_summary AS
        WITH latest_price AS (
            SELECT 
                from_airport,
                to_airport,
                DATE(departure) as departure_date,
                airline_name,
                price as current_price,
                ROW_NUMBER() OVER (
                    PARTITION BY from_airport, to_airport, DATE(departure), airline_name
                    ORDER BY query_time DESC
                ) as rn
            FROM flight_searches
        )
        SELECT 
            DATE(fs.query_time) as date,
            fs.from_airport,
            fs.to_airport,
            DATE(fs.departure) as departure_date,
            fs.airline_name,
            MIN(fs.price) as min_daily_price,
            MAX(fs.price) as max_daily_price,
            AVG(fs.price) as avg_daily_price,
            STDDEV(fs.price) as price_volatility,
            COUNT(*) as daily_checks,
            MAX(fs.price) - MIN(fs.price) as daily_price_swing,
            lp.current_price as latest_price
        FROM flight_searches fs
        LEFT JOIN latest_price lp ON 
            fs.from_airport = lp.from_airport 
            AND fs.to_airport = lp.to_airport 
            AND DATE(fs.departure) = lp.departure_date 
            AND fs.airline_name = lp.airline_name 
            AND lp.rn = 1
        GROUP BY 
            DATE(fs.query_time), fs.from_airport, fs.to_airport, 
            DATE(fs.departure), fs.airline_name, lp.current_price;
        """)

        # Drop existing route_analysis view and its index
        cur.execute("""
        DROP MATERIALIZED VIEW IF EXISTS route_analysis CASCADE;
        DROP INDEX IF EXISTS idx_route_analysis;
        """)

        # 2. Route Analysis
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS route_analysis AS
        WITH latest_prices AS (
            SELECT 
                from_airport,
                to_airport,
                EXTRACT(DOW FROM departure) as day_of_week,
                price as latest_price,
                ROW_NUMBER() OVER (
                    PARTITION BY from_airport, to_airport, EXTRACT(DOW FROM departure)
                    ORDER BY query_time DESC
                ) as rn
            FROM flight_searches
        )
        SELECT 
            fs.from_airport,
            fs.to_airport,
            fs.airline_name,
            EXTRACT(DOW FROM fs.departure) as day_of_week,
            MIN(fs.price) as historical_low,
            MAX(fs.price) as historical_high,
            lp.latest_price,
            AVG(fs.stops) as avg_stops,
            MODE() WITHIN GROUP (ORDER BY fs.duration) as typical_duration,
            COUNT(DISTINCT DATE(fs.departure)) as days_tracked,
            COUNT(*) as total_searches
        FROM flight_searches fs
        LEFT JOIN latest_prices lp ON 
            fs.from_airport = lp.from_airport 
            AND fs.to_airport = lp.to_airport 
            AND EXTRACT(DOW FROM fs.departure) = lp.day_of_week
            AND lp.rn = 1
        GROUP BY 
            fs.from_airport, fs.to_airport, fs.airline_name, 
            EXTRACT(DOW FROM fs.departure), lp.latest_price;
        """)

        # Drop the old price_trends view and its index
        cur.execute("""
        DROP MATERIALIZED VIEW IF EXISTS price_trends CASCADE;
        DROP INDEX IF EXISTS idx_price_trends;
        """)
        
        # Create new price_trends view
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS price_trends AS
        WITH daily_prices AS (
            SELECT 
                DATE(query_time) as query_date,
                DATE(departure) as departure_date,
                from_airport,
                to_airport,
                airline_name,
                MIN(price) as min_price
            FROM flight_searches
            GROUP BY 
                DATE(query_time),
                DATE(departure),
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
        ORDER BY 
            query_date,
            departure_date;
        """)
        
        # Create index for better performance
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_trends 
        ON price_trends (from_airport, to_airport, query_date, departure_date);
        """)

        # 4. Advance Purchase Analysis
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS advance_purchase_analysis AS
        SELECT 
            from_airport,
            to_airport,
            airline_name,
            departure - DATE(query_time) as days_before_flight,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            COUNT(*) as sample_size
        FROM flight_searches
        WHERE departure > query_time
        GROUP BY 
            from_airport, to_airport, airline_name,
            departure - DATE(query_time)
        HAVING COUNT(*) > 5;
        """)

        # 5. Latest Prices
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS latest_prices AS
        WITH ranked_prices AS (
            SELECT 
                from_airport,
                to_airport,
                airline_name,
                departure,
                price,
                query_time,
                ROW_NUMBER() OVER (
                    PARTITION BY from_airport, to_airport, airline_name, departure
                    ORDER BY query_time DESC
                ) as rn
            FROM flight_searches
        )
        SELECT 
            from_airport,
            to_airport,
            airline_name,
            departure,
            price as latest_price,
            query_time as last_updated
        FROM ranked_prices
        WHERE rn = 1;
        """)

        # 6. Lowest Historical Prices
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS lowest_prices AS
        SELECT 
            from_airport,
            to_airport,
            airline_name,
            departure,
            MIN(price) as lowest_price,
            MIN(query_time) as first_seen
        FROM flight_searches
        GROUP BY 
            from_airport, to_airport, airline_name, departure;
        """)

        # 7. Highest Historical Prices
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS highest_prices AS
        SELECT 
            from_airport,
            to_airport,
            airline_name,
            departure,
            MAX(price) as highest_price,
            MAX(query_time) as last_seen
        FROM flight_searches
        GROUP BY 
            from_airport, to_airport, airline_name, departure;
        """)

        # 8. Average Historical Prices
        cur.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS average_prices AS
        SELECT 
            from_airport,
            to_airport,
            airline_name,
            departure,
            AVG(price) as avg_price,
            COUNT(*) as price_points,
            MIN(query_time) as first_seen,
            MAX(query_time) as last_seen
        FROM flight_searches
        GROUP BY 
            from_airport, to_airport, airline_name, departure;
        """)

        # Create indexes for better performance
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_summary 
        ON flight_daily_summary (from_airport, to_airport, departure_date);
        
        CREATE INDEX IF NOT EXISTS idx_route_analysis 
        ON route_analysis (from_airport, to_airport, airline_name, day_of_week);
        
        CREATE INDEX IF NOT EXISTS idx_advance_purchase 
        ON advance_purchase_analysis (from_airport, to_airport, days_before_flight);
        
        CREATE INDEX IF NOT EXISTS idx_latest_prices 
        ON latest_prices (from_airport, to_airport, departure);
        
        CREATE INDEX IF NOT EXISTS idx_lowest_prices 
        ON lowest_prices (from_airport, to_airport, departure);
        
        CREATE INDEX IF NOT EXISTS idx_highest_prices 
        ON highest_prices (from_airport, to_airport, departure);
        
        CREATE INDEX IF NOT EXISTS idx_average_prices 
        ON average_prices (from_airport, to_airport, departure);
        """)
        
        conn.commit()

def refresh_analysis_views(conn):
    """Refresh all materialized views"""
    with conn.cursor() as cur:
        views = [
            'flight_daily_summary',
            'route_analysis',
            'price_trends',
            'advance_purchase_analysis',
            'latest_prices',
            'lowest_prices',
            'highest_prices',
            'average_prices'
        ]
        
        for view in views:
            try:
                cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
                print(f"Successfully refreshed {view}")
            except Exception as e:
                print(f"Error refreshing {view}: {str(e)}")
        
        conn.commit()

def get_analysis_data(conn, view_name, **filters):
    """Generic function to query analysis views"""
    query = f"SELECT * FROM {view_name}"
    
    # Add WHERE clause if filters are provided
    if filters:
        conditions = [f"{k} = %s" for k in filters.keys()]
        query += " WHERE " + " AND ".join(conditions)
    
    with conn.cursor() as cur:
        cur.execute(query, list(filters.values()))
        columns = [desc[0] for desc in cur.description]
        results = cur.fetchall()
        return [dict(zip(columns, row)) for row in results] 