import streamlit as st
from fast_flights import FlightData, Passengers
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import time

# Ensure the parent directory is in the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.flight_service import get_flights_with_additional_info
from pprint import pformat
from services.configuration_service import (
    create_flight_configurations,
    save_configurations,
    load_configurations,
    FlightConfiguration
)
from services.batch_processor import process_configurations, filter_valid_configurations

st.title("Reguler Flyer Buddy")

# Add tabs to separate single search and batch processing
tab1, tab2 = st.tabs(["Single Search", "Batch Processing"])

with tab1:
    # Input Fields
    departure_airport = st.text_input("From (IATA Code)", "SEA")
    arrival_airport = st.text_input("To (IATA Code)", "MKE")
    date = st.date_input("Departure Date")
    trip_type = st.selectbox("Trip Type", ["one-way", "round-trip"])
    seat_class = st.selectbox("Seat Class", ["economy", "business"])
    max_stops = st.slider("Max Stops", 0, 2, 0)
    num_adults = st.number_input("Number of Adults", min_value=1, max_value=10, value=1)
    fetch_mode = st.selectbox("Fetch Mode", ["normal", "fallback"])

    def format_datetime(dt_str):
        try:
            dt = datetime.strptime(dt_str, '%I:%M %p on %a, %b %d, %Y')
            return dt.strftime('%I:%M %p on %a, %b %d, %Y')
        except ValueError:
            return dt_str

    # Search Button
    if st.button("Search Flights"):
        flight_data = [FlightData(date=date.strftime('%Y-%m-%d'), from_airport=departure_airport, to_airport=arrival_airport)]
        passengers = Passengers(adults=num_adults)

        result = get_flights_with_additional_info(
            flight_data=flight_data,
            trip=trip_type,
            seat=seat_class,
            max_stops=max_stops,
            passengers=passengers,
            fetch_mode=fetch_mode
        )

        # Display results in card format
        if result:
            # Ensure result is a list of dictionaries
            if isinstance(result, dict):
                result = [result]
            
            for flight in result:
                query_time = format_datetime(flight.get('query_time', 'N/A'))
                departure = format_datetime(flight.get('departure', ''))
                arrival = format_datetime(flight.get('arrival', ''))

                st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                        <h4>{flight.get('name', 'Unknown Airline')}</h4>
                        <p><strong>Query Time:</strong> {query_time}</p>
                        <p><strong>From:</strong> {flight.get('from_airport', '')} <strong>To:</strong> {flight.get('to_airport', '')}</p>
                        <p><strong>Departure:</strong> {departure}</p>
                        <p><strong>Arrival:</strong> {arrival}</p>
                        <p><strong>Duration:</strong> {flight.get('duration', '')}</p>
                        <p><strong>Stops:</strong> {flight.get('stops', '')}</p>
                        <p><strong>Price:</strong> {flight.get('price', '')}</p>
                        <p><strong>Best Option:</strong> {'Yes' if flight.get('is_best', False) else 'No'}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No flights found.")

with tab2:
    st.header("Batch Flight Search Configuration")

    # Batch search parameters
    col1, col2 = st.columns(2)
    with col1:
        batch_from_airport = st.text_input("From (IATA Code)", "SEA", key="batch_from")
        batch_to_airport = st.text_input("To (IATA Code)", "MKE", key="batch_to")
        batch_start_date = st.date_input("Start Date", datetime.now())
        batch_end_date = st.date_input("End Date", datetime.now() + timedelta(days=180))
        
    with col2:
        outbound_day = st.selectbox("Outbound Day", 
            options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            index=3  # Thursday
        )
        return_day = st.selectbox("Return Day", 
            options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            index=6  # Sunday
        )
        batch_seat_class = st.selectbox("Seat Class", ["economy", "business"], key="batch_seat")
        batch_max_stops = st.slider("Max Stops", 0, 2, 0, key="batch_stops")

    # Convert day names to numbers (0 = Monday, 6 = Sunday)
    day_to_number = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }

    if st.button("Generate Configurations"):
        configs = create_flight_configurations(
            from_airport=batch_from_airport,
            to_airport=batch_to_airport,
            start_date=datetime.combine(batch_start_date, datetime.min.time()),
            end_date=datetime.combine(batch_end_date, datetime.min.time()),
            outbound_day=day_to_number[outbound_day],
            return_day=day_to_number[return_day],
            seat_class=batch_seat_class,
            max_stops=batch_max_stops
        )
        
        # Store configurations in session state
        st.session_state.configs = configs
        
        # Display configuration summary
        st.write(f"Generated {len(configs)} flight configurations")
        
        # Show sample of configurations in a table
        configs_df = pd.DataFrame([vars(config) for config in configs])
        st.dataframe(configs_df)

    # Add a separate section for saving configurations
    if hasattr(st.session_state, 'configs') and st.session_state.configs:
        if st.button("Save Configurations"):
            save_path = "flight_configs.json"
            save_configurations(st.session_state.configs, save_path)
            st.success(f"Configurations saved to {save_path}")

    # Batch Processing Section
    st.header("Process Configurations")
    
    if st.button("Start Batch Processing"):
        if hasattr(st.session_state, 'configs') and st.session_state.configs:
            configs = st.session_state.configs
            
            # Filter configurations
            valid_configs, invalid_configs = filter_valid_configurations(configs)
            
            if invalid_configs:
                st.warning(f"Skipping {len(invalid_configs)} configurations with past dates")
            
            if not valid_configs:
                st.error("No valid configurations to process (all dates are in the past)")
            else:
                # Create a progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process configurations with progress updates
                total_configs = len(valid_configs)
                for i, config in enumerate(valid_configs):
                    try:
                        flight_data = [FlightData(
                            date=config.date,
                            from_airport=config.from_airport,
                            to_airport=config.to_airport
                        )]
                        passengers = Passengers(adults=1)

                        status_text.text(f"Processing flight {i+1}/{total_configs}: "
                                       f"{config.from_airport} -> {config.to_airport} on {config.date}")
                        
                        result = get_flights_with_additional_info(
                            flight_data=flight_data,
                            trip=config.trip_type,
                            seat=config.seat_class,
                            max_stops=config.max_stops,
                            passengers=passengers,
                            fetch_mode="normal"
                        )
                        
                        # Update progress
                        progress_bar.progress((i + 1) / total_configs)
                        
                        # Add delay between requests
                        time.sleep(5)  # 5 second delay between requests
                        
                    except Exception as e:
                        st.error(f"Error processing configuration: {e}")
                        continue

                status_text.text("Batch processing completed!")
                st.success(f"Successfully processed {total_configs} configurations")
        else:
            st.error("No configurations available. Please generate configurations first.")

    # Option to load saved configurations
    st.header("Load Saved Configurations")
    if st.button("Load Configurations"):
        try:
            configs = load_configurations("flight_configs.json")
            st.session_state.configs = configs
            
            # Display loaded configurations
            configs_df = pd.DataFrame([vars(config) for config in configs])
            st.dataframe(configs_df)
            st.success("Configurations loaded successfully!")
        except FileNotFoundError:
            st.error("No saved configurations found.")
