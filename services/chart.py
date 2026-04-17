import io

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend — must be set before importing pyplot
import matplotlib.pyplot as plt


def generate_price_chart(
    ticker: str,
    close_prices: list[float],
    volumes: list[float],
    timeframe: str,
) -> bytes:
    """
    Renders a two-panel dark-themed chart and returns PNG bytes.

    Top panel: price line + SMA20 overlay (omitted if < 20 data points).
    Bottom panel: volume bars (green if price >= prior close, red otherwise).

    Does not write to disk. Creates and closes its own figure.
    """
    plt.style.use('dark_background')
    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1,
        gridspec_kw={'height_ratios': [3, 1]},
        figsize=(10, 6),
        sharex=False,
    )

    x = list(range(len(close_prices)))

    # --- Top panel: price line ---
    ax_price.plot(x, close_prices, color='#00bfff', linewidth=1.5, label='Price')

    # SMA20 overlay — only if enough data
    if len(close_prices) >= 20:
        sma20 = [
            sum(close_prices[i - 20:i]) / 20
            for i in range(20, len(close_prices) + 1)
        ]
        ax_price.plot(
            range(19, len(close_prices)),
            sma20,
            color='#ffa500',
            linewidth=1.0,
            linestyle='--',
            label='SMA20',
        )
        ax_price.legend(loc='upper left', fontsize=8)

    ax_price.set_title(f"{ticker} — {timeframe}", fontsize=12)
    ax_price.set_ylabel('Price (USD)', fontsize=9)
    ax_price.tick_params(labelbottom=False)

    # --- Bottom panel: volume bars ---
    bar_colors = ['#26a69a']  # first bar defaults to green
    for i in range(1, len(close_prices)):
        if close_prices[i] >= close_prices[i - 1]:
            bar_colors.append('#26a69a')  # green
        else:
            bar_colors.append('#ef5350')  # red

    ax_vol.bar(x, volumes, color=bar_colors, width=1.0)
    ax_vol.set_ylabel('Volume', fontsize=9)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
