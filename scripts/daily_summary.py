#!/usr/bin/env python3
"""
TAO Investor - Daily Summary
Generates a daily P&L summary and sends it via Telegram at configured hour.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"
LOG_DIR = Path(__file__).parent.parent / "logs"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def send_telegram(message, config):
    """Send alert via Telegram if configured."""
    token = config["alerts"]["telegram_bot_token"]
    chat_id = config["alerts"]["telegram_chat_id"]

    if not token or not chat_id:
        print(f"[SUMMARY] {message}")
        return

    import urllib.request
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")


def get_yesterday_logs():
    """Load yesterday's monitoring logs."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"monitor_{yesterday}.json"

    if not log_file.exists():
        return None

    with open(log_file) as f:
        return json.load(f)


def generate_summary():
    """Generate daily P&L summary."""
    config = load_config()
    logs = get_yesterday_logs()

    if not logs:
        msg = (
            f"📋 *Daily TAO Summary*\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"No data from yesterday. Monitor may not have run."
        )
        print(msg)
        send_telegram(msg, config)
        return

    # Compare first and last readings of the day
    first = logs[0]
    last = logs[-1]

    tao_change = last["total_tao"] - first["total_tao"]
    change_symbol = "📈" if tao_change >= 0 else "📉"

    msg = (
        f"📋 *Daily TAO Summary*\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"💰 Total TAO: {last['total_tao']:.4f}\n"
        f"{change_symbol} Daily Change: {tao_change:+.4f} TAO\n"
        f"🔒 Staked: {last['total_staked']:.4f}\n"
        f"💳 Free: {last['free_balance']:.4f}\n"
        f"📊 Checks yesterday: {len(logs)}\n"
    )

    if config["cost_basis_gbp"] > 0:
        msg += f"\n💷 Cost Basis: £{config['cost_basis_gbp']:.2f}"

    print(msg)
    send_telegram(msg, config)


if __name__ == "__main__":
    generate_summary()
