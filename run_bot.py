#!/usr/bin/env python3
"""
Run Telegram Bot for Hermes Crypto Agent
"""

import os
import sys
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.telegram_bot import CryptoTelegramBot


def main():
    """Main entry point"""
    # Load config
    config_path = Path(__file__).parent / "config" / "config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("⚠️  Config file not found, using defaults")
        config = {}
    
    # Get token from env or config
    token = os.getenv("TELEGRAM_BOT_TOKEN") or config.get("telegram", {}).get("bot_token")
    
    if not token:
        print("❌ No Telegram bot token configured!")
        print("\nOptions:")
        print("1. Set env var: export TELEGRAM_BOT_TOKEN=your_token")
        print("2. Edit config/config.yaml and add your token")
        return
    
    # Get allowed users from config
    allowed_users = config.get("telegram", {}).get("allowed_users", [])
    
    print("=" * 50)
    print("🤖 Hermes Crypto Telegram Bot")
    print("=" * 50)
    print(f"\nToken: {token[:10]}...")
    print(f"Allowed users: {allowed_users if allowed_users else 'All'}")
    print("\nStarting bot...")
    print("Press Ctrl+C to stop\n")
    
    # Create and run bot
    bot = CryptoTelegramBot(token=token, allowed_users=allowed_users)
    bot.run()


if __name__ == "__main__":
    main()
