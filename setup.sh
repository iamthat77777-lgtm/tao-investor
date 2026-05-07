#!/bin/bash
# TAO Investor — Interactive Setup
# Configures Telegram + wallet info and writes config files.

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "=========================================="
echo "  TAO Investor — Setup"
echo "=========================================="
echo ""

# --- Dependency checks ---
echo "→ Checking dependencies..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 not found. Install Python 3.9+ first."
  exit 1
fi
echo "  ✓ python3 ($(python3 --version 2>&1))"

if ! command -v pip3 >/dev/null 2>&1; then
  echo "❌ pip3 not found. Install pip first."
  exit 1
fi
echo "  ✓ pip3"

if ! python3 -c "import bittensor" >/dev/null 2>&1; then
  echo "  ⚠ bittensor not installed. Installing..."
  pip3 install --user bittensor
fi
echo "  ✓ bittensor"

if ! command -v pm2 >/dev/null 2>&1; then
  echo "  ⚠ pm2 not installed. Run: npm install -g pm2"
  echo "    (skipping for now, you can use cron instead)"
else
  echo "  ✓ pm2"
fi

echo ""
echo "→ Telegram bot setup"
echo "  Create a bot via @BotFather on Telegram, then send any message to it."
echo "  Get your chat_id from: https://api.telegram.org/bot<TOKEN>/getUpdates"
echo ""

read -p "Telegram bot token: " TG_TOKEN
read -p "Telegram chat ID: " TG_CHAT
echo ""

echo "→ Bittensor wallet"
echo "  If you don't have one yet: btcli wallet new_coldkey --wallet.name my_wallet"
echo ""
read -p "Wallet name [my_wallet]: " WALLET
WALLET=${WALLET:-my_wallet}
read -p "Hotkey name [default]: " HOTKEY
HOTKEY=${HOTKEY:-default}
read -p "Coldkey SS58 address: " COLDKEY
read -p "Hotkey SS58 address: " HOTKEYSS58
echo ""

echo "→ Strategy parameters"
read -p "Principal TAO deployed [0]: " PRINCIPAL
PRINCIPAL=${PRINCIPAL:-0}
read -p "Entry price USD [250.00]: " ENTRY
ENTRY=${ENTRY:-250.00}
echo ""

# --- Write configs ---
mkdir -p config logs

python3 - <<PYEOF
import json
from pathlib import Path

cfg = json.load(open("config/strategy.example.json"))
cfg["alerts"]["telegram_bot_token"] = "$TG_TOKEN"
cfg["alerts"]["telegram_chat_id"] = "$TG_CHAT"
cfg["wallet_name"] = "$WALLET"
cfg["hotkey"] = "$HOTKEY"
cfg["coldkey_address"] = "$COLDKEY"
cfg["hotkey_address"] = "$HOTKEYSS58"
cfg["total_tao_deployed"] = float("$PRINCIPAL")
json.dump(cfg, open("config/strategy.json", "w"), indent=2)

ex = json.load(open("config/exit_strategy.example.json"))
ex["principal_tao"] = float("$PRINCIPAL")
ex["current_price_at_creation"] = float("$ENTRY")
from datetime import date
ex["created_at"] = date.today().isoformat()
json.dump(ex, open("config/exit_strategy.json", "w"), indent=2)

print("  ✓ config/strategy.json")
print("  ✓ config/exit_strategy.json")
PYEOF

# --- Test Telegram ---
echo ""
echo "→ Sending Telegram test message..."
RESP=$(curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  -d chat_id="${TG_CHAT}" \
  -d parse_mode="Markdown" \
  -d text="✅ *TAO Investor Setup Complete*

Wallet: \`${COLDKEY:0:12}...\`
Principal: ${PRINCIPAL} TAO
Entry: \$${ENTRY}

You'll start receiving alerts shortly.")

if echo "$RESP" | grep -q '"ok":true'; then
  echo "  ✓ Telegram test sent successfully"
else
  echo "  ❌ Telegram test failed:"
  echo "$RESP"
  echo ""
  echo "  Check your bot token and chat ID, then re-edit config/strategy.json"
fi

# --- Make scripts executable ---
chmod +x start.sh 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start the bots:    ./start.sh start"
echo "  2. Check status:      ./start.sh status"
echo "  3. View logs:         ./start.sh logs"
echo "  4. Open dashboard:    open dashboard.html"
echo ""
echo "Or use cron instead of PM2 — see README.md for details."
echo ""
