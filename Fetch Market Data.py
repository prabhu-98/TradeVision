import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta

class MarketDataFetcher:
    def __init__(self, symbol, exchange="US"):
        self.symbol = symbol
        self.exchange = exchange
        self.data = None
    
    def is_market_open(self):
        """Check if the market is open based on the exchange."""
        now = datetime.now()
        if self.exchange == "India":
            india_time = now + timedelta(hours=5, minutes=30)
            market_open = india_time.replace(hour=9, minute=15)
            market_close = india_time.replace(hour=15, minute=30)
            return market_open <= india_time <= market_close
        else:
            est_time = now - timedelta(hours=5)
            market_open = est_time.replace(hour=9, minute=30)
            market_close = est_time.replace(hour=16, minute=0)
            return market_open <= est_time <= market_close
    
    def fetch_data(self, period='5d', interval='15m'):
        """Fetch historical market data from Yahoo Finance."""
        if not self.is_market_open():
            st.warning("Market is closed. Data might be outdated.")
        
        ticker = yf.Ticker(self.symbol)
        self.data = ticker.history(period=period, interval=interval)
        
        if self.data.empty:
            st.error(f"No data found for {self.symbol}.")
            return None
        
        st.success(f"Fetched {len(self.data)} records for {self.symbol}")
        return self.process_data()
    
    def process_data(self):
        """Compute key market risk metrics."""
        self.data['Volatility'] = self.data['Close'].rolling(window=20).std()
        self.data['Volume_MA'] = self.data['Volume'].rolling(window=20).mean()
        self.data['Price_Change'] = self.data['Close'].pct_change()
        self.data['Spread'] = self.data['High'] - self.data['Low']
        return self.data
    
    def calculate_risk_metrics(self, trade_size):
        """Calculate trade settlement risk based on market conditions."""
        if self.data is None or self.data.empty:
            return None
        
        latest_data = self.data.iloc[-1]
        avg_volume = self.data['Volume'].mean()
        
        risk_metrics = {
            'volatility_risk': min(1, latest_data['Volatility'] / latest_data['Close'] if latest_data['Close'] != 0 else 1),
            'liquidity_risk': min(1, trade_size / avg_volume if avg_volume != 0 else 1),
            'spread_risk': min(1, latest_data['Spread'] / latest_data['Close'] if latest_data['Close'] != 0 else 1),
            'volume_risk': min(1, 1 - (latest_data['Volume'] / latest_data['Volume_MA'] if latest_data['Volume_MA'] != 0 else 1))
        }
        
        total_risk = sum(risk_metrics.values()) / len(risk_metrics)
        risk_metrics['total_risk'] = min(1, total_risk)
        
        return risk_metrics
    
    def generate_trade_recommendations(self, risk_metrics, trade_size):
        """Generate trade recommendations based on calculated risk."""
        if risk_metrics is None:
            return None
        
        total_risk = risk_metrics['total_risk']
        
        if total_risk > 0.8:
            return "High Risk - Avoid trading or split into smaller orders"
        elif total_risk > 0.5:
            return "Medium Risk - Consider splitting trade or waiting for better conditions"
        else:
            return "Low Risk - Proceed with trade"
    
    def get_optimal_execution_time(self):
        """Suggest optimal execution time based on historical patterns."""
        if self.data is None or self.data.empty:
            return "Unable to determine optimal execution time due to lack of data"
        
        self.data['Hour'] = pd.to_datetime(self.data.index).hour
        hourly_risk = self.data.groupby('Hour').agg({
            'Volatility': 'mean',
            'Volume': 'mean',
            'Spread': 'mean'
        })
        hourly_risk = (hourly_risk - hourly_risk.mean()) / hourly_risk.std()
        best_hour = hourly_risk.mean(axis=1).idxmin()
        
        return f"Optimal execution time: {best_hour}:00"
    
# Streamlit UI
st.title("Trade Settlement Risk Analyzer")

symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, TCS.NS):", "AAPL")
exchange = st.selectbox("Select Exchange:", ["US", "India"], index=0)
trade_size = st.number_input("Trade Size (Shares):", min_value=1, value=100)

if st.button("Analyze Risk"):
    fetcher = MarketDataFetcher(symbol, exchange)
    market_data = fetcher.fetch_data()
    
    if market_data is not None:
        risk_metrics = fetcher.calculate_risk_metrics(trade_size)
        trade_recommendation = fetcher.generate_trade_recommendations(risk_metrics, trade_size)
        optimal_time = fetcher.get_optimal_execution_time()
        
        st.subheader("Market Insights")
        st.metric("Open Price", f"{market_data.iloc[-1]['Open']:.2f}")
        st.metric("High Price", f"{market_data.iloc[-1]['High']:.2f}")
        st.metric("Low Price", f"{market_data.iloc[-1]['Low']:.2f}")
        st.metric("Volume", f"{market_data.iloc[-1]['Volume']:,}")
        
        st.subheader("Risk Metrics")
        st.json(risk_metrics)
        
        st.subheader("Trade Recommendation")
        st.success(trade_recommendation)
        
        st.subheader("Optimal Execution Time")
        st.info(optimal_time)
        
        st.subheader("Risk Breakdown")
        risk_df = pd.DataFrame(list(risk_metrics.items()), columns=["Metric", "Value"])
        fig = px.bar(risk_df, x="Metric", y="Value", title="Risk Breakdown", color="Value")
        st.plotly_chart(fig)
        
        st.subheader("Stock Price Trend")
        fig2 = px.line(market_data, x=market_data.index, y="Close", title="Stock Price Trend Over Time")
        st.plotly_chart(fig2)
