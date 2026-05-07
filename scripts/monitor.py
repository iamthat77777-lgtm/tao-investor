#!/usr/bin/env python3
"""
TAO Investor Monitor
Checks all staking positions every hour and logs performance.
Sends alerts via Telegram (if configured) or prints to console.
"""

import json
import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import bittensor as bt

# Paths
CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def send_telegram(message, config):
    """Send alert via Telegram if configured."""
    token = config["alerts"]["telegram_bot_token"]
    chat_id = config["alerts"]["telegram_chat_id"]

    if not token or not chat_id:
        print(f"[ALERT] {message}")
        return

    import urllib.request
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")


async def get_balance(wallet):
    """Get current TAO balance."""
    subtensor = bt.subtensor(network="finney")
    balance = await subtensor.get_balance(wallet.coldkeypub.ss58_address)
    return float(balance)


async def get_stake_info(wallet):
    """Get staking info for all subnets."""
    subtensor = bt.subtensor(network="finney")
    stakes = []

    try:
        # Get total stake
        total_stake = await subtensor.get_total_stake_for_coldkey(wallet.coldkeypub.ss58_address)
        stakes.append({"type": "total_stake", "amount": float(total_stake)})
    except Exception as e:
        stakes.append({"type": "total_stake", "amount": 0, "error": str(e)})

    return stakes


def check_positions(config):
    """Check all positions and return status report."""
    wallet = bt.wallet(name=config["wallet_name"], hotkey=config["hotkey"])

    report = {
        "timestamp": datetime.now().isoformat(),
        "wallet": config["coldkey_address"],
        "positions": [],
        "total_tao": 0,
        "alerts": []
    }

    try:
        # Try to get balance (sync wrapper)
        subtensor = bt.subtensor(network="finney")
        balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
        report["free_balance"] = float(balance) if balance else 0
    except Exception as e:
        report["free_balance"] = 0
        report["balance_error"] = str(e)

    try:
        # Get total stake
        total_stake = subtensor.get_total_stake_for_coldkey(wallet.coldkeypub.ss58_address)
        report["total_staked"] = float(total_stake) if total_stake else 0
    except Exception as e:
        report["total_staked"] = 0
        report["stake_error"] = str(e)

    report["total_tao"] = report["free_balance"] + report["total_staked"]

    # Check for alerts
    if config["cost_basis_gbp"] > 0 and report["total_tao"] > 0:
        # Profit tracking would go here with price API
        pass

    return report


def log_report(report):
    """Save report to daily log file."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"monitor_{date_str}.json"

    # Append to daily log
    logs = []
    if log_file.exists():
        with open(log_file) as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

    logs.append(report)

    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

    return log_file


def format_report(report):
    """Format report for display/alerts."""
    lines = [
        f"📊 *TAO Monitor Report*",
        f"⏰ {report['timestamp'][:19]}",
        f"",
        f"💰 Free Balance: {report['free_balance']:.4f} TAO",
        f"🔒 Total Staked: {report['total_staked']:.4f} TAO",
        f"📈 Total TAO: {report['total_tao']:.4f}",
    ]

    if report.get("alerts"):
        lines.append("")
        lines.append("⚠️ *Alerts:*")
        for alert in report["alerts"]:
            lines.append(f"  - {alert}")

    return "\n".join(lines)


def run_monitor():
    """Main monitoring function."""
    print(f"[{datetime.now().isoformat()}] Running TAO monitor check...")

    config = load_config()

    if config["total_tao_deployed"] == 0:
        msg = (
            f"📊 *TAO Monitor*\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"ℹ️ No TAO deployed yet.\n"
            f"Wallet: `{config['coldkey_address'][:12]}...`\n"
            f"Status: Ready to deploy when funded."
        )
        print(msg)
        send_telegram(msg, config)
        return

    report = check_positions(config)
    log_file = log_report(report)
    formatted = format_report(report)

    print(formatted)
    send_telegram(formatted, config)
    print(f"[LOG] Saved to {log_file}")


if __name__ == "__main__":
    run_monitor()
