# Paystack Payment Service for Kenya
import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PaystackConfig:
    """Paystack configuration for Kenya"""
    BASE_URL = "https://api.paystack.co"
    SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
    PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
    CURRENCY = "KES"  # Kenyan Shillings
    
    # Subscription Plans - KES pricing for Kenya market
    PLANS = {
        "day_pass": {
            "name": "Day Pass",
            "amount": 2900,  # KES 29
            "interval": "daily",
            "brands": 1,
            "content_limit": 5,
            "features": [
                "24-hour access",
                "1 brand profile",
                "5 content pieces",
                "Full trend access",
                "No commitment"
            ]
        },
        "free": {
            "name": "Free",
            "amount": 0,
            "interval": "monthly",
            "brands": 1,
            "content_limit": 10,
            "features": [
                "1 brand profile",
                "10 content pieces/month",
                "Manual trend selection",
                "7-day history",
                "Email support"
            ]
        },
        "starter": {
            "name": "Starter",
            "amount": 99900,  # KES 2,999 in kobo
            "interval": "monthly",
            "brands": 3,
            "content_limit": 100,
            "features": [
                "3 brand profiles",
                "100 content pieces/month",
                "Daily AI trends",
                "30-day history",
                "No watermark",
                "Priority email support"
            ]
        },
        "professional": {
            "name": "Professional",
            "amount": 299900,  # KES 7,999 in kobo
            "interval": "monthly",
            "brands": 10,
            "content_limit": 500,
            "popular": True,
            "features": [
                "10 brand profiles",
                "500 content pieces/month",
                "3x daily trends",
                "Team collaboration (3 users)",
                "API access",
                "Advanced analytics",
                "Phone & email support"
            ]
        },
        "agency": {
            "name": "Agency",
            "amount": 999900,  # KES 19,999 in kobo
            "interval": "monthly",
            "brands": -1,  # Unlimited
            "content_limit": 2000,
            "features": [
                "Unlimited brands",
                "2,000 content pieces/month",
                "Hourly trend updates",
                "Unlimited team members",
                "White-label option",
                "Dedicated account manager",
                "Custom integrations"
            ]
        }
    }


