# TAO Investor — Automated Setup

> ⚠️ **Important — read before continuing**
>
> This file builds technical infrastructure for monitoring and managing a Bittensor (TAO) staking position. It is not financial advice. Cryptocurrency investments are highly speculative and can result in total loss of capital. Past results are not indicative of future performance. Before investing, consult a qualified financial adviser. Staking rewards may be taxable in your jurisdiction — consult a tax professional.

## How to use this file

1. Download or clone this project to your Mac
2. Open Terminal and navigate to the project folder:
   ```
   cd ~/Downloads/AI-Agent/tao-investor
   ```
3. Type `claude` and press Enter to start Claude Code
4. Say: **"Read TAO_INVESTOR_SETUP.md and set up my TAO Investor system"**

Claude Code will guide you through everything from here. No coding required.

---

## Instructions for Claude Code

You are a friendly setup assistant helping someone configure their personal TAO Investor monitoring system. The person you're helping may have limited coding experience. Explain everything clearly and simply. Never use jargon without immediately explaining it in plain English.

Work through each phase in order. Do not skip ahead. Do not configure anything until you have all the information you need.

---

## PHASE 0: Welcome

Introduce yourself warmly:

> "Welcome! I'm going to help you get your TAO Investor system running. By the time we're done, you'll have:
>
> - A live monitoring system that tracks your TAO balance and staking positions every hour
> - Telegram alerts sent directly to your phone — morning reports, price warnings, and 3-hour portfolio snapshots
> - A local dashboard showing your price history, portfolio value, and estimated staking returns
>
> This should take about 10 minutes. I'll ask a few questions first, then set everything up for you."

---

## PHASE 1: Gather Configuration

Ask these questions one at a time. Wait for each answer before asking the next.

**Question 1 — Telegram bot:**
> "First, I need to connect your alert system to Telegram. Do you already have a Telegram bot set up? If yes, share your bot token and chat ID. If not, just say no and I'll walk you through creating one — it takes 5 minutes."

If they need Telegram setup, guide them:
> "Here's how to set up your Telegram alerts:
>
> 1. Open Telegram on your phone
> 2. Search for **@BotFather** and start a chat
> 3. Send: `/newbot`
> 4. Give your bot a name — something like 'TAO Watcher' works great
> 5. BotFather will give you a token — it looks like: `1234567890:AAABBB...` — copy it and paste it here
> 6. Now search for **@userinfobot** and send it any message
> 7. It replies with your personal ID number — paste that here too
> 8. Finally, send your new bot any message (just say 'hi') so it knows you exist
>
> Once you have both numbers, paste them here."

**Question 2 — Bittensor wallet:**
> "Do you already have a Bittensor wallet? If yes, what is your coldkey SS58 address? (It looks like: 5ECnrM...) And what is your hotkey name — usually 'default' unless you changed it. If you don't have a wallet yet, say no and I'll create one for you."

If they don't have a wallet yet, run:
```bash
btcli wallet new_coldkey --wallet.name tao_main
```

Then say:
> "Your wallet is being created. In a moment you'll see a 12-word seed phrase on screen.
>
> **This is the most important thing in this entire setup.** Write it down with pen and paper right now. Store it somewhere physically safe — not in a photo, not in a note on your phone.
>
> If you lose it, your TAO is gone forever. If someone else gets it, your TAO is gone forever.
>
> Once you've written it down safely, tell me your coldkey address — the long string starting with 5 that appeared on screen."

**Question 3 — Wallet name:**
> "What did you name your wallet? (Default is `tao_main` if we just created it, otherwise it's whatever name you used when creating it.)"

**Question 4 — TAO deployed:**
> "How much TAO have you deployed so far? If you haven't staked anything yet, enter 0 — we can still build the system and you can deploy later."

**Question 5 — Entry price:**
> "What price (in USD) did you buy most of your TAO at? This is your entry price — used to track profit/loss and set your alert thresholds. If you bought at multiple prices, use an average."

**Question 6 — Principal:**
> "How many TAO tokens do you consider your principal (the amount you plan to stake long-term)? This is used for portfolio value calculations in your alerts and dashboard."

---

## PHASE 2: Install Dependencies

Check and install what's needed:

```bash
python3 --version
```

If Python 3.9+ is not installed, say:
> "You'll need Python 3.9 or later. Download it from python.org — it's free and takes 2 minutes to install. Come back when it's done."

Install the bittensor library if missing:
```bash
python3 -c "import bittensor" 2>/dev/null || pip3 install --user bittensor
```

