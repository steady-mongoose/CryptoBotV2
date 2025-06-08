
# CryptoBot V2

A cryptocurrency bot that posts daily market updates to X (Twitter) and Discord with real-time price data, social metrics, and video content.

## Quick Start

1. **Set Environment Variables** (in Replit Secrets):
   - `DISCORD_WEBHOOK_URL`
   - `X_CONSUMER_KEY`
   - `X_CONSUMER_SECRET` 
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
   - `YOUTUBE_API_KEY`
   - `PHONE_NUMBER` (for SMS notifications)

2. **Run the Bot**:
   - Click the **Run** button (uses safe queue system)
   - Or use workflows from the dropdown menu

## Available Workflows

- **Run Bot (Queue Safe)** - Main bot with queue system (prevents rate limits)
- **Discord Only** - Post to Discord webhook only
- **Run Diagnostics** - Test all systems before running
- **Check Queue Status** - Monitor X posting queue

## Features

- Real-time price data from multiple sources (Binance US, Coinbase, CoinGecko)
- Social sentiment analysis
- YouTube/Rumble video integration with quality rating
- Smart queue system to prevent X API rate limits
- Auto-failover between platforms
- SMS notifications

## Core Files

- `bot_v2.py` - Main bot script
- `modules/` - Core functionality modules
- `pre_run_diagnostics.py` - System health checks
- `check_queue_status.py` - Queue monitoring
- `fix_queue_permanently.py` - Queue repair tool

## Usage

The bot tracks 8 cryptocurrencies: XRP, HBAR, XLM, XDC, SUI, ONDO, ALGO, CSPR

Posts include:
- Current price and 24h change
- Price predictions using linear regression
- Transaction volume
- Top projects and research
- Social metrics (mentions, sentiment)
- Latest educational videos

## Safety Features

- Queue system prevents X API rate limits
- Auto-resume if worker stops
- Duplicate post prevention
- Multiple data source failovers
- Comprehensive error handling
