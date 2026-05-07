#!/usr/bin/env python3
"""
TAO Investor - Deploy Stake
Stakes TAO across subnets according to the configured strategy.
Run this manually when you're ready to deploy funds.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import bittensor as bt

CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategy.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_balance(wallet):
    """Get available TAO balance."""
    subtensor = bt.subtensor(network="finney")
    balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
    return float(balance) if balance else 0


def deploy_strategy(dry_run=True):
    """Deploy TAO according to strategy allocations."""
    config = load_config()
    wallet = bt.wallet(name=config["wallet_name"], hotkey=config["hotkey"])
    subtensor = bt.subtensor(network="finney")

    balance = get_balance(wallet)
    print(f"\n{'='*50}")
    print(f"  TAO STAKING DEPLOYMENT")
    print(f"{'='*50}")
    print(f"\n  Wallet: {config['coldkey_address'][:20]}...")
    print(f"  Available Balance: {balance:.4f} TAO")
    print(f"  Strategy: {config['strategy']}")
    print(f"  Mode: {'DRY RUN (no transactions)' if dry_run else 'LIVE'}")
    print(f"\n{'='*50}")
    print(f"  ALLOCATION PLAN:")
    print(f"{'='*50}\n")

    if balance <= 0.01:
        print("  ⚠️  Insufficient balance. Fund your wallet first.")
        print(f"  Send TAO to: {config['coldkey_address']}")
        return

    # Reserve small amount for transaction fees
    deployable = balance - 0.05  # Keep 0.05 TAO for fees

    for alloc in config["allocations"]:
        amount = deployable * (alloc["percentage"] / 100)
        print(f"  [{alloc['name']}]")
        print(f"    Subnet: SN{alloc['subnet']}")
        print(f"    Amount: {amount:.4f} TAO ({alloc['percentage']}%)")
        print(f"    Purpose: {alloc['description']}")

        if not dry_run and amount > 0.01:
            try:
                if alloc["subnet"] == 0:
                    # Root network staking (delegate)
                    print(f"    → Staking to root network...")
                    # For root: use add_stake
                    success = subtensor.add_stake(
                        wallet=wallet,
                        hotkey_ss58=wallet.hotkey.ss58_address,
                        amount=bt.Balance.from_tao(amount),
                        netuid=0
                    )
                    status = "✅ Success" if success else "❌ Failed"
                else:
                    # Subnet staking
                    print(f"    → Staking to subnet {alloc['subnet']}...")
                    success = subtensor.add_stake(
                        wallet=wallet,
                        hotkey_ss58=wallet.hotkey.ss58_address,
                        amount=bt.Balance.from_tao(amount),
                        netuid=alloc["subnet"]
                    )
                    status = "✅ Success" if success else "❌ Failed"
                print(f"    {status}")
            except Exception as e:
                print(f"    ❌ Error: {e}")
        elif dry_run:
            print(f"    → [DRY RUN - no transaction]")
        print()

    print(f"{'='*50}")
    if dry_run:
        print(f"  This was a DRY RUN. To deploy for real, run:")
        print(f"  python3 deploy_stake.py --live")
    else:
        print(f"  Deployment complete! Run monitor.py to track positions.")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    live = "--live" in sys.argv
    if live:
        confirm = input("⚠️  LIVE MODE: This will stake real TAO. Type 'YES' to confirm: ")
        if confirm != "YES":
            print("Aborted.")
            sys.exit(0)
    deploy_strategy(dry_run=not live)
