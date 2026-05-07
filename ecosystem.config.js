// PM2 Ecosystem Configuration for TAO Investor
const path = require("path");
const ROOT = __dirname;
const SCRIPTS = path.join(ROOT, "scripts");
const LOGS = path.join(ROOT, "logs");

const baseEnv = {
  PATH: process.env.PATH + ":" + path.join(process.env.HOME || "", "Library/Python/3.9/bin")
};

module.exports = {
  apps: [
    {
      name: "tao-monitor",
      script: path.join(SCRIPTS, "monitor.py"),
      interpreter: "python3",
      cron_restart: "0 * * * *",
      autorestart: false,
      watch: false,
      max_memory_restart: "200M",
      log_file: path.join(LOGS, "pm2-monitor.log"),
      error_file: path.join(LOGS, "pm2-monitor-error.log"),
      env: baseEnv
    },
    {
      name: "tao-daily-summary",
      script: path.join(SCRIPTS, "daily_summary.py"),
      interpreter: "python3",
      cron_restart: "0 9 * * *",
      autorestart: false,
      watch: false,
      max_memory_restart: "200M",
      log_file: path.join(LOGS, "pm2-summary.log"),
      error_file: path.join(LOGS, "pm2-summary-error.log"),
      env: baseEnv
    },
    {
      name: "tao-morning-alert",
      script: path.join(SCRIPTS, "morning_alert.py"),
      interpreter: "python3",
      cron_restart: "0 7 * * *",
      autorestart: false,
      watch: false,
      max_memory_restart: "200M",
      log_file: path.join(LOGS, "pm2-morning.log"),
      error_file: path.join(LOGS, "pm2-morning-error.log"),
      env: baseEnv
    },
    {
      name: "tao-price-guardian",
      script: path.join(SCRIPTS, "price_guardian.py"),
      interpreter: "python3",
      cron_restart: "*/30 * * * *",
      autorestart: false,
      watch: false,
      max_memory_restart: "200M",
      log_file: path.join(LOGS, "pm2-guardian.log"),
      error_file: path.join(LOGS, "pm2-guardian-error.log"),
      env: baseEnv
    },
    {
      name: "tao-summary-alert",
      script: path.join(SCRIPTS, "summary_alert.py"),
      interpreter: "python3",
      cron_restart: "0 */3 * * *",
      autorestart: false,
      watch: false,
      max_memory_restart: "200M",
      log_file: path.join(LOGS, "pm2-summary-alert.log"),
      error_file: path.join(LOGS, "pm2-summary-alert-error.log"),
      env: baseEnv
    }
  ]
};
