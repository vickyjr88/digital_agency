from sqlalchemy.orm import Session
from database.models import Trend
from core.trends import TrendSpotter
import logging

class TrendService:
    def __init__(self, db: Session):
        self.db = db
        self.spotter = TrendSpotter()

    def fetch_and_store_trends(self):
        """
        Fetches trends from external sources and stores them in the DB.
        """
        logging.info("Fetching fresh trends...")
        try:
            raw_trends = self.spotter.get_top_trends(limit=10)
            
            saved_trends = []
            for topic in raw_trends:
                # Check if trend exists (simple check by topic for now)
                # In a real app, we might want to check if it was trending recently
                existing = self.db.query(Trend).filter(Trend.topic == topic).first()
                if not existing:
                    new_trend = Trend(
                        topic=topic,
                        source="Aggregated", # Since Spotter aggregates
                        volume="Trending"
                    )
                    self.db.add(new_trend)
                    saved_trends.append(new_trend)
            
            self.db.commit()
            logging.info(f"Saved {len(saved_trends)} new trends.")
            return saved_trends
        except Exception as e:
            logging.error(f"Error in fetch_and_store_trends: {e}")
            self.db.rollback()
            return []

    def get_latest_trends(self, limit=20):
        return self.db.query(Trend).order_by(Trend.timestamp.desc()).limit(limit).all()
