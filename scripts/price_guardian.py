#!/usr/bin/env python3
"""
TAO Price Guardian - Intelligent Exit Strategy
Monitors TAO price hourly and executes tiered exit strategy.
Uses 24-hour confirmation to avoid flash crash false triggers.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"
EXIT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "exit_strategy.json"
STATE_PATH = Path(__file__).parent.parent / "logs" / "guardian_state.json"
LOG_DIR = Path(__file__).parent.parent / "logs"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_exit_strategy():
    with open(EXIT_CONFIG_PATH) as f:
        return json.load(f)


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {
        "level_first_triggered": {},
        "unstaked_levels": [],
        "total_unstaked_pct": 0,
        "price_history": [],
        "last_check": None
    }


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def get_tao_price():
    """Fetch current TAO price from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bittensor&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data["bittensor"]["usd"]
    except Exception as e:
        print(f"Price fetch error: {e}")
        return None


def send_telegram(message, config):
    """Send Telegram alert."""
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


def unstake_percentage(config, pct):
    """Unstake a percentage of current positions."""
    import bittensor as bt

    wallet = bt.wallet(name=config["wallet_name"], hotkey=config["hotkey"])
    subtensor = bt.subtensor(network="finney")

    results = []
    for alloc in config["allocations"]:
        try:
            # Calculate amount to unstake from this position
            # Get current stake for this position
            amount_to_unstake = alloc.get("current_stake", 0) * (pct / 100)

            if amount_to_unstake < 0.001:
                continue

            print(f"  Unstaking {amount_to_unstake:.4f} TAO from {alloc['name']} (SN{alloc['subnet']})")

            success = subtensor.unstake(
                wallet=wallet,
                hotkey_ss58=alloc.get("validator_hotkey", wallet.hotkey.ss58_address),
                amount=bt.Balance.from_tao(amount_to_unstake),
                netuid=alloc["subnet"]
            )
            status = "SUCCESS" if success else "FAILED"
            results.append({"name": alloc["name"], "amount": amount_to_unstake, "status": status})
        except Exception as e:
            results.append({"name": alloc["name"], "amount": 0, "status": f"ERROR: {e}"})

    return results


def determine_level(price, exit_strategy):
    """Determine which exit level the current price falls into."""
    levels = exit_strategy["levels"]

    for level in levels:
        if "above" in level and price > level["above"]:
            return level
        if "range" in level and level["range"][0] <= price <= level["range"][1]:
            return level
        if "below" in level and price < level["below"]:
            return level

    return levels[0]  # Default to SAFE


