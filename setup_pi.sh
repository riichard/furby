#!/bin/bash
# setup_pi.sh — One-time setup script for Furby AI on Raspberry Pi Zero W
# Run this on the Pi after cloning the repo:  bash setup_pi.sh

set -e
echo "=== Furby Pi Setup ==="

# ---------------------------------------------------------------------------
# 1. Audio: enable I2S + Adafruit Speaker Bonnet (MAX98357A / hifiberry-dac)
# ---------------------------------------------------------------------------
echo "[1/4] Configuring audio (I2S + hifiberry-dac)..."

CONFIG=/boot/firmware/config.txt

# Enable I2S (uncomment if commented out)
sudo sed -i 's/#dtparam=i2s=on/dtparam=i2s=on/' $CONFIG

# Disable bcm2835 onboard audio (conflicts with I2S)
sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' $CONFIG

# Add hifiberry-dac overlay if not already present
if ! grep -q "dtoverlay=hifiberry-dac" $CONFIG; then
    sudo sed -i '/dtparam=i2s=on/a dtoverlay=hifiberry-dac' $CONFIG
    echo "  Added dtoverlay=hifiberry-dac"
else
    echo "  hifiberry-dac overlay already present"
fi

# ---------------------------------------------------------------------------
# 2. Set HifiBerry as default ALSA device
# ---------------------------------------------------------------------------
echo "[2/4] Setting HifiBerry as default ALSA device..."

sudo tee /etc/asound.conf > /dev/null << 'EOF'
# Output: HifiBerry DAC (card 0) — with mono->stereo conversion
# Input:  USB PnP Sound Device (card 1)
pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:1,0"
    }
}
ctl.!default { type hw card 0 }
EOF

# ---------------------------------------------------------------------------
# 3. Install system dependencies
# ---------------------------------------------------------------------------
echo "[3/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y portaudio19-dev python3-pyaudio ffmpeg

# ---------------------------------------------------------------------------
# 4. Install Python dependencies
# ---------------------------------------------------------------------------
echo "[4/5] Installing Python packages..."
pip3 install --break-system-packages anthropic openai pyyaml numpy python-dotenv yt-dlp phue

# ---------------------------------------------------------------------------
# 5. Create memory directory and install nightly summarize cron job
# ---------------------------------------------------------------------------
echo "[5/5] Setting up memory directory and cron job..."

FURBY_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$FURBY_DIR/memory"

# Install cron job: run summarize.py daily at 3am
CRON_JOB="0 3 * * * cd $FURBY_DIR && python3 summarize.py >> $FURBY_DIR/memory/summarize.log 2>&1"
# Add only if not already present
( crontab -l 2>/dev/null | grep -v "summarize.py"; echo "$CRON_JOB" ) | crontab -
echo "  Cron job installed: daily summarize at 3am"
echo "  Verify with: crontab -l"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy your .env file:  scp .env furby:~/furby/.env"
echo "  2. Reboot the Pi:        sudo reboot"
echo "  3. Calibrate expressions: make calibrate"
echo "  4. Run Furby:            make run"
echo "  5. Manual memory summary: make summarize"
