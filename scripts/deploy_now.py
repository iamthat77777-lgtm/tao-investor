#!/usr/bin/env python3
"""
TAO Investor - Live Deployment
Stakes TAO across optimized 3-position strategy.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import bittensor as bt

CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"
LOG_DIR = Path(__file__).parent.parent / "logs"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def send_telegram(message, config):
    token = config["alerts"]["telegram_bot_token"]
    chat_id = config["alerts"]["telegram_chat_id"]
    if not token or not chat_id:
        return
    import urllib.request
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Telegram error: {e}")

def deploy():
    config = load_config()
    wallet = bt.wallet(name=config["wallet_name"], hotkey=config["hotkey"])
    subtensor = bt.subtensor(network="finney")

    # Check balance
    balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
    free = float(balance)

    print(f"\n{'='*55}")
    print(f"  TAO STAKING DEPLOYMENT - LIVE")
    print(f"{'='*55}")
    print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Wallet:  {config['coldkey_address'][:20]}...")
    print(f"  Balance: {free:.6f} TAO")
    print(f"  Strategy: {config['strategy']}")
    print(f"{'='*55}\n")

    if free < 0.1:
        print("  Insufficient balance!")
        return

    # Reserve for fees
    deployable = free - 0.05
    print(f"  Deployable: {deployable:.6f} TAO (keeping 0.05 for fees)\n")

    results = []

    for alloc in config["allocations"]:
        amount = round(deployable * (alloc["percentage"] / 100), 6)
        print(f"  [{alloc['name']}] SN{alloc['subnet']}")
        print(f"    Amount: {amount:.6f} TAO ({alloc['percentage']}%)")

        try:
            if alloc["subnet"] == 0:
                # Root network - delegate stake
                print(f"    Staking to root network...")
                success = subtensor.add_stake(
                    wallet=wallet,
                    hotkey_ss58=wallet.hotkey.ss58_address,
                    amount=bt.Balance.from_tao(amount),
                    netuid=0
                )
            else:
                # Subnet staking
                print(f"    Staking to subnet {alloc['subnet']}...")
                success = subtensor.add_stake(
                    wallet=wallet,
                    hotkey_ss58=wallet.hotkey.ss58_address,
                    amount=bt.Balance.from_tao(amount),
                    netuid=alloc["subnet"]
                )

            status = "SUCCESS" if success else "FAILED"
            print(f"    Result: {status}")
            results.append({"subnet": alloc["subnet"], "name": alloc["name"], "amount": amount, "status": status})
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"subnet": alloc["subnet"], "name": alloc["name"], "amount": amount, "status": f"ERROR: {e}"})

        print()
        time.sleep(2)  # Small delay between transactions

    # Check final balance
    final_balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
    final_free = float(final_balance)

    print(f"{'='*55}")
    print(f"  DEPLOYMENT COMPLETE")
    print(f"  Remaining balance: {final_free:.6f} TAO")
    print(f"{'='*55}\n")

    # Send Telegram notification
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    msg = (
        f"🚀 TAO Deployment Complete!\n\n"
        f"Strategy: {config['strategy']}\n"
        f"Positions: {success_count}/{len(results)} successful\n\n"
    )
    for r in results:
        icon = "✅" if r["status"] == "SUCCESS" else "❌"
        msg += f"{icon} {r['name']} (SN{r['subnet']}): {r['amount']:.4f} TAO\n"
    msg += f"\n💰 Remaining: {final_free:.6f} TAO"

    send_telegram(msg, config)

    # Log deployment
    log_file = LOG_DIR / f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": results, "remaining": final_free}, f, indent=2)
    print(f"  Log saved: {log_file}")

if __name__ == "__main__":
    deploy()
