from datetime import datetime, timedelta
import json
from typing import List, Dict
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class FlightConfiguration:
    from_airport: str
    to_airport: str
    date: str
    trip_type: str = "one-way"
    seat_class: str = "economy"
    max_stops: int = 0
    num_adults: int = 1
    fetch_mode: str = "normal"

def generate_date_sequence(
    start_date: datetime,
    end_date: datetime,
    weekday: int  # 0 = Monday, 6 = Sunday
) -> List[datetime]:
    dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() == weekday:
            dates.append(current)
        current += timedelta(days=1)
    return dates

def create_flight_configurations(
    from_airport: str,
    to_airport: str,
    start_date: datetime,
    end_date: datetime,
    outbound_day: int,  # weekday for outbound flight
    return_day: int,    # weekday for return flight
    **kwargs
) -> List[FlightConfiguration]:
    configs = []
    
    # Generate outbound flight dates (Thursdays)
    outbound_dates = generate_date_sequence(start_date, end_date, outbound_day)
    
    # Generate return flight dates (Sundays)
    return_dates = generate_date_sequence(start_date, end_date, return_day)
    
    # Create outbound flight configurations
    for date in outbound_dates:
        configs.append(FlightConfiguration(
            from_airport=from_airport,
            to_airport=to_airport,
            date=date.strftime('%Y-%m-%d'),
            **kwargs
        ))
    
    # Create return flight configurations
    for date in return_dates:
        configs.append(FlightConfiguration(
            from_airport=to_airport,
            to_airport=from_airport,
            date=date.strftime('%Y-%m-%d'),
            **kwargs
        ))
    
    return configs

def save_configurations(configs: List[FlightConfiguration], filename: str):
    config_data = [vars(config) for config in configs]
    abs_path = os.path.abspath(filename)
    print(f"Saving configurations to: {abs_path}")  # Debug print
    with open(filename, 'w') as f:
        json.dump(config_data, f, indent=2)
    return abs_path

def load_configurations(filename: str) -> List[FlightConfiguration]:
    with open(filename, 'r') as f:
        config_data = json.load(f)
    return [FlightConfiguration(**config) for config in config_data] 