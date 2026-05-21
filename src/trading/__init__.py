"""
Paper Trading Engine - Simulates real trading without risk
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class Position:
    """Represents an open position"""
    coin_id: str
    symbol: str
    amount: float
    entry_price: float
    entry_time: str
    stop_loss: float
    take_profit: float


@dataclass
class Trade:
    """Represents a completed trade"""
    trade_id: int
    coin_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    price: float
    total_usd: float
    timestamp: str
    pnl: float = 0.0


class PaperTradingEngine:
    """Simulates cryptocurrency trading"""
    
    def __init__(self, db_path: str = "data/paper_trading.db", initial_balance: float = 10000.0):
        self.db_path = db_path
        self.initial_balance = initial_balance
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Portfolio table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                stop_loss REAL,
                take_profit REAL
            )
        """)
        
        # Trade history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                total_usd REAL NOT NULL,
                timestamp TEXT NOT NULL,
                pnl REAL DEFAULT 0.0
            )
        """)
        
        # Account balance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY,
                balance REAL NOT NULL,
                total_pnl REAL DEFAULT 0.0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Initialize account if not exists
        cursor.execute("SELECT COUNT(*) FROM account")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO account (id, balance, updated_at) VALUES (1, ?, ?)",
                (self.initial_balance, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
    
    def get_balance(self) -> float:
        """Get current cash balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM account WHERE id = 1")
        balance = cursor.fetchone()[0]
        conn.close()
        return balance
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio")
        positions = [
            {
                "id": row[0],
                "coin_id": row[1],
                "symbol": row[2],
                "amount": row[3],
                "entry_price": row[4],
                "entry_time": row[5],
                "stop_loss": row[6],
                "take_profit": row[7]
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return positions
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,))
        trades = [
            {
                "trade_id": row[0],
                "coin_id": row[1],
                "symbol": row[2],
                "side": row[3],
                "amount": row[4],
                "price": row[5],
                "total_usd": row[6],
                "timestamp": row[7],
                "pnl": row[8]
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return trades
    
    def calculate_position_size(self, coin_id: str, price: float, max_pct: float = 0.2) -> float:
        """Calculate position size based on Kelly Criterion"""
        balance = self.get_balance()
        max_amount = balance * max_pct
        
        # Calculate amount of coins
        amount = max_amount / price
        
        return amount
    
    def buy(self, coin_id: str, symbol: str, amount: float, price: float, 
            stop_loss_pct: float = 0.05, take_profit_pct: float = 0.15) -> Optional[Trade]:
        """
        Execute a buy order
        
        Args:
            coin_id: CoinGecko coin ID
            symbol: Coin symbol (e.g., BTC)
            amount: Amount of coins to buy
            price: Current price
            stop_loss_pct: Stop loss percentage (e.g., 0.05 = 5%)
            take_profit_pct: Take profit percentage (e.g., 0.15 = 15%)
        
        Returns:
            Trade object if successful, None otherwise
        """
        total_usd = amount * price
        balance = self.get_balance()
        
        if total_usd > balance:
            logger.warning(f"Insufficient balance: ${balance:.2f} < ${total_usd:.2f}")
            return None
        
        # Calculate stop loss and take profit prices
        stop_loss = price * (1 - stop_loss_pct)
        take_profit = price * (1 + take_profit_pct)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if position already exists
            cursor.execute("SELECT id, amount, entry_price FROM portfolio WHERE coin_id = ?", (coin_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Average up/down the position
                new_amount = existing[2] + amount
                avg_price = (existing[2] * existing[3] + price * amount) / new_amount
                cursor.execute(
                    "UPDATE portfolio SET amount = ?, entry_price = ?, stop_loss = ?, take_profit = ? WHERE id = ?",
                    (new_amount, avg_price, stop_loss, take_profit, existing[0])
                )
            else:
                # Create new position
                cursor.execute(
                    "INSERT INTO portfolio (coin_id, symbol, amount, entry_price, entry_time, stop_loss, take_profit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (coin_id, symbol, amount, price, datetime.now().isoformat(), stop_loss, take_profit)
                )
            
            # Update balance
            new_balance = balance - total_usd
            cursor.execute("UPDATE account SET balance = ?, total_trades = total_trades + 1, updated_at = ? WHERE id = 1",
                          (new_balance, datetime.now().isoformat()))
            
            # Record trade
            cursor.execute(
                "INSERT INTO trades (coin_id, symbol, side, amount, price, total_usd, timestamp) VALUES (?, ?, 'buy', ?, ?, ?, ?)",
                (coin_id, symbol, amount, price, total_usd, datetime.now().isoformat())
            )
            
            conn.commit()
            
            trade = Trade(
                trade_id=cursor.lastrowid,
                coin_id=coin_id,
                symbol=symbol,
                side="buy",
                amount=amount,
                price=price,
                total_usd=total_usd,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"BUY {amount:.4f} {symbol} @ ${price:.2f} = ${total_usd:.2f}")
            return trade
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error executing buy: {e}")
            return None
        finally:
            conn.close()
    
    def sell(self, coin_id: str, symbol: str, amount: float, price: float) -> Optional[Trade]:
        """
        Execute a sell order
        
        Args:
            coin_id: CoinGecko coin ID
            symbol: Coin symbol
            amount: Amount of coins to sell
            price: Current price
        
        Returns:
            Trade object if successful, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if position exists
            cursor.execute("SELECT id, amount, entry_price FROM portfolio WHERE coin_id = ?", (coin_id,))
            position = cursor.fetchone()
            
            if not position or position[2] < amount:
                logger.warning(f"Insufficient position: {position[2] if position else 0} < {amount}")
                return None
            
            total_usd = amount * price
            entry_price = position[3]
            pnl = (price - entry_price) * amount
            
            # Update position
            new_amount = position[2] - amount
            if new_amount <= 0:
                cursor.execute("DELETE FROM portfolio WHERE id = ?", (position[0],))
            else:
                cursor.execute("UPDATE portfolio SET amount = ? WHERE id = ?", (new_amount, position[0]))
            
            # Update balance
            balance = self.get_balance()
            new_balance = balance + total_usd
            cursor.execute(
                "UPDATE account SET balance = ?, total_pnl = total_pnl + ?, winning_trades = winning_trades + CASE WHEN ? > 0 THEN 1 ELSE 0 END, updated_at = ? WHERE id = 1",
                (new_balance, pnl, pnl, datetime.now().isoformat())
            )
            
            # Record trade
            cursor.execute(
                "INSERT INTO trades (coin_id, symbol, side, amount, price, total_usd, timestamp, pnl) VALUES (?, ?, 'sell', ?, ?, ?, ?, ?)",
                (coin_id, symbol, amount, price, total_usd, datetime.now().isoformat(), pnl)
            )
            
            conn.commit()
            
            trade = Trade(
                trade_id=cursor.lastrowid,
                coin_id=coin_id,
                symbol=symbol,
                side="sell",
                amount=amount,
                price=price,
                total_usd=total_usd,
                timestamp=datetime.now().isoformat(),
                pnl=pnl
            )
            
            logger.info(f"SELL {amount:.4f} {symbol} @ ${price:.2f} = ${total_usd:.2f} (PnL: ${pnl:.2f})")
            return trade
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error executing sell: {e}")
            return None
        finally:
            conn.close()
    
    def check_stop_loss_take_profit(self, coin_id: str, current_price: float) -> Optional[str]:
        """Check if stop loss or take profit is triggered"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM portfolio WHERE coin_id = ?", (coin_id,))
        position = cursor.fetchone()
        
        if not position:
            conn.close()
            return None
        
        stop_loss = position[6]
        take_profit = position[7]
        
        if current_price <= stop_loss:
            conn.close()
            return "stop_loss"
        elif current_price >= take_profit:
            conn.close()
            return "take_profit"
        
        conn.close()
        return None
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value including positions"""
        balance = self.get_balance()
        positions = self.get_positions()
        
        positions_value = sum(
            pos["amount"] * prices.get(pos["coin_id"], pos["entry_price"])
            for pos in positions
        )
        
        return balance + positions_value
    
    def get_performance_stats(self) -> Dict:
        """Get trading performance statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM account WHERE id = 1")
        account = cursor.fetchone()
        
        cursor.execute("SELECT SUM(pnl) FROM trades WHERE pnl > 0")
        total_profit = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(pnl) FROM trades WHERE pnl < 0")
        total_loss = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM trades WHERE side = 'sell'")
        total_sells = cursor.fetchone()[0]
        
        conn.close()
        
        balance = account[1]
        total_pnl = account[2]
        total_trades = account[3]
        winning_trades = account[4]
        
        win_rate = (winning_trades / total_sells * 100) if total_sells > 0 else 0
        
        return {
            "balance": balance,
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / self.initial_balance) * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "profit_factor": abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        }
    
    def format_portfolio(self, prices: Dict[str, float]) -> str:
        """Format portfolio for display"""
        positions = self.get_positions()
        balance = self.get_balance()
        stats = self.get_performance_stats()
        
        output = []
        output.append("=" * 50)
        output.append("💰 PAPER TRADING PORTFOLIO")
        output.append("=" * 50)
        
        output.append(f"\n💵 Cash Balance: ${balance:,.2f}")
        
        if positions:
            output.append("\n📊 OPEN POSITIONS:")
            total_positions_value = 0
            
            for pos in positions:
                current_price = prices.get(pos["coin_id"], pos["entry_price"])
                value = pos["amount"] * current_price
                pnl = (current_price - pos["entry_price"]) * pos["amount"]
                pnl_pct = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100
                
                total_positions_value += value
                
                emoji = "🟢" if pnl >= 0 else "🔴"
                output.append(
                    f"  {emoji} {pos['symbol']}: {pos['amount']:.4f} coins"
                    f"\n     Entry: ${pos['entry_price']:,.2f} | Current: ${current_price:,.2f}"
                    f"\n     Value: ${value:,.2f} | PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)"
                )
            
            output.append(f"\n📈 Total Positions Value: ${total_positions_value:,.2f}")
        else:
            output.append("\n📊 No open positions")
        
        total_value = balance + sum(
            pos["amount"] * prices.get(pos["coin_id"], pos["entry_price"])
            for pos in positions
        )
        
        output.append(f"\n💎 Total Portfolio Value: ${total_value:,.2f}")
        
        output.append("\n" + "-" * 50)
        output.append("📈 PERFORMANCE STATS:")
        output.append(f"  Total PnL: ${stats['total_pnl']:,.2f} ({stats['total_pnl_pct']:+.2f}%)")
        output.append(f"  Win Rate: {stats['win_rate']:.1f}%")
        output.append(f"  Total Trades: {stats['total_trades']}")
        output.append(f"  Profit Factor: {stats['profit_factor']:.2f}")
        
        output.append("=" * 50)
        
        return "\n".join(output)