class PaystackService:
    """Service for handling Paystack payments in Kenya"""
    
    def __init__(self):
        self.base_url = PaystackConfig.BASE_URL
        self.secret_key = PaystackConfig.SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a request to Paystack API"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API error: {e}")
            raise Exception(f"Payment service error: {str(e)}")
    
    def initialize_transaction(
        self,
        email: str,
        amount: int,
        callback_url: str,
        plan_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize a Paystack transaction
        
        Args:
            email: Customer's email
            amount: Amount in kobo (cents)
            callback_url: URL to redirect after payment
            plan_id: Subscription plan ID (optional)
            user_id: Internal user ID (optional)
            metadata: Additional transaction metadata
        
        Returns:
            Transaction initialization response with authorization_url
        """
        # Build metadata
        payload_metadata = {}
        if user_id:
            payload_metadata["user_id"] = user_id
        if plan_id:
            payload_metadata["plan_id"] = plan_id
            payload_metadata["custom_fields"] = [
                {
                    "display_name": "Plan",
                    "variable_name": "plan",
                    "value": plan_id
                }
            ]
        
        # Add additional metadata
        if metadata:
            payload_metadata.update(metadata)

        data = {
            "email": email,
            "amount": amount,
            "currency": PaystackConfig.CURRENCY,
            "callback_url": callback_url,
            "metadata": payload_metadata
        }
        
        return self._make_request("POST", "/transaction/initialize", data)
    
    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a Paystack transaction
        
        Args:
            reference: Transaction reference
        
        Returns:
            Transaction verification response
        """
        return self._make_request("GET", f"/transaction/verify/{reference}")
    
    def create_subscription_plan(
        self,
        name: str,
        amount: int,
        interval: str = "monthly",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a subscription plan on Paystack
        
        Args:
            name: Plan name
            amount: Amount in kobo
            interval: Billing interval (hourly, daily, weekly, monthly, annually)
            description: Plan description
        
        Returns:
            Created plan details
        """
        data = {
            "name": name,
            "amount": amount,
            "interval": interval,
            "description": description,
            "currency": PaystackConfig.CURRENCY
        }
        
        return self._make_request("POST", "/plan", data)
    
    def create_subscription(
        self,
        customer_email: str,
        plan_code: str,
        authorization_code: str,
        start_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription for a customer
        
        Args:
            customer_email: Customer's email
            plan_code: Paystack plan code
            authorization_code: Customer's saved card authorization
            start_date: Optional start date for the subscription
        
        Returns:
            Subscription details
        """
        data = {
            "customer": customer_email,
            "plan": plan_code,
            "authorization": authorization_code
        }
        
        if start_date:
            data["start_date"] = start_date
        
        return self._make_request("POST", "/subscription", data)
    
    def disable_subscription(self, subscription_code: str, token: str) -> Dict[str, Any]:
        """
        Disable/cancel a subscription
        
        Args:
            subscription_code: Subscription code
            token: Email token for the subscription
        
        Returns:
            Cancellation response
        """
        data = {
            "code": subscription_code,
            "token": token
        }
        
        return self._make_request("POST", "/subscription/disable", data)
    
    def enable_subscription(self, subscription_code: str, token: str) -> Dict[str, Any]:
        """
        Enable a subscription
        
        Args:
            subscription_code: Subscription code
            token: Email token for the subscription
        
        Returns:
            Enable response
        """
        data = {
            "code": subscription_code,
            "token": token
        }
        
        return self._make_request("POST", "/subscription/enable", data)
    
    def get_subscription(self, subscription_id_or_code: str) -> Dict[str, Any]:
        """
        Fetch a subscription by ID or code
        
        Args:
            subscription_id_or_code: Subscription ID or code
        
        Returns:
            Subscription details
        """
        return self._make_request("GET", f"/subscription/{subscription_id_or_code}")
    
    def list_plans(self) -> Dict[str, Any]:
        """
        List all subscription plans
        
        Returns:
            List of plans
        """
        return self._make_request("GET", "/plan")
    
    def create_customer(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a customer on Paystack
        
        Args:
            email: Customer's email
            first_name: Customer's first name
            last_name: Customer's last name
            phone: Customer's phone number
        
        Returns:
            Customer details
        """
        data = {"email": email}
        
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if phone:
            data["phone"] = phone
        
        return self._make_request("POST", "/customer", data)
    
    def get_customer(self, email_or_code: str) -> Dict[str, Any]:
        """
        Fetch a customer by email or customer code
        
        Args:
            email_or_code: Customer email or code
        
        Returns:
            Customer details
        """
        return self._make_request("GET", f"/customer/{email_or_code}")
    
    def charge_authorization(
        self,
        email: str,
        amount: int,
        authorization_code: str,
        reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Charge a saved card authorization
        
        Args:
            email: Customer's email
            amount: Amount in kobo
            authorization_code: Saved card authorization code
            reference: Optional unique reference
        
        Returns:
            Charge response
        """
        data = {
            "email": email,
            "amount": amount,
            "authorization_code": authorization_code,
            "currency": PaystackConfig.CURRENCY
        }
        
        if reference:
            data["reference"] = reference
        
        return self._make_request("POST", "/transaction/charge_authorization", data)
    
    @staticmethod
    def get_plan_details(plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plan details from config
        
        Args:
            plan_id: Plan identifier (free, starter, professional, agency)
        
        Returns:
            Plan details or None if not found
        """
        return PaystackConfig.PLANS.get(plan_id)
    
    @staticmethod
    def get_all_plans() -> Dict[str, Dict[str, Any]]:
        """
        Get all available plans
        
        Returns:
            Dictionary of all plans
        """
        return PaystackConfig.PLANS
    
    @staticmethod
    def format_amount(amount_in_kobo: int) -> str:
        """
        Format amount from kobo to KES display string
        
        Args:
            amount_in_kobo: Amount in kobo (cents)
        
        Returns:
            Formatted string like "KES 2,999"
        """
        amount_in_kes = amount_in_kobo / 100
        return f"KES {amount_in_kes:,.0f}"


# Webhook handler for Paystack events
class PaystackWebhookHandler:
    """Handle Paystack webhook events"""
    
    SUPPORTED_EVENTS = [
        "charge.success",
        "subscription.create",
        "subscription.disable",
        "subscription.enable",
        "invoice.create",
        "invoice.payment_failed",
        "invoice.update"
    ]
    
    @staticmethod
    def verify_webhook(payload: bytes, signature: str, secret_key: str) -> bool:
        """
        Verify webhook signature
        
        Args:
            payload: Raw request body
            signature: X-Paystack-Signature header value
            secret_key: Paystack secret key
        
        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib
        
        computed_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)
    
    @staticmethod
    def handle_charge_success(data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful charge webhook"""
        return {
            "event": "charge.success",
            "reference": data.get("reference"),
            "amount": data.get("amount"),
            "customer_email": data.get("customer", {}).get("email"),
            "metadata": data.get("metadata", {}),
            "paid_at": data.get("paid_at"),
            "authorization_code": data.get("authorization", {}).get("authorization_code")
        }
    
    @staticmethod
    def handle_subscription_create(data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription created webhook"""
        return {
            "event": "subscription.create",
            "subscription_code": data.get("subscription_code"),
            "customer_email": data.get("customer", {}).get("email"),
            "plan_code": data.get("plan", {}).get("plan_code"),
            "status": data.get("status"),
            "next_payment_date": data.get("next_payment_date")
        }
    
    @staticmethod
    def handle_subscription_disable(data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription disabled webhook"""
        return {
            "event": "subscription.disable",
            "subscription_code": data.get("subscription_code"),
            "customer_email": data.get("customer", {}).get("email"),
            "status": "cancelled"
        }
