import requests
import xml.etree.ElementTree as ET
import logging
import tweepy
import os

class TrendSpotter:
    def __init__(self, geo='KE'):
        self.geo = geo
        # Google Trends RSS
        self.rss_url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={self.geo}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Twitter API Setup
        self.twitter_client = None
        self.twitter_api = None
        self._setup_twitter()

    def _setup_twitter(self):
        try:
            api_key = os.getenv("TWITTER_API_KEY")
            api_secret = os.getenv("TWITTER_API_SECRET")
            access_token = os.getenv("TWITTER_ACCESS_TOKEN")
            access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
            
            if api_key and api_secret:
                auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
                self.twitter_api = tweepy.API(auth)
                logging.info("Twitter API initialized.")
            else:
                logging.warning("Twitter API keys missing. Skipping Twitter setup.")
        except Exception as e:
            logging.error(f"Error initializing Twitter API: {e}")

    def get_top_trends(self, limit=3):
        """
        Fetches trends from Twitter (Trends API -> Timeline Analysis) and Google Trends.
        """
        trends = []
        
        # 1. Try Twitter Trends (Official API)
        twitter_trends = self.get_twitter_trends(limit=limit)
        if twitter_trends:
            trends.extend(twitter_trends)
            logging.info(f"Using Twitter Trends: {twitter_trends}")
        
        # 2. If Trends API fails (403), try Timeline Analysis
        if not trends and self.twitter_api:
            logging.info("Twitter Trends failed/empty. Analyzing Timeline for topics...")
            timeline_topics = self.get_timeline_topics(limit=limit)
            if timeline_topics:
                trends.extend(timeline_topics)
                logging.info(f"Using Timeline Topics: {timeline_topics}")

        # 3. If we still need trends, fetch from Google
        if len(trends) < limit:
            google_limit = limit - len(trends)
            google_trends = self.get_google_trends(limit=google_limit)
            if google_trends:
                trends.extend(google_trends)
                logging.info(f"Added Google Trends: {google_trends}")

        # 4. Fallback if empty
        if not trends:
            return self._get_fallback_trends()
            
        return trends[:limit]

    def get_twitter_trends(self, limit=3):
        """
        Fetches top trends from Twitter for Kenya.
        """
        if not self.twitter_api:
            return []
            
        try:
            woeid = 23424863 
            trends_response = self.twitter_api.get_place_trends(id=woeid)
            if trends_response:
                trend_data = trends_response[0]['trends']
                sorted_trends = sorted(trend_data, key=lambda x: x['tweet_volume'] or 0, reverse=True)
                return [t['name'] for t in sorted_trends[:limit]]
        except Exception as e:
            logging.warning(f"Twitter Trends API failed: {e}")
            return []

    def get_timeline_topics(self, limit=3):
        """
        Fetches trends by scraping Trends24 (Kenya) since Twitter API Read access is restricted.
        """
        try:
            url = "https://trends24.in/kenya/"
            logging.info(f"Scraping trends from {url}...")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Trends24 structure: <ol class="trend-card__list"><li><a>Trend Name</a></li>...
                # We want the first list (current hour)
                trend_list = soup.find('ol', class_='trend-card__list')
                if trend_list:
                    trends = []
                    for li in trend_list.find_all('li'):
                        tag = li.find('a')
                        if tag:
                            trends.append(tag.text)
                            if len(trends) >= limit:
                                break
                    
                    if trends:
                        logging.info(f"Scraped Trends24: {trends}")
                        return trends
            
            logging.warning("Failed to scrape Trends24.")
            return []
            
        except Exception as e:
            logging.error(f"Error scraping Trends24: {e}")
            return []

    def get_google_trends(self, limit=3):
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
                        return trends
                else:
                    logging.warning(f"Failed to fetch from {url}. Status: {response.status_code}")
            except Exception as e:
                logging.error(f"Error fetching from {url}: {e}")

        logging.warning("All Google RSS feeds failed.")
        return []

    def _get_fallback_trends(self):
        # A more diverse set of fallback trends relevant to Kenya/Global
        return ["Artificial Intelligence", "Crypto Market", "Premier League", "Nairobi Traffic", "Kenyan Shilling"]

if __name__ == "__main__":
    # Test
    spotter = TrendSpotter()
    print(spotter.get_top_trends())
