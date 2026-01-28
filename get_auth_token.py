
import requests
import sys

BASE_URL = "http://localhost:8000/api/v2"

def get_token():
    # Try to login first
    login_data = {
        "email": "testbrand@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            return response.json()["access_token"]
    except Exception as e:
        print(f"Login failed: {e}")

    # If login fails, try to register
    register_data = {
        "email": "testbrand@example.com",
        "password": "password123",
        "name": "Test Brand",
        "role": "brand"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/signup", json=register_data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"Registration failed: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Registration request failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    token = get_token()
    if token:
        print(token)
    else:
        print("Failed to get token")
        sys.exit(1)
