#!/usr/bin/env python3
"""
TAO 3-Hour Summary Alert
Sends a combined price + portfolio snapshot to Telegram every 3 hours.
"""

import json
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import bittensor as bt

CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"
EXIT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "exit_strategy.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_exit_strategy():
    with open(EXIT_CONFIG_PATH) as f:
        return json.load(f)


def get_tao_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bittensor&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data["bittensor"]["usd"]
    except Exception as e:
        print(f"Price fetch error: {e}")
        return None


def get_balance(config):
    try:
        wallet = bt.wallet(name=config["wallet_name"], hotkey=config["hotkey"])
        subtensor = bt.subtensor(network="finney")
        balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
        free = float(balance) if balance else 0
    except Exception as e:
        print(f"Balance fetch error: {e}")
        free = 0

    try:
        stake = subtensor.get_stake_for_coldkey_and_hotkey(
            wallet.coldkeypub.ss58_address, wallet.hotkey.ss58_address
        )
        staked = float(stake) if stake else 0
    except Exception:
        staked = 0

    return free, staked


def get_exit_level(price, exit_strategy):
    for lvl in exit_strategy["levels"]:
        if "above" in lvl and price > lvl["above"]:
            return lvl["name"]
        if "range" in lvl and lvl["range"][0] <= price <= lvl["range"][1]:
            return lvl["name"]
        if "below" in lvl and price < lvl["below"]:
            return lvl["name"]
    return "SAFE"


def send_telegram(message, config):
    token = config["alerts"]["telegram_bot_token"]
    chat_id = config["alerts"]["telegram_chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
        print("✅ Alert sent to Telegram.")
    except Exception as e:
        print(f"Telegram error: {e}")


def run():
    config = load_config()
    exit_strategy = load_exit_strategy()
    now = datetime.now()

    price = get_tao_price()
    free_balance, total_staked = get_balance(config)
    total_tao = free_balance + total_staked

    entry_price = exit_strategy.get("current_price_at_creation", 256.88)
    principal = exit_strategy.get("principal_tao", 105)
    blended_apy = exit_strategy.get("blended_apy", 0.1862)

    level_icons = {"SAFE": "🟢", "CAUTION": "🟡", "DEFENSIVE": "🟠", "EXIT": "🔴", "EMERGENCY": "⚫"}

    if price:
        change = price - entry_price
        change_pct = (change / entry_price) * 100
        direction = "📈" if change >= 0 else "📉"
        sign = "+" if change >= 0 else ""
        portfolio_value = principal * price
        daily_reward_tao = principal * blended_apy / 365
        daily_reward_usd = daily_reward_tao * price
        level = get_exit_level(price, exit_strategy)
        icon = level_icons.get(level, "⚪")

        msg = (
            f"📊 *TAO Summary — {now.strftime('%H:%M')}*\n"
            f"📅 {now.strftime('%d %b %Y')}\n\n"
            f"💵 *Price:* ${price:.2f}\n"
            f"{direction} vs Entry: {sign}${change:.2f} ({sign}{change_pct:.1f}%)\n\n"
            f"💰 Free Balance: {free_balance:.4f} TAO\n"
            f"🔒 Total Staked: {total_staked:.4f} TAO\n"
            f"📈 Total TAO: {total_tao:.4f}\n\n"
            f"💼 Portfolio Value: ${portfolio_value:,.2f}\n"
            f"📊 Est. Daily Reward: {daily_reward_tao:.4f} TAO (${daily_reward_usd:.2f})\n\n"
            f"{icon} Exit Level: *{level}*"
        )
    else:
        msg = (
            f"📊 *TAO Summary — {now.strftime('%H:%M')}*\n"
            f"📅 {now.strftime('%d %b %Y')}\n\n"
            f"⚠️ Price unavailable\n\n"
            f"💰 Free Balance: {free_balance:.4f} TAO\n"
            f"🔒 Total Staked: {total_staked:.4f} TAO\n"
            f"📈 Total TAO: {total_tao:.4f}"
        )

    print(msg)
    send_telegram(msg, config)


if __name__ == "__main__":
    run()
