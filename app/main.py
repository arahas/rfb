import streamlit as st
from fast_flights import FlightData, Passengers
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import plotly.express as px
import plotly.graph_objects as go


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
from services.analysis_views import get_analysis_data, refresh_analysis_views
from services.flight_database import create_connection


st.title("Reguler Flyer Buddy 😎")

def initialize_session_states():
    """Initialize all session state variables if they don't exist"""
    if 'show_route_analysis' not in st.session_state:
        st.session_state.show_route_analysis = False
    if 'show_weekly_trends' not in st.session_state:
        st.session_state.show_weekly_trends = False
    if 'show_price_analysis' not in st.session_state:
        st.session_state.show_price_analysis = False
    if 'show_raw_data' not in st.session_state:
        st.session_state.show_raw_data = False

# Add tabs to separate single search and batch processing
tab1, tab2, tab3 = st.tabs(["Single Search", "Batch Processing", "Analysis"])

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

with tab3:
    st.header("Flight Price Analysis")
    
    initialize_session_states()
    
    conn = create_connection()
    
    # Add refresh button
    if st.button("🔄 Refresh Analysis Data"):
        try:
            refresh_analysis_views(conn)
            st.success("Analysis views refreshed successfully!")
        except Exception as e:
            st.error(f"Error refreshing views: {str(e)}")
    
    # Common filters at the top
    col1, col2 = st.columns(2)
    with col1:
        from_airport = st.text_input("From Airport", "SEA")
    with col2:
        to_airport = st.text_input("To Airport", "MKE")

    # 1. Route Analysis
    st.subheader("🛫 Route Analysis by Day of Week")
    if st.button("Show Route Analysis"):
        st.session_state.show_route_analysis = not st.session_state.show_route_analysis

    if st.session_state.show_route_analysis:
        route_data = get_analysis_data(
            conn, 
            'route_analysis',
            from_airport=from_airport,
            to_airport=to_airport
        )
        
        if route_data:
            df = pd.DataFrame(route_data)
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                       'Friday', 'Saturday']
            # Convert day_of_week to integer before indexing
            df['day_name'] = df['day_of_week'].apply(lambda x: day_names[int(x)])
            
            # Create the bar chart
            fig = go.Figure()
            
            # Add Historical High bars (black)
            fig.add_trace(go.Bar(
                x=df['day_name'],
                y=df['historical_high'],
                name='Historical High',
                marker_color='black',
                width=0.2
            ))
            
            # Add Latest Price bars (red)
            fig.add_trace(go.Bar(
                x=df['day_name'],
                y=df['latest_price'],
                name='Latest Price',
                marker_color='red',
                width=0.2
            ))
            
            # Add Historical Low bars (green)
            fig.add_trace(go.Bar(
                x=df['day_name'],
                y=df['historical_low'],
                name='Historical Low',
                marker_color='green',
                width=0.2
            ))
            
            # Update layout
            fig.update_layout(
                title='Price Analysis by Day of Week',
                xaxis_title='Day of Week',
                yaxis_title='Price ($)',
                barmode='group',  # Group bars side by side
                showlegend=True,
                bargap=0.15,      # Gap between bars in the same group
                bargroupgap=0.1   # Gap between bar groups
            )
            
            st.plotly_chart(fig)
            st.dataframe(df)
        else:
            st.warning("No route analysis data available")

    # 2. Price Trends by Query Date
    st.subheader("📈 Price Trends by Query Date")
    if st.button("Show Price Trends"):
        st.session_state.show_weekly_trends = not st.session_state.show_weekly_trends

    if st.session_state.show_weekly_trends:
        trends_data = get_analysis_data(
            conn, 
            'price_trends',
            from_airport=from_airport,
            to_airport=to_airport
        )
        
        if trends_data:
            df = pd.DataFrame(trends_data)
            
            # Create the line plot
            fig = go.Figure()
            
            # Get unique query dates
            unique_query_dates = sorted(df['query_date'].unique())
            
            # Add a line for each query date
            for query_date in unique_query_dates:
                mask = df['query_date'] == query_date
                df_filtered = df[mask]
                
                fig.add_trace(go.Scatter(
                    x=df_filtered['departure_date'],
                    y=df_filtered['min_price'],
                    name=f'Prices as of {query_date.strftime("%Y-%m-%d")}',
                    mode='lines+markers'
                ))
            
            fig.update_layout(
                title='Price Trends by Query Date',
                xaxis_title='Departure Date',
                yaxis_title='Price ($)',
                showlegend=True
            )
            
            st.plotly_chart(fig)
            
            # Show the data in a table format
            st.dataframe(df.pivot(
                index='departure_date',
                columns='query_date',
                values='min_price'
            ).reset_index())
        else:
            st.warning("No price trends data available")

    # Initialize session state variables if they don't exist
    if 'show_price_analysis' not in st.session_state:
        st.session_state.show_price_analysis = False

    if 'show_raw_data' not in st.session_state:
        st.session_state.show_raw_data = False

    # 3. Comprehensive Price Analysis
    st.subheader("📊 Comprehensive Price Analysis")
    if st.button("Show Price Analysis"):
        st.session_state.show_price_analysis = not st.session_state.show_price_analysis

    if st.session_state.show_price_analysis:
        # Fetch all necessary data
        latest_data = get_analysis_data(conn, 'latest_prices',
                                      from_airport=from_airport, to_airport=to_airport)
        lowest_data = get_analysis_data(conn, 'lowest_prices',
                                      from_airport=from_airport, to_airport=to_airport)
        highest_data = get_analysis_data(conn, 'highest_prices',
                                      from_airport=from_airport, to_airport=to_airport)
        
        if any([latest_data, lowest_data, highest_data]):
            # Combine all data into a single DataFrame
            dfs = []
            merge_cols = ['departure', 'airline_name', 'from_airport', 'to_airport']
            
            if latest_data:
                df_latest = pd.DataFrame(latest_data)
                df_latest['departure'] = pd.to_datetime(df_latest['departure'])
                dfs.append(df_latest)
            if lowest_data:
                df_lowest = pd.DataFrame(lowest_data)
                df_lowest['departure'] = pd.to_datetime(df_lowest['departure'])
                dfs.append(df_lowest)
            if highest_data:
                df_highest = pd.DataFrame(highest_data)
                df_highest['departure'] = pd.to_datetime(df_highest['departure'])
                dfs.append(df_highest)
            
            # Merge all DataFrames
            df_combined = dfs[0]
            for df in dfs[1:]:
                df_combined = pd.merge(df_combined, df, on=merge_cols, how='outer')
            
            # Create comprehensive visualization
            fig = go.Figure()
            
            # Add high price line (black)
            fig.add_trace(go.Scatter(
                x=df_combined['departure'],
                y=df_combined['highest_price'],
                line=dict(color='black', width=2),
                name='High Price'
            ))
            
            # Add low price line (green)
            fig.add_trace(go.Scatter(
                x=df_combined['departure'],
                y=df_combined['lowest_price'],
                line=dict(color='green', width=2),
                name='Low Price'
            ))
            
            # Add shaded area between high and low prices
            fig.add_trace(go.Scatter(
                x=df_combined['departure'],
                y=df_combined['highest_price'],
                fill=None,
                mode='lines',
                line_color='rgba(0,0,0,0)',
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=df_combined['departure'],
                y=df_combined['lowest_price'],
                fill='tonexty',
                mode='lines',
                line_color='rgba(0,0,0,0)',
                fillcolor='rgba(128,128,128,0.2)',
                name='Price Range'
            ))
            
            # Add latest price as scatter points
            fig.add_trace(go.Scatter(
                x=df_combined['departure'],
                y=df_combined['latest_price'],
                mode='markers',
                marker=dict(
                    color='red',
                    size=8,
                    symbol='circle'
                ),
                name='Latest Price'
            ))
            
            fig.update_layout(
                title='Price Analysis Over Time',
                xaxis_title='Departure Date',
                yaxis_title='Price ($)',
                showlegend=True,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig)
            st.dataframe(df_combined)
        else:
            st.warning("""No price analysis data available. This could be because:
            1. No flight searches have been performed yet
            2. The specified route has no recorded data
            3. The data is still being collected
            
            Try performing some flight searches first or checking a different route.""")

    # 4. Flight Searches Data
    st.subheader("🔍 Flight Searches Data")
    if st.button("Show Raw Data"):
        st.session_state.show_raw_data = not st.session_state.show_raw_data

    if st.session_state.show_raw_data:
        flight_searches_data = get_analysis_data(conn, 'flight_searches', from_airport=from_airport, to_airport=to_airport)
        if flight_searches_data:
            flight_searches_df = pd.DataFrame(flight_searches_data)
            st.dataframe(flight_searches_df)
        else:
            st.warning("No flight searches data available.")
    else:
        st.write("Click the button above to view the raw flight searches data.")

    conn.close()