def run_guardian():
    """Main price guardian check."""
    config = load_config()
    exit_strategy = load_exit_strategy()
    state = load_state()
    now = datetime.now()

    print(f"\n{'='*60}")
    print(f"  PRICE GUARDIAN CHECK")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Get current price
    price = get_tao_price()
    if price is None:
        print("  Could not fetch price. Skipping check.")
        return

    print(f"  Current TAO Price: ${price:.2f}")
    print(f"  Entry Price: ${exit_strategy['current_price_at_creation']:.2f}")

    # Track price history (keep last 48 hours)
    state["price_history"].append({
        "time": now.isoformat(),
        "price": price
    })
    # Keep only last 48 entries (hourly = 48 hours)
    state["price_history"] = state["price_history"][-48:]

    # Determine current level
    current_level = determine_level(price, exit_strategy)
    level_name = current_level["name"]
    print(f"  Current Level: {level_name}")

    # Check if already fully executed
    if state["total_unstaked_pct"] >= 75:
        print(f"  Maximum unstaking already executed (75%). 25% conviction hold active.")
        save_state(state)
        return

    # Handle each level
    if level_name == "SAFE":
        print(f"  ✅ SAFE ZONE. No action needed.")
        # Clear any pending triggers
        state["level_first_triggered"] = {}

    elif level_name == "CAUTION":
        print(f"  ⚠️  CAUTION ZONE (${current_level['range'][0]}-${current_level['range'][1]})")

        # Send alert (max once per 6 hours)
        last_alert = state.get("last_caution_alert")
        if not last_alert or (now - datetime.fromisoformat(last_alert)) > timedelta(hours=6):
            msg = (
                f"⚠️ *TAO Price Alert - CAUTION*\n\n"
                f"Price: ${price:.2f}\n"
                f"Level: CAUTION (${current_level['range'][0]}-${current_level['range'][1]})\n"
                f"Entry: ${exit_strategy['current_price_at_creation']:.2f}\n\n"
                f"Staking rewards can recover this dip in 3-6 months.\n"
                f"No auto-action taken. Monitoring closely."
            )
            send_telegram(msg, config)
            state["last_caution_alert"] = now.isoformat()
            print(f"  📱 Telegram alert sent.")

    elif level_name in ["DEFENSIVE", "EXIT", "EMERGENCY"]:
        unstake_pct = current_level["unstake_pct"]
        confirmation_hours = exit_strategy.get("confirmation_hours", 24)

        print(f"  🔴 {level_name} ZONE")
        print(f"  Required action: Unstake {unstake_pct}%")
        print(f"  Requires {confirmation_hours}hr confirmation")

        # Check if already executed this level
        if level_name in state["unstaked_levels"]:
            print(f"  Already executed {level_name} level. Skipping.")
        else:
            # Start or check 24-hour confirmation
            trigger_key = f"level_{level_name}"

            if trigger_key not in state["level_first_triggered"]:
                # First time hitting this level
                state["level_first_triggered"][trigger_key] = now.isoformat()
                hours_remaining = confirmation_hours

                msg = (
                    f"🔴 *TAO Price Alert - {level_name}*\n\n"
                    f"Price: ${price:.2f}\n"
                    f"Level: {level_name}\n\n"
                    f"⏳ 24-hour confirmation started.\n"
                    f"If price stays below ${current_level.get('range', [current_level.get('below', 0)])[0]} "
                    f"for {confirmation_hours} hours, will auto-unstake {unstake_pct}%.\n\n"
                    f"You can manually override by running:\n"
                    f"`python3 price_guardian.py --cancel`"
                )
                send_telegram(msg, config)
                print(f"  ⏳ 24hr confirmation STARTED. Alert sent.")

            else:
                # Check if 24 hours have passed
                first_triggered = datetime.fromisoformat(state["level_first_triggered"][trigger_key])
                hours_elapsed = (now - first_triggered).total_seconds() / 3600

                if hours_elapsed >= confirmation_hours:
                    # Check that ALL price readings in last 24h were below threshold
                    recent_prices = [
                        p["price"] for p in state["price_history"]
                        if datetime.fromisoformat(p["time"]) >= first_triggered
                    ]

                    threshold = current_level.get("range", [current_level.get("below", 0)])[0] if "range" in current_level else current_level.get("below", 0)

                    if all(p <= threshold + 5 for p in recent_prices):  # +$5 tolerance
                        print(f"  ✅ 24hr CONFIRMED. Executing {level_name} unstake.")

                        # Execute unstake
                        results = unstake_percentage(config, unstake_pct)

                        state["unstaked_levels"].append(level_name)
                        state["total_unstaked_pct"] += unstake_pct

                        msg = (
                            f"🚨 *AUTO-UNSTAKE EXECUTED - {level_name}*\n\n"
                            f"Price: ${price:.2f}\n"
                            f"Unstaked: {unstake_pct}% of positions\n"
                            f"Total unstaked so far: {state['total_unstaked_pct']}%\n"
                            f"Remaining staked: {100 - state['total_unstaked_pct']}%\n\n"
                        )
                        for r in results:
                            icon = "✅" if r["status"] == "SUCCESS" else "❌"
                            msg += f"{icon} {r['name']}: {r['amount']:.4f} TAO - {r['status']}\n"

                        send_telegram(msg, config)
                    else:
                        print(f"  Price bounced above threshold during confirmation. Resetting.")
                        del state["level_first_triggered"][trigger_key]
                else:
                    remaining = confirmation_hours - hours_elapsed
                    print(f"  ⏳ Confirmation in progress: {hours_elapsed:.1f}h elapsed, {remaining:.1f}h remaining")

    # Save state
    state["last_check"] = now.isoformat()
    save_state(state)

    # Log
    log_entry = {
        "timestamp": now.isoformat(),
        "price": price,
        "level": level_name,
        "total_unstaked_pct": state["total_unstaked_pct"]
    }
    log_file = LOG_DIR / f"guardian_{now.strftime('%Y-%m-%d')}.json"
    logs = []
    if log_file.exists():
        with open(log_file) as f:
            try:
                logs = json.load(f)
            except:
                logs = []
    logs.append(log_entry)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

    print(f"\n  Log saved to {log_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if "--cancel" in sys.argv:
        state = load_state()
        state["level_first_triggered"] = {}
        save_state(state)
        print("✅ All pending exit confirmations cancelled.")
        config = load_config()
        send_telegram("✅ Exit confirmations cancelled by user.", config)
    else:
        run_guardian()
