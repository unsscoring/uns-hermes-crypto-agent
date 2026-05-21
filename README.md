# 🤖 Hermes Crypto Agent

Crypto intelligence agent powered by Hermes Agent + Xiaomi MiMo model. Features real-time market analysis, paper trading, and automated trading signals.

## 🌟 Features

- **Real-time Market Data** - Live crypto prices, market cap, volume from CoinGecko
- **Technical Analysis** - RSI, MACD, Bollinger Bands, Moving Averages
- **Sentiment Analysis** - Fear & Greed Index, social sentiment tracking
- **Paper Trading** - Simulated trading with virtual portfolio
- **Trading Signals** - AI-powered buy/sell recommendations
- **Telegram Integration** - Real-time alerts and reports via Telegram
- **Scheduled Reports** - Automated market analysis every 4 hours

## 🏗️ Architecture

```
hermes-crypto-agent/
├── src/
│   ├── crawler/          # Data collection from exchanges
│   ├── analysis/         # Technical & sentiment analysis
│   ├── trading/          # Paper trading engine
│   └── agents/           # Hermes Agent integration
├── config/               # Configuration files
├── tests/                # Unit tests
└── docs/                 # Documentation
```

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/unsscoring/hermes-crypto-agent.git
cd hermes-crypto-agent
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your settings
```

### 3. Run Agent

```bash
# Run market analysis
python -m src.main analyze

# Run paper trading
python -m src.main trade

# Start Telegram bot
python -m src.main bot
```

## 📊 Trading Strategies

### 1. RSI Strategy
- Buy when RSI < 30 (oversold)
- Sell when RSI > 70 (overbought)

### 2. MACD Strategy
- Buy on MACD crossover above signal line
- Sell on MACD crossover below signal line

### 3. Bollinger Bands
- Buy when price touches lower band
- Sell when price touches upper band

### 4. Combined Strategy
- Uses weighted scoring from multiple indicators
- Higher confidence = stronger signals

## 💰 Paper Trading

The paper trading module simulates real trading without risking actual money:

- **Starting Balance**: $10,000 (configurable)
- **Position Sizing**: Kelly Criterion / Fixed Percentage
- **Risk Management**: Stop-loss, take-profit, max drawdown
- **Trade History**: Full logging of all trades
- **Performance Metrics**: PnL, Sharpe ratio, win rate

## 🔧 Configuration

Edit `config/config.yaml`:

```yaml
# Trading Settings
trading:
  initial_balance: 10000
  max_position_pct: 0.2
  stop_loss_pct: 0.05
  take_profit_pct: 0.1

# Watchlist
watchlist:
  - bitcoin
  - ethereum
  - solana
  - cardano

# Alerts
alerts:
  price_change_threshold: 5
  volume_spike_threshold: 2
```

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/crypto` | Get market overview |
| `/price <coin>` | Get specific coin price |
| `/signals` | View trading signals |
| `/portfolio` | View paper trading portfolio |
| `/trade <coin> <amount>` | Execute paper trade |
| `/history` | View trade history |

## 🛠️ Tech Stack

- **Agent Framework**: Hermes Agent
- **AI Model**: Xiaomi MiMo
- **Data Source**: CoinGecko API
- **Messaging**: Telegram Bot
- **Language**: Python 3.11+
- **Database**: SQLite (trade history)

## 📈 Performance Tracking

The agent tracks:
- Total PnL (Profit & Loss)
- Win Rate
- Sharpe Ratio
- Maximum Drawdown
- Trade History

## ⚠️ Disclaimer

This is for educational purposes only. Not financial advice. Always do your own research before trading.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
