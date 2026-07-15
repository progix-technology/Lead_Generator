#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

if [ -n "${RENDER:-}" ] || [ -n "${PLAYWRIGHT_DISABLED:-}" ]; then
  echo "==> Skipping Playwright browser install in Render or when disabled."
else
  echo "==> Installing Playwright Chromium browser..."
  playwright install chromium --with-deps
fi

echo "==> Build complete!"
