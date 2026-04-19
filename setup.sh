#!/bin/bash
echo "Installing Nanda VPN Bot Dependencies..."
sudo apt update && sudo apt install -y python3-pip git screen
pip3 install python-telegram-bot requests urllib3
echo "Setup Complete!"
echo "To run bot: screen -S nandabot python3 main.py"
