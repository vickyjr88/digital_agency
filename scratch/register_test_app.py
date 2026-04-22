import sys
import os

# Add current directory to path so we can import local modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database.config import SessionLocal, init_db
from database.models import ExternalService
import secrets

def create_external_app(name):
    # Ensure tables exist
    init_db()
    
    db = SessionLocal()

    try:
        # Check if already exists
        existing = db.query(ExternalService).filter(ExternalService.name == name).first()
        if existing:
            print(f"App '{name}' already exists.")
            print(f"API Key: {existing.api_key}")
            return
        
        api_key = f"dex_{secrets.token_urlsafe(32)}"
        new_app = ExternalService(
            name=name,
            api_key=api_key
        )
        db.add(new_app)
        db.commit()
        print(f"Successfully registered '{name}'")
        print(f"API Key: {api_key}")
        print("Keep this key safe!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    app_name = "External Ebook Delivery App"
    create_external_app(app_name)
