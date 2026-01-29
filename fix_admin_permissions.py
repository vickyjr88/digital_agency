
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import User, UserType, UserRole

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from database.config import get_db, SessionLocal

def fix_admin_permissions(email):
    print(f"Checking permissions for {email}...")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"Error: User with email {email} not found.")
            return
        
        print(f"Found user: {user.name} (ID: {user.id})")
        print(f"Current Role: {user.role}")
        print(f"Current User Type: {user.user_type}")
        
        # Update to ensure full Admin access
        changes_made = False
        
        # 1. Update Legacy Role if needed
        if user.role != UserRole.ADMIN:
            print(f"Updating legacy role from {user.role} to ADMIN...")
            user.role = UserRole.ADMIN
            changes_made = True
            
        # 2. Update User Type
        # Check if it's already the enum value or string 'admin'
        current_type_str = str(user.user_type.value) if hasattr(user.user_type, 'value') else str(user.user_type)
        
        if current_type_str.lower() != 'admin':
            print(f"Updating user_type from {user.user_type} to admin...")
            user.user_type = UserType.ADMIN
            changes_made = True
            
        if changes_made:
            db.commit()
            print("Successfully updated user permissions! ✅")
            print("Please restart the backend service to ensure changes take effect.")
        else:
            print("User already has correct ADMIN permissions. No changes needed.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix admin user permissions')
    parser.add_argument('--email', default='admin@dexter.com', help='Email of the admin user')
    
    args = parser.parse_args()
    fix_admin_permissions(args.email)
