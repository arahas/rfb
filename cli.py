#!/usr/bin/env python3
import click
from datetime import datetime
import sys
import os
from typing import List
import time

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.flight_service import get_flights_with_additional_info
from services.configuration_service import (
    create_flight_configurations,
    save_configurations,
    load_configurations,
    FlightConfiguration
)
from services.batch_processor import process_configurations
from services.analysis_views import refresh_analysis_views, create_analysis_views
from services.flight_database import create_connection, create_flights_table
from fast_flights import FlightData, Passengers

@click.group()
def cli():
    """
    Regular Flyer Buddy (RFB) CLI - Flight Search and Analysis Tool

    This CLI provides commands for:

    \b
    1. search           - Perform single flight searches
    2. generate-configs - Generate configuration files for batch processing
    3. batch-process    - Process multiple flight searches from a config file
    4. refresh-views    - Refresh database materialized views for analysis
    5. init-db         - Initialize database tables and views
    """
    pass

@cli.command()
@click.option('--from-airport', '-f', required=True, 
              help='Departure airport IATA code (e.g., SEA, MKE)')
@click.option('--to-airport', '-t', required=True, 
              help='Arrival airport IATA code (e.g., LAX, ORD)')
@click.option('--date', '-d', required=True, 
              help='Flight date in YYYY-MM-DD format (e.g., 2024-03-01)')
@click.option('--trip-type', default='one-way', type=click.Choice(['one-way', 'round-trip']),
              help='Type of trip: one-way or round-trip [default: one-way]')
@click.option('--seat-class', default='economy', type=click.Choice(['economy', 'business']),
              help='Class of service: economy or business [default: economy]')
@click.option('--max-stops', default=0, type=int,
              help='Maximum number of stops (0-2) [default: 0]')
@click.option('--num-adults', default=1, type=int,
              help='Number of adult passengers (1-10) [default: 1]')
@click.option('--fetch-mode', default='normal', type=click.Choice(['normal', 'fallback']),
              help='API fetch mode: normal or fallback [default: normal]')
def search(from_airport, to_airport, date, trip_type, seat_class, max_stops, num_adults, fetch_mode):
    """
    Perform a single flight search with specified parameters.

    \b
    Examples:
        ./cli.py search -f SEA -t MKE -d 2024-03-01
        ./cli.py search --from-airport SEA --to-airport MKE --date 2024-03-01 --seat-class business
        ./cli.py search -f SEA -t MKE -d 2024-03-01 --trip-type round-trip --max-stops 1
    """
    click.echo(f"Searching flights from {from_airport} to {to_airport} on {date}...")
    
    flight_data = [FlightData(date=date, from_airport=from_airport, to_airport=to_airport)]
    passengers = Passengers(adults=num_adults)
    
    result = get_flights_with_additional_info(
        flight_data=flight_data,
        trip=trip_type,
        seat=seat_class,
        max_stops=max_stops,
        passengers=passengers,
        fetch_mode=fetch_mode
    )
    
    if result:
        click.echo("\nFlight Details:")
        for key, value in result.items():
            if value is not None:  # Only show non-None values
                click.echo(f"{key}: {value}")
    else:
        click.echo("No flights found.")

@cli.command()
@click.option('--from-airport', '-f', required=True,
              help='Departure airport IATA code (e.g., SEA)')
@click.option('--to-airport', '-t', required=True,
              help='Arrival airport IATA code (e.g., MKE)')
@click.option('--start-date', required=True, 
              help='Start date in YYYY-MM-DD format (e.g., 2024-03-01)')
@click.option('--end-date', required=True, 
              help='End date in YYYY-MM-DD format (e.g., 2024-09-01)')
@click.option('--outbound-day', type=int, default=3,
              help='Outbound weekday (0=Monday, 6=Sunday) [default: 3 (Thursday)]')
@click.option('--return-day', type=int, default=6,
              help='Return weekday (0=Monday, 6=Sunday) [default: 6 (Sunday)]')
@click.option('--seat-class', default='economy', type=click.Choice(['economy', 'business']),
              help='Class of service [default: economy]')
@click.option('--max-stops', default=0, type=int,
              help='Maximum number of stops (0-2) [default: 0]')
@click.option('--output', '-o', default='flight_configs.json',
              help='Output configuration file path [default: flight_configs.json]')
def generate_configs(from_airport, to_airport, start_date, end_date, 
                    outbound_day, return_day, seat_class, max_stops, output):
    """
    Generate flight search configurations for batch processing.

    Creates a JSON configuration file containing multiple flight search parameters
    based on specified date ranges and weekdays.

    \b
    Examples:
        ./cli.py generate-configs -f SEA -t MKE --start-date 2024-03-01 --end-date 2024-09-01
        ./cli.py generate-configs -f SEA -t MKE --start-date 2024-03-01 --end-date 2024-09-01 
                                --outbound-day 1 --return-day 4 --seat-class business
    """
    click.echo("Generating flight configurations...")
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        configs = create_flight_configurations(
            from_airport=from_airport,
            to_airport=to_airport,
            start_date=start,
            end_date=end,
            outbound_day=outbound_day,
            return_day=return_day,
            seat_class=seat_class,
            max_stops=max_stops
        )
        
        save_path = save_configurations(configs, output)
        click.echo(f"Successfully saved {len(configs)} configurations to {save_path}")
        
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--delay', default=5, type=int,
              help='Delay between requests in seconds [default: 5]')
def batch_process(config_file, delay):
    """
    Process multiple flight searches from a configuration file.

    Arguments:
        config_file: Path to the JSON configuration file containing flight search parameters

    \b
    Examples:
        ./cli.py batch-process flight_configs.json
        ./cli.py batch-process flight_configs.json --delay 10
    """
    try:
        configs = load_configurations(config_file)
        click.echo(f"Loaded {len(configs)} configurations from {config_file}")
        process_configurations(configs, delay_between_requests=delay)
        click.echo("Batch processing completed successfully!")
        
    except FileNotFoundError:
        click.echo(f"Error: Configuration file '{config_file}' not found.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during batch processing: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
def init_db():
    """Initialize database tables and materialized views."""
    click.echo("Initializing database...")
    conn = create_connection()
    try:
        click.echo("Creating flight_searches table...")
        create_flights_table(conn)
        click.echo("Creating analysis views...")
        create_analysis_views(conn)
        click.secho("Database initialization completed successfully!", fg='green')
    except Exception as e:
        click.secho(f"Error during initialization: {e}", fg='red')
        sys.exit(1)
    finally:
        conn.close()

@cli.command()
def refresh_views():
    """Refresh all materialized views with latest data."""
    click.echo("Starting materialized views refresh...")
    conn = create_connection()
    try:
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
        
        with click.progressbar(views, label='Refreshing views') as view_list:
            for view in view_list:
                try:
                    start_time = time.time()
                    with conn.cursor() as cur:
                        cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
                        conn.commit()
                    duration = time.time() - start_time
                    click.echo(f"✓ {view}: {duration:.2f}s")
                except Exception as e:
                    click.secho(f"✗ Error refreshing {view}: {str(e)}", fg='red')
                    continue
        
        click.secho("\nRefresh operation completed successfully!", fg='green')
        
    except Exception as e:
        click.secho(f"Critical error during refresh: {str(e)}", fg='red')
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    cli() 