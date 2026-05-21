"""
Crypto Data Crawler - Fetches real-time market data
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger


class CryptoCrawler:
    """Fetches cryptocurrency market data from CoinGecko API"""
    
    def __init__(self, api_key: str = None):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.headers = {"accept": "application/json"}
        if api_key:
            self.headers["x-cg-demo-api-key"] = api_key
    
    def get_market_data(self, coin_ids: List[str], vs_currency: str = "usd") -> pd.DataFrame:
        """
        Get current market data for specified coins
        
        Returns DataFrame with columns:
        - id, symbol, name, current_price, market_cap, total_volume
        - price_change_24h, price_change_percentage_24h
        - price_change_percentage_7d_in_currency
        - high_24h, low_24h, ath, atl
        """
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "ids": ",".join(coin_ids),
            "order": "market_cap_desc",
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                logger.warning("No market data returned")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['timestamp'] = datetime.now().isoformat()
            
            logger.info(f"Fetched market data for {len(df)} coins")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return pd.DataFrame()
    
    def get_coin_history(self, coin_id: str, days: int = 30) -> pd.DataFrame:
        """
        Get historical price data for a coin
        
        Returns DataFrame with columns:
        - timestamp, price, market_cap, total_volume
        """
        url = f"{self.base_url}/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            volumes = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
            market_caps = pd.DataFrame(data['market_caps'], columns=['timestamp', 'market_cap'])
            
            df = prices.merge(volumes, on='timestamp').merge(market_caps, on='timestamp')
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            logger.info(f"Fetched {len(df)} days of history for {coin_id}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching history for {coin_id}: {e}")
            return pd.DataFrame()
    
    def get_trending(self) -> List[Dict]:
        """Get trending coins"""
        url = f"{self.base_url}/search/trending"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            trending = [
                {
                    "name": coin["item"]["name"],
                    "symbol": coin["item"]["symbol"],
                    "market_cap_rank": coin["item"].get("market_cap_rank"),
                    "price_btc": coin["item"].get("price_btc")
                }
                for coin in data.get("coins", [])
            ]
            
            logger.info(f"Found {len(trending)} trending coins")
            return trending
            
        except Exception as e:
            logger.error(f"Error fetching trending: {e}")
            return []
    
    def get_fear_greed_index(self) -> Dict:
        """Get Fear & Greed Index"""
        url = "https://api.alternative.me/fng/"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                fng = data["data"][0]
                result = {
                    "value": int(fng["value"]),
                    "classification": fng["value_classification"],
                    "timestamp": fng["timestamp"]
                }
                logger.info(f"Fear & Greed Index: {result['value']} ({result['classification']})")
                return result
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed: {e}")
            return {}
    
    def get_global_market_data(self) -> Dict:
        """Get global cryptocurrency market data"""
        url = f"{self.base_url}/global"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()["data"]
            
            result = {
                "total_market_cap_usd": data["total_market_cap"]["usd"],
                "total_volume_usd": data["total_volume"]["usd"],
                "btc_dominance": data["market_cap_percentage"]["btc"],
                "eth_dominance": data["market_cap_percentage"]["eth"],
                "active_cryptos": data["active_cryptocurrencies"],
                "markets": data["markets"]
            }
            
            logger.info(f"Global market cap: ${result['total_market_cap_usd']:,.0f}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching global data: {e}")
            return {}


# Convenience function
def fetch_all_data(coin_ids: List[str]) -> Dict:
    """Fetch all market data at once"""
    crawler = CryptoCrawler()
    
    return {
        "market": crawler.get_market_data(coin_ids),
        "trending": crawler.get_trending(),
        "fear_greed": crawler.get_fear_greed_index(),
        "global": crawler.get_global_market_data()
    }
