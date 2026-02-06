#!/usr/bin/env bash
set -euo pipefail

echo "=== QwickService CIS Setup ==="

# Copy env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[+] Created .env from .env.example"
fi

# Install interceptor dependencies
echo "[*] Installing interceptor dependencies..."
cd services/interceptor && npm install && cd ../..

# Install dashboard dependencies
echo "[*] Installing dashboard dependencies..."
cd services/dashboard && npm install && cd ../..

# Install Python service dependencies
for svc in detection policy review; do
    echo "[*] Installing $svc dependencies..."
    cd "services/$svc" && pip install -e ".[dev]" && cd ../..
done

# Download spaCy model for detection
echo "[*] Downloading spaCy model..."
python -m spacy download en_core_web_sm

echo "=== Setup complete ==="