Check PM2:
```bash
which pm2 || echo "not found"
```

If PM2 is not found:
> "I'm going to install PM2 — this is a process manager that keeps your monitoring scripts running in the background, even after you close Terminal. It requires Node.js."

```bash
which node || echo "Node not found"
```

If Node is missing, say:
> "You'll need Node.js first. Download it from nodejs.org — choose the LTS version. Come back when it's installed."

Then install PM2:
```bash
npm install -g pm2
```

---

## PHASE 3: Write Configuration Files

Create the `logs` folder if it doesn't exist:
```bash
mkdir -p logs
```

Write `config/strategy.json` using the answers from Phase 1:

```python
import json
from pathlib import Path

config = {
  "wallet_name": "[WALLET_NAME]",
  "hotkey": "[HOTKEY]",
  "wallet_path": "~/.bittensor/wallets/",
  "coldkey_address": "[COLDKEY_ADDRESS]",
  "hotkey_address": "[HOTKEY_ADDRESS]",
  "cost_basis_gbp": 0,
  "total_tao_deployed": [TAO_DEPLOYED],
  "strategy": "custom",
  "allocations": [],
  "alerts": {
    "telegram_bot_token": "[TELEGRAM_BOT_TOKEN]",
    "telegram_chat_id": "[TELEGRAM_CHAT_ID]",
    "apy_drop_threshold_percent": 20,
    "rebalance_drift_percent": 5,
    "profit_alert_gbp": 100
  },
  "monitoring": {
    "check_interval_minutes": 60,
    "daily_summary_hour": 9
  }
}

Path("config/strategy.json").write_text(json.dumps(config, indent=2))
```

Write `config/exit_strategy.json` using the entry price from Phase 1:

```python
import json
from pathlib import Path
from datetime import date

strategy = {
  "current_price_at_creation": [ENTRY_PRICE],
  "created_at": date.today().isoformat(),
  "principal_tao": [PRINCIPAL_TAO],
  "blended_apy": 0.1862,
  "confirmation_hours": 24,
  "conviction_hold_pct": 25,
  "levels": [
    {"name": "SAFE",      "above": 230, "action": "none",              "unstake_pct": 0},
    {"name": "CAUTION",   "range": [205, 230], "action": "alert_only", "unstake_pct": 0},
    {"name": "DEFENSIVE", "range": [165, 205], "action": "alert_and_unstake", "unstake_pct": 25},
    {"name": "EXIT",      "range": [130, 165], "action": "alert_and_unstake", "unstake_pct": 50},
    {"name": "EMERGENCY", "below": 130, "action": "emergency_exit",    "unstake_pct": 75}
  ]
}

Path("config/exit_strategy.json").write_text(json.dumps(strategy, indent=2))
```

Then say:
> "I've written your configuration files. A few important things:
>
> - `config/strategy.json` contains your Telegram bot token — keep this file private
> - Never upload this folder to GitHub, Google Drive, or any cloud storage without checking the `.gitignore` first
> - Consider copying the config folder to a USB drive as a backup
>
> Both files are already listed in `.gitignore` so they won't be accidentally committed if you use git."

---

## PHASE 4: Send Test Alert

Verify Telegram is working:

```python
import json, urllib.request

config = json.load(open("config/strategy.json"))
token = config["alerts"]["telegram_bot_token"]
chat_id = config["alerts"]["telegram_chat_id"]

url = f"https://api.telegram.org/bot{token}/sendMessage"
data = json.dumps({
    "chat_id": chat_id,
    "text": "✅ *TAO Investor Setup*\n\nYour alert system is connected and working.",
    "parse_mode": "Markdown"
}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read())
print("✓ Telegram connected" if resp.get("ok") else f"❌ Failed: {resp}")
```

If it fails, say:
> "The Telegram test failed. Most likely the bot token or chat ID is wrong. Double-check:
> - The token from @BotFather (no spaces, starts with numbers)
> - Your chat ID from @userinfobot (just the number)
> - That you sent at least one message to your bot after creating it
>
> Edit `config/strategy.json` and update the values, then I'll test again."

---

## PHASE 5: Run a Live Check

Run the monitor script to confirm everything is working end-to-end:

```bash
python3 scripts/monitor.py
```

Then run the price guardian:

```bash
python3 scripts/price_guardian.py
```

Say:
> "If you saw your balance and the current TAO price printed above — your system is working. If you got an error, paste it here and I'll fix it."

---

## PHASE 6: Start Background Monitoring

Start all 5 monitoring processes with PM2:

```bash
pm2 start ecosystem.config.js
pm2 save
```

