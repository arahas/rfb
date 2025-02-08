from datetime import datetime
from fast_flights import FlightData, Passengers, get_flights
from collections import OrderedDict
from .flight_database import store_flight_search  # Add this import

def get_flights_with_additional_info(flight_data, trip, seat, max_stops, passengers, fetch_mode):
    """
    Fetch flight information and augment it with additional details.
    """
    try:
        result = get_flights(
            flight_data=flight_data,
            trip=trip,
            seat=seat,
            max_stops=max_stops,
            passengers=passengers,
            fetch_mode=fetch_mode
        )
        
        query_time = datetime.now().strftime('%I:%M %p on %a, %b %d, %Y')

        if result.flights:
            flight_info = vars(result.flights[0])
            flight_info['departure'] = datetime.strptime(
                flight_info['departure'] + ', 2025', 
                '%I:%M %p on %a, %b %d, %Y'
            ).strftime('%I:%M %p on %a, %b %d, %Y')
        else:
            flight_info = {}

        additional_info = {
            'query_time': query_time,
            'from_airport': flight_data[0].from_airport,
            'to_airport': flight_data[0].to_airport,
            'seat': seat,
            'trip': trip
        }

        # Create the flight data dictionary
        flight_data_dict = OrderedDict([
            ('query_time', additional_info['query_time']),
            ('from_airport', additional_info['from_airport']),
            ('to_airport', additional_info['to_airport']),
            ('trip', additional_info['trip']),
            ('seat', additional_info['seat']),
            ('name', flight_info.get('name')),
            ('departure', flight_info.get('departure')),
            ('arrival', flight_info.get('arrival')),
            ('duration', flight_info.get('duration')),
            ('stops', flight_info.get('stops')),
            ('price', flight_info.get('price')),
            ('is_best', flight_info.get('is_best')),
            ('arrival_time_ahead', flight_info.get('arrival_time_ahead')),
            ('delay', flight_info.get('delay'))
        ])

        # Store the flight data in the database
        flight_id = store_flight_search(flight_data_dict)
        if flight_id:
            print(f"Flight data stored with ID: {flight_id}")

        return flight_data_dict

    except AssertionError as e:
        return {"error": f"No flights available: {str(e)}"}