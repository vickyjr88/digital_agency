import requests
from bs4 import BeautifulSoup
import logging
from typing import List

class TrendScraper:
    def __init__(self):
        self.url = "https://trends24.in/kenya/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

    def get_kenya_trends(self) -> List[str]:
        """
        Scrapes the top trends from trends24.in/kenya/
        """
        try:
            logging.info(f"Scraping trends from {self.url}...")
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trends24 structure: <ol class="trend-card__list"><li><a>Trend Name</a></li>...</ol>
            # We usually want the first card (most recent hour)
            
            trends = []
            
            # Find the first trend list (latest hour)
            latest_list = soup.find('ol', class_='trend-card__list')
            if latest_list:
                list_items = latest_list.find_all('li')
                for item in list_items:
                    link = item.find('a', class_='trend-link')
                    if link:
                        trends.append(link.text.strip())
            
            logging.info(f"Found {len(trends)} trends from Trends24")
            return trends
            
        except Exception as e:
            logging.error(f"Error scraping Trends24: {e}")
            return []

if __name__ == "__main__":
    # Test
    scraper = TrendScraper()
    print(scraper.get_kenya_trends())
