# Regular Flyer Buddy (RFB) 🛫

Regular Flyer Buddy is a flight search and analysis tool that helps you track flight prices over time and identify the best times to book your flights.

## Features

- **Single Flight Search**: Quick search for specific flight routes
- **Batch Processing**: Monitor multiple flight routes and dates automatically
- **Price Analysis**: Track price trends and historical data
- **Interactive Dashboard**: Visualize flight price patterns and trends
- **Database Integration**: Store and analyze historical flight data

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/regular-flyer-buddy.git
cd regular-flyer-buddy
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Set up your database configuration in `.env`:
```
DB_NAME=rfb
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

4. Initialize the database:
```
./cli.py init-db
```

## Usage

### CLI Commands

1. **Single Flight Search**:
```
./cli.py search -f SEA -t MKE -d 2024-03-01
```

2. **Generate Search Configurations**:
```
./cli.py generate-configs -f SEA -t MKE --start-date 2024-03-01 --end-date 2024-09-01
```

3. **Batch Process Searches**:
```
./cli.py batch-process flight_configs.json
```

4. **Refresh Analysis Views**:
```
./cli.py refresh-views
```

### Web Dashboard

Launch the Streamlit dashboard:
```
streamlit run app/main.py
```

## Analysis Features

- **Route Analysis**: View price patterns by day of week
- **Price Trends**: Track how prices change over time
- **Historical Data**: Access lowest, highest, and average prices
- **Advance Purchase Analysis**: Understand how prices vary based on booking timing

## Project Structure

```
regular-flyer-buddy/
├── app/
│   └── main.py           # Streamlit dashboard
├── services/
│   ├── flight_service.py     # Flight search logic
│   ├── flight_database.py    # Database operations
│   ├── analysis_views.py     # Analysis queries
│   └── batch_processor.py    # Batch processing
├── cli.py                # Command-line interface
├── scheduler.py          # Automated scheduling
└── requirements.txt      # Dependencies
```

## Requirements

- Python 3.8+
- PostgreSQL
- Dependencies listed in `requirements.txt`

## Acknowledgments

- Built with [Fast Flights](https://pypi.org/project/fast-flights/) for flight data
- Uses Streamlit for the dashboard interface
- PostgreSQL for data storage and analysis
