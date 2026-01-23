import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from datetime import datetime
import os
import json

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
        
        # Helper function to safely convert to string, using JSON for dicts/lists
        def safe_str(value):
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        
        row = [
            timestamp,
            brand_name,
            trend,
            str(content_data.get('tweet', '')),
            str(content_data.get('facebook_post', '')),
            safe_str(content_data.get('instagram_reel_script', '')),
            safe_str(content_data.get('tiktok_idea', '')),
            "Pending Review"
        ]
        
        try:
            self.sheet.append_row(row)
            logging.info(f"Saved content for {brand_name} to Google Sheet.")
        except Exception as e:
            logging.error(f"Error saving to Google Sheet: {e}")

    def get_all_content(self):
        """
        Fetches all records from the sheet.
        Returns a list of dictionaries with 'id' (row number) included.
        Handles cases where headers might be missing.
        """
        if not self.sheet:
            if not self.connect():
                return []
        
        try:
            # Get all values
            rows = self.sheet.get_all_values()
            if not rows:
                return []
            
            EXPECTED_HEADERS = ["Timestamp", "Brand", "Trend", "Tweet", "Facebook Post", "Instagram Reel Script", "TikTok Idea", "Status"]
            
            # Check if the first row looks like headers
            first_row = rows[0]
            is_header = False
            if len(first_row) >= 3 and first_row[0] == "Timestamp" and first_row[1] == "Brand":
                is_header = True
            
            headers = EXPECTED_HEADERS
            start_index = 0
            
            if is_header:
                headers = first_row
                start_index = 1
            
            data = []
            # Iterate through rows
            # Row index in Google Sheets is 1-based.
            # If is_header is True, first data row is index 2.
            # If is_header is False, first data row is index 1.
            
            current_row_idx = start_index + 1 # 1-based index for the first data row
            
            for i, row in enumerate(rows[start_index:], start=current_row_idx):
                record = {"id": i}
                for h_index, header in enumerate(headers):
                    if h_index < len(row):
                        record[header] = row[h_index]
                    else:
                        record[header] = ""
                
                # Ensure critical keys exist even if row is short
                for expected in EXPECTED_HEADERS:
                    if expected not in record:
                        record[expected] = ""
                        
                data.append(record)
            
            # Sort by Timestamp descending (newest first) if possible
            return sorted(data, key=lambda x: x.get('Timestamp', ''), reverse=True)
        except Exception as e:
            logging.error(f"Error fetching content: {e}")
            return []

    def update_content(self, row_id, update_data):
        """
        Updates a specific row in the sheet.
        row_id: The 1-based row index.
        update_data: Dictionary of {Header: NewValue}
        """
        if not self.sheet:
            if not self.connect():
                return False
        
        try:
            # We need to map headers to column indices
            headers = self.sheet.row_values(1)
            
            # Prepare a list of cells to update or update one by one?
            # Updating one by one is slower but safer if we don't want to overwrite everything.
            # Better: Construct the full row? No, that's risky.
            # Let's iterate over the update_data and find the column index for each.
            
            for key, value in update_data.items():
                if key in headers:
                    col_index = headers.index(key) + 1
                    self.sheet.update_cell(row_id, col_index, str(value))
            
            logging.info(f"Updated row {row_id} in Google Sheet.")
            return True
        except Exception as e:
            logging.error(f"Error updating content: {e}")
            return False

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
