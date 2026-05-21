"""
AI Analysis Module - Uses Xiaomi MiMo for intelligent crypto analysis
"""

import json
import requests
from typing import Dict, List, Optional
from loguru import logger


class MiMoAnalyzer:
    """AI-powered crypto analysis using Xiaomi MiMo"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        # Load from env or use default
        import os
        self.api_key = api_key or os.getenv("XIAOMI_API_KEY", "tp-s141ux797whq00jxlknzb8w6ezmtlj9s45kgofvmgk58o9a7")
        self.base_url = base_url or os.getenv("XIAOMI_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
        self.model = "mimo-v2.5"
    
    def _call_mimo(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        """Call MiMo API"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"MiMo API error: {e}")
            return f"Error calling MiMo: {str(e)}"
    
    def analyze_market(self, market_data: Dict, fear_greed: Dict = None) -> str:
        """AI analysis of market conditions"""
        
        system_prompt = """You are a professional crypto market analyst. 
Analyze the provided market data and give clear, actionable insights.
Use emoji for better readability. Be concise but informative.
Always include risk disclaimer at the end."""

        # Format market data
        coins_text = ""
        if "coins" in market_data:
            for coin in market_data["coins"]:
                coins_text += f"""
- {coin.get('name', 'N/A')} ({coin.get('symbol', 'N/A')}):
  Price: ${coin.get('current_price', 0):,.2f}
  24h Change: {coin.get('price_change_24h', 0):+.2f}%
  Market Cap: ${coin.get('market_cap', 0):,.0f}
"""
        
        fng_text = ""
        if fear_greed:
            fng_text = f"\nFear & Greed Index: {fear_greed.get('value', 'N/A')} ({fear_greed.get('classification', 'N/A')})"
        
        user_prompt = f"""Analyze this crypto market data:

{coins_text}
{fng_text}

Provide:
1. Market Overview (1-2 sentences)
2. Key Observations
3. Trading Opportunities
4. Risk Assessment
5. Short-term Outlook (24-48h)"""

        return self._call_mimo(system_prompt, user_prompt)
    
    def analyze_coin(self, coin_name: str, price_data: Dict, technical_signals: Dict) -> str:
        """AI analysis for specific coin"""
        
        system_prompt = """You are a crypto trading expert. Analyze the coin data and provide:
- Clear BUY/SELL/HOLD recommendation
- Entry/exit price suggestions
- Risk management tips
- Key support/resistance levels
Be specific with numbers and percentages."""

        user_prompt = f"""Analyze {coin_name}:

Current Price: ${price_data.get('current_price', 0):,.2f}
24h Change: {price_data.get('price_change_24h', 0):+.2f}%
7d Change: {price_data.get('price_change_7d', 0):+.2f}%
24h High: ${price_data.get('high_24h', 0):,.2f}
24h Low: ${price_data.get('low_24h', 0):,.2f}
Volume: ${price_data.get('volume', 0):,.0f}

Technical Signals:
- RSI: {technical_signals.get('rsi', {}).get('value', 'N/A')} ({technical_signals.get('rsi', {}).get('signal', 'N/A')})
- MACD: {technical_signals.get('macd', {}).get('signal', 'N/A')}
- Bollinger: {technical_signals.get('bollinger', {}).get('signal', 'N/A')}
- EMA Crossover: {technical_signals.get('ema_crossover', {}).get('signal', 'N/A')}
- Combined Signal: {technical_signals.get('combined_signal', 'N/A')} (confidence: {technical_signals.get('confidence', 0):.0%})

Provide detailed analysis with specific price targets."""

        return self._call_mimo(system_prompt, user_prompt)
    
    def generate_trading_signals(self, analysis_results: List[Dict]) -> str:
        """Generate AI-powered trading signals"""
        
        system_prompt = """You are a trading signal generator. Based on the analysis, provide:
1. TOP 3 BUY signals with entry prices and stop-loss
2. TOP 3 SELL signals with reasoning
3. COINS TO WATCH for potential opportunities
4. RISK WARNING for any concerning patterns

Format with clear emoji and structure."""

        # Format analysis results
        results_text = ""
        for result in analysis_results:
            coin = result.get('coin', 'Unknown')
            signal = result.get('signal', 'neutral')
            confidence = result.get('confidence', 0)
            price = result.get('price', 0)
            
            emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪"
            results_text += f"\n{emoji} {coin}: ${price:,.2f} | Signal: {signal.upper()} | Confidence: {confidence:.0%}"
        
        user_prompt = f"""Generate trading signals based on this analysis:

{results_text}

Provide actionable signals with specific price levels and risk management."""

        return self._call_mimo(system_prompt, user_prompt)
    
    def explain_signal(self, coin: str, signal: str, indicators: Dict) -> str:
        """Explain a trading signal in simple terms"""
        
        system_prompt = """You are a friendly crypto educator. Explain trading signals in simple, easy-to-understand language. Use analogies and examples. Be encouraging but realistic about risks."""

        user_prompt = f"""Explain why {coin} has a {signal.upper()} signal:

Indicators:
- RSI: {indicators.get('rsi', {}).get('description', 'N/A')}
- MACD: {indicators.get('macd', {}).get('description', 'N/A')}
- Bollinger Bands: {indicators.get('bollinger', {}).get('description', 'N/A')}
- EMA Crossover: {indicators.get('ema_crossover', {}).get('description', 'N/A')}

Explain in simple terms:
1. What does this signal mean?
2. Why did these indicators trigger this signal?
3. What should a trader do?
4. What are the risks?"""

        return self._call_mimo(system_prompt, user_prompt, max_tokens=1000)
    
    def summarize_portfolio(self, portfolio: Dict, market_data: Dict) -> str:
        """AI summary of portfolio performance"""
        
        system_prompt = """You are a portfolio manager. Analyze the portfolio and provide:
- Performance summary
- Diversification assessment
- Recommendations for rebalancing
- Risk exposure analysis
Be specific with numbers and percentages."""

        # Format portfolio
        positions_text = ""
        for pos in portfolio.get('positions', []):
            current_price = market_data.get(pos['coin_id'], {}).get('price', pos['entry_price'])
            pnl = (current_price - pos['entry_price']) * pos['amount']
            pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
            
            positions_text += f"""
- {pos['symbol']}: {pos['amount']:.4f} coins
  Entry: ${pos['entry_price']:,.2f} → Now: ${current_price:,.2f}
  PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)
"""
        
        user_prompt = f"""Analyze this portfolio:

Cash Balance: ${portfolio.get('balance', 0):,.2f}
Total Value: ${portfolio.get('total_value', 0):,.2f}
Total PnL: ${portfolio.get('total_pnl', 0):,.2f}

Positions:
{positions_text}

Provide portfolio analysis and recommendations."""

        return self._call_mimo(system_prompt, user_prompt)
    
    def generate_market_report(self, all_data: Dict) -> str:
        """Generate comprehensive market report"""
        
        system_prompt = """You are a senior crypto market analyst. Generate a comprehensive market report that includes:
1. Executive Summary
2. Market Overview
3. Top Performers Analysis
4. Underperformers Analysis
5. Technical Outlook
6. Fundamental Factors
7. Risk Assessment
8. Action Items

Use professional language with clear sections. Include specific data points."""

        # Format all data
        market_text = json.dumps(all_data, indent=2, default=str)
        
        user_prompt = f"""Generate a comprehensive crypto market report based on this data:

{market_text}

Provide a professional market report suitable for investors."""

        return self._call_mimo(system_prompt, user_prompt, max_tokens=3000)
    
    def chat(self, message: str, context: str = None) -> str:
        """General chat about crypto"""
        
        system_prompt = """You are a helpful crypto assistant named Hermes Crypto Agent. 
You can discuss:
- Market analysis and trends
- Trading strategies
- Technical analysis concepts
- Portfolio management
- Risk management
- Crypto news and events

Be helpful, informative, and always remind users about investment risks.
You can use Indonesian if the user writes in Indonesian."""

        user_prompt = message
        if context:
            user_prompt = f"Context: {context}\n\nUser question: {message}"
        
        return self._call_mimo(system_prompt, user_prompt, max_tokens=1500)


# Global instance
mimo = MiMoAnalyzer()


def analyze_with_ai(market_data: Dict, fear_greed: Dict = None) -> str:
    """Convenience function for AI market analysis"""
    return mimo.analyze_market(market_data, fear_greed)


def get_ai_signal(coin: str, price_data: Dict, technical_signals: Dict) -> str:
    """Convenience function for AI coin analysis"""
    return mimo.analyze_coin(coin, price_data, technical_signals)


def chat_about_crypto(message: str) -> str:
    """Convenience function for crypto chat"""
    return mimo.chat(message)
