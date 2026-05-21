"""
Main Entry Point - Hermes Crypto Agent
"""

import os
import sys
import yaml
import asyncio
from pathlib import Path
from loguru import logger
from datetime import datetime

from src.crawler import CryptoCrawler, fetch_all_data
from src.analysis import TechnicalAnalysis
from src.trading import PaperTradingEngine


class CryptoAgent:
    """Main crypto agent orchestrator"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.crawler = CryptoCrawler(self.config.get("coingecko", {}).get("api_key"))
        self.analyzer = TechnicalAnalysis(self.config.get("analysis", {}))
        self.trader = PaperTradingEngine(
            initial_balance=self.config.get("trading", {}).get("initial_balance", 10000)
        )
        
        # Setup logging
        logger.add(
            self.config.get("logging", {}).get("file", "logs/crypto_agent.log"),
            rotation=self.config.get("logging", {}).get("rotation", "10 MB"),
            retention=self.config.get("logging", {}).get("retention", "30 days")
        )
    
    def _load_config(self, path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {path}, using defaults")
            return {}
    
    def analyze_market(self) -> str:
        """Analyze market and generate report"""
        watchlist = self.config.get("watchlist", {}).get("coins", [])
        coin_ids = [coin["id"] for coin in watchlist]
        
        if not coin_ids:
            coin_ids = ["bitcoin", "ethereum", "solana", "cardano"]
        
        logger.info(f"Analyzing market for {len(coin_ids)} coins...")
        
        # Fetch data
        market_data = self.crawler.get_market_data(coin_ids)
        trending = self.crawler.get_trending()
        fear_greed = self.crawler.get_fear_greed_index()
        global_data = self.crawler.get_global_market_data()
        
        # Generate report
        report = []
        report.append("=" * 55)
        report.append("🤖 HERMES CRYPTO AGENT - MARKET ANALYSIS")
        report.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 55)
        
        # Global Market
        if global_data:
            report.append("\n🌍 GLOBAL MARKET")
            report.append(f"  Total Market Cap: ${global_data.get('total_market_cap_usd', 0):,.0f}")
            report.append(f"  24h Volume: ${global_data.get('total_volume_usd', 0):,.0f}")
            report.append(f"  BTC Dominance: {global_data.get('btc_dominance', 0):.1f}%")
        
        # Fear & Greed
        if fear_greed:
            value = fear_greed.get('value', 50)
            classification = fear_greed.get('classification', 'Neutral')
            
            if value < 25:
                emoji = "🟢"
            elif value < 45:
                emoji = "🟡"
            elif value < 55:
                emoji = "⚪"
            elif value < 75:
                emoji = "🟠"
            else:
                emoji = "🔴"
            
            report.append(f"\n😱 FEAR & GREED INDEX: {emoji} {value} ({classification})")
        
        # Market Data & Analysis
        if not market_data.empty:
            report.append("\n📊 MARKET DATA & SIGNALS:")
            report.append("-" * 55)
            
            for _, coin in market_data.iterrows():
                coin_id = coin['id']
                symbol = coin['symbol'].upper()
                name = coin['name']
                price = coin.get('current_price', 0)
                change_24h = coin.get('price_change_percentage_24h', 0) or 0
                change_7d = coin.get('price_change_percentage_7d_in_currency', 0) or 0
                
                # Get historical data for analysis
                history = self.crawler.get_coin_history(coin_id, days=30)
                
                if not history.empty:
                    analysis = self.analyzer.analyze(history)
                    signal = analysis.get('combined_signal', 'neutral')
                    confidence = analysis.get('confidence', 0)
                    
                    signal_emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪"
                    
                    report.append(f"\n{symbol} ({name})")
                    report.append(f"  💲 Price: ${price:,.2f}")
                    report.append(f"  📈 24h: {change_24h:+.2f}% | 7d: {change_7d:+.2f}%")
                    report.append(f"  {signal_emoji} Signal: {signal.upper()} (confidence: {confidence:.0%})")
                    
                    # Key signals
                    signals = analysis.get('signals', {})
                    for indicator, data in signals.items():
                        report.append(f"    - {indicator}: {data.get('description', '')}")
        
        # Trending
        if trending:
            report.append("\n🔥 TRENDING COINS:")
            for coin in trending[:5]:
                report.append(f"  - {coin['name']} ({coin['symbol']})")
        
        # Trading Recommendations
        report.append("\n" + "=" * 55)
        report.append("💡 TRADING RECOMMENDATIONS:")
        report.append("-" * 55)
        
        recommendations = self._generate_recommendations(market_data, fear_greed, global_data)
        for rec in recommendations:
            report.append(f"  {rec}")
        
        report.append("\n⚠️  This is not financial advice. Trade responsibly.")
        report.append("=" * 55)
        
        return "\n".join(report)
    
    def _generate_recommendations(self, market_data, fear_greed, global_data) -> list:
        """Generate trading recommendations"""
        recommendations = []
        
        # Fear & Greed based
        if fear_greed:
            value = fear_greed.get('value', 50)
            if value < 25:
                recommendations.append("🟢 EXTREME FEAR - Potential buying opportunity for quality assets")
            elif value < 45:
                recommendations.append("🟡 CAUTIOUS - Consider dollar-cost averaging into positions")
            elif value > 75:
                recommendations.append("🔴 EXTREME GREED - Consider taking profits or reducing exposure")
            else:
                recommendations.append("⚪ NEUTRAL MARKET - Good time for research and analysis")
        
        # Market trend
        if not market_data.empty:
            avg_24h = market_data['price_change_percentage_24h'].mean()
            if avg_24h > 5:
                recommendations.append("📈 STRONG UPTREND - Momentum trading opportunities")
            elif avg_24h < -5:
                recommendations.append("📉 DOWNTREND - Wait for reversal or use bearish strategies")
        
        # General advice
        recommendations.append("📊 Use stop-losses and proper position sizing")
        recommendations.append("🔍 Do your own research (DYOR)")
        recommendations.append("💰 Never invest more than you can afford to lose")
        
        return recommendations
    
    def get_portfolio(self) -> str:
        """Get current portfolio status"""
        positions = self.trader.get_positions()
        prices = {}
        
        for pos in positions:
            market_data = self.crawler.get_market_data([pos['coin_id']])
            if not market_data.empty:
                prices[pos['coin_id']] = market_data.iloc[0]['current_price']
        
        return self.trader.format_portfolio(prices)
    
    def execute_trade(self, coin_id: str, symbol: str, side: str, amount: float) -> str:
        """Execute a paper trade"""
        market_data = self.crawler.get_market_data([coin_id])
        
        if market_data.empty:
            return f"❌ Could not fetch price for {symbol}"
        
        price = market_data.iloc[0]['current_price']
        
        if side.lower() == "buy":
            trade = self.trader.buy(coin_id, symbol, amount, price)
            if trade:
                return f"✅ BUY {amount:.4f} {symbol} @ ${price:,.2f} = ${trade.total_usd:,.2f}"
            else:
                return f"❌ Failed to execute buy order"
        elif side.lower() == "sell":
            trade = self.trader.sell(coin_id, symbol, amount, price)
            if trade:
                return f"✅ SELL {amount:.4f} {symbol} @ ${price:,.2f} = ${trade.total_usd:,.2f} (PnL: ${trade.pnl:,.2f})"
            else:
                return f"❌ Failed to execute sell order"
        else:
            return f"❌ Invalid side: {side}"


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hermes Crypto Agent")
    parser.add_argument("command", choices=["analyze", "portfolio", "trade", "history"],
                       help="Command to execute")
    parser.add_argument("--coin", help="Coin ID (e.g., bitcoin)")
    parser.add_argument("--symbol", help="Coin symbol (e.g., BTC)")
    parser.add_argument("--side", choices=["buy", "sell"], help="Trade side")
    parser.add_argument("--amount", type=float, help="Trade amount")
    parser.add_argument("--config", default="config/config.yaml", help="Config file path")
    
    args = parser.parse_args()
    
    agent = CryptoAgent(args.config)
    
    if args.command == "analyze":
        print(agent.analyze_market())
    elif args.command == "portfolio":
        print(agent.get_portfolio())
    elif args.command == "trade":
        if not all([args.coin, args.symbol, args.side, args.amount]):
            print("❌ Trade requires: --coin, --symbol, --side, --amount")
            sys.exit(1)
        print(agent.execute_trade(args.coin, args.symbol, args.side, args.amount))
    elif args.command == "history":
        trades = agent.trader.get_trade_history()
        for trade in trades:
            print(f"{trade['timestamp']} | {trade['side'].upper()} {trade['amount']:.4f} {trade['symbol']} @ ${trade['price']:,.2f} | PnL: ${trade['pnl']:,.2f}")


if __name__ == "__main__":
    main()
