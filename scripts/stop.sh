#!/bin/bash
echo "Deteniendo bot..."
pkill -f "bot.py" 2>/dev/null || true
sleep 2

if pgrep -f "bot.py" > /dev/null; then
    echo "Forzando detención..."
    pkill -9 -f "bot.py" 2>/dev/null || true
fi
echo "Bot detenido"