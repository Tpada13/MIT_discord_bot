# Mapping from ticker symbol to CoinGecko coin ID
SUPPORTED_COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "XDC": "xdce-crowd-sale",
    "LINK": "chainlink",
    "SUI": "sui",
    "ZRO": "layerzero",
    "ONDO": "ondo-finance",
    "CRV": "curve-dao-token",
    "SEI": "sei-network",
}

# Valid timeframes for /price command
PRICE_TIMEFRAMES = ["1h", "24h", "3d", "7d"]
DEFAULT_PRICE_TIMEFRAME = "24h"

# Valid timeframes for /analyze and /forecast commands
ANALYSIS_TIMEFRAMES = ["7d", "30d", "90d", "180d"]
DEFAULT_ANALYSIS_TIMEFRAME = "30d"

# Maps timeframe string to number of days for CoinGecko API
TIMEFRAME_TO_DAYS = {
    "1h": 1,
    "24h": 1,
    "3d": 3,
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
}
