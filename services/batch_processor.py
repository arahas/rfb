from typing import List, Tuple
import time
from datetime import datetime, date
from .configuration_service import FlightConfiguration
from .flight_service import get_flights_with_additional_info
from fast_flights import FlightData, Passengers
from .analysis_views import refresh_analysis_views
from .flight_database import create_connection

__all__ = ['process_configurations', 'filter_valid_configurations']

def process_configurations(
    configs: List[FlightConfiguration],
    delay_between_requests: int = 5  # seconds
):
    conn = create_connection()
    try:
        # Filter out past dates
        valid_configs, invalid_configs = filter_valid_configurations(configs)
        
        if invalid_configs:
            print(f"Skipping {len(invalid_configs)} configurations with past dates:")
            for config in invalid_configs:
                print(f"- {config.from_airport} -> {config.to_airport} on {config.date}")
        
        if not valid_configs:
            print("No valid configurations to process (all dates are in the past)")
            return
        
        for config in valid_configs:
            try:
                flight_data = [FlightData(
                    date=config.date,
                    from_airport=config.from_airport,
                    to_airport=config.to_airport
                )]
                passengers = Passengers(adults=config.num_adults)

                print(f"Processing flight: {config.from_airport} -> {config.to_airport} on {config.date}")
                
                result = get_flights_with_additional_info(
                    flight_data=flight_data,
                    trip=config.trip_type,
                    seat=config.seat_class,
                    max_stops=config.max_stops,
                    passengers=passengers,
                    fetch_mode=config.fetch_mode
                )
                
                # Add delay between requests
                time.sleep(delay_between_requests)

            except Exception as e:
                print(f"Error processing configuration: {e}")
                continue
        
        # After processing all configurations, refresh the views
        refresh_analysis_views(conn)
    finally:
        conn.close()

def filter_valid_configurations(configs: List[FlightConfiguration]) -> Tuple[List[FlightConfiguration], List[FlightConfiguration]]:
    """
    Filter out configurations with past dates and return only valid future dates.
    Returns a tuple of (valid_configs, invalid_configs)
    """
    today = date.today()
    valid_configs = []
    invalid_configs = []
    
    for config in configs:
        config_date = datetime.strptime(config.date, '%Y-%m-%d').date()
        if config_date >= today:
            valid_configs.append(config)
        else:
            invalid_configs.append(config)
            
    return valid_configs, invalid_configs 