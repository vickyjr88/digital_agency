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
    trends = spotter.get_top_trends(limit=10)
    
    if not trends:
        logging.warning("No trends found. Aborting cycle.")
        return

    # 2. Initialize Generator and Sheets Handler
    generator = ContentGenerator()
    sheets = SheetsHandler()
    sheets_connected = sheets.connect()

    if not sheets_connected:
        logging.warning("Could not connect to Google Sheets. Content will only be logged.")

    # 3. Generate Content for each Brand (Two Cycles: Viral & Local/Niche)
    # We'll use the #1 trend for "Viral" and the #5 trend (or similar) for "Local/Niche"
    # assuming the list is ordered by popularity.
    
    target_trends = []
    if len(trends) >= 1:
        target_trends.append({"type": "Viral/Top", "topic": trends[0]})
    
    # Cycle 2: AI Selects the best "Local" trend
    if len(trends) > 1:
        local_trend = generator.select_local_trend(trends)
        if local_trend:
             target_trends.append({"type": "Local/Niche (AI)", "topic": local_trend})
        elif len(trends) >= 5:
             # Fallback to index 4 if AI fails
             target_trends.append({"type": "Local/Niche (Fallback)", "topic": trends[4]})
        else:
             target_trends.append({"type": "Secondary", "topic": trends[1]})

    for cycle in target_trends:
        trend_topic = cycle['topic']
        cycle_type = cycle['type']
        logging.info(f"--- Starting Cycle: {cycle_type} (Trend: {trend_topic}) ---")

        for brand_key, persona in PERSONAS.items():
            logging.info(f"Processing brand: {persona['name']}")
            
            # Pass the cycle type to the generator to influence the prompt?
            # For now, just generating based on the trend is enough, 
            # but we could append "Focus on local relevance" to the prompt for the second cycle.
            
            # We need to update generator.py to accept context or just append it to the trend string
            # e.g. "Nairobi Rains (Focus on local community impact)"
            
            effective_trend = trend_topic
            if cycle_type == "Local/Niche":
                 # subtly influence the generator
                 pass 

            content = generator.generate_content(effective_trend, persona)
            
            if content:
                if sheets_connected:
                    # Append cycle type to the trend name in the sheet for clarity
                    sheets.save_content(persona['name'], f"{trend_topic} ({cycle_type})", content)
                else:
                    logging.info(f"Generated Content for {persona['name']} [{cycle_type}]:\n{content}")
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
