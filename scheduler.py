#!/usr/bin/env python3
import sys
import os
from datetime import datetime, date, timedelta
import logging
import click
import time

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.configuration_service import (
    create_flight_configurations,
    save_configurations,
    load_configurations
)
from services.batch_processor import process_configurations
from services.analysis_views import refresh_analysis_views
from services.flight_database import create_connection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rfb_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def generate_configs(from_airport: str, to_airport: str) -> str:
    """Generate configurations for the next 6 months"""
    try:
        start_date = date.today()
        end_date = start_date + timedelta(days=180)  # 6 months
        
        logger.info(f"Generating configurations from {start_date} to {end_date}")
        
        configs = create_flight_configurations(
            from_airport=from_airport,
            to_airport=to_airport,
            start_date=start_date,
            end_date=end_date,
            outbound_day=4,  # Thursday
            return_day=0,    # Sunday
            seat_class='economy',
            max_stops=0
        )
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        config_file = f'flight_configs_{timestamp}.json'
        
        save_configurations(configs, config_file)
        logger.info(f"Saved {len(configs)} configurations to {config_file}")
        
        return config_file
        
    except Exception as e:
        logger.error(f"Error generating configurations: {str(e)}")
        raise
def run_batch_process(config_file: str, delay: int = 5):
    """Run batch processing on the configuration file"""
    try:
        logger.info(f"Starting batch processing of {config_file}")
        # Load the configurations from the file
        configs = load_configurations(config_file)
        # Pass the loaded configurations to process_configurations
        process_configurations(configs, delay_between_requests=delay)
        logger.info("Batch processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error during batch processing: {str(e)}")
        raise

def refresh_materialized_views():
    """Refresh all materialized views"""
    try:
        logger.info("Starting view refresh")
        conn = create_connection()
        refresh_analysis_views(conn)
        logger.info("Successfully refreshed all materialized views")
        
    except Exception as e:
        logger.error(f"Error refreshing views: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

@click.command()
@click.option('--from-airport', '-f', help='Departure airport IATA code')
@click.option('--to-airport', '-t', help='Arrival airport IATA code')
@click.option('--delay', default=5, help='Delay between requests in seconds')
@click.option('--continuous', is_flag=True, default=False, 
              help='Run in continuous mode (for container deployment)')
def run_workflow(from_airport, to_airport, delay, continuous):
    """Run the workflow either once or continuously"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    if continuous:
        while True:
            try:
                logging.info("Starting scheduled workflow")
                if from_airport and to_airport:
                    # Run with specific airports
                    process_specific_route(from_airport, to_airport, delay)
                else:
                    # Run all configured routes
                    process_all_routes(delay)
                
                logging.info("Workflow completed, sleeping for 1 hour")
                time.sleep(3600)
            except Exception as e:
                logging.error(f"Error in scheduled workflow: {e}")
                time.sleep(300)
    else:
        # One-off execution
        if not (from_airport and to_airport):
            raise click.UsageError("Both --from-airport and --to-airport are required for one-off execution")
        process_specific_route(from_airport, to_airport, delay)

if __name__ == "__main__":
    run_workflow()
