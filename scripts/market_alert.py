#!/usr/bin/env python3
"""
Multi-Asset Market Alert
Sends a Telegram price snapshot for BTC, ALGO, XRP, SUI, SEI, DOGE every 3 hours.
Prices sourced from Kraken public API — no key required.
"""

import json
import urllib.request
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"

ASSETS = [
    ("TAO",  "TAOUSD",  "TAOUSD",   "τ"),
    ("BTC",  "XBTUSD",  "XXBTZUSD", "₿"),
    ("XRP",  "XRPUSD",  "XXRPZUSD", "✦"),
    ("DOGE", "XDGUSD",  "XDGUSD",   "🐕"),
    ("ALGO", "ALGOUSD", "ALGOUSD",  "◎"),
    ("SUI",  "SUIUSD",  "SUIUSD",   "💧"),
    ("SEI",  "SEIUSD",  "SEIUSD",   "⚡"),
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_prices():
    pairs = ",".join(p for _, p, _, _ in ASSETS)
    url = f"https://api.kraken.com/0/public/Ticker?pair={pairs}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    if data.get("error"):
        raise Exception(f"Kraken error: {data['error']}")
    return data["result"]


def send_telegram(message, config):
    token = config["alerts"]["telegram_bot_token"]
    chat_id = config["alerts"]["telegram_chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
        print("✅ Market alert sent.")
    except Exception as e:
        print(f"Telegram error: {e}")


def format_price(symbol, price):
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"


def run():
    config = load_config()
    now = datetime.now()

    try:
        result = get_prices()
    except Exception as e:
        print(f"Price fetch error: {e}")
        send_telegram(f"⚠️ Market Alert: Could not fetch prices from Kraken.\n`{e}`", config)
        return

    lines = [
        f"📊 *Market Prices — {now.strftime('%H:%M')}*",
        f"📅 {now.strftime('%d %b %Y')}",
        ""
    ]

    for symbol, pair, result_key, icon in ASSETS:
        try:
            price = float(result[result_key]["c"][0])
            high = float(result[result_key]["h"][1])
            low = float(result[result_key]["l"][1])
            lines.append(
                f"{icon} *{symbol}*: {format_price(symbol, price)}"
                f"  _(H: {format_price(symbol, high)} / L: {format_price(symbol, low)})_"
            )
        except KeyError:
            lines.append(f"• *{symbol}*: unavailable")

    message = "\n".join(lines)
    print(message)
    send_telegram(message, config)


if __name__ == "__main__":
    run()
