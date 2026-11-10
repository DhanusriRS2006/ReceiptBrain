"""Category list + a deterministic merchant lookup (fast, free, no LLM needed)."""

CATEGORIES = ["Food", "Travel", "Shopping", "Utilities", "Entertainment",
              "Healthcare", "Subscriptions", "Other"]

MERCHANT_MAP = {
    "swiggy": "Food", "zomato": "Food", "blinkit": "Food", "bigbasket": "Food",
    "zepto": "Food", "dunzo": "Food", "dominos": "Food", "mcdonald": "Food",
    "amazon prime": "Subscriptions", "netflix": "Subscriptions", "spotify": "Subscriptions",
    "hotstar": "Subscriptions", "youtube": "Subscriptions",
    "amazon": "Shopping", "flipkart": "Shopping", "myntra": "Shopping",
    "nykaa": "Shopping", "meesho": "Shopping", "ajio": "Shopping",
    "airtel": "Utilities", "jio": "Utilities", "bescom": "Utilities", "tneb": "Utilities",
    "bsnl": "Utilities", "tangedco": "Utilities",
    "uber": "Travel", "ola": "Travel", "rapido": "Travel", "makemytrip": "Travel",
    "irctc": "Travel", "redbus": "Travel", "indigo": "Travel", "goibibo": "Travel",
    "bookmyshow": "Entertainment", "pvr": "Entertainment", "inox": "Entertainment",
    "apollo": "Healthcare", "practo": "Healthcare", "1mg": "Healthcare", "medplus": "Healthcare",
}


def normalize_category(merchant: str, hint: str = "") -> str:
    """Merchant lookup first (most reliable), then the model's hint, else 'Other'."""
    m = (merchant or "").lower()
    for key, cat in MERCHANT_MAP.items():   # 'amazon prime' is listed before 'amazon'
        if key in m:
            return cat
    for cat in CATEGORIES:
        if (hint or "").strip().lower() == cat.lower():
            return cat
    return "Other"
