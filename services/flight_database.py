# services/flight_database.py

import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv
from .analysis_views import create_analysis_views

# Load environment variables to access database configuration
load_dotenv()

def create_connection():
    """Create a connection to our PostgreSQL database"""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'rfb'),
        host=os.getenv('DB_HOST', 'localhost')
    )

def parse_datetime(date_str):
    """Convert date strings from flight data into proper datetime objects"""
    try:
        return datetime.strptime(date_str, '%I:%M %p on %a, %b %d, %Y')
    except ValueError:
        # Handle dates without year by assuming 2025
        partial_date = datetime.strptime(date_str + ', 2025', '%I:%M %p on %a, %b %d, %Y')
        return partial_date

def parse_price(price_str):
    """Convert price strings like '$284' into decimal numbers"""
    if not price_str:
        return 0.0
    return float(price_str.replace('$', ''))

def parse_duration(duration_str):
    """Convert duration strings like '3 hr 53 min' into PostgreSQL interval format"""
    if not duration_str:
        return '0 hours'
    parts = duration_str.split()
    hours = int(parts[0])
    minutes = int(parts[2]) if len(parts) > 2 else 0
    return f"{hours} hours {minutes} minutes"

def create_flights_table(conn):
    """Set up the database table structure for storing flight information"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flight_searches (
                id SERIAL PRIMARY KEY,
                query_time TIMESTAMP NOT NULL,
                from_airport VARCHAR(3) NOT NULL,
                to_airport VARCHAR(3) NOT NULL,
                trip VARCHAR(10) NOT NULL,
                seat VARCHAR(20) NOT NULL,
                airline_name VARCHAR(50),
                departure TIMESTAMP,
                arrival TIMESTAMP,
                duration INTERVAL,
                stops INTEGER,
                price DECIMAL(10,2),
                is_best BOOLEAN,
                arrival_time_ahead VARCHAR(100),
                delay INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def insert_flight_data(conn, flight_data):
    """Insert a single flight search result into the database"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO flight_searches (
                query_time, from_airport, to_airport, trip, seat,
                airline_name, departure, arrival, duration, stops,
                price, is_best, arrival_time_ahead, delay
            ) VALUES (
                %(query_time)s, %(from_airport)s, %(to_airport)s, %(trip)s, %(seat)s,
                %(airline_name)s, %(departure)s, %(arrival)s, %(duration)s, %(stops)s,
                %(price)s, %(is_best)s, %(arrival_time_ahead)s, %(delay)s
            ) RETURNING id
        """, {
            'query_time': parse_datetime(flight_data['query_time']),
            'from_airport': flight_data['from_airport'],
            'to_airport': flight_data['to_airport'],
            'trip': flight_data['trip'],
            'seat': flight_data['seat'],
            'airline_name': flight_data.get('name'),
            'departure': parse_datetime(flight_data['departure']) if flight_data.get('departure') else None,
            'arrival': parse_datetime(flight_data['arrival']) if flight_data.get('arrival') else None,
            'duration': parse_duration(flight_data.get('duration')),
            'stops': flight_data.get('stops', 0),
            'price': parse_price(flight_data.get('price')),
            'is_best': flight_data.get('is_best', False),
            'arrival_time_ahead': flight_data.get('arrival_time_ahead'),
            'delay': flight_data.get('delay')
        })
        conn.commit()
        return cur.fetchone()[0]

def store_flight_search(flight_data):
    """Main entry point for storing flight search results"""
    try:
        conn = create_connection()
        create_flights_table(conn)
        flight_id = insert_flight_data(conn, flight_data)
        print(f"Successfully stored flight data with ID: {flight_id}")
        return flight_id
    except Exception as e:
        print(f"Error storing flight data: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def initialize_database():
    """Initialize database tables and views"""
    conn = create_connection()
    try:
        create_flights_table(conn)
        create_analysis_views(conn)
    finally:
        conn.close()