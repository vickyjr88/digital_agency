import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from datetime import datetime
import os

class SheetsHandler:
    def __init__(self, credentials_file='service_account.json', sheet_name='Agency Content Calendar'):
        self.credentials_file = credentials_file
        self.sheet_name = sheet_name
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.client = None
        self.sheet = None

    def connect(self):
        try:
            if not os.path.exists(self.credentials_file):
                logging.warning(f"Credentials file '{self.credentials_file}' not found. Google Sheets integration will be disabled.")
                return False
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, self.scope)
            self.client = gspread.authorize(creds)
            # Open the spreadsheet. If it doesn't exist, we might want to create it, 
            # but usually it's better to expect an existing one or create one if possible.
            # For now, let's try to open it.
            try:
                self.sheet = self.client.open(self.sheet_name).sheet1
            except gspread.SpreadsheetNotFound:
                logging.warning(f"Spreadsheet '{self.sheet_name}' not found. Creating it...")
                sh = self.client.create(self.sheet_name)
                sh.share('vickyjunior@gmail.com', perm_type='user', role='owner') # Placeholder email, maybe should ask user
                self.sheet = sh.sheet1
                # Initialize headers
                self.sheet.append_row(["Timestamp", "Brand", "Trend", "Tweet", "Facebook Post", "IG Reel Script", "TikTok Idea", "Status"])
            
            return True
        except Exception as e:
            logging.error(f"Error connecting to Google Sheets: {e}")
            return False

    def save_content(self, brand_name, trend, content_data):
        if not self.sheet:
            if not self.connect():
                logging.error("Cannot save content: No connection to Google Sheets.")
                return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            brand_name,
            trend,
            str(content_data.get('tweet', '')),
            str(content_data.get('facebook_post', '')),
            str(content_data.get('instagram_reel_script', '')),
            str(content_data.get('tiktok_idea', '')),
            "Pending Review"
        ]
        
        try:
            self.sheet.append_row(row)
            logging.info(f"Saved content for {brand_name} to Google Sheet.")
        except Exception as e:
            logging.error(f"Error saving to Google Sheet: {e}")

if __name__ == "__main__":
    # Test
    handler = SheetsHandler()
    if handler.connect():
        handler.save_content("Test Brand", "Test Trend", {
            "tweet": "Hello world",
            "facebook_post": "Hello Facebook",
            "instagram_reel_script": "Dance",
            "tiktok_idea": "Jump"
        })
