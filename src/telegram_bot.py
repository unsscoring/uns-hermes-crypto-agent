"""
Telegram Bot Handler for Hermes Crypto Agent
"""

import asyncio
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from src.crawler import CryptoCrawler
from src.analysis import TechnicalAnalysis
from src.trading import PaperTradingEngine
from src.token_tracker import TokenTracker
from src.ai_analysis import MiMoAnalyzer

logger = logging.getLogger(__name__)


class CryptoTelegramBot:
    """Telegram bot for crypto agent"""
    
    def __init__(self, token: str, allowed_users: list = None):
        self.token = token
        self.allowed_users = allowed_users or []
        self.crawler = CryptoCrawler()
        self.analyzer = TechnicalAnalysis()
        self.trader = PaperTradingEngine()
        self.tracker = TokenTracker()
        self.ai = MiMoAnalyzer()  # MiMo AI Analyzer
        
        # Default watchlist
        self.watchlist = ["bitcoin", "ethereum", "solana", "cardano", "ripple"]
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        if not self.allowed_users:
            return True  # Allow all if no restriction
        return user_id in self.allowed_users
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied. You are not authorized.")
            return
        
        welcome = """
🤖 *Hermes Crypto Agent*

Selamat datang! Saya adalah AI agent untuk analisis crypto dan paper trading.

*Commands:*
/crypto - Analisis market lengkap
/price <coin> - Harga spesifik (contoh: /price bitcoin)
/portfolio - Status portfolio paper trading
/trade <coin> <side> <amount> - Paper trade
/signals - Trading signals
/insight - Token usage
/help - Bantuan

*Contoh:*
/price bitcoin
/trade bitcoin buy 0.01
        """
        
        await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    
    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📖 *Command Reference*

*Market Analysis:*
/crypto - Analisis market lengkap dengan signals
/price <coin> - Harga dan info coin

*Paper Trading:*
/portfolio - Lihat portfolio dan PnL
/trade <coin> <buy/sell> <amount> - Eksekusi trade
/history - History trade

*Info:*
/signals - Trading signals semua coin
/insight - Token usage

