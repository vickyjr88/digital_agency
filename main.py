import argparse
import time
import schedule
import logging
import sys
from config.personas import PERSONAS
from core.trends import TrendSpotter
from core.generator import ContentGenerator
from core.sheets_handler import SheetsHandler

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agency_bot.log")
    ]
)

def run_agency_cycle():
    logging.info("Starting Agency Content Cycle...")
    
    # 1. Fetch Trends
    spotter = TrendSpotter()
    trends = spotter.get_top_trends(limit=3)
    
    if not trends:
        logging.warning("No trends found. Aborting cycle.")
        return

    # 2. Initialize Generator and Sheets Handler
    generator = ContentGenerator()
    sheets = SheetsHandler()
    sheets_connected = sheets.connect()

    if not sheets_connected:
        logging.warning("Could not connect to Google Sheets. Content will only be logged.")

    # 3. Generate Content for each Brand
    for brand_key, persona in PERSONAS.items():
        logging.info(f"Processing brand: {persona['name']}")
        
        # Pick the first trend for simplicity, or iterate all? 
        # Let's pick the most relevant one or just the first one for now.
        # Ideally, we'd match trends to brands, but for now, let's use the top trend.
        trend = trends[0] 
        
        content = generator.generate_content(trend, persona)
        
        if content:
            if sheets_connected:
                sheets.save_content(persona['name'], trend, content)
            else:
                logging.info(f"Generated Content for {persona['name']}:\n{content}")
        else:
            logging.error(f"Failed to generate content for {persona['name']}")

    logging.info("Agency Content Cycle Completed.")

def start_scheduler():
    logging.info("Starting Scheduler (Every 3 Hours)...")
    # Run once immediately
    run_agency_cycle()
    
    schedule.every(3).hours.do(run_agency_cycle)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    parser = argparse.ArgumentParser(description="Digital Employee: Automated Marketing CLI")
    parser.add_argument("--mode", choices=["once", "schedule"], default="once", help="Run once or schedule every 3 hours")
    args = parser.parse_args()

    if args.mode == "schedule":
        start_scheduler()
    else:
        run_agency_cycle()

if __name__ == "__main__":
    main()
