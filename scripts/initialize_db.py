import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.database import create_connection
from services.flight_database import create_flights_table
from services.analysis_views import create_analysis_views

def initialize_database():
    """Initialize database tables and views"""
    conn = create_connection()
    try:
        print("Creating flight_searches table...")
        create_flights_table(conn)
        print("Creating analysis views...")
        create_analysis_views(conn)
        print("Database initialization completed successfully!")
    except Exception as e:
        print(f"Error during initialization: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database()
