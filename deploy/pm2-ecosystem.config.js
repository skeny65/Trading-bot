module.exports = {
  apps: [{
    name: 'trading-bot',
    script: './bot.py',
    interpreter: './venv/bin/python',
    cwd: './',
    env: {
      PYTHONPATH: '.'
    },
    autorestart: true,
    watch: false,
    max_restarts: 10,
    restart_delay: 4000,
    log_date_format: "YYYY-MM-DD HH:mm Z",
    error_file: "./logs/pm2-error.log",
    out_file: "./logs/pm2-out.log"
  }]
};