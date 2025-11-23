import requests
import xml.etree.ElementTree as ET
import logging

class TrendSpotter:
    def __init__(self, geo='KE'):
        self.geo = geo
        # specific geo code for Kenya in some google contexts is 'KE' but for RSS it might be different or not supported for daily trends.
        # Trying with a User-Agent to avoid being blocked.
        self.rss_url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={self.geo}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_top_trends(self, limit=3):
        """
        Fetches the top trending searches using Google Trends RSS feed.
        """
        # List of RSS URLs to try in order: Kenya, South Africa, US (as last resort for data)
        urls = [
            f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={self.geo}",
            "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ZA",
            "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        ]

        for url in urls:
            try:
                logging.info(f"Fetching trends from RSS: {url}...")
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    trends = []
                    for item in root.findall('.//item'):
                        title = item.find('title').text
                        trends.append(title)
                        if len(trends) >= limit:
                            break
                    
                    if trends:
                        logging.info(f"Top trends found: {trends}")
                        return trends
                else:
                    logging.warning(f"Failed to fetch from {url}. Status: {response.status_code}")
            except Exception as e:
                logging.error(f"Error fetching from {url}: {e}")

        logging.warning("All RSS feeds failed. Using fallback trends.")
        return self._get_fallback_trends()

    def _get_fallback_trends(self):
        # A more diverse set of fallback trends relevant to Kenya/Global
        return ["Artificial Intelligence", "Crypto Market", "Premier League", "Nairobi Traffic", "Kenyan Shilling"]

if __name__ == "__main__":
    # Test
    spotter = TrendSpotter()
    print(spotter.get_top_trends())
