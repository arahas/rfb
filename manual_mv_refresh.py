from services.analysis_views import refresh_analysis_views
from services.flight_database import create_connection
import sys
import time

def manual_refresh_views():
    print("Starting materialized views refresh...")
    conn = create_connection()
    try:
        # List of views to refresh
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
        
        total_views = len(views)
        for i, view in enumerate(views, 1):
            try:
                print(f"Refreshing {view} ({i}/{total_views})...")
                start_time = time.time()
                
                # Execute refresh for single view
                with conn.cursor() as cur:
                    cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
                    conn.commit()
                
                end_time = time.time()
                print(f"✓ Successfully refreshed {view} in {end_time - start_time:.2f} seconds")
                
            except Exception as e:
                print(f"✗ Error refreshing {view}: {str(e)}")
                continue
        
        print("\nRefresh operation completed!")
        
    except Exception as e:
        print(f"Critical error during refresh: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    manual_refresh_views()