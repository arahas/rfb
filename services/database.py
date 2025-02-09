import os
import getpass
import psycopg2

def create_connection():
    """Create a connection to our PostgreSQL database"""
    # Get system username as default
    default_user = getpass.getuser()
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'rfb'),
        user=os.getenv('DB_USER', default_user),  # Use system username as default
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )
    return conn 