*Watchlist:*
BTC, ETH, SOL, ADA, XRP
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def crypto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /crypto command - Full market analysis with AI"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        await update.message.reply_text("⏳ Fetching market data & analyzing with AI...")
        
        try:
            # Fetch data
            market_data = self.crawler.get_market_data(self.watchlist)
            fear_greed = self.crawler.get_fear_greed_index()
            trending = self.crawler.get_trending()
            
            # Get technical analysis for each coin
            analysis_results = []
            for coin_id in self.watchlist:
                history = self.crawler.get_coin_history(coin_id, days=30)
                if not history.empty:
                    analysis = self.analyzer.analyze(history)
                    market_coin = market_data[market_data['id'] == coin_id]
                    
                    if not market_coin.empty:
                        analysis_results.append({
                            'coin': coin_id,
                            'symbol': market_coin.iloc[0]['symbol'].upper(),
                            'price': market_coin.iloc[0].get('current_price', 0),
                            'signal': analysis.get('combined_signal', 'neutral'),
                            'confidence': analysis.get('confidence', 0),
                            'signals': analysis.get('signals', {})
                        })
            
            # AI Analysis with MiMo
            market_dict = {
                'coins': market_data.to_dict('records') if not market_data.empty else [],
                'fear_greed': fear_greed,
                'trending': trending
            }
            
            ai_analysis = self.ai.analyze_market(market_dict, fear_greed)
            
            # Build report
            report = []
            report.append("🤖 *AI-POWERED CRYPTO ANALYSIS*\n")
            
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
                
                report.append(f"*Fear & Greed:* {emoji} {value} ({classification})\n")
            
            # Signals summary
            report.append("*📊 SIGNALS SUMMARY:*")
            for result in analysis_results:
                signal_emoji = "🟢" if result['signal'] == "buy" else "🔴" if result['signal'] == "sell" else "⚪"
                report.append(
                    f"{signal_emoji} *{result['symbol']}*: ${result['price']:,.2f} | {result['signal'].upper()} ({result['confidence']:.0%})"
                )
            
            # AI Insights
            report.append("\n*🧠 AI INSIGHTS (MiMo):*")
            report.append(ai_analysis[:1500])  # Telegram limit
            
            # Log usage
            self.tracker.log_usage(
                tokens=2000,  # Estimate for AI call
                model="mimo-v2.5",
                platform="telegram",
                description="AI crypto analysis"
            )
            
            await update.message.reply_text("\n".join(report), parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in /crypto: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /price <coin>\nContoh: /price bitcoin"
            )
            return
        
        coin_id = context.args[0].lower()
        
        await update.message.reply_text(f"⏳ Fetching {coin_id} data...")
        
        try:
            market_data = self.crawler.get_market_data([coin_id])
            
            if market_data.empty:
                await update.message.reply_text(f"❌ Coin '{coin_id}' not found.")
                return
            
            coin = market_data.iloc[0]
            symbol = coin['symbol'].upper()
            name = coin['name']
            price = coin.get('current_price', 0)
            change_24h = coin.get('price_change_percentage_24h', 0) or 0
            change_7d = coin.get('price_change_percentage_7d_in_currency', 0) or 0
            market_cap = coin.get('market_cap', 0)
            volume = coin.get('total_volume', 0)
            
            # Analysis
            history = self.crawler.get_coin_history(coin_id, days=30)
            signal_text = ""
            
            if not history.empty:
                analysis = self.analyzer.analyze(history)
                signal = analysis.get('combined_signal', 'neutral')
                confidence = analysis.get('confidence', 0)
                
                signal_emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪"
                signal_text = f"\n\n*Signal:* {signal_emoji} {signal.upper()} (confidence: {confidence:.0%})"
            
            report = f"""
*{name} ({symbol})*

💲 *Price:* ${price:,.2f}
📈 *24h:* {change_24h:+.2f}%
📈 *7d:* {change_7d:+.2f}%
💰 *Market Cap:* ${market_cap:,.0f}
📊 *Volume:* ${volume:,.0f}
{signal_text}
            """
            
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in /price: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        try:
            positions = self.trader.get_positions()
            balance = self.trader.get_balance()
            stats = self.trader.get_performance_stats()
            
            report = []
            report.append("💰 *PAPER TRADING PORTFOLIO*\n")
            report.append(f"*Cash Balance:* ${balance:,.2f}")
            
            if positions:
                report.append("\n*📊 POSITIONS:*")
                total_value = 0
                
                for pos in positions:
                    # Get current price
                    market_data = self.crawler.get_market_data([pos['coin_id']])
                    
                    if not market_data.empty:
                        current_price = market_data.iloc[0]['current_price']
                        value = pos['amount'] * current_price
                        pnl = (current_price - pos['entry_price']) * pos['amount']
                        pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                        
                        total_value += value
                        
                        emoji = "🟢" if pnl >= 0 else "🔴"
                        report.append(
                            f"{emoji} *{pos['symbol']}*: {pos['amount']:.4f} coins"
                            f"\n   Entry: ${pos['entry_price']:,.2f} → Now: ${current_price:,.2f}"
                            f"\n   PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)"
                        )
                
                report.append(f"\n*Total Value:* ${balance + total_value:,.2f}")
            else:
                report.append("\n*No open positions*")
            
            # Stats
            report.append("\n*📈 STATS:*")
            report.append(f"Win Rate: {stats['win_rate']:.1f}%")
            report.append(f"Total PnL: ${stats['total_pnl']:,.2f}")
            
            await update.message.reply_text("\n".join(report), parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in /portfolio: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trade command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        if len(context.args) != 3:
            await update.message.reply_text(
                "Usage: /trade <coin> <buy/sell> <amount>\n"
                "Contoh: /trade bitcoin buy 0.01"
            )
            return
        
        coin_id = context.args[0].lower()
        side = context.args[1].lower()
        
        try:
            amount = float(context.args[2])
        except ValueError:
            await update.message.reply_text("❌ Amount harus angka.")
            return
        
        if side not in ['buy', 'sell']:
            await update.message.reply_text("❌ Side harus 'buy' atau 'sell'.")
            return
        
        await update.message.reply_text(f"⏳ Executing {side} {amount} {coin_id}...")
        
        try:
            # Get current price
            market_data = self.crawler.get_market_data([coin_id])
            
            if market_data.empty:
                await update.message.reply_text(f"❌ Coin '{coin_id}' not found.")
                return
            
            coin = market_data.iloc[0]
            symbol = coin['symbol'].upper()
            price = coin['current_price']
            
            # Execute trade
            if side == 'buy':
                trade = self.trader.buy(coin_id, symbol, amount, price)
            else:
                trade = self.trader.sell(coin_id, symbol, amount, price)
            
            if trade:
                if side == 'buy':
                    msg = f"""
✅ *BUY EXECUTED*

{symbol}: {amount:.4f} coins
Price: ${price:,.2f}
Total: ${trade.total_usd:,.2f}
                    """
                else:
                    msg = f"""
✅ *SELL EXECUTED*

{symbol}: {amount:.4f} coins
Price: ${price:,.2f}
Total: ${trade.total_usd:,.2f}
PnL: ${trade.pnl:,.2f}
                    """
                
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text("❌ Trade failed. Check your balance/position.")
            
        except Exception as e:
            logger.error(f"Error in /trade: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        await update.message.reply_text("⏳ Analyzing signals...")
        
        try:
            report = ["📡 *TRADING SIGNALS*\n"]
            
            for coin_id in self.watchlist:
                market_data = self.crawler.get_market_data([coin_id])
                
                if not market_data.empty:
                    coin = market_data.iloc[0]
                    symbol = coin['symbol'].upper()
                    price = coin.get('current_price', 0)
                    
                    history = self.crawler.get_coin_history(coin_id, days=30)
                    
                    if not history.empty:
                        analysis = self.analyzer.analyze(history)
                        signal = analysis.get('combined_signal', 'neutral')
                        confidence = analysis.get('confidence', 0)
                        
                        signal_emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪"
                        
                        report.append(
                            f"{signal_emoji} *{symbol}*: ${price:,.2f}\n"
                            f"   Signal: {signal.upper()} ({confidence:.0%})"
                        )
            
            await update.message.reply_text("\n".join(report), parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in /signals: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def insight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /insight command"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        try:
            quota = self.tracker.get_quota()
            
            if not quota:
                await update.message.reply_text("❌ No token data configured.")
                return
            
            total = quota["total_tokens"]
            used = quota["used_tokens"]
            remaining = quota["remaining_tokens"]
            pct = quota["usage_percentage"]
            
            # Progress bar
            bar_length = 20
            filled = int(bar_length * pct / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            # Status
            if pct < 50:
                status = "🟢"
            elif pct < 75:
                status = "🟡"
            elif pct < 90:
                status = "🟠"
            else:
                status = "🔴"
            
            report = f"""
📊 *TOKEN USAGE*

{status} Status: {'Healthy' if pct < 75 else 'Warning' if pct < 90 else 'Critical'}

📈 Usage: {pct:.1f}%
`[{bar}]`

*Total:*     {total:,}
*Used:*      {used:,}
*Remaining:* {remaining:,}

📅 Last Updated: {quota['last_updated'][:10]}
            """
            
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in /insight: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command - AI analysis for specific coin"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /analyze <coin>\nContoh: /analyze bitcoin"
            )
            return
        
        coin_id = context.args[0].lower()
        
        await update.message.reply_text(f"🧠 Analyzing {coin_id} with MiMo AI...")
        
        try:
            # Get market data
            market_data = self.crawler.get_market_data([coin_id])
            
            if market_data.empty:
                await update.message.reply_text(f"❌ Coin '{coin_id}' not found.")
                return
            
            coin = market_data.iloc[0]
            symbol = coin['symbol'].upper()
            name = coin['name']
            price = coin.get('current_price', 0)
            change_24h = coin.get('price_change_percentage_24h', 0) or 0
            change_7d = coin.get('price_change_percentage_7d_in_currency', 0) or 0
            high_24h = coin.get('high_24h', 0)
            low_24h = coin.get('low_24h', 0)
            volume = coin.get('total_volume', 0)
            
            # Get technical analysis
            history = self.crawler.get_coin_history(coin_id, days=30)
            technical_signals = {}
            
            if not history.empty:
                analysis = self.analyzer.analyze(history)
                technical_signals = analysis.get('signals', {})
                technical_signals['combined_signal'] = analysis.get('combined_signal', 'neutral')
                technical_signals['confidence'] = analysis.get('confidence', 0)
            
            # AI Analysis
            price_data = {
                'current_price': price,
                'price_change_24h': change_24h,
                'price_change_7d': change_7d,
                'high_24h': high_24h,
                'low_24h': low_24h,
                'volume': volume
            }
            
            ai_analysis = self.ai.analyze_coin(name, price_data, technical_signals)
            
            # Build report
            report = []
            report.append(f"🧠 *AI ANALYSIS: {name} ({symbol})*\n")
            
            # Basic info
            report.append(f"*Current Price:* ${price:,.2f}")
            report.append(f"*24h Change:* {change_24h:+.2f}%")
            report.append(f"*7d Change:* {change_7d:+.2f}%")
            report.append(f"*24h Range:* ${low_24h:,.2f} - ${high_24h:,.2f}")
            report.append(f"*Volume:* ${volume:,.0f}")
            
            # Technical signals
            signal = technical_signals.get('combined_signal', 'neutral')
            confidence = technical_signals.get('confidence', 0)
            signal_emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪"
            report.append(f"\n*Technical Signal:* {signal_emoji} {signal.upper()} ({confidence:.0%})")
            
            # AI Insights
            report.append("\n*🧠 MiMo AI INSIGHTS:*")
            report.append(ai_analysis[:2000])  # Telegram limit
            
            # Log usage
            self.tracker.log_usage(
                tokens=1500,  # Estimate for AI call
                model="mimo-v2.5",
                platform="telegram",
                description=f"AI analysis for {coin_id}"
            )
            
            await update.message.reply_text("\n".join(report), parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in /analyze: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages - AI chat"""
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        message = update.message.text
        
        # Use MiMo for chat
        await update.message.reply_text("🤔 Thinking...")
        
        try:
            response = self.ai.chat(message)
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    def setup_handlers(self, app: Application):
        """Setup all command handlers"""
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help_cmd))
        app.add_handler(CommandHandler("crypto", self.crypto))
        app.add_handler(CommandHandler("analyze", self.analyze))
        app.add_handler(CommandHandler("price", self.price))
        app.add_handler(CommandHandler("portfolio", self.portfolio))
        app.add_handler(CommandHandler("trade", self.trade))
        app.add_handler(CommandHandler("signals", self.signals))
        app.add_handler(CommandHandler("insight", self.insight))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def set_commands(self, app: Application):
        """Set bot commands menu"""
        commands = [
            BotCommand("start", "Start bot"),
            BotCommand("help", "Show help"),
            BotCommand("crypto", "AI market analysis"),
            BotCommand("analyze", "AI analysis for specific coin"),
            BotCommand("price", "Coin price (e.g., /price bitcoin)"),
            BotCommand("portfolio", "Paper trading portfolio"),
            BotCommand("trade", "Execute trade (e.g., /trade bitcoin buy 0.01)"),
            BotCommand("signals", "Trading signals"),
            BotCommand("insight", "Token usage"),
        ]
        
        await app.bot.set_my_commands(commands)
        logger.info("Bot commands set successfully")
    
    def run(self):
        """Run the bot"""
        app = Application.builder().token(self.token).build()
        
        # Setup handlers
        self.setup_handlers(app)
        
        # Post init - set commands
        app.post_init = self.set_commands
        
        # Start bot
        logger.info("Starting Crypto Telegram Bot...")
        app.run_polling(drop_pending_updates=True)


def main():
    """Main entry point"""
    import yaml
    from pathlib import Path
    
    # Load config
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {}
    
    # Get token from env or config
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN") or config.get("telegram", {}).get("bot_token")
    
    if not token:
        print("❌ No Telegram bot token configured!")
        print("Set TELEGRAM_BOT_TOKEN env var or configure in config.yaml")
        return
    
    # Get allowed users
    allowed_users = config.get("telegram", {}).get("allowed_users", [])
    
    # Create and run bot
    bot = CryptoTelegramBot(token=token, allowed_users=allowed_users)
    bot.run()


if __name__ == "__main__":
    main()