Then set up automatic startup so everything restarts if your Mac reboots. PM2 will print a command for you to run — it looks like:

```
sudo env PATH=$PATH:/usr/local/bin pm2 startup launchd -u yourusername --hp /Users/yourusername
```

Say:
> "PM2 just printed a command starting with `sudo`. Copy it exactly and run it — it will ask for your Mac password. This is safe: it's just telling your Mac to start PM2 automatically when you log in.
>
> If you're not sure what it's asking, paste it here and I'll explain before you run it."

Then set up cron jobs as a backup layer:

```bash
(crontab -l 2>/dev/null; cat << 'EOF'
# TAO Investor — backup cron layer
0 * * * * /usr/bin/python3 PATH_TO_PROJECT/scripts/monitor.py >> PATH_TO_PROJECT/logs/cron-monitor.log 2>&1
0 7 * * * /usr/bin/python3 PATH_TO_PROJECT/scripts/morning_alert.py >> PATH_TO_PROJECT/logs/cron-morning.log 2>&1
0 9 * * * /usr/bin/python3 PATH_TO_PROJECT/scripts/daily_summary.py >> PATH_TO_PROJECT/logs/cron-summary.log 2>&1
*/30 * * * * /usr/bin/python3 PATH_TO_PROJECT/scripts/price_guardian.py >> PATH_TO_PROJECT/logs/cron-guardian.log 2>&1
0 */3 * * * /usr/bin/python3 PATH_TO_PROJECT/scripts/summary_alert.py >> PATH_TO_PROJECT/logs/cron-summary-alert.log 2>&1
EOF
) | crontab -
```

Replace `PATH_TO_PROJECT` with the actual path. Say:
> "I've added cron jobs as a safety net. Even if PM2 stops unexpectedly, your monitoring will keep running via cron. Both systems watch for each other."

---

## PHASE 7: Build the Dashboard

Generate the dashboard data and open it:

```bash
python3 regen_data.py
open dashboard.html
```

Say:
> "Your dashboard is open in your browser. It shows:
>
> - Current TAO price vs your entry price
> - Portfolio value vs cost basis
> - Estimated staking returns over time
> - Your exit level (SAFE / CAUTION / DEFENSIVE / EXIT / EMERGENCY)
>
> To refresh the charts with new data any time, run: `python3 regen_data.py`
>
> I'd recommend bookmarking `dashboard.html` in your browser."

---

## PHASE 8: Completion

Run `pm2 list` and show the output.

Then give this summary:

> ⚠️ **Tax reminder:** Staking rewards may be taxable events in your jurisdiction. Keep a record of what you staked, when, and at what price. Consult a tax professional — especially if you're in the UK, US, EU, or Australia.

> "🎉 Your TAO Investor system is live.
>
> Here's what's running on your machine right now:
>
> | Process | What it does | Schedule |
> |---|---|---|
> | `tao-monitor` | Checks wallet balance + stake | Every hour |
> | `tao-morning-alert` | Morning portfolio report | 7:00 AM daily |
> | `tao-daily-summary` | End-of-day summary | 9:00 AM daily |
> | `tao-price-guardian` | Price level check + unstake alerts | Every 30 min |
> | `tao-summary-alert` | Full snapshot (price + balance + P&L) | Every 3 hours |
>
> You'll get a Telegram message on your phone when:
> - TAO drops below your entry price
> - Your portfolio hits a new level (CAUTION / DEFENSIVE / EXIT / EMERGENCY)
> - Price moves significantly in either direction
> - Every 3 hours with a full snapshot
>
> **Useful commands:**
> ```bash
> pm2 list                          # check all processes are running
> pm2 logs tao-monitor --lines 50   # view recent monitor output
> python3 scripts/monitor.py        # run a manual check now
> python3 regen_data.py             # refresh dashboard charts
> open dashboard.html               # open dashboard in browser
> ```
>
> **Files you should back up:**
> - `config/strategy.json` — your Telegram credentials and wallet settings
> - `config/exit_strategy.json` — your price levels and strategy
>
> One final thing: set a weekly reminder on your phone to run `pm2 list` and confirm all 5 processes show 'online'. It takes 5 seconds and will catch any silent failures before they become a problem.
>
> Good luck. Your TAO is now being watched 24/7."

---

*This file builds technical infrastructure for a Bittensor monitoring and alerting system. It is not financial advice. Cryptocurrency investments are highly speculative and can result in total loss of capital. Past performance is not indicative of future results. Staking rewards may constitute taxable events — consult a qualified tax professional.*
