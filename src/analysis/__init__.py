"""
Technical Analysis Module - Calculates indicators and generates signals
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from loguru import logger


class TechnicalAnalysis:
    """Technical analysis for cryptocurrency trading"""
    
    def __init__(self, config: Dict = None):
        # Default flat config
        defaults = {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "bb_period": 20,
            "bb_std": 2
        }
        
        # Handle nested YAML config (analysis.indicators.rsi.period -> rsi_period)
        if config and "indicators" in config:
            ind = config["indicators"]
            if "rsi" in ind:
                defaults["rsi_period"] = ind["rsi"].get("period", 14)
                defaults["rsi_overbought"] = ind["rsi"].get("overbought", 70)
                defaults["rsi_oversold"] = ind["rsi"].get("oversold", 30)
            if "macd" in ind:
                defaults["macd_fast"] = ind["macd"].get("fast", 12)
                defaults["macd_slow"] = ind["macd"].get("slow", 26)
                defaults["macd_signal"] = ind["macd"].get("signal", 9)
            if "bollinger" in ind:
                defaults["bb_period"] = ind["bollinger"].get("period", 20)
                defaults["bb_std"] = ind["bollinger"].get("std_dev", 2)
        elif config:
            defaults.update(config)
        
        self.config = defaults
    
    def calculate_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        """Calculate Relative Strength Index"""
        period = period or self.config["rsi_period"]
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        fast = self.config["macd_fast"]
        slow = self.config["macd_slow"]
        signal = self.config["macd_signal"]
        
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    def calculate_bollinger_bands(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        period = self.config["bb_period"]
        std_dev = self.config["bb_std"]
        
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }
    
    def calculate_ema(self, prices: pd.Series, periods: List[int]) -> Dict[str, pd.Series]:
        """Calculate Exponential Moving Averages"""
        emas = {}
        for period in periods:
            emas[f"ema_{period}"] = prices.ewm(span=period, adjust=False).mean()
        return emas
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Generate trading signals for all indicators
        
        Returns dict with signal for each indicator:
        - 'buy': positive signal
        - 'sell': negative signal  
        - 'neutral': no clear signal
        """
        if df.empty or len(df) < 50:
            logger.warning("Insufficient data for analysis")
            return {}
        
        prices = df['price']
        signals = {}
        
        # RSI Signal
        rsi = self.calculate_rsi(prices)
        current_rsi = rsi.iloc[-1]
        
        if current_rsi < self.config["rsi_oversold"]:
            rsi_signal = "buy"
        elif current_rsi > self.config["rsi_overbought"]:
            rsi_signal = "sell"
        else:
            rsi_signal = "neutral"
        
        signals["rsi"] = {
            "signal": rsi_signal,
            "value": current_rsi,
            "description": f"RSI: {current_rsi:.1f}"
        }
        
        # MACD Signal
        macd = self.calculate_macd(prices)
        current_macd = macd["macd"].iloc[-1]
        current_signal = macd["signal"].iloc[-1]
        prev_macd = macd["macd"].iloc[-2]
        prev_signal = macd["signal"].iloc[-2]
        
        if prev_macd <= prev_signal and current_macd > current_signal:
            macd_signal = "buy"
        elif prev_macd >= prev_signal and current_macd < current_signal:
            macd_signal = "sell"
        else:
            macd_signal = "neutral"
        
        signals["macd"] = {
            "signal": macd_signal,
            "value": current_macd,
            "description": f"MACD: {current_macd:.4f}"
        }
        
        # Bollinger Bands Signal
        bb = self.calculate_bollinger_bands(prices)
        current_price = prices.iloc[-1]
        upper_band = bb["upper"].iloc[-1]
        lower_band = bb["lower"].iloc[-1]
        
        if current_price <= lower_band:
            bb_signal = "buy"
        elif current_price >= upper_band:
            bb_signal = "sell"
        else:
            bb_signal = "neutral"
        
        signals["bollinger"] = {
            "signal": bb_signal,
            "value": current_price,
            "description": f"Price: ${current_price:.2f} | BB: ${lower_band:.2f}-${upper_band:.2f}"
        }
        
        # EMA Crossover Signal
        emas = self.calculate_ema(prices, [9, 21])
        ema_9 = emas["ema_9"].iloc[-1]
        ema_21 = emas["ema_21"].iloc[-1]
        prev_ema_9 = emas["ema_9"].iloc[-2]
        prev_ema_21 = emas["ema_21"].iloc[-2]
        
        if prev_ema_9 <= prev_ema_21 and ema_9 > ema_21:
            ema_signal = "buy"
        elif prev_ema_9 >= prev_ema_21 and ema_9 < ema_21:
            ema_signal = "sell"
        else:
            ema_signal = "neutral"
        
        signals["ema_crossover"] = {
            "signal": ema_signal,
            "value": ema_9,
            "description": f"EMA9: ${ema_9:.2f} | EMA21: ${ema_21:.2f}"
        }
        
        return signals
    
    def calculate_combined_score(self, signals: Dict[str, Dict]) -> Tuple[str, float]:
        """
        Calculate combined signal score from all indicators
        
        Returns:
        - signal: 'buy', 'sell', or 'neutral'
        - confidence: 0.0 to 1.0
        """
        if not signals:
            return "neutral", 0.0
        
        # Weight for each indicator
        weights = {
            "rsi": 0.25,
            "macd": 0.30,
            "bollinger": 0.25,
            "ema_crossover": 0.20
        }
        
        buy_score = 0
        sell_score = 0
        
        for indicator, data in signals.items():
            weight = weights.get(indicator, 0.25)
            signal = data["signal"]
            
            if signal == "buy":
                buy_score += weight
            elif signal == "sell":
                sell_score += weight
        
        # Determine final signal
        if buy_score > sell_score and buy_score > 0.3:
            return "buy", buy_score
        elif sell_score > buy_score and sell_score > 0.3:
            return "sell", sell_score
        else:
            return "neutral", max(buy_score, sell_score)
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Complete technical analysis
        
        Returns comprehensive analysis results
        """
        signals = self.generate_signals(df)
        combined_signal, confidence = self.calculate_combined_score(signals)
        
        return {
            "signals": signals,
            "combined_signal": combined_signal,
            "confidence": confidence,
            "timestamp": pd.Timestamp.now().isoformat()
        }
