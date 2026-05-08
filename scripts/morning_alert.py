#!/usr/bin/env python3
"""
TAO Morning Alert - 7:00 AM Daily
Sends a Telegram alert if TAO price is below $256.76 (entry price).
Also includes a quick portfolio summary.
"""

import json
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"
EXIT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "exit_strategy.json"

ENTRY_PRICE = 256.76  # Your price alert threshold


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_exit_strategy():
    with open(EXIT_CONFIG_PATH) as f:
        return json.load(f)


def get_tao_price():
    try:
        url = "https://api.kraken.com/0/public/Ticker?pair=TAOUSD"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return float(data["result"]["TAOUSD"]["c"][0])
    except Exception as e:
        print(f"Price fetch error: {e}")
        return None


def send_telegram(message, config):
    token = config["alerts"]["telegram_bot_token"]
    chat_id = config["alerts"]["telegram_chat_id"]
    if not token or not chat_id:
        print(f"[ALERT] {message}")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Telegram error: {e}")


def morning_check():
    config = load_config()
    exit_strategy = load_exit_strategy()
    now = datetime.now()

    price = get_tao_price()
    if price is None:
        send_telegram("⚠️ Morning Alert: Could not fetch TAO price. Check manually.", config)
        return

    principal = exit_strategy.get("principal_tao", 105)
    blended_apy = exit_strategy.get("blended_apy", 0.1862)
    portfolio_value = principal * price
    change = price - ENTRY_PRICE
    change_pct = (change / ENTRY_PRICE) * 100
    daily_reward_tao = principal * blended_apy / 365
    daily_reward_usd = daily_reward_tao * price

    # Determine level
    level = "SAFE"
    for lvl in exit_strategy["levels"]:
        if "above" in lvl and price > lvl["above"]:
            level = lvl["name"]
            break
        if "range" in lvl and lvl["range"][0] <= price <= lvl["range"][1]:
            level = lvl["name"]
            break
        if "below" in lvl and price < lvl["below"]:
            level = lvl["name"]
            break

    level_icons = {"SAFE": "🟢", "CAUTION": "🟡", "DEFENSIVE": "🟠", "EXIT": "🔴", "EMERGENCY": "⚫"}
    icon = level_icons.get(level, "⚪")

    if price < ENTRY_PRICE:
        # BELOW entry price - ALERT
        msg = (
            f"🔔 Good Morning - TAO BELOW ENTRY PRICE\n\n"
            f"📅 {now.strftime('%A, %d %B %Y')}\n"
            f"⏰ {now.strftime('%H:%M')}\n\n"
            f"💰 TAO Price: ${price:.2f}\n"
            f"📉 Entry Price: ${ENTRY_PRICE:.2f}\n"
            f"🔻 Down: ${abs(change):.2f} ({change_pct:.1f}%)\n\n"
            f"{icon} Exit Level: {level}\n"
            f"💼 Portfolio: ${portfolio_value:,.2f}\n"
            f"📊 Daily Reward: {daily_reward_tao:.4f} TAO (${daily_reward_usd:.2f})\n\n"
            f"⚠️ Price is below your ${ENTRY_PRICE} threshold."
        )
    else:
        # ABOVE entry price - all good
        msg = (
            f"☀️ Good Morning - TAO Status\n\n"
            f"📅 {now.strftime('%A, %d %B %Y')}\n"
            f"⏰ {now.strftime('%H:%M')}\n\n"
            f"💰 TAO Price: ${price:.2f}\n"
            f"📈 Entry Price: ${ENTRY_PRICE:.2f}\n"
            f"🔼 Up: +${change:.2f} (+{change_pct:.1f}%)\n\n"
            f"{icon} Exit Level: {level}\n"
            f"💼 Portfolio: ${portfolio_value:,.2f}\n"
            f"📊 Daily Reward: {daily_reward_tao:.4f} TAO (${daily_reward_usd:.2f})\n\n"
            f"✅ All good. Keep staking."
        )

    print(msg)
    send_telegram(msg, config)
    print(f"\n✅ Morning alert sent to Telegram.")


if __name__ == "__main__":
    morning_check()
