#!/bin/bash
# MAX setup — run once on a fresh VM to get MAX running
set -e

cd "$(dirname "$0")"

echo "==> Installing Python dependencies..."
pip3 install -r requirements.txt

echo "==> Installing Playwright browsers..."
python3 -m playwright install chromium --with-deps 2>/dev/null || true

echo "==> Setting up .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "  !! Fill in .env with your credentials, then run: sudo systemctl restart max"
    echo ""
fi

echo "==> Creating data directory..."
mkdir -p data static/img static/files public

echo "==> Installing systemd service..."
sudo cp max.service /etc/systemd/system/max.service
sudo systemctl daemon-reload
sudo systemctl enable max
sudo systemctl restart max

echo ""
echo "MAX is running at http://localhost:8000"
echo "Check logs: tail -f /home/boxd/max/max.log"
