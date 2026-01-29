import os
from dotenv import load_dotenv

load_dotenv()

# Platform Fees
PLATFORM_FEE_PERCENT = int(os.getenv("PLATFORM_FEE_PERCENT", 15))

# Escrow Settings
ESCROW_AUTO_RELEASE_DAYS = int(os.getenv("ESCROW_AUTO_RELEASE_DAYS", 14))

# Wallet Settings
MIN_WITHDRAWAL_AMOUNT_CENTS = int(os.getenv("MIN_WITHDRAWAL_AMOUNT_CENTS", 10000))  # KES 100
