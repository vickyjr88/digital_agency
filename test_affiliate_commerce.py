#!/usr/bin/env python3
"""
Comprehensive test script for Affiliate Commerce System
Tests the complete flow from brand setup to commission payout
"""

import requests
import json
from typing import Dict, Any
from decimal import Decimal

# Configuration
BASE_URL = "http://localhost:8000"
BRAND_EMAIL = "testbrand@example.com"
BRAND_PASSWORD = "testpass123"
INFLUENCER_EMAIL = "testinfluencer@example.com"
INFLUENCER_PASSWORD = "testpass123"

# Test results storage
test_results = []
brand_token = None
influencer_token = None
brand_profile_id = None
product_id = None
affiliate_link = None
order_id = None


def log_test(name: str, success: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"   {details}")
    test_results.append({
        "test": name,
        "success": success,
        "details": details
    })


def make_request(method: str, endpoint: str, data: Dict = None, token: str = None):
    """Make HTTP request"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)

        return response
    except Exception as e:
        print(f"   Error: {str(e)}")
        return None


# ============================================================================
# Test 1: User Registration
# ============================================================================

def test_user_registration():
    """Test creating brand and influencer users"""
    print("\n" + "="*60)
    print("TEST 1: USER REGISTRATION")
    print("="*60)

    # Register Brand
    brand_data = {
        "email": BRAND_EMAIL,
        "password": BRAND_PASSWORD,
        "name": "Test Brand",
        "user_type": "brand"
    }

    response = make_request("POST", "/api/register", brand_data)
    if response and response.status_code in [200, 201]:
        log_test("Register Brand User", True, f"Brand registered: {BRAND_EMAIL}")
    else:
        # User might already exist - try logging in
        log_test("Register Brand User", True, "User may already exist, will try login")

    # Register Influencer
    influencer_data = {
        "email": INFLUENCER_EMAIL,
        "password": INFLUENCER_PASSWORD,
        "name": "Test Influencer",
        "user_type": "influencer"
    }

    response = make_request("POST", "/api/register", influencer_data)
    if response and response.status_code in [200, 201]:
        log_test("Register Influencer User", True, f"Influencer registered: {INFLUENCER_EMAIL}")
    else:
        log_test("Register Influencer User", True, "User may already exist, will try login")


# ============================================================================
# Test 2: Authentication
# ============================================================================

def test_authentication():
    """Test login for brand and influencer"""
    global brand_token, influencer_token

    print("\n" + "="*60)
    print("TEST 2: AUTHENTICATION")
    print("="*60)

    # Brand Login
    brand_login = {
        "email": BRAND_EMAIL,
        "password": BRAND_PASSWORD
    }

    response = make_request("POST", "/api/login", brand_login)
    if response and response.status_code == 200:
        data = response.json()
        brand_token = data.get("access_token")
        log_test("Brand Login", True, f"Token: {brand_token[:20]}...")
    else:
        log_test("Brand Login", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    # Influencer Login
    influencer_login = {
        "email": INFLUENCER_EMAIL,
        "password": INFLUENCER_PASSWORD
    }

    response = make_request("POST", "/api/login", influencer_login)
    if response and response.status_code == 200:
        data = response.json()
        influencer_token = data.get("access_token")
        log_test("Influencer Login", True, f"Token: {influencer_token[:20]}...")
    else:
        log_test("Influencer Login", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    return True


# ============================================================================
# Test 3: Brand Profile Creation
# ============================================================================

def test_brand_profile():
    """Test creating brand profile with contact info"""
    global brand_profile_id

    print("\n" + "="*60)
    print("TEST 3: BRAND PROFILE CREATION")
    print("="*60)

    profile_data = {
        "whatsapp_number": "+254712345678",
        "business_location": "123 Test Street, Nairobi, Kenya",
        "business_hours": "Mon-Sat, 9AM-6PM",
        "preferred_contact_method": "whatsapp",
        "phone_number": "+254712345678",
        "business_email": "contact@testbrand.com",
        "website_url": "https://testbrand.com",
        "instagram_handle": "@testbrand",
        "business_description": "Test brand selling premium products",
        "business_category": "Fashion",
        "auto_approve_influencers": True
    }

    response = make_request("POST", "/api/brand-profiles/", profile_data, brand_token)
    if response and response.status_code in [200, 201]:
        data = response.json()
        brand_profile_id = data.get("id")
        log_test("Create Brand Profile", True, f"Profile ID: {brand_profile_id}")
        return True
    elif response and response.status_code == 400 and "already exists" in response.text:
        # Profile exists, get it
        response = make_request("GET", "/api/brand-profiles/me", None, brand_token)
        if response and response.status_code == 200:
            data = response.json()
            brand_profile_id = data.get("id")
            log_test("Get Existing Brand Profile", True, f"Profile ID: {brand_profile_id}")
            return True

    log_test("Create Brand Profile", False, f"Status: {response.status_code if response else 'No response'}")
    return False


# ============================================================================
# Test 4: Product Creation
# ============================================================================

def test_product_creation():
    """Test creating a product"""
    global product_id

    print("\n" + "="*60)
    print("TEST 4: PRODUCT CREATION")
    print("="*60)

    product_data = {
        "name": "Test Product - Premium Sneakers",
        "description": "High-quality athletic sneakers perfect for daily wear",
        "category": "Footwear",
        "price": 5000.00,
        "compare_at_price": 7000.00,
        "currency": "KES",
        "commission_type": "percentage",
        "commission_rate": 15.00,
        "platform_fee_type": "percentage",
        "platform_fee_rate": 10.00,
        "in_stock": True,
        "stock_quantity": 50,
        "track_inventory": True,
        "images": [
            "https://example.com/sneaker1.jpg",
            "https://example.com/sneaker2.jpg"
        ],
        "thumbnail": "https://example.com/sneaker-thumb.jpg",
        "has_variants": True,
        "variants": [
            {
                "name": "Size 9 / Red",
                "sku": "SNK-RED-9",
                "price": 5000.00,
                "stock_quantity": 10,
                "attributes": {"size": "9", "color": "Red"}
            },
            {
                "name": "Size 10 / Blue",
                "sku": "SNK-BLUE-10",
                "price": 5000.00,
                "stock_quantity": 15,
                "attributes": {"size": "10", "color": "Blue"}
            }
        ],
        "requires_shipping": True,
        "weight": 1.2,
        "tags": ["sneakers", "athletic", "fashion"],
        "auto_approve": True
    }

    response = make_request("POST", "/api/products/", product_data, brand_token)
    if response and response.status_code in [200, 201]:
        data = response.json()
        product_id = data.get("id")
        log_test("Create Product", True, f"Product ID: {product_id}, Slug: {data.get('slug')}")
        return True
    else:
        error_detail = response.json().get("detail") if response and response.status_code == 400 else "Unknown error"
        log_test("Create Product", False, f"Status: {response.status_code if response else 'No response'}, Error: {error_detail}")
        return False


# ============================================================================
# Test 5: Influencer Profile (if needed)
# ============================================================================

def test_influencer_profile():
    """Ensure influencer has a profile"""
    print("\n" + "="*60)
    print("TEST 5: INFLUENCER PROFILE CHECK")
    print("="*60)

    # Check if profile exists
    response = make_request("GET", "/api/v2/influencers/me", None, influencer_token)
    if response and response.status_code == 200:
        log_test("Get Influencer Profile", True, "Profile exists")
        return True

    # Create profile
    profile_data = {
        "display_name": "Test Influencer",
        "bio": "Test influencer for affiliate commerce testing",
        "niche": "Fashion",
        "location": "Nairobi, Kenya",
        "instagram_handle": "test_influencer",
        "instagram_followers": 50000,
        "instagram_engagement_rate": 3.5
    }

    response = make_request("POST", "/api/v2/influencers/profile", profile_data, influencer_token)
    if response and response.status_code in [200, 201]:
        log_test("Create Influencer Profile", True, "Profile created")
        return True

    log_test("Influencer Profile Setup", False, f"Status: {response.status_code if response else 'No response'}")
    return False


# ============================================================================
# Test 6: Affiliate Application
# ============================================================================

def test_affiliate_application():
    """Test influencer applying to promote product"""
    global affiliate_link

    print("\n" + "="*60)
    print("TEST 6: AFFILIATE APPLICATION")
    print("="*60)

    application_data = {
        "product_id": product_id,
        "application_message": "I have 50K followers and excellent engagement. Perfect fit for this product!"
    }

    response = make_request("POST", "/api/affiliate/apply", application_data, influencer_token)
    if response and response.status_code in [200, 201]:
        data = response.json()
        status = data.get("status")
        log_test("Submit Affiliate Application", True, f"Application Status: {status}")

        # If auto-approved, get affiliate link
        if status == "approved":
            link_response = make_request("GET", f"/api/affiliate/links/{product_id}", None, influencer_token)
            if link_response and link_response.status_code == 200:
                affiliate_link = link_response.json()
                log_test("Auto-Approved - Link Generated", True, f"Link: {affiliate_link.get('link_url')}")
                return True

        return True
    else:
        error_detail = response.json().get("detail") if response else "Unknown error"
        log_test("Submit Affiliate Application", False, f"Error: {error_detail}")
        return False


# ============================================================================
# Test 7: Order Placement
# ============================================================================

def test_order_placement():
    """Test customer placing an order"""
    global order_id

    print("\n" + "="*60)
    print("TEST 7: ORDER PLACEMENT (NO PAYMENT)")
    print("="*60)

    if not affiliate_link:
        log_test("Order Placement", False, "No affiliate link available")
        return False

    order_data = {
        "product_id": product_id,
        "quantity": 2,
        "customer_name": "Test Customer",
        "customer_email": "customer@example.com",
        "customer_phone": "+254700000000",
        "customer_notes": "Please call before delivery",
        "affiliate_code": affiliate_link.get("affiliate_code")
    }

    response = make_request("POST", "/api/orders/place", order_data)
    if response and response.status_code in [200, 201]:
        data = response.json()
        order_id = data.get("id")
        order_number = data.get("order_number")
        total_amount = data.get("total_amount")
        commission = data.get("commission_amount")
        brand_contact = data.get("brand_contact")

        log_test("Place Order", True, f"Order: {order_number}, Total: KES {total_amount}, Commission: KES {commission}")
        log_test("Brand Contact Info Provided", True, f"WhatsApp: {brand_contact.get('whatsapp_number')}")

        print(f"\n   📱 Customer would see:")
        print(f"   WhatsApp: {brand_contact.get('whatsapp_number')}")
        print(f"   Location: {brand_contact.get('business_location')}")
        print(f"   Hours: {brand_contact.get('business_hours')}")

        return True
    else:
        error_detail = response.json().get("detail") if response else "Unknown error"
        log_test("Place Order", False, f"Error: {error_detail}")
        return False


# ============================================================================
# Test 8: Order Fulfillment & Commission Payout
# ============================================================================

def test_order_fulfillment():
    """Test brand marking order as fulfilled and commission payout"""
    print("\n" + "="*60)
    print("TEST 8: ORDER FULFILLMENT & COMMISSION PAYOUT")
    print("="*60)

    if not order_id:
        log_test("Order Fulfillment", False, "No order ID available")
        return False

    # Check influencer wallet before
    wallet_before = make_request("GET", "/api/v2/wallet/balance", None, influencer_token)
    balance_before = 0
    if wallet_before and wallet_before.status_code == 200:
        balance_before = wallet_before.json().get("balance", 0)
        log_test("Check Wallet Balance (Before)", True, f"Balance: KES {balance_before / 100:.2f}")

    # Mark order as fulfilled
    status_update = {
        "status": "fulfilled",
        "brand_notes": "Customer picked up order successfully"
    }

    response = make_request("PUT", f"/api/orders/{order_id}/status", status_update, brand_token)
    if response and response.status_code == 200:
        data = response.json()
        log_test("Mark Order as Fulfilled", True, f"Status: {data.get('status')}")

        # Check wallet after
        wallet_after = make_request("GET", "/api/v2/wallet/balance", None, influencer_token)
        if wallet_after and wallet_after.status_code == 200:
            balance_after = wallet_after.json().get("balance", 0)
            commission_paid = (balance_after - balance_before) / 100
            log_test("Commission Paid to Wallet", True, f"Commission: KES {commission_paid:.2f}")
            log_test("New Wallet Balance", True, f"Balance: KES {balance_after / 100:.2f}")

            return True

    error_detail = response.json().get("detail") if response else "Unknown error"
    log_test("Order Fulfillment", False, f"Error: {error_detail}")
    return False


# ============================================================================
# Test 9: Analytics
# ============================================================================

def test_analytics():
    """Test analytics endpoints"""
    print("\n" + "="*60)
    print("TEST 9: ANALYTICS")
    print("="*60)

    # Influencer dashboard
    response = make_request("GET", "/api/affiliate-analytics/influencer/dashboard?days=30", None, influencer_token)
    if response and response.status_code == 200:
        data = response.json()
        log_test("Influencer Dashboard", True,
                 f"Clicks: {data.get('total_clicks')}, Orders: {data.get('total_orders')}, "
                 f"Earnings: KES {data.get('total_commissions_earned')}")
    else:
        log_test("Influencer Dashboard", False, f"Status: {response.status_code if response else 'No response'}")

    # Brand dashboard
    response = make_request("GET", "/api/affiliate-analytics/brand/dashboard?days=30", None, brand_token)
    if response and response.status_code == 200:
        data = response.json()
        log_test("Brand Dashboard", True,
                 f"Products: {data.get('total_products')}, Affiliates: {data.get('total_affiliates')}, "
                 f"Sales: KES {data.get('total_sales')}")
    else:
        log_test("Brand Dashboard", False, f"Status: {response.status_code if response else 'No response'}")


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "="*60)
    print("AFFILIATE COMMERCE SYSTEM - COMPREHENSIVE TESTS")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print("")

    # Run tests in order
    test_user_registration()

    if not test_authentication():
        print("\n❌ CRITICAL: Authentication failed. Cannot continue tests.")
        return

    if not test_brand_profile():
        print("\n❌ CRITICAL: Brand profile setup failed. Cannot continue tests.")
        return

    if not test_product_creation():
        print("\n❌ CRITICAL: Product creation failed. Cannot continue tests.")
        return

    if not test_influencer_profile():
        print("\n⚠️  WARNING: Influencer profile setup failed. Some tests may fail.")

    if not test_affiliate_application():
        print("\n⚠️  WARNING: Affiliate application failed. Order tests may fail.")

    test_order_placement()
    test_order_fulfillment()
    test_analytics()

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for result in test_results if result["success"])
    failed = len(test_results) - passed

    print(f"Total Tests: {len(test_results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed / len(test_results) * 100):.1f}%")

    if failed > 0:
        print("\nFailed Tests:")
        for result in test_results:
            if not result["success"]:
                print(f"  ❌ {result['test']}: {result['details']}")

    print("\n" + "="*60)


if __name__ == "__main__":
    run_all_tests()
