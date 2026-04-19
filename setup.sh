#!/bin/bash

echo "------------------------------------------------"
echo "🚀 NandaBot V2.5 Auto-Installer Starting..."
echo "------------------------------------------------"

# 1. Update System
sudo apt update && sudo apt install -y python3-pip git screen

# 2. Install Python Libraries
pip3 install python-telegram-bot requests urllib3 python-dotenv --break-system-packages

# 3. Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found! Creating a template..."
    cat <<EOT >> .env
BOT_TOKEN=YOUR_BOT_TOKEN
ADMIN_ID=5567910560
S1_URL=https://s1.n4vpn.xyz:4121/n4
S1_DOMAIN=s1.n4vpn.xyz
S1_USER=n
S1_PASS=n
S1_SUB_PORT=2096
EOT
    echo "✅ .env template created. Please edit it with 'nano .env' before running."
fi

# 4. Success Message
echo "------------------------------------------------"
echo "✅ Setup Complete!"
echo "1. Edit secrets: nano .env"
echo "2. Start Bot: screen -dmS nandabot python3 main.py"
echo "3. View Logs: screen -r nandabot"
echo "------------------------------------------------"
