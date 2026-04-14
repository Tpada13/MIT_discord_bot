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

# ---------------------------------------------------------------------------
# Claude Analyst — prompt constants
# All strings live here so they can be tuned without touching service code.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a senior cryptocurrency financial analyst with 15+ years of experience \
in digital asset markets.

INTERPRETATION GUIDELINES:
- RSI <30: oversold — watch for reversal up
- RSI >70: overbought — watch for reversal down
- RSI 30-70: neutral momentum
- Price above SMA20 and SMA50: bullish trend structure
- Price below SMA20 and SMA50: bearish trend structure
- EMA12 > EMA26 (positive MACD): bullish momentum
- EMA12 < EMA26 (negative MACD): bearish momentum
- Rising volume confirms trend; declining volume = weakening conviction
- When signals conflict: acknowledge it, weigh recency and magnitude, don't force conviction

MARKET CONTEXT:
- Crypto trades 24/7 with higher volatility than equities
- Macro events (Fed rates, regulation) can override technicals instantly
- Adjust confidence when indicators show N/A (insufficient data)

RULES:
- Base analysis strictly on the data provided — never fabricate price history
- Always give specific price target ranges, not vague language
- Flag insufficient data explicitly and lower confidence accordingly\
"""

DERIVED_SIGNALS_TEMPLATE = """\

DERIVED SIGNALS:
- Price vs SMA20: {price_vs_sma20}
- Price vs SMA50: {price_vs_sma50}
- MACD Proxy (EMA12 - EMA26): {macd_value} - {macd_signal}
- Trend Structure: {trend_structure}\
"""

FORECAST_TEMPLATE = """\
ASSET: {ticker} - {coin_description}

MARKET DATA:
- Current Price: ${current_price:,.4f}
- Price Change ({timeframe}): {price_change_pct:+.2f}%
- Market Cap: ${market_cap:,.0f}
- 24h Volume: ${volume_24h:,.0f}

TECHNICAL INDICATORS ({timeframe} data):
- RSI (14): {rsi}
- SMA 20: {sma20}
- SMA 50: {sma50}
- EMA 12: {ema12}
- EMA 26: {ema26}
- Volume Trend: {volume_trend}
{derived_signals}

Analyze {ticker} based on the above {timeframe} data and provide a comprehensive forecast.
Respond using EXACTLY this format:

**{ticker} -- Senior Analyst Forecast** *(based on {timeframe} data)*

**Summary**
[2-3 sentence market overview]

**Key Signals**
- [Signal 1]
- [Signal 2]
- [Signal 3]

**Risk Factors**
- [Risk 1]
- [Risk 2]

**Price Target**
Short-term (7-14d): $X,XXX - $X,XXX

**Recommendation**
[HOLD/BUY/SELL] -- [one-line rationale]

**Analyst Commentary**
[2-3 sentence narrative conclusion in plain English]\
"""

DISCLAIMER = "\n\n---\n⚠️ *This is not financial advice. Crypto markets are highly volatile.*"

COIN_DESCRIPTIONS = {
    "BTC":  "Bitcoin - decentralized digital currency, largest by market cap, primary store of value",
    "ETH":  "Ethereum - smart contract platform, backbone of DeFi and NFT ecosystems",
    "SOL":  "Solana - high-throughput L1 blockchain, strong NFT and DeFi ecosystem",
    "BNB":  "BNB - Binance exchange token, powers BNB Chain ecosystem",
    "XRP":  "XRP - payments-focused cryptocurrency, used for cross-border settlement",
    "ADA":  "Cardano - proof-of-stake L1 blockchain with academic research focus",
    "DOGE": "Dogecoin - meme-origin cryptocurrency with large retail following",
    "AVAX": "Avalanche - fast L1 blockchain with subnet architecture for custom chains",
    "XDC":  "XDC Network - enterprise-grade blockchain for trade finance",
    "LINK": "Chainlink - decentralized oracle network connecting smart contracts to real-world data",
    "SUI":  "Sui - high-performance L1 blockchain with object-based data model",
    "ZRO":  "LayerZero - cross-chain interoperability protocol",
    "ONDO": "Ondo Finance - real-world asset (RWA) tokenization protocol",
    "CRV":  "Curve Finance - decentralized stablecoin exchange, dominant in DeFi liquidity",
    "SEI":  "Sei - L1 blockchain optimized for trading and order-book DEXs",
}
