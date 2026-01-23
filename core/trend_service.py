from sqlalchemy.orm import Session
from database.models import Trend
from core.trend_scraper import TrendScraper
from datetime import datetime, timedelta
import logging

class TrendService:
    def __init__(self, db: Session):
        self.db = db
        self.scraper = TrendScraper()

    def fetch_and_store_trends(self):
        """
        Fetches trends from external sources and stores them in the DB.
        """
        logging.info("Fetching fresh trends...")
        try:
            # Get trends from scraper
            raw_trends = self.scraper.get_kenya_trends()
            
            # If scraper fails, fallback to existing spotter logic (optional, or just return empty)
            if not raw_trends:
                logging.warning("Scraper returned no trends.")
                return []
            
            saved_trends = []
            six_hours_ago = datetime.utcnow() - timedelta(hours=6)
            
            for topic in raw_trends:
                # Check if trend exists within the last 6 hours
                existing = self.db.query(Trend).filter(
                    Trend.topic == topic,
                    Trend.timestamp >= six_hours_ago
                ).first()
                
                if not existing:
                    new_trend = Trend(
                        topic=topic,
                        source="Trends24",
                        volume="Trending"
                    )
                    self.db.add(new_trend)
                    saved_trends.append(new_trend)
                else:
                    logging.info(f"Skipping duplicate trend '{topic}' (found within last 6h)")
            
            self.db.commit()
            logging.info(f"Saved {len(saved_trends)} new trends.")
            return saved_trends
        except Exception as e:
            logging.error(f"Error in fetch_and_store_trends: {e}")
            self.db.rollback()
            return []

    def get_latest_trends(self, limit=20):
        return self.db.query(Trend).order_by(Trend.timestamp.desc()).limit(limit).all()
