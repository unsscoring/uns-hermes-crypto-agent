"""
Token Usage Tracker - Monitors Xiaomi MiMo token consumption
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from loguru import logger


class TokenTracker:
    """Track Xiaomi MiMo token usage with persistent storage"""
    
    def __init__(self, db_path: str = "data/token_tracker.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Token quota table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_quota (
                id INTEGER PRIMARY KEY,
                provider TEXT NOT NULL DEFAULT 'xiaomi_mimo',
                total_tokens INTEGER NOT NULL,
                used_tokens INTEGER NOT NULL DEFAULT 0,
                remaining_tokens INTEGER GENERATED ALWAYS AS (total_tokens - used_tokens) STORED,
                last_updated TEXT NOT NULL,
                notes TEXT
            )
        """)
        
        # Usage history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL DEFAULT 'xiaomi_mimo',
                session_tokens INTEGER NOT NULL,
                model TEXT,
                platform TEXT,
                description TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Daily usage summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                date TEXT PRIMARY KEY,
                provider TEXT NOT NULL DEFAULT 'xiaomi_mimo',
                total_tokens INTEGER NOT NULL DEFAULT 0,
                requests INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def set_quota(self, total_tokens: int, used_tokens: int, notes: str = "") -> Dict:
        """Set initial token quota"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Check if quota exists
        cursor.execute("SELECT id FROM token_quota WHERE provider = 'xiaomi_mimo'")
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE token_quota 
                SET total_tokens = ?, used_tokens = ?, last_updated = ?, notes = ?
                WHERE provider = 'xiaomi_mimo'
            """, (total_tokens, used_tokens, now, notes))
        else:
            cursor.execute("""
                INSERT INTO token_quota (provider, total_tokens, used_tokens, last_updated, notes)
                VALUES ('xiaomi_mimo', ?, ?, ?, ?)
            """, (total_tokens, used_tokens, now, notes))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Token quota set: {total_tokens:,} total, {used_tokens:,} used")
        
        return self.get_quota()
    
    def get_quota(self) -> Dict:
        """Get current token quota"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM token_quota WHERE provider = 'xiaomi_mimo'")
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                "provider": row[1],
                "total_tokens": row[2],
                "used_tokens": row[3],
                "remaining_tokens": row[4],
                "usage_percentage": (row[3] / row[2] * 100) if row[2] > 0 else 0,
                "last_updated": row[5],
                "notes": row[6]
            }
        
        return {}
    
    def log_usage(self, tokens: int, model: str = "mimo-v2.5", 
                  platform: str = "cli", description: str = "") -> Dict:
        """Log token usage for a request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        date = datetime.now().strftime("%Y-%m-%d")
        
        # Log to history
        cursor.execute("""
            INSERT INTO usage_history (provider, session_tokens, model, platform, description, timestamp)
            VALUES ('xiaomi_mimo', ?, ?, ?, ?, ?)
        """, (tokens, model, platform, description, now))
        
        # Update daily summary
        cursor.execute("""
            INSERT INTO daily_usage (date, provider, total_tokens, requests)
            VALUES (?, 'xiaomi_mimo', ?, 1)
            ON CONFLICT(date) DO UPDATE SET
                total_tokens = total_tokens + ?,
                requests = requests + 1
        """, (date, tokens, tokens))
        
        # Update quota
        cursor.execute("""
            UPDATE token_quota 
            SET used_tokens = used_tokens + ?, last_updated = ?
            WHERE provider = 'xiaomi_mimo'
        """, (tokens, now))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Logged {tokens:,} tokens ({model})")
        
        return self.get_quota()
    
    def get_usage_history(self, days: int = 30) -> list:
        """Get usage history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT * FROM usage_history 
            WHERE timestamp >= ? 
            ORDER BY timestamp DESC
        """, (start_date,))
        
        history = [
            {
                "id": row[0],
                "provider": row[1],
                "tokens": row[2],
                "model": row[3],
                "platform": row[4],
                "description": row[5],
                "timestamp": row[6]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return history
    
    def get_daily_usage(self, days: int = 30) -> list:
        """Get daily usage summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT * FROM daily_usage 
            WHERE date >= ? 
            ORDER BY date DESC
        """, (start_date,))
        
        daily = [
            {
                "date": row[0],
                "provider": row[1],
                "tokens": row[2],
                "requests": row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return daily
    
    def format_quota_report(self) -> str:
        """Format token quota report"""
        quota = self.get_quota()
        
        if not quota:
            return "❌ No token quota configured. Run: set_quota()"
        
        total = quota["total_tokens"]
        used = quota["used_tokens"]
        remaining = quota["remaining_tokens"]
        pct = quota["usage_percentage"]
        
        # Progress bar
        bar_length = 30
        filled = int(bar_length * pct / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Status emoji
        if pct < 50:
            status = "🟢"
        elif pct < 75:
            status = "🟡"
        elif pct < 90:
            status = "🟠"
        else:
            status = "🔴"
        
        output = []
        output.append("=" * 55)
        output.append(f"📊 XIAOMI MIMO TOKEN USAGE")
        output.append("=" * 55)
        output.append(f"\n{status} Status: {'Healthy' if pct < 75 else 'Warning' if pct < 90 else 'Critical'}")
        output.append(f"\n📈 Usage: {pct:.1f}%")
        output.append(f"   [{bar}]")
        
        output.append(f"\n💰 Token Summary:")
        output.append(f"   Total:     {total:>15,}")
        output.append(f"   Used:      {used:>15,}")
        output.append(f"   Remaining: {remaining:>15,}")
        
        output.append(f"\n📅 Last Updated: {quota['last_updated']}")
        
        if quota.get("notes"):
            output.append(f"📝 Notes: {quota['notes']}")
        
        # Daily usage
        daily = self.get_daily_usage(7)
        if daily:
            output.append("\n" + "-" * 55)
            output.append("📊 DAILY USAGE (Last 7 days):")
            
            for day in daily:
                bar_len = min(20, day["tokens"] // 100000) if day["tokens"] > 0 else 0
                day_bar = "▓" * bar_len
                output.append(f"   {day['date']}  {day['tokens']:>12,} tokens  ({day['requests']} reqs)  {day_bar}")
        
        output.append("=" * 55)
        
        return "\n".join(output)
    
    def estimate_remaining_days(self, avg_daily_usage: float = None) -> float:
        """Estimate how many days until tokens run out"""
        quota = self.get_quota()
        
        if not quota or quota["remaining_tokens"] <= 0:
            return 0
        
        if avg_daily_usage is None:
            # Calculate from last 7 days
            daily = self.get_daily_usage(7)
            if daily:
                avg_daily_usage = sum(d["tokens"] for d in daily) / len(daily)
            else:
                return -1  # Unknown
        
        if avg_daily_usage <= 0:
            return -1
        
        return quota["remaining_tokens"] / avg_daily_usage


# Global instance
tracker = TokenTracker()


def set_initial_quota():
    """Set initial quota based on user's data"""
    return tracker.set_quota(
        total_tokens=700_000_000,  # 700 jt
        used_tokens=460_000_000,   # 460an jt
        notes="Initial setup - User reported ~460M used"
    )


def get_usage_report() -> str:
    """Get formatted usage report"""
    return tracker.format_quota_report()


def log_current_session(tokens: int, description: str = "Hermes session"):
    """Log current session token usage"""
    return tracker.log_usage(tokens=tokens, description=description)


if __name__ == "__main__":
    # Initialize with user's data
    print("Initializing token tracker...")
    set_initial_quota()
    print("\n" + get_usage_report())
