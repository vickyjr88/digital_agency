import argparse
import time
import schedule
import logging
import sys
from database.config import SessionLocal
from core.trend_service import TrendService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("trend_worker.log")
    ]
)

def run_trend_cycle():
    logging.info("Starting Trend Fetch Cycle...")
    db = SessionLocal()
    try:
        service = TrendService(db)
        trends = service.fetch_and_store_trends()
        logging.info(f"Cycle Complete. {len(trends)} new trends found.")
    except Exception as e:
        logging.error(f"Error in trend cycle: {e}")
    finally:
        db.close()

def start_scheduler():
    logging.info("Starting Trend Scheduler (Every 2 Hours)...")
    # Run once immediately
    run_trend_cycle()
    
    schedule.every(2).hours.do(run_trend_cycle)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    parser = argparse.ArgumentParser(description="Dexter Trend Worker")
    parser.add_argument("--mode", choices=["once", "schedule"], default="schedule", help="Run once or schedule")
    args = parser.parse_args()

    if args.mode == "schedule":
        start_scheduler()
    else:
        run_trend_cycle()

if __name__ == "__main__":
    main()
