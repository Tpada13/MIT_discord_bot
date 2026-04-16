from cogs.crypto import _format_market_block


def test_market_sort_order():
    """Rows must be sorted by price_change_pct descending; failed coins appear last."""
    rows = [
        {"ticker": "ETH", "current_price": 3000.0, "price_change_pct": 1.5},
        {"ticker": "BTC", "current_price": 80000.0, "price_change_pct": 3.2},
        {"ticker": "SOL", "current_price": 150.0, "price_change_pct": -2.1},
        {"ticker": "ADA", "current_price": 0.45, "price_change_pct": 5.7},
        {"ticker": "BNB", "current_price": 600.0, "price_change_pct": 0.8},
    ]
    failed = ["XRP"]

    result = _format_market_block(rows, failed)

    # Expected order: ADA (5.7) > BTC (3.2) > ETH (1.5) > BNB (0.8) > SOL (-2.1) > XRP (unavailable)
    ada_pos = result.index("ADA")
    btc_pos = result.index("BTC")
    eth_pos = result.index("ETH")
    bnb_pos = result.index("BNB")
    sol_pos = result.index("SOL")
    xrp_pos = result.index("XRP")

    assert ada_pos < btc_pos < eth_pos < bnb_pos < sol_pos < xrp_pos
    assert "(unavailable)" in result


def test_market_formatting():
    """Output with 15 coins must be a string within Discord's 1024-char field limit."""
    from config import SUPPORTED_COINS

    rows = [
        {
            "ticker": ticker,
            "current_price": 100.0 * (i + 1),
            "price_change_pct": float(i - 7),
        }
        for i, ticker in enumerate(SUPPORTED_COINS.keys())
    ]
    failed = []

    result = _format_market_block(rows, failed)

    assert isinstance(result, str)
    assert len(result) <= 1024
    for ticker in SUPPORTED_COINS.keys():
        assert ticker in result
