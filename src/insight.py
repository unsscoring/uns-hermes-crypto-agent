"""
Token Usage Insight Module - Track and display token usage
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from loguru import logger


class TokenInsight:
    """Track token usage for the crypto agent"""
    
    def __init__(self, db_path: str = "data/token_usage.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for token tracking"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Token usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                model TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                tool_calls INTEGER DEFAULT 0,
                platform TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Daily summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_tool_calls INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                sessions INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_usage(self, model: str, input_tokens: int, output_tokens: int, 
                  tool_calls: int = 0, platform: str = "cli", session_id: str = None):
        """Log token usage for a request"""
        total_tokens = input_tokens + output_tokens
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert usage record
        cursor.execute("""
            INSERT INTO token_usage (session_id, model, input_tokens, output_tokens, 
                                     total_tokens, tool_calls, platform, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, model, input_tokens, output_tokens, total_tokens, 
              tool_calls, platform, timestamp))
        
        # Update daily summary
        date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO daily_summary (date, total_input_tokens, total_output_tokens, 
                                       total_tokens, total_tool_calls, sessions)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(date) DO UPDATE SET
                total_input_tokens = total_input_tokens + ?,
                total_output_tokens = total_output_tokens + ?,
                total_tokens = total_tokens + ?,
                total_tool_calls = total_tool_calls + ?,
                sessions = sessions + 1
        """, (date, input_tokens, output_tokens, total_tokens, tool_calls,
              input_tokens, output_tokens, total_tokens, tool_calls))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Logged {total_tokens} tokens for {model}")
    
    def get_usage_summary(self, days: int = 30) -> Dict:
        """Get usage summary for the specified period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Total usage
        cursor.execute("""
            SELECT 
                SUM(total_tokens) as total_tokens,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(tool_calls) as tool_calls,
                COUNT(DISTINCT session_id) as sessions
            FROM token_usage
            WHERE timestamp >= ?
        """, (start_date,))
        
        row = cursor.fetchone()
        total = {
            "total_tokens": row[0] or 0,
            "input_tokens": row[1] or 0,
            "output_tokens": row[2] or 0,
            "tool_calls": row[3] or 0,
            "sessions": row[4] or 0
        }
        
        # Per model breakdown
        cursor.execute("""
            SELECT 
                model,
                SUM(total_tokens) as tokens,
                COUNT(*) as requests
            FROM token_usage
            WHERE timestamp >= ?
            GROUP BY model
            ORDER BY tokens DESC
        """, (start_date,))
        
        models = [
            {"model": row[0], "tokens": row[1], "requests": row[2]}
            for row in cursor.fetchall()
        ]
        
        # Per platform breakdown
        cursor.execute("""
            SELECT 
                platform,
                SUM(total_tokens) as tokens,
                COUNT(*) as requests
            FROM token_usage
            WHERE timestamp >= ?
            GROUP BY platform
            ORDER BY tokens DESC
        """, (start_date,))
        
        platforms = [
            {"platform": row[0], "tokens": row[1], "requests": row[2]}
            for row in cursor.fetchall()
        ]
        
        # Daily breakdown
        cursor.execute("""
            SELECT 
                date,
                total_tokens,
                total_tool_calls
            FROM daily_summary
            WHERE date >= ?
            ORDER BY date DESC
            LIMIT 7
        """, (start_date,))
        
        daily = [
            {"date": row[0], "tokens": row[1], "tool_calls": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "period_days": days,
            "summary": total,
            "by_model": models,
            "by_platform": platforms,
            "daily": daily
        }
    
    def format_insight(self, days: int = 30) -> str:
        """Format usage insight for display"""
        data = self.get_usage_summary(days)
        summary = data["summary"]
        
        output = []
        output.append("=" * 50)
        output.append("📊 TOKEN USAGE INSIGHT")
        output.append(f"📅 Period: Last {days} days")
        output.append("=" * 50)
        
        # Summary
        output.append("\n📋 SUMMARY")
        output.append(f"  Total Tokens:    {summary['total_tokens']:>15,}")
        output.append(f"  Input Tokens:    {summary['input_tokens']:>15,}")
        output.append(f"  Output Tokens:   {summary['output_tokens']:>15,}")
        output.append(f"  Tool Calls:      {summary['tool_calls']:>15,}")
        output.append(f"  Sessions:        {summary['sessions']:>15,}")
        
        # Per Model
        if data["by_model"]:
            output.append("\n🤖 BY MODEL")
            for model in data["by_model"]:
                output.append(f"  {model['model']:<20} {model['tokens']:>12,} tokens  ({model['requests']} requests)")
        
        # Per Platform
        if data["by_platform"]:
            output.append("\n📱 BY PLATFORM")
            for platform in data["by_platform"]:
                output.append(f"  {platform['platform']:<20} {platform['tokens']:>12,} tokens  ({platform['requests']} requests)")
        
        # Daily Activity
        if data["daily"]:
            output.append("\n📅 DAILY ACTIVITY (Last 7 days)")
            for day in data["daily"]:
                bar_len = min(30, day["tokens"] // 10000) if day["tokens"] > 0 else 0
                bar = "█" * bar_len
                output.append(f"  {day['date']}  {day['tokens']:>10,} tokens  {bar}")
        
        # Estimate costs (rough estimate based on mimo-v2.5 pricing)
        output.append("\n💰 ESTIMATED COSTS")
        input_cost = summary['input_tokens'] * 0.000001  # $1 per 1M input tokens
        output_cost = summary['output_tokens'] * 0.000002  # $2 per 1M output tokens
        total_cost = input_cost + output_cost
        output.append(f"  Input:   ${input_cost:.4f}")
        output.append(f"  Output:  ${output_cost:.4f}")
        output.append(f"  Total:   ${total_cost:.4f}")
        
        output.append("=" * 50)
        
        return "\n".join(output)


# Global instance
insight = TokenInsight()


def log_token_usage(model: str, input_tokens: int, output_tokens: int, 
                    tool_calls: int = 0, platform: str = "cli"):
    """Convenience function to log token usage"""
    insight.log_usage(model, input_tokens, output_tokens, tool_calls, platform)


def get_insight(days: int = 30) -> str:
    """Convenience function to get formatted insight"""
    return insight.format_insight(days)
