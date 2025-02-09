import os
import psycopg2
from dotenv import load_dotenv

def create_connection():
    """Create a connection to the PostgreSQL database"""
    load_dotenv()  # Load environment variables from .env file
    
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        raise