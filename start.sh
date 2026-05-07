#!/bin/bash
# TAO Investor - Start/Stop/Status
# Usage: ./start.sh [start|stop|status|logs]

PROJECT_DIR="/Users/shatavuthu/Downloads/AI-Agent/tao-investor"
export PATH="$PATH:/Users/shatavuthu/Library/Python/3.9/bin"

case "${1:-start}" in
  start)
    echo "🚀 Starting TAO Investor monitoring..."
    pm2 start "$PROJECT_DIR/ecosystem.config.js"
    pm2 save
    echo "✅ Monitor started. Run './start.sh status' to check."
    ;;
  stop)
    echo "🛑 Stopping TAO Investor..."
    pm2 stop tao-monitor tao-daily-summary
    echo "✅ Stopped."
    ;;
  status)
    echo "📊 TAO Investor Status:"
    pm2 list
    echo ""
    echo "Latest log entries:"
    tail -20 "$PROJECT_DIR/logs/pm2-monitor.log" 2>/dev/null || echo "No logs yet."
    ;;
  logs)
    pm2 logs --lines 50
    ;;
  restart)
    pm2 restart tao-monitor tao-daily-summary
    echo "✅ Restarted."
    ;;
  deploy)
    echo "🚀 Running staking deployment (DRY RUN)..."
    python3 "$PROJECT_DIR/scripts/deploy_stake.py"
    ;;
  deploy-live)
    echo "⚠️  Running LIVE staking deployment..."
    python3 "$PROJECT_DIR/scripts/deploy_stake.py" --live
    ;;
  *)
    echo "Usage: ./start.sh [start|stop|status|logs|restart|deploy|deploy-live]"
    ;;
esac
