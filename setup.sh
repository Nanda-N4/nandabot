#!/bin/bash
echo "Installing Nanda VPN Bot..."
sudo apt update && sudo apt install -y python3-pip git screen
pip3 install python-telegram-bot requests urllib3 python-dotenv
echo "✅ Setup Complete! Now create .env and run 'python3 main.py'"